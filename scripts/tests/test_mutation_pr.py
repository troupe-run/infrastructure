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
