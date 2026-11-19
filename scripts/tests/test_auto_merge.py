"""The safe-PR rule's conditions and what the evaluator does with them (spec: auto-merge;
auto-merge design D2-D6, D12).

Every test starts from troupe-run/troupe#467 as GitHub answered for it on 2026-11-19
(fixtures/auto_merge, provenance.json), made open and mergeable, with a review result recorded for
its head in the shape claude-review.yml writes. Each test then changes the one answer its scenario
is about. A read the fixture doesn't hold fails the test, so none can depend on an answer it didn't
record.
"""

import copy
import io
import json
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import auto_merge as am

# Every test judges with the committed auto-merge.toml's rules.
pytestmark = pytest.mark.auto_merge

FIXTURES = Path(__file__).parent / "fixtures" / "auto_merge"
REPO = "troupe-run/troupe"
NUMBER = 467
HEAD = "d61dfd0e515b169b9a1e180f5f525dcd249a695a"
EARLIER = "9197f01c759670249284d547e72059b7d906da9a"
AUTHOR = "martin-at-hpsgd"
GRAPHQL = 'GRAPHQL {"after": null, "name": "troupe", "number": 467, "owner": "troupe-run"}'
COMMITS = f"GET repos/{REPO}/pulls/{NUMBER}/commits?per_page=100&page=1"
FILES = f"GET repos/{REPO}/pulls/{NUMBER}/files?per_page=100&page=1"
COMMENTS = f"GET repos/{REPO}/issues/{NUMBER}/comments?per_page=100&page=1"
CHECK_RUNS = f"GET repos/{REPO}/commits/{HEAD}/check-runs?per_page=100&page=1"
RUNS = f"GET repos/{REPO}/actions/runs?head_sha={HEAD}&event=pull_request&per_page=100&page=1"
ISSUE = f"GET repos/{REPO}/issues/442"
BLOCKED = f"GET repos/{REPO}/issues/442/dependencies/blocked_by?per_page=100&page=1"
VARIABLE = {
    repository: f"GET repos/troupe-run/{repository}/actions/variables/AUTO_MERGE"
    for repository in am.REPOSITORIES
}
OPEN_PRS = {
    repository: f"GET repos/troupe-run/{repository}/pulls?state=open&per_page=100&page=1"
    for repository in am.REPOSITORIES
}
RULES = am.read_config(Path(__file__).resolve().parents[2]).repositories["troupe"]


def review_runs(sha: str) -> str:
    return (
        f"GET repos/{REPO}/actions/workflows/claude-review.yml/runs?head_sha={sha}"
        "&event=pull_request&per_page=100&page=1"
    )


def zipped(result: Mapping[str, object]) -> dict[str, str]:
    import base64

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("review-result.json", json.dumps(result))
    return {"__base64__": base64.b64encode(buffer.getvalue()).decode()}


def record_review(tape: dict[str, Any], sha: str, coverage: str, artifact_id: int) -> None:
    """Give ``sha``'s newest review run a review-result artifact saying ``coverage``."""
    runs = tape[review_runs(sha)]["workflow_runs"]
    newest = max(runs, key=lambda run: run["id"])
    key = f"GET repos/{REPO}/actions/runs/{newest['id']}/artifacts"
    tape[key]["artifacts"].append({"id": artifact_id, "name": "review-result"})
    tape[f"RAW repos/{REPO}/actions/artifacts/{artifact_id}/zip"] = zipped(
        {"head": sha, "coverage": coverage, "code": "all"}
    )


@pytest.fixture(scope="module")
def recorded() -> dict[str, Any]:
    tape: dict[str, Any] = json.loads((FIXTURES / "troupe-467.json").read_text(encoding="utf-8"))
    return tape


@pytest.fixture
def tape(recorded: dict[str, Any]) -> dict[str, Any]:
    """#467, open and mergeable, with a complete review recorded for its head."""
    tape = copy.deepcopy(recorded)
    pull = tape[GRAPHQL]["repository"]["pullRequest"]
    pull.update(state="OPEN", mergeable="MERGEABLE", mergeQueueEntry=None, isDraft=False)
    record_review(tape, HEAD, "complete", 9001)
    return tape


def pull(tape: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = tape[GRAPHQL]["repository"]["pullRequest"]
    return result


def judged(
    tape: Mapping[str, object], measure: tuple[int, int] = (0, 0)
) -> tuple[am.Verdict, am.Replay]:
    replay = am.Replay(tape)
    pr = am.PullRequest(replay, "troupe", NUMBER, RULES, lambda _: measure)
    return am.judge(pr), replay


def failed(tape: Mapping[str, object], measure: tuple[int, int] = (0, 0)) -> am.Check:
    verdict, _ = judged(tape, measure)
    assert verdict.error is None, verdict.error
    assert not verdict.qualified
    return verdict.checks[-1]


def errored(tape: Mapping[str, object]) -> str:
    verdict, _ = judged(tape)
    assert not verdict.qualified
    assert verdict.error is not None
    return verdict.error


# --- Everything holds -----------------------------------------------------------------------------


def test_the_recorded_pull_request_qualifies_when_open_with_a_complete_review(
    tape: dict[str, Any],
) -> None:
    verdict, replay = judged(tape)
    assert verdict.error is None, verdict.error
    assert verdict.qualified, verdict.line()
    assert [check.name for check in verdict.checks] == [
        "ready", "queued once per head", "required checks", "conversations", "commits",
        "pushed by the author", "archived", "closed issues", "protected", "size", "review",
    ]  # fmt: skip
    assert replay.writes == []


# --- Only a ready pull request from the same repository qualifies --------------------------------


@pytest.mark.parametrize(
    ("change", "said"),
    [
        ({"isDraft": True}, "it's a draft"),
        (
            {"headRepository": {"nameWithOwner": "someone/troupe"}},
            "its branch is in someone/troupe",
        ),
        ({"headRepository": None}, "a deleted fork"),
        ({"mergeable": "CONFLICTING"}, "it conflicts with main"),
        ({"mergeable": "UNKNOWN"}, "hasn't worked out yet"),
        ({"baseRefName": "next"}, "it targets next"),
        ({"state": "CLOSED"}, "it's closed"),
        ({"labels": {"nodes": [{"name": "hold"}]}}, "the `hold` label"),
    ],
)
def test_a_pull_request_that_isnt_ready_isnt_queued(
    tape: dict[str, Any], change: dict[str, object], said: str
) -> None:
    pull(tape).update(change)
    check = failed(tape)
    assert check.name == "ready"
    assert said in check.saw


# --- Every required check is green on the head ----------------------------------------------------


def _check_run(tape: dict[str, Any], name: str) -> dict[str, Any]:
    run: dict[str, Any] = next(r for r in tape[CHECK_RUNS]["check_runs"] if r["name"] == name)
    return run


def test_a_failed_required_check_isnt_queued(tape: dict[str, Any]) -> None:
    _check_run(tape, "check")["conclusion"] = "failure"
    check = failed(tape)
    assert check.name == "required checks"
    assert "check failure" in check.saw


def test_a_required_check_still_running_isnt_queued_yet(tape: dict[str, Any]) -> None:
    run = _check_run(tape, "guard (workflow rules)")
    run.update(status="in_progress", conclusion=None)
    assert "guard (workflow rules) is still in_progress" in failed(tape).saw


def test_a_skipped_required_check_counts_as_passed(tape: dict[str, Any]) -> None:
    _check_run(tape, "check")["conclusion"] = "skipped"
    verdict, _ = judged(tape)
    assert verdict.qualified, verdict.line()


def test_a_required_check_that_never_reported_isnt_queued(tape: dict[str, Any]) -> None:
    runs = tape[CHECK_RUNS]["check_runs"]
    tape[CHECK_RUNS]["check_runs"] = [r for r in runs if r["name"] != "DCO"]
    assert "DCO hasn't reported" in failed(tape).saw


def test_the_newest_run_of_a_check_decides(tape: dict[str, Any]) -> None:
    old = copy.deepcopy(_check_run(tape, "check"))
    old.update(id=1, conclusion="failure")
    tape[CHECK_RUNS]["check_runs"].append(old)
    verdict, _ = judged(tape)
    assert verdict.qualified, verdict.line()


# --- No conversation is open and no change is requested -------------------------------------------


def test_an_open_conversation_isnt_queued(tape: dict[str, Any]) -> None:
    pull(tape)["reviewThreads"]["nodes"] = [{"isResolved": True}, {"isResolved": False}]
    check = failed(tape)
    assert check.name == "conversations"
    assert "1 conversation(s) open" in check.saw


def test_a_review_requesting_changes_isnt_queued(tape: dict[str, Any]) -> None:
    pull(tape)["reviewDecision"] = "CHANGES_REQUESTED"
    assert "requests changes" in failed(tape).saw


def test_conversations_past_the_first_page_are_read(tape: dict[str, Any]) -> None:
    pull(tape)["reviewThreads"] = {
        "nodes": [{"isResolved": True}] * 100,
        "pageInfo": {"hasNextPage": True, "endCursor": "CURSOR"},
    }
    second = copy.deepcopy(tape[GRAPHQL])
    second["repository"]["pullRequest"]["reviewThreads"] = {
        "nodes": [{"isResolved": False}],
        "pageInfo": {"hasNextPage": False, "endCursor": None},
    }
    tape[GRAPHQL.replace('"after": null', '"after": "CURSOR"')] = second
    assert "1 conversation(s) open" in failed(tape).saw


# --- Every commit is signed off, a person's, and the head was pushed by the author ---------------


def test_a_commit_without_sign_off_isnt_queued(tape: dict[str, Any]) -> None:
    tape[COMMITS][0]["commit"]["message"] = "feat: x\n\nNo trailer here."
    check = failed(tape)
    assert check.name == "commits"
    assert "has no Signed-off-by" in check.saw


def test_a_commit_committed_by_the_merge_app_isnt_queued(tape: dict[str, Any]) -> None:
    commit = tape[COMMITS][-1]
    commit["committer"] = {"login": "troupe-run-merge[bot]", "type": "Bot"}
    commit["commit"]["committer"]["email"] = (
        "5832075+troupe-run-merge[bot]@users.noreply.github.com"
    )
    check = failed(tape)
    assert check.name == "commits"
    assert "committer is a bot (troupe-run-merge[bot])" in check.saw


def test_a_commit_by_a_bot_account_with_an_ordinary_email_isnt_queued(tape: dict[str, Any]) -> None:
    """An App writing through the API may give any email: its account's type still tells."""
    tape[COMMITS][0]["author"] = {"login": "troupe-run-merge[bot]", "type": "Bot"}
    assert "author is a bot (troupe-run-merge[bot])" in failed(tape).saw


def test_a_commit_authored_by_another_bot_isnt_queued(tape: dict[str, Any]) -> None:
    commit = tape[COMMITS][0]
    commit["author"] = None
    commit["commit"]["author"]["email"] = "49699333+dependabot[bot]@users.noreply.github.com"
    assert "author is a bot" in failed(tape).saw


def test_a_commit_whose_author_cant_be_read_isnt_queued(tape: dict[str, Any]) -> None:
    commit = tape[COMMITS][0]
    commit["author"] = None
    commit["commit"]["author"] = None
    assert "author can't be read" in failed(tape).saw


def test_a_head_pushed_by_someone_else_isnt_queued(tape: dict[str, Any]) -> None:
    tape[RUNS]["workflow_runs"][0]["actor"] = {"login": "troupe-run-merge[bot]"}
    check = failed(tape)
    assert check.name == "pushed by the author"
    assert "troupe-run-merge[bot]" in check.saw


def test_a_run_triggered_by_someone_else_isnt_queued(tape: dict[str, Any]) -> None:
    tape[RUNS]["workflow_runs"][-1]["triggering_actor"] = {"login": "someone-else"}
    assert "someone-else" in failed(tape).saw


def test_a_head_with_no_pull_request_run_isnt_queued(tape: dict[str, Any]) -> None:
    tape[RUNS] = {"total_count": 0, "workflow_runs": []}
    assert "who pushed it can't be read" in failed(tape).saw


def test_runs_that_cant_be_listed_are_an_error(tape: dict[str, Any]) -> None:
    tape[RUNS] = {"__error__": "gh api failed: HTTP 502"}
    assert "502" in errored(tape)


def test_a_change_not_yet_archived_isnt_queued(tape: dict[str, Any]) -> None:
    key = f"GET repos/{REPO}/contents/openspec/changes/empty-fan-out?ref={HEAD}"
    tape[key] = [{"name": "proposal.md"}]
    check = failed(tape)
    assert check.name == "archived"
    assert "openspec/changes/empty-fan-out/ is still there" in check.saw


# --- The issues it closes are neither decisions nor blocked ---------------------------------------


def test_closing_a_decision_isnt_queued(tape: dict[str, Any]) -> None:
    tape[ISSUE]["type"] = {"name": "Decision"}
    check = failed(tape)
    assert check.name == "closed issues"
    assert "troupe-run/troupe#442 is a Decision" in check.saw


def test_closing_an_issue_waiting_on_the_owner_isnt_queued(tape: dict[str, Any]) -> None:
    tape[ISSUE]["labels"] = [{"name": "needs:owner"}]
    assert "labelled needs:owner" in failed(tape).saw


def test_closing_a_blocked_issue_isnt_queued(tape: dict[str, Any]) -> None:
    tape[BLOCKED] = [
        {"number": 272, "state": "open",
         "repository_url": "https://api.github.com/repos/troupe-run/infrastructure"}
    ]  # fmt: skip
    assert "blocked by troupe-run/infrastructure#272" in failed(tape).saw


def test_a_blocked_by_list_that_cant_be_read_is_an_error(tape: dict[str, Any]) -> None:
    tape[BLOCKED] = {"__error__": "HTTP 403"}
    assert "couldn't read what blocks troupe-run/troupe#442" in errored(tape)


def test_an_issue_only_github_links_as_closing_is_judged_too(tape: dict[str, Any]) -> None:
    pull(tape)["closingIssuesReferences"]["nodes"].append(
        {"number": 7, "repository": {"nameWithOwner": "troupe-run/website"}}
    )
    tape["GET repos/troupe-run/website/issues/7"] = {"type": {"name": "Decision"}, "labels": []}
    tape["GET repos/troupe-run/website/issues/7/dependencies/blocked_by?per_page=100&page=1"] = []
    assert "troupe-run/website#7 is a Decision" in failed(tape).saw


# --- Nothing protected changes, within the limits ------------------------------------------------


def _file(tape: dict[str, Any], **fields: object) -> None:
    tape[FILES].append({"additions": 1, "deletions": 0, "status": "modified", **fields})
    pull(tape)["changedFiles"] = len(tape[FILES])


@pytest.mark.parametrize(
    ("path", "status"),
    [
        (".github/workflows/ci.yml", "modified"),
        ("packages/troupe/src/troupe/core/masking.py", "modified"),
        ("packages/troupe-plugin-sdk/src/troupe_plugin_sdk/credential.py", "modified"),
        ("scripts/guard.py", "modified"),
        ("scripts/mutation_run.py", "modified"),  # delivered, named by guard-delivery.json
        ("plugins/runner-foo/pyproject.toml", "removed"),
        ("openspec/specs/runs/spec.md", "removed"),
    ],
)
def test_a_protected_change_isnt_queued(tape: dict[str, Any], path: str, status: str) -> None:
    _file(tape, filename=path, status=status)
    check = failed(tape)
    assert check.name == "protected"
    assert path in check.saw


def test_a_rename_out_of_a_protected_path_is_protected(tape: dict[str, Any]) -> None:
    _file(tape, filename="src/x.py", previous_filename="scripts/guard.py", status="renamed")
    assert "scripts/guard.py" in failed(tape).saw


def test_too_many_lines_isnt_queued(tape: dict[str, Any]) -> None:
    _file(tape, filename="packages/troupe/src/troupe/big.py", additions=1200)
    check = failed(tape)
    assert check.name == "size"
    assert "lines 1236 > 800" in check.saw


def test_lock_files_fixtures_and_prose_dont_count_toward_lines(tape: dict[str, Any]) -> None:
    _file(tape, filename="uv.lock", additions=3000)
    _file(tape, filename="plugins/x/fixtures/run/recording.jsonl", additions=5000)
    _file(tape, filename="openspec/changes/x/design.md", additions=600)
    verdict, _ = judged(tape)
    assert verdict.qualified, verdict.line()
    assert "lines 36/800" in verdict.checks[-2].saw


def test_too_many_files_isnt_queued_but_generated_files_dont_count(tape: dict[str, Any]) -> None:
    for index in range(40):
        _file(tape, filename=f"plugins/p{index}/uv.lock")
    verdict, _ = judged(tape)
    assert verdict.qualified, verdict.line()
    for index in range(26):
        _file(tape, filename=f"docs/page{index}.md")
    assert "files 31 > 30" in failed(tape).saw


def test_one_complex_function_isnt_queued(tape: dict[str, Any]) -> None:
    check = failed(tape, measure=(18, 18))
    assert "max complexity 18 > 15" in check.saw


def test_too_much_added_complexity_isnt_queued(tape: dict[str, Any]) -> None:
    assert "complexity increase 41 > 40" in failed(tape, measure=(10, 41)).saw


def test_a_file_list_github_cut_short_is_an_error(tape: dict[str, Any]) -> None:
    pull(tape)["changedFiles"] = 3500
    assert "3,000" in errored(tape)


# --- Claude's review read everything ------------------------------------------------------------


def test_coverage_at_the_floor_only_isnt_queued(tape: dict[str, Any]) -> None:
    tape[f"RAW repos/{REPO}/actions/artifacts/9001/zip"] = zipped(
        {"head": HEAD, "coverage": "incomplete", "code": "all"}
    )
    tape[f"GET repos/{REPO}/commits/{HEAD}"]["files"] = [{"filename": "src/x.py"}]
    check = failed(tape)
    assert check.name == "review"
    assert "coverage incomplete" in check.saw


def test_an_earlier_complete_review_counts_past_openspec_only_commits(
    recorded: dict[str, Any],
) -> None:
    """#467's head changes only openspec/ (its archive), so its first commit's review counts."""
    tape = copy.deepcopy(recorded)
    pull(tape).update(state="OPEN", mergeable="MERGEABLE")
    record_review(tape, EARLIER, "complete", 9002)
    verdict, _ = judged(tape)
    assert verdict.qualified, verdict.line()
    assert "carried past openspec/-only commits" in verdict.checks[-1].saw


def test_a_code_commit_after_the_complete_review_stops_the_carry(recorded: dict[str, Any]) -> None:
    tape = copy.deepcopy(recorded)
    pull(tape).update(state="OPEN", mergeable="MERGEABLE")
    record_review(tape, EARLIER, "complete", 9002)
    tape[f"GET repos/{REPO}/commits/{HEAD}"]["files"] = [{"filename": "scripts/auto_merge.py"}]
    check = failed(tape)
    assert check.name == "review"
    assert f"the review of {HEAD[:7]}" in check.saw


def test_no_review_result_isnt_queued(recorded: dict[str, Any]) -> None:
    tape = copy.deepcopy(recorded)
    pull(tape).update(state="OPEN", mergeable="MERGEABLE")
    assert "no result recorded" in failed(tape).saw


def test_a_review_result_for_another_head_doesnt_count(tape: dict[str, Any]) -> None:
    tape[f"RAW repos/{REPO}/actions/artifacts/9001/zip"] = zipped(
        {"head": EARLIER, "coverage": "complete", "code": "all"}
    )
    tape[f"GET repos/{REPO}/commits/{HEAD}"]["files"] = [{"filename": "src/x.py"}]
    assert failed(tape).name == "review"


# --- Acting: the switch, the markers, the queueing, the hold (design D5) ------------------------


def everything(tape: dict[str, Any], switches: Mapping[str, object]) -> dict[str, Any]:
    """The tape, plus each repository's switch and open pull requests: #467 in troupe only."""
    tape = copy.deepcopy(tape)
    for repository in am.REPOSITORIES:
        value = switches.get(repository)
        tape[VARIABLE[repository]] = {"__status__": 404} if value is None else {"value": value}
        tape[OPEN_PRS[repository]] = [{"number": NUMBER}] if repository == "troupe" else []
    return tape


def text(write: Mapping[str, object]) -> str:
    """A recorded comment write's text."""
    body = write["body"]
    assert isinstance(body, dict)
    return str(body["body"])


def run(tape: Mapping[str, object]) -> tuple[int, list[str], am.Replay]:
    replay = am.Replay(tape)
    lines: list[str] = []
    config = am.read_config(Path(__file__).resolve().parents[2])
    status = am.run(replay, config, lambda _: (0, 0), lines.append)
    return status, lines, replay


def test_on_queues_with_the_judged_head_after_writing_the_record(tape: dict[str, Any]) -> None:
    status, lines, replay = run(everything(tape, {"troupe": "on"}))
    assert status == 0
    assert "  - #467: queued" in lines
    comment, enqueue, label = replay.writes
    assert comment["path"] == f"repos/{REPO}/issues/{NUMBER}/comments"
    assert text(comment).startswith(f"<!-- auto-merge:queued {HEAD} -->")
    assert enqueue == {
        "graphql": "enqueuePullRequest",
        "variables": {"id": pull(tape)["id"], "head": HEAD},
    }
    assert label == {"method": "POST", "path": f"repos/{REPO}/issues/{NUMBER}/labels",
                     "body": {"labels": ["auto-merged"]}}  # fmt: skip


def test_the_record_says_what_each_condition_saw(tape: dict[str, Any]) -> None:
    _, _, replay = run(everything(tape, {"troupe": "on"}))
    body = text(replay.writes[0])
    assert f"**Queued by auto-merge** at `{HEAD}`, under the safe-PR rule v1 (#319)." in body
    for name in ("check", "DCO", "guard (workflow rules)", "claude review completed"):
        newest = max(
            (r for r in tape[CHECK_RUNS]["check_runs"] if r["name"] == name), key=lambda r: r["id"]
        )
        assert f"[{name}]({newest['html_url']})" in body, name
    assert "| required checks | all 4 green on d61dfd0: [check](https://github.com/" in body
    for line in (
        "| closed issues | no Decision, no needs:owner, nothing blocked: troupe-run/troupe#442 |",
        "| size | lines 36/800, files 5/30, max complexity 0/15, increase 0/40 |",
        "| review | coverage complete on d61dfd0 |",
    ):
        assert line in body
    assert "add the `hold` label" in body


@pytest.mark.parametrize("unset", [None, "off"])
def test_off_or_unset_does_nothing(tape: dict[str, Any], unset: str | None) -> None:
    status, lines, replay = run(everything(tape, {"troupe": unset}))
    assert status == 0
    assert replay.writes == []
    assert "- troupe-run/troupe: AUTO_MERGE is off, so nothing is judged" in lines


def test_a_bad_switch_value_is_an_error_and_does_nothing_there(tape: dict[str, Any]) -> None:
    status, lines, replay = run(everything(tape, {"troupe": "yes", "website": "on"}))
    assert status == 1
    assert replay.writes == []
    assert any("'yes'" in line and "off, dry-run, on" in line for line in lines)
    assert "- troupe-run/website (on): 0 open pull request(s)" in lines


def test_dry_run_comments_once_per_head_and_queues_nothing(tape: dict[str, Any]) -> None:
    _, lines, replay = run(everything(tape, {"troupe": "dry-run"}))
    (comment,) = replay.writes
    body = text(comment)
    assert body.startswith(f"<!-- auto-merge:dry-run {HEAD} -->")
    assert "**Auto-merge would have queued this**" in body
    assert "  - #467: qualifies (dry-run): commented" in lines

    again = everything(tape, {"troupe": "dry-run"})
    again[COMMENTS].append({"user": {"login": am.APP_LOGIN}, "body": body})
    _, lines, replay = run(again)
    assert replay.writes == []
    assert "  - #467: qualifies (dry-run; already commented on this head)" in lines


def test_dry_run_comments_again_for_a_new_head(tape: dict[str, Any]) -> None:
    again = everything(tape, {"troupe": "dry-run"})
    old = f"<!-- auto-merge:dry-run {EARLIER} -->"
    again[COMMENTS].append({"user": {"login": am.APP_LOGIN}, "body": old})
    _, _, replay = run(again)
    assert len(replay.writes) == 1


def test_a_marker_written_by_anyone_but_the_app_counts_for_nothing(tape: dict[str, Any]) -> None:
    again = everything(tape, {"troupe": "dry-run"})
    again[COMMENTS].append(
        {"user": {"login": AUTHOR}, "body": f"<!-- auto-merge:dry-run {HEAD} -->"}
    )
    _, _, replay = run(again)
    assert len(replay.writes) == 1


def test_a_head_the_app_queued_before_isnt_queued_again(tape: dict[str, Any]) -> None:
    again = everything(tape, {"troupe": "on"})
    again[COMMENTS].append(
        {"user": {"login": am.APP_LOGIN}, "body": f"<!-- auto-merge:queued {HEAD} -->"}
    )
    _, lines, replay = run(again)
    assert replay.writes == []
    assert any("re-queueing it is the owner's" in line for line in lines)


def test_hold_takes_out_a_pull_request_the_app_queued(tape: dict[str, Any]) -> None:
    again = everything(tape, {"troupe": "on"})
    pull(again).update(mergeQueueEntry={"id": "MQE_1"}, labels={"nodes": [{"name": "hold"}]})
    again[COMMENTS].append(
        {"user": {"login": am.APP_LOGIN}, "body": f"<!-- auto-merge:queued {HEAD} -->"}
    )
    _, lines, replay = run(again)
    assert replay.writes == [
        {"graphql": "dequeuePullRequest", "variables": {"id": pull(tape)["id"]}}
    ]
    assert "  - #467: held: taken out of the queue the App put it in" in lines


def test_hold_leaves_a_pull_request_the_owner_queued(tape: dict[str, Any]) -> None:
    again = everything(tape, {"troupe": "on"})
    pull(again).update(mergeQueueEntry={"id": "MQE_1"}, labels={"nodes": [{"name": "hold"}]})
    _, lines, replay = run(again)
    assert replay.writes == []
    assert "  - #467: already in the queue" in lines


def test_one_pull_request_failing_doesnt_stop_the_rest_and_the_run_is_red(
    tape: dict[str, Any],
) -> None:
    again = everything(tape, {"troupe": "on", "website": "on"})
    again[OPEN_PRS["website"]] = [{"number": 5}]
    status, lines, _ = run(again)
    assert status == 1
    assert "  - #467: queued" in lines
    assert any(line.startswith("  - #5: error:") for line in lines)


# --- The transport --------------------------------------------------------------------------------


def test_a_listing_is_read_to_its_last_page() -> None:
    first: list[object] = [{"n": index} for index in range(100)]
    replay = am.Replay(
        {"GET x?per_page=100&page=1": first, "GET x?per_page=100&page=2": [{"n": 100}]}
    )
    assert len(am.get_all(replay, "x")) == 101


def test_the_replay_refuses_a_read_the_tape_doesnt_hold() -> None:
    with pytest.raises(am.AutoMergeError, match="the tape has no answer"):
        am.Replay({}).get("repos/x")


def test_a_recorder_sends_reads_and_keeps_writes() -> None:
    inner = am.Replay({"GET a": [1]})
    recorder = am.Recorder(inner)
    assert recorder.get("a") == [1]
    recorder.write("POST", "b", {"x": 1})
    recorder.graphql("mutation($id: ID!) { x }", {"id": "1"})
    assert inner.writes == []
    assert len(recorder.writes) == 2
