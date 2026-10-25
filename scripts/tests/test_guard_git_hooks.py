"""Task 2.4: the git hooks end to end, making real commits in a temporary repository."""

import json
import shutil
import subprocess
from collections.abc import Callable

import pytest
from conftest import FAILING_CHECK, Repo, clean_env, git

import guard


def test_a_commit_on_main_is_refused_and_leaves_no_commit(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    repo.hooks_on()
    before = repo.head()
    repo.write("a.txt", "a\n")
    result = repo.commit("feat: add a")
    assert result.returncode != 0
    assert "guard: commit-on-main:" in result.stderr
    assert repo.head() == before


def test_a_commit_on_a_branch_without_its_change_is_refused(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    repo.hooks_on()
    repo.switch("add-thing")
    before = repo.head()
    repo.write("a.txt", "a\n")
    result = repo.commit("feat: add a")
    assert result.returncode != 0
    assert "guard: commit-branch-change:" in result.stderr
    assert repo.head() == before


def test_a_non_conventional_message_is_refused_and_leaves_no_commit(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    repo.hooks_on()
    repo.change("add-thing")
    repo.switch("add-thing")
    before = repo.head()
    result = repo.commit("Add a thing")
    assert result.returncode != 0
    assert "guard: commit-message:" in result.stderr
    assert repo.head() == before


def test_a_failing_check_refuses_the_commit(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    repo.hooks_on(check_script=FAILING_CHECK)
    repo.change("add-thing")
    repo.switch("add-thing")
    before = repo.head()
    result = repo.commit("feat: add a thing")
    assert result.returncode != 0
    assert "guard: commit-checks: the mypy --strict gate failed." in result.stderr
    assert repo.head() == before


def test_a_commit_that_meets_every_rule_is_made(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    repo.hooks_on()
    repo.change("add-thing")
    repo.switch("add-thing")
    before = repo.head()
    result = repo.commit("feat(thing): add a thing")
    assert result.returncode == 0, result.stderr
    assert repo.head() != before


# Rule: schema-commit-type (#122). Tasks 1.1-1.3 of protocol-schema-commit-types.

SCHEMA = "protocol/schemas/a.schema.json"


def schema_repo(make_repo: Callable[[], Repo]) -> Repo:
    """A repository with the hooks on, a protocol schema committed, and a change branch."""
    repo = make_repo()
    repo.write(SCHEMA, '{"type": "object"}\n')
    repo.write("protocol/README.md", "The protocol.\n")
    repo.write("protocol/CHANGELOG.md", "# Changelog\n")
    repo.hooks_on()
    repo.change("add-thing")
    repo.switch("add-thing")
    repo.commit("docs(openspec): propose add-thing")
    return repo


def test_a_docs_commit_to_protocol_files_outside_the_schemas_is_made(
    make_repo: Callable[[], Repo],
) -> None:
    repo = schema_repo(make_repo)
    repo.write("protocol/README.md", "The protocol, explained.\n")
    repo.write("protocol/CHANGELOG.md", "# Changelog\n\nNothing yet.\n")
    result = repo.commit("docs(protocol): explain versioning")
    assert result.returncode == 0, result.stderr


def test_a_chore_commit_in_a_repository_without_protocol_schemas_is_made(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    repo.hooks_on()
    repo.change("add-thing")
    repo.switch("add-thing")
    repo.write("a.txt", "a\n")
    result = repo.commit("chore: add a")
    assert result.returncode == 0, result.stderr


def test_a_feat_commit_changing_a_schema_is_made(make_repo: Callable[[], Repo]) -> None:
    repo = schema_repo(make_repo)
    repo.write(SCHEMA, '{"type": "object", "required": []}\n')
    result = repo.commit("feat(protocol): require nothing yet")
    assert result.returncode == 0, result.stderr


def test_a_docs_commit_changing_a_schema_is_refused_and_leaves_no_commit(
    make_repo: Callable[[], Repo],
) -> None:
    repo = schema_repo(make_repo)
    before = repo.head()
    repo.write(SCHEMA, '{"type": "object", "description": "A."}\n')
    result = repo.commit("docs(protocol): describe the schema")
    assert result.returncode != 0
    assert "guard: schema-commit-type:" in result.stderr
    assert SCHEMA in result.stderr
    assert repo.head() == before


def test_a_staged_schema_left_out_of_a_pathspec_commit_doesn_t_count(
    make_repo: Callable[[], Repo], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = schema_repo(make_repo)
    repo.write(SCHEMA, '{"type": "object", "description": "A."}\n')
    repo.write("protocol/README.md", "The protocol, explained.\n")
    git(repo.path, "add", SCHEMA, "protocol/README.md")
    # As `git commit protocol/README.md` does: the index it commits is HEAD plus the named path.
    # End to end, commit-checks refuses first, since the left-out schema is in the working tree.
    lock = repo.path / ".git" / "next-index-1.lock"
    env = {**clean_env(), "GIT_INDEX_FILE": str(lock)}
    subprocess.run(["git", "read-tree", "HEAD"], cwd=repo.path, env=env, check=True)
    subprocess.run(["git", "add", "protocol/README.md"], cwd=repo.path, env=env, check=True)
    assert commit_msg_with_index(repo, "docs(protocol): explain", str(lock), monkeypatch) == 0


def commit_msg_with_index(
    repo: Repo, message: str, index: str, monkeypatch: pytest.MonkeyPatch
) -> int:
    """Run the commit-msg entry as git runs it, with GIT_INDEX_FILE naming the index git commits."""
    message_file = repo.path / ".git" / "COMMIT_EDITMSG"
    message_file.write_text(message, encoding="utf-8")
    monkeypatch.setenv("GIT_INDEX_FILE", index)
    return guard.run_commit_msg(repo.path, message_file)


def test_the_index_git_is_committing_is_judged_as_commit_a_builds_it(
    make_repo: Callable[[], Repo], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = schema_repo(make_repo)
    repo.write(SCHEMA, '{"type": "object", "description": "A."}\n')
    # As `git commit -a` does: the schema edit is in index.lock, while .git/index doesn't have it.
    lock = repo.path / ".git" / "index.lock"
    shutil.copyfile(repo.path / ".git" / "index", lock)
    env = {**clean_env(), "GIT_INDEX_FILE": str(lock)}
    subprocess.run(["git", "add", SCHEMA], cwd=repo.path, env=env, check=True)
    assert git(repo.path, "diff", "--cached", "--name-only").stdout == ""
    assert commit_msg_with_index(repo, "docs: describe", str(lock), monkeypatch) == 1


def test_a_schema_edit_only_in_the_working_tree_doesn_t_count(
    make_repo: Callable[[], Repo], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = schema_repo(make_repo)
    repo.write(SCHEMA, '{"type": "object", "description": "A."}\n')
    repo.write("protocol/README.md", "The protocol, explained.\n")
    git(repo.path, "add", "protocol/README.md")
    # git sets it relative to the repository's root for a plain commit.
    assert commit_msg_with_index(repo, "docs: explain", ".git/index", monkeypatch) == 0


# minor-corrections (#103): the pre-commit rules judge what the commit contains (design D1, D2).

SKIP_OPENSPEC = 'version = 1\n\n[skip]\npaths = ["openspec/**"]\n'


def change_repo(make_repo: Callable[[], Repo]) -> Repo:
    """A repository with the hooks on, a check-paths declaration skipping openspec/, a tracked
    `a.txt` and `b.txt`, and a change branch."""
    repo = make_repo()
    repo.write(guard.CHECK_PATHS, SKIP_OPENSPEC)
    repo.write("a.txt", "a\n")
    repo.write("b.txt", "b\n")
    repo.hooks_on()
    repo.change("add-thing")
    repo.switch("add-thing")
    assert repo.commit("docs(openspec): propose add-thing").returncode == 0
    return repo


def test_a_plain_commit_with_an_unstaged_tracked_edit_is_refused_naming_it(
    make_repo: Callable[[], Repo],
) -> None:
    repo = change_repo(make_repo)
    before = repo.head()
    repo.write("a.txt", "a, changed\n")
    repo.write("b.txt", "b, changed\n")
    result = repo.commit("fix: change a", "a.txt")
    assert result.returncode != 0
    assert "guard: commit-checks: tracked files have unstaged changes (b.txt)" in result.stderr
    assert repo.head() == before


def test_a_plain_commit_of_only_skipped_paths_skips_the_check(
    make_repo: Callable[[], Repo],
) -> None:
    repo = change_repo(make_repo)
    repo.write("openspec/changes/add-thing/proposal.md", "# Proposal\n")
    result = repo.commit("docs(openspec): add the proposal")
    assert result.returncode == 0, result.stderr
    assert "the check is skipped" in result.stderr


def test_a_path_commit_leaving_out_an_unstaged_edit_is_refused_naming_it(
    make_repo: Callable[[], Repo],
) -> None:
    repo = change_repo(make_repo)
    before = repo.head()
    repo.write("a.txt", "a, changed\n")
    repo.write("b.txt", "b, changed\n")
    result = git(repo.path, "commit", "-q", "-m", "fix: change a", "a.txt", check=False)
    assert result.returncode != 0
    assert "guard: commit-checks: tracked files have unstaged changes (" in result.stderr
    assert "b.txt" in result.stderr
    assert repo.head() == before


def test_a_path_commit_names_only_the_edits_it_leaves_out(make_repo: Callable[[], Repo]) -> None:
    repo = change_repo(make_repo)
    repo.write("a.txt", "a, changed\n")
    repo.write("b.txt", "b, changed\n")
    result = git(repo.path, "commit", "-q", "-m", "fix: change a", "a.txt", check=False)
    assert "guard: commit-checks: tracked files have unstaged changes (b.txt)" in result.stderr


def test_a_path_commit_leaving_out_a_staged_edit_is_refused_naming_it(
    make_repo: Callable[[], Repo],
) -> None:
    repo = change_repo(make_repo)
    before = repo.head()
    repo.write("a.txt", "a, changed\n")
    repo.write("b.txt", "b, changed\n")
    git(repo.path, "add", "a.txt", "b.txt")
    result = git(repo.path, "commit", "-q", "-m", "fix: change a", "a.txt", check=False)
    assert result.returncode != 0
    assert "guard: commit-checks: tracked files have unstaged changes (b.txt)" in result.stderr
    assert "With `git commit <path>`, name them too, or commit without paths." in result.stderr
    assert repo.head() == before


def commit_all(repo: Repo, message: str) -> subprocess.CompletedProcess[str]:
    return git(repo.path, "commit", "-q", "-a", "-m", message, check=False)


def test_commit_a_with_an_unstaged_tracked_edit_runs_the_check_and_is_made(
    make_repo: Callable[[], Repo],
) -> None:
    repo = change_repo(make_repo)
    before = repo.head()
    repo.write("a.txt", "a, changed\n")
    result = commit_all(repo, "fix: change a")
    assert result.returncode == 0, result.stderr
    assert "guard: running scripts/check.py" in result.stderr
    assert repo.head() != before


def test_commit_a_of_a_declaration_edit_runs_the_full_check(
    make_repo: Callable[[], Repo],
) -> None:
    repo = change_repo(make_repo)
    repo.write(guard.CHECK_PATHS, SKIP_OPENSPEC + "\n# Nothing else is skipped.\n")
    result = commit_all(repo, "chore: explain the declaration")
    assert result.returncode == 0, result.stderr
    assert "guard: running scripts/check.py, the same check CI runs" in result.stderr


def test_commit_a_of_a_malformed_declaration_is_refused_for_the_declaration(
    make_repo: Callable[[], Repo],
) -> None:
    repo = change_repo(make_repo)
    before = repo.head()
    repo.write(guard.CHECK_PATHS, "version = 2\n")
    result = commit_all(repo, "chore: break the declaration")
    assert result.returncode != 0
    assert "guard: commit-checks:" in result.stderr
    assert guard.CHECK_PATHS in result.stderr
    assert "unstaged" not in result.stderr
    assert repo.head() == before


def test_commit_a_leaving_an_archived_task_unticked_is_refused_naming_it(
    make_repo: Callable[[], Repo],
) -> None:
    repo = change_repo(make_repo)
    tasks = repo.change("add-thing", archived_on="2026-10-25") / "tasks.md"
    assert repo.commit("docs(openspec): archive add-thing").returncode == 0
    before = repo.head()
    tasks.write_text("- [x] 1.1 done\n- [ ] 1.2 not yet\n", encoding="utf-8")
    result = commit_all(repo, "docs(openspec): add a task")
    assert result.returncode != 0
    assert "guard: archive-incomplete:" in result.stderr
    assert "1.2 not yet" in result.stderr
    assert repo.head() == before


def test_commit_a_of_a_delivered_file_edit_is_refused_naming_it(
    make_repo: Callable[[], Repo],
) -> None:
    repo = change_repo(make_repo)
    listing = {"source": guard.SOURCE_REPOSITORY, "files": ["b.txt", guard.DELIVERY_LIST]}
    repo.write(guard.DELIVERY_LIST, json.dumps(listing))
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "--no-verify", "-m", "chore(guard): deliver the list")
    before = repo.head()
    repo.write("b.txt", "b, changed\n")
    result = commit_all(repo, "fix: change b")
    assert result.returncode != 0
    assert "guard: delivered-file:" in result.stderr
    assert "b.txt" in result.stderr
    assert repo.head() == before
