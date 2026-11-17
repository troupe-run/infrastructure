"""The weekly mutation run and the pull request report hold no secret where they run code, never
block a merge, and keep their budgets and token in step with their declarations (spec:
mutation-testing, mutation-issue-credentials; lint-mutation design D3, D4, D9)."""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO
from test_dependabot_issues_workflow import (
    apps,
    declared_inputs,
    environment_of,
    steps_using,
    token_problems,
)

import mutation_settings as ms

pytestmark = [pytest.mark.mutation, pytest.mark.oob, pytest.mark.tofu, pytest.mark.schedules]

WEEKLY = REPO / ".github" / "workflows" / "mutation.yml"
PR = REPO / ".github" / "workflows" / "mutation-pr.yml"
SETTINGS = ms.load_settings((REPO / "scripts" / "mutation.json").read_text(encoding="utf-8"))
APP = "troupe-run-test-quality"


def load(path: Path) -> dict[Any, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def triggers(workflow: dict[Any, Any]) -> set[str]:
    # PyYAML reads the key `on` as True.
    return set(workflow.get(True) or workflow.get("on") or {})


# The weekly run


def test_the_weekly_run_runs_on_its_schedule_and_by_hand_only() -> None:
    workflow = load(WEEKLY)
    assert triggers(workflow) == {"schedule", "workflow_dispatch"}
    assert workflow[True]["schedule"] == [{"cron": "23 3 * * 0"}]
    assert workflow["permissions"] == {}
    assert workflow["concurrency"] == {"group": "mutation", "cancel-in-progress": False}


def test_the_mutate_job_holds_no_secret_and_has_the_budget() -> None:
    mutate = load(WEEKLY)["jobs"]["mutate"]
    assert mutate["permissions"] == {"contents": "read", "actions": "read"}
    assert "environment" not in mutate
    assert "secrets." not in json.dumps(mutate)
    timeout, budget = mutate["timeout-minutes"], SETTINGS.budget_minutes
    assert timeout == budget + 30, f"mutate's timeout is {timeout}; budget_minutes is {budget}"
    assert mutate["strategy"]["matrix"]["repository"] == sorted(
        SETTINGS.repositories, key=["troupe", "infrastructure", "website"].index
    )


def test_the_issues_job_checks_out_only_this_repository_and_asks_for_the_apps_permissions() -> None:
    issues = load(WEEKLY)["jobs"]["issues"]
    assert environment_of(issues) == "mutation-issues"
    assert issues["permissions"] == {"contents": "read", "pull-requests": "read"}
    for step in steps_using(issues, "actions/checkout"):
        given = step.get("with") or {}
        assert "repository" not in given, given
        assert "ref" not in given, given
    granted = declared_inputs(apps(), APP)
    assert granted == {"permission-issues": "write"}, f"{APP} is declared with {granted}"
    problems = token_problems(
        issues, "issues", "TEST_QUALITY_APP_PRIVATE_KEY", "TEST_QUALITY_APP_CLIENT_ID", granted
    )
    assert problems == []


def test_the_token_asking_for_more_than_the_app_is_granted_is_named() -> None:
    issues = load(WEEKLY)["jobs"]["issues"]
    [mint] = steps_using(issues, "create-github-app-token")
    mint["with"]["permission-pull-requests"] = "write"
    problems = token_problems(
        issues,
        "issues",
        "TEST_QUALITY_APP_PRIVATE_KEY",
        "TEST_QUALITY_APP_CLIENT_ID",
        {"permission-issues": "write"},
    )
    assert problems == [
        "issues's token asks for permission-pull-requests: write, which it isn't granted"
    ]


def test_the_board_job_adds_only_issues_in_the_three_repositories() -> None:
    board = load(WEEKLY)["jobs"]["board"]
    assert environment_of(board) == "board"
    script = board["steps"][-1]["run"]
    assert (
        "^https://github\\.com/troupe-run/(troupe|website|infrastructure)/issues/[0-9]+$" in script
    )


def test_the_weekly_run_is_watched_for_stopping() -> None:
    watched = json.loads((REPO / "scripts" / "watched-schedules.json").read_text(encoding="utf-8"))
    assert {
        "repository": "infrastructure",
        "workflow": "mutation.yml",
        "max_age_days": 8,
    } in watched


# The pull request report


def test_the_pull_request_report_runs_on_pull_requests_only() -> None:
    workflow = load(PR)
    assert triggers(workflow) == {"pull_request"}
    assert workflow["permissions"] == {}


def test_the_job_that_runs_the_pull_requests_code_holds_no_write_token() -> None:
    mutate = load(PR)["jobs"]["mutate"]
    assert mutate["permissions"] == {"contents": "read"}
    assert "environment" not in mutate
    assert "secrets." not in json.dumps(mutate)
    assert mutate["if"] == "${{ !github.event.pull_request.draft }}"
    assert mutate["timeout-minutes"] == SETTINGS.pr_budget_minutes + 30


def test_the_comment_job_checks_out_the_base_commit_only() -> None:
    comment = load(PR)["jobs"]["comment"]
    assert comment["permissions"] == {"contents": "read", "pull-requests": "write"}
    [checkout] = steps_using(comment, "actions/checkout")
    assert checkout["with"] == {"ref": "${{ github.event.pull_request.base.sha }}"}


def test_neither_workflow_is_a_required_check() -> None:
    required = json.loads((REPO / "tofu" / "required-checks.json").read_text(encoding="utf-8"))
    contexts = {check["context"] for checks in required.values() for check in checks}
    names = {
        job.get("name", key) for path in (WEEKLY, PR) for key, job in load(path)["jobs"].items()
    }
    assert not contexts & names, contexts & names


def test_the_pull_request_report_and_what_it_runs_are_delivered() -> None:
    import tofu_text

    delivered = set(
        tofu_text.guard_files((REPO / "tofu" / "guard_delivery.tf").read_text(encoding="utf-8"))
    )
    needed = {
        ".github/workflows/mutation-pr.yml",
        "scripts/mutation.json",
        "scripts/mutation_children.py",
        "scripts/mutation_pr.py",
        "scripts/mutation_report.py",
        "scripts/mutation_run.py",
        "scripts/mutation_settings.py",
    }
    assert needed <= delivered, needed - delivered
    # The weekly run, its issue upkeep and the App's credential stay here.
    assert not {".github/workflows/mutation.yml", "scripts/mutation_issues.py"} & delivered
