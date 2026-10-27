"""tofu.yml runs scripts/main_ci.py before a scheduled or manual plan of main, so a red main holds
it (spec: ci-apply, "A scheduled or manual plan of main waits for green CI"; plans-wait-for-ci
design D1, D3, D5, D6).

GitHub runs the workflow, so these tests pin what it's given: the gate in one step of the plan job,
after the target and before the guard wait and the plan, skipped only after CI on a merge; a job
timeout the gate's limit fits in; ci.yml skipping exactly the file the gate looks past; no input
that skips it; and the drift job left out of it. test_main_ci.py tests the gate itself."""

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO

import main_ci
import plan_target

TOFU = REPO / ".github" / "workflows" / "tofu.yml"
CI = REPO / ".github" / "workflows" / "ci.yml"

GATE_IF = "github.event_name != 'workflow_run' && steps.target.outputs.plan == 'true'"
GUARD_WAIT = "Wait for the guard check on this commit"
GUARD_WAIT_MINUTES = 10


def load(path: Path) -> dict[Any, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def triggers(workflow: dict[Any, Any]) -> dict[str, Any]:
    # PyYAML reads the `on:` key as True.
    found = workflow["on"] if "on" in workflow else workflow[True]
    assert isinstance(found, dict)
    return found


def problems(tofu: dict[str, Any], ci: dict[str, Any]) -> list[str]:
    found = []
    plan = tofu["jobs"]["plan"]
    steps: list[dict[str, Any]] = plan["steps"]
    gates = [i for i, step in enumerate(steps) if "scripts/main_ci.py" in step.get("run", "")]
    if len(gates) != 1:
        return [f"plan runs scripts/main_ci.py in {len(gates)} steps, not one"]
    at = gates[0]
    gate = steps[at]
    names = [step.get("name") for step in steps]
    ids = [step.get("id") for step in steps]
    if "target" not in ids or ids.index("target") > at:
        found.append("the gate doesn't run after the target step")
    if GUARD_WAIT not in names or names.index(GUARD_WAIT) < at:
        found.append("the gate doesn't run before the guard wait")
    if "plan" not in ids or ids.index("plan") < at:
        found.append("the gate doesn't run before the plan")
    if gate.get("if") != GATE_IF:
        found.append(f"the gate's if is {gate.get('if')!r}, not {GATE_IF!r}")
    run = gate["run"]
    for expected in (
        "--main origin/main",
        '--repository "$GITHUB_REPOSITORY"',
        '--summary "$GITHUB_STEP_SUMMARY"',
    ):
        if expected not in run:
            found.append(f"the gate doesn't pass {expected}")
    if gate.get("env", {}).get("GH_TOKEN") != "${{ github.token }}":
        found.append("the gate isn't given GH_TOKEN")
    if gate.get("continue-on-error"):
        found.append("the gate's failure doesn't stop the plan")

    limit = main_ci.LIMIT_SECONDS // 60 + GUARD_WAIT_MINUTES
    if int(plan.get("timeout-minutes", 0)) <= limit:
        found.append(f"plan's timeout isn't above the gate's limit plus the guard wait ({limit})")

    dispatch = triggers(tofu).get("workflow_dispatch")
    if dispatch and dispatch.get("inputs"):
        found.append("workflow_dispatch takes inputs, so a run could skip the gate")

    oob = tofu["jobs"]["oob"]
    if oob.get("needs"):
        found.append("the drift job needs another job, so a red main could stop it")
    if "main_ci.py" in str(oob):
        found.append("the drift job runs the gate")

    ignored = triggers(ci).get("push", {}).get("paths-ignore")
    if ignored != [plan_target.STATE_PATH]:
        found.append(f"ci.yml's push ignores {ignored}, not only {plan_target.STATE_PATH}")
    return found


def test_the_plan_of_main_waits_for_green_ci_as_designed() -> None:
    assert problems(load(TOFU), load(CI)) == []


def gate(workflow: dict[str, Any]) -> dict[str, Any]:
    found: list[dict[str, Any]] = [
        s for s in workflow["jobs"]["plan"]["steps"] if "main_ci.py" in s.get("run", "")
    ]
    return found[0]


def plan_steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = workflow["jobs"]["plan"]["steps"]
    return found


def drop_the_gate(tofu: dict[str, Any], ci: dict[str, Any]) -> None:
    plan_steps(tofu).remove(gate(tofu))


def gate_after_the_plan(tofu: dict[str, Any], ci: dict[str, Any]) -> None:
    step = gate(tofu)
    plan_steps(tofu).remove(step)
    plan_steps(tofu).append(step)


def gate_before_the_target(tofu: dict[str, Any], ci: dict[str, Any]) -> None:
    step = gate(tofu)
    plan_steps(tofu).remove(step)
    plan_steps(tofu).insert(0, step)


def gate_after_merges_too(tofu: dict[str, Any], ci: dict[str, Any]) -> None:
    gate(tofu)["if"] = "steps.target.outputs.plan == 'true'"


def gate_only_on_schedule(tofu: dict[str, Any], ci: dict[str, Any]) -> None:
    gate(tofu)["if"] = "github.event_name == 'schedule'"


def gate_carries_on(tofu: dict[str, Any], ci: dict[str, Any]) -> None:
    gate(tofu)["continue-on-error"] = True


def no_token(tofu: dict[str, Any], ci: dict[str, Any]) -> None:
    del gate(tofu)["env"]["GH_TOKEN"]


def gate_reads_the_run_s_commit(tofu: dict[str, Any], ci: dict[str, Any]) -> None:
    gate(tofu)["run"] = gate(tofu)["run"].replace("--main origin/main", "--main HEAD")


def short_timeout(tofu: dict[str, Any], ci: dict[str, Any]) -> None:
    tofu["jobs"]["plan"]["timeout-minutes"] = 30


def a_skip_input(tofu: dict[str, Any], ci: dict[str, Any]) -> None:
    triggers(tofu)["workflow_dispatch"] = {"inputs": {"skip-ci": {"type": "boolean"}}}


def drift_waits_for_the_plan(tofu: dict[str, Any], ci: dict[str, Any]) -> None:
    tofu["jobs"]["oob"]["needs"] = "plan"


def ci_ignores_more(tofu: dict[str, Any], ci: dict[str, Any]) -> None:
    triggers(ci)["push"]["paths-ignore"].append("docs/**")


@pytest.mark.parametrize(
    "mutate",
    [
        drop_the_gate,
        gate_after_the_plan,
        gate_before_the_target,
        gate_after_merges_too,
        gate_only_on_schedule,
        gate_carries_on,
        no_token,
        gate_reads_the_run_s_commit,
        short_timeout,
        a_skip_input,
        drift_waits_for_the_plan,
        ci_ignores_more,
    ],
)
def test_each_way_of_breaking_it_is_caught(
    mutate: Callable[[dict[str, Any], dict[str, Any]], None],
) -> None:
    tofu, ci = copy.deepcopy(load(TOFU)), copy.deepcopy(load(CI))
    if mutate is not drop_the_gate and not [
        s for s in plan_steps(tofu) if "main_ci.py" in s.get("run", "")
    ]:
        pytest.fail("tofu.yml has no gate step to break")
    mutate(tofu, ci)
    assert problems(tofu, ci) != []
