"""tofu.yml on a draft pull request (spec: ci-apply, "A draft pull request isn't tested or planned
until it's ready"; ci-once-per-commit design D2): `changes` answers plan=false, so `plan (pull
request)` is skipped and asks the owner for no approval, and marking it ready runs both again.

The conditions are evaluated as GitHub does, with test_tofu_merge_group's evaluator."""

import copy
from typing import Any

import pytest
from test_tofu_merge_group import evaluate, tofu

PULL_REQUEST_TYPES = ["opened", "synchronize", "reopened", "ready_for_review"]


def step(job: dict[str, Any], ident: str) -> dict[str, Any]:
    return next((each for each in job["steps"] if each.get("id") == ident), {})


def problems(workflow: dict[Any, Any]) -> list[str]:
    found = []
    types = (workflow[True].get("pull_request") or {}).get("types")  # YAML 1.1 reads `on` as true
    if types != PULL_REQUEST_TYPES:
        found.append(f"pull requests trigger on {types!r}, not {PULL_REQUEST_TYPES!r}")
    changes = workflow["jobs"]["changes"]
    draft = step(changes, "draft")
    if draft.get("if") != "github.event.pull_request.draft" or "plan=false" not in str(
        draft.get("run")
    ):
        found.append("changes doesn't answer plan=false on a draft")
    if step(changes, "paths").get("if") != "${{ !github.event.pull_request.draft }}":
        found.append("changes reads a draft's paths too")
    plan = str(changes.get("outputs", {}).get("plan", ""))
    if "steps.draft.outputs.plan" not in plan or "steps.paths.outputs.plan" not in plan:
        found.append(f"changes' plan output is {plan!r}, not the draft's or the paths' answer")
    return found


def test_a_draft_asks_for_no_plan_and_ready_asks_again() -> None:
    assert problems(tofu()) == []


def test_a_draft_s_answer_skips_the_pr_plan() -> None:
    """`changes` answered plan=false, as it does on a draft: pr-plan's condition fails, so the job
    is skipped before its environment asks for an approval."""
    jobs = tofu()["jobs"]
    context = {
        "github.event_name": "pull_request",
        "needs.changes.result": "success",
        "needs.changes.outputs.plan": "false",
    }
    assert not evaluate(jobs["pr-plan"]["if"], context)


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (lambda w: w[True].update(pull_request=None), "pull requests trigger on"),
        (
            lambda w: w[True]["pull_request"]["types"].remove("ready_for_review"),
            "pull requests trigger on",
        ),
        (
            lambda w: w["jobs"]["changes"]["steps"].pop(0),
            "doesn't answer plan=false on a draft",
        ),
        (
            lambda w: step(w["jobs"]["changes"], "paths").pop("if"),
            "reads a draft's paths too",
        ),
        (
            lambda w: w["jobs"]["changes"]["outputs"].update(
                plan="${{ steps.paths.outputs.plan }}"
            ),
            "plan output",
        ),
    ],
)
def test_a_broken_draft_rule_is_named(change: Any, named: str) -> None:  # noqa: ANN401
    workflow = copy.deepcopy(tofu())
    change(workflow)
    assert any(named in problem for problem in problems(workflow)), problems(workflow)
