"""A scheduled or manual plan of main waits for green CI, and a red main fails it saying how to
recover (spec: ci-apply; plans-wait-for-ci design D2-D4).

Each test builds a real repository shaped like main's history (conftest.History). GitHub's CI runs
come from a fake `gh`, and time from a fake clock, so nothing waits for real.
"""

import re
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


IDENTICAL = {"status": "identical", "total_commits": 0, "commits": [], "files": []}
NEWER = "b496971" + "0" * 33
STATE_COMMIT = "9d29f66" + "0" * 33


def ahead(*files: str, commits: list[str] | None = None, total: int | None = None) -> Any:  # noqa: ANN401 (JSON)
    """GitHub's compare of the commit checked with main, as main_ci.py's --jq shapes it."""
    listed = [NEWER] if commits is None else commits
    return {
        "status": "ahead",
        "total_commits": len(listed) if total is None else total,
        "commits": listed,
        "files": list(files),
    }


class FakeCI:
    """CI's push runs on main, by commit. A commit's list is what each poll sees in turn; the last
    one stays. A commit not listed has no run. compare is GitHub's answer to comparing a commit
    with main (main unmoved, unless a test says otherwise), or what that read raises. files is
    what reading a commit's files answers, by commit (NEWER changes a script, unless a test says
    otherwise), or what that read raises."""

    def __init__(
        self,
        runs: dict[str, list[dict[str, Any] | None]],
        compare: Any = IDENTICAL,  # noqa: ANN401 (JSON)
        files: dict[str, Any] | None = None,
    ) -> None:
        self.runs = runs
        self.compare = compare
        self.files = {NEWER: ["scripts/main_ci.py"]} if files is None else files
        self.asked: list[str] = []
        self.compared: list[str] = []
        self.read_files: list[str] = []

    def __call__(self, args: list[str]) -> Any:  # noqa: ANN401 (JSON)
        if args[0] == "api" and "/commits/" in args[1]:
            sha = args[1].rsplit("/", 1)[1]
            self.read_files.append(sha)
            answer = self.files[sha]
            if isinstance(answer, BaseException):
                raise answer
            return answer
        if args[0] == "api":
            assert args[1].endswith("...main")
            self.compared.append(args[1])
            if isinstance(self.compare, BaseException):
                raise self.compare
            return self.compare
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
def test_every_conclusion_but_success_fails_with_main_unmoved(
    history: History, conclusion: str
) -> None:
    """FakeCI's compare answers identical, so a cancel here is one with main unmoved: by hand."""
    head = history.merge()
    result = gate(history, FakeCI({head: [run(7, "completed", conclusion)]}))
    assert not result.passed
    assert f"**{conclusion}**" in result.summary


def test_a_cancel_with_main_ahead_by_a_merge_is_superseded_naming_both_commits(
    history: History,
) -> None:
    head = history.merge()
    ci = FakeCI(
        {head: [run(7, "completed", "cancelled")]},
        compare=ahead("scripts/main_ci.py", "tofu/terraform.tfstate"),
    )
    result = gate(history, ci)
    assert result.passed
    assert result.superseded
    assert result.error == ""
    assert head[:7] in result.summary
    assert NEWER[:7] in result.summary
    assert f"{URL}7" in result.summary
    assert "isn't green" not in result.summary
    assert ci.compared == [f"repos/{{owner}}/{{repo}}/compare/{head}...main"]


def test_a_cancel_with_main_unmoved_fails_as_red(history: History) -> None:
    head = history.merge()
    result = gate(history, FakeCI({head: [run(7, "completed", "cancelled")]}, IDENTICAL))
    assert not result.passed
    assert not result.superseded
    assert "**cancelled**" in result.summary
    assert "isn't green" in result.summary


def test_a_cancel_with_only_state_commits_since_fails_as_red(history: History) -> None:
    head = history.merge()
    ci = FakeCI({head: [run(7, "completed", "cancelled")]}, ahead("tofu/terraform.tfstate"))
    result = gate(history, ci)
    assert not result.passed
    assert not result.superseded
    assert "tofu/terraform.tfstate" in result.summary


@pytest.mark.parametrize("status", ["behind", "diverged", "something_new"])
def test_a_cancel_compared_as_anything_but_ahead_or_identical_fails_naming_it(
    history: History, status: str
) -> None:
    head = history.merge()
    answer = {**ahead("scripts/main_ci.py"), "status": status}
    result = gate(history, FakeCI({head: [run(7, "completed", "cancelled")]}, answer))
    assert not result.passed
    assert not result.superseded
    assert f"**{status}**" in result.summary


def test_a_failed_compare_read_fails_with_its_error(history: History) -> None:
    head = history.merge()
    broken = main_ci.ReadError("HTTP 502: Bad Gateway")
    result = gate(history, FakeCI({head: [run(7, "completed", "cancelled")]}, broken))
    assert not result.passed
    assert not result.superseded
    assert "HTTP 502: Bad Gateway" in result.summary
    assert "HTTP 502: Bad Gateway" in result.error


@pytest.mark.parametrize(
    "answer",
    [
        [],
        {"status": "ahead"},
        {**ahead("scripts/main_ci.py"), "files": "scripts/main_ci.py"},
        {**ahead("scripts/main_ci.py"), "total_commits": "1"},
        {**ahead("scripts/main_ci.py"), "commits": [1]},
    ],
    ids=["a-list", "no-files", "files-not-a-list", "total-not-a-number", "commit-not-a-sha"],
)
def test_a_compare_answer_of_the_wrong_shape_fails(history: History, answer: Any) -> None:  # noqa: ANN401 (JSON)
    head = history.merge()
    result = gate(history, FakeCI({head: [run(7, "completed", "cancelled")]}, answer))
    assert not result.passed
    assert not result.superseded


def test_more_commits_than_compare_lists_reads_none_and_names_no_sha(history: History) -> None:
    head = history.merge()
    answer = ahead("scripts/main_ci.py", total=300)
    ci = FakeCI({head: [run(7, "completed", "cancelled")]}, answer)
    result = gate(history, ci)
    assert result.superseded
    assert "the newest merge on `main`" in result.summary
    assert NEWER[:7] not in result.summary
    assert ci.read_files == []


def test_a_merge_then_the_apps_state_commit_since_names_the_merge(history: History) -> None:
    head = history.merge()
    answer = ahead("scripts/main_ci.py", "tofu/terraform.tfstate", commits=[NEWER, STATE_COMMIT])
    files = {NEWER: ["scripts/main_ci.py"], STATE_COMMIT: ["tofu/terraform.tfstate"]}
    ci = FakeCI({head: [run(7, "completed", "cancelled")]}, answer, files)
    result = gate(history, ci)
    assert result.superseded
    assert NEWER[:7] in result.summary
    assert STATE_COMMIT[:7] not in result.summary
    assert ci.read_files == [STATE_COMMIT, NEWER]


def test_a_failed_read_of_a_commits_files_fails_as_red(history: History) -> None:
    head = history.merge()
    files = {NEWER: main_ci.ReadError("HTTP 502: Bad Gateway")}
    ci = FakeCI({head: [run(7, "completed", "cancelled")]}, ahead("scripts/main_ci.py"), files)
    result = gate(history, ci)
    assert not result.passed
    assert not result.superseded
    assert "HTTP 502: Bad Gateway" in result.summary


@pytest.mark.parametrize(
    "answer", [{}, "scripts/main_ci.py", [1]], ids=["object", "text", "number"]
)
def test_a_commits_files_of_the_wrong_shape_fail_as_red(history: History, answer: Any) -> None:  # noqa: ANN401 (JSON)
    head = history.merge()
    ci = FakeCI(
        {head: [run(7, "completed", "cancelled")]}, ahead("scripts/main_ci.py"), {NEWER: answer}
    )
    result = gate(history, ci)
    assert not result.passed
    assert not result.superseded


def test_no_listed_commit_changing_more_than_the_state_file_fails_as_red(history: History) -> None:
    """The compare's net files and its commits disagree: no guess at which merge plans it."""
    head = history.merge()
    files = {NEWER: ["tofu/terraform.tfstate"]}
    ci = FakeCI({head: [run(7, "completed", "cancelled")]}, ahead("scripts/main_ci.py"), files)
    result = gate(history, ci)
    assert not result.passed
    assert not result.superseded


@pytest.mark.parametrize("conclusion", ["failure", "timed_out", "startup_failure", "skipped"])
def test_conclusions_other_than_cancelled_fail_without_asking_whether_main_moved(
    history: History, conclusion: str
) -> None:
    head = history.merge()
    ci = FakeCI({head: [run(7, "completed", conclusion)]}, ahead("scripts/main_ci.py"))
    result = gate(history, ci)
    assert not result.passed
    assert not result.superseded
    assert ci.compared == []


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


def args_for(history: History, summary: Path) -> list[str]:
    return [
        "--repo", str(history.path), "--main", "main",
        "--repository", "troupe-run/infrastructure", "--summary", str(summary),
    ]  # fmt: skip


def test_main_prints_only_superseded_false_on_stdout_on_green_ci(
    history: History,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    head = history.merge()
    monkeypatch.setattr(main_ci, "gh", FakeCI({head: [run(1, "completed", "success")]}))
    assert main_ci.main(args_for(history, tmp_path / "summary.md")) == 0
    assert capsys.readouterr().out == "superseded=false\n"


def test_main_exits_0_printing_superseded_true_and_its_summary_when_a_merge_supersedes_it(
    history: History,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    head = history.merge()
    ci = FakeCI({head: [run(7, "completed", "cancelled")]}, ahead("scripts/main_ci.py"))
    monkeypatch.setattr(main_ci, "gh", ci)
    summary = tmp_path / "summary.md"
    assert main_ci.main(args_for(history, summary)) == 0
    out = capsys.readouterr()
    assert out.out == "superseded=true\n"
    assert "::error::" not in out.err
    assert NEWER[:7] in summary.read_text(encoding="utf-8")


def test_main_prints_only_name_value_lines_on_stdout_on_red_ci(
    history: History,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    head = history.merge()
    monkeypatch.setattr(main_ci, "gh", FakeCI({head: [run(1, "completed", "failure")]}))
    assert main_ci.main(args_for(history, tmp_path / "summary.md")) == 1
    out = capsys.readouterr().out
    assert all(re.fullmatch(r"[a-z_]+=[a-z]*", line) for line in out.splitlines())


def test_main_compares_with_main_in_the_repository_given(
    history: History, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = history.merge()
    ci = FakeCI({head: [run(7, "completed", "cancelled")]}, IDENTICAL)
    monkeypatch.setattr(main_ci, "gh", ci)
    main_ci.main(args_for(history, tmp_path / "summary.md"))
    assert ci.compared == [f"repos/troupe-run/infrastructure/compare/{head}...main"]


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
