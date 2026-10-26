"""tofu.yml plans, and applies, the commit plan_target.py names, so each plan of main reads main's
current state (spec: ci-apply, "A plan of main reads main's current state"; plan-each-merge-once
design D3).

GitHub runs the workflow, so these tests pin what it's given: main fetched with its history before
the script, the script's answer checked out, every later step gated on it, and its `sha` the one
the guard wait, the summary and the apply use. test_plan_target.py tests the answer itself."""

import copy
from collections.abc import Callable
from typing import Any

import pytest
import yaml
from conftest import REPO

TOFU = REPO / ".github" / "workflows" / "tofu.yml"

TARGET_SHA = "${{ steps.target.outputs.sha }}"
GATE = "steps.target.outputs.plan == 'true'"
# Outputs of steps that are themselves gated: a step reading only these is gated too.
GATED_OUTPUTS = ("steps.plan.outputs.", "steps.modes.outputs.")
# Where the commit a run was started for comes from; only the target step may read them.
STARTED_FOR = ("github.event.workflow_run.head_sha", "github.sha")
CHECKOUT = "actions/checkout"


def tofu() -> dict[str, Any]:
    loaded = yaml.safe_load(TOFU.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def named(steps: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    found = [step for step in steps if step.get("name") == name]
    return found[0] if len(found) == 1 else None


def problems(workflow: dict[str, Any]) -> list[str]:
    found = []
    plan = workflow["jobs"]["plan"]
    steps: list[dict[str, Any]] = plan["steps"]
    targets = [i for i, step in enumerate(steps) if "scripts/plan_target.py" in step.get("run", "")]
    if len(targets) != 1 or steps[targets[0]].get("id") != "target":
        return [f"plan runs scripts/plan_target.py in {len(targets)} steps, not once as `target`"]
    at = targets[0]
    target = steps[at]
    run = target["run"]
    for expected in (
        '--state-author "$STATE_AUTHOR"',
        "--main origin/main",
        '--summary "$GITHUB_STEP_SUMMARY"',
        '>> "$GITHUB_OUTPUT"',
    ):
        if expected not in run:
            found.append(f"the target step doesn't pass {expected}")
    if "github.event.workflow_run.head_sha" not in str(target.get("env", {}).get("COMMIT", "")):
        found.append("the target step isn't given the commit CI ran on")

    checkouts = [i for i, step in enumerate(steps) if CHECKOUT in str(step.get("uses", ""))]
    if len(checkouts) != 1:
        found.append(f"plan has {len(checkouts)} checkouts, not one of main")
    else:
        fetch = steps[checkouts[0]].get("with", {})
        if checkouts[0] > at or fetch.get("ref") != "main" or fetch.get("fetch-depth") != 0:
            found.append("main isn't checked out with its history before the target step")

    switch = named(steps, "Check out that commit")
    if (
        switch is None
        or steps.index(switch) != at + 1
        or switch.get("if") != GATE
        or switch.get("env", {}).get("SHA") != TARGET_SHA
        or 'git checkout -q --detach "$SHA"' not in switch.get("run", "")
    ):
        found.append("the target's commit isn't checked out straight after it, gated on it")

    for step in steps[at + 1 :]:
        condition = str(step.get("if", ""))
        if GATE not in condition and not any(output in condition for output in GATED_OUTPUTS):
            found.append(f"{step.get('name', step.get('uses'))!r} runs whatever the target says")
    for step in steps:
        if step is target:
            continue
        if any(source in str(step) for source in STARTED_FOR):
            found.append(
                f"{step.get('name', step.get('uses'))!r} reads the commit the run started for"
            )

    if plan.get("outputs", {}).get("sha") != TARGET_SHA:
        found.append("plan's sha output isn't the target's")
    for name in ("Wait for the guard check on this commit", "Show the plan for approval"):
        uses = named(steps, name)
        if uses is None or uses.get("env", {}).get("SHA") != TARGET_SHA:
            found.append(f"{name!r} doesn't use the target's sha")

    apply = workflow["jobs"]["apply"]
    apply_checkout = [s for s in apply["steps"] if CHECKOUT in str(s.get("uses", ""))]
    if [s.get("with", {}).get("ref") for s in apply_checkout] != ["${{ needs.plan.outputs.sha }}"]:
        found.append("apply doesn't check out the commit plan planned")
    if apply.get("env", {}).get("SHA") != "${{ needs.plan.outputs.sha }}":
        found.append("apply's state commit doesn't name the commit plan planned")
    return found


def test_the_plan_and_apply_use_the_target_step_s_answer() -> None:
    assert problems(tofu()) == []


def steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = workflow["jobs"]["plan"]["steps"]
    return found


def step(workflow: dict[str, Any], name: str) -> dict[str, Any]:
    found = named(steps(workflow), name)
    assert found is not None
    return found


def drop_the_target(workflow: dict[str, Any]) -> None:
    steps(workflow)[:] = [s for s in steps(workflow) if s.get("id") != "target"]


def no_state_author(workflow: dict[str, Any]) -> None:
    target = step(workflow, "The commit to plan")
    target["run"] = target["run"].replace('--state-author "$STATE_AUTHOR"', "")


def plan_the_trigger_commit(workflow: dict[str, Any]) -> None:
    step(workflow, "The commit to plan")["env"]["COMMIT"] = "${{ github.sha }}"


def shallow_checkout(workflow: dict[str, Any]) -> None:
    steps(workflow)[0]["with"]["fetch-depth"] = 2


def checkout_the_run_s_commit(workflow: dict[str, Any]) -> None:
    steps(workflow)[0]["with"]["ref"] = "${{ github.event.workflow_run.head_sha }}"


def a_second_checkout(workflow: dict[str, Any]) -> None:
    steps(workflow).append(copy.deepcopy(steps(workflow)[0]))


def no_switch(workflow: dict[str, Any]) -> None:
    steps(workflow).remove(step(workflow, "Check out that commit"))


def ungated_switch(workflow: dict[str, Any]) -> None:
    del step(workflow, "Check out that commit")["if"]


def ungated_plan(workflow: dict[str, Any]) -> None:
    del step(workflow, "Plan")["if"]


def guard_waits_on_the_run_s_commit(workflow: dict[str, Any]) -> None:
    step(workflow, "Wait for the guard check on this commit")["env"]["SHA"] = (
        "${{ github.event.workflow_run.head_sha }}"
    )


def summary_names_another_sha(workflow: dict[str, Any]) -> None:
    step(workflow, "Show the plan for approval")["env"]["SHA"] = "${{ github.sha }}"


def output_another_sha(workflow: dict[str, Any]) -> None:
    workflow["jobs"]["plan"]["outputs"]["sha"] = "${{ github.sha }}"


def apply_the_run_s_commit(workflow: dict[str, Any]) -> None:
    for s in workflow["jobs"]["apply"]["steps"]:
        if CHECKOUT in str(s.get("uses", "")):
            s["with"]["ref"] = "${{ github.event.workflow_run.head_sha }}"


@pytest.mark.parametrize(
    "mutate",
    [
        drop_the_target,
        no_state_author,
        plan_the_trigger_commit,
        shallow_checkout,
        checkout_the_run_s_commit,
        a_second_checkout,
        no_switch,
        ungated_switch,
        ungated_plan,
        guard_waits_on_the_run_s_commit,
        summary_names_another_sha,
        output_another_sha,
        apply_the_run_s_commit,
    ],
)
def test_each_way_of_breaking_it_is_caught(mutate: Callable[[dict[str, Any]], None]) -> None:
    workflow = copy.deepcopy(tofu())
    mutate(workflow)
    assert problems(workflow) != []
