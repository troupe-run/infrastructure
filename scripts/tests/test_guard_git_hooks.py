"""Task 2.4: the git hooks end to end, making real commits in a temporary repository."""

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
    make_repo: Callable[[], Repo],
) -> None:
    repo = schema_repo(make_repo)
    repo.write(SCHEMA, '{"type": "object", "description": "A."}\n')
    repo.write("protocol/README.md", "The protocol, explained.\n")
    git(repo.path, "add", SCHEMA, "protocol/README.md")
    result = git(
        repo.path,
        "commit",
        "-q",
        "-m",
        "docs(protocol): explain",
        "protocol/README.md",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert git(repo.path, "diff", "--cached", "--name-only").stdout.split() == [SCHEMA]


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
