"""A pull request's changed code is mutation tested, and only survivors on changed lines are
reported, as a report that never blocks (spec: mutation-testing; lint-mutation design D9)."""

import json
from pathlib import Path

import pytest

import mutation_pr as pr
import mutation_report as mr
import mutation_settings as ms

pytestmark = pytest.mark.mutation

SETTINGS = ms.load_settings(pr.SETTINGS.read_text(encoding="utf-8"))

DIFF = """\
diff --git a/scripts/mutation_settings.py b/scripts/mutation_settings.py
--- a/scripts/mutation_settings.py
+++ b/scripts/mutation_settings.py
@@ -80,0 +81,2 @@ def closed(
+    if not keys:
+        raise SettingsError("no keys")
@@ -100 +102 @@ def number(
-    return float(value)
+    return float(value) + 0
diff --git a/old.py b/old.py
deleted file mode 100644
--- a/old.py
+++ /dev/null
@@ -1,2 +0,0 @@
-a = 1
-b = 2
"""


def test_the_diff_gives_each_files_added_and_changed_lines() -> None:
    assert pr.changed_lines(DIFF) == {"scripts/mutation_settings.py": {81, 82, 102}}


SOURCE = """\
import os

CONSTANT = 1


def top(a):
    return a + 1


class Store:
    @property
    def size(self):
        return 2

    def other(self):
        return 3
"""


def test_changed_lines_name_the_functions_and_methods_they_fall_in() -> None:
    assert pr.mutmut_functions(SOURCE, {7}) == {"x_top"}
    assert pr.mutmut_functions(SOURCE, {11}) == {"xǁStoreǁsize"}  # the decorator's line
    assert (
        pr.mutmut_functions(SOURCE, {3}) == set()
    )  # module level: mutmut 3 mutates functions only
    assert pr.mutmut_functions(SOURCE, {7, 16}) == {"x_top", "xǁStoreǁother"}


def test_infrastructures_changed_functions_become_mutmut_globs_but_tests_dont() -> None:
    changed = {"scripts/calc.py": {7}, "scripts/tests/test_calc.py": {3}, "README.md": {1}}
    targets = pr.plan(SETTINGS.repositories["infrastructure"], changed, lambda path: SOURCE)
    assert targets == [pr.Target("scripts", ("calc.x_top__mutmut_*",), {"scripts/calc.py": [7]})]


def test_a_troupe_package_names_its_modules_from_its_src() -> None:
    changed = {"packages/troupe-vcs-git/src/troupe_vcs_git/repo.py": {7}}
    targets = pr.plan(SETTINGS.repositories["troupe"], changed, lambda path: SOURCE)
    assert [(t.unit, t.globs) for t in targets] == [
        ("troupe-vcs-git", ("troupe_vcs_git.repo.x_top__mutmut_*",))
    ]


def test_websites_changed_lines_become_stryker_ranges() -> None:
    changed = {"src/lib/site-path.ts": {3, 4, 5, 9}, "src/components/Hero.astro": {2}}
    targets = pr.plan(SETTINGS.repositories["website"], changed, lambda path: "")
    assert targets == [
        pr.Target(
            "stryker",
            ("src/lib/site-path.ts:3-5", "src/lib/site-path.ts:9-9"),
            {"src/lib/site-path.ts": [3, 4, 5, 9]},
        )
    ]


def test_a_pull_request_changing_no_target_plans_nothing() -> None:
    assert (
        pr.plan(SETTINGS.repositories["infrastructure"], {"docs/x.md": {1}}, lambda path: "") == []
    )


def survivor(path: str, line: int) -> mr.Survivor:
    return mr.Survivor(f"m.x_f__mutmut_{line}", path, line, "-a\n+b")


def test_only_survivors_on_changed_lines_are_reported() -> None:
    module = mr.Module(
        5, 3, 0, 0, 0, 0, True, (survivor("a.py", 7), survivor("a.py", 8), survivor("b.py", 7))
    )
    kept = pr.on_changed_lines({"m": module}, {"a.py": [7]})
    assert [(s.path, s.line) for s in kept] == [("a.py", 7)]


def report_fields(**overrides: object) -> dict[str, object]:
    module = mr.Module(5, 1, 0, 0, 0, 0, True, (survivor("a.py", 7),))
    report = mr.Report("infrastructure", "a" * 40, None, {"m": module})
    target = pr.Target("scripts", ("m.x_f__mutmut_*",), {"a.py": [7]})
    fields = pr.pr_report(
        "infrastructure", [target], report, {"plan": 0.1, "mutation": 61.0, "total": 62.0}
    )
    fields.update(overrides)
    return fields


def test_the_comment_lists_the_survivors_says_it_doesnt_block_and_gives_the_runtime() -> None:
    text = pr.comment(pr.load_pr_report(json.dumps(report_fields())))
    assert text.startswith(pr.MARKER + "\n")
    assert "6 mutants on changed code: 5 caught, **1 surviving on changed lines**." in text
    assert "- `a.py:7` `m.x_f__mutmut_7`: `-a / +b`" in text
    assert "doesn't block the merge" in text
    assert "Time: plan 0s, mutation 61s, total 62s" in text


def test_a_pull_request_with_nothing_to_mutate_says_so() -> None:
    fields = pr.pr_report("infrastructure", [], None, {"plan": 0.1, "total": 0.1})
    text = pr.comment(pr.load_pr_report(json.dumps(fields)))
    assert "nothing was mutated" in text


def test_a_run_stopped_by_its_budget_says_so() -> None:
    text = pr.comment(pr.load_pr_report(json.dumps(report_fields(finished=False))))
    assert "stopped at its budget" in text


@pytest.mark.parametrize(
    ("overrides", "named"),
    [
        ({"surprise": 1}, "surprise"),
        ({"version": 2}, "version"),
        ({"nothing": "no"}, "nothing"),
        ({"mutants": -1}, "mutants"),
        ({"timings": {"plan": "fast"}}, "timings"),
        ({"survivors": [{"name": "x"}]}, "survivors"),
    ],
)
def test_a_malformed_pull_request_report_is_refused_naming_the_field(
    overrides: dict[str, object], named: str
) -> None:
    with pytest.raises((ms.SettingsError, mr.ReportError), match=named):
        pr.load_pr_report(json.dumps(report_fields(**overrides)))


def test_the_comment_command_prints_the_comment(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report_fields()), encoding="utf-8")
    assert pr.main(["comment", str(path)]) == 0
    assert capsys.readouterr().out.startswith(pr.MARKER)


def test_a_repository_the_settings_dont_list_fails_naming_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        pr.main(
            ["run", "a", "b", str(tmp_path / "r.json")], {"GITHUB_REPOSITORY": "troupe-run/.github"}
        )
        == 2
    )
    assert "'.github'" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("path", "glob", "matches"),
    [
        ("src/index.ts", "src/**/*.ts", True),  # **/ is zero directories too, as Stryker reads it
        ("src/lib/site-path.ts", "src/**/*.ts", True),
        ("src/lib/deep/a.ts", "src/**/*.ts", True),
        ("scripts/check.mjs", "scripts/**/*.mjs", True),
        ("src/lib/a.tsx", "src/**/*.ts", False),
        ("tests/unit/a.ts", "src/**/*.ts", False),
        ("src/lib/a.ts", "src/*.ts", False),  # * stays within one directory
    ],
)
def test_globs_match_as_stryker_reads_them(path: str, glob: str, matches: bool) -> None:
    assert pr.glob_match(path, glob) is matches


def test_a_change_to_a_file_directly_under_a_globbed_directory_is_mutated() -> None:
    changed = {"scripts/check.mjs": {4}, "src/route-middleware.ts": {2}}
    [target] = pr.plan(SETTINGS.repositories["website"], changed, lambda path: "")
    assert target.globs == ("scripts/check.mjs:4-4", "src/route-middleware.ts:2-2")


def test_a_backtick_in_a_reports_strings_cant_end_the_code_span() -> None:
    fields = report_fields(
        survivors=[
            {
                "name": "m`@owner`",
                "path": "a`[x](https://example.invalid)`.py",
                "line": 7,
                "change": "-a\n+b`",
                "commit": None,
                "new": False,
            }
        ]
    )
    text = pr.comment(pr.load_pr_report(json.dumps(fields)))
    line = next(line for line in text.splitlines() if line.startswith("- `a"))
    assert line.count("`") == 6, line


# The run, over a scratch repository with mutation_run faked (lint-mutation 6b)


def scratch_repo(tmp_path: Path) -> tuple[Path, str, str]:
    from conftest import git

    repo = tmp_path / "repo"
    (repo / "scripts" / "tests").mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    (repo / "scripts" / "calc.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8"
    )
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base", "--author=Test <test@example.invalid>")
    base = git(repo, "rev-parse", "HEAD").stdout.strip()
    return repo, base, base


def commit_change(repo: Path, path: str, text: str) -> str:
    from conftest import git

    (repo / path).write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "change", "--author=Test <test@example.invalid>")
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def test_a_run_mutates_the_changed_functions_and_writes_the_report_and_summary(
    tmp_path: Path,
) -> None:
    repo, base, _ = scratch_repo(tmp_path)
    head = commit_change(repo, "scripts/calc.py", "def add(a, b):\n    return a + b + 0\n")
    commands: list[list[str]] = []

    def mutate(command: list[str]) -> int:
        commands.append(command)
        survivor = mr.Survivor("calc.x_add__mutmut_1", "scripts/calc.py", 2, "-a\n+b")
        modules = {"calc": mr.Module(3, 1, 0, 0, 0, 0, True, (survivor,))}
        # As mutation_run.py does, it makes the report's directory.
        target = Path(command[4])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(mr.dump_report(mr.Report("infrastructure", "a" * 40, None, modules)))
        return 0

    out = tmp_path / "out" / "pr-report.json"
    summary = tmp_path / "summary.md"
    env = {"GITHUB_REPOSITORY": "troupe-run/infrastructure", "GITHUB_STEP_SUMMARY": str(summary)}
    assert pr.main(["run", base, head, str(out)], env, repo, mutate) == 0
    [command] = commands
    assert command[1:4] == [str(repo / "scripts" / "mutation_run.py"), "infrastructure", str(repo)]
    assert command[4] == str(out.with_suffix(".mutants.json"))
    assert command[5:] == ["--only", json.dumps({"scripts": ["calc.x_add__mutmut_*"]})]
    fields = json.loads(out.read_text(encoding="utf-8"))
    assert {k: fields[k] for k in ("repository", "nothing", "finished", "mutants", "caught")} == {
        "repository": "infrastructure",
        "nothing": False,
        "finished": True,
        "mutants": 4,
        "caught": 3,
    }
    assert [s["line"] for s in fields["survivors"]] == [2]
    assert set(fields["timings"]) == {"plan", "mutation", "total"}
    assert summary.read_text(encoding="utf-8") == pr.comment(
        pr.load_pr_report(out.read_text(encoding="utf-8"))
    )


def test_a_run_that_changed_no_target_mutates_nothing(tmp_path: Path) -> None:
    repo, base, _ = scratch_repo(tmp_path)
    head = commit_change(repo, "README.md", "y\n")
    called: list[list[str]] = []

    def mutate(command: list[str]) -> int:
        called.append(command)
        return 0

    out = tmp_path / "pr-report.json"
    env = {"GITHUB_REPOSITORY": "troupe-run/infrastructure"}
    assert pr.main(["run", base, head, str(out)], env, repo, mutate) == 0
    fields = json.loads(out.read_text(encoding="utf-8"))
    assert (fields["nothing"], fields["mutants"], set(fields["timings"])) == (
        True,
        0,
        {"plan", "total"},
    )
    assert called == []


def test_a_failed_mutation_run_fails_the_report_naming_its_exit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, base, _ = scratch_repo(tmp_path)
    head = commit_change(repo, "scripts/calc.py", "def add(a, b):\n    return b + a\n")
    out = tmp_path / "pr-report.json"
    env = {"GITHUB_REPOSITORY": "troupe-run/infrastructure"}
    assert pr.main(["run", base, head, str(out)], env, repo, lambda c: 3) == 2
    assert capsys.readouterr().err == "mutation_pr: mutation_run.py failed (exit 3)\n"
    assert not out.exists()


def test_an_unknown_base_fails_naming_the_range(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, _, head = scratch_repo(tmp_path)
    env = {"GITHUB_REPOSITORY": "troupe-run/infrastructure"}
    assert pr.main(["run", "f" * 40, head, str(tmp_path / "r.json")], env, repo, lambda c: 0) == 2
    assert f"mutation_pr: git diff {'f' * 40}...{head} failed" in capsys.readouterr().err


# The comment's text


def test_the_comment_in_full() -> None:
    fields = report_fields()
    assert (
        pr.comment(pr.load_pr_report(json.dumps(fields)))
        == "\n".join(
            [
                pr.MARKER,
                "### Mutation testing of this pull request's changes",
                "",
                "6 mutants on changed code: 5 caught, **1 surviving on changed lines**.",
                "",
                "No test fails when these changed lines are changed:",
                "",
                "- `a.py:7` `m.x_f__mutmut_7`: `-a / +b`",
                "",
                "Add a test that fails for each, or exempt a line with the tool's own comment and "
                "a reason (`# pragma: no mutate`, "
                "`// Stryker disable next-line <mutator>: <reason>`).",
                "",
                "This is a report: it doesn't block the merge (lint-mutation design D9).",
                "",
                "Time: plan 0s, mutation 61s, total 62s",
            ]
        )
        + "\n"
    )


def test_a_comment_with_nothing_mutated_says_only_that() -> None:
    fields = pr.pr_report("infrastructure", [], None, {"total": 1.0})
    text = pr.comment(pr.load_pr_report(json.dumps(fields)))
    assert "No file this repository mutation tests changed, so nothing was mutated.\n" in text
    assert "No test fails" not in text
    assert "mutants on changed code" not in text


@pytest.mark.parametrize(
    ("count", "more"), [(30, None), (31, "- and 1 more, in the run's summary")]
)
def test_the_comment_lists_thirty_survivors_then_counts_the_rest(
    count: int, more: str | None
) -> None:
    survivors = [vars(survivor("a.py", n + 1)) for n in range(count)]
    text = pr.comment(pr.load_pr_report(json.dumps(report_fields(survivors=survivors))))
    assert text.count("`m.x_f__mutmut_") == 30
    assert (more in text) if more else ("more, in the run's summary" not in text)


def test_a_report_that_isnt_one_load_pr_report_read_is_refused() -> None:
    with pytest.raises(ms.SettingsError, match="isn't one load_pr_report read"):
        pr.comment({**report_fields(), "timings": []})
    with pytest.raises(ms.SettingsError, match="a survivor in the report isn't an object"):
        pr.comment({**report_fields(), "survivors": ["x"]})


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ([], "the pull request report isn't an object"),
        ({**report_fields(), "caught": 1.5}, "the pull request report's caught is 1.5"),
        ({**report_fields(), "survivors": {}}, "the pull request report's survivors isn't a list"),
        (
            {**report_fields(), "timings": {"plan": True}},
            "the pull request report's timings aren't seconds by step",
        ),
        (
            {**report_fields(), "finished": 1},
            "the pull request report's finished isn't true or false",
        ),
    ],
)
def test_a_malformed_report_is_refused_with_its_message(fields: object, message: str) -> None:
    with pytest.raises(ms.SettingsError) as raised:
        pr.load_pr_report(json.dumps(fields))
    assert str(raised.value).startswith(message)


# Globs and diffs at the edges


@pytest.mark.parametrize(
    ("path", "glob", "matches"),
    [
        ("src/a.ts", "src/?.ts", True),
        ("src/ab.ts", "src/?.ts", False),
        ("src/a/b.ts", "src/?/b.ts", True),
        ("src/x/y/z", "src/**", True),
        ("src/axts", "src/a.ts", False),  # a dot is a dot
        ("a/b", "a*b", False),  # * never crosses /
    ],
)
def test_glob_edges(path: str, glob: str, matches: bool) -> None:
    assert pr.glob_match(path, glob) is matches


def test_a_hunk_before_any_file_header_is_ignored_and_a_count_of_zero_adds_nothing() -> None:
    diff = "@@ -1 +1 @@\n+++ b/a.py\n@@ -3 +3,0 @@\n@@ -5 +5 @@\n"
    assert pr.changed_lines(diff) == {"a.py": {5}}


def test_a_changed_test_file_or_non_python_file_is_never_mutated() -> None:
    unit = ms.Unit("scripts", "scripts", "scripts/tests")
    repository = ms.Repository("infrastructure", "mutmut", units=(unit,))
    changed = {"scripts/tests/test_a.py": {1}, "scripts/a.txt": {1}, "scripts/b.py": {2}}
    targets = pr.plan(repository, changed, lambda path: "def f():\n    return 1\n")
    assert targets == [pr.Target("scripts", ("b.x_f__mutmut_*",), {"scripts/b.py": [2]})]


def test_a_timing_for_an_unknown_step_is_refused_so_no_key_reaches_the_comment() -> None:
    fields = report_fields(timings={"[x](https://example.invalid) @owner": 1.0})
    with pytest.raises(ms.SettingsError) as raised:
        pr.load_pr_report(json.dumps(fields))
    assert str(raised.value) == (
        "the pull request report's timings name '[x](https://example.invalid) @owner', "
        "not one of ['mutation', 'plan', 'total']"
    )
