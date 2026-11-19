"""dependabot-dispatch.yml starts infrastructure's dependabot-issues when Dependabot acts in troupe
or website, and its auto-merge.yml when a pull request's state changes there; each of its two jobs
can do nothing but its one dispatch (specs: dependency-updates, dependabot-dispatch-credentials;
dependabot-issues-on-events design D1, D2; auto-merge design D8).

GitHub evaluates the workflow, so these tests pin what it's given: when it runs, where its job is
skipped, what its token may do, the environment that holds the key, and the dispatch it sends."""

import copy
import re
from typing import Any

import pytest
import yaml
from conftest import REPO

WORKFLOW = REPO / ".github" / "workflows" / "dependabot-dispatch.yml"
TRIGGERS = {
    "workflow_run": {
        "workflows": ["Dependabot Updates", "CI", "guard", "claude review"],
        "types": ["completed"],
    },
    "pull_request_target": {"types": ["labeled", "unlabeled"]},
}
# infrastructure holds the file as its source and is started directly (design D1); each job starts
# on its own events only, read in its `if:`, the one place the event is read.
JOBS = {
    "dispatch": {
        "if": "github.repository != 'troupe-run/infrastructure' && github.event_name == "
        "'workflow_run' && github.event.workflow_run.name == 'Dependabot Updates'",
        # main, no inputs: every run reads everything it needs itself.
        "command": "gh workflow run dependabot-issues.yml -R troupe-run/infrastructure --ref main",
    },
    "auto-merge": {
        "if": "github.repository != 'troupe-run/infrastructure' && (github.event_name == "
        "'pull_request_target' || github.event.workflow_run.name != 'Dependabot Updates')",
        "command": "gh workflow run auto-merge.yml -R troupe-run/infrastructure --ref main",
    },
}
DISPATCH = JOBS["dispatch"]["command"]
MINTED = "${{ steps.app-token.outputs.token }}"
HEADER = (
    "# Source: troupe-run/infrastructure. Change it there; copies in other repositories are "
    "delivered."
)


def dispatcher() -> dict[str, Any]:
    loaded = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    # YAML 1.1 reads the key `on` as true.
    loaded["on"] = loaded.pop(True, loaded.get("on"))
    return loaded


def steps_using(job: dict[str, Any], action: str) -> list[dict[str, Any]]:
    return [step for step in job.get("steps", []) if action in str(step.get("uses", ""))]


def problems(workflow: dict[str, Any]) -> list[str]:
    found = []
    on = workflow.get("on") or {}
    if on != TRIGGERS:
        found.append(
            f"it runs on {on!r}, not on Dependabot's, CI's, guard's and the review's runs and "
            "label changes only"
        )
    if workflow.get("permissions") != {}:
        found.append(f"the default permissions are {workflow.get('permissions')!r}, not {{}}")
    jobs = workflow.get("jobs") or {}
    if set(jobs) != set(JOBS):
        return [*found, f"its jobs are {sorted(jobs)}, not {sorted(JOBS)}"]
    for name, wanted in JOBS.items():
        found += job_problems(name, jobs[name], wanted)
    return found


def job_problems(name: str, job: dict[str, Any], wanted: dict[str, str]) -> list[str]:
    found = []
    if " ".join(str(job.get("if", "")).split()) != wanted["if"]:
        found.append(f"{name} runs when {job.get('if')!r}, not {wanted['if']!r}")
    rest = {key: value for key, value in job.items() if key != "if"}
    if re.search(r"github\.event\b", yaml.safe_dump(rest)):
        found.append(f"an expression in {name} reads github.event: nothing from it is passed on")
    environment = job.get("environment")
    env_name = environment.get("name") if isinstance(environment, dict) else environment
    if env_name != "dependabot-dispatch":
        found.append(f"{name}'s environment is {environment!r}, not dependabot-dispatch")
    if job.get("permissions") != {}:
        found.append(f"{name}'s GITHUB_TOKEN permissions are {job.get('permissions')!r}")
    if steps_using(job, "actions/checkout"):
        found.append(f"{name} checks out the repository; it needs no code")
    others = [
        step
        for step in job.get("steps", [])
        if "uses" in step and "create-github-app-token" not in str(step["uses"])
    ]
    if others:
        found.append(f"{name} uses {[step['uses'] for step in others]}; it runs no other action")

    tokens = steps_using(job, "create-github-app-token")
    if len(tokens) != 1:
        found.append(f"{name} doesn't mint exactly one App token")
    else:
        token = tokens[0]
        inputs = token.get("with") or {}
        if token.get("id") != "app-token":
            found.append(f"the token step's id is {token.get('id')!r}, not app-token")
        granted = {key: value for key, value in inputs.items() if key.startswith("permission-")}
        if granted != {"permission-actions": "write"}:
            found.append(f"{name}'s token asks for {granted}, not actions write only")
        if inputs.get("owner") != "troupe-run" or inputs.get("repositories") != "infrastructure":
            found.append(
                f"{name}'s token is for {inputs.get('owner')!r}/{inputs.get('repositories')!r},"
                " not troupe-run/infrastructure only"
            )
        if inputs.get("private-key") != "${{ secrets.DISPATCH_APP_PRIVATE_KEY }}":
            found.append(f"{name}'s token is minted from {inputs.get('private-key')!r}")
        if inputs.get("client-id") != "${{ vars.DISPATCH_APP_CLIENT_ID }}":
            found.append(f"{name}'s token names the App with {inputs.get('client-id')!r}")

    runs = [step for step in job.get("steps", []) if "run" in step]
    if len(runs) != 1:
        found.append(f"{name} runs {len(runs)} commands, not the one dispatch")
    else:
        step = runs[0]
        command = " ".join(str(step["run"]).split())
        if command != wanted["command"]:
            found.append(f"{name} sends {command!r}, not {wanted['command']!r}")
        if (step.get("env") or {}) != {"GH_TOKEN": MINTED}:
            found.append(
                f"{name}'s dispatch runs with {step.get('env')!r}, not the dispatch App's token "
                "only"
            )
    return found


def test_the_workflow_is_as_designed() -> None:
    assert problems(dispatcher()) == []


def test_it_says_where_it_comes_from() -> None:
    """The delivered copies carry the same first line as the guard's other workflows."""
    assert WORKFLOW.read_text(encoding="utf-8").splitlines()[0] == HEADER


def token(jobs: dict[str, Any]) -> dict[str, Any]:
    return steps_using(jobs["dispatch"], "create-github-app-token")[0]["with"]  # type: ignore[no-any-return]


def dispatch(jobs: dict[str, Any]) -> dict[str, Any]:
    return next(step for step in jobs["dispatch"]["steps"] if "run" in step)


def command(jobs: dict[str, Any], run: str) -> None:
    dispatch(jobs)["run"] = run


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (lambda w: w["on"].update({"pull_request": None}), "not on Dependabot's, CI's"),
        (lambda w: w["on"].pop("pull_request_target"), "not on Dependabot's, CI's"),
        (lambda w: w["on"].update({"workflow_dispatch": None}), "not on Dependabot's, CI's"),
        (
            lambda w: w["on"]["workflow_run"].update({"workflows": ["CI"]}),
            "not on Dependabot's, CI's",
        ),
        (
            lambda w: w["on"]["workflow_run"].update({"types": ["requested"]}),
            "not on Dependabot's, CI's",
        ),
        (lambda w: w.update({"permissions": {"contents": "read"}}), "not {}"),
        (lambda w: w.pop("permissions"), "not {}"),
        (lambda w: w["jobs"].update({"other": {}}), "not ['auto-merge', 'dispatch']"),
        (lambda w: w["jobs"]["dispatch"].pop("if"), "dispatch runs when"),
        (
            lambda w: w["jobs"]["dispatch"].update({"if": "always()"}),
            "dispatch runs when",
        ),
        (lambda w: w["jobs"]["dispatch"].pop("environment"), "not dependabot-dispatch"),
        (
            lambda w: w["jobs"]["dispatch"].update({"environment": "docs"}),
            "not dependabot-dispatch",
        ),
        (
            lambda w: w["jobs"]["dispatch"].update({"permissions": {"actions": "write"}}),
            "dispatch's GITHUB_TOKEN permissions",
        ),
        (
            lambda w: w["jobs"]["dispatch"]["steps"].insert(0, {"uses": "actions/checkout@v7"}),
            "checks out the repository",
        ),
        (
            lambda w: w["jobs"]["dispatch"]["steps"].insert(0, {"uses": "astral-sh/setup-uv@v7"}),
            "it runs no other action",
        ),
        (
            lambda w: token(w["jobs"]).update({"permission-issues": "write"}),
            "not actions write only",
        ),
        (lambda w: token(w["jobs"]).pop("repositories"), "not troupe-run/infrastructure only"),
        (
            lambda w: token(w["jobs"]).update({"repositories": "infrastructure,website"}),
            "not troupe-run/infrastructure only",
        ),
        (
            lambda w: token(w["jobs"]).update(
                {"private-key": "${{ secrets.DOCS_APP_PRIVATE_KEY }}"}
            ),
            "minted from",
        ),
        (
            lambda w: token(w["jobs"]).update({"client-id": "${{ vars.DOCS_APP_CLIENT_ID }}"}),
            "names the App with",
        ),
        (lambda w: command(w["jobs"], DISPATCH.replace("--ref main", "--ref next")), "--ref next"),
        (lambda w: command(w["jobs"], DISPATCH.replace("dependabot-issues", "tofu")), "tofu.yml"),
        (
            lambda w: command(w["jobs"], f"{DISPATCH} -f only=website"),
            "-f only=website",
        ),
        (
            lambda w: dispatch(w["jobs"]).update(
                {
                    "env": {
                        "GH_TOKEN": MINTED,
                        "HEAD": "${{ github.event.workflow_run.head_branch }}",
                    }
                }
            ),
            "reads github.event",
        ),
        (lambda w: w["jobs"]["dispatch"]["steps"].append({"run": "env"}), "not the one dispatch"),
        (
            lambda w: dispatch(w["jobs"]).update({"env": {"GH_TOKEN": "${{ github.token }}"}}),
            "not the dispatch App's token only",
        ),
        # The auto-merge job (auto-merge design D8).
        (lambda w: w["jobs"].pop("auto-merge"), "not ['auto-merge', 'dispatch']"),
        (lambda w: w["jobs"]["auto-merge"].pop("if"), "auto-merge runs when"),
        (
            lambda w: w["jobs"]["auto-merge"].update({"if": "github.repository != 'x'"}),
            "auto-merge runs when",
        ),
        (
            lambda w: next(s for s in w["jobs"]["auto-merge"]["steps"] if "run" in s).update(
                {"run": DISPATCH}
            ),
            "auto-merge sends",
        ),
        (
            lambda w: next(s for s in w["jobs"]["auto-merge"]["steps"] if "run" in s).update(
                {"run": JOBS["auto-merge"]["command"] + " -f pr=${{ github.event.number }}"}
            ),
            "an expression in auto-merge reads github.event",
        ),
        (
            lambda w: steps_using(w["jobs"]["auto-merge"], "create-github-app-token")[0][
                "with"
            ].update({"permission-pull-requests": "write"}),
            "auto-merge's token asks for",
        ),
        (
            lambda w: w["jobs"]["auto-merge"].update({"environment": "auto-merge"}),
            "auto-merge's environment",
        ),
        (
            lambda w: w["on"]["pull_request_target"].update({"types": ["opened"]}),
            "not on Dependabot's, CI's",
        ),
    ],
)
def test_each_way_the_workflow_can_go_wrong_is_named(change: Any, named: str) -> None:  # noqa: ANN401
    workflow = copy.deepcopy(dispatcher())
    change(workflow)
    assert any(named in problem for problem in problems(workflow)), problems(workflow)
