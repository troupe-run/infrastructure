"""ci.yml runs what a pull request's paths need, and everything otherwise (spec: ci-apply;
run-checks-by-path design D4, D6, D7).

GitHub evaluates these conditions, so the tests pin the conditions themselves: each one's failure
modes were proven on a throwaway repository (tasks.md, 1.1), and a change here has to be proven
again."""

import copy
from typing import Any

import pytest
import yaml
from conftest import REPO

CI = REPO / ".github" / "workflows" / "ci.yml"

CHECK_IF = "!cancelled() && needs.changes.outputs.scope != 'none'"
LEGS_IF = (
    "!cancelled() && (needs.changes.result != 'success' || needs.changes.outputs.guard == 'true')"
)


def ci() -> dict[str, Any]:
    loaded = yaml.safe_load(CI.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def condition(job: dict[str, Any]) -> str:
    """A job's `if`, without the optional `${{ }}` and with runs of whitespace as one space."""
    text = str(job.get("if", "")).strip()
    if text.startswith("${{") and text.endswith("}}"):
        text = text[3:-2]
    return " ".join(text.split())


def needs(job: dict[str, Any]) -> list[str]:
    value = job.get("needs", [])
    return [value] if isinstance(value, str) else list(value)


def runs(job: dict[str, Any]) -> str:
    return "\n".join(str(step.get("run", "")) for step in job["steps"])


def problems(workflow: dict[str, Any]) -> list[str]:
    jobs = workflow["jobs"]
    found = []
    changes = jobs["changes"]
    if condition(changes) != "github.event_name == 'pull_request'":
        found.append(f"changes runs on {condition(changes)!r}, not only on pull requests")
    script = runs(changes)
    for piece in ("--no-renames", "guard.py check-scope", "guard_tests_needed.py"):
        if piece not in script:
            found.append(f"changes doesn't run {piece!r}")
    for output in ("scope", "check-args", "guard"):
        if output not in changes.get("outputs", {}):
            found.append(f"changes has no output {output!r}")
    check = jobs["check"]
    if needs(check) != ["changes"] or condition(check) != CHECK_IF:
        found.append(f"check runs on {condition(check)!r}; it must skip only on scope=none")
    if "needs.changes.outputs['check-args']" not in str(check["steps"]):
        found.append("check doesn't pass the changes job's check-args")
    legs = jobs["guard-tests"]
    if needs(legs) != ["changes"] or condition(legs) != LEGS_IF:
        found.append(f"the legs run on {condition(legs)!r}; a failed changes must run them")
    result = jobs["guard-tests-result"]
    if result.get("name") != "guard tests":
        found.append(f"the legs' result is named {result.get('name')!r}, not 'guard tests'")
    if sorted(needs(result)) != ["changes", "guard-tests"] or condition(result) != "always()":
        found.append("the legs' result must need changes and the legs, and always run")
    if "guard_tests_needed.py --result" not in runs(result):
        found.append("the legs' result isn't judged by guard_tests_needed.py --result")
    return found


def test_ci_runs_what_the_paths_need_and_everything_otherwise() -> None:
    assert problems(ci()) == []


def mutated(path: list[str], value: object) -> dict[str, Any]:
    workflow = copy.deepcopy(ci())
    target = workflow
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return workflow


@pytest.mark.parametrize(
    ("path", "value", "named"),
    [
        (["jobs", "changes", "if"], "always()", "changes runs on"),
        (["jobs", "check", "if"], "needs.changes.outputs.scope != 'none'", "check runs on"),
        (
            ["jobs", "check", "if"],
            "!cancelled() && needs.changes.outputs.scope == 'full'",
            "check runs on",
        ),
        (["jobs", "guard-tests", "if"], "needs.changes.outputs.guard == 'true'", "the legs run"),
        (["jobs", "guard-tests-result", "if"], "success()", "always run"),
        (["jobs", "guard-tests-result", "name"], "guard tests (all)", "named"),
    ],
)
def test_a_changed_condition_is_named(path: list[str], value: object, named: str) -> None:
    found = problems(mutated(path, value))
    assert any(named in problem for problem in found), found


def test_a_dropped_check_args_is_named() -> None:
    workflow = copy.deepcopy(ci())
    for step in workflow["jobs"]["check"]["steps"]:
        step.pop("env", None)
    assert "check doesn't pass the changes job's check-args" in problems(workflow)
