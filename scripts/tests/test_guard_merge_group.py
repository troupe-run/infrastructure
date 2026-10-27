"""A merge group is re-checked on GitHub as main is (merge-queue design D3): its range runs from the
group's base on main to its head, judged under the name of the branch it lands on, never under the
queue's gh-readonly-queue/... branch, which matches no change."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO, Repo, git
from test_guard_openspec import EVERYTHING
from test_guard_pr_description import passing_openspec  # noqa: F401 (a fixture)
from test_guard_push_and_ci import commit_without_hooks, pr_repo, with_remote

import guard

INFRASTRUCTURE = "troupe-run/infrastructure"
GUARD = REPO / ".github" / "workflows" / "guard.yml"
QUEUE_BRANCH = "gh-readonly-queue/main/pr-7-0123456789abcdef0123456789abcdef01234567"


def queued(make_repo: Callable[[], Repo], tmp_path: Path, *messages: str) -> tuple[Repo, str]:
    """main, and a queue commit on top of it carrying ``messages``, as the queue builds it: the
    clone is checked out at the group's head, on no branch of its own. Returns it and the base."""
    repo = make_repo()
    with_remote(repo, tmp_path)
    base = repo.head()
    git(repo.path, "switch", "-q", "--detach")
    for index, message in enumerate(messages):
        commit_without_hooks(repo, message, f"queued-{index}.txt")
    return repo, base


def merge_group_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, merge_group: object) -> None:
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"merge_group": merge_group}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "merge_group")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    monkeypatch.setenv("GITHUB_REF_NAME", QUEUE_BRANCH)
    monkeypatch.setenv("GITHUB_REPOSITORY", INFRASTRUCTURE)


def group(base: str, head: str, base_ref: object = "refs/heads/main") -> dict[str, object]:
    return {"base_sha": base, "head_sha": head, "base_ref": base_ref,
            "head_ref": f"refs/heads/{QUEUE_BRANCH}"}  # fmt: skip


def test_the_github_inputs_of_a_merge_group_are_its_range_judged_as_main(
    make_repo: Callable[[], Repo], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base = queued(make_repo, tmp_path, "feat: queued work")
    merge_group_event(tmp_path, monkeypatch, group(base, repo.head()))
    inputs = guard.github_ci_inputs(repo.path)
    assert inputs == (base, repo.head(), "main", None, INFRASTRUCTURE, None)


def test_a_merge_group_is_validated_in_full_as_a_push_to_main_is(
    make_repo: Callable[[], Repo], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base = queued(make_repo, tmp_path, "docs: a typo")
    merge_group_event(tmp_path, monkeypatch, group(base, repo.head()))
    _, _, branch, title, _, _ = guard.github_ci_inputs(repo.path)
    assert guard.openspec_scope(["README.md"], branch, title is not None, lambda p: True) == (
        EVERYTHING
    )


@pytest.mark.usefixtures("passing_openspec")
def test_a_conforming_merge_group_passes_although_its_branch_matches_no_change(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base = queued(make_repo, tmp_path, "feat: queued work", "fix: more queued work")
    merge_group_event(tmp_path, monkeypatch, group(base, repo.head()))
    assert guard.run_ci_entry(repo.path, None, None, None) == 0
    assert "commit-branch-change" not in capsys.readouterr().err


@pytest.mark.usefixtures("passing_openspec")
def test_a_merge_group_carrying_a_non_conventional_commit_fails_naming_it(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base = queued(make_repo, tmp_path, "feat: queued work", "Add a thing")
    merge_group_event(tmp_path, monkeypatch, group(base, repo.head()))
    assert guard.run_ci_entry(repo.path, None, None, None) == 1
    err = capsys.readouterr().err
    assert "guard: commit-message:" in err
    assert repo.head()[:7] in err


@pytest.mark.parametrize(
    "merge_group",
    [
        None,
        "refs/heads/main",
        {"head_sha": "0" * 40, "base_ref": "refs/heads/main"},
        {"base_sha": "0" * 40, "base_ref": "refs/heads/main"},
        {"base_sha": 7, "head_sha": "0" * 40, "base_ref": "refs/heads/main"},
        {"base_sha": "0" * 40, "head_sha": "0" * 40},
        {"base_sha": "0" * 40, "head_sha": "0" * 40, "base_ref": "main"},
    ],
)
def test_a_merge_group_the_check_can_t_read_fails_saying_so(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    merge_group: object,
) -> None:
    repo, _ = queued(make_repo, tmp_path, "feat: queued work")
    merge_group_event(tmp_path, monkeypatch, merge_group)
    assert guard.run_ci_entry(repo.path, None, None, None) == 1
    err = capsys.readouterr().err
    assert "guard: commit-branch-change: couldn't read the merge group" in err
    assert "Re-run the check" in err
    assert "tell the owner" in err


# What must stay the same: the exemption comes from the event, never from a branch's name.


def test_a_pull_request_from_a_branch_named_like_a_queue_s_is_still_judged_by_the_branch_rule(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    repo.switch(QUEUE_BRANCH)
    commit_without_hooks(repo, "feat: not really queued", "a.txt")
    [refusal] = guard.run_ci(repo.path, base, repo.head(), QUEUE_BRANCH, "feat: x", INFRASTRUCTURE)
    assert refusal.rule == "commit-branch-change"


def test_a_push_to_a_branch_named_like_a_queue_s_is_still_judged_by_the_branch_rule(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = pr_repo(make_repo, tmp_path)
    repo.switch(QUEUE_BRANCH)
    commit_without_hooks(repo, "feat: not really queued", "a.txt")
    [refusal] = guard.run_ci(repo.path, base, repo.head(), QUEUE_BRANCH, None, INFRASTRUCTURE)
    assert refusal.rule == "commit-branch-change"


# guard.yml's triggers (merge-queue design D3)


def guard_triggers() -> dict[str, Any]:
    workflow = yaml.safe_load(GUARD.read_text(encoding="utf-8"))
    triggers = workflow[True]  # YAML 1.1 reads the key `on` as true
    assert isinstance(triggers, dict)
    return triggers


def test_the_guard_runs_on_every_merge_group_the_queue_asks_checks_of() -> None:
    assert guard_triggers()["merge_group"] == {"types": ["checks_requested"]}


def test_the_guard_s_pull_request_trigger_is_unchanged() -> None:
    types = ["opened", "edited", "synchronize", "reopened"]
    assert guard_triggers()["pull_request"] == {"types": types}
