"""ci.yml runs what a pull request's paths need, nothing on a draft, nothing again on a commit the
merge queue passed, and everything otherwise (spec: ci-apply; run-checks-by-path design D4, D6, D7;
ci-once-per-commit design D2-D4).

GitHub evaluates these conditions, so the tests pin the conditions themselves: each one's failure
modes were proven on a throwaway repository (tasks.md, 1.1), and a change here has to be proven
again."""

import copy
from typing import Any, cast

import pytest
import yaml
from conftest import REPO

CI = REPO / ".github" / "workflows" / "ci.yml"

CHANGES_IF = "github.event_name != 'merge_group'"
PULL_REQUEST_TYPES = ["opened", "synchronize", "reopened", "ready_for_review"]
DRAFT = "github.event.pull_request.draft"
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


def step(job: dict[str, Any], ident: str) -> dict[str, Any]:
    return next((each for each in job["steps"] if each.get("id") == ident), {})


def problems(workflow: dict[str, Any]) -> list[str]:
    jobs = workflow["jobs"]
    found = []
    on = cast(dict[Any, Any], workflow)[True]  # YAML 1.1 reads the key `on` as true
    types = (on.get("pull_request") or {}).get("types")
    if types != PULL_REQUEST_TYPES:
        found.append(f"pull requests trigger on {types!r}, not {PULL_REQUEST_TYPES!r}")
    changes = jobs["changes"]
    if condition(changes) != CHANGES_IF:
        found.append(f"changes runs on {condition(changes)!r}, not pull requests and pushes")
    if changes.get("permissions", {}).get("actions") != "read":
        found.append("changes can't read the merge queue's runs: it needs actions: read")
    draft = step(changes, "draft")
    if condition(draft) != f"github.event_name == 'pull_request' && {DRAFT}" or not all(
        answer in runs({"steps": [draft]}) for answer in ("scope=none", "guard=false")
    ):
        found.append("changes doesn't answer scope=none and guard=false on a draft")
    main = step(changes, "main")
    if condition(main) != "github.event_name == 'push'" or "queue_passed.py" not in str(
        main.get("run")
    ):
        found.append("changes doesn't ask queue_passed.py on a push to main")
    if main.get("env", {}).get("SHA") != "${{ github.sha }}":
        found.append("changes doesn't ask queue_passed.py about the commit pushed")
    paths = step(changes, "paths")
    if condition(paths) != f"github.event_name == 'pull_request' && !{DRAFT}":
        found.append(f"changes reads the paths on {condition(paths)!r}, not a ready pull request")
    for output in ("scope", "check-args", "guard"):
        value = str(changes.get("outputs", {}).get(output, ""))
        if not all(f"steps.{ident}.outputs" in value for ident in ("draft", "main", "paths")):
            found.append(f"changes' output {output!r} doesn't come from all three answers")
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
        (["jobs", "changes", "if"], "github.event_name == 'pull_request'", "changes runs on"),
        ([True, "pull_request"], None, "pull requests trigger on"),
        (
            [True, "pull_request", "types"],
            ["opened", "synchronize", "reopened"],
            "pull requests trigger on",
        ),
        (["jobs", "changes", "permissions"], {"contents": "read"}, "actions: read"),
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


@pytest.mark.parametrize(
    ("ident", "named"),
    [
        ("draft", "on a draft"),
        ("main", "queue_passed.py on a push"),
        ("paths", "reads the paths"),
    ],
)
def test_a_removed_answer_is_named(ident: str, named: str) -> None:
    workflow = copy.deepcopy(ci())
    changes = workflow["jobs"]["changes"]
    changes["steps"] = [each for each in changes["steps"] if each.get("id") != ident]
    assert any(named in problem for problem in problems(workflow)), problems(workflow)


def test_the_paths_read_on_a_draft_too_is_named() -> None:
    workflow = copy.deepcopy(ci())
    step(workflow["jobs"]["changes"], "paths")["if"] = "github.event_name == 'pull_request'"
    assert any("reads the paths" in problem for problem in problems(workflow))


def test_a_dropped_check_args_is_named() -> None:
    workflow = copy.deepcopy(ci())
    for step in workflow["jobs"]["check"]["steps"]:
        step.pop("env", None)
    assert "check doesn't pass the changes job's check-args" in problems(workflow)


# merge-queue design D4: each commit a merge queue tests runs in full, as main does.


def test_ci_runs_on_every_commit_a_merge_queue_tests() -> None:
    workflow: dict[Any, Any] = ci()
    triggers = workflow[True]  # YAML 1.1 reads the key `on` as true
    assert "merge_group" in triggers
    assert triggers["merge_group"] is None or "branches" not in triggers["merge_group"]


def evaluate(expression: str, values: dict[str, str]) -> bool:
    """A job condition of the shapes ci.yml uses, evaluated for a run that isn't cancelled: each
    `needs.*` reference is replaced by its value ('' when a skipped job has no outputs)."""
    text = expression.replace("!cancelled()", "True").replace("&&", " and ").replace("||", " or ")
    for name in sorted(values, key=len, reverse=True):
        text = text.replace(name, repr(values[name]))
    assert "needs." not in text, text
    result = eval(text, {"__builtins__": {}}, {})  # noqa: S307 (the workflow's own fixed conditions)
    assert isinstance(result, bool)
    return result


def test_a_merge_group_runs_the_full_check_and_every_leg() -> None:
    """On a merge group `changes` doesn't run (its condition excludes merge groups), so it is
    skipped and has no outputs: the check's condition and the legs' both hold, and the check gets
    no --scope, so it runs in full."""
    jobs = ci()["jobs"]
    assert condition(jobs["changes"]) == CHANGES_IF
    skipped = {
        "needs.changes.result": "skipped",
        "needs.changes.outputs.scope": "",
        "needs.changes.outputs.guard": "",
    }
    assert evaluate(condition(jobs["check"]), skipped)
    assert evaluate(condition(jobs["guard-tests"]), skipped)


def test_the_evaluation_skips_the_check_when_changes_found_only_skipped_paths() -> None:
    """The evaluation above can say no: it does for a pull request that changes nothing checked,
    and for the same answer given on a draft or a push the merge queue passed."""
    jobs = ci()["jobs"]
    answered = {
        "needs.changes.result": "success",
        "needs.changes.outputs.scope": "none",
        "needs.changes.outputs.guard": "false",
    }
    assert not evaluate(condition(jobs["check"]), answered)
    assert not evaluate(condition(jobs["guard-tests"]), answered)


def test_a_push_the_queue_did_not_pass_runs_the_full_check_and_every_leg() -> None:
    """queue_passed.py's "everything" answer: scope=full with no --scope, and guard=true."""
    jobs = ci()["jobs"]
    answered = {
        "needs.changes.result": "success",
        "needs.changes.outputs.scope": "full",
        "needs.changes.outputs.guard": "true",
    }
    assert evaluate(condition(jobs["check"]), answered)
    assert evaluate(condition(jobs["guard-tests"]), answered)
