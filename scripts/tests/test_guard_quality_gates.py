"""The quality gates' measures (spec: quality-gates; quality-gates design D2-D8).

Named test_guard_*: scripts/quality_gates.py is delivered with the guard and runs in troupe's check
on every OS, so the guard's legs run these tests on each OS and Python too.

Tool output is real: pip-audit, OSV, npm audit, coverage.py and Vitest reports were captured on
2026-11-17 (fixtures/quality-gates). lizard runs for real on scratch git repositories.
"""

# ruff: noqa: F811 (each test's `repo` parameter is the fixture imported below, not a redefinition)

import json
import re
import shutil
from pathlib import Path

import pytest
from quality_gates_support import (  # noqa: F401 (pytest's fixtures, imported to be found)
    CONFIG,
    FIXTURES,
    LIZARD,
    commit,
    fixture,
    git,
    no_inherited_git,
    repo,
)

import quality_gates as qg


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


# --- Size (#271) ----------------------------------------------------------------------------------

SIZE = """
[size]
block_above = 100
warn_above = 50
exclude = ["**/fixtures/**"]

[size.allow]
"docs/big.md" = 200
"""
"""Small limits, so the tests' files stay small; the rule is the same at 48 KiB."""

PLAIN = SIZE[: SIZE.index("[size.allow]")]
"""The same limits with no allowance."""


def size_config(extra: str = SIZE) -> qg.SizeConfig:
    size = qg.parse_config(CONFIG + extra).size
    assert size is not None
    return size


def test_size_is_optional_and_none_when_absent() -> None:
    """Optional until troupe and website declare it (gate-files design D7)."""
    assert qg.parse_config(CONFIG).size is None


def test_the_size_table_parses() -> None:
    assert size_config() == qg.SizeConfig(100, 50, ("**/fixtures/**",), {"docs/big.md": 200})


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ("[size]\nblock_above = 100\n", "`size.warn_above` is required"),
        ("[size]\nblock_above = 100\nwarn_above = 50\nblok = 1\n", "unknown key `size.blok`"),
        ('[size]\nblock_above = "48k"\nwarn_above = 50\n', "`size.block_above` must be a whole"),
        ("[size]\nblock_above = 0\nwarn_above = 0\n", "`size.block_above` must be a whole"),
        ("[size]\nblock_above = 100\nwarn_above = 1.5\n", "`size.warn_above` must be a whole"),
        ("[size]\nblock_above = 100\nwarn_above = 101\n", "must be at or below `size.block_above`"),
        ('[size]\nblock_above = 100\nwarn_above = 50\nexclude = "x"\n', "`size.exclude` must be"),
        ("[size]\nblock_above = 100\nwarn_above = 50\nallow = 3\n", "`size.allow` must be a table"),
        (
            '[size]\nblock_above = 100\nwarn_above = 50\n[size.allow]\n"a.py" = "big"\n',
            "`size.allow.a.py` must be a whole",
        ),
        (
            '[size]\nblock_above = 100\nwarn_above = 50\n[size.allow]\n"a.py" = 100\n',
            "a ceiling must be above `size.block_above` (100)",
        ),
    ],
)
def test_a_bad_size_table_names_the_key(table: str, message: str) -> None:
    with pytest.raises(qg.GateError, match=re.escape(message)):
        qg.parse_config(CONFIG + "\n" + table)


def size_problems(repo: Path, base: str, extra: str = SIZE) -> list[str]:
    return qg.size_result(repo, base, size_config(extra)).problems


def test_a_file_grown_past_the_limit_fails(repo: Path) -> None:
    base = commit(repo, {"a.py": "x" * 90})
    (repo / "a.py").write_text("x" * 104, encoding="utf-8")
    assert size_problems(repo, base, PLAIN) == [
        "a.py: grew from 90 to 104 bytes, above the limit of 100"
    ]


def test_a_new_file_past_the_limit_fails(repo: Path) -> None:
    base = commit(repo, {"a.py": "x"})
    (repo / "b.md").write_text("é" * 60, encoding="utf-8")  # 120 bytes, 60 characters
    assert size_problems(repo, base, PLAIN) == [
        "b.md: a new file of 120 bytes, above the limit of 100"
    ]


def test_a_file_already_past_the_limit_that_shrinks_passes(repo: Path) -> None:
    base = commit(repo, {"a.py": "x" * 150})
    (repo / "a.py").write_text("x" * 140, encoding="utf-8")
    result = qg.size_result(repo, base, size_config(PLAIN))
    assert result.problems == []
    assert result.notes == [
        "a.py is 140 bytes, above the warning at 50 (more than one Read for a review)"
    ]


def test_a_declared_file_within_its_ceiling_passes(repo: Path) -> None:
    base = commit(repo, {"docs/big.md": "x" * 150})
    (repo / "docs" / "big.md").write_text("x" * 190, encoding="utf-8")
    assert size_problems(repo, base) == []


def test_a_declared_file_past_its_ceiling_fails(repo: Path) -> None:
    base = commit(repo, {"docs/big.md": "x" * 150})
    (repo / "docs" / "big.md").write_text("x" * 201, encoding="utf-8")
    assert size_problems(repo, base) == [
        "docs/big.md: grew from 150 to 201 bytes, above its ceiling of 200 in `size.allow`"
    ]


def test_a_file_over_the_warning_is_noted_and_passes(repo: Path) -> None:
    base = commit(repo, {"a.py": "x"})
    (repo / "a.py").write_text("x" * 60, encoding="utf-8")
    result = qg.size_result(repo, base, size_config(PLAIN))
    assert result.problems == []
    assert result.notes == [
        "a.py is 60 bytes, above the warning at 50 (more than one Read for a review)"
    ]


def test_an_excluded_binary_or_delivered_file_isnt_measured(repo: Path) -> None:
    base = commit(repo, {"docs/big.md": "x" * 150})
    (repo / "tests" / "fixtures").mkdir(parents=True)
    (repo / "tests" / "fixtures" / "plan.txt").write_text("x" * 500, encoding="utf-8")
    (repo / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 500)
    (repo / "latin1.txt").write_bytes(b"\xe9" * 500)
    (repo / "scripts").mkdir()
    (repo / "scripts" / "guard.py").write_text("x" * 500, encoding="utf-8")
    (repo / ".github").mkdir()
    shutil.copy(FIXTURES / "troupe-delivery-list.json", repo / ".github" / "guard-delivery.json")
    result = qg.size_result(repo, base, size_config())
    assert result == qg.SizeResult([], [])


def test_an_allowance_for_a_file_that_now_fits_is_stale(repo: Path) -> None:
    base = commit(repo, {"docs/big.md": "x" * 150})
    (repo / "docs" / "big.md").write_text("x" * 30, encoding="utf-8")
    assert size_problems(repo, base) == [
        "docs/big.md is 30 bytes, within the limit of 100, so it needs no allowance. "
        "Fix: remove its entry from `size.allow`."
    ]


def test_an_allowance_for_a_missing_file_is_stale(repo: Path) -> None:
    base = commit(repo, {"a.py": "x"})
    assert size_problems(repo, base) == [
        "`size.allow` names docs/big.md, which doesn't exist. Fix: remove its entry."
    ]


def test_the_size_command_fails_and_says_how_to_fix(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "quality-gates.toml").write_text(
        CONFIG + SIZE.replace('"docs/big.md" = 200', ""), encoding="utf-8"
    )
    base = commit(repo, {"a.py": "x"})
    (repo / "a.py").write_text("x" * 101, encoding="utf-8")
    assert qg.main(["size", "--base", base], root=repo) == 1
    assert capsys.readouterr().out.splitlines() == [
        "size: FAIL a.py: grew from 1 to 101 bytes, above the limit of 100",
        "size: split the file so a review can read it in one or two goes, or declare it with "
        "a ceiling in [size.allow] (the limits are [size] in quality-gates.toml).",
    ]


def test_the_size_command_passes_and_says_so(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "quality-gates.toml").write_text(
        CONFIG + SIZE.replace('"docs/big.md" = 200', ""), encoding="utf-8"
    )
    base = commit(repo, {"a.py": "x"})
    assert qg.main(["size", "--base", base], root=repo) == 0
    assert capsys.readouterr().out.splitlines() == ["size: no added or grown file above 100 bytes"]


def test_without_a_size_table_the_command_says_so_and_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No base is needed: with nothing declared, nothing is measured."""
    (tmp_path / "quality-gates.toml").write_text(CONFIG, encoding="utf-8")
    assert qg.main(["size"], root=tmp_path) == 0
    assert capsys.readouterr().out.splitlines() == [
        "size: not declared in this repository (no [size] in quality-gates.toml)"
    ]


def test_crlf_line_endings_count_as_lf(repo: Path) -> None:
    """A Windows checkout of a repository with no eol attribute writes CRLF: the size is the same
    on every OS, and a file that didn't change doesn't grow."""
    base = commit(repo, {"a.py": "x\n" * 45})
    (repo / "a.py").write_bytes(b"x\r\n" * 45 + b"y\r\n" * 5)  # 100 bytes measured, 150 on disk
    assert size_problems(repo, base, PLAIN) == []
    (repo / "a.py").write_bytes(b"x\r\n" * 51)  # 102 measured
    assert size_problems(repo, base, PLAIN) == [
        "a.py: grew from 90 to 102 bytes, above the limit of 100"
    ]


def test_an_allowance_for_a_binary_file_is_refused(repo: Path) -> None:
    base = commit(repo, {"a.py": "x"})
    (repo / "docs").mkdir()
    (repo / "docs" / "big.md").write_bytes(b"\0" * 150)
    assert size_problems(repo, base) == [
        "`size.allow` names docs/big.md, which isn't measured, being binary. Fix: remove its entry."
    ]


def test_a_file_named_like_a_lizard_option_is_read_as_a_file(tmp_path: Path) -> None:
    """Passed bare, `--output_file=o.py` would send lizard's report to a file and hide every
    function, from this gate and from auto-merge alike (#359's review)."""
    (tmp_path / "--output_file=o.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text(
        "def f(x):\n    if x:\n        return 1\n    return 0\n", encoding="utf-8"
    )
    found = qg.lizard_functions(LIZARD, tmp_path, ["--output_file=o.py", "b.py"])
    assert [(f.path, f.name, f.complexity) for f in found] == [("b.py", "f", 2)]
