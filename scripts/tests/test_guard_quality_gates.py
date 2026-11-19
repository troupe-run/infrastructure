"""The quality gates' measures (spec: quality-gates; quality-gates design D2-D8).

Named test_guard_*: scripts/quality_gates.py is delivered with the guard and runs in troupe's check
on every OS, so the guard's legs run these tests on each OS and Python too.

Tool output is real: pip-audit, OSV, npm audit, coverage.py and Vitest reports were captured on
2026-11-17 (fixtures/quality-gates). lizard runs for real on scratch git repositories.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

import quality_gates as qg

FIXTURES = Path(__file__).parent / "fixtures" / "quality-gates"
LIZARD = shutil.which("lizard", path=str(Path(sys.executable).parent)) or "lizard"

CONFIG = """\
version = 1

[coverage]
floor = 80.0
tolerance = 0.5

[coverage.packages.core]
paths = ["packages/core/src"]
baseline = 90.0

[coverage.packages.plugin]
paths = ["plugins/plugin"]

[complexity]
block_above = 5
languages = ["python", "typescript"]
exclude = ["**/tests/**"]

[audit]
lock_files = ["uv.lock"]
block = ["high", "critical"]
"""


def fixture(name: str) -> dict[str, object]:
    data: dict[str, object] = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return data


@pytest.fixture(autouse=True)
def no_inherited_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tests may run inside a real pre-commit hook, whose GIT_* variables name this repo."""
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "commit.gpgsign", "false")
    (tmp_path / "quality-gates.toml").write_text(CONFIG, encoding="utf-8")
    return tmp_path


def commit(repo: Path, files: dict[str, str], message: str = "change") -> str:
    for path, text in files.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def branches(count: int, name: str = "f") -> str:
    """A Python function with cyclomatic complexity 1 + count."""
    body = "".join(f"    if x == {i}:\n        return {i}\n" for i in range(count))
    return f"def {name}(x):\n{body}    return -1\n"


# --- Config ---------------------------------------------------------------------------------------


def test_a_valid_config_parses_every_table() -> None:
    config = qg.parse_config(CONFIG + '\n[mutation]\nlast_judged = "abc"\n')
    assert config.coverage is not None
    assert config.coverage.floor == 80.0
    assert config.coverage.tolerance == 0.5
    assert [(p.name, p.paths, p.baseline) for p in config.coverage.packages] == [
        ("core", ("packages/core/src",), 90.0),
        ("plugin", ("plugins/plugin",), None),
    ]
    assert config.complexity == qg.ComplexityConfig(5, ("python", "typescript"), ("**/tests/**",))
    assert config.audit == qg.AuditConfig(("uv.lock",), ("high", "critical"))
    assert config.mutation == {"last_judged": "abc"}


def test_mutation_is_empty_when_absent() -> None:
    assert qg.parse_config(CONFIG).mutation == {}


def without_coverage(config: str) -> str:
    """The config with its [coverage] tables removed, as a repository that measures none has it."""
    start = config.index("[coverage]")
    return config[:start] + config[config.index("[complexity]") :]


def test_coverage_is_optional_and_none_when_absent() -> None:
    """Coverage applies only to the repositories infrastructure's list names (#332)."""
    config = qg.parse_config(without_coverage(CONFIG))
    assert config.coverage is None
    assert config.complexity.block_above == 5


def test_a_malformed_coverage_table_is_still_refused() -> None:
    with pytest.raises(qg.GateError, match=r"`coverage\.floor` is required"):
        qg.parse_config(CONFIG.replace("floor = 80.0\n", "", 1))


@pytest.mark.parametrize(
    ("before", "after", "message"),
    [
        ("block_above = 5", "block_abve = 5", "unknown key `complexity.block_abve`"),
        ("[audit]", "[audits]\nx = 1\n[audit]", "unknown key `audits`"),
        ("floor = 80.0", "floor = 180.0", "`coverage.floor` must be from 0 to 100"),
        ("floor = 80.0", 'floor = "80"', "`coverage.floor` must be a number"),
        ("tolerance = 0.5", "tolerance = -1", "`coverage.tolerance` must be from 0 to 100"),
        ("block_above = 5", "block_above = 2.5", "`complexity.block_above` must be a whole number"),
        (
            "block_above = 5",
            "block_above = true",
            "`complexity.block_above` must be a whole number",
        ),
        ('"high", "critical"', '"high", "severe"', "`audit.block` can't hold 'severe'"),
        ('"python", "typescript"', '"python", "rust"', "`complexity.languages` can't hold 'rust'"),
        ('["uv.lock"]', '["poetry.lock"]', "`audit.lock_files` can't hold 'poetry.lock'"),
        (
            "baseline = 90.0",
            "baseline = 90.0\nfloor = 1",
            "unknown key `coverage.packages.core.floor`",
        ),
        (
            'paths = ["plugins/plugin"]',
            'paths = ["packages/core"]',
            "packages `core` and `plugin` overlap",
        ),
        ("version = 1", "version = 2", "`version` must be 1"),
        ("[complexity]\nblock_above = 5", "[complexity]", "`complexity.block_above` is required"),
    ],
)
def test_a_bad_config_names_the_key_and_what_is_valid(
    before: str, after: str, message: str
) -> None:
    assert before in CONFIG
    with pytest.raises(qg.GateError, match=message.replace("(", r"\(").replace(")", r"\)")):
        qg.parse_config(CONFIG.replace(before, after, 1))


def test_an_unknown_key_lists_what_the_table_takes() -> None:
    with pytest.raises(qg.GateError, match="takes: block_above, languages, exclude"):
        qg.parse_config(CONFIG.replace("block_above = 5", "block_abve = 5"))


def test_a_missing_config_is_an_error_not_a_skipped_gate(tmp_path: Path) -> None:
    with pytest.raises(qg.GateError, match=r"quality-gates.toml is missing"):
        qg.read_config(tmp_path)


def test_overlap_is_by_whole_path_segments() -> None:
    config = CONFIG.replace('paths = ["plugins/plugin"]', 'paths = ["packages/core/src2"]')
    coverage = qg.parse_config(config).coverage
    assert coverage is not None
    assert len(coverage.packages) == 2


@pytest.mark.parametrize(
    ("pattern", "path", "matches"),
    [
        ("**/tests/**", "scripts/tests/test_x.py", True),
        ("**/tests/**", "tests/unit/a.ts", True),
        ("**/tests/**", "scripts/testsuite.py", False),
        ("scripts/guard.py", "scripts/guard.py", True),
        ("scripts/*.py", "scripts/sub/a.py", False),
        ("src/**/*.ts", "src/a.ts", True),
    ],
)
def test_exclude_patterns(pattern: str, path: str, matches: bool) -> None:
    assert qg.excluded(path, [pattern]) is matches


# --- Complexity -----------------------------------------------------------------------------------


def test_a_new_function_above_the_limit_fails(repo: Path) -> None:
    base = commit(repo, {"a.py": "def ok():\n    return 1\n"})
    (repo / "b.py").write_text(branches(6), encoding="utf-8")
    problems = qg.complexity_problems(repo, base, qg.read_config(repo).complexity, LIZARD)
    assert [p.text() for p in problems] == [
        "b.py:1 f: a new function with complexity 7, above the limit of 5"
    ]


def test_a_function_at_the_limit_passes(repo: Path) -> None:
    base = commit(repo, {"a.py": "def ok():\n    return 1\n"})
    (repo / "a.py").write_text(branches(4), encoding="utf-8")
    assert qg.complexity_problems(repo, base, qg.read_config(repo).complexity, LIZARD) == []


def test_an_old_complex_function_made_worse_fails(repo: Path) -> None:
    base = commit(repo, {"a.py": branches(6)})
    (repo / "a.py").write_text(branches(7), encoding="utf-8")
    problems = qg.complexity_problems(repo, base, qg.read_config(repo).complexity, LIZARD)
    assert [p.text() for p in problems] == [
        "a.py:1 f: complexity rose from 7 to 8, above the limit of 5"
    ]


def test_an_old_complex_function_edited_without_more_branches_passes(repo: Path) -> None:
    base = commit(repo, {"a.py": branches(6)})
    (repo / "a.py").write_text(branches(6).replace("return -1", "return -2"), encoding="utf-8")
    assert qg.complexity_problems(repo, base, qg.read_config(repo).complexity, LIZARD) == []


def test_an_untouched_complex_function_beside_an_edit_passes(repo: Path) -> None:
    base = commit(repo, {"a.py": branches(6) + "\n\ndef g():\n    return 1\n"})
    edited = branches(6) + "\n\ndef g():\n    return 2\n"
    (repo / "a.py").write_text(edited, encoding="utf-8")
    assert qg.complexity_problems(repo, base, qg.read_config(repo).complexity, LIZARD) == []


def test_an_excluded_path_isnt_measured(repo: Path) -> None:
    base = commit(repo, {"a.py": "x = 1\n"})
    (repo / "scripts" / "tests").mkdir(parents=True)
    (repo / "scripts" / "tests" / "test_a.py").write_text(branches(9), encoding="utf-8")
    assert qg.complexity_problems(repo, base, qg.read_config(repo).complexity, LIZARD) == []


def test_a_delivered_file_isnt_measured(repo: Path) -> None:
    """A delivered file's complexity is judged at its source, with no pattern in the config."""
    base = commit(repo, {"a.py": "x = 1\n"})
    (repo / "scripts").mkdir()
    (repo / "scripts" / "mutation_run.py").write_text(branches(9), encoding="utf-8")
    config = qg.read_config(repo).complexity
    assert [p.function.path for p in qg.complexity_problems(repo, base, config, LIZARD)] == [
        "scripts/mutation_run.py"
    ]
    (repo / ".github").mkdir()
    shutil.copy(FIXTURES / "troupe-delivery-list.json", repo / ".github" / "guard-delivery.json")
    assert qg.complexity_problems(repo, base, config, LIZARD) == []


def test_a_language_the_config_doesnt_name_isnt_measured(repo: Path) -> None:
    base = commit(repo, {"a.py": "x = 1\n"})
    js = "function f(x) {\n" + "".join(f"  if (x === {i}) return {i};\n" for i in range(9)) + "}\n"
    (repo / "a.mjs").write_text(js, encoding="utf-8")
    assert qg.complexity_problems(repo, base, qg.read_config(repo).complexity, LIZARD) == []
    (repo / "a.mts").write_text(js, encoding="utf-8")
    problems = qg.complexity_problems(repo, base, qg.read_config(repo).complexity, LIZARD)
    assert [p.function.path for p in problems] == ["a.mts"]


def test_staged_and_unstaged_edits_are_both_judged(repo: Path) -> None:
    base = commit(repo, {"a.py": "x = 1\n", "b.py": "y = 1\n"})
    (repo / "a.py").write_text(branches(6, "staged"), encoding="utf-8")
    git(repo, "add", "a.py")
    (repo / "b.py").write_text(branches(6, "unstaged"), encoding="utf-8")
    problems = qg.complexity_problems(repo, base, qg.read_config(repo).complexity, LIZARD)
    assert sorted(p.function.name for p in problems) == ["staged", "unstaged"]


def test_untracked_files_count_as_wholly_changed_and_are_never_opened(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A gate reads no file it doesn't measure, such as an untracked file under openspec/."""
    base = commit(repo, {"a.py": "x = 1\n"})
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    (repo / "openspec" / "changes" / "x").mkdir(parents=True)
    (repo / "openspec" / "changes" / "x" / "design.md").write_text("# x\n", encoding="utf-8")

    def refuse(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("changed_lines opened a file")

    monkeypatch.setattr(Path, "read_text", refuse)
    monkeypatch.setattr(Path, "read_bytes", refuse)
    assert qg.changed_lines(repo, base) == {
        "a.py": frozenset({1}),
        "openspec/changes/x/design.md": None,
    }


def test_committed_work_since_the_base_is_judged(repo: Path) -> None:
    base = commit(repo, {"a.py": "x = 1\n"})
    commit(repo, {"a.py": branches(6)})
    problems = qg.complexity_problems(repo, base, qg.read_config(repo).complexity, LIZARD)
    assert [p.function.name for p in problems] == ["f"]


def test_a_missing_base_says_how_to_fetch_it(repo: Path) -> None:
    commit(repo, {"a.py": "x = 1\n"})
    with pytest.raises(qg.GateError, match=r"git fetch origin main"):
        qg.resolve_base(repo, None)
    with pytest.raises(qg.GateError, match=r"isn't a commit here"):
        qg.resolve_base(repo, "0" * 40)


def test_the_base_defaults_to_where_the_work_left_origin_main(repo: Path) -> None:
    base = commit(repo, {"a.py": "x = 1\n"})
    git(repo, "update-ref", "refs/remotes/origin/main", base)
    commit(repo, {"a.py": "x = 2\n"})
    assert qg.resolve_base(repo, None) == base


def test_the_complexity_command_fails_and_names_the_limit(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = commit(repo, {"a.py": "x = 1\n"})
    (repo / "a.py").write_text(branches(6), encoding="utf-8")
    assert qg.main(["complexity", "--base", base, "--lizard", LIZARD], root=repo) == 1
    out = capsys.readouterr().out
    assert "a.py:1 f: a new function with complexity 7" in out
    assert "[complexity] block_above" in out


def test_a_bad_config_stops_the_gate_with_exit_2(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "quality-gates.toml").write_text(CONFIG.replace("floor", "flor"), encoding="utf-8")
    assert qg.main(["complexity", "--base", "HEAD", "--lizard", LIZARD], root=repo) == 2
    assert "unknown key `coverage.flor`" in capsys.readouterr().err


# --- Coverage -------------------------------------------------------------------------------------


def _coverage_config() -> qg.CoverageConfig:
    coverage = qg.parse_config(CONFIG).coverage
    assert coverage is not None
    return coverage


COVERAGE = _coverage_config()


def test_coveragepy_counts_statements_and_branches(tmp_path: Path) -> None:
    counts = qg.coveragepy_counts(fixture("coveragepy-troupe-excerpt.json"), tmp_path)
    script = counts["plugins/runner-scripted/src/troupe_runner_scripted/script.py"]
    summary = fixture("coveragepy-troupe-excerpt.json")["files"]
    raw = summary["plugins/runner-scripted/src/troupe_runner_scripted/script.py"]["summary"]  # type: ignore[index]
    assert script == qg.Counts(
        raw["covered_lines"] + raw["covered_branches"], raw["num_statements"] + raw["num_branches"]
    )
    # coverage.py's own branch-mode percentage is the same measure.
    assert script.percent == pytest.approx(raw["percent_covered"])


def test_a_coveragepy_report_without_branches_is_refused(tmp_path: Path) -> None:
    report = {"files": {"a.py": {"summary": {"covered_lines": 1, "num_statements": 1}}}}
    with pytest.raises(qg.GateError, match="branch = true"):
        qg.coveragepy_counts(report, tmp_path)


def test_vitest_counts_are_made_relative_to_the_root() -> None:
    counts = qg.vitest_counts(fixture("vitest-website-excerpt.json"), Path("/ROOT"))
    assert sorted(counts) == ["scripts/roadmap-lib.mjs", "src/lib/site-path.ts"]
    raw = fixture("vitest-website-excerpt.json")["/ROOT/src/lib/site-path.ts"]
    assert counts["src/lib/site-path.ts"] == qg.Counts(
        raw["statements"]["covered"] + raw["branches"]["covered"],  # type: ignore[index]
        raw["statements"]["total"] + raw["branches"]["total"],  # type: ignore[index]
    )


@pytest.mark.parametrize(
    ("path", "root", "relative"),
    [
        ("/repo/src/a.ts", "/repo", "src/a.ts"),
        ("src/a.ts", "/repo", "src/a.ts"),
        ("C:\\work\\site\\src\\a.ts", "C:\\work\\site", "src/a.ts"),
        ("C:/work/site/scripts/b.mjs", "C:/work/site", "scripts/b.mjs"),
        ("/elsewhere/c.ts", "/repo", "/elsewhere/c.ts"),
        ("/repo2/c.ts", "/repo", "/repo2/c.ts"),
    ],
)
def test_report_paths_are_made_relative_whatever_their_separators(
    path: str, root: str, relative: str
) -> None:
    assert qg._relative(path, Path(root)) == relative


def test_coverage_below_baseline_by_more_than_the_tolerance_fails() -> None:
    files = {
        "packages/core/src/a.py": qg.Counts(892, 1000),
        "plugins/plugin/b.py": qg.Counts(9, 10),
    }
    result = qg.coverage_result(files, COVERAGE)
    assert result.problems == [
        "core measures 89.2%, 0.8 below its baseline of 90.0% (tolerance 0.5)"
    ]
    assert result.lines[0] == "core: 89.2% (baseline 90.0%, -0.8)"


def test_coverage_within_the_tolerance_passes() -> None:
    files = {
        "packages/core/src/a.py": qg.Counts(895, 1000),
        "plugins/plugin/b.py": qg.Counts(9, 10),
    }
    assert qg.coverage_result(files, COVERAGE).problems == []


def test_coverage_above_baseline_says_how_far_it_could_be_raised() -> None:
    files = {
        "packages/core/src/a.py": qg.Counts(921, 1000),
        "plugins/plugin/b.py": qg.Counts(9, 10),
    }
    result = qg.coverage_result(files, COVERAGE)
    assert result.problems == []
    assert (
        result.lines[0]
        == "core: 92.1% (baseline 90.0%, +2.1); its baseline could be raised to 92.1"
    )


def test_a_package_with_no_baseline_below_the_floor_fails() -> None:
    files = {"packages/core/src/a.py": qg.Counts(95, 100), "plugins/plugin/b.py": qg.Counts(7, 10)}
    assert qg.coverage_result(files, COVERAGE).problems == [
        "plugin measures 70.0%, below the floor of 80.0% for a package with no baseline"
    ]


def test_a_file_in_no_package_fails() -> None:
    files = {"packages/core/src/a.py": qg.Counts(95, 100), "packages/other/c.py": qg.Counts(1, 1)}
    problems = qg.coverage_result(files, COVERAGE).problems
    assert problems[0] == (
        "packages/other/c.py is in no package. "
        "Fix: add it to a package's paths in quality-gates.toml."
    )


def test_a_package_with_nothing_to_measure_passes_and_says_so() -> None:
    files = {"packages/core/src/a.py": qg.Counts(95, 100)}
    result = qg.coverage_result(files, COVERAGE)
    assert result.problems == []
    assert "plugin: nothing to measure" in result.lines


def test_the_coverage_command_reports_every_package(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "quality-gates.toml").write_text(CONFIG, encoding="utf-8")
    report = {
        "files": {
            "packages/core/src/a.py": {"summary": {"covered_lines": 90, "num_statements": 100,
                                                   "covered_branches": 0, "num_branches": 0}},
        }
    }  # fmt: skip
    (tmp_path / "coverage.json").write_text(json.dumps(report), encoding="utf-8")
    assert (
        qg.main(["coverage", "--coveragepy", str(tmp_path / "coverage.json")], root=tmp_path) == 0
    )
    assert capsys.readouterr().out.splitlines() == [
        "coverage: core: 90.0% (baseline 90.0%, +0.0)",
        "coverage: plugin: nothing to measure",
    ]


def test_the_coverage_command_without_coverage_says_so_and_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no [coverage], the leg reads no report: there's nothing to judge it against."""
    (tmp_path / "quality-gates.toml").write_text(without_coverage(CONFIG), encoding="utf-8")
    missing = tmp_path / "never-written.json"
    assert qg.main(["coverage", "--coveragepy", str(missing)], root=tmp_path) == 0
    assert capsys.readouterr().out.splitlines() == [
        "coverage: not measured in this repository (no [coverage] in quality-gates.toml)"
    ]


# --- Delivered files (#333) -----------------------------------------------------------------------

TROUPE_SCRIPTS = """\
version = 1

[coverage]
floor = 80.0
tolerance = 0.6

[coverage.packages.scripts]
paths = ["scripts"]
baseline = 88.4

[complexity]
block_above = 25
languages = ["python"]

[audit]
lock_files = ["uv.lock"]
block = ["high", "critical"]
"""
"""troupe's `scripts` package and tolerance, from its quality-gates.toml at 4ffa922d."""


def _statements(covered: int, total: int) -> dict[str, dict[str, int]]:
    return {"summary": {"covered_lines": covered, "num_statements": total,
                        "covered_branches": 0, "num_branches": 0}}  # fmt: skip


def troupe_after_325(root: Path) -> Path:
    """troupe as troupe-run/troupe#444 found it on 2026-11-18: its delivered list (copied from
    troupe 4ffa922d) names the five scripts/mutation_*.py files #325 began delivering, 626
    statements untested in troupe, and no pattern of troupe's own leaves them out. Its own scripts
    measured 88.5%; with the delivered ones counted, 71.9%. The report's statement counts are
    those figures, split over the files."""
    (root / "quality-gates.toml").write_text(TROUPE_SCRIPTS, encoding="utf-8")
    (root / ".github").mkdir()
    shutil.copy(FIXTURES / "troupe-delivery-list.json", root / ".github" / "guard-delivery.json")
    delivered = ["children", "pr", "report", "run", "settings"]
    report = {
        "files": {
            "scripts/check.py": _statements(2399, 2711),
            **{f"scripts/mutation_{name}.py": _statements(0, 125) for name in delivered[:-1]},
            "scripts/mutation_settings.py": _statements(0, 126),
        }
    }
    (root / "coverage.json").write_text(json.dumps(report), encoding="utf-8")
    return root / "coverage.json"


def test_delivered_scripts_dont_count_in_a_receiving_repositorys_coverage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = troupe_after_325(tmp_path)
    assert qg.main(["coverage", "--coveragepy", str(report)], root=tmp_path) == 0
    assert capsys.readouterr().out.splitlines() == [
        "coverage: scripts: 88.5% (baseline 88.4%, +0.1)"
    ]


def test_a_delivered_file_under_no_package_isnt_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = troupe_after_325(tmp_path)
    data = json.loads(report.read_text(encoding="utf-8"))
    data["files"][".claude/settings.json"] = _statements(0, 3)  # delivered, under no package
    data["files"]["tools/own.py"] = _statements(1, 1)  # troupe's own, under no package
    report.write_text(json.dumps(data), encoding="utf-8")
    assert qg.main(["coverage", "--coveragepy", str(report)], root=tmp_path) == 1
    failures = [line for line in capsys.readouterr().out.splitlines() if "FAIL" in line]
    assert failures == [
        "coverage: FAIL tools/own.py is in no package. "
        "Fix: add it to a package's paths in quality-gates.toml."
    ]


def test_without_a_delivered_list_every_file_is_measured(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """infrastructure, the source, holds no list: the scripts it delivers count there."""
    report = troupe_after_325(tmp_path)
    (tmp_path / ".github" / "guard-delivery.json").unlink()
    assert qg.main(["coverage", "--coveragepy", str(report)], root=tmp_path) == 1
    assert "coverage: scripts: 71.9% (baseline 88.4%, -16.5)" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("{not json", "isn't valid JSON"),
        ('["scripts/guard.py"]', "must be an object whose `files` is a list of paths"),
        ('{"source": "troupe-run/infrastructure"}', "must be an object whose `files`"),
        ('{"files": "scripts/guard.py"}', "must be an object whose `files`"),
        ('{"files": ["scripts/guard.py", 3]}', "must be an object whose `files`"),
    ],
)
def test_a_malformed_delivered_list_stops_the_gate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str, problem: str
) -> None:
    report = troupe_after_325(tmp_path)
    (tmp_path / ".github" / "guard-delivery.json").write_text(text, encoding="utf-8")
    assert qg.main(["coverage", "--coveragepy", str(report)], root=tmp_path) == 2
    error = capsys.readouterr().err
    assert ".github/guard-delivery.json" in error
    assert problem in error


# --- Audit ----------------------------------------------------------------------------------------


def osv_fixtures(advisory_id: str) -> str | None:
    """The severity from the OSV records captured for the requests probe."""
    path = FIXTURES / f"osv-{advisory_id}.json"
    if not path.exists():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    severity: str = record["database_specific"]["severity"]
    return severity.lower()


AUDIT = qg.parse_config(CONFIG).audit


def test_pip_audit_advisories_read_severity_through_the_github_alias() -> None:
    looked_up: list[str] = []

    def lookup(advisory_id: str) -> str | None:
        looked_up.append(advisory_id)
        return osv_fixtures(advisory_id)

    advisories = qg.pip_audit_advisories(fixture("pip-audit-requests-2.19.0.json"), lookup)
    # pip-audit lists each of the five advisories twice; each is reported, and looked up, once.
    assert len(looked_up) == 5
    assert sorted((a.id, a.severity, a.fixed_in) for a in advisories) == [
        ("GHSA-9hjg-9r4m-mvj7", "moderate", "2.32.4"),
        ("GHSA-9wx4-h78v-vm56", "moderate", "2.32.0"),
        ("GHSA-gc5v-m9x4-r6x2", "moderate", "2.33.0"),
        ("GHSA-j8r2-6x86-q33q", "moderate", "2.31.0"),
        ("GHSA-x84v-xcm2-53pg", "high", "2.20.0"),
    ]


def test_a_fixable_high_advisory_blocks_and_moderates_dont() -> None:
    advisories = qg.pip_audit_advisories(fixture("pip-audit-requests-2.19.0.json"), osv_fixtures)
    assert [a.text() for a in qg.blocking(advisories, AUDIT)] == [
        "requests 2.19.0: GHSA-x84v-xcm2-53pg (high, fixed in 2.20.0)"
    ]


def test_a_high_advisory_with_no_fix_doesnt_block() -> None:
    advisory = qg.Advisory("p", "1.0", "GHSA-x", "critical", None)
    assert qg.blocking([advisory], AUDIT) == []


def test_an_advisory_with_no_known_severity_blocks() -> None:
    report = fixture("pip-audit-requests-2.19.0.json")
    advisories = qg.pip_audit_advisories(report, lambda _: None)
    assert {a.severity for a in advisories} == {"unknown"}
    assert len(qg.blocking(advisories, AUDIT)) == 5


def osv_records(advisory_id: str) -> dict[str, object] | None:
    """The OSV records captured on 2026-11-17 and 18, as OSV would answer, or None for a 404."""
    path = FIXTURES / f"osv-{advisory_id}.json"
    if not path.exists():
        return None
    record: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    return record


WEBSITE = "npm-audit-website-2026-11-18.json"
"""website's lock on 2026-11-18: picomatch's high advisory has no patched version, and npm marks it
fixable by downgrading astro from 7.4.7 to 5.3.0 (#330)."""


def test_npms_downgrade_of_a_dependent_isnt_a_fix() -> None:
    """Spec: quality-gates, "npm offers a downgrade of a dependent as the fix" (#330)."""
    advisories = qg.npm_audit_advisories(fixture(WEBSITE), osv_records)
    picomatch = next(a for a in advisories if a.package == "picomatch")
    assert (picomatch.id, picomatch.severity, picomatch.fixed_in) == (
        "GHSA-fc5q-39xc-vjpf",
        "high",
        None,
    )
    assert qg.blocking(advisories, AUDIT) == []


def test_each_root_advisory_is_listed_once_with_osvs_fixed_version() -> None:
    advisories = qg.npm_audit_advisories(fixture(WEBSITE), osv_records)
    # npm lists 30 vulnerable packages; four advisories are their roots.
    assert sorted((a.package, a.id, a.severity, a.fixed_in) for a in advisories) == [
        ("glob", "GHSA-3g3m-2fjr-6pw4", "moderate", "14.0.2"),
        ("minimatch", "GHSA-g3hv-75wg-m249", "moderate", "11.0.1"),
        ("picomatch", "GHSA-fc5q-39xc-vjpf", "high", None),
        ("postcss-selector-parser", "GHSA-rj75-hqrm-r3gf", "moderate", "6.1.5"),
    ]


def test_an_advisory_its_own_package_fixes_blocks() -> None:
    advisories = qg.npm_audit_advisories(fixture("npm-audit-lodash-minimist.json"), osv_records)
    failing = qg.blocking(advisories, AUDIT)
    assert {a.package for a in failing} == {"lodash", "minimist"}
    assert all(a.fixed_in is not None for a in failing)


def test_an_advisory_osv_doesnt_know_has_no_known_fix() -> None:
    advisories = qg.npm_audit_advisories(fixture(WEBSITE), lambda _: None)
    assert {a.fixed_in for a in advisories} == {None}
    assert qg.blocking(advisories, AUDIT) == []


def with_picomatch_fix(fix: object) -> dict[str, object]:
    """website's real report, with npm's fix for picomatch set to `fix`."""
    report = fixture(WEBSITE)
    vulnerabilities = report["vulnerabilities"]
    assert isinstance(vulnerabilities, dict)
    vulnerabilities["picomatch"] = {**vulnerabilities["picomatch"], "fixAvailable": fix}
    return report


def test_without_an_osv_record_npms_fix_counts_when_it_names_the_package_itself() -> None:
    """Spec: quality-gates, "OSV has no record, and npm's fix names the vulnerable package" (owner,
    2026-11-18, #331's review)."""
    fix = {"name": "picomatch", "version": "4.0.8", "isSemVerMajor": False}
    advisories = qg.npm_audit_advisories(with_picomatch_fix(fix), lambda _: None)
    picomatch = next(a for a in advisories if a.package == "picomatch")
    assert picomatch.fixed_in == "4.0.8"
    assert qg.blocking(advisories, AUDIT) == [picomatch]


def test_without_an_osv_record_npms_fix_doesnt_count_when_it_names_a_dependent() -> None:
    # The real report: npm's fix for picomatch names astro@5.3.0, a downgrade of a dependent.
    advisories = qg.npm_audit_advisories(fixture(WEBSITE), lambda _: None)
    assert next(a for a in advisories if a.package == "picomatch").fixed_in is None
    assert qg.blocking(advisories, AUDIT) == []


def test_an_osv_record_wins_over_npms_fix() -> None:
    fix = {"name": "picomatch", "version": "4.0.8", "isSemVerMajor": False}
    advisories = qg.npm_audit_advisories(with_picomatch_fix(fix), osv_records)
    assert next(a for a in advisories if a.package == "picomatch").fixed_in is None


def test_osvs_fixed_version_is_the_lowest_for_that_package() -> None:
    record = osv_records("GHSA-rj75-hqrm-r3gf")
    assert record is not None
    assert qg.osv_fixed_version(record, "postcss-selector-parser") == "6.1.5"
    assert qg.osv_fixed_version(record, "some-other-package") is None


def test_an_unreachable_osv_fails_the_npm_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> object:
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    with pytest.raises(qg.GateError, match="couldn't read GHSA-"):
        qg.npm_audit_advisories(fixture(WEBSITE), qg.osv_record)


def test_an_npm_error_is_an_error() -> None:
    with pytest.raises(qg.GateError, match="npm audit failed"):
        qg.npm_audit_advisories({"error": {"code": "ENOLOCK"}}, osv_records)


def test_only_a_changed_lock_file_is_audited(repo: Path) -> None:
    base = commit(repo, {"uv.lock": "version = 1\n"})
    assert qg.changed_lock_files(repo, base, ["uv.lock"]) == []
    (repo / "uv.lock").write_text("version = 2\n", encoding="utf-8")
    assert qg.changed_lock_files(repo, base, ["uv.lock"]) == ["uv.lock"]


def test_the_audit_command_skips_without_a_changed_lock_file(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = commit(repo, {"uv.lock": "version = 1\n"})
    assert (
        qg.main(["audit", "--base", base, "--uv", "false", "--pip-audit", "false"], root=repo) == 0
    )
    assert "no lock file changed" in capsys.readouterr().out


def test_a_failing_audit_tool_is_an_error_not_a_pass(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = commit(repo, {"uv.lock": "version = 1\n"})
    (repo / "uv.lock").write_text("version = 2\n", encoding="utf-8")
    assert (
        qg.main(["audit", "--base", base, "--uv", "false", "--pip-audit", "false"], root=repo) == 2
    )
    assert "uv export failed" in capsys.readouterr().err


def test_an_unreachable_osv_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> object:
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    with pytest.raises(qg.GateError, match="couldn't read GHSA-x from OSV"):
        qg.osv_severity("GHSA-x")


# --- Weekly report -------------------------------------------------------------------------------


class FakeIssues:
    """One repository's issues, in memory."""

    def __init__(self, open_number: int | None = None) -> None:
        self.open_number = open_number
        self.calls: list[tuple[str, ...]] = []

    def find_open(self) -> int | None:
        return self.open_number

    def create(self, body: str) -> str:
        self.calls.append(("create", body))
        self.open_number = 7
        return "https://github.com/troupe-run/infrastructure/issues/7"

    def edit(self, number: int, body: str) -> None:
        self.calls.append(("edit", str(number), body))

    def close(self, number: int, comment: str) -> None:
        self.calls.append(("close", str(number), comment))
        self.open_number = None


HIGH = qg.Advisory("requests", "2.19.0", "GHSA-x84v-xcm2-53pg", "high", "2.20.0")
MODERATE = qg.Advisory("glob", "9.0.0 - 14.0.1", "npm audit", "moderate", None)


def test_advisories_with_no_open_issue_open_one_and_return_its_url() -> None:
    issues = FakeIssues()
    url = qg.upkeep([HIGH, MODERATE], AUDIT, issues, ["uv.lock"])
    assert url == "https://github.com/troupe-run/infrastructure/issues/7"
    assert [call[0] for call in issues.calls] == ["create"]
    body = issues.calls[0][1]
    assert "| requests | 2.19.0 | GHSA-x84v-xcm2-53pg | high | 2.20.0 | yes |" in body
    assert "| glob | 9.0.0 - 14.0.1 | npm audit | moderate | no fix yet |  |" in body


def test_advisories_with_an_open_issue_update_it_and_open_no_other() -> None:
    issues = FakeIssues(open_number=3)
    assert qg.upkeep([MODERATE], AUDIT, issues, ["uv.lock"]) is None
    assert [call[:2] for call in issues.calls] == [("edit", "3")]


def test_no_advisories_close_the_open_issue() -> None:
    issues = FakeIssues(open_number=3)
    assert qg.upkeep([], AUDIT, issues, ["uv.lock"]) is None
    assert issues.calls == [("close", "3", "The weekly dependency audit found no advisories.")]


def test_no_advisories_and_no_issue_do_nothing() -> None:
    issues = FakeIssues()
    assert qg.upkeep([], AUDIT, issues, ["uv.lock"]) is None
    assert issues.calls == []


FAKE_GH = """\
import json, pathlib, sys
log = pathlib.Path(sys.argv[0]).with_suffix(".log")
args = sys.argv[1:]
with log.open("a") as out:
    stdin = "" if sys.stdin.isatty() else sys.stdin.read()
    out.write(json.dumps({"args": args, "stdin": stdin}) + "\\n")
if args[:2] == ["issue", "list"]:
    print(json.dumps([
        {"number": 12, "title": "Dependency advisories in website"},
        {"number": 9, "title": "Dependency advisories"},
    ]))
elif args[:2] == ["issue", "create"]:
    print("https://github.com/troupe-run/infrastructure/issues/40")
"""


def fake_gh(tmp_path: Path) -> tuple[str, Path]:
    script = tmp_path / "gh.py"
    script.write_text(FAKE_GH, encoding="utf-8")
    wrapper = tmp_path / "gh"
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
    wrapper.chmod(0o755)
    return str(wrapper), script.with_suffix(".log")


@pytest.mark.skipif(sys.platform == "win32", reason="the fake gh is a shell script")
def test_gh_issues_finds_its_issue_by_exact_title_and_label(tmp_path: Path) -> None:
    gh, log = fake_gh(tmp_path)
    issues = qg.GhIssues(gh, "troupe-run/infrastructure")
    assert issues.find_open() == 9
    issues.edit(9, "the body")
    issues.close(9, "clear")
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert calls[0]["args"][:7] == [
        "issue", "list", "--state", "open", "--label", "dependencies", "--search",
    ]  # fmt: skip
    assert calls[0]["args"][-2:] == ["-R", "troupe-run/infrastructure"]
    assert calls[1]["args"] == [
        "issue", "edit", "9", "--body-file", "-", "-R", "troupe-run/infrastructure",
    ]  # fmt: skip
    assert calls[1]["stdin"] == "the body"
    assert calls[2]["args"][:4] == ["issue", "close", "9", "--comment"]


@pytest.mark.skipif(sys.platform == "win32", reason="the fake gh is a shell script")
def test_gh_issues_creates_with_title_label_and_body(tmp_path: Path) -> None:
    gh, log = fake_gh(tmp_path)
    url = qg.GhIssues(gh, "troupe-run/infrastructure").create("the body")
    assert url == "https://github.com/troupe-run/infrastructure/issues/40"
    call = json.loads(log.read_text().splitlines()[0])
    assert call["args"][:6] == [
        "issue", "create", "--title", "Dependency advisories", "--label", "dependencies",
    ]  # fmt: skip
    assert call["stdin"] == "the body"


def test_a_failing_gh_is_an_error() -> None:
    with pytest.raises(qg.GateError, match="gh issue list failed"):
        qg.GhIssues("false", "troupe-run/infrastructure").find_open()
