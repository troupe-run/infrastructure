"""A plan that closes a milestone lists the open issues with no milestone (spec: milestones, "A plan
that closes a milestone lists the open issues with no milestone", "The list of issues with no
milestone is never silently short"; needed-for-milestones design D4).

The plan changes are written in `tofu show -json`'s shape for resource_changes. No real plan here
closes a milestone yet, so the script refuses any milestone change whose state it can't read: every
plan lists each milestone, unchanged ones as no-op, so a shape it misreads fails every plan rather
than hiding a close. The issues are the API's shape, trimmed to the fields the script reads.

The fake answers like GitHub's issues list: every open issue and pull request, with or without a
milestone, and `open_issues_count` counts them all. A token that can't see some of them (#247: a
job token with `pull-requests: write` saw only the pull requests) is a count above what's listed.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from conftest import REPO

import milestone_review as mr

REPOSITORIES = ["troupe", "infrastructure", "website", ".github"]
DECLARED = {"repositories": REPOSITORIES, "milestones": []}


def change(repo: str, before: str, after: str, title: str = "0.1.0") -> dict[str, Any]:
    """One milestone's entry in resource_changes, as `tofu show -json` writes it."""
    actions = ["no-op"] if before == after else ["update"]
    values = {"owner": "troupe-run", "repository": repo, "title": title, "description": "d"}
    return {
        "address": f'github_repository_milestone.release["{repo}/{title}"]',
        "mode": "managed",
        "type": "github_repository_milestone",
        "name": "release",
        "index": f"{repo}/{title}",
        "change": {
            "actions": actions,
            "before": {**values, "state": before},
            "after": {**values, "state": after},
        },
    }


def plan(*changes: dict[str, Any]) -> dict[str, Any]:
    other = {
        "address": "github_repository.this",
        "type": "github_repository",
        "name": "this",
        "change": {"actions": ["no-op"], "before": {"name": "troupe"}, "after": {"name": "troupe"}},
    }
    return {"format_version": "1.2", "resource_changes": [other, *changes]}


def closing(title: str = "0.1.0") -> dict[str, Any]:
    return plan(*(change(repo, "open", "closed", title) for repo in REPOSITORIES))


def issue(
    repo: str, number: int, title: str = "Some work", milestone: str | None = None
) -> dict[str, Any]:
    return {
        "number": number,
        "title": title,
        "html_url": f"https://github.com/troupe-run/{repo}/issues/{number}",
        "milestone": None if milestone is None else {"title": milestone},
    }


def pull(repo: str, number: int) -> dict[str, Any]:
    return {**issue(repo, number, "Bump something"), "pull_request": {"url": "x"}}


class FakeGitHub:
    """Answers `gh api` reads from per-repository data, a page per list, and records each path.

    `counts` gives a repository's `open_issues_count`; by default it's how many are listed."""

    def __init__(
        self,
        issues: dict[str, list[list[dict[str, Any]]]],
        counts: dict[str, Any] | None = None,
        **fail: bool,
    ) -> None:
        self.issues = issues
        self.counts = counts or {}
        self.fail = fail
        self.paths: list[str] = []

    def __call__(self, args: list[str], stdin: str | None) -> mr.GhResult:
        assert args[0] == "api"
        assert stdin is None
        path = args[-1]
        self.paths.append(path)
        repo = path.split("/")[2].split("?")[0]
        if self.fail.get(repo.lstrip(".")):
            return mr.GhResult(1, "", f"gh: {repo} is down (HTTP 502)")
        if "/issues?" in path:
            assert "--paginate" in args
            assert "--slurp" in args
            assert "milestone=" not in path  # every open item, so the count can be checked
            assert "state=open" in path
            return mr.GhResult(0, json.dumps(self.issues.get(repo, [[]])), "")
        listed = sum(len(page) for page in self.issues.get(repo, [[]]))
        about = {
            "name": repo,
            "has_issues": repo != ".github",
            "open_issues_count": self.counts.get(repo, listed),
        }
        if self.counts.get(repo, listed) is None:
            del about["open_issues_count"]
        return mr.GhResult(0, json.dumps(about), "")


def run(
    tmp_path: Path, planned: dict[str, Any], gh: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str, str]:
    plan_json = tmp_path / "plan.json"
    plan_json.write_text(json.dumps(planned))
    declared = tmp_path / "milestones.json"
    declared.write_text(json.dumps(DECLARED))
    summary = tmp_path / "review.md"
    code = mr.main(
        ["--plan-json", str(plan_json), "--summary", str(summary), "--milestones", str(declared)],
        gh,
    )
    written = summary.read_text(encoding="utf-8") if summary.exists() else "<not written>"
    captured = capsys.readouterr()
    return code, written, captured.out + captured.err


def test_a_plan_closing_a_release_lists_it_once_with_each_repository_s_issues(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    troupe = [issue("troupe", n) for n in (197, 156, 201, 205)]
    gh = FakeGitHub({"troupe": [troupe]})
    code, written, _ = run(tmp_path, closing(), gh, capsys)
    assert code == 0
    assert written.count("0.1.0") == 1
    assert "troupe: 4" in written
    for each in troupe:
        assert f"[#{each['number']}]({each['html_url']})" in written
    assert "infrastructure: none" in written
    assert "website: none" in written
    assert "4 open issues with no milestone" in written
    for outcome in ("into a milestone", "`parked`", "not planned"):
        assert outcome in written


def test_a_plan_closing_nothing_writes_an_empty_section_and_reads_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gh = FakeGitHub({})
    unchanged = plan(*(change(repo, "open", "open") for repo in REPOSITORIES))
    code, written, out = run(tmp_path, unchanged, gh, capsys)
    assert (code, written, gh.paths) == (0, "", [])
    assert "4 milestone changes" in out
    assert "none closes a milestone" in out


def test_a_re_described_milestone_lists_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    redescribed = change("troupe", "open", "open")
    redescribed["change"]["actions"] = ["update"]
    redescribed["change"]["after"]["description"] = "new"
    code, written, _ = run(tmp_path, plan(redescribed), FakeGitHub({}), capsys)
    assert (code, written) == (0, "")


def test_a_repository_with_issues_off_is_left_out_and_said_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gh = FakeGitHub({})
    code, written, _ = run(tmp_path, closing(), gh, capsys)
    assert code == 0
    assert "`.github`: left out, its issues are off" in written
    assert not any(p.startswith("repos/troupe-run/.github/issues") for p in gh.paths)


def test_pull_requests_are_left_out(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    gh = FakeGitHub({"website": [[pull("website", 55), issue("website", 80)]]})
    _, written, _ = run(tmp_path, closing(), gh, capsys)
    assert "website: 1" in written
    assert "#55" not in written


def test_issues_with_a_milestone_are_left_out(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    planned = issue("troupe", 12, milestone="0.2.0")
    gh = FakeGitHub({"troupe": [[planned, issue("troupe", 13)]]})
    code, written, _ = run(tmp_path, closing(), gh, capsys)
    assert code == 0
    assert "troupe: 1" in written
    assert "[#13]" in written
    assert "#12" not in written


def test_a_read_short_of_github_s_count_fails_naming_the_repository_and_both_numbers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # #245: the token saw troupe's pull requests and none of its issues.
    pulls = [pull("troupe", n) for n in (301, 302, 303)]
    gh = FakeGitHub({"troupe": [pulls]}, counts={"troupe": 17})
    code, written, said = run(tmp_path, closing(), gh, capsys)
    assert (code, written) == (1, "<not written>")
    assert "troupe-run/troupe" in said
    assert "read 3" in said
    assert "GitHub counts 17" in said


def test_a_read_above_github_s_count_lists_as_it_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # An issue opened between reading the count and reading the list.
    gh = FakeGitHub({"troupe": [[issue("troupe", 7), issue("troupe", 8)]]}, counts={"troupe": 1})
    code, written, _ = run(tmp_path, closing(), gh, capsys)
    assert code == 0
    assert "troupe: 2" in written


def test_an_issue_without_a_milestone_field_fails_rather_than_counting_as_none(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bare = issue("troupe", 7)
    del bare["milestone"]
    code, written, said = run(tmp_path, closing(), FakeGitHub({"troupe": [[bare]]}), capsys)
    assert (code, written) == (1, "<not written>")
    assert "no milestone field" in said


@pytest.mark.parametrize("count", [None, "17", True])
def test_a_count_that_can_t_be_read_fails_and_writes_no_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], count: object
) -> None:
    gh = FakeGitHub({"troupe": [[issue("troupe", 7)]]}, counts={"troupe": count})
    code, written, said = run(tmp_path, closing(), gh, capsys)
    assert (code, written) == (1, "<not written>")
    assert "troupe-run/troupe" in said
    assert "open_issues_count" in said


def test_every_page_is_read(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pages = [
        [issue("troupe", n) for n in range(1, 101)],
        [issue("troupe", n) for n in range(101, 151)],
    ]
    _, written, _ = run(tmp_path, closing(), FakeGitHub({"troupe": pages}), capsys)
    assert "troupe: 150" in written
    assert "[#150]" in written


def test_a_repository_that_can_t_be_read_fails_naming_it_and_writes_no_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gh = FakeGitHub({"website": [[issue("website", 80)]]}, troupe=True)
    plan_json = tmp_path / "plan.json"
    plan_json.write_text(json.dumps(closing()))
    declared = tmp_path / "milestones.json"
    declared.write_text(json.dumps(DECLARED))
    summary = tmp_path / "review.md"
    code = mr.main(
        ["--plan-json", str(plan_json), "--summary", str(summary), "--milestones", str(declared)],
        gh,
    )
    assert code == 1
    assert not summary.exists()
    assert "troupe-run/troupe" in capsys.readouterr().err


def test_a_milestone_change_whose_state_can_t_be_read_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    misread = change("troupe", "open", "closed")
    del misread["change"]["after"]["state"]
    code, written, said = run(tmp_path, plan(misread), FakeGitHub({}), capsys)
    assert (code, written) == (2, "<not written>")
    assert 'github_repository_milestone.release["troupe/0.1.0"]' in said


def test_a_title_reaches_the_comment_as_text_not_markup(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hostile = "Fix `x` for @someone, see #12 and [here](https://example.com) <b>"
    gh = FakeGitHub({"troupe": [[issue("troupe", 9, hostile)]]})
    _, written, _ = run(tmp_path, closing(), gh, capsys)
    line = next(line for line in written.splitlines() if "[#9]" in line)
    assert "`` Fix `x` for @someone, see #12 and [here](https://example.com) <b> ``" in line


def test_two_milestones_closing_are_both_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    both = plan(
        change("troupe", "open", "closed", "0.1.0"), change("troupe", "open", "closed", "0.2.0")
    )
    _, written, _ = run(tmp_path, both, FakeGitHub({}), capsys)
    assert "0.1.0 and 0.2.0" in written


@pytest.mark.milestones
def test_the_real_declaration_names_the_repositories_to_read() -> None:
    declared = json.loads((REPO / "tofu" / "milestones.json").read_text(encoding="utf-8"))
    assert mr.repositories(declared) == declared["repositories"]
