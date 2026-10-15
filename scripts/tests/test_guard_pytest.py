"""commit-check-paths tasks 4.3-4.4: the pytest plugin checks each test's tags against its reads.

Each test runs pytest in a subprocess, on a throwaway project holding this repository's guard.py
and guard_pytest.py, as a governed repository would (design D9).
"""

import os
import subprocess
import sys
from pathlib import Path

from conftest import SCRIPTS

DECLARATION = """\
version = 1

[skip]
paths = ["openspec/**"]

[scopes.docs]
paths = ["docs/**"]
"""

CONFTEST = 'import sys\nsys.path.insert(0, "scripts")\npytest_plugins = ["guard_pytest"]\n'


def project(tmp_path: Path, tests: str, declaration: str | None = DECLARATION) -> Path:
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
    return root


def run_pytest(root: Path) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--strict-markers", "-p", "no:cacheprovider"],
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
