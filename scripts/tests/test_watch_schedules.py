"""The schedule watch finds a watched workflow that stopped running, and keeps one tracking issue
about it (spec: schedule-watch; watch-website-link-check design D2 to D4, D7, D8).

The API's answers are the real payloads in fixtures/schedule-watch (its README says where each came
from). A test that needs another value changes that one field, so every shape is GitHub's own."""

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from conftest import REPO

import watch_schedules as ws

FIXTURES = Path(__file__).parent / "fixtures" / "schedule-watch"
WEBSITE = ws.Watched("website", "links-weekly.yml", 8)
# The fixtures' scheduled run began at 2026-10-19T08:52:35Z.
LAST_RUN = datetime(2026, 10, 19, 8, 52, 35, tzinfo=UTC)
RUN_URL = "https://github.com/troupe-run/infrastructure/actions/runs/1"

# The declaration's scope (scripts/check-paths.toml): a change to it runs these tests.
pytestmark = pytest.mark.schedules


def fixture(name: str) -> Any:  # noqa: ANN401
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def workflow(state: str = "active") -> dict[str, Any]:
    loaded = fixture("workflow.json")
    loaded["state"] = state
    return dict(loaded)


def runs(created_at: datetime | None = LAST_RUN, event: str = "schedule") -> dict[str, Any]:
    if created_at is None:
        return dict(fixture("runs-empty.json"))
    loaded = fixture("runs.json")
    loaded["workflow_runs"][0]["created_at"] = created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    loaded["workflow_runs"][0]["event"] = event
    return dict(loaded)


def problem(
    found: dict[str, Any] | None, page: dict[str, Any] | None, now: datetime
) -> ws.Problem | None:
    return ws.problem_for(WEBSITE, found, page, now)


# The declaration (spec: "The watched workflows are declared in one place")


def test_website_s_weekly_check_is_watched_for_8_days() -> None:
    text = (REPO / "scripts" / "watched-schedules.json").read_text(encoding="utf-8")
    assert WEBSITE in ws.load_declaration(text)


def test_the_dependabot_issues_backstop_is_watched_for_2_days() -> None:
    """Its schedule runs hours late, so 2 days allows one missed day (dependabot-issues-on-events
    design D6). Event runs don't count, so they can't hide a schedule that stopped."""
    text = (REPO / "scripts" / "watched-schedules.json").read_text(encoding="utf-8")
    assert ws.Watched("infrastructure", "dependabot-issues.yml", 2) in ws.load_declaration(text)


@pytest.mark.parametrize(
    ("entry", "named"),
    [
        ({"repository": "website", "workflow": "links-weekly.yml"}, "max_age_days"),
        (
            {"repository": "website", "workflow": "links-weekly.yml", "max_age_days": 0},
            "max_age_days",
        ),
        (
            {"repository": "website", "workflow": "links-weekly.yml", "max_age_days": "8"},
            "max_age_days",
        ),
        (
            {"repository": "website", "workflow": "links-weekly.yml", "max_age_days": True},
            "max_age_days",
        ),
        ({"repository": "website", "workflow": "links-weekly", "max_age_days": 8}, "workflow"),
        ({"repository": "a/b", "workflow": "links-weekly.yml", "max_age_days": 8}, "repository"),
        (
            {"repository": "website", "workflow": "x.yml", "max_age_days": 8, "branch": "main"},
            "branch",
        ),
    ],
)
def test_a_malformed_entry_is_refused_naming_the_entry_and_field(
    entry: dict[str, Any], named: str
) -> None:
    with pytest.raises(ws.DeclarationError, match=f"entry 1.*{named}"):
        ws.load_declaration(json.dumps([entry]))


@pytest.mark.parametrize("text", ["{}", "[]", "not json", '["website"]'])
def test_a_declaration_that_isn_t_a_list_of_entries_is_refused(text: str) -> None:
    with pytest.raises(ws.DeclarationError):
        ws.load_declaration(text)


# What counts as stopped (spec: "A stopped workflow is a problem")


def test_a_recent_scheduled_run_of_an_active_workflow_is_fine() -> None:
    assert problem(workflow(), runs(), LAST_RUN + timedelta(days=7, hours=23)) is None


@pytest.mark.parametrize("state", ["disabled_inactivity", "disabled_manually", "deleted"])
def test_a_workflow_turned_off_is_a_problem_with_its_state_and_the_command(state: str) -> None:
    found = problem(workflow(state), runs(), LAST_RUN + timedelta(days=1))
    assert found is not None
    assert found.kind == "not-active"
    assert state in found.detail
    assert "gh workflow enable links-weekly.yml -R troupe-run/website" in found.fix


def test_an_active_workflow_whose_last_scheduled_run_is_too_old_is_a_problem() -> None:
    found = problem(workflow(), runs(), LAST_RUN + timedelta(days=9))
    assert found is not None
    assert found.kind == "too-old"
    assert "2026-10-19" in found.detail


def test_a_workflow_that_never_ran_on_its_schedule_is_a_problem() -> None:
    found = problem(workflow(), runs(None), LAST_RUN)
    assert found is not None
    assert found.kind == "never-ran"


def test_a_workflow_not_found_is_a_problem_naming_the_declaration() -> None:
    found = problem(None, None, LAST_RUN)
    assert found is not None
    assert found.kind == "not-found"
    assert "scripts/watched-schedules.json" in found.fix


def test_a_run_started_by_hand_in_the_answer_is_refused() -> None:
    """The read asks for scheduled runs only; a run of another event in the answer is refused."""
    with pytest.raises(ws.ReadError, match="workflow_dispatch"):
        problem(workflow(), runs(LAST_RUN, event="workflow_dispatch"), LAST_RUN)


def test_the_read_asks_for_scheduled_runs_only() -> None:
    calls: list[list[str]] = []

    def gh(args: list[str]) -> ws.GhResult:
        calls.append(args)
        if args[1].endswith("/runs?event=schedule&per_page=1"):
            return ws.GhResult(0, json.dumps(runs()), "")
        return ws.GhResult(0, json.dumps(workflow()), "")

    ws.read(WEBSITE, gh)
    assert ["api", "repos/troupe-run/website/actions/workflows/links-weekly.yml"] in calls
    assert [
        "api",
        "repos/troupe-run/website/actions/workflows/links-weekly.yml/runs?event=schedule&per_page=1",
    ] in calls


def test_a_404_is_read_as_not_found() -> None:
    def gh(args: list[str]) -> ws.GhResult:
        return ws.GhResult(
            1,
            (FIXTURES / "not-found.json").read_text(encoding="utf-8"),
            (FIXTURES / "not-found.stderr").read_text(encoding="utf-8"),
        )

    assert ws.read(WEBSITE, gh) == (None, None)


# Errors aren't problems (spec: "An unreadable workflow is an error, not a clean result")


@pytest.mark.parametrize(
    ("result", "named"),
    [
        (ws.GhResult(1, '{"message":"Server Error"}', "gh: Server Error (HTTP 502)"), "HTTP 502"),
        (ws.GhResult(1, "", "gh: Resource not accessible (HTTP 403)"), "HTTP 403"),
        (ws.GhResult(1, "", "error connecting to api.github.com"), "error connecting"),
        (ws.GhResult(0, "<html>", ""), "JSON"),
    ],
)
def test_a_failed_read_raises_naming_the_workflow_and_the_error(
    result: ws.GhResult, named: str
) -> None:
    with pytest.raises(ws.ReadError, match=f"website/links-weekly.yml.*{named}"):
        ws.read(WEBSITE, lambda args: result)


@pytest.mark.parametrize(
    "change",
    [
        lambda w, r: w.pop("state"),
        lambda w, r: w.update(state=3),
        lambda w, r: r.pop("workflow_runs"),
        lambda w, r: r["workflow_runs"][0].update(created_at="yesterday"),
    ],
)
def test_an_answer_of_another_shape_raises_rather_than_reports_all_clear(change: Any) -> None:  # noqa: ANN401
    found, page = workflow(), runs()
    change(found, page)
    with pytest.raises(ws.ReadError):
        problem(found, page, LAST_RUN)


# The tracking issue (spec: "One tracking issue reports the problems")


def listed(*numbers: int, state: str = "OPEN") -> list[dict[str, Any]]:
    """Real list entries, renamed to the tracking title and reopened."""
    entries = []
    for entry in fixture("issues.json"):
        if entry["number"] in numbers:
            entry = copy.deepcopy(entry)
            entry["title"] = ws.TITLE
            entry["state"] = state
            entries.append(entry)
    return entries


def test_the_oldest_tracking_issue_opened_by_the_workflow_s_token_is_kept() -> None:
    found = ws.tracking_issues(listed(19, 21))
    assert [issue["number"] for issue in found] == [19, 21]


def test_an_issue_a_person_opened_with_the_same_title_is_ignored() -> None:
    assert ws.tracking_issues(listed(18)) == []


def test_an_issue_with_another_title_is_ignored() -> None:
    assert ws.tracking_issues(fixture("issues.json")) == []


STOPPED = ws.Problem("website", "links-weekly.yml", "not-active", "state is x", "fix it")
LATE = ws.Problem("website", "links-weekly.yml", "too-old", "last ran long ago", "fix it")
OTHER = ws.Problem("troupe", "nightly.yml", "never-ran", "never ran", "fix it")
OPEN_ISSUE = {"number": 7, "url": "https://github.com/troupe-run/infrastructure/issues/7"}


@pytest.mark.parametrize(
    ("problems", "issue", "last", "action"),
    [
        ([STOPPED], None, None, "open"),
        ([STOPPED], OPEN_ISSUE, ws.fingerprint([STOPPED]), "none"),
        ([STOPPED], OPEN_ISSUE, ws.fingerprint([LATE]), "comment"),
        ([STOPPED, OTHER], OPEN_ISSUE, ws.fingerprint([STOPPED]), "comment"),
        ([STOPPED], OPEN_ISSUE, ws.fingerprint([STOPPED, OTHER]), "comment"),
        ([STOPPED], OPEN_ISSUE, None, "comment"),
        ([], OPEN_ISSUE, ws.fingerprint([STOPPED]), "close"),
        ([], None, None, "none"),
    ],
)
def test_the_issue_action_follows_design_d4_s_table(
    problems: list[ws.Problem], issue: dict[str, Any] | None, last: str | None, action: str
) -> None:
    assert ws.decide(problems, issue, last) == action


def test_the_fingerprint_ignores_details_such_as_ages_and_order() -> None:
    older = ws.Problem("website", "links-weekly.yml", "too-old", "began 10 days ago", "x")
    assert ws.fingerprint([LATE, OTHER]) == ws.fingerprint([OTHER, older])


def test_the_report_names_each_problem_its_fix_the_run_and_carries_the_fingerprint() -> None:
    body = ws.report([STOPPED, OTHER], RUN_URL)
    for found in (STOPPED, OTHER):
        assert found.detail in body
        assert found.fix in body
    assert RUN_URL in body
    assert ws.last_fingerprint({"body": body, "comments": []}) == ws.fingerprint([STOPPED, OTHER])


def test_the_last_fingerprint_is_the_newest_the_watch_posted() -> None:
    view = fixture("issue-view.json")
    view["body"] = ws.report([STOPPED], RUN_URL)
    view["comments"][0]["body"] = ws.report([LATE], RUN_URL)
    # A person quoting an older report doesn't count.
    view["comments"][2]["body"] = ws.report([OTHER], RUN_URL)
    assert ws.last_fingerprint(view) == ws.fingerprint([LATE])


def test_no_fingerprint_when_the_marker_was_edited_out() -> None:
    assert ws.last_fingerprint(fixture("issue-view.json")) is None


# The extra workflow (spec: "The issue path can be proved without stopping a watched workflow")


def test_an_extra_workflow_in_the_org_is_watched_for_8_days() -> None:
    assert ws.parse_extra("troupe-run/infra-probe-x/probe.yml") == ws.Watched(
        "infra-probe-x", "probe.yml", 8
    )
    assert ws.parse_extra("") is None


@pytest.mark.parametrize(
    "value",
    [
        "someone-else/repo/x.yml",
        "troupe-run/website",
        "troupe-run/website/.github/workflows/links-weekly.yml",
        "troupe-run/website/links-weekly",
        "troupe-run/web site/x.yml",
        "troupe-run/website/x.yml; rm -rf /",
    ],
)
def test_an_extra_workflow_in_any_other_form_is_refused_naming_it(value: str) -> None:
    with pytest.raises(ws.DeclarationError, match="extra-workflow"):
        ws.parse_extra(value)


# The whole run against a fake gh (spec: "A run that finds a problem fails", "Outside GitHub
# Actions the watch only reports")


class FakeGh:
    """Answers reads from the fixtures, and records every write."""

    def __init__(
        self, state: str = "active", open_issues: list[dict[str, Any]] | None = None
    ) -> None:
        self.state = state
        self.open_issues = open_issues or []
        self.writes: list[list[str]] = []

    def __call__(self, args: list[str]) -> ws.GhResult:
        if args[:2] == ["issue", "list"]:
            return ws.GhResult(0, json.dumps(self.open_issues), "")
        if args[:2] == ["issue", "view"]:
            return ws.GhResult(0, json.dumps(fixture("issue-view.json")), "")
        if args[0] == "api" and args[1].endswith("per_page=1"):
            return ws.GhResult(0, json.dumps(runs()), "")
        if args[0] == "api":
            return ws.GhResult(0, json.dumps(workflow(self.state)), "")
        self.writes.append(args)
        url = "https://github.com/troupe-run/infrastructure/issues/9\n"
        return ws.GhResult(0, url if args[:2] == ["issue", "create"] else "", "")


def actions_env(tmp_path: Path) -> dict[str, str]:
    return {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": "troupe-run/infrastructure",
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_RUN_ID": "1",
        "GITHUB_OUTPUT": str(tmp_path / "output"),
    }


def declaration(tmp_path: Path) -> Path:
    path = tmp_path / "watched.json"
    path.write_text(
        json.dumps([{"repository": "website", "workflow": "links-weekly.yml", "max_age_days": 8}]),
        encoding="utf-8",
    )
    return path


def test_a_problem_opens_the_issue_hands_its_url_over_and_fails_the_run(tmp_path: Path) -> None:
    gh = FakeGh(state="disabled_inactivity")
    code = ws.run(declaration(tmp_path), "", actions_env(tmp_path), gh, now=LAST_RUN)
    assert code == 1
    assert [write[:2] for write in gh.writes] == [["issue", "create"]]
    assert ws.TITLE in gh.writes[0]
    assert (tmp_path / "output").read_text(encoding="utf-8") == (
        "issue-url=https://github.com/troupe-run/infrastructure/issues/9\n"
    )


def test_no_problem_closes_the_open_issue_and_the_run_succeeds(tmp_path: Path) -> None:
    gh = FakeGh(open_issues=listed(19))
    code = ws.run(declaration(tmp_path), "", actions_env(tmp_path), gh, now=LAST_RUN)
    assert code == 0
    assert [write[:3] for write in gh.writes] == [["issue", "close", "19"]]
    assert not (tmp_path / "output").exists()


def test_a_failed_read_touches_no_issue(tmp_path: Path) -> None:
    def gh(args: list[str]) -> ws.GhResult:
        if args[0] == "api":
            return ws.GhResult(1, "", "gh: Server Error (HTTP 502)")
        raise AssertionError(f"touched the issue: {args}")

    code = ws.run(declaration(tmp_path), "", actions_env(tmp_path), gh, now=LAST_RUN)
    assert code == 2


def test_a_bad_extra_workflow_reads_nothing(tmp_path: Path) -> None:
    def gh(args: list[str]) -> ws.GhResult:
        raise AssertionError(f"read GitHub: {args}")

    code = ws.run(
        declaration(tmp_path), "elsewhere/x/y.yml", actions_env(tmp_path), gh, now=LAST_RUN
    )
    assert code == 2


def test_outside_actions_it_only_reports(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gh = FakeGh(state="disabled_manually")
    code = ws.run(declaration(tmp_path), "", {}, gh, now=LAST_RUN)
    assert gh.writes == []
    assert code == 1
    out = capsys.readouterr().out
    assert "website/links-weekly.yml" in out
    assert "would open" in out
