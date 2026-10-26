"""pr-closes-issue on GitHub: a pull request's description closes an issue, read from the event
payload the same way the local rule reads gh pr create's --body (guard-closes-issue)."""

import json
import os
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import Repo
from test_guard_openspec import captured, stub_openspec
from test_guard_push_and_ci import (
    ORDINARY,
    RELEASE_BRANCH,
    TROUPE,
    commit_as,
    commit_without_hooks,
    guard_ci,
    pr_repo,
    pull_request_event,
    release_repo,
)

import guard

CLOSING_BODIES = [
    "Closes #22",
    "Does x.\n\nfixes #22",
    "Resolves: https://github.com/troupe-run/infrastructure/issues/22",
    "Closes troupe-run/infrastructure#173",
]
NOT_CLOSING = "Bumps the build."


@pytest.fixture
def passing_openspec(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """openspec-strict runs after the git-level rules: a passing one keeps it out of the way."""
    bin_dir = stub_openspec(tmp_path / "bin", captured("pass"))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")


# What must not change (design Context): a push checks no description, and the local rule's reading


def test_a_push_event_s_ci_run_passes_a_conforming_range_with_no_description(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    passing_openspec: None,
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(thing): add a thing", "a.txt")
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"before": base}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    monkeypatch.setenv("GITHUB_REF_NAME", "add-thing")
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert guard.run_ci_entry(repo.path, None, None, None) == 0, capsys.readouterr().err


@pytest.mark.parametrize("body", CLOSING_BODIES)
def test_the_local_rule_accepts_each_closing_form(body: str) -> None:
    assert not guard.pr_closes_issue(["gh", "pr", "create", "--body", body], Path.cwd()).refused


def test_the_local_rule_refuses_a_description_that_closes_nothing() -> None:
    decision = guard.pr_closes_issue(["gh", "pr", "create", "--body", NOT_CLOSING], Path.cwd())
    assert decision.rule == "pr-closes-issue"


# Task 2.1: the rule, one reading with the local rule (design D1, D2)


@pytest.mark.parametrize("body", [*CLOSING_BODIES, NOT_CLOSING, "", "Related to #22", "Closes 22"])
def test_the_github_rule_and_the_local_rule_agree_on_every_description(body: str) -> None:
    local = guard.pr_closes_issue(["gh", "pr", "create", "--body", body], Path.cwd()).refused
    assert guard.pr_description("feat: x", body).refused is local


@pytest.mark.parametrize("body", CLOSING_BODIES)
def test_a_description_with_a_closing_line_passes(body: str) -> None:
    assert not guard.pr_description("feat: x", body).refused


def test_a_description_that_closes_nothing_is_refused_naming_the_pull_request_and_the_fix() -> None:
    decision = guard.pr_description("feat: x", NOT_CLOSING)
    assert decision.rule == "pr-closes-issue"
    assert "pull request 'feat: x'" in decision.problem
    assert "its description has no closing line" in decision.problem
    assert "gh pr edit" in decision.fix
    assert "'Closes #22'" in decision.fix
    assert "'Closes owner/repo#22'" in decision.fix
    assert "re-runs this check" in decision.fix


@pytest.mark.parametrize("body", ["", "  \n"])
def test_an_empty_description_is_refused_saying_there_is_none(body: str) -> None:
    decision = guard.pr_description("feat: x", body)
    assert decision.rule == "pr-closes-issue"
    assert "it has no description" in decision.problem
    assert "gh pr edit" in decision.fix


# Task 2.2: run_ci checks a pull request's description, with release-please's exempt (design D4)

DEPENDABOT_BRANCH = "dependabot/npm_and_yarn/zod-4.6.7"


def rules(decisions: list[guard.Decision]) -> set[str | None]:
    return {decision.rule for decision in decisions}


def test_a_pull_request_with_no_closing_line_fails(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(thing): add a thing", "a.txt")
    head = repo.head()
    decisions = guard.run_ci(repo.path, base, head, "add-thing", "feat: x", None, NOT_CLOSING)
    assert rules(decisions) == {"pr-closes-issue"}


@pytest.mark.parametrize("body", CLOSING_BODIES)
def test_a_pull_request_that_closes_an_issue_here_or_elsewhere_passes(
    make_repo: Callable[[], Repo], tmp_path: Path, body: str
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(thing): add a thing", "a.txt")
    assert guard.run_ci(repo.path, base, repo.head(), "add-thing", "feat: x", None, body) == []


def test_no_description_means_no_pull_request_and_checks_nothing(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(thing): add a thing", "a.txt")
    assert guard.run_ci(repo.path, base, repo.head(), "add-thing", "feat: x", None, None) == []


def release_pull_request(
    make_repo: Callable[[], Repo], tmp_path: Path, branch: str, repository: str
) -> list[guard.Decision]:
    repo, base = release_repo(make_repo, tmp_path)
    repo.switch(branch)
    commit_as(repo, ORDINARY, "chore: release main", "CHANGELOG.md")
    title = "chore: release main"
    return guard.run_ci(repo.path, base, repo.head(), branch, title, repository, NOT_CLOSING)


def test_troupe_s_release_pull_request_needs_no_closing_line(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    assert release_pull_request(make_repo, tmp_path, RELEASE_BRANCH, TROUPE) == []


@pytest.mark.parametrize("repository", ["someone/troupe", "troupe-run/infrastructure"])
def test_a_release_branch_from_a_fork_or_where_its_name_isn_t_reserved_needs_one(
    make_repo: Callable[[], Repo], tmp_path: Path, repository: str
) -> None:
    decisions = release_pull_request(make_repo, tmp_path, RELEASE_BRANCH, repository)
    assert rules(decisions) == {"pr-closes-issue", "commit-branch-change"}


def test_a_dependabot_pull_request_needs_a_closing_line_too(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    decisions = release_pull_request(make_repo, tmp_path, DEPENDABOT_BRANCH, TROUPE)
    assert rules(decisions) == {"pr-closes-issue", "commit-branch-change"}


# Task 2.3: guard.py ci --description, for a local run


def test_guard_ci_checks_a_description_given_on_the_command_line(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    passing_openspec: None,
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(thing): add a thing", "a.txt")
    args = ["--base", base, "--head", repo.head(), "--branch", "add-thing", "--title", "feat: x"]
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert guard_ci(repo, monkeypatch, *args, "--description", NOT_CLOSING) == 1
    assert "guard: pr-closes-issue: pull request 'feat: x'" in capsys.readouterr().err
    assert guard_ci(repo, monkeypatch, *args) == 0


# Task 3.1: the description comes from the event payload (design D2, D3)


def pull_request_with(
    repo: Repo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pull_request: dict[str, object]
) -> None:
    pull_request_event(
        repo, tmp_path, monkeypatch, {"action": "opened", "pull_request": pull_request}
    )
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)


def test_the_github_inputs_of_a_pull_request_carry_its_description(
    make_repo: Callable[[], Repo], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _ = pr_repo(make_repo, tmp_path)
    pull_request_with(repo, tmp_path, monkeypatch, {"title": "feat: x", "body": "Closes #22"})
    assert guard.github_ci_inputs(repo.path)[5] == "Closes #22"


def test_an_empty_description_from_github_is_refused_as_empty(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    passing_openspec: None,
) -> None:
    repo, _ = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(thing): add a thing", "a.txt")
    pull_request_with(repo, tmp_path, monkeypatch, {"title": "feat: x", "body": None})
    assert guard.github_ci_inputs(repo.path)[5] == ""
    assert guard.run_ci_entry(repo.path, None, None, None) == 1
    assert "pull request 'feat: x' doesn't close an issue: it has no description" in (
        capsys.readouterr().err
    )


@pytest.mark.parametrize("pull_request", [{"title": "feat: x"}, {"title": "feat: x", "body": 3}])
def test_a_description_that_can_t_be_read_fails_saying_so(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pull_request: dict[str, object],
) -> None:
    repo, _ = pr_repo(make_repo, tmp_path)
    pull_request_with(repo, tmp_path, monkeypatch, pull_request)
    assert guard.run_ci_entry(repo.path, None, None, None) == 1
    err = capsys.readouterr().err
    assert "guard: pr-closes-issue: couldn't read the pull request's description" in err
    assert "Re-run the check" in err
    assert "tell the owner" in err


def test_a_closing_description_from_github_passes(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    passing_openspec: None,
) -> None:
    repo, _ = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(thing): add a thing", "a.txt")
    pull_request_with(repo, tmp_path, monkeypatch, {"title": "feat: x", "body": "Closes #22"})
    assert guard.run_ci_entry(repo.path, None, None, None) == 0, capsys.readouterr().err


# Task 3.2: editing the description re-runs the check, which reads the edited description


def test_an_edited_description_that_now_closes_an_issue_passes(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    passing_openspec: None,
) -> None:
    repo, _ = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(thing): add a thing", "a.txt")
    payload = {
        "action": "edited",
        "changes": {"body": {"from": NOT_CLOSING}},
        "pull_request": {"title": "feat: x", "body": f"{NOT_CLOSING} Closes #22"},
    }
    pull_request_event(repo, tmp_path, monkeypatch, payload)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert guard.run_ci_entry(repo.path, None, None, None) == 0, capsys.readouterr().err
