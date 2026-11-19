"""blocked-by: a pull request can't merge while an issue it closes is blocked by an open issue
(spec: development-workflow; #275; auto-merge design D7).

The blocked-by listings' shape is GitHub's, as read on 2026-11-19 from a throwaway repository and
from troupe-run/troupe#286 and troupe-run/infrastructure#339 (design D7's probe): a list of issues,
each with its number, state and repository_url.
"""

import io
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import Repo
from test_guard_pr_description import passing_openspec, pull_request_with  # noqa: F401 (a fixture)
from test_guard_push_and_ci import commit_without_hooks, pr_repo

import guard

TROUPE = "troupe-run/troupe"
INFRASTRUCTURE = "troupe-run/infrastructure"
GITHUB_GET = guard.github_get
"""The real reader, kept before conftest's autouse fake replaces it for every test."""
QUEUE_REF = "refs/heads/gh-readonly-queue/main/pr-41-b54dfa1027945d3f1f900c742ea4f510aa5651c4"


def blocker(repository: str, number: int, state: str) -> dict[str, object]:
    return {
        "number": number,
        "state": state,
        "repository_url": f"https://api.github.com/repos/{repository}",
        "title": "a blocker",
    }


def blocked_path(repository: str, number: int, page: int = 1) -> str:
    return f"repos/{repository}/issues/{number}/dependencies/blocked_by?per_page=100&page={page}"


def reader(answers: dict[str, object]) -> Callable[[str], object]:
    """A fake API: each path's answer, an exception to raise, or a 404 for any other path."""
    asked: list[str] = []

    def read(path: str) -> object:
        asked.append(path)
        answer = answers.get(path)
        if answer is None:
            raise guard.UnreadableGitHubError("GitHub answered 404 Not Found")
        if isinstance(answer, Exception):
            raise answer
        return answer

    read.asked = asked  # type: ignore[attr-defined]
    return read


def test_an_open_blocker_in_another_repository_fails_naming_both_and_the_fix() -> None:
    read = reader({blocked_path(TROUPE, 278): [blocker(INFRASTRUCTURE, 272, "open")]})
    decision = guard.blocked_by("Runtimes.\n\nCloses #278", TROUPE, read)
    assert decision.rule == "blocked-by"
    assert (
        "troupe-run/troupe#278 is blocked by troupe-run/infrastructure#272, which is still open"
        in (decision.problem)
    )
    assert "Merge what blocks it first" in decision.fix
    assert "re-run this check" in decision.fix


def test_a_closed_blocker_passes() -> None:
    read = reader({blocked_path(TROUPE, 278): [blocker(INFRASTRUCTURE, 272, "closed")]})
    assert not guard.blocked_by("Closes #278", TROUPE, read).refused


def test_a_blocker_in_the_same_repository_is_named_in_full() -> None:
    read = reader({blocked_path(INFRASTRUCTURE, 300): [blocker(INFRASTRUCTURE, 299, "open")]})
    decision = guard.blocked_by("Fixes #300", INFRASTRUCTURE, read)
    assert "troupe-run/infrastructure#299" in decision.problem


def test_any_open_blocker_counts_whatever_its_type() -> None:
    epic = blocker(TROUPE, 9, "open") | {"type": {"name": "Epic"}}
    read = reader({blocked_path(TROUPE, 10): [epic]})
    assert guard.blocked_by("Closes #10", TROUPE, read).refused


def test_no_blockers_passes() -> None:
    read = reader({blocked_path(TROUPE, 5): []})
    assert not guard.blocked_by("Closes #5", TROUPE, read).refused


def test_every_closed_issue_is_judged_in_every_form_closing_reads() -> None:
    read = reader(
        {
            blocked_path(TROUPE, 1): [],
            blocked_path(INFRASTRUCTURE, 2): [],
            blocked_path("troupe-run/website", 3): [blocker("troupe-run/website", 4, "open")],
        }
    )
    decision = guard.blocked_by(
        "Closes #1, fixes troupe-run/infrastructure#2\n"
        "Resolves: https://github.com/troupe-run/website/issues/3",
        TROUPE,
        read,
    )
    assert decision.problem == (
        "troupe-run/website#3 is blocked by troupe-run/website#4, which is still open."
    )


def test_a_description_that_closes_nothing_reads_nothing() -> None:
    read = reader({})
    assert not guard.blocked_by("Bumps the build.", TROUPE, read).refused
    assert read.asked == []  # type: ignore[attr-defined]


def test_a_long_blocker_list_is_read_to_its_last_page() -> None:
    first = [blocker(TROUPE, n, "closed") for n in range(100, 200)]
    read = reader(
        {blocked_path(TROUPE, 7): first, blocked_path(TROUPE, 7, 2): [blocker(TROUPE, 1, "open")]}
    )
    decision = guard.blocked_by("Closes #7", TROUPE, read)
    assert "troupe-run/troupe#1" in decision.problem


def test_a_refused_read_fails_and_never_counts_as_not_blocked() -> None:
    read = reader(
        {blocked_path(TROUPE, 278): guard.UnreadableGitHubError("GitHub answered 403 Forbidden")}
    )
    decision = guard.blocked_by("Closes #278", TROUPE, read)
    assert decision.rule == "blocked-by"
    assert "couldn't read what blocks troupe-run/troupe#278" in decision.problem
    assert "403" in decision.problem
    assert "Re-run the check" in decision.fix


def test_a_closed_issue_that_does_not_exist_fails() -> None:
    decision = guard.blocked_by("Closes #99999", TROUPE, reader({}))
    assert "troupe-run/troupe#99999" in decision.problem
    assert "404" in decision.problem


@pytest.mark.parametrize(
    "listing",
    [{"message": "Not a list"}, ["not an object"], [{"number": 1, "state": "closed"}],
     [{"number": "1", "state": "open", "repository_url": f"https://api.github.com/repos/{TROUPE}"}],
     [{"number": 1, "state": "weird", "repository_url": f"https://api.github.com/repos/{TROUPE}"}]],
)  # fmt: skip
def test_a_listing_of_the_wrong_shape_fails(listing: object) -> None:
    read = reader({blocked_path(TROUPE, 8): listing})
    assert guard.blocked_by("Closes #8", TROUPE, read).rule == "blocked-by"


# --- which description, on which event ---------------------------------------------------------


def test_a_merge_group_judges_the_description_of_the_pull_request_it_was_built_for() -> None:
    read = reader(
        {
            f"repos/{TROUPE}/pulls/41": {"number": 41, "body": "Closes #278"},
            blocked_path(TROUPE, 278): [blocker(INFRASTRUCTURE, 272, "open")],
        }
    )
    payload = {"merge_group": {"head_ref": QUEUE_REF}}
    decision = guard.blocked_by_on_github("merge_group", payload, None, TROUPE, read)
    assert "troupe-run/infrastructure#272" in decision.problem


def test_a_merge_group_whose_head_ref_names_no_pull_request_fails() -> None:
    payload = {"merge_group": {"head_ref": "refs/heads/somewhere-else"}}
    decision = guard.blocked_by_on_github("merge_group", payload, None, TROUPE, reader({}))
    assert decision.rule == "blocked-by"
    assert "couldn't tell which pull request this merge group is for" in decision.problem


def test_a_pull_request_event_judges_its_own_description() -> None:
    read = reader({blocked_path(TROUPE, 3): [blocker(TROUPE, 2, "open")]})
    decision = guard.blocked_by_on_github("pull_request", {}, "Closes #3", TROUPE, read)
    assert decision.refused


def test_a_release_pull_request_with_no_description_to_judge_passes() -> None:
    read = reader({})
    assert not guard.blocked_by_on_github("pull_request", {}, None, TROUPE, read).refused


def test_a_push_reads_nothing() -> None:
    read = reader({})
    assert not guard.blocked_by_on_github("push", {}, None, TROUPE, read).refused
    assert read.asked == []  # type: ignore[attr-defined]


# --- the HTTP read -------------------------------------------------------------------------------


def test_the_read_sends_the_token_to_the_api_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "t0ken")
    sent: list[urllib.request.Request] = []

    def send(request: urllib.request.Request, timeout: float) -> bytes:
        sent.append(request)
        return b"[]"

    assert GITHUB_GET("repos/a/b/issues/1/dependencies/blocked_by", send) == []
    (request,) = sent
    assert request.full_url == "https://api.github.com/repos/a/b/issues/1/dependencies/blocked_by"
    assert request.unredirected_hdrs["Authorization"] == "Bearer t0ken"
    assert "Authorization" not in request.headers


def test_an_http_error_is_unreadable_naming_the_status() -> None:
    def send(request: urllib.request.Request, timeout: float) -> bytes:
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, io.BytesIO())  # type: ignore[arg-type]

    with pytest.raises(guard.UnreadableGitHubError, match="403 Forbidden"):
        GITHUB_GET("repos/a/b/issues/1", send)


def test_a_body_that_is_not_json_is_unreadable() -> None:
    with pytest.raises(guard.UnreadableGitHubError, match="isn't JSON"):
        GITHUB_GET("repos/a/b/issues/1", lambda request, timeout: b"<html>")


@pytest.mark.usefixtures("passing_openspec")
def test_the_github_check_fails_a_pull_request_whose_closed_issue_is_blocked(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Through run_ci_entry, as GitHub runs it: the pull request event's description is judged,
    a bare #n in the repository the run is in."""
    repo, _ = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(thing): add a thing", "a.txt")
    pull_request_with(repo, tmp_path, monkeypatch, {"title": "feat: x", "body": "Closes #278"})
    monkeypatch.setenv("GITHUB_REPOSITORY", TROUPE)
    read = reader({blocked_path(TROUPE, 278): [blocker(INFRASTRUCTURE, 272, "open")]})
    assert guard.run_ci_entry(repo.path, None, None, None, read_github=read) == 1
    assert (
        "guard: blocked-by: troupe-run/troupe#278 is blocked by troupe-run/infrastructure#272"
        in capsys.readouterr().err
    )


@pytest.mark.usefixtures("passing_openspec")
def test_the_github_check_passes_once_the_blocker_closes(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, _ = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(thing): add a thing", "a.txt")
    pull_request_with(repo, tmp_path, monkeypatch, {"title": "feat: x", "body": "Closes #278"})
    monkeypatch.setenv("GITHUB_REPOSITORY", TROUPE)
    read = reader({blocked_path(TROUPE, 278): [blocker(INFRASTRUCTURE, 272, "closed")]})
    assert guard.run_ci_entry(repo.path, None, None, None, read_github=read) == 0, (
        capsys.readouterr().err
    )
