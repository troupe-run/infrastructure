"""Every Dependabot pull request gets its issue, and closes it (spec: dependency-updates;
dependabot-issues design D2 to D6, D8).

The pull requests and issues are the real payloads in fixtures/dependabot-issues (its README says
where each came from). A test that needs another value changes that one field, so every shape is
GitHub's own."""

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from conftest import REPO

import dependabot_issues as di

FIXTURES = Path(__file__).parent / "fixtures" / "dependabot-issues"
NOW = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)


def fixture(name: str) -> Any:  # noqa: ANN401
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def pull(name: str = "website-44", **changes: Any) -> dict[str, Any]:  # noqa: ANN401
    loaded = dict(fixture(f"pull-{name}.json"))
    loaded.update(changes)
    return loaded


def app_issue(for_pull: dict[str, Any], number: int = 100, **changes: Any) -> dict[str, Any]:  # noqa: ANN401
    """The issue the App would have opened for for_pull, in the shape of a real bot's issue."""
    loaded = dict(fixture("issue-website-21.json"))
    update = di.read_update(for_pull)
    loaded.update(
        number=number,
        title=di.issue_title(for_pull, update),
        state="open",
        state_reason=None,
        closed_at=None,
        user={"login": di.APP, "type": "Bot"},
        labels=[di.LABEL],
        body=di.issue_body(for_pull, update),
        html_url=f"https://github.com/troupe-run/website/issues/{number}",
    )
    loaded.update(changes)
    return loaded


def closed(p: dict[str, Any], ago: timedelta, merged: bool = False) -> dict[str, Any]:
    at = (NOW - ago).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {**p, "state": "closed", "closed_at": at, "merged_at": at if merged else None}


def kinds(result: di.Plan) -> list[tuple[str, int, int | None]]:
    return [
        (a.kind, int(a.pull["number"]), int(a.issue["number"]) if a.issue else None)
        for a in result.actions
    ]


def lined(p: dict[str, Any], issue: int) -> dict[str, Any]:
    return {**p, "body": di.with_closing_line(p, issue)}


def just_changed(p: dict[str, Any]) -> dict[str, Any]:
    """As the run Dependabot's change started sees it: updated minutes ago, so not a miss."""
    return {**p, "updated_at": (NOW - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")}


# Reading a pull request (spec: "The issue says what the update is"; design D3, D4)


@pytest.mark.parametrize(
    ("name", "ecosystem", "directory", "dependency", "old", "new", "kind"),
    [
        ("website-44", "npm_and_yarn", "/", "zod", "4.6.5", "4.6.7", "patch"),
        ("website-55", "npm_and_yarn", "/", "typescript", "6.0.3", "7.0.2", "major"),
        ("website-58", "npm_and_yarn", "/", "@axe-core/playwright", "4.13.0", "4.14.0", "minor"),
        ("website-54", "npm_and_yarn", "/", "postcss-selector-parser", "6.1.4", "6.1.5", "patch"),
        ("infrastructure-184", "github_actions", "/", "actions/download-artifact", "8.0.1",
         "8.0.2", "patch"),
        ("troupe-175", "uv", "/", "uv-build", "<0.14,>=0.13.0", ">=0.13.2,<0.14", "patch"),
        ("troupe-181", "uv", "/", "uv-build", "<0.14,>=0.13.0", ">=0.13.5,<0.14", "patch"),
    ],
)  # fmt: skip
def test_each_real_title_gives_its_dependency_versions_and_type(
    name: str, ecosystem: str, directory: str, dependency: str, old: str, new: str, kind: str
) -> None:
    update = di.read_update(pull(name))
    assert update == di.Update(di.Key(ecosystem, directory, dependency), old, new, kind)


@pytest.mark.parametrize(
    ("old", "new", "kind"),
    [
        ("0.30.0", "0.30.2", "patch"),
        ("3", "7", "major"),
        ("v3", "v4", "major"),
        ("1.2", "1.3.0", "minor"),
        ("1.2.3.4", "1.2.3.5", "patch"),
        ("1.2.3", "1.2.3", "unknown"),
        ("1.2.3", "1.2.3-rc.1", "unknown"),
        ("abc1234", "def5678", "unknown"),
    ],
)
def test_update_type_counts_as_dependabot_does(old: str, new: str, kind: str) -> None:
    assert di.update_type(old, new) == kind


# A requirement update's ranges (guard-requirement-range design D4)


@pytest.mark.parametrize(
    ("old", "new", "kind"),
    [
        ("<0.14,>=0.13.0", ">=0.13.5,<0.14", "patch"),  # troupe #181, bounds reordered
        ("<9.6,>=9.5.6", ">=9.6.0,<9.7", "minor"),
        ("<5,>=4.26", ">=4.26,<6", "major"),
        ("^4.6.5", "^4.7.0", "minor"),
        (">=1.2 <2", ">=1.3 <2", "minor"),  # npm separates bounds with a space
        ("<0.14,>=0.13.5", ">=0.13.0,<0.14", "unknown"),  # a bound that goes down
        ("<0.14,>=0.13.0", ">=0.13.0,<0.14", "unknown"),  # nothing moves
        ("<0.14,>=0.13.0", "~=0.13.5", "unknown"),  # the operators change
        ("<0.14,>=0.13.0", ">=0.13.5", "unknown"),  # a bound is dropped
        ("<0.14,>=0.13.0", ">=0.13.5,<0.14,!=0.13.6", "unknown"),  # a bound is added
        ("4.x", "5.x", "unknown"),
        (">=1,>=2", ">=1,>=3", "unknown"),  # an operator twice
    ],
)
def test_a_range_counts_by_its_bounds_paired_by_operator(old: str, new: str, kind: str) -> None:
    assert di.range_kind(old, new) == kind


def test_a_requirement_title_counts_its_ranges() -> None:
    p = pull("troupe-181", title="Update jsonschema requirement from <5,>=4.26 to >=4.26,<6")
    assert di.read_update(p).kind == "major"


def test_a_bump_title_with_ranges_is_still_unknown() -> None:
    # Only a requirement title is read as ranges; a bump's versions are versions.
    p = pull("website-44", title="chore(deps): Bump zod from <5,>=4.6.5 to >=4.6.7,<5")
    assert di.read_update(p).kind == "unknown"


def test_a_requirement_issue_within_a_minor_series_doesnt_need_a_change() -> None:
    p = pull("troupe-181")
    body = di.issue_body(p, di.read_update(p))
    assert "Update type: **patch**." in body
    assert "OpenSpec change" not in body


def test_a_requirement_issue_admitting_a_new_major_needs_a_change() -> None:
    p = pull("troupe-181", title="Update jsonschema requirement from <5,>=4.26 to >=4.26,<6")
    body = di.issue_body(p, di.read_update(p))
    assert "Update type: **major**." in body
    assert "needs an OpenSpec change" in body


def test_a_requirement_issue_whose_bounds_dont_match_needs_a_change() -> None:
    p = pull("troupe-181", title="Update uv-build requirement from <0.14,>=0.13.0 to ~=0.13.5")
    body = di.issue_body(p, di.read_update(p))
    assert "Update type: **unknown**." in body
    assert "needs an OpenSpec change" in body


def test_a_directory_in_the_title_is_part_of_the_key_and_the_issue_title() -> None:
    p = pull(title="chore(deps): Bump zod from 4.6.5 to 4.6.7 in /site")
    update = di.read_update(p)
    assert update.key == di.Key("npm_and_yarn", "/site", "zod")
    assert di.issue_title(p, update) == "Update zod from 4.6.5 to 4.6.7 in /site"


def test_a_patch_issue_names_the_dependency_versions_and_type() -> None:
    p = pull("website-44")
    update = di.read_update(p)
    assert di.issue_title(p, update) == "Update zod from 4.6.5 to 4.6.7"
    body = di.issue_body(p, update)
    assert "#44" in body
    assert "release notes" in body
    assert "Update type: **patch**." in body
    assert "OpenSpec change" not in body


def test_a_major_issue_says_it_needs_an_openspec_change() -> None:
    body = di.issue_body(pull("website-55"), di.read_update(pull("website-55")))
    assert "Update type: **major**." in body
    assert "needs an OpenSpec change" in body


def test_versions_that_cant_be_read_give_an_unknown_issue_from_the_title() -> None:
    p = pull(title="chore(deps): Bump zod and undici")
    update = di.read_update(p)
    assert update == di.Update(None, None, None, "unknown")
    assert di.issue_title(p, update) == "Bump zod and undici"
    body = di.issue_body(p, update)
    assert "Update type: **unknown**." in body
    assert "needs an OpenSpec change" in body


def test_the_issue_doesnt_copy_the_release_notes() -> None:
    p = pull("website-44")
    assert "malicious commits" in p["body"]
    assert "malicious commits" not in di.issue_body(p, di.read_update(p))


def test_the_marker_reads_back_as_written() -> None:
    p = pull("website-58")
    mark = di.read_marker(app_issue(p))
    assert mark == di.Marker(di.Key("npm_and_yarn", "/", "@axe-core/playwright"), 58)


def test_an_unkeyed_marker_reads_back_with_no_key() -> None:
    p = pull(title="chore(deps): Bump zod and undici")
    assert di.read_marker(app_issue(p)) == di.Marker(None, 44)


@pytest.mark.parametrize(
    "body",
    [
        "no marker here",
        "<!-- dependabot-issue: {not json} -->",
        '<!-- dependabot-issue: {"pull": "44"} -->',
        '<!-- dependabot-issue: {"pull": 44, "ecosystem": "npm_and_yarn"} -->',
    ],
)
def test_a_malformed_marker_is_an_error_not_a_guess(body: str) -> None:
    with pytest.raises(di.ReadError, match="#100"):
        di.read_marker(app_issue(pull(), body=body))


# The closing line (spec: "A Dependabot pull request closes its issue")


def test_the_closing_line_is_appended_and_the_description_kept() -> None:
    p = pull("website-44")
    body = di.with_closing_line(p, 100)
    assert body.startswith(p["body"].rstrip())
    assert body.endswith("\n\nCloses #100")
    assert di.has_closing_line({"body": body}, 100)


def test_another_issue_s_line_isnt_this_one() -> None:
    assert not di.has_closing_line({"body": "Closes #101"}, 100)
    assert not di.has_closing_line({"body": "Closes #1000"}, 100)
    assert not di.has_closing_line({"body": None}, 100)


# Deciding (spec: every requirement on the issue's life; design D2)


def test_a_new_pull_request_gets_a_new_issue() -> None:
    assert kinds(di.plan([pull()], [], {}, NOW)) == [("open", 44, None)]


def test_every_open_pull_request_gets_its_own_issue() -> None:
    pulls = [pull("website-44"), pull("website-55"), pull("website-58")]
    assert kinds(di.plan(pulls, [], {}, NOW)) == [
        ("open", 44, None),
        ("open", 55, None),
        ("open", 58, None),
    ]


def test_nothing_to_do_when_each_has_its_issue_and_line() -> None:
    p = pull()
    assert di.plan([lined(p, 100)], [app_issue(p)], {}, NOW).actions == []


def test_a_rewritten_description_gets_its_line_back() -> None:
    p = pull()  # Dependabot's own description: no closing line
    assert kinds(di.plan([p], [app_issue(p)], {}, NOW)) == [("line", 44, 100)]


def test_a_superseded_update_relinks_its_issue() -> None:
    old = pull()
    new = pull(number=60, title="chore(deps): Bump zod from 4.6.5 to 4.6.8",
               head={"ref": "dependabot/npm_and_yarn/zod-4.6.8"})  # fmt: skip
    issue = app_issue(old)
    result = di.plan([new], [issue], {44: closed(old, timedelta(minutes=5))}, NOW)
    assert kinds(result) == [("relink", 60, 100), ("line", 60, 100)]


def test_the_same_name_in_another_ecosystem_gets_a_new_issue() -> None:
    old = pull()
    other = pull(number=61, head={"ref": "dependabot/github_actions/zod-4.6.8"})
    issue = app_issue(old)
    result = di.plan([other], [issue], {44: closed(old, timedelta(minutes=5))}, NOW)
    assert kinds(result) == [("open", 61, None)]


def test_an_issue_whose_pull_request_is_still_open_isnt_relinked() -> None:
    first = pull()
    second = pull(number=60)
    result = di.plan([lined(first, 100), second], [app_issue(first)], {}, NOW)
    assert kinds(result) == [("open", 60, None)]


def test_an_unkeyed_issue_is_never_reused() -> None:
    old = pull(title="chore(deps): Bump zod and undici")
    new = pull(number=60, title="chore(deps): Bump zod and undici")
    result = di.plan([new], [app_issue(old)], {44: closed(old, timedelta(minutes=5))}, NOW)
    assert ("open", 60, None) in kinds(result)


def test_merged_while_the_issue_stays_open_closes_it_as_completed() -> None:
    p = pull()
    result = di.plan([], [app_issue(p)], {44: closed(p, timedelta(minutes=1), merged=True)}, NOW)
    assert kinds(result) == [("close-completed", 44, 100)]


def test_closed_without_merging_waits_an_hour_for_a_successor() -> None:
    p = pull()
    result = di.plan([], [app_issue(p)], {44: closed(p, timedelta(minutes=59))}, NOW)
    assert result.actions == []


def test_closed_without_merging_and_no_successor_closes_as_not_planned() -> None:
    p = pull()
    result = di.plan([], [app_issue(p)], {44: closed(p, timedelta(hours=1))}, NOW)
    assert kinds(result) == [("close-not-planned", 44, 100)]


def test_a_successor_keeps_the_old_issue_open_when_it_took_another() -> None:
    # The successor is linked to its own issue already: the old one closes only if its key is free.
    old = pull()
    new = pull(number=60, title="chore(deps): Bump zod from 4.6.5 to 4.6.8")
    issues = [app_issue(new, number=101), app_issue(old)]
    result = di.plan([lined(new, 101)], issues, {44: closed(old, timedelta(hours=2))}, NOW)
    assert result.actions == []


def test_a_reopened_pull_request_reopens_its_issue() -> None:
    p = pull()
    issue = app_issue(p, state="closed", state_reason="not_planned")
    assert kinds(di.plan([lined(p, 100)], [issue], {}, NOW)) == [("reopen", 44, 100)]


def test_an_issue_a_change_closed_isnt_reopened_while_dependabot_s_pull_request_is_open() -> None:
    p = pull()
    issue = app_issue(p, state="closed", state_reason="completed")
    assert di.plan([p], [issue], {}, NOW).actions == []


def test_an_issue_whose_marker_was_edited_away_is_left_alone_with_its_pull_request() -> None:
    p = pull()
    damaged = app_issue(p, body="Someone tidied this description.")
    other = pull("website-55")
    result = di.plan([lined(p, 100), other], [damaged], {}, NOW)
    # No duplicate for #44, nothing done to #100, and #55 is still handled.
    assert kinds(result) == [("open", 55, None)]
    assert len(result.unreadable) == 1
    assert "#100" in result.unreadable[0]
    assert "edit history" in result.unreadable[0]


def test_a_damaged_closed_issue_doesn_t_stop_a_merge_closing_another() -> None:
    p = pull()
    old = pull("website-58")
    damaged = app_issue(old, number=99, state="closed", body="no marker")
    result = di.plan([], [damaged, app_issue(p)], {44: closed(p, timedelta(1), merged=True)}, NOW)
    assert kinds(result) == [("close-completed", 44, 100)]
    assert len(result.unreadable) == 1


def test_the_issue_says_to_add_notes_as_comments() -> None:
    assert "Add notes as comments" in di.issue_body(pull(), di.read_update(pull()))


def test_an_issue_whose_pull_request_wasnt_read_is_an_error() -> None:
    with pytest.raises(di.ReadError, match="#44 wasn't read"):
        di.plan([], [app_issue(pull())], {}, NOW)


# Trust (spec: "Only Dependabot's pull requests and the App's own issues are trusted"; design D6)


def test_a_person_s_branch_named_like_dependabot_s_is_left_alone() -> None:
    person = pull(user={"login": "someone", "type": "User"},
                  head={"ref": "dependabot/npm_and_yarn/zod-4.6.8"})  # fmt: skip
    assert di.plan([person], [], {}, NOW).actions == []


def test_a_user_named_like_dependabot_who_isnt_a_bot_is_left_alone() -> None:
    assert di.plan([pull(user={"login": di.DEPENDABOT, "type": "User"})], [], {}, NOW).actions == []


# A person, and another App's bot, which is also of type Bot.
@pytest.mark.parametrize(
    "author",
    [{"login": "someone", "type": "User"}, {"login": "github-actions[bot]", "type": "Bot"}],
)
def test_someone_else_s_issue_with_a_copied_marker_is_neither_reused_nor_closed(
    author: dict[str, str],
) -> None:
    p = pull()
    fake = app_issue(p, user=author)
    assert kinds(di.plan([p], [fake], {}, NOW)) == [("open", 44, None)]
    gone = closed(p, timedelta(hours=2))
    assert di.plan([], [fake], {44: gone}, NOW).actions == []


def test_a_closing_line_to_someone_else_s_issue_still_gets_the_app_s_issue() -> None:
    p = pull(body="Closes #7")
    assert kinds(di.plan([p], [], {}, NOW)) == [("open", 44, None)]


# The release in progress (spec: "The release in progress is the lowest open milestone"; D5)


@pytest.mark.milestones
def test_today_s_release_in_progress_is_0_1_0() -> None:
    text = (REPO / "tofu" / "milestones.json").read_text(encoding="utf-8")
    assert di.release_in_progress(text) == "0.1.0"


def test_the_lowest_version_wins_not_the_first_listed() -> None:
    declared = {"milestones": [
        {"title": "0.10.0", "state": "open"},
        {"title": "0.1.0", "state": "closed"},
        {"title": "0.2.0", "state": "open"},
    ]}  # fmt: skip
    assert di.release_in_progress(json.dumps(declared)) == "0.2.0"


def test_no_open_milestone_is_an_error() -> None:
    declared = {"milestones": [{"title": "0.1.0", "state": "closed"}]}
    with pytest.raises(di.StartError, match="no release in progress"):
        di.release_in_progress(json.dumps(declared))


@pytest.mark.labels
def test_the_repositories_are_those_with_dependabot_ecosystems() -> None:
    text = (REPO / "tofu" / "labels" / "dependabot.json").read_text(encoding="utf-8")
    assert di.repositories(text) == ["infrastructure", "troupe", "website"]


# Security updates (spec: dependency-updates, "A security update is told by the repository's open
# alerts", "A run never takes a milestone off an issue"; needed-for-milestones design D1, D3). The
# alerts are website's real ones: zod, fast-uri and postcss-selector-parser open, undici fixed.

ALERTS = fixture("alerts-website.json")


def bump(dependency: str, old: str, new: str, ecosystem: str = "npm_and_yarn") -> dict[str, Any]:
    """website #44 retitled and rebranched as Dependabot would for another dependency."""
    return pull(
        number=70,
        title=f"chore(deps): Bump {dependency} from {old} to {new}",
        head={"ref": f"dependabot/{ecosystem}/{dependency}-{new}"},
    )


def alert(ecosystem: str, name: str, patched: str | None, state: str = "open") -> dict[str, Any]:
    """website's zod alert, changed to another package (the fixture's shape)."""
    zod = next(a for a in ALERTS if a["dependency"]["package"]["name"] == "zod")
    loaded: dict[str, Any] = copy.deepcopy(zod)
    loaded["state"] = state
    loaded["dependency"]["package"] = {"ecosystem": ecosystem, "name": name}
    loaded["security_vulnerability"]["first_patched_version"] = (
        {"identifier": patched} if patched is not None else None
    )
    return loaded


def opened(p: dict[str, Any], alerts: list[dict[str, Any]]) -> di.Action:
    (action,) = di.plan([p], [], {}, NOW, alerts).actions
    assert action.kind == "open"
    return action


def test_a_pull_request_that_fixes_an_open_alert_is_a_security_update() -> None:
    assert opened(pull("website-44"), ALERTS).security  # zod 4.6.5 to 4.6.7, fixed in 4.6.6


def test_a_pull_request_that_moves_to_the_patched_version_itself_is_a_security_update() -> None:
    assert opened(bump("fast-uri", "3.1.8", "3.1.9"), ALERTS).security


def test_a_version_update_for_a_package_with_no_alert_is_a_version_update() -> None:
    assert not opened(pull("website-55"), ALERTS).security  # typescript


def test_an_alert_that_s_already_fixed_doesn_t_make_a_security_update() -> None:
    assert not opened(bump("undici", "8.11.2", "8.12.3"), ALERTS).security


def test_a_pull_request_that_stops_short_of_the_fix_is_a_version_update() -> None:
    assert not opened(bump("fast-uri", "3.1.7", "3.1.8"), ALERTS).security


def test_the_same_name_in_another_ecosystem_isn_t_a_security_update() -> None:
    assert not opened(bump("zod", "4.6.5", "4.6.7", "github_actions"), ALERTS).security


def test_an_alert_with_no_patched_version_makes_no_security_update() -> None:
    assert not opened(pull("website-44"), [alert("npm", "zod", None)]).security


def test_a_python_name_matches_as_pypi_normalises_it() -> None:
    assert opened(
        bump("uv-build", "0.13.0", "0.13.5", "uv"), [alert("pip", "UV_Build", "0.13.2")]
    ).security


def test_an_action_s_name_matches_whatever_its_case() -> None:
    p = pull("infrastructure-184")  # actions/download-artifact 8.0.1 to 8.0.2
    assert opened(p, [alert("actions", "Actions/Download-Artifact", "8.0.2")]).security


def test_a_range_that_can_t_be_read_as_a_version_counts_as_a_security_update() -> None:
    p = pull("troupe-175")  # uv-build requirement, <0.14,>=0.13.0 to >=0.13.2,<0.14
    assert opened(p, [alert("pip", "uv_build", "0.13.1")]).security


def test_a_title_that_can_t_be_read_is_a_security_update_while_any_alert_has_a_fix() -> None:
    p = pull(title="chore(deps): Bump the npm group with 3 updates")
    assert opened(p, ALERTS).security
    assert not opened(p, [alert("npm", "zod", "4.6.6", state="fixed")]).security


def test_an_ecosystem_with_no_alert_ecosystem_opens_no_issue_and_names_it() -> None:
    p = pull(head={"ref": "dependabot/cargo/serde-1.0.2"})
    result = di.plan([p], [], {}, NOW, ALERTS)
    assert result.actions == []
    (problem,) = result.unreadable
    assert "cargo" in problem
    assert "ALERT_ECOSYSTEMS" in problem


def test_an_unknown_ecosystem_doesn_t_stop_a_pull_request_that_already_has_its_issue() -> None:
    p = pull(head={"ref": "dependabot/cargo/serde-1.0.2"})
    result = di.plan([lined(p, 100)], [app_issue(p)], {}, NOW, ALERTS)
    assert (result.actions, result.unreadable) == ([], [])


def relinked(old: dict[str, Any], new: dict[str, Any], issue: dict[str, Any]) -> di.Action:
    linked = {int(old["number"]): closed(old, timedelta(minutes=5))}
    action = di.plan([new], [issue], linked, NOW, ALERTS).actions[0]
    assert action.kind == "relink"
    return action


def test_a_security_update_relinked_to_an_issue_with_no_milestone_sets_it() -> None:
    old, new = bump("zod", "4.6.4", "4.6.5"), pull("website-44")
    action = relinked(old, new, app_issue(old, milestone=None))
    assert action.security
    assert di.relink_payload(action, 1)["milestone"] == 1


def test_a_version_update_relinked_to_an_issue_in_a_milestone_keeps_its_milestone() -> None:
    old, new = bump("vitest", "5.0.3", "5.0.4"), {**bump("vitest", "5.0.3", "5.0.5"), "number": 71}
    action = relinked(old, new, app_issue(old, milestone={"number": 1, "title": "0.1.0"}))
    assert not action.security
    assert "milestone" not in di.relink_payload(action, 1)


def test_a_milestone_set_by_hand_stays_when_a_security_update_is_relinked() -> None:
    old, new = bump("zod", "4.6.4", "4.6.5"), pull("website-44")
    action = relinked(old, new, app_issue(old, milestone={"number": 3, "title": "0.2.0"}))
    assert action.security
    assert "milestone" not in di.relink_payload(action, 1)


def test_the_dry_run_says_which_kind_of_update_it_would_open() -> None:
    assert di.describe(opened(pull("website-44"), ALERTS)).endswith("(a security update)")
    assert di.describe(opened(pull("website-55"), ALERTS)).endswith("(a version update)")


# The run, against a fake GitHub (design D2, D8)


class FakeGitHub:
    """Answers the reads from per-repository data, and records every write."""

    def __init__(self, data: dict[str, dict[str, Any]]) -> None:
        # Every run reads the tracking issue there (design D5); a test that needs it down says so.
        self.data = {"infrastructure": {}, **data}
        self.writes: list[tuple[str, str, dict[str, Any]]] = []
        self.next_issue = 500

    def __call__(self, args: list[str], stdin: str | None) -> di.GhResult:
        assert args[0] == "api"
        if "--method" in args:
            method, path = args[args.index("--method") + 1], args[args.index("--method") + 2]
            payload = json.loads(stdin or "{}")
            self.writes.append((method, path, payload))
            if method == "POST" and path.endswith("/issues"):
                self.next_issue += 1
                repo = path.split("/")[2]
                url = f"https://github.com/troupe-run/{repo}/issues/{self.next_issue}"
                return di.GhResult(0, json.dumps({"number": self.next_issue, "html_url": url}), "")
            return di.GhResult(0, "{}", "")
        path = args[-1]
        repo = path.split("/")[2]
        data = self.data.get(repo)
        if data is None or data.get("fail"):
            return di.GhResult(1, "", f"gh: {repo} is down (HTTP 502)")
        if "/milestones" in path:
            return di.GhResult(0, json.dumps([fixture("milestones-website.json")]), "")
        if "/dependabot/alerts?" in path:
            if data.get("alerts-fail"):
                return di.GhResult(1, "", "gh: Resource not accessible by integration (HTTP 403)")
            found = [a for a in data.get("alerts", []) if a["state"] == "open"]
            return di.GhResult(0, json.dumps([found]), "")
        if "/pulls?" in path:
            return di.GhResult(0, json.dumps([data.get("pulls", [])]), "")
        if "/issues?" in path:
            state = "open" if "state=open" in path else "closed"
            found = [i for i in data.get("issues", []) if i["state"] == state]
            if f"labels={di.LABEL}" in path:
                found = [i for i in found if di.LABEL in di.labels_of(i)]
            return di.GhResult(0, json.dumps([found]), "")
        if "/comments?" in path:
            number = int(path.split("/")[4])
            return di.GhResult(0, json.dumps([data.get("comments", {}).get(number, [])]), "")
        number = int(path.rsplit("/", 1)[1])
        return di.GhResult(0, json.dumps(data["linked"][number]), "")


@pytest.fixture
def declarations(tmp_path: Path) -> tuple[Path, Path]:
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({"repositories": {"website": ["npm"], "troupe": ["uv"],
                                                   ".github": []}}))  # fmt: skip
    milestones = tmp_path / "milestones.json"
    milestones.write_text(json.dumps({"milestones": [{"title": "0.1.0", "state": "open"}]}))
    return labels, milestones


ACTIONS = {"GITHUB_ACTIONS": "true"}


def test_outside_actions_it_writes_nothing_and_says_what_it_would_do(
    declarations: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    gh = FakeGitHub({"website": {"pulls": [just_changed(pull())]}, "troupe": {}})
    assert di.run(*declarations, {}, gh, NOW) == 0
    assert gh.writes == []
    out = capsys.readouterr().out
    assert "would open the issue “Update zod from 4.6.5 to 4.6.7” for #44" in out


def test_in_actions_a_new_pull_request_gets_its_issue_and_line(
    declarations: tuple[Path, Path], tmp_path: Path
) -> None:
    output = tmp_path / "output"
    gh = FakeGitHub({"website": {"pulls": [just_changed(pull())]}, "troupe": {}})
    assert di.run(*declarations, {**ACTIONS, "GITHUB_OUTPUT": str(output)}, gh, NOW) == 0
    (m1, p1, issue), (m2, p2, edit) = gh.writes
    assert (m1, p1) == ("POST", "repos/troupe-run/website/issues")
    assert issue["title"] == "Update zod from 4.6.5 to 4.6.7"
    assert issue["labels"] == ["dependencies"]
    assert issue["type"] == "Task"
    assert "milestone" not in issue  # a version update: website has no alert for zod here
    assert (m2, p2) == ("PATCH", "repos/troupe-run/website/pulls/44")
    assert edit["body"].endswith("\n\nCloses #501")
    assert output.read_text() == 'issue-urls=["https://github.com/troupe-run/website/issues/501"]\n'


def test_in_actions_nothing_to_do_writes_nothing(declarations: tuple[Path, Path]) -> None:
    p = pull()
    gh = FakeGitHub({"website": {"pulls": [lined(p, 100)], "issues": [app_issue(p)]}, "troupe": {}})
    assert di.run(*declarations, ACTIONS, gh, NOW) == 0
    assert gh.writes == []


def test_in_actions_relinking_retitles_and_comments(declarations: tuple[Path, Path]) -> None:
    old = pull()
    new = just_changed(pull(number=60, title="chore(deps): Bump zod from 4.6.5 to 4.6.8"))
    gh = FakeGitHub({"website": {"pulls": [new], "issues": [app_issue(old)],
                                 "linked": {44: closed(old, timedelta(minutes=5))}},
                     "troupe": {}})  # fmt: skip
    assert di.run(*declarations, ACTIONS, gh, NOW) == 0
    paths = [(m, p) for m, p, _ in gh.writes]
    assert paths == [
        ("PATCH", "repos/troupe-run/website/issues/100"),
        ("POST", "repos/troupe-run/website/issues/100/comments"),
        ("PATCH", "repos/troupe-run/website/pulls/60"),
    ]
    assert gh.writes[0][2]["title"] == "Update zod from 4.6.5 to 4.6.8"
    assert '"pull": 60' in gh.writes[0][2]["body"]
    assert "#44" in gh.writes[1][2]["body"]
    assert "#60" in gh.writes[1][2]["body"]


def test_in_actions_closing_as_not_planned_comments_then_closes(
    declarations: tuple[Path, Path],
) -> None:
    p = pull()
    gh = FakeGitHub({"website": {"issues": [app_issue(p)],
                                 "linked": {44: closed(p, timedelta(hours=2))}},
                     "troupe": {}})  # fmt: skip
    assert di.run(*declarations, ACTIONS, gh, NOW) == 0
    (_, c, said), (_, _i, state) = gh.writes
    assert c.endswith("/issues/100/comments")
    assert "#44" in said["body"]
    assert state == {"state": "closed", "state_reason": "not_planned"}


def test_a_repository_that_cant_be_read_is_left_alone_and_the_run_fails(
    declarations: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    gh = FakeGitHub(
        {"website": {"fail": True}, "troupe": {"pulls": [just_changed(pull("troupe-175"))]}}
    )
    assert di.run(*declarations, ACTIONS, gh, NOW) == 1
    assert [p for _, p, _ in gh.writes] == [
        "repos/troupe-run/troupe/issues",
        "repos/troupe-run/troupe/pulls/175",
    ]
    assert "troupe-run/website" in capsys.readouterr().err


def test_a_damaged_issue_fails_the_run_after_the_rest_is_handled(
    declarations: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    p = pull()
    damaged = app_issue(p, body="no marker")
    gh = FakeGitHub({"website": {"pulls": [lined(p, 100), just_changed(pull("website-55"))],
                                 "issues": [damaged]}, "troupe": {}})  # fmt: skip
    assert di.run(*declarations, ACTIONS, gh, NOW) == 1
    assert [path for _, path, _ in gh.writes] == [
        "repos/troupe-run/website/issues",
        "repos/troupe-run/website/pulls/55",
    ]
    err = capsys.readouterr().err
    assert "troupe-run/website" in err
    assert "#100" in err


def test_a_repository_without_the_milestone_gets_no_issue_and_the_run_fails(
    declarations: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    labels, milestones = declarations
    milestones.write_text(json.dumps({"milestones": [{"title": "9.9.9", "state": "open"}]}))
    gh = FakeGitHub({"website": {"pulls": [pull()]}, "troupe": {}})
    assert di.run(labels, milestones, ACTIONS, gh, NOW) == 1
    assert gh.writes == []
    assert "no open milestone titled 9.9.9" in capsys.readouterr().err


def test_no_release_in_progress_stops_before_any_read(
    declarations: tuple[Path, Path],
) -> None:
    labels, milestones = declarations
    milestones.write_text(json.dumps({"milestones": [{"title": "0.1.0", "state": "closed"}]}))
    gh = FakeGitHub({})
    calls: list[list[str]] = []

    def watching(args: list[str], stdin: str | None) -> di.GhResult:
        calls.append(args)
        return gh(args, stdin)

    assert di.run(labels, milestones, ACTIONS, watching, NOW) == 2
    assert calls == []


def test_pull_request_text_reaches_github_only_as_json_data(
    declarations: tuple[Path, Path],
) -> None:
    hostile = just_changed(
        pull(
            title='chore(deps): Bump zod from 4.6.5 to 4.6.7"; $(rm -rf /) ${{ x }}',
            body="`whoami` $(id) ${{ secrets.X }}",
        )
    )
    seen: list[tuple[list[str], str | None]] = []
    gh = FakeGitHub({"website": {"pulls": [hostile]}, "troupe": {}})

    def watching(args: list[str], stdin: str | None) -> di.GhResult:
        seen.append((copy.copy(args), stdin))
        return gh(args, stdin)

    di.run(*declarations, ACTIONS, watching, NOW)
    for args, _ in seen:
        assert not any("$(" in a or "whoami" in a for a in args)
    edit = next(
        json.loads(s or "{}") for a, s in seen if a[-3:-2] == ["repos/troupe-run/website/pulls/44"]
    )
    assert "`whoami` $(id) ${{ secrets.X }}" in edit["body"]


def test_in_actions_a_security_update_s_issue_is_in_the_release_in_progress(
    declarations: tuple[Path, Path],
) -> None:
    gh = FakeGitHub({"website": {"pulls": [just_changed(pull())], "alerts": ALERTS}, "troupe": {}})
    assert di.run(*declarations, ACTIONS, gh, NOW) == 0
    (_, path, issue), _edit = gh.writes
    assert path == "repos/troupe-run/website/issues"
    assert issue["milestone"] == 1  # website's number for 0.1.0


def test_in_actions_a_version_update_s_issue_has_no_milestone(
    declarations: tuple[Path, Path],
) -> None:
    gh = FakeGitHub({"website": {"pulls": [just_changed(pull("website-55"))], "alerts": ALERTS},
                     "troupe": {}})  # fmt: skip
    assert di.run(*declarations, ACTIONS, gh, NOW) == 0
    (_, path, issue), _edit = gh.writes
    assert path == "repos/troupe-run/website/issues"
    assert "milestone" not in issue


def test_alerts_that_can_t_be_read_open_no_issue_there_and_fail_the_run(
    declarations: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    gh = FakeGitHub({"website": {"pulls": [just_changed(pull())], "alerts-fail": True},
                     "troupe": {"pulls": [just_changed(pull("troupe-175"))]}})  # fmt: skip
    assert di.run(*declarations, ACTIONS, gh, NOW) == 1
    assert [p for _, p, _ in gh.writes] == [
        "repos/troupe-run/troupe/issues",
        "repos/troupe-run/troupe/pulls/175",
    ]
    err = capsys.readouterr().err
    assert "troupe-run/website" in err
    assert "dependabot/alerts" in err


def test_alerts_are_read_only_where_dependabot_has_a_pull_request_open(
    declarations: tuple[Path, Path],
) -> None:
    gh = FakeGitHub({"website": {"alerts-fail": True}, "troupe": {}})
    paths: list[str] = []

    def watching(args: list[str], stdin: str | None) -> di.GhResult:
        paths.append(args[-1])
        return gh(args, stdin)

    assert di.run(*declarations, ACTIONS, watching, NOW) == 0
    assert not any("/dependabot/alerts" in p for p in paths)


# Missed events (spec: dependency-updates, "A missed event is reported", "The missed-event tracking
# issue follows the misses"; dependabot-issues-on-events design D4, D5)


def stale(p: dict[str, Any], ago: timedelta) -> dict[str, Any]:
    return {**p, "updated_at": (NOW - ago).strftime("%Y-%m-%dT%H:%M:%SZ")}


def tracking(number: int = 7, missed: list[str] | None = None, **changes: Any) -> dict[str, Any]:  # noqa: ANN401
    """The tracking issue as the App would have opened it, in a real issue's shape."""
    loaded = dict(fixture("issue-website-21.json"))
    loaded.update(
        number=number,
        title=di.TRACKING_TITLE,
        state="open",
        state_reason=None,
        closed_at=None,
        user={"login": di.APP, "type": "Bot"},
        labels=[di.TRACKING_LABEL],
        body=di.tracking_report(missed or ["troupe-run/website#44"], "https://run/1"),
        html_url=f"https://github.com/troupe-run/infrastructure/issues/{number}",
    )
    loaded.update(changes)
    return loaded


def app_comment(body: str) -> dict[str, Any]:
    return {"user": {"login": di.APP, "type": "Bot"}, "body": body}


def test_a_line_missing_for_over_an_hour_is_a_miss() -> None:
    p = stale(pull(), timedelta(hours=3))
    decided = di.plan([p], [app_issue(p)], {}, NOW)
    assert di.misses("website", decided, NOW) == ["troupe-run/website#44"]


def test_an_issue_missing_for_over_an_hour_is_a_miss() -> None:
    decided = di.plan([stale(pull(), timedelta(hours=2))], [], {}, NOW)
    assert kinds(decided) == [("open", 44, None)]
    assert di.misses("website", decided, NOW) == ["troupe-run/website#44"]


def test_a_superseding_pull_request_left_unlinked_is_a_miss() -> None:
    old = pull()
    new = stale(
        pull(number=60, title="chore(deps): Bump zod from 4.6.5 to 4.6.8"), timedelta(hours=2)
    )
    decided = di.plan([new], [app_issue(old)], {44: closed(old, timedelta(hours=2))}, NOW)
    assert di.misses("website", decided, NOW) == ["troupe-run/website#60"]


def test_a_pull_request_changed_within_the_hour_is_fixed_but_not_a_miss() -> None:
    p = stale(pull(), timedelta(minutes=10))
    decided = di.plan([p], [app_issue(p)], {}, NOW)
    assert kinds(decided) == [("line", 44, 100)]
    assert di.misses("website", decided, NOW) == []


def test_work_only_time_or_a_person_makes_due_is_not_a_miss() -> None:
    merged, gone = pull(), pull("website-55")
    issues = [app_issue(merged, 100), app_issue(gone, 101)]
    linked = {
        44: closed(merged, timedelta(days=1), merged=True),
        55: closed(gone, timedelta(hours=5)),
    }
    decided = di.plan([], issues, linked, NOW)
    assert kinds(decided) == [("close-completed", 44, 100), ("close-not-planned", 55, 101)]
    assert di.misses("website", decided, NOW) == []


def test_a_pull_request_a_person_reopened_is_not_a_miss() -> None:
    p = stale(pull(), timedelta(hours=3))
    issue = app_issue(p, state="closed", state_reason="not_planned")
    decided = di.plan([p], [issue], {}, NOW)
    assert kinds(decided) == [("reopen", 44, 100), ("line", 44, 100)]
    assert di.misses("website", decided, NOW) == []


def test_the_tracking_issue_is_never_taken_for_an_update_s_issue() -> None:
    assert not di.is_app_issue(tracking())


def test_the_tracking_issue_names_each_miss_and_its_marker_reads_back() -> None:
    missed = ["troupe-run/troupe#175", "troupe-run/website#44"]
    issue = tracking(missed=missed)
    assert "- troupe-run/website#44" in issue["body"]
    assert "https://run/1" in issue["body"]
    assert di.last_reported(issue, []) == missed


def test_the_newest_report_is_the_last_one() -> None:
    issue = tracking(missed=["troupe-run/website#44"])
    later = app_comment(di.tracking_report(["troupe-run/website#55"], "https://run/2"))
    someone = {
        "user": {"login": "someone", "type": "User"},
        "body": di.tracking_report(["x#1"], "r"),
    }
    assert di.last_reported(issue, [later, someone]) == ["troupe-run/website#55"]


@pytest.mark.parametrize(
    ("missed", "has_issue", "last", "may_close", "action"),
    [
        (["a#1"], False, None, True, "open"),
        (["a#1"], True, ["a#1"], True, "none"),
        (["a#1", "a#2"], True, ["a#1"], True, "comment"),
        ([], True, ["a#1"], True, "close"),
        ([], True, ["a#1"], False, "none"),
        ([], False, None, True, "none"),
    ],
)
def test_the_tracking_issue_follows_the_misses(
    missed: list[str], has_issue: bool, last: list[str] | None, may_close: bool, action: str
) -> None:
    issue = tracking() if has_issue else None
    assert di.decide_tracking(missed, issue, last, may_close) == action


def test_someone_else_s_issue_with_the_tracking_title_is_ignored() -> None:
    person = tracking(user={"login": "someone", "type": "User"})
    assert di.tracking_issues([person]) == []


def test_two_tracking_issues_update_the_oldest() -> None:
    assert [i["number"] for i in di.tracking_issues([tracking(9), tracking(7)])] == [7, 9]


RUN_ENV = {**ACTIONS, "GITHUB_SERVER_URL": "https://github.com",
           "GITHUB_REPOSITORY": "troupe-run/infrastructure", "GITHUB_RUN_ID": "42",
           "GITHUB_EVENT_NAME": "workflow_run"}  # fmt: skip
DAILY_ENV = {**RUN_ENV, "GITHUB_EVENT_NAME": "schedule"}
RUN_URL = "https://github.com/troupe-run/infrastructure/actions/runs/42"


def test_a_run_dependabot_s_change_started_reports_no_miss(
    declarations: tuple[Path, Path],
) -> None:
    """The pull request it was started for changed minutes ago, so it isn't late (design D4)."""
    gh = FakeGitHub({"website": {"pulls": [just_changed(pull())]}, "troupe": {}})
    assert di.run(*declarations, RUN_ENV, gh, NOW) == 0
    assert all("infrastructure" not in path for _, path, _ in gh.writes)


def test_any_run_fixes_a_miss_first_then_opens_the_tracking_issue_and_fails(
    declarations: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "output"
    p = stale(pull(), timedelta(hours=3))
    gh = FakeGitHub({"website": {"pulls": [p], "issues": [app_issue(p)]}, "troupe": {},
                     "infrastructure": {}})  # fmt: skip
    env = {**RUN_ENV, "GITHUB_OUTPUT": str(output)}
    assert di.run(*declarations, env, gh, NOW) == 1
    (_, line, _), (method, path, opened) = gh.writes
    assert line == "repos/troupe-run/website/pulls/44"
    assert (method, path) == ("POST", "repos/troupe-run/infrastructure/issues")
    assert opened["title"] == "Dependabot events missed"
    assert opened["labels"] == ["bug"]
    assert "- troupe-run/website#44" in opened["body"]
    assert RUN_URL in opened["body"]
    assert "troupe-run/website#44" in capsys.readouterr().err
    urls = json.loads(output.read_text().removeprefix("issue-urls="))
    assert "https://github.com/troupe-run/infrastructure/issues/501" in urls


def test_the_same_misses_add_no_comment(declarations: tuple[Path, Path]) -> None:
    p = stale(pull(), timedelta(hours=3))
    reported = tracking(missed=["troupe-run/website#44"])
    gh = FakeGitHub({"website": {"pulls": [p], "issues": [app_issue(p)]}, "troupe": {},
                     "infrastructure": {"issues": [reported]}})  # fmt: skip
    assert di.run(*declarations, RUN_ENV, gh, NOW) == 1
    assert [path for _, path, _ in gh.writes] == ["repos/troupe-run/website/pulls/44"]


def test_new_misses_comment(declarations: tuple[Path, Path]) -> None:
    p = stale(pull(), timedelta(hours=3))
    reported = tracking(missed=["troupe-run/troupe#175"])
    gh = FakeGitHub({"website": {"pulls": [p], "issues": [app_issue(p)]}, "troupe": {},
                     "infrastructure": {"issues": [reported]}})  # fmt: skip
    assert di.run(*declarations, RUN_ENV, gh, NOW) == 1
    method, path, said = gh.writes[-1]
    assert (method, path) == ("POST", "repos/troupe-run/infrastructure/issues/7/comments")
    assert "- troupe-run/website#44" in said["body"]


def test_a_clean_daily_run_closes_the_tracking_issue_and_succeeds(
    declarations: tuple[Path, Path], tmp_path: Path
) -> None:
    output = tmp_path / "output"
    p = pull()
    gh = FakeGitHub({"website": {"pulls": [lined(p, 100)], "issues": [app_issue(p)]},
                     "troupe": {}, "infrastructure": {"issues": [tracking()]}})  # fmt: skip
    env = {**DAILY_ENV, "GITHUB_OUTPUT": str(output)}
    assert di.run(*declarations, env, gh, NOW) == 0
    (_, c, said), (method, path, state) = gh.writes
    assert c == "repos/troupe-run/infrastructure/issues/7/comments"
    assert RUN_URL in said["body"]
    assert (method, path) == ("PATCH", "repos/troupe-run/infrastructure/issues/7")
    assert state == {"state": "closed", "state_reason": "completed"}
    assert "infrastructure/issues/7" not in output.read_text()


def test_a_clean_event_run_leaves_the_tracking_issue_open(
    declarations: tuple[Path, Path], tmp_path: Path
) -> None:
    """Minutes after a miss, the next run finds it fixed. The cause may still be there, so only the
    daily run closes the issue (design D5)."""
    output = tmp_path / "output"
    p = pull()
    gh = FakeGitHub({"website": {"pulls": [lined(p, 100)], "issues": [app_issue(p)]},
                     "troupe": {}, "infrastructure": {"issues": [tracking()]}})  # fmt: skip
    assert di.run(*declarations, {**RUN_ENV, "GITHUB_OUTPUT": str(output)}, gh, NOW) == 0
    assert gh.writes == []
    assert "https://github.com/troupe-run/infrastructure/issues/7" in output.read_text()


def test_a_daily_run_that_couldn_t_read_a_repository_leaves_the_tracking_issue_open(
    declarations: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    gh = FakeGitHub({"website": {"fail": True}, "troupe": {},
                     "infrastructure": {"issues": [tracking()]}})  # fmt: skip
    assert di.run(*declarations, DAILY_ENV, gh, NOW) == 1
    assert gh.writes == []
    assert "troupe-run/website" in capsys.readouterr().err


def test_misses_and_a_failed_repository_are_both_named(
    declarations: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    p = stale(pull("troupe-175"), timedelta(hours=3))
    gh = FakeGitHub({"website": {"fail": True}, "troupe": {"pulls": [p]}, "infrastructure": {}})
    assert di.run(*declarations, RUN_ENV, gh, NOW) == 1
    err = capsys.readouterr().err
    assert "missed events, handled now: troupe-run/troupe#175" in err
    assert "couldn't handle website" in err


def test_a_tracking_issue_that_can_t_be_read_fails_the_run_after_the_fixes(
    declarations: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    p = stale(pull(), timedelta(hours=3))
    gh = FakeGitHub({"website": {"pulls": [p], "issues": [app_issue(p)]}, "troupe": {},
                     "infrastructure": {"fail": True}})  # fmt: skip
    assert di.run(*declarations, RUN_ENV, gh, NOW) == 1
    assert [path for _, path, _ in gh.writes] == ["repos/troupe-run/website/pulls/44"]
    assert "couldn't read the tracking issue" in capsys.readouterr().err


def test_outside_actions_a_miss_only_says_what_it_would_do(
    declarations: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    p = stale(pull(), timedelta(hours=3))
    gh = FakeGitHub({"website": {"pulls": [p], "issues": [app_issue(p)]}, "troupe": {},
                     "infrastructure": {}})  # fmt: skip
    assert di.run(*declarations, {}, gh, NOW) == 1
    assert gh.writes == []
    assert "would open the tracking issue" in capsys.readouterr().out
