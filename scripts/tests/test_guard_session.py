"""Task 5.1: the SessionStart entry point activates the git hooks and reports the workflow."""

import io
import json
import os
from collections.abc import Callable

import pytest
from conftest import Repo, git

import guard


def session_start(repo: Repo) -> str:
    stream = io.StringIO()
    assert guard.run_claude_session_start(repo.path, stdout=stream) == 0
    output = json.loads(stream.getvalue())
    specific = output["hookSpecificOutput"]
    assert specific["hookEventName"] == "SessionStart"
    context: str = specific["additionalContext"]
    return context


def hooks_path(repo: Repo) -> str:
    return git(repo.path, "config", "--get", "core.hooksPath", check=False).stdout.strip()


def test_inactive_git_hooks_are_activated_and_the_session_is_told(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    assert hooks_path(repo) == ""
    context = session_start(repo)
    assert hooks_path(repo) == ".githooks"
    assert "Activated the repository's git hooks (core.hooksPath was unset" in context


def test_hooks_pointing_elsewhere_are_reset_to_the_repository_s_hooks(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    git(repo.path, "config", "core.hooksPath", "/somewhere/else")
    context = session_start(repo)
    assert hooks_path(repo) == ".githooks"
    assert "was /somewhere/else" in context


def test_already_active_hooks_are_left_alone_and_not_mentioned(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    git(repo.path, "config", "core.hooksPath", ".githooks")
    assert "Activated" not in session_start(repo)


def test_the_context_states_the_workflow(make_repo: Callable[[], Repo]) -> None:
    context = session_start(make_repo())
    assert "issue -> OpenSpec change" in context
    assert "Conventional Commits" in context
    assert "Only the owner can grant an override" in context


def test_the_context_says_when_the_branch_has_no_matching_change(
    make_repo: Callable[[], Repo],
) -> None:
    context = session_start(make_repo())
    assert "Branch 'main' has no matching OpenSpec change" in context


def test_the_context_says_when_the_branch_matches_a_change(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    repo.change("add-thing")
    repo.switch("add-thing")
    context = session_start(repo)
    assert "Branch 'add-thing' matches the OpenSpec change openspec/changes/add-thing" in context


# --- a hook git would skip (spec: development-workflow; executable-hooks design D6) -----------

posix_only = pytest.mark.skipif(os.name == "nt", reason="Git for Windows has no executable bit")


def add_hook(repo: Repo, name: str, executable: bool) -> None:
    repo.write(f".githooks/{name}", "#!/bin/sh\nexit 0\n")
    (repo.path / ".githooks" / name).chmod(0o755 if executable else 0o644)


def deliver(repo: Repo, *paths: str) -> None:
    repo.write(".github/guard-delivery.json", json.dumps({"files": list(paths)}))


@posix_only
def test_a_delivered_hook_that_isn_t_executable_is_reported_with_its_source(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    add_hook(repo, "pre-push", executable=False)
    deliver(repo, ".githooks/pre-push")
    context = session_start(repo)
    assert "Git skips .githooks/pre-push: it isn't executable." in context
    assert "delivered from troupe-run/infrastructure" in context
    assert "don't change it here" in context
    assert os.access(repo.path / ".githooks" / "pre-push", os.X_OK) is False


@posix_only
def test_a_source_hook_that_isn_t_executable_says_how_to_make_it_executable(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    add_hook(repo, "commit-msg", executable=False)
    context = session_start(repo)
    assert "Git skips .githooks/commit-msg" in context
    assert "git update-index --chmod=+x .githooks/commit-msg" in context


@posix_only
def test_only_the_hooks_that_aren_t_executable_are_named(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    add_hook(repo, "pre-commit", executable=True)
    add_hook(repo, "pre-push", executable=False)
    context = session_start(repo)
    assert ".githooks/pre-push" in context
    assert ".githooks/pre-commit" not in context


def test_executable_hooks_are_not_mentioned(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    git(repo.path, "config", "core.hooksPath", ".githooks")
    add_hook(repo, "pre-push", executable=True)
    assert guard.activate_hooks(repo.path) is None
    assert "Git skips" not in session_start(repo)


def test_nothing_is_reported_where_git_ignores_the_mode(
    make_repo: Callable[[], Repo], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_repo()
    git(repo.path, "config", "core.hooksPath", ".githooks")
    add_hook(repo, "pre-push", executable=False)
    monkeypatch.setattr(os, "name", "nt")
    assert guard.activate_hooks(repo.path) is None
