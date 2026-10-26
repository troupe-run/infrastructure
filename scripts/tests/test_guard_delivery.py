"""The delivered-file rule (spec: guard-delivery, design D4): in a repository that receives the
guard, delivered files are changed only at their source, at every layer."""

import io
import json
from collections.abc import Callable

from conftest import Repo, git

import guard

# .github/dependabot.yml is delivered beside the guard and named in the same list (spec:
# dependency-updates).
DELIVERED = [
    "scripts/guard.py",
    ".githooks/pre-commit",
    ".githooks/commit-msg",
    ".github/dependabot.yml",
]


def receiving(repo: Repo) -> None:
    """Make `repo` a repository that receives the guard: commit its delivered list."""
    listing = {"source": guard.SOURCE_REPOSITORY, "files": [*DELIVERED, guard.DELIVERY_LIST]}
    repo.write(guard.DELIVERY_LIST, json.dumps(listing))
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "--no-verify", "-m", "chore(guard): deliver the list")


def on_a_change_branch(repo: Repo) -> None:
    repo.change("add-thing")
    repo.switch("add-thing")


def edit_denial(repo: Repo, relative: str) -> str | None:
    """The Claude Code PreToolUse hook's denial for an edit, or None when it allows it."""
    out = io.StringIO()
    payload: dict[str, object] = {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(repo.path / relative)},
        "cwd": str(repo.path),
    }
    guard.run_claude_pre_tool_use(payload, out)
    if not out.getvalue():
        return None
    reason: str = json.loads(out.getvalue())["hookSpecificOutput"]["permissionDecisionReason"]
    return reason


def commit_as(repo: Repo, email: str, message: str, relative: str) -> str:
    repo.write(relative, f"changed by {email}\n")
    git(repo.path, "add", relative)
    # --author, not user.email: inside a commit hook git exports GIT_AUTHOR_EMAIL, which would win.
    author = f"Committer <{email}>"
    git(repo.path, "commit", "-q", "--no-verify", f"--author={author}", "-m", message)
    return repo.head()


# pre-commit


def test_committing_a_change_to_a_delivered_file_is_refused_and_leaves_no_commit(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    repo.hooks_on()
    receiving(repo)
    on_a_change_branch(repo)
    before = repo.head()
    repo.write(".githooks/commit-msg", "#!/bin/sh\nexit 0\n")
    result = repo.commit("fix(guard): skip the message check")
    assert result.returncode != 0
    assert "guard: delivered-file:" in result.stderr
    assert ".githooks/commit-msg" in result.stderr
    assert guard.SOURCE_REPOSITORY in result.stderr
    assert repo.head() == before


def test_committing_a_change_to_the_delivered_dependabot_config_is_refused_naming_the_source(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    repo.hooks_on()
    receiving(repo)
    on_a_change_branch(repo)
    before = repo.head()
    repo.write(".github/dependabot.yml", "version: 2\nupdates: []\n")
    result = repo.commit("chore(deps): stop dependabot")
    assert result.returncode != 0
    assert "guard: delivered-file:" in result.stderr
    assert ".github/dependabot.yml" in result.stderr
    assert guard.SOURCE_REPOSITORY in result.stderr
    assert repo.head() == before


def test_a_commit_that_touches_only_other_files_is_made(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    repo.hooks_on()
    receiving(repo)
    on_a_change_branch(repo)
    result = repo.commit("feat(thing): add a thing")
    assert result.returncode == 0, result.stderr


def test_deleting_the_list_doesn_t_lift_the_rule_in_the_same_commit(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    repo.hooks_on()
    receiving(repo)
    on_a_change_branch(repo)
    (repo.path / guard.DELIVERY_LIST).unlink()
    # Not guard.py: the hook runs the working tree's copy, so replacing it disables the hook
    # itself. That gap is local only; the GitHub check catches it (the range test below).
    repo.write(".githooks/commit-msg", "#!/bin/sh\nexit 0\n")
    result = repo.commit("chore: stop receiving the guard")
    assert result.returncode != 0
    assert "guard: delivered-file:" in result.stderr


def test_the_source_repository_commits_its_own_guard_files(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    repo.hooks_on()
    on_a_change_branch(repo)
    repo.write("scripts/guard.py", (repo.path / "scripts/guard.py").read_text() + "# changed\n")
    result = repo.commit("feat(guard): change the guard at its source")
    assert result.returncode == 0, result.stderr


# Claude Code PreToolUse


def test_an_agent_s_edit_to_a_delivered_file_is_refused_naming_the_source(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    repo.hooks_on()
    receiving(repo)
    on_a_change_branch(repo)
    denial = edit_denial(repo, "scripts/guard.py")
    assert denial is not None
    assert "guard: delivered-file:" in denial
    assert guard.SOURCE_REPOSITORY in denial


def test_an_agent_s_edit_to_the_list_itself_is_refused(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    receiving(repo)
    on_a_change_branch(repo)
    denial = edit_denial(repo, guard.DELIVERY_LIST)
    assert denial is not None
    assert "guard: delivered-file:" in denial


def test_an_agent_edits_other_files_and_the_source_s_guard(make_repo: Callable[[], Repo]) -> None:
    receiver, source = make_repo(), make_repo()
    receiving(receiver)
    for repo in (receiver, source):
        on_a_change_branch(repo)
    assert edit_denial(receiver, "README.md") is None
    assert edit_denial(source, "scripts/guard.py") is None


def test_an_unreadable_list_still_protects_itself(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    repo.write(guard.DELIVERY_LIST, "{ not json")
    on_a_change_branch(repo)
    denial = edit_denial(repo, guard.DELIVERY_LIST)
    assert denial is not None
    assert "guard: delivered-file:" in denial


# The GitHub check


def test_a_pushed_change_to_a_delivered_file_fails_naming_the_commit_and_file(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    receiving(repo)
    base = repo.head()
    on_a_change_branch(repo)
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "--no-verify", "-m", "docs(openspec): plan add-thing")
    bad = commit_as(repo, "someone@example.com", "fix(guard): tweak it here", "scripts/guard.py")
    [refusal] = guard.run_ci(repo.path, base, repo.head(), "add-thing")
    assert refusal.rule == "delivered-file"
    assert bad[:7] in refusal.problem
    assert "scripts/guard.py" in refusal.problem


def test_the_app_s_delivery_to_main_passes(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    receiving(repo)
    before = repo.head()
    commit_as(
        repo,
        guard.DELIVERY_AUTHOR_EMAIL,
        "chore(guard): deliver scripts/guard.py 0123456789ab from troupe-run/infrastructure",
        "scripts/guard.py",
    )
    assert guard.run_ci(repo.path, before, repo.head(), "main") == []


def test_a_range_that_removes_the_list_is_still_checked(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    receiving(repo)
    before = repo.head()
    (repo.path / guard.DELIVERY_LIST).unlink()
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "--no-verify", "-m", "chore: drop the list")
    commit_as(repo, "someone@example.com", "fix: change the hook", ".githooks/pre-commit")
    [refusal] = guard.run_ci(repo.path, before, repo.head(), "main")
    assert refusal.rule == "delivered-file"


def test_the_source_repository_s_own_changes_pass(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    before = repo.head()
    commit_as(repo, "someone@example.com", "feat(guard): change it here", "scripts/guard.py")
    assert guard.run_ci(repo.path, before, repo.head(), "main") == []
