"""Which commit a run on main plans: one with main's current state, or none (spec: ci-apply, "A plan
of main reads main's current state"; plan-each-merge-once design D1, D2).

Each test builds a real repository shaped like main's history: merges by a person, and the App's
state commits, which change only the state file.
"""

from pathlib import Path

import pytest
from conftest import git

import guard
import plan_target

APP = "340938853+troupe-run-infrastructure[bot]@users.noreply.github.com"
STATE = plan_target.STATE_PATH


@pytest.fixture(autouse=True)
def no_hook_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    """The script reads git where it runs; under a pre-commit hook, GIT_DIR points elsewhere."""
    for name in guard.REPOSITORY_LOCATION_VARIABLES:
        monkeypatch.delenv(name, raising=False)


class History:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.mkdir()
        git(path, "init", "-q", "-b", "main")
        git(path, "config", "user.email", "tester@example.com")
        git(path, "config", "user.name", "Tester")
        git(path, "config", "commit.gpgsign", "false")
        self.state = 0
        self.declaration = 0
        self.write(STATE, "state 0")
        self.write("tofu/main.tf", "declaration 0")
        git(path, "add", "-A")
        git(path, "commit", "-q", "-m", "chore: start")

    def write(self, relative: str, text: str) -> None:
        target = self.path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")

    def head(self) -> str:
        return git(self.path, "rev-parse", "HEAD").stdout.strip()

    def merge(self, *, state: bool = False) -> str:
        """A merged pull request: the declaration changes, and with `state`, the state too
        (a break-glass apply)."""
        self.declaration += 1
        self.write("tofu/main.tf", f"declaration {self.declaration}")
        if state:
            self.state += 1
            self.write(STATE, f"state {self.state}")
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", f"feat: merge {self.declaration}")
        return self.head()

    def apply(self) -> str:
        """The App's state commit after an apply: only the state file, by the App's bot."""
        self.state += 1
        self.write(STATE, f"state {self.state}")
        git(self.path, "add", STATE)
        # --author, not user.email: under a commit hook, git's GIT_AUTHOR_* would win over config.
        git(
            self.path,
            "commit",
            "-q",
            f"--author=troupe-run-infrastructure[bot] <{APP}>",
            "-m",
            "chore(tofu): commit the state after applying x",
        )
        return self.head()


@pytest.fixture
def history(tmp_path: Path) -> History:
    return History(tmp_path / "repo")


def target(history: History, event: str, commit: str) -> plan_target.Target:
    return plan_target.decide(history.path, event, commit, APP, "main")


@pytest.mark.parametrize("event", ["schedule", "workflow_dispatch"])
def test_a_scheduled_or_manual_run_plans_mains_head_when_it_starts(
    history: History, event: str
) -> None:
    started_on = history.merge()
    history.apply()
    head = history.merge()
    found = target(history, event, started_on)
    assert found.sha == head
    assert "has moved" in found.reason


def test_a_scheduled_run_on_mains_head_plans_it(history: History) -> None:
    head = history.merge()
    found = target(history, "schedule", head)
    assert found.sha == head
    assert "has moved" not in found.reason


def test_a_merge_with_the_current_state_plans_itself(history: History) -> None:
    merge = history.merge()
    assert target(history, "workflow_run", merge).sha == merge


def test_a_merge_followed_only_by_merges_still_plans_itself(history: History) -> None:
    merge = history.merge()
    history.merge()
    history.merge()
    assert target(history, "workflow_run", merge).sha == merge


def test_a_merge_already_applied_by_another_run_plans_mains_head(history: History) -> None:
    """#167: the daily run applied d5ba974 first; its own run must plan the state that left."""
    merge = history.merge()
    head = history.apply()
    found = target(history, "workflow_run", merge)
    assert found.sha == head
    assert merge[:7] in found.reason
    assert head[:7] in found.reason


def test_two_applies_after_a_merge_plan_mains_head(history: History) -> None:
    merge = history.merge()
    history.apply()
    head = history.apply()
    assert target(history, "workflow_run", merge).sha == head


def test_state_commits_then_a_later_merge_plan_the_last_state_commit(history: History) -> None:
    """The earlier merge is applied by its own run, whatever the later merge's CI concludes."""
    merge = history.merge()
    history.apply()
    last = history.apply()
    history.merge()
    found = target(history, "workflow_run", merge)
    assert found.sha == last
    assert merge[:7] in found.reason
    assert last[:7] in found.reason


def test_state_committed_after_a_later_merge_plans_nothing_and_names_it(
    history: History,
) -> None:
    merge = history.merge()
    later = history.merge()
    history.apply()
    found = target(history, "workflow_run", merge)
    assert found.sha is None
    assert later[:7] in found.reason


def test_the_later_merge_itself_then_plans_mains_head(history: History) -> None:
    history.merge()
    later = history.merge()
    head = history.apply()
    assert target(history, "workflow_run", later).sha == head


def test_the_apps_state_commit_plans_nothing(history: History) -> None:
    history.merge()
    state = history.apply()
    found = target(history, "workflow_run", state)
    assert found.sha is None
    assert "state commit" in found.reason


def test_a_break_glass_merge_changing_the_state_isnt_a_state_commit(history: History) -> None:
    """A local apply reaches main by a pull request, made by a person: a merge like any other."""
    merge = history.merge()
    later = history.merge(state=True)
    found = target(history, "workflow_run", merge)
    assert found.sha is None
    assert later[:7] in found.reason
    assert target(history, "workflow_run", later).sha == later


def test_a_state_only_commit_by_someone_else_isnt_a_state_commit(history: History) -> None:
    merge = history.merge()
    history.state += 1
    history.write(STATE, f"state {history.state}")
    git(history.path, "add", STATE)
    git(history.path, "commit", "-q", "-m", "chore: hand-made state")
    other = history.head()
    found = target(history, "workflow_run", merge)
    assert found.sha is None
    assert other[:7] in found.reason


def test_a_commit_main_doesnt_contain_is_refused(history: History) -> None:
    history.merge()
    git(history.path, "switch", "-q", "-c", "side")
    side = history.merge()
    git(history.path, "switch", "-q", "main")
    with pytest.raises(plan_target.RefusedError, match=side):
        target(history, "workflow_run", side)


def test_a_commit_git_doesnt_know_is_refused(history: History) -> None:
    with pytest.raises(plan_target.RefusedError, match="0" * 40):
        target(history, "workflow_run", "0" * 40)


@pytest.mark.parametrize("commit", ["", "abc1234", "main", "g" * 40])
def test_a_commit_that_isnt_a_full_sha_is_refused(history: History, commit: str) -> None:
    with pytest.raises(plan_target.RefusedError, match="full commit sha"):
        target(history, "workflow_run", commit)


@pytest.mark.parametrize("event", ["", "push", "pull_request", "Schedule"])
def test_an_unknown_event_is_refused(history: History, event: str) -> None:
    with pytest.raises(plan_target.RefusedError, match="event"):
        target(history, event, history.head())


def test_the_cli_prints_outputs_and_writes_the_summary(
    history: History, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    merge = history.merge()
    head = history.apply()
    summary = tmp_path / "summary.md"
    code = plan_target.main(
        [
            "--repo", str(history.path), "--event", "workflow_run", "--commit", merge,
            "--state-author", APP, "--main", "main", "--summary", str(summary),
        ]
    )  # fmt: skip
    assert code == 0
    assert capsys.readouterr().out == f"sha={head}\nplan=true\n"
    assert head[:7] in summary.read_text(encoding="utf-8")


def test_the_cli_says_plan_false_with_no_sha_when_nothing_is_planned(
    history: History, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    history.merge()
    state = history.apply()
    summary = tmp_path / "summary.md"
    code = plan_target.main(
        [
            "--repo", str(history.path), "--event", "workflow_run", "--commit", state,
            "--state-author", APP, "--main", "main", "--summary", str(summary),
        ]
    )  # fmt: skip
    assert code == 0
    assert capsys.readouterr().out == "sha=\nplan=false\n"
    assert "Nothing to plan" in summary.read_text(encoding="utf-8")


def test_the_cli_fails_on_a_refusal_naming_it(
    history: History, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    summary = tmp_path / "summary.md"
    code = plan_target.main(
        [
            "--repo", str(history.path), "--event", "push", "--commit", history.head(),
            "--state-author", APP, "--main", "main", "--summary", str(summary),
        ]
    )  # fmt: skip
    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "::error::" in captured.err
    assert "push" in captured.err
    assert not summary.exists()
