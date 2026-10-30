"""Both plan jobs list the open issues with no milestone when their plan closes one (spec:
milestones, "A plan that closes a milestone lists the open issues with no milestone";
needed-for-milestones design D4).

GitHub runs the workflow, so these tests pin what it's given: in each job that shows a plan, a step
runs milestone_review.py on the plan's JSON after the check that it holds no key, with the job's own
token and no new permission, and the step that shows the plan includes its section."""

from typing import Any

import yaml
from conftest import REPO

TOFU = REPO / ".github" / "workflows" / "tofu.yml"
STEP = "Issues with no milestone"
CHECKED = "The plan holds no key"
SHOWN = {"pr-plan": "Post the plan on the pull request", "plan": "Show the plan for approval"}
# What each job may hold: the review adds nothing (design D4).
PERMISSIONS = {"pr-plan": {"contents": "read", "pull-requests": "write"}, "plan": None}


def tofu() -> dict[str, Any]:
    loaded = yaml.safe_load(TOFU.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def names(job: dict[str, Any]) -> list[str]:
    return [str(step.get("name")) for step in job["steps"]]


def test_each_plan_job_lists_the_issues_after_the_key_check_and_before_showing() -> None:
    for job_name, shown in SHOWN.items():
        job = tofu()["jobs"][job_name]
        order = names(job)
        assert order.count(STEP) == 1, job_name
        assert order.index(CHECKED) < order.index(STEP) < order.index(shown), job_name


def test_the_step_reads_the_plan_json_with_the_job_s_own_token() -> None:
    for job_name in SHOWN:
        step = next(s for s in tofu()["jobs"][job_name]["steps"] if s.get("name") == STEP)
        assert step["env"] == {"GH_TOKEN": "${{ github.token }}"}, job_name
        run = " ".join(str(step["run"]).split())
        assert "scripts/milestone_review.py" in run
        assert '--plan-json "$RUNNER_TEMP/plan.json"' in run
        assert '--summary "$RUNNER_TEMP/review.md"' in run
        assert "continue-on-error" not in step, job_name  # a failed read must fail the job


def test_the_shown_plan_includes_the_list() -> None:
    for job_name, shown in SHOWN.items():
        step = next(s for s in tofu()["jobs"][job_name]["steps"] if s.get("name") == shown)
        assert 'cat "$RUNNER_TEMP/review.md"' in str(step["run"]), job_name


def test_no_plan_job_gains_a_permission() -> None:
    workflow = tofu()
    assert workflow["permissions"] == {"contents": "read"}
    for job_name, expected in PERMISSIONS.items():
        assert workflow["jobs"][job_name].get("permissions") == expected, job_name
