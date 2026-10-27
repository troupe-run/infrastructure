"""A scheduled or manual plan of main waits for green CI, and a red main fails it saying how to
recover (spec: ci-apply; plans-wait-for-ci design D2-D4).

Each test builds a real repository shaped like main's history (conftest.History). GitHub's CI runs
come from a fake `gh`, and time from a fake clock, so nothing waits for real.
"""

from pathlib import Path
from typing import Any

import pytest
from conftest import History

import guard
import main_ci

URL = "https://github.com/troupe-run/infrastructure/actions/runs/"


@pytest.fixture(autouse=True)
def no_hook_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    """The script reads git where it runs; under a pre-commit hook, GIT_DIR points elsewhere."""
    for name in guard.REPOSITORY_LOCATION_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def run(number: int, status: str, conclusion: str = "") -> dict[str, Any]:
    return {
        "databaseId": number,
        "status": status,
        "conclusion": conclusion,
        "url": f"{URL}{number}",
    }


class FakeCI:
    """CI's push runs on main, by commit. A commit's list is what each poll sees in turn; the last
    one stays. A commit not listed has no run."""

    def __init__(self, runs: dict[str, list[dict[str, Any] | None]]) -> None:
        self.runs = runs
        self.asked: list[str] = []

    def __call__(self, args: list[str]) -> Any:  # noqa: ANN401 (JSON)
        assert args[:2] == ["run", "list"]
        assert args[args.index("--workflow") + 1] == "ci.yml"
        assert args[args.index("--event") + 1] == "push"
        assert args[args.index("--branch") + 1] == "main"
        sha = args[args.index("--commit") + 1]
        self.asked.append(sha)
        seen = self.runs.get(sha, [None])
        found = seen.pop(0) if len(seen) > 1 else seen[0]
        return [] if found is None else [found]


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept = 0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds
        self.slept += 1


def gate(history: History, ci: FakeCI, clock: Clock | None = None) -> main_ci.Result:
    clock = clock or Clock()
    return main_ci.wait_for_ci(history.path, "main", ci, now=clock.time, sleep=clock.sleep)


def test_green_ci_on_the_head_merge_passes(history: History) -> None:
    head = history.merge()
    result = gate(history, FakeCI({head: [run(1, "completed", "success")]}))
    assert result.passed
    assert result.sha == head


def test_the_apps_state_commit_at_the_head_is_looked_past_to_the_merge(history: History) -> None:
    merge = history.merge()
    history.apply()
    result = gate(history, FakeCI({merge: [run(1, "completed", "success")]}))
    assert result.passed
    assert result.sha == merge


def test_a_persons_state_only_commit_with_no_ci_run_is_looked_past(history: History) -> None:
    """A break-glass state merge: CI's paths-ignore skips it whoever made it."""
    merge = history.merge()
    history.state_only()
    result = gate(history, FakeCI({merge: [run(1, "completed", "success")]}))
    assert result.passed
    assert result.sha == merge


def test_a_state_only_last_commit_with_a_ci_run_is_the_one_checked(history: History) -> None:
    """A push of a merge and then a state-only commit: CI runs on the push's last commit."""
    history.merge()
    last = history.state_only()
    result = gate(history, FakeCI({last: [run(1, "completed", "failure")]}))
    assert not result.passed
    assert result.sha == last


def test_a_merge_with_no_run_yet_waits_until_one_appears(history: History) -> None:
    head = history.merge()
    clock = Clock()
    ci = FakeCI({head: [None, None, run(1, "queued"), run(1, "completed", "success")]})
    result = gate(history, ci, clock)
    assert result.passed
    assert clock.slept == 3


def test_a_run_found_on_a_later_commit_of_the_push_is_used_once_it_appears(
    history: History,
) -> None:
    """The walk runs again at every poll: before the run appears on the state-only last commit, it
    waits on the merge before it."""
    merge = history.merge()
    last = history.state_only()
    ci = FakeCI({last: [None, run(1, "completed", "success")]})
    result = gate(history, ci)
    assert result.passed
    assert result.sha == last
    assert merge in ci.asked


def test_queued_then_running_then_success_passes(history: History) -> None:
    head = history.merge()
    clock = Clock()
    ci = FakeCI({head: [run(1, "queued"), run(1, "in_progress"), run(1, "completed", "success")]})
    assert gate(history, ci, clock).passed
    assert clock.slept == 2


@pytest.mark.parametrize("status", ["waiting", "requested", "pending"])
def test_each_waiting_status_is_waited_for(history: History, status: str) -> None:
    head = history.merge()
    ci = FakeCI({head: [run(1, status), run(1, "completed", "success")]})
    assert gate(history, ci).passed


def test_running_then_failure_fails(history: History) -> None:
    head = history.merge()
    ci = FakeCI({head: [run(1, "in_progress"), run(1, "completed", "failure")]})
    result = gate(history, ci)
    assert not result.passed
    assert "failure" in result.summary


@pytest.mark.parametrize(
    "conclusion",
    [
        "failure",
        "cancelled",
        "timed_out",
        "startup_failure",
        "action_required",
        "neutral",
        "skipped",
        "stale",
        "something_new",
    ],
)
def test_every_conclusion_but_success_fails(history: History, conclusion: str) -> None:
    head = history.merge()
    result = gate(history, FakeCI({head: [run(7, "completed", conclusion)]}))
    assert not result.passed
    assert f"**{conclusion}**" in result.summary


def test_an_unknown_status_fails_naming_it(history: History) -> None:
    head = history.merge()
    result = gate(history, FakeCI({head: [run(1, "paused_for_lunch")]}))
    assert not result.passed
    assert "paused_for_lunch" in result.summary
    assert "paused_for_lunch" in result.error


def test_a_failed_gh_read_fails_with_its_error(history: History) -> None:
    history.merge()

    def broken(args: list[str]) -> Any:  # noqa: ANN401 (JSON)
        raise main_ci.ReadError("HTTP 502: Bad Gateway")

    result = main_ci.wait_for_ci(
        history.path, "main", broken, now=lambda: 0.0, sleep=lambda _: None
    )
    assert not result.passed
    assert "HTTP 502: Bad Gateway" in result.error
    assert "HTTP 502: Bad Gateway" in result.summary


def test_ci_that_doesnt_finish_in_time_fails_naming_the_commit(history: History) -> None:
    head = history.merge()
    clock = Clock()
    result = gate(history, FakeCI({head: [run(3, "in_progress")]}), clock)
    assert not result.passed
    assert clock.now >= main_ci.LIMIT_SECONDS
    assert "didn't finish" in result.summary
    assert head[:7] in result.summary
    assert f"{URL}3" in result.summary


def test_a_commit_with_no_run_by_the_limit_fails_saying_ci_didnt_start(history: History) -> None:
    head = history.merge()
    result = gate(history, FakeCI({}))
    assert not result.passed
    assert "didn't finish" in result.summary
    assert head[:7] in result.summary


def test_the_red_summary_names_the_commit_links_the_run_and_lists_the_ways_out(
    history: History,
) -> None:
    head = history.merge()
    result = gate(history, FakeCI({head: [run(42, "completed", "failure")]}))
    assert head[:7] in result.summary
    assert "feat: merge 1" in result.summary
    assert f"{URL}42" in result.summary
    assert "fix pull request" in result.summary
    assert "gh run rerun 42 --failed" in result.summary
    assert "Break-glass" in result.summary
    assert head[:7] in result.error


def test_a_pass_writes_one_line_naming_the_commit_and_run(history: History) -> None:
    head = history.merge()
    result = gate(history, FakeCI({head: [run(5, "completed", "success")]}))
    assert result.summary.strip().count("\n") == 0
    assert head[:7] in result.summary
    assert f"{URL}5" in result.summary
    assert result.error == ""


def test_main_exits_0_and_appends_the_summary_on_green_ci(
    history: History, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = history.merge()
    monkeypatch.setattr(main_ci, "gh", FakeCI({head: [run(1, "completed", "success")]}))
    summary = tmp_path / "summary.md"
    summary.write_text("before\n", encoding="utf-8")
    code = main_ci.main(
        [
            "--repo", str(history.path), "--main", "main",
            "--repository", "troupe-run/infrastructure", "--summary", str(summary),
        ]
    )  # fmt: skip
    assert code == 0
    text = summary.read_text(encoding="utf-8")
    assert text.startswith("before\n")
    assert head[:7] in text


def test_main_exits_1_with_an_error_annotation_on_red_ci(
    history: History,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    head = history.merge()
    monkeypatch.setattr(main_ci, "gh", FakeCI({head: [run(1, "completed", "failure")]}))
    summary = tmp_path / "summary.md"
    code = main_ci.main(
        [
            "--repo", str(history.path), "--main", "main",
            "--repository", "troupe-run/infrastructure", "--summary", str(summary),
        ]
    )  # fmt: skip
    assert code == 1
    assert "::error::" in capsys.readouterr().err
    assert "gh run rerun 1 --failed" in summary.read_text(encoding="utf-8")


def test_main_passes_the_repository_to_gh(
    history: History, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = history.merge()
    asked: list[list[str]] = []
    ci = FakeCI({head: [run(1, "completed", "success")]})

    def recording(args: list[str]) -> Any:  # noqa: ANN401 (JSON)
        asked.append(args)
        return ci(args)

    monkeypatch.setattr(main_ci, "gh", recording)
    main_ci.main(
        [
            "--repo", str(history.path), "--main", "main",
            "--repository", "troupe-run/infrastructure", "--summary", str(tmp_path / "s.md"),
        ]
    )  # fmt: skip
    assert all(a[a.index("--repo") + 1] == "troupe-run/infrastructure" for a in asked)
