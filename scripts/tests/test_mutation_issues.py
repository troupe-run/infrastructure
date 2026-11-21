"""The weekly run keeps exactly one test-quality issue per module under its threshold or baseline
(spec: mutation-testing; lint-mutation design D5, D7, D8). GitHub is faked: each test records the
gh calls the script makes."""

import json
from pathlib import Path

import pytest

import mutation_issues as mi
import mutation_report as mr
import mutation_settings as ms

pytestmark = pytest.mark.mutation

SHA = "a" * 40
# The settings as they were with three repositories and both tools (#332 cut the real list to
# troupe), so every tool's code stays tested.
SETTINGS_THREE = Path(__file__).parent / "fixtures" / "mutation" / "settings-three.json"
SETTINGS = ms.load_settings(SETTINGS_THREE.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def three_repositories(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() reads the settings from mi.SETTINGS: give it the same three repositories."""
    monkeypatch.setattr(mi, "SETTINGS", SETTINGS_THREE)


GATES = (Path(mi.__file__).resolve().parent.parent / "quality-gates.toml").read_text(
    encoding="utf-8"
)
"""A whole, valid quality-gates.toml (#322's), which a repository's baselines are read from."""
RUN = "https://github.com/troupe-run/infrastructure/actions/runs/1"


def survivors(count: int, new: bool = False, commit: str | None = None) -> tuple[mr.Survivor, ...]:
    return tuple(
        mr.Survivor(f"m.f__mutmut_{n}", "src/m.py", n + 1, "-a\n+b", commit, new)
        for n in range(count)
    )


def module(killed: int, survived: int = 0, finished: bool = True, **extra: int) -> mr.Module:
    new = bool(extra.pop("new", 0))
    # Every survivor in a weekly report is attributed; only a failed blame leaves none (#377).
    commit = "b" * 40 if new else "a" * 40
    return mr.Module(
        killed=killed,
        survived=survived,
        no_tests=extra.get("no_tests", 0),
        timeout=0,
        crashed=0,
        skipped=0,
        finished=finished,
        survivors=survivors(survived, new, commit),
    )


def report(**modules: mr.Module) -> mr.Report:
    return mr.Report("troupe", SHA, None, modules)


def issue(
    name: str, score: float | None = 50.0, survived: int | None = 10, number: int = 7
) -> mi.Issue:
    return mi.Issue(
        number, f"https://github.com/troupe-run/troupe/issues/{number}", name, score, survived
    )


def plan(
    r: mr.Report, issues: tuple[mi.Issue, ...] = (), baselines: dict[str, ms.Baseline] | None = None
) -> mi.Plan:
    return mi.plan_repository(r, baselines or {}, issues, SETTINGS, RUN, "mutmut", {})


def kinds(p: mi.Plan) -> list[tuple[str, str]]:
    return [(action.kind, action.module) for action in p.actions]


# Each module under the threshold or its baseline has exactly one issue


def test_a_module_falling_under_the_threshold_gets_an_issue_listing_its_survivors() -> None:
    p = plan(report(**{"troupe.a": module(killed=10, survived=10)}))
    assert kinds(p) == [("open", "troupe.a")]
    opened = p.actions[0]
    assert opened.title == "Mutation score 50% in troupe.a (under 60%)"
    assert opened.body.startswith("<!-- mutation-testing: troupe:troupe.a -->\n")
    assert "`src/m.py:1` `m.f__mutmut_0`" in opened.body
    assert "under the threshold of **60%**" in opened.body


def test_a_module_staying_under_with_the_same_numbers_is_rewritten_without_a_comment() -> None:
    p = plan(report(**{"troupe.a": module(killed=10, survived=10)}), (issue("troupe.a", 50.0, 10),))
    assert kinds(p) == [("update", "troupe.a")]


def test_a_module_staying_under_with_new_numbers_gets_a_comment_too() -> None:
    p = plan(report(**{"troupe.a": module(killed=11, survived=9)}), (issue("troupe.a", 50.0, 10),))
    assert kinds(p) == [("update", "troupe.a"), ("comment", "troupe.a")]
    assert "55% with 9 surviving (was 50% with 10)" in p.actions[1].comment


def test_a_module_that_recovers_has_its_issue_commented_on_and_closed() -> None:
    p = plan(report(**{"troupe.a": module(killed=19, survived=1)}), (issue("troupe.a"),))
    assert kinds(p) == [("close", "troupe.a")]
    assert "95%" in p.actions[0].comment


def test_a_module_falling_again_after_its_issue_closed_gets_a_new_one() -> None:
    # Only open issues are listed, so a closed one is never found, and never reopened (design D7).
    p = plan(report(**{"troupe.a": module(killed=10, survived=10)}), ())
    assert kinds(p) == [("open", "troupe.a")]


def gh_listing(items: list[dict[str, object]]) -> mi.Gh:
    def gh(args: list[str]) -> mi.GhResult:
        return mi.GhResult(0, json.dumps([items]), "")

    return gh


def test_a_persons_issue_quoting_the_marker_isnt_the_runs_own() -> None:
    marker = mi.marker("troupe", "troupe.a")
    listed = mi.list_issues(
        gh_listing(
            [
                {
                    "number": 1,
                    "body": marker,
                    "user": {"login": "martin-at-hpsgd"},
                    "html_url": "u1",
                },
                {"number": 2, "body": marker, "user": {"login": mi.APP}, "html_url": "u2"},
            ]
        ),
        "troupe",
    )
    assert [found.number for found in listed] == [2]


def test_a_marker_for_another_repository_isnt_read_as_this_ones() -> None:
    marker = mi.marker("website", "src/lib/a.ts")
    found = gh_listing([{"number": 3, "body": marker, "user": {"login": mi.APP}, "html_url": "u"}])
    assert mi.list_issues(found, "troupe") == []


def test_the_state_line_is_read_back() -> None:
    text = (
        mi.marker("troupe", "troupe.a")
        + "\n<!-- mutation-testing-state: score=48.5 survived=12 -->\n"
    )
    read = mi.read_issue({"number": 4, "body": text, "html_url": "u"}, "troupe")
    assert read == mi.Issue(4, "u", "troupe.a", 48.5, 12)


# Judging


def test_a_small_module_isnt_judged_and_its_issue_is_left_alone() -> None:
    p = plan(report(**{"troupe.a": module(killed=2, survived=7)}), (issue("troupe.a"),))
    assert p.actions == []
    assert p.not_judged == ["troupe.a"]


def test_an_unfinished_module_isnt_judged() -> None:
    p = plan(report(**{"troupe.a": module(killed=5, survived=20, finished=False)}))
    assert p.actions == []
    assert p.not_judged == ["troupe.a"]


def test_untested_code_counts_against_a_module() -> None:
    p = plan(report(**{"troupe.a": module(killed=10, survived=4, no_tests=6)}))
    assert kinds(p) == [("open", "troupe.a")]
    assert "50%" in p.actions[0].title


# A module's baseline only moves up (design D7)


def baseline(score: float) -> ms.Baseline:
    return ms.Baseline(score, 100, "e" * 40)


def test_a_module_falling_below_its_baseline_above_the_threshold_gets_an_issue() -> None:
    # 70.5%: 141 of 200.
    r = report(**{"troupe.a": module(killed=141, survived=59)})
    p = plan(r, baselines={"troupe.a": baseline(72.0)})
    assert kinds(p) == [("open", "troupe.a")]
    assert p.actions[0].title == "Mutation score 70.5% in troupe.a (below its 72% baseline)"
    assert "baseline of **72%**" in p.actions[0].body
    assert p.raises == {}


def test_a_module_that_improves_has_its_raise_reported_and_no_issue() -> None:
    p = plan(
        report(**{"troupe.a": module(killed=75, survived=25)}),
        baselines={"troupe.a": baseline(72.0)},
    )
    assert p.actions == []
    assert p.raises == {"troupe.a": 75.0}


def test_a_module_with_no_baseline_over_the_threshold_reports_its_first_baseline() -> None:
    p = plan(report(**{"troupe.a": module(killed=16, survived=9)}))  # 64%
    assert p.actions == []
    assert p.raises == {"troupe.a": 64.0}


def test_a_low_baseline_still_holds_a_module_to_the_threshold() -> None:
    p = plan(
        report(**{"troupe.a": module(killed=40, survived=60)}),
        baselines={"troupe.a": baseline(40.0)},
    )
    assert kinds(p) == [("open", "troupe.a")]
    assert "under 60%" in p.actions[0].title


# A module's issue lists its surviving mutants


def test_a_module_with_45_survivors_lists_30_and_says_how_to_list_the_rest() -> None:
    p = plan(report(**{"troupe.a": module(killed=5, survived=45)}))
    text = p.actions[0].body
    assert text.count("m.f__mutmut_") == 30
    assert "and 15 more: `mutmut results`" in text


# A run opens a bounded number of new issues


def test_more_modules_under_than_the_cap_opens_the_cap_and_names_the_rest() -> None:
    modules = {f"troupe.m{n}": module(killed=10, survived=10) for n in range(8)}
    p = plan(report(**modules), (issue("troupe.m7"),))
    opened = [module for kind, module in kinds(p) if kind == "open"]
    assert len(opened) == SETTINGS.max_new_issues == 5
    assert ("update", "troupe.m7") in kinds(p)
    assert p.deferred == ["troupe.m5", "troupe.m6"]


# New survivors are attributed (design D8)


def test_new_survivors_come_first_with_their_pull_request() -> None:
    r = report(**{"troupe.a": module(killed=5, survived=5, new=1)})
    p = mi.plan_repository(r, {}, (), SETTINGS, RUN, "mutmut", {"b" * 40: 412})
    assert "### New since the last run" in p.actions[0].body
    assert "added in #412" in p.actions[0].body


def test_new_survivors_are_looked_up_with_the_read_token_and_no_pull_request_is_written(
    tmp_path: Path,
) -> None:
    r = mr.Report("troupe", SHA, None, {"troupe.a": module(killed=5, survived=5, new=1)})
    (tmp_path / "report-troupe.json").write_text(mr.dump_report(r), encoding="utf-8")
    for name in ("infrastructure", "website"):
        (tmp_path / f"skipped-{name}").touch()
    reads: list[list[str]] = []

    def read_gh(args: list[str]) -> mi.GhResult:
        reads.append(args)
        return mi.GhResult(
            0, json.dumps([{"number": 412, "merged_at": "2026-11-16T10:00:00Z"}]), ""
        )

    app = FakeGitHub()
    assert mi.main([str(tmp_path)], actions_env(tmp_path), app, read_gh) == 0
    assert reads == [["api", f"repos/troupe-run/troupe/commits/{'b' * 40}/pulls"]]
    [opened] = app.writes
    assert opened[1] == "repos/troupe-run/troupe/issues"
    assert any("added in #412" in arg for arg in opened)


# The whole run


class FakeGitHub:
    """Answers the reads the run makes and records every write."""

    def __init__(self) -> None:
        self.writes: list[list[str]] = []

    def __call__(self, args: list[str]) -> mi.GhResult:
        if "--paginate" in args:
            return mi.GhResult(0, "[[]]", "")
        if "-f" in args or "-X" in args:
            self.writes.append(args)
            return mi.GhResult(
                0, json.dumps({"html_url": "https://github.com/troupe-run/x/issues/9"}), ""
            )
        return mi.GhResult(0, "[]", "")


def write_reports(directory: Path, skip: str = "", bad: str = "") -> None:
    for name in ("troupe", "infrastructure", "website"):
        if name == skip:
            continue
        r = mr.Report(name, SHA, None, {f"{name}.a": module(killed=10, survived=10)})
        text = mr.dump_report(r)
        if name == bad:
            text = text.replace('"finished"', '"surprise": 1, "finished"')
        (directory / f"report-{name}.json").write_text(text, encoding="utf-8")


def actions_env(tmp_path: Path) -> dict[str, str]:
    return {"GITHUB_ACTIONS": "true", "GITHUB_OUTPUT": str(tmp_path / "out"), "GITHUB_RUN_ID": "1"}


def test_a_run_opens_the_issues_and_hands_their_urls_to_the_board_job(tmp_path: Path) -> None:
    write_reports(tmp_path)
    gh = FakeGitHub()
    assert mi.main([str(tmp_path)], actions_env(tmp_path), gh) == 0
    assert len(gh.writes) == 3
    assert all(f"labels[]={mi.LABEL}" in write for write in gh.writes)
    out = (tmp_path / "out").read_text(encoding="utf-8")
    assert out.startswith("issue-urls=[")
    assert len(json.loads(out.removeprefix("issue-urls="))) == 3


def test_a_run_reads_each_repositorys_state_record_into_its_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The file mutation_run.py writes beside the report, by the same name (#380's review)."""
    write_reports(tmp_path)
    (tmp_path / "state-troupe.json").write_text(json.dumps(STATE), encoding="utf-8")
    assert mi.main([str(tmp_path)], actions_env(tmp_path), FakeGitHub()) == 0
    assert "- `troupe`: 1805 results carried from run 41" in capsys.readouterr().out


@pytest.mark.parametrize("bad", ["{not json", '{"units": []}', '{"units": {"troupe": 1}}'])
def test_a_malformed_state_record_is_named_and_its_repository_left_untouched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], bad: str
) -> None:
    """Read before any issue is written: a bad record can't strand opened issues off the board."""
    write_reports(tmp_path)
    (tmp_path / "state-troupe.json").write_text(bad, encoding="utf-8")
    gh = FakeGitHub()
    assert mi.main([str(tmp_path)], actions_env(tmp_path), gh) == 1
    assert len(gh.writes) == 2
    assert "troupe: state-troupe.json is malformed" in capsys.readouterr().err
    assert (tmp_path / "out").read_text(encoding="utf-8").startswith("issue-urls=[")


def test_a_malformed_report_fails_the_run_after_the_others_are_handled(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_reports(tmp_path, bad="website")
    gh = FakeGitHub()
    assert mi.main([str(tmp_path)], actions_env(tmp_path), gh) == 1
    assert len(gh.writes) == 2
    assert "website: website's report" in capsys.readouterr().err


def test_a_missing_report_fails_the_run_naming_the_repository(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_reports(tmp_path, skip="troupe")
    assert mi.main([str(tmp_path)], actions_env(tmp_path), FakeGitHub()) == 1
    assert "troupe: no report" in capsys.readouterr().err


def test_a_repository_a_dispatch_skipped_isnt_a_failure(tmp_path: Path) -> None:
    write_reports(tmp_path, skip="troupe")
    (tmp_path / "skipped-troupe").touch()
    assert mi.main([str(tmp_path)], actions_env(tmp_path), FakeGitHub()) == 0


def test_a_malformed_mutation_table_fails_that_repository(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_reports(tmp_path)
    (tmp_path / "quality-gates-troupe.toml").write_text(
        GATES
        + '\n[mutation.baselines."troupe.a"]\nscore = "high"\nmutants = 1\njudged_at = "'
        + "e" * 40
        + '"\n',
        encoding="utf-8",
    )
    gh = FakeGitHub()
    assert mi.main([str(tmp_path)], actions_env(tmp_path), gh) == 1
    assert "troupe-run/troupe/quality-gates.toml" in capsys.readouterr().err
    assert len(gh.writes) == 2


@pytest.mark.parametrize("argv_extra", [["--dry-run"], []])
def test_a_dry_run_or_a_run_outside_actions_writes_nothing(
    tmp_path: Path, argv_extra: list[str]
) -> None:
    write_reports(tmp_path)
    gh = FakeGitHub()
    env = actions_env(tmp_path) if argv_extra else {"GITHUB_ACTIONS": "false"}
    assert mi.main([str(tmp_path), *argv_extra], env, gh) == 0
    assert gh.writes == []


def test_the_summary_names_scores_and_the_baselines_to_raise(tmp_path: Path) -> None:
    r = report(
        **{"troupe.a": module(killed=16, survived=9), "troupe.b": module(killed=10, survived=10)}
    )
    p = plan(r)
    text = mi.summary("troupe", r, p, SETTINGS, dry=True)
    assert "| `troupe.a` | 64% | 25 | yes |" in text
    assert "- would open `troupe.b`" in text
    assert '[mutation.baselines."troupe.a"]\nscore = 64\nmutants = 25' in text


def test_the_summary_names_every_crashed_mutant_and_what_it_ended() -> None:
    """For the owner to decide on exclusions from real data (#361)."""
    crashes = (
        mr.Crashed(
            "troupe.platform.processes.x__kill_group__mutmut_4",
            "packages/troupe/src/troupe/platform/processes.py",
            389,
            "-    os.killpg(pid, signal.SIGKILL)\n+    os.killpg(0, signal.SIGKILL)",
            -9,
        ),
        mr.Crashed("ArithmeticOperator#3", "src/lib/add.ts", 2, "-a + b\n+a - b", None),
    )
    m = mr.Module(10, 0, 0, 0, 2, 0, True, (), crashes)
    r = report(**{"troupe.platform.processes": m})
    text = mi.summary("troupe", r, plan(r), SETTINGS, dry=True)
    assert (
        "Crashed mutants: each ended only its own test process, and the tool recorded it and went "
        "on. Excluding any (`# pragma: no mutate`) is the owner's decision." in text
    )
    assert (
        "- `troupe.platform.processes.x__kill_group__mutmut_4` at "
        "`packages/troupe/src/troupe/platform/processes.py:389` (exit -9): "
        "`-    os.killpg(pid, signal.SIGKILL) / +    os.killpg(0, signal.SIGKILL)`" in text
    )
    assert (
        "- `ArithmeticOperator#3` at `src/lib/add.ts:2` (no exit code): `-a + b / +a - b`" in text
    )


def test_a_backtick_in_a_crashed_mutant_cant_end_its_code_span_in_the_summary() -> None:
    """A crash's strings come from a run of other code, as a survivor's do (#361's review)."""
    crash = mr.Crashed("m`@owner`", "a`b`.py", 3, "-x`\n+*y*", -9)
    r = report(**{"troupe.a": mr.Module(1, 0, 0, 0, 1, 0, True, (), (crash,))})
    [line] = [
        line
        for line in mi.summary("troupe", r, plan(r), SETTINGS, dry=True).splitlines()
        if line.startswith("- `m")
    ]
    assert line == "- `m'@owner'` at `a'b'.py:3` (exit -9): `-x' / +*y*`"


def test_the_summary_names_each_survivor_it_couldnt_attribute() -> None:
    """A failed blame leaves one survivor without a commit rather than losing the report, and the
    summary says so, never silently (#377)."""
    lost = mr.Survivor("m.f__mutmut_9", "src/m.py", 9, "-a\n+b", None, False)
    m = module(killed=10, survived=1)
    r = report(**{"troupe.a": mr.Module(10, 1, 0, 0, 0, 0, True, (lost,))})
    text = mi.summary("troupe", r, plan(r), SETTINGS, dry=True)
    assert (
        "Unattributed survivors: their `git blame` failed, so who last changed their line isn't "
        "known; the run's log says why." in text
    )
    assert "- `m.f__mutmut_9` at `src/m.py:9`" in text
    plain = report(**{"troupe.a": m})
    assert "Unattributed" not in mi.summary("troupe", plain, plan(plain), SETTINGS, dry=True)


STATE = {
    "version": 1,
    "repository": "troupe",
    "units": {
        "troupe": {
            "restored_from": "41",
            "filled_since": "2026-11-20",
            "carried": 1805,
            "tested": 3210,
            "discarded": ["src/troupe/cut.py.meta can't be read: its mutants are tested again"],
            "lost": False,
            "unfit": True,
            "refreshed": False,
            "saved": True,
            "non_python_changes": ["uv.lock"],
        },
        "troupe-vcs-git": {
            "restored_from": None,
            "filled_since": None,
            "carried": 0,
            "tested": 900,
            "discarded": ["no state kept yet: a first fill"],
            "lost": False,
            "unfit": False,
            "refreshed": False,
            "saved": True,
            "non_python_changes": [],
        },
    },
}


def test_the_summary_says_where_each_units_results_came_from() -> None:
    """Carried from the kept state or tested this run, what was discarded and why, and the
    non-Python changes mutmut keeps cached results despite (#378, design D4)."""
    r = report(**{"troupe.a": module(killed=10)})
    text = mi.summary("troupe", r, plan(r), SETTINGS, dry=True, state=STATE)
    assert (
        "Kept mutmut state: each run resumes from the last run's saved results and tests only "
        "what changed or is left." in text
    )
    assert (
        "- `troupe`: 1805 results carried from run 41, 3210 tested in this run (filled since "
        "2026-11-20)" in text
    )
    assert "  - src/troupe/cut.py.meta can't be read: its mutants are tested again" in text
    assert (
        "  - non-Python files changed since the last full run, cached results kept: `uv.lock`"
        in text
    )
    assert "- `troupe-vcs-git`: 900 tested in this run" in text
    assert "  - no state kept yet: a first fill" in text


def test_a_summary_with_no_state_record_has_no_section_for_it() -> None:
    r = report(**{"troupe.a": module(killed=10)})
    assert "Kept mutmut state" not in mi.summary("troupe", r, plan(r), SETTINGS, dry=True)


def test_a_summary_with_no_crashed_mutant_has_no_section_for_them() -> None:
    r = report(**{"troupe.a": module(killed=10)})
    assert "Crashed mutants" not in mi.summary("troupe", r, plan(r), SETTINGS, dry=True)


def test_a_commit_is_attributed_to_its_merged_pull_request_only() -> None:
    answers = {
        "b" * 40: [
            {"number": 5, "merged_at": None},
            {"number": 412, "merged_at": "2026-11-16T10:00:00Z"},
        ],
        "c" * 40: [],
    }

    def gh(args: list[str]) -> mi.GhResult:
        commit = args[1].split("/")[-2]
        return mi.GhResult(0, json.dumps(answers[commit]), "")

    assert mi.pulls_for(gh, "troupe", {"b" * 40, "c" * 40}) == {"b" * 40: 412}


def test_an_issue_says_mutmut_cant_see_code_tests_run_in_a_subprocess() -> None:
    p = plan(report(**{"troupe.a": module(killed=10, survived=4, no_tests=6)}))
    assert (
        "6 reached by no test in the test process (mutmut doesn't see code a test runs"
        in p.actions[0].body
    )


def test_the_apps_issues_are_listed_with_its_login_encoded_in_the_query() -> None:
    asked: list[list[str]] = []

    def gh(args: list[str]) -> mi.GhResult:
        asked.append(args)
        return mi.GhResult(0, "[[]]", "")

    mi.list_issues(gh, "troupe")
    [query] = [arg for arg in asked[0] if arg.startswith("repos/")]
    assert "creator=troupe-run-test-quality%5Bbot%5D&" in query
    assert "[" not in query


def test_a_backtick_in_a_survivor_cant_end_the_code_span_in_an_issue() -> None:
    survivor = mr.Survivor("m`@owner`", "a`b`.py", 3, "-x`\n+y")
    line = mi.survivor_line(survivor, {})
    assert line.count("`") == 6, line


def test_an_issue_opened_before_a_later_write_fails_still_goes_to_the_board(tmp_path: Path) -> None:
    modules = {
        "troupe.a": module(killed=10, survived=10),
        "troupe.b": module(killed=10, survived=10),
    }
    (tmp_path / "report-troupe.json").write_text(
        mr.dump_report(mr.Report("troupe", SHA, None, modules)), encoding="utf-8"
    )
    for name in ("infrastructure", "website"):
        (tmp_path / f"skipped-{name}").touch()

    class FailsSecondWrite(FakeGitHub):
        def __call__(self, args: list[str]) -> mi.GhResult:
            if ("-f" in args or "-X" in args) and len(self.writes) == 1:
                return mi.GhResult(1, "", "API rate limit exceeded")
            return super().__call__(args)

    assert mi.main([str(tmp_path)], actions_env(tmp_path), FailsSecondWrite()) == 1
    out = (tmp_path / "out").read_text(encoding="utf-8")
    assert json.loads(out.removeprefix("issue-urls=")) == [
        "https://github.com/troupe-run/x/issues/9"
    ]


# What each write sends GitHub (lint-mutation 6b: the pull request report's survivors)


def recorded_apply(plan_: mi.Plan) -> tuple[list[list[str]], list[str]]:
    calls: list[list[str]] = []

    def gh(args: list[str]) -> mi.GhResult:
        calls.append(args)
        return mi.GhResult(
            0, json.dumps({"html_url": "https://github.com/troupe-run/troupe/issues/9"}), ""
        )

    opened: list[str] = []
    mi.apply(gh, "troupe", plan_, opened)
    return calls, opened


def test_opening_an_issue_sends_its_title_body_label_and_type() -> None:
    plan_ = mi.Plan(actions=[mi.Action("open", "troupe.a", None, "T", "B")])
    calls, opened = recorded_apply(plan_)
    assert calls == [
        [
            "api",
            "repos/troupe-run/troupe/issues",
            "-f",
            "title=T",
            "-f",
            "body=B",
            "-f",
            "labels[]=test-quality",
            "-f",
            "type=Task",
        ]
    ]
    assert opened == ["https://github.com/troupe-run/troupe/issues/9"]


def test_updating_an_issue_patches_its_title_and_body() -> None:
    plan_ = mi.Plan(
        actions=[mi.Action("update", "troupe.a", issue("troupe.a", number=7), "T", "B")]
    )
    calls, opened = recorded_apply(plan_)
    assert calls == [
        ["api", "-X", "PATCH", "repos/troupe-run/troupe/issues/7", "-f", "title=T", "-f", "body=B"]
    ]
    assert opened == []


def test_commenting_on_an_issue_posts_the_comment() -> None:
    plan_ = mi.Plan(
        actions=[mi.Action("comment", "troupe.a", issue("troupe.a", number=7), comment="C")]
    )
    calls, _ = recorded_apply(plan_)
    assert calls == [["api", "repos/troupe-run/troupe/issues/7/comments", "-f", "body=C"]]


def test_closing_an_issue_comments_then_closes_it_as_completed() -> None:
    plan_ = mi.Plan(
        actions=[mi.Action("close", "troupe.a", issue("troupe.a", number=7), comment="C")]
    )
    calls, _ = recorded_apply(plan_)
    assert calls == [
        ["api", "repos/troupe-run/troupe/issues/7/comments", "-f", "body=C"],
        [
            "api",
            "-X",
            "PATCH",
            "repos/troupe-run/troupe/issues/7",
            "-f",
            "state=closed",
            "-f",
            "state_reason=completed",
        ],
    ]


@pytest.mark.parametrize("kind", ["update", "comment", "close"])
def test_an_action_on_an_existing_issue_without_one_writes_nothing(kind: str) -> None:
    calls, _ = recorded_apply(mi.Plan(actions=[mi.Action(kind, "troupe.a", None, "T", "B", "C")]))
    assert calls == []


def test_a_refused_write_names_the_command_and_githubs_reason() -> None:
    def gh(args: list[str]) -> mi.GhResult:
        return mi.GhResult(1, "", "  HTTP 403: Resource not accessible by integration \n")

    with pytest.raises(mi.GitHubError) as raised:
        mi.gh_json(gh, ["api", "repos/troupe-run/troupe/issues", "-f", "title=T"])
    assert str(raised.value) == (
        "gh api repos/troupe-run/troupe/issues -f failed: "
        "HTTP 403: Resource not accessible by integration"
    )


def test_an_empty_answer_reads_as_nothing() -> None:
    assert mi.gh_json(lambda args: mi.GhResult(0, "", ""), ["api", "x"]) is None


# Judging at the edges


def judged(killed: int, survived: int, baseline_score: float | None = None) -> mi.Judgement:
    base = None if baseline_score is None else baseline(baseline_score)
    return mi.judge("m", module(killed=killed, survived=survived), base, SETTINGS)


def test_a_score_exactly_at_the_threshold_isnt_under() -> None:
    j = judged(6, 4)  # 60%
    assert (j.score, j.counted, j.under_threshold, j.under) == (60.0, 10, False, False)


def test_a_score_exactly_at_its_baseline_hasnt_fallen_and_raises_nothing() -> None:
    j = judged(7, 3, baseline_score=70.0)
    assert (j.below_baseline, j.raise_to, j.baseline) == (False, None, 70.0)


def test_a_score_just_over_its_baseline_raises_it() -> None:
    assert judged(71, 29, baseline_score=70.0).raise_to == 71.0


def test_an_unjudged_module_raises_nothing_and_isnt_under() -> None:
    j = mi.judge("m", module(killed=1, survived=8), None, SETTINGS)
    assert (j.judged, j.under_threshold, j.below_baseline, j.raise_to, j.under) == (
        False,
        False,
        False,
        None,
        False,
    )


# Listing and reading the App's issues


def test_the_listing_asks_for_every_page_of_open_test_quality_issues() -> None:
    asked: list[list[str]] = []

    def gh(args: list[str]) -> mi.GhResult:
        asked.append(args)
        return mi.GhResult(0, "[[]]", "")

    mi.list_issues(gh, "troupe")
    assert asked == [
        [
            "api",
            "--paginate",
            "--slurp",
            "repos/troupe-run/troupe/issues?state=open&labels=test-quality"
            "&creator=troupe-run-test-quality%5Bbot%5D&per_page=100",
        ]
    ]


@pytest.mark.parametrize("answer", ["{}", "[{}]", '[["x"]]', '[[{"user": {"login": "someone"}}]]'])
def test_a_listing_of_another_shape_finds_no_issue(answer: str) -> None:
    assert mi.list_issues(lambda args: mi.GhResult(0, answer, ""), "troupe") == []


def test_an_issue_with_no_number_or_body_isnt_read() -> None:
    marker = mi.marker("troupe", "troupe.a")
    assert mi.read_issue({"body": marker}, "troupe") is None
    assert mi.read_issue({"number": 3}, "troupe") is None
    assert mi.read_issue({"number": 3, "body": "text\n" + marker}, "troupe") is None


def test_an_issue_without_html_url_falls_back_to_its_api_url() -> None:
    read = mi.read_issue(
        {"number": 3, "body": mi.marker("troupe", "a"), "url": "api-url"}, "troupe"
    )
    assert read == mi.Issue(3, "api-url", "a", None, None)


# The issue's text


def test_a_survivor_names_its_commit_when_no_pull_request_is_known() -> None:
    new = mr.Survivor("m.f__mutmut_1", "a.py", 4, "-a\n+b", "c" * 40, True)
    assert (
        mi.survivor_line(new, {}) == f"- `a.py:4` `m.f__mutmut_1`, added in {'c' * 12}: `-a / +b`"
    )
    old = mr.Survivor("m.f__mutmut_1", "a.py", 4, "-a\n+b", "c" * 40, False)
    assert mi.survivor_line(old, {"c" * 40: 5}) == "- `a.py:4` `m.f__mutmut_1`: `-a / +b`"


def test_was_shows_a_number_or_a_question_mark() -> None:
    assert (mi.was(None), mi.was(50.0), mi.was(12)) == ("?", "50", "12")


def issue_body(m: mr.Module, tool: str = "mutmut", baseline_score: float | None = None) -> str:
    j = mi.judge(
        "troupe.a", m, None if baseline_score is None else baseline(baseline_score), SETTINGS
    )
    return mi.body("troupe", j, m, SETTINGS, RUN, tool, {})


def test_the_body_says_what_was_measured_and_how_to_close_it() -> None:
    text = issue_body(module(killed=10, survived=5, no_tests=5))
    assert text.split("\n")[:3] == [
        mi.marker("troupe", "troupe.a"),
        "<!-- mutation-testing-state: score=50 survived=5 -->",
        "",
    ]
    assert (
        f"`troupe.a` scored **50%** in the weekly mutation run ([run]({RUN})): 10 caught of 20 "
        "(10 killed, 0 timed out, 0 crashed), 5 survived, 5 reached by no test in the test process"
    ) in text
    assert f"Settings: [scripts/mutation.json]({mi.SETTINGS_URL})." in text
    assert "\n### Surviving mutants\n\n- `src/m.py:1`" in text
    assert text.endswith(
        "A test that fails for a mutant kills it. Close this by raising the score: the weekly run "
        "closes it when the module is back at or over its threshold and baseline.\n"
    )


def test_a_module_with_every_mutant_reached_says_nothing_about_subprocesses() -> None:
    text = issue_body(module(killed=10, survived=10))
    assert "10 survived, 0 reached by no test." in text


def test_a_stryker_module_points_at_its_html_report_for_the_rest() -> None:
    text = issue_body(module(killed=5, survived=40), tool="stryker")
    assert "- and 10 more: the Stryker HTML report in the run's artifacts lists them all" in text
    assert "in the test process" not in issue_body(
        module(killed=5, survived=4, no_tests=6), tool="stryker"
    )


def test_new_survivors_leave_room_for_the_rest_within_thirty() -> None:
    m = module(killed=5, survived=3, new=1)
    old = tuple(mr.Survivor(f"m.g__mutmut_{n}", "src/m.py", 50 + n, "-a\n+b") for n in range(40))
    mixed = mr.Module(5, 43, 0, 0, 0, 0, True, m.survivors + old)
    text = issue_body(mixed)
    assert text.count("m.f__mutmut_") == 3
    assert text.count("m.g__mutmut_") == 27
    assert "- and 13 more:" in text


# The summary and the run's outputs


def test_the_summary_lays_out_the_table_the_actions_and_the_baselines() -> None:
    r = report(
        **{
            "troupe.a": module(killed=16, survived=9),
            "troupe.b": module(killed=10, survived=10),
            "troupe.c": module(killed=1, survived=1),
        }
    )
    p = mi.plan_repository(r, {}, (issue("troupe.b", number=4),), SETTINGS, RUN, "mutmut", {})
    p.deferred.append("troupe.z")
    text = mi.summary("troupe", r, p, SETTINGS, dry=False)
    assert text.split("\n")[:5] == [
        f"## troupe at {SHA[:12]}",
        "",
        "| Module | Score | Mutants | Judged |",
        "|---|---|---|---|",
        "| `troupe.a` | 64% | 25 | yes |",
    ]
    assert "| `troupe.c` | 50% | 2 | no |" in text
    assert "- update `troupe.b` (#4)" in text
    cap = SETTINGS.max_new_issues
    assert (
        f"- under, but past the cap of {cap} new issues: `troupe.z` (raised by a later run)" in text
    )
    # troupe.b has no baseline yet, so its first judged score is one to record too (design D7).
    raises = (
        "Baselines to raise in this repository's `quality-gates.toml`, by pull request:\n\n"
        "```toml\n"
        f'[mutation.baselines."troupe.a"]\nscore = 64\nmutants = 25\njudged_at = "{SHA}"\n\n'
        f'[mutation.baselines."troupe.b"]\nscore = 50\nmutants = 20\njudged_at = "{SHA}"\n\n```\n'
    )
    assert text.endswith(raises)


def test_a_run_writes_its_summary_and_names_what_it_couldnt_handle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_reports(tmp_path, skip="troupe")
    env = actions_env(tmp_path) | {"GITHUB_STEP_SUMMARY": str(tmp_path / "summary")}
    assert mi.main([str(tmp_path)], env, FakeGitHub()) == 1
    summary_text = (tmp_path / "summary").read_text(encoding="utf-8")
    assert summary_text == capsys.readouterr().out.removesuffix("\n")
    assert "## infrastructure at" in summary_text
    assert "## website at" in summary_text
    assert summary_text.endswith(
        "\n**Not handled:** troupe: no report (its job failed or timed out)\n"
    )


def test_a_run_links_its_issues_to_this_run(tmp_path: Path) -> None:
    write_reports(tmp_path)
    gh = FakeGitHub()
    env = actions_env(tmp_path) | {
        "GITHUB_SERVER_URL": "https://github.example",
        "GITHUB_REPOSITORY": "troupe-run/infrastructure",
        "GITHUB_RUN_ID": "77",
    }
    mi.main([str(tmp_path)], env, gh)
    bodies = [arg for write in gh.writes for arg in write if arg.startswith("body=")]
    assert all(
        "([run](https://github.example/troupe-run/infrastructure/actions/runs/77))" in b
        for b in bodies
    )


def test_unreadable_settings_stop_the_run_before_anything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "mutation.json"
    bad.write_text("{", encoding="utf-8")
    monkeypatch.setattr(mi, "SETTINGS", bad)
    assert mi.main([str(tmp_path)], {}, FakeGitHub()) == 2
    assert capsys.readouterr().err.startswith(
        "mutation_issues: mutation.json: the settings aren't JSON"
    )


def test_a_repositorys_read_token_reads_its_pull_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    made: list[str] = []

    def reading(token: str) -> mi.Gh:
        made.append(token)
        return lambda args: mi.GhResult(0, "[]", "")

    monkeypatch.setattr(mi, "reading_gh", reading)
    write_reports(tmp_path)
    mi.main([str(tmp_path)], actions_env(tmp_path) | {"READ_TOKEN": "t"}, FakeGitHub())
    assert made == ["t"]


def test_a_baseline_file_is_read_for_its_own_repository(tmp_path: Path) -> None:
    write_reports(tmp_path)
    # infrastructure.a at 50% with a 40% baseline: under 60%, but not below its baseline.
    (tmp_path / "quality-gates-infrastructure.toml").write_text(
        GATES
        + '\n[mutation.baselines."infrastructure.a"]\nscore = 40.0\nmutants = 20\njudged_at = "'
        + "e" * 40
        + '"\n',
        encoding="utf-8",
    )
    gh = FakeGitHub()
    assert mi.main([str(tmp_path)], actions_env(tmp_path), gh) == 0
    titles = sorted(arg for write in gh.writes for arg in write if arg.startswith("title="))
    assert titles == [
        "title=Mutation score 50% in infrastructure.a (under 60%)",
        "title=Mutation score 50% in troupe.a (under 60%)",
        "title=Mutation score 50% in website.a (under 60%)",
    ]
