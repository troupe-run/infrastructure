"""Both plan jobs list the open issues with no milestone when their plan closes one (spec:
milestones, "A plan that closes a milestone lists the open issues with no milestone";
needed-for-milestones design D4).

GitHub runs the workflow, so these tests pin what it's given: in each job that shows a plan, a step
runs milestone_review.py on the plan's JSON after the check that it holds no key, and the step that
shows the plan includes its section. It reads with a token from the infrastructure App that reads
issues and pull requests on the milestone repositories, minted just before it, never the job's own
token: `pr-plan`'s, with `pull-requests: write`, saw only the pull requests (#247;
milestone-list-token design D1). No job gains a permission for it."""

import json
from typing import Any

import pytest
import yaml
from conftest import REPO

TOFU = REPO / ".github" / "workflows" / "tofu.yml"
MILESTONES = REPO / "tofu" / "milestones.json"
STEP = "Issues with no milestone"
MINT = "Token to read the issues"
INFRASTRUCTURE_APP = "5272634"
# What the list reads: issues, and pull requests, which open_issues_count counts too (design D1).
TOKEN_PERMISSIONS = {"permission-issues": "read", "permission-pull-requests": "read"}
CHECKED = "The plan holds no key"
SHOWN = {"pr-plan": "Post the plan on the pull request", "plan": "Show the plan for approval"}
# What each job may hold: the list adds nothing (needed-for-milestones design D4; its token is the
# App's, milestone-list-token design D1).
PERMISSIONS = {"pr-plan": {"contents": "read", "pull-requests": "write"}, "plan": None}


def tofu() -> dict[str, Any]:
    loaded = yaml.safe_load(TOFU.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def names(job: dict[str, Any]) -> list[str]:
    return [str(step.get("name")) for step in job["steps"]]


def step(job_name: str, name: str) -> dict[str, Any]:
    found = [s for s in tofu()["jobs"][job_name]["steps"] if s.get("name") == name]
    assert len(found) == 1, (job_name, name)
    only = found[0]
    assert isinstance(only, dict)
    return only


def milestone_repositories() -> list[str]:
    declared = json.loads(MILESTONES.read_text(encoding="utf-8"))
    repositories = declared["repositories"]
    assert isinstance(repositories, list)
    return [str(r) for r in repositories]


def test_each_plan_job_lists_the_issues_after_the_key_check_and_before_showing() -> None:
    for job_name, shown in SHOWN.items():
        job = tofu()["jobs"][job_name]
        order = names(job)
        assert order.count(STEP) == 1, job_name
        assert order.index(CHECKED) < order.index(STEP) < order.index(shown), job_name


def test_each_plan_job_mints_the_token_just_before_the_list_under_the_same_condition() -> None:
    for job_name in SHOWN:
        order = names(tofu()["jobs"][job_name])
        assert order.count(MINT) == 1, job_name
        assert order.index(MINT) + 1 == order.index(STEP), job_name
        assert step(job_name, MINT).get("if") == step(job_name, STEP).get("if"), job_name


def test_the_token_is_the_infrastructure_app_s_reading_issues_and_pull_requests_only() -> None:
    for job_name in SHOWN:
        minted = step(job_name, MINT)
        assert str(minted["uses"]).startswith("actions/create-github-app-token@"), job_name
        given = minted["with"]
        assert str(given["app-id"]) == INFRASTRUCTURE_APP, job_name
        assert given["private-key"] == "${{ secrets.TF_VAR_github_app_pem }}", job_name
        assert given["owner"] == "troupe-run", job_name
        permissions = {k: v for k, v in given.items() if str(k).startswith("permission-")}
        assert permissions == TOKEN_PERMISSIONS, job_name
        assert set(given) == {"app-id", "private-key", "owner", "repositories", *TOKEN_PERMISSIONS}


@pytest.mark.milestones
def test_the_token_reaches_exactly_the_milestone_repositories() -> None:
    expected = sorted(milestone_repositories())
    for job_name in SHOWN:
        listed = str(step(job_name, MINT)["with"]["repositories"]).split(",")
        assert sorted(r.strip() for r in listed) == expected, job_name


def test_the_step_reads_the_plan_json_with_the_minted_token_not_the_job_s_own() -> None:
    for job_name in SHOWN:
        listing = step(job_name, STEP)
        token_id = step(job_name, MINT).get("id")
        assert token_id, job_name
        minted = f"${{{{ steps.{token_id}.outputs.token }}}}"
        assert listing["env"] == {"GH_TOKEN": minted}, job_name
        run = " ".join(str(listing["run"]).split())
        assert "scripts/milestone_review.py" in run
        assert '--plan-json "$RUNNER_TEMP/plan.json"' in run
        assert '--summary "$RUNNER_TEMP/review.md"' in run
        assert "continue-on-error" not in listing, job_name  # a failed read must fail the job


def test_the_shown_plan_includes_the_list() -> None:
    for job_name, shown in SHOWN.items():
        step = next(s for s in tofu()["jobs"][job_name]["steps"] if s.get("name") == shown)
        assert 'cat "$RUNNER_TEMP/review.md"' in str(step["run"]), job_name


def test_no_plan_job_gains_a_permission() -> None:
    workflow = tofu()
    assert workflow["permissions"] == {"contents": "read"}
    for job_name, expected in PERMISSIONS.items():
        assert workflow["jobs"][job_name].get("permissions") == expected, job_name
