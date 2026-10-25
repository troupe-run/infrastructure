"""Tasks 7.2-7.3: commit messages checked before a push, and every git-level rule re-checked on
GitHub for a push or a pull request."""

import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import SCRIPTS, Repo, clean_env, git

import guard


def with_remote(repo: Repo, tmp_path: Path) -> Path:
    remote = tmp_path / f"{repo.path.name}-remote.git"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    git(repo.path, "remote", "add", "origin", str(remote))
    git(repo.path, "push", "-q", "origin", "main")
    return remote


def commit_without_hooks(repo: Repo, message: str, name: str) -> str:
    """A commit made with --no-verify: exactly what the push and CI checks must still catch."""
    repo.write(name, f"{name}\n")
    git(repo.path, "add", name)
    git(repo.path, "commit", "-q", "--no-verify", "-m", message)
    return repo.head()


# Task 7.2: pre-push


def test_a_push_carrying_a_non_conventional_commit_is_refused_naming_it(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo = make_repo()
    repo.hooks_on()
    with_remote(repo, tmp_path)
    repo.change("add-thing")
    repo.switch("add-thing")
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "-m", "docs(openspec): plan add-thing")
    bad = commit_without_hooks(repo, "Add a thing", "a.txt")
    result = git(repo.path, "push", "-u", "origin", "add-thing", check=False)
    assert result.returncode != 0
    assert "guard: commit-message:" in result.stderr
    assert bad[:7] in result.stderr
    assert "'Add a thing'" in result.stderr
    remote_branches = git(repo.path, "ls-remote", "--heads", "origin").stdout
    assert "add-thing" not in remote_branches


def test_a_push_of_conventional_commits_goes_ahead(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo = make_repo()
    repo.hooks_on()
    with_remote(repo, tmp_path)
    repo.change("add-thing")
    repo.switch("add-thing")
    result = repo.commit("feat(thing): add a thing")
    assert result.returncode == 0, result.stderr
    pushed = git(repo.path, "push", "-u", "origin", "add-thing", check=False)
    assert pushed.returncode == 0, pushed.stderr


def test_only_commits_new_to_the_remote_are_checked(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo = make_repo()
    with_remote(repo, tmp_path)
    commit_without_hooks(repo, "Old bad message already on the remote", "old.txt")
    git(repo.path, "push", "-q", "--no-verify", "origin", "main")
    good = commit_without_hooks(repo, "fix: a new, conforming commit", "new.txt")
    remote_main = git(repo.path, "rev-parse", "origin/main").stdout.strip()
    assert guard.commits_in_range(repo.path, remote_main, good) == [good]


def test_deleting_a_remote_branch_checks_nothing(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    line = f"(delete) {'0' * 40} refs/heads/gone {'1' * 40}"
    assert guard.run_pre_push(repo.path, [line]) == 0


# Rule: schema-commit-type before a push (#122)

SCHEMA = "protocol/schemas/a.schema.json"


def test_a_pushed_schema_commit_reworded_to_chore_is_refused_naming_it(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo = make_repo()
    repo.hooks_on()
    with_remote(repo, tmp_path)
    repo.change("add-thing")
    repo.switch("add-thing")
    repo.commit("docs(openspec): plan add-thing")
    repo.write(SCHEMA, "{}\n")
    made = repo.commit("feat(protocol): add a schema")
    assert made.returncode == 0, made.stderr
    # Rewording runs the commit-msg hook against an index with nothing new staged (design D5).
    reworded = git(repo.path, "commit", "-q", "--amend", "-m", "chore: tidy", check=False)
    assert reworded.returncode == 0, reworded.stderr
    result = git(repo.path, "push", "-u", "origin", "add-thing", check=False)
    assert result.returncode != 0
    assert "guard: schema-commit-type:" in result.stderr
    assert f"{repo.head()[:7]} 'chore: tidy' ({SCHEMA})" in result.stderr
    assert "add-thing" not in git(repo.path, "ls-remote", "--heads", "origin").stdout


# Task 7.3: the same rules on GitHub


def pr_repo(make_repo: Callable[[], Repo], tmp_path: Path) -> tuple[Repo, str]:
    repo = make_repo()
    with_remote(repo, tmp_path)
    base = repo.head()
    repo.change("add-thing")
    repo.switch("add-thing")
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "-m", "docs(openspec): plan add-thing")
    return repo, base


def test_a_conforming_pull_request_passes(make_repo: Callable[[], Repo], tmp_path: Path) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(thing): add a thing", "a.txt")
    assert guard.run_ci(repo.path, base, repo.head(), "add-thing") == []


def test_a_pull_request_with_a_no_verify_bad_message_fails_naming_the_commit(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    bad = commit_without_hooks(repo, "Add a thing", "a.txt")
    [refusal] = guard.run_ci(repo.path, base, repo.head(), "add-thing")
    assert refusal.rule == "commit-message"
    assert bad[:7] in refusal.problem


def test_a_pull_request_with_a_no_verify_test_schema_commit_fails_naming_it(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    bad = commit_without_hooks(repo, "test: cover the schema", SCHEMA)
    commit_without_hooks(repo, "docs(protocol): explain it", "protocol/README.md")
    [refusal] = guard.run_ci(repo.path, base, repo.head(), "add-thing")
    assert refusal.rule == "schema-commit-type"
    assert refusal.problem.startswith("1 commit(s)")
    assert f"{bad[:7]} 'test: cover the schema' ({SCHEMA})" in refusal.problem


def test_a_pull_request_of_releasing_schema_commits_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(protocol): add a schema", SCHEMA)
    commit_without_hooks(repo, "refactor(protocol)!: rename it", "protocol/schemas/b.schema.json")
    commit_without_hooks(repo, "perf: a faster schema", "protocol/schemas/c.schema.json")
    assert guard.run_ci(repo.path, base, repo.head(), "add-thing") == []


def test_a_repository_whose_first_commit_adds_a_schema_under_chore_fails(
    tmp_path: Path,
) -> None:
    path = tmp_path / "fresh"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "tester@example.com")
    git(path, "config", "user.name", "Tester")
    git(path, "config", "commit.gpgsign", "false")
    repo = Repo(path)
    first = commit_without_hooks(repo, "chore: initial", SCHEMA)
    [refusal] = guard.run_ci(path, None, first, "main")
    assert refusal.rule == "schema-commit-type"
    assert SCHEMA in refusal.problem


def test_a_pull_request_from_a_branch_with_no_change_fails(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo = make_repo()
    with_remote(repo, tmp_path)
    base = repo.head()
    repo.switch("no-change")
    commit_without_hooks(repo, "feat: something", "a.txt")
    [refusal] = guard.run_ci(repo.path, base, repo.head(), "no-change")
    assert refusal.rule == "commit-branch-change"


def test_a_push_to_main_checks_messages_but_not_the_branch_rule(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo = make_repo()
    with_remote(repo, tmp_path)
    before = repo.head()
    commit_without_hooks(repo, "fix: on main", "a.txt")
    assert guard.run_ci(repo.path, before, repo.head(), "main") == []
    commit_without_hooks(repo, "Bad on main", "b.txt")
    [refusal] = guard.run_ci(repo.path, before, repo.head(), "main")
    assert refusal.rule == "commit-message"


def test_a_new_branch_push_checks_everything_not_on_the_remote(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, _ = pr_repo(make_repo, tmp_path)
    bad = commit_without_hooks(repo, "Add a thing", "a.txt")
    [refusal] = guard.run_ci(repo.path, None, repo.head(), "add-thing")
    assert bad[:7] in refusal.problem


def test_an_archived_change_with_an_unticked_task_fails(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    repo.change("add-thing", archived_on="2026-10-11", tasks="- [ ] 1.1 not done\n")
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "--no-verify", "-m", "docs(openspec): archive add-thing")
    rules = [d.rule for d in guard.run_ci(repo.path, base, repo.head(), "add-thing")]
    assert rules == ["archive-incomplete"]


def test_a_local_override_doesn_t_excuse_anything_on_github(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "Add a thing", "a.txt")
    guard.grant_override(repo.path, "commit-message", "trying to slip one through")
    [refusal] = guard.run_ci(repo.path, base, repo.head(), "add-thing")
    assert refusal.rule == "commit-message"


# release-please-prs: the release branch passes the branch rule where GitHub reserves its name: in
# a repository whose ruleset lets only the release App create or update those branches, whoever
# authored its commits (open-release-exemption design D1, D2; drop-forgery-resistance design D1)

RELEASE_BRANCH = "release-please--branches--main"
ORDINARY = "Someone <someone@example.com>"
RELEASE_BOT = "troupe-run-release[bot] <341990208+troupe-run-release[bot]@users.noreply.github.com>"
TROUPE = "troupe-run/troupe"


def commit_as(repo: Repo, author: str, message: str, name: str) -> str:
    repo.write(name, f"{name}\n")
    git(repo.path, "add", name)
    git(repo.path, "commit", "-q", "--no-verify", f"--author={author}", "-m", message)
    return repo.head()


def release_repo(make_repo: Callable[[], Repo], tmp_path: Path) -> tuple[Repo, str]:
    """A repository whose main is on its remote."""
    repo = make_repo()
    with_remote(repo, tmp_path)
    return repo, repo.head()


def test_a_release_branch_in_troupe_passes(make_repo: Callable[[], Repo], tmp_path: Path) -> None:
    repo, base = release_repo(make_repo, tmp_path)
    repo.switch(RELEASE_BRANCH)
    commit_as(repo, RELEASE_BOT, "chore: release main", "CHANGELOG.md")
    assert guard.run_ci(repo.path, base, repo.head(), RELEASE_BRANCH, repository=TROUPE) == []


def test_a_release_branch_in_troupe_passes_whoever_authored_its_commits(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = release_repo(make_repo, tmp_path)
    repo.switch(RELEASE_BRANCH)
    commit_as(repo, RELEASE_BOT, "chore: release main", "CHANGELOG.md")
    commit_as(repo, ORDINARY, "fix: someone else's commit", "a.txt")
    assert guard.run_ci(repo.path, base, repo.head(), RELEASE_BRANCH, repository=TROUPE) == []


def test_a_release_branch_in_a_repository_without_the_release_ruleset_fails_the_branch_rule(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = release_repo(make_repo, tmp_path)
    repo.switch(RELEASE_BRANCH)
    commit_as(repo, RELEASE_BOT, "chore: release main", "CHANGELOG.md")
    [refusal] = guard.run_ci(
        repo.path, base, repo.head(), RELEASE_BRANCH, repository="troupe-run/infrastructure"
    )
    assert refusal.rule == "commit-branch-change"


def test_a_release_branch_in_a_fork_fails_the_branch_rule(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = release_repo(make_repo, tmp_path)
    repo.switch(RELEASE_BRANCH)
    commit_as(repo, RELEASE_BOT, "chore: release main", "CHANGELOG.md")
    [refusal] = guard.run_ci(
        repo.path, base, repo.head(), RELEASE_BRANCH, repository="someone/troupe"
    )
    assert refusal.rule == "commit-branch-change"


def test_a_release_branch_with_no_repository_named_fails_the_branch_rule(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = release_repo(make_repo, tmp_path)
    repo.switch(RELEASE_BRANCH)
    commit_as(repo, RELEASE_BOT, "chore: release main", "CHANGELOG.md")
    [refusal] = guard.run_ci(repo.path, base, repo.head(), RELEASE_BRANCH, repository=None)
    assert refusal.rule == "commit-branch-change"


def test_the_bot_s_commits_on_a_branch_with_another_name_fail_the_branch_rule(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = release_repo(make_repo, tmp_path)
    repo.switch("not-a-release")
    commit_as(repo, RELEASE_BOT, "chore: release main", "CHANGELOG.md")
    [refusal] = guard.run_ci(repo.path, base, repo.head(), "not-a-release", repository=TROUPE)
    assert refusal.rule == "commit-branch-change"


def test_a_non_conventional_commit_on_the_release_branch_fails_naming_it(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = release_repo(make_repo, tmp_path)
    repo.switch(RELEASE_BRANCH)
    bad = commit_as(repo, ORDINARY, "Release main", "CHANGELOG.md")
    [refusal] = guard.run_ci(repo.path, base, repo.head(), RELEASE_BRANCH, repository=TROUPE)
    assert refusal.rule == "commit-message"
    assert bad[:7] in refusal.problem


def test_a_release_branch_that_changes_a_delivered_file_fails_the_delivered_file_rule(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, _ = release_repo(make_repo, tmp_path)
    listing = {"source": guard.SOURCE_REPOSITORY, "files": ["a.txt", guard.DELIVERY_LIST]}
    repo.write(guard.DELIVERY_LIST, json.dumps(listing))
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "--no-verify", "-m", "chore(guard): deliver the list")
    git(repo.path, "push", "-q", "origin", "main")
    base = repo.head()
    repo.switch(RELEASE_BRANCH)
    bad = commit_as(repo, ORDINARY, "chore: release main", "a.txt")
    [refusal] = guard.run_ci(repo.path, base, repo.head(), RELEASE_BRANCH, repository=TROUPE)
    assert refusal.rule == "delivered-file"
    assert bad[:7] in refusal.problem


def test_a_release_branch_rebuilt_on_a_newer_main_passes_on_the_force_push_range(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, _ = release_repo(make_repo, tmp_path)
    repo.switch(RELEASE_BRANCH)
    old_head = commit_as(repo, ORDINARY, "chore: release main", "CHANGELOG.md")
    git(repo.path, "switch", "-q", "main")
    commit_without_hooks(repo, "feat: someone else's work on main", "b.txt")
    git(repo.path, "push", "-q", "origin", "main")
    git(repo.path, "switch", "-q", "-C", RELEASE_BRANCH, "main")
    commit_as(repo, ORDINARY, "chore: release main", "CHANGELOG.md")
    # The push event's range holds main's new commit as well as the rebuilt release commit.
    assert len(guard.commits_in_range(repo.path, old_head, repo.head())) == 2
    assert guard.run_ci(repo.path, old_head, repo.head(), RELEASE_BRANCH, repository=TROUPE) == []


TOFU = SCRIPTS.parent / "tofu"


def _blocks(text: str, opening: str) -> list[str]:
    """Each top-level block in a .tf file whose first line matches the pattern, by brace depth."""
    blocks = []
    for match in re.finditer(opening, text, re.MULTILINE):
        depth, end = 0, match.end()
        for end in range(match.start(), len(text)):
            depth += {"{": 1, "}": -1}.get(text[end], 0)
            if depth == 0 and text[end] == "}":
                break
        blocks.append(text[match.start() : end + 1])
    return blocks


def release_ruleset_repositories(release_tf: str, repositories_tf: str) -> set[str]:
    """The repositories a ruleset reserving release-please--* branches is declared for, by full
    name: it covers those branches and refuses their creation and update to all but its bypass. A
    text reading of the two files, not an HCL parser (open-release-exemption design D4;
    drop-forgery-resistance design D6)."""
    owner = guard.SOURCE_REPOSITORY.split("/")[0]
    names = {}
    for block in _blocks(repositories_tf, r'^module "(\w+)" \{'):
        module = re.match(r'module "(\w+)"', block)
        name = re.search(r'^  name\s*=\s*"([^"]+)"', block, re.MULTILINE)
        if module and name:
            names[module.group(1)] = f"{owner}/{name.group(1)}"
    covered = set()
    for block in _blocks(release_tf, r'^resource "github_repository_ruleset" "\w+" \{'):
        target = re.search(r"repository\s*=\s*module\.(\w+)\.name", block)
        reserves = all(
            re.search(rf"^\s*{rule}\s*=\s*true\s*$", block, re.MULTILINE)
            for rule in ("creation", "update")
        )
        covers = '"refs/heads/release-please--*"' in block
        if covers and reserves and target and target.group(1) in names:
            covered.add(names[target.group(1)])
    return covered


@pytest.mark.tofu
def test_every_repository_the_guard_exempts_has_the_release_ruleset_declared() -> None:
    covered = release_ruleset_repositories(
        (TOFU / "release.tf").read_text(encoding="utf-8"),
        (TOFU / "repositories.tf").read_text(encoding="utf-8"),
    )
    assert guard.RELEASE_REPOSITORIES.issubset(covered)


@pytest.mark.tofu
def test_removing_the_release_ruleset_leaves_its_repository_uncovered() -> None:
    release_tf = (TOFU / "release.tf").read_text(encoding="utf-8")
    [ruleset] = [
        block
        for block in _blocks(release_tf, r'^resource "github_repository_ruleset" "\w+" \{')
        if "release-please--" in block
    ]
    covered = release_ruleset_repositories(
        release_tf.replace(ruleset, ""), (TOFU / "repositories.tf").read_text(encoding="utf-8")
    )
    assert not guard.RELEASE_REPOSITORIES.issubset(covered)


@pytest.mark.tofu
@pytest.mark.parametrize("rule", ["creation", "update"])
def test_a_release_ruleset_that_stops_reserving_the_name_leaves_its_repository_uncovered(
    rule: str,
) -> None:
    release_tf = (TOFU / "release.tf").read_text(encoding="utf-8")
    pattern = rf"^(\s*{rule}\s*=\s*)true\s*$"
    weakened, count = re.subn(pattern, r"\1false", release_tf, flags=re.MULTILINE)
    assert count == 1
    covered = release_ruleset_repositories(
        weakened, (TOFU / "repositories.tf").read_text(encoding="utf-8")
    )
    assert not guard.RELEASE_REPOSITORIES.issubset(covered)


# release-please-prs: pull request titles are Conventional Commits (design D3)


def test_a_conventional_pull_request_title_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(thing): add a thing", "a.txt")
    assert guard.run_ci(repo.path, base, repo.head(), "add-thing", "chore: release main") == []


def test_a_non_conventional_title_fails_naming_it_and_says_to_edit_the_title(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(thing): add a thing", "a.txt")
    [refusal] = guard.run_ci(repo.path, base, repo.head(), "add-thing", "Release main")
    assert refusal.rule == "commit-message"
    assert "title 'Release main'" in refusal.problem
    assert "gh pr edit" in refusal.fix
    assert "--amend" not in refusal.fix


def test_a_push_with_no_title_checks_no_title(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    commit_without_hooks(repo, "feat(thing): add a thing", "a.txt")
    assert guard.run_ci(repo.path, base, repo.head(), "add-thing", None) == []


def pull_request_event(
    repo: Repo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: object
) -> None:
    event = tmp_path / "event.json"
    event.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    monkeypatch.setenv("GITHUB_HEAD_REF", "add-thing")


def test_the_github_inputs_of_a_pull_request_carry_its_title(
    make_repo: Callable[[], Repo], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    pull_request_event(repo, tmp_path, monkeypatch, {"pull_request": {"title": "Release main"}})
    assert guard.github_ci_inputs(repo.path)[:4] == (base, repo.head(), "add-thing", "Release main")


def test_a_pull_request_event_with_no_title_fails_saying_it_couldn_t_read_it(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, _ = pr_repo(make_repo, tmp_path)
    pull_request_event(repo, tmp_path, monkeypatch, {"pull_request": {"title": None}})
    assert guard.run_ci_entry(repo.path, None, None, None) == 1
    assert "couldn't read the pull request's title" in capsys.readouterr().err


def test_guard_ci_with_a_non_conventional_title_exits_1_and_prints_the_refusal(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    env = {k: v for k, v in clean_env().items() if k != "CLAUDE_PROJECT_DIR"}
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "guard.py"), "ci", "--base", base, "--head", repo.head(),
         "--branch", "add-thing", "--title", "Release main"],
        cwd=repo.path, capture_output=True, text=True, check=False, env=env,
    )  # fmt: skip
    assert result.returncode == 1
    assert "guard: commit-message: pull request title 'Release main'" in result.stderr


# open-release-exemption: the repository comes from GitHub (design D2)


def push_event(
    repo: Repo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, before: str, branch: str
) -> None:
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"before": before}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    monkeypatch.setenv("GITHUB_REF_NAME", branch)


def test_the_github_inputs_of_a_push_name_the_run_s_repository(
    make_repo: Callable[[], Repo], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    push_event(repo, tmp_path, monkeypatch, base, "add-thing")
    monkeypatch.setenv("GITHUB_REPOSITORY", TROUPE)
    assert guard.github_ci_inputs(repo.path) == (base, repo.head(), "add-thing", None, TROUPE)


def test_the_github_inputs_of_a_push_with_no_repository_name_none(
    make_repo: Callable[[], Repo], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    push_event(repo, tmp_path, monkeypatch, base, "add-thing")
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert guard.github_ci_inputs(repo.path)[4] is None


def test_the_github_inputs_of_a_pull_request_name_its_head_repository_not_the_run_s(
    make_repo: Callable[[], Repo], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _ = pr_repo(make_repo, tmp_path)
    payload = {"pull_request": {"title": "chore: release main",
                                "head": {"repo": {"full_name": "someone/troupe"}}}}  # fmt: skip
    pull_request_event(repo, tmp_path, monkeypatch, payload)
    monkeypatch.setenv("GITHUB_REPOSITORY", TROUPE)
    assert guard.github_ci_inputs(repo.path)[4] == "someone/troupe"


def test_the_github_inputs_of_a_pull_request_from_a_deleted_fork_name_none(
    make_repo: Callable[[], Repo], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _ = pr_repo(make_repo, tmp_path)
    payload = {"pull_request": {"title": "chore: release main", "head": {"repo": None}}}
    pull_request_event(repo, tmp_path, monkeypatch, payload)
    monkeypatch.setenv("GITHUB_REPOSITORY", TROUPE)
    assert guard.github_ci_inputs(repo.path)[4] is None


@pytest.mark.parametrize("head_repo", ["troupe-run/troupe", {"full_name": 7}, {}, []])
def test_a_pull_request_whose_head_repository_can_t_be_read_fails_saying_so(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    head_repo: object,
) -> None:
    repo, _ = pr_repo(make_repo, tmp_path)
    payload = {"pull_request": {"title": "chore: release main", "head": {"repo": head_repo}}}
    pull_request_event(repo, tmp_path, monkeypatch, payload)
    assert guard.run_ci_entry(repo.path, None, None, None) == 1
    err = capsys.readouterr().err
    assert "couldn't read the pull request's head repository" in err
    assert "Re-run the check" in err
    assert "tell the owner" in err


def guard_ci(repo: Repo, monkeypatch: pytest.MonkeyPatch, *args: str) -> int:
    """guard.py ci run in-process, the way the workflow runs it."""
    monkeypatch.chdir(repo.path)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    return guard.main(["ci", *args])


def test_guard_ci_exempts_a_release_branch_in_the_named_repository(
    make_repo: Callable[[], Repo], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base = release_repo(make_repo, tmp_path)
    repo.switch(RELEASE_BRANCH)
    commit_as(repo, ORDINARY, "chore: release main", "CHANGELOG.md")
    head = repo.head()
    args = ["--base", base, "--head", head, "--branch", RELEASE_BRANCH, "--repository", TROUPE]
    assert guard_ci(repo, monkeypatch, *args) == 0


def test_guard_ci_refuses_a_release_branch_in_another_repository(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base = release_repo(make_repo, tmp_path)
    repo.switch(RELEASE_BRANCH)
    commit_as(repo, ORDINARY, "chore: release main", "CHANGELOG.md")
    head = repo.head()
    args = ["--base", base, "--head", head, "--branch", RELEASE_BRANCH,
            "--repository", "troupe-run/infrastructure"]  # fmt: skip
    assert guard_ci(repo, monkeypatch, *args) == 1
    assert "guard: commit-branch-change:" in capsys.readouterr().err


# security-scanning: a Dependabot pull request in a governed repository is an alert that comes with
# a fix, not something to merge. No exemption covers its branch, so its fix arrives through an
# OpenSpec change (security-scanning design D5; owner, 2026-10-16).

# Copied from the security update Dependabot opened on the probe (security-scanning task 2.6).
DEPENDABOT_BRANCH = "dependabot/pip/requests-2.33.0"
DEPENDABOT_BOT = "dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>"
DEPENDABOT_MESSAGE = (
    "build(deps): Bump requests from 2.19.0 to 2.33.0\n\n"
    "Bumps [requests](https://github.com/psf/requests) from 2.19.0 to 2.33.0.\n\n"
    "Signed-off-by: dependabot[bot] <support@github.com>"
)


@pytest.mark.parametrize("repository", [TROUPE, "troupe-run/infrastructure"])
def test_a_dependabot_branch_in_a_governed_repository_fails_the_branch_rule(
    make_repo: Callable[[], Repo], tmp_path: Path, repository: str
) -> None:
    repo, base = release_repo(make_repo, tmp_path)
    repo.switch(DEPENDABOT_BRANCH)
    commit_as(repo, DEPENDABOT_BOT, DEPENDABOT_MESSAGE, "requirements.txt")
    [refusal] = guard.run_ci(repo.path, base, repo.head(), DEPENDABOT_BRANCH, repository=repository)
    assert refusal.rule == "commit-branch-change"


# minor-corrections (#103): a force-pushed branch is still judged on GitHub (design D3).


def force_pushed_clone(
    make_repo: Callable[[], Repo], tmp_path: Path, message: str
) -> tuple[Path, str, str]:
    """A branch carrying a commit with ``message`` is pushed, rebased onto a newer main and
    force-pushed. Returns a clone made as actions/checkout makes one, which holds only what a ref
    reaches, so not the replaced tip; that tip; and the rebased commit."""
    repo, _ = pr_repo(make_repo, tmp_path)
    remote = repo.path.parent / f"{repo.path.name}-remote.git"
    commit_without_hooks(repo, message, "a.txt")
    git(repo.path, "push", "-q", "origin", "add-thing")
    old_tip = repo.head()
    git(repo.path, "switch", "-q", "main")
    commit_without_hooks(repo, "feat: someone else's work on main", "b.txt")
    git(repo.path, "push", "-q", "origin", "main")
    git(repo.path, "switch", "-q", "add-thing")
    git(repo.path, "rebase", "-q", "main")
    git(repo.path, "push", "-q", "--force", "origin", "add-thing")
    rebased = repo.head()
    clone = tmp_path / "checkout"
    # --no-local: a local clone copies every object, unreachable ones included.
    git(tmp_path, "clone", "-q", "--no-local", "--branch", "add-thing", str(remote), str(clone))
    assert git(clone, "cat-file", "-e", f"{old_tip}^{{commit}}", check=False).returncode != 0
    return clone, old_tip, rebased


def test_a_push_whose_previous_tip_is_in_the_clone_starts_its_range_there(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, before = pr_repo(make_repo, tmp_path)
    push_event(repo, tmp_path, monkeypatch, before, "add-thing")
    assert guard.github_ci_inputs(repo.path)[0] == before
    assert "isn't in this clone" not in capsys.readouterr().out


@pytest.mark.xfail(strict=True, reason="#103")
def test_a_force_pushed_branch_with_a_bad_message_fails_naming_the_commit(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    clone, old_tip, rebased = force_pushed_clone(make_repo, tmp_path, "Add a thing")
    push_event(Repo(clone), tmp_path, monkeypatch, old_tip, "add-thing")
    assert guard.run_ci_entry(clone, None, None, None) == 1
    captured = capsys.readouterr()
    assert "guard: commit-message:" in captured.err
    assert rebased[:7] in captured.err


@pytest.mark.xfail(strict=True, reason="#103")
def test_a_force_pushed_branch_s_run_says_where_its_range_starts(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    clone, old_tip, _ = force_pushed_clone(make_repo, tmp_path, "feat: add a thing")
    push_event(Repo(clone), tmp_path, monkeypatch, old_tip, "add-thing")
    base = git(clone, "merge-base", "origin/main", "HEAD").stdout.strip()
    assert guard.github_ci_inputs(clone)[0] == base
    out = capsys.readouterr().out
    assert f"the push's previous tip {old_tip[:7]} isn't in this clone" in out
    assert f"where the branch left main ({base[:7]})" in out
