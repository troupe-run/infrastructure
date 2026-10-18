"""commit-check-paths tasks 4.3-4.4: the pytest plugin checks each test's tags against its reads,
and scope-test-directories tasks 3.1-3.2: it tags the tests under a scope's `tests` directories.

Each test runs pytest in a subprocess, on a throwaway project holding this repository's guard.py
and guard_pytest.py, as a governed repository would (design D9).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS

DECLARATION = """\
version = 1

[skip]
paths = ["openspec/**"]

[scopes.docs]
paths = ["docs/**"]
"""

CONFTEST = 'import sys\nsys.path.insert(0, "scripts")\npytest_plugins = ["guard_pytest"]\n'


def project(
    tmp_path: Path,
    tests: str,
    declaration: str | None = DECLARATION,
    files: dict[str, str] | None = None,
) -> Path:
    root = tmp_path / "project"
    (root / "scripts").mkdir(parents=True)
    for name in ("guard.py", "guard_pytest.py"):
        (root / "scripts" / name).write_text((SCRIPTS / name).read_text(encoding="utf-8"))
    if declaration is not None:
        (root / "scripts" / "check-paths.toml").write_text(declaration, encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "a.md").write_text("docs\n", encoding="utf-8")
    (root / "openspec").mkdir()
    (root / "openspec" / "a.md").write_text("spec\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (root / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    (root / "test_reads.py").write_text(
        "from pathlib import Path\n\nimport pytest\n\nROOT = Path(__file__).parent\n\n" + tests,
        encoding="utf-8",
    )
    for relative, text in (files or {}).items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text, encoding="utf-8")
    return root


def run_pytest(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--strict-markers", "-p", "no:cacheprovider", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_an_untagged_test_reading_a_scope_s_path_fails_naming_the_test_file_and_tag(
    tmp_path: Path,
) -> None:
    root = project(
        tmp_path, 'def test_reads_docs():\n    assert (ROOT / "docs/a.md").read_text()\n'
    )
    result = run_pytest(root)
    assert result.returncode != 0, result.stdout
    assert "test_reads.py::test_reads_docs reads docs/a.md" in result.stdout
    assert "`docs`" in result.stdout


def test_the_same_test_tagged_with_the_scope_passes(tmp_path: Path) -> None:
    root = project(
        tmp_path,
        '@pytest.mark.docs\ndef test_reads_docs():\n    assert (ROOT / "docs/a.md").read_text()\n',
    )
    result = run_pytest(root)
    assert result.returncode == 0, result.stdout


def test_a_test_reading_a_skipped_path_through_open_fails_naming_the_skip_entry(
    tmp_path: Path,
) -> None:
    root = project(
        tmp_path,
        "def test_reads_spec():\n"
        '    with open(ROOT / "openspec/a.md", encoding="utf-8") as file:\n'
        "        assert file.read()\n",
    )
    result = run_pytest(root)
    assert result.returncode != 0, result.stdout
    assert "test_reads.py::test_reads_spec reads openspec/a.md" in result.stdout
    assert "`openspec/**`" in result.stdout


def test_a_test_reading_its_own_temporary_files_passes(tmp_path: Path) -> None:
    root = project(
        tmp_path,
        "def test_tmp(tmp_path):\n"
        '    (tmp_path / "docs").mkdir()\n'
        '    (tmp_path / "docs" / "x.md").write_text("x")\n'
        '    assert (tmp_path / "docs" / "x.md").read_text() == "x"\n',
    )
    result = run_pytest(root)
    assert result.returncode == 0, result.stdout


def test_without_a_declaration_reads_pass_and_no_marker_is_registered(tmp_path: Path) -> None:
    reads = 'def test_reads_docs():\n    assert (ROOT / "docs/a.md").read_text()\n'
    assert run_pytest(project(tmp_path / "plain", reads, declaration=None)).returncode == 0
    marked = project(
        tmp_path / "marked", "@pytest.mark.docs\ndef test_marked():\n    pass\n", declaration=None
    )
    result = run_pytest(marked)
    assert result.returncode != 0
    assert "'docs' not found in `markers` configuration option" in result.stdout + result.stderr


def test_a_malformed_declaration_fails_the_session_with_the_guard_s_message(
    tmp_path: Path,
) -> None:
    root = project(
        tmp_path,
        "def test_nothing():\n    pass\n",
        declaration='version = 1\n[skip]\npaths = ["docs/*.md"]\n',
    )
    result = run_pytest(root)
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "scripts/check-paths.toml is malformed" in output
    assert "`docs/*.md` uses a wildcard" in output


def test_a_read_at_import_counts_for_every_test_in_the_module(tmp_path: Path) -> None:
    """Found in troupe: test_runs_doc.py reads its doc at module level, outside any test."""
    root = project(
        tmp_path,
        'TEXT = (ROOT / "docs/a.md").read_text()\n\n'
        "def test_one():\n    assert TEXT\n\n"
        "def test_two():\n    assert TEXT\n",
    )
    result = run_pytest(root)
    assert result.returncode != 0, result.stdout
    assert "test_reads.py::test_one reads docs/a.md" in result.stdout
    assert "test_reads.py::test_two reads docs/a.md" in result.stdout


def test_a_read_while_collecting_parameters_counts_for_each_generated_test(
    tmp_path: Path,
) -> None:
    """Found in troupe: test_cli_docs.py parametrizes from its doc during collection."""
    root = project(
        tmp_path,
        "def lines():\n"
        '    return (ROOT / "docs/a.md").read_text().splitlines()\n\n'
        '@pytest.mark.parametrize("line", lines())\n'
        "def test_line(line):\n    assert line\n",
    )
    result = run_pytest(root)
    assert result.returncode != 0, result.stdout
    assert "test_reads.py::test_line[docs] reads docs/a.md" in result.stdout


def test_a_module_marked_with_the_scope_covers_its_import_time_reads(tmp_path: Path) -> None:
    root = project(
        tmp_path,
        "pytestmark = pytest.mark.docs\n\n"
        'TEXT = (ROOT / "docs/a.md").read_text()\n\n'
        "def test_one():\n    assert TEXT\n",
    )
    assert run_pytest(root).returncode == 0


def test_a_shared_fixture_s_read_counts_for_every_test_that_uses_it(tmp_path: Path) -> None:
    root = project(
        tmp_path,
        '@pytest.fixture(scope="session")\n'
        "def doc():\n"
        '    return (ROOT / "docs/a.md").read_text()\n\n'
        "@pytest.mark.docs\n"
        "def test_first(doc):\n    assert doc\n\n"
        "def test_second(doc):\n    assert doc\n",
    )
    result = run_pytest(root)
    assert result.returncode != 0, result.stdout
    assert "test_reads.py::test_second reads docs/a.md" in result.stdout
    assert "test_first reads" not in result.stdout


# A scope's `tests` directories (scope-test-directories tasks 3.1-3.2, design D5, D6)

SUITES = """\
version = 1

[scopes.sa]
paths = ["docs/**"]
tests = ["suites/a/**", "suites/shared/**"{extra}]

[scopes.sb]
paths = ["path1/**"]
tests = ["suites/b/**", "suites/shared/**"]
"""

SUITE_FILES = {
    "suites/a/test_a.py": (
        "from pathlib import Path\n\n"
        "ROOT = Path(__file__).parents[2]\n\n"
        'def test_reads_docs():\n    assert (ROOT / "docs/a.md").read_text()\n\n'
        "def test_two():\n    pass\n"
    ),
    "suites/a/deeper/test_deep.py": "def test_deep():\n    pass\n",
    "suites/b/test_b.py": "def test_b():\n    pass\n",
    "suites/shared/test_shared.py": "def test_shared():\n    pass\n",
    "suites/c/test_c.py": (
        "import pytest\n\n@pytest.mark.sa\ndef test_marked():\n    pass\n\n"
        "def test_unmarked():\n    pass\n"
    ),
}

IN_SA = {
    "suites/a/test_a.py::test_reads_docs",
    "suites/a/test_a.py::test_two",
    "suites/a/deeper/test_deep.py::test_deep",
    "suites/shared/test_shared.py::test_shared",
    "suites/c/test_c.py::test_marked",
}
IN_SB = {"suites/b/test_b.py::test_b", "suites/shared/test_shared.py::test_shared"}
PARALLEL = [pytest.param((), id="serial"), pytest.param(("-n", "2"), id="xdist")]


def suites(tmp_path: Path, extra: str = "") -> Path:
    return project(
        tmp_path,
        "def test_root():\n    pass\n",
        declaration=SUITES.format(extra=extra),
        files=SUITE_FILES,
    )


def passed(result: subprocess.CompletedProcess[str]) -> set[str]:
    """The node ids pytest's `-rA` summary lists as passed, serially or under xdist."""
    return {
        line.split(" ", 1)[1].strip()
        for line in result.stdout.splitlines()
        if line.startswith("PASSED ")
    }


@pytest.mark.parametrize("parallel", PARALLEL)
@pytest.mark.parametrize(("scope", "expected"), [("sa", IN_SA), ("sb", IN_SB)])
def test_a_scope_selects_exactly_its_tests_directories_and_its_marked_tests(
    tmp_path: Path, parallel: tuple[str, ...], scope: str, expected: set[str]
) -> None:
    result = run_pytest(suites(tmp_path), "-rA", "-m", scope, *parallel)
    assert result.returncode == 0, result.stdout
    assert passed(result) == expected


@pytest.mark.parametrize("parallel", PARALLEL)
def test_a_full_run_with_tests_directories_runs_every_test(
    tmp_path: Path, parallel: tuple[str, ...]
) -> None:
    result = run_pytest(suites(tmp_path), "-rA", *parallel)
    assert result.returncode == 0, result.stdout
    assert len(passed(result)) == 8


def test_an_untagged_test_under_a_scope_s_directory_may_read_the_scope_s_paths(
    tmp_path: Path,
) -> None:
    result = run_pytest(suites(tmp_path), "-rA", "suites/a/test_a.py")
    assert result.returncode == 0, result.stdout
    assert "suites/a/test_a.py::test_reads_docs" in passed(result)


def test_the_same_read_outside_the_scope_s_directories_still_fails(tmp_path: Path) -> None:
    root = suites(tmp_path)
    (root / "suites/b/test_b.py").write_text(
        "from pathlib import Path\n\n"
        "def test_b():\n"
        '    assert (Path(__file__).parents[2] / "docs/a.md").read_text()\n',
        encoding="utf-8",
    )
    result = run_pytest(root)
    assert result.returncode != 0, result.stdout
    assert "suites/b/test_b.py::test_b reads docs/a.md" in result.stdout


GONE = ', "suites/gone/**"'


@pytest.mark.parametrize("parallel", PARALLEL)
@pytest.mark.parametrize("selection", [(), ("-m", "sa")], ids=["full", "scope"])
def test_an_entry_matching_no_test_fails_the_run_naming_the_scope_and_entry(
    tmp_path: Path, parallel: tuple[str, ...], selection: tuple[str, ...]
) -> None:
    result = run_pytest(suites(tmp_path, extra=GONE), *selection, *parallel)
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "INTERNALERROR" not in output
    assert "scripts/check-paths.toml::scopes.sa.tests[2]" in output
    assert "scope `sa` runs the tests under `suites/gone/**`" in output
    assert "Correct the entry" in output


@pytest.mark.parametrize("target", ["suites/b", "suites/b/test_b.py", "suites/a/test_a.py"])
def test_a_run_that_does_not_collect_from_the_entry_s_directory_does_not_check_it(
    tmp_path: Path, target: str
) -> None:
    result = run_pytest(suites(tmp_path, extra=GONE), target)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("testpaths", ['["suites"]', '["suites/b"]'])
def test_a_run_from_testpaths_checks_every_entry(tmp_path: Path, testpaths: str) -> None:
    """Found in troupe: its runs collect from `testpaths`, which lists the real suites, so a stale
    entry is outside every one of them. Checking only inside them let a missing suite pass."""
    root = suites(tmp_path, extra=GONE)
    (root / "pyproject.toml").write_text(
        f"[tool.pytest.ini_options]\ntestpaths = {testpaths}\n", encoding="utf-8"
    )
    result = run_pytest(root)
    assert result.returncode == 1, result.stdout
    assert "scope `sa` runs the tests under `suites/gone/**`" in result.stdout


def test_a_run_given_a_directory_containing_the_entry_checks_it(tmp_path: Path) -> None:
    result = run_pytest(suites(tmp_path, extra=GONE), "suites")
    assert result.returncode == 1, result.stdout
    assert "scope `sa` runs the tests under `suites/gone/**`" in result.stdout


def test_the_scope_s_marker_says_which_directories_it_runs(tmp_path: Path) -> None:
    result = run_pytest(suites(tmp_path), "--markers")
    assert "@pytest.mark.sa: reads docs/**; runs suites/a/**, suites/shared/**" in result.stdout
    assert "@pytest.mark.sb: reads path1/**; runs suites/b/**, suites/shared/**" in result.stdout
