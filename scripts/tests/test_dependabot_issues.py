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
        ("troupe-175", "uv", "/", "uv-build", "<0.14,>=0.13.0", ">=0.13.2,<0.14", "unknown"),
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


# The run, against a fake GitHub (design D2, D8)


class FakeGitHub:
    """Answers the reads from per-repository data, and records every write."""

    def __init__(self, data: dict[str, dict[str, Any]]) -> None:
        self.data = data
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
        if "/pulls?" in path:
            return di.GhResult(0, json.dumps([data.get("pulls", [])]), "")
        if "/issues?" in path:
            state = "open" if "state=open" in path else "closed"
            found = [i for i in data.get("issues", []) if i["state"] == state]
            return di.GhResult(0, json.dumps([found]), "")
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
    gh = FakeGitHub({"website": {"pulls": [pull()]}, "troupe": {}})
    assert di.run(*declarations, {}, gh, NOW) == 0
    assert gh.writes == []
    out = capsys.readouterr().out
    assert "would open the issue “Update zod from 4.6.5 to 4.6.7” for #44" in out


def test_in_actions_a_new_pull_request_gets_its_issue_and_line(
    declarations: tuple[Path, Path], tmp_path: Path
) -> None:
    output = tmp_path / "output"
    gh = FakeGitHub({"website": {"pulls": [pull()]}, "troupe": {}})
    assert di.run(*declarations, {**ACTIONS, "GITHUB_OUTPUT": str(output)}, gh, NOW) == 0
    (m1, p1, issue), (m2, p2, edit) = gh.writes
    assert (m1, p1) == ("POST", "repos/troupe-run/website/issues")
    assert issue["title"] == "Update zod from 4.6.5 to 4.6.7"
    assert issue["labels"] == ["dependencies"]
    assert issue["type"] == "Task"
    assert issue["milestone"] == 1  # website's number for 0.1.0
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
    new = pull(number=60, title="chore(deps): Bump zod from 4.6.5 to 4.6.8")
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
    gh = FakeGitHub({"website": {"fail": True}, "troupe": {"pulls": [pull("troupe-175")]}})
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
    gh = FakeGitHub({"website": {"pulls": [lined(p, 100), pull("website-55")],
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
    hostile = pull(title='chore(deps): Bump zod from 4.6.5 to 4.6.7"; $(rm -rf /) ${{ x }}',
                   body="`whoami` $(id) ${{ secrets.X }}")  # fmt: skip
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
