"""milestones-notice.yml rebuilds troupe.run when the milestones change on main, and its one job
can do nothing but dispatch the website's deploy (specs: milestones, docs-build-credentials;
rebuild-site-on-milestones design D2 to D4).

GitHub evaluates the workflow, so these tests pin what it's given: when it runs, what its token
may do, the environment that holds the key, and the dispatch it sends."""

import copy
from typing import Any

import pytest
import yaml
from conftest import REPO

NOTICE = REPO / ".github" / "workflows" / "milestones-notice.yml"
# The same dispatch troupe's release workflow sends (design D3): main, no inputs.
DISPATCH = "gh workflow run deploy.yml -R troupe-run/website --ref main"
# What the dispatch reads its token from: the minted one, never GITHUB_TOKEN.
MINTED = "${{ steps.app-token.outputs.token }}"


def notice() -> dict[str, Any]:
    loaded = yaml.safe_load(NOTICE.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    # YAML 1.1 reads the key `on` as true.
    loaded["on"] = loaded.pop(True, loaded.get("on"))
    return loaded


def steps_using(job: dict[str, Any], action: str) -> list[dict[str, Any]]:
    return [step for step in job.get("steps", []) if action in str(step.get("uses", ""))]


def problems(workflow: dict[str, Any]) -> list[str]:
    found = []
    on = workflow.get("on") or {}
    if set(on) != {"push"}:
        found.append(f"it runs on {sorted(on)}, not on a push only")
    push = on.get("push") or {}
    if set(push) != {"branches", "paths"}:
        found.append(f"its push filters are {sorted(push)}, not branches and paths")
    if push.get("branches") != ["main"]:
        found.append(f"it runs on pushes to {push.get('branches')!r}, not to main only")
    if push.get("paths") != ["tofu/milestones.json"]:
        found.append(f"it runs on changes to {push.get('paths')!r}, not tofu/milestones.json only")
    if workflow.get("permissions") != {}:
        found.append(f"the default permissions are {workflow.get('permissions')!r}, not {{}}")

    jobs = workflow.get("jobs") or {}
    if set(jobs) != {"notify"}:
        return [*found, f"its jobs are {sorted(jobs)}, not notify only"]
    notify = jobs["notify"]

    if "if" in notify:
        found.append(f"notify runs only when {notify['if']!r}; the trigger is the condition")
    environment = notify.get("environment")
    name = environment.get("name") if isinstance(environment, dict) else environment
    if name != "docs":
        found.append(f"notify's environment is {environment!r}, not docs")
    if notify.get("permissions") != {}:
        found.append(f"notify's GITHUB_TOKEN permissions are {notify.get('permissions')!r}")
    if steps_using(notify, "actions/checkout"):
        found.append("notify checks out the repository; it needs no code")
    others = [
        step
        for step in notify.get("steps", [])
        if "uses" in step and "create-github-app-token" not in str(step["uses"])
    ]
    if others:
        found.append(f"notify uses {[step['uses'] for step in others]}; it runs no other action")

    tokens = steps_using(notify, "create-github-app-token")
    if len(tokens) != 1:
        found.append("notify doesn't mint exactly one App token")
    else:
        token = tokens[0]
        inputs = token.get("with") or {}
        if token.get("id") != "app-token":
            found.append(f"the token step's id is {token.get('id')!r}, not app-token")
        granted = {key: value for key, value in inputs.items() if key.startswith("permission-")}
        if granted != {"permission-actions": "write"}:
            found.append(f"notify's token asks for {granted}, not actions write only")
        if inputs.get("owner") != "troupe-run" or inputs.get("repositories") != "website":
            found.append(
                f"notify's token is for {inputs.get('owner')!r}/{inputs.get('repositories')!r},"
                " not troupe-run/website only"
            )
        if inputs.get("private-key") != "${{ secrets.DOCS_APP_PRIVATE_KEY }}":
            found.append(f"notify's token is minted from {inputs.get('private-key')!r}")
        if inputs.get("client-id") != "${{ vars.DOCS_APP_CLIENT_ID }}":
            found.append(f"notify's token names the App with {inputs.get('client-id')!r}")

    runs = [step for step in notify.get("steps", []) if "run" in step]
    if len(runs) != 1:
        found.append(f"notify runs {len(runs)} commands, not the one dispatch")
    else:
        step = runs[0]
        command = " ".join(str(step["run"]).split())
        if command != DISPATCH:
            found.append(f"notify dispatches {command!r}, not {DISPATCH!r}")
        if (step.get("env") or {}) != {"GH_TOKEN": MINTED}:
            found.append(
                f"the dispatch runs with {step.get('env')!r}, not the docs App's token only"
            )
    return found


def test_the_workflow_is_as_designed() -> None:
    assert problems(notice()) == []


def token(jobs: dict[str, Any]) -> dict[str, Any]:
    return steps_using(jobs["notify"], "create-github-app-token")[0]["with"]  # type: ignore[no-any-return]


def dispatch(jobs: dict[str, Any]) -> dict[str, Any]:
    return next(step for step in jobs["notify"]["steps"] if "run" in step)


def command(jobs: dict[str, Any], run: str) -> None:
    dispatch(jobs)["run"] = run


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (lambda w: w["on"].update({"pull_request": None}), "not on a push only"),
        (lambda w: w["on"].update({"workflow_dispatch": None}), "not on a push only"),
        (lambda w: w["on"]["push"].update({"branches": ["main", "next"]}), "not to main only"),
        (lambda w: w["on"]["push"].pop("branches"), "not to main only"),
        (lambda w: w["on"]["push"].pop("paths"), "not tofu/milestones.json only"),
        (
            lambda w: w["on"]["push"].update({"paths": ["tofu/milestones.json", "tofu/**"]}),
            "not tofu/milestones.json only",
        ),
        (lambda w: w["on"]["push"].update({"tags": ["*"]}), "not branches and paths"),
        (lambda w: w.update({"permissions": {"contents": "read"}}), "not {}"),
        (lambda w: w.pop("permissions"), "not {}"),
        (lambda w: w["jobs"].update({"other": {}}), "not notify only"),
        (lambda w: w["jobs"]["notify"].update({"if": "always()"}), "the trigger is the condition"),
        (lambda w: w["jobs"]["notify"].pop("environment"), "not docs"),
        (lambda w: w["jobs"]["notify"].update({"environment": "release"}), "not docs"),
        (
            lambda w: w["jobs"]["notify"].update({"permissions": {"actions": "write"}}),
            "notify's GITHUB_TOKEN permissions",
        ),
        (lambda w: w["jobs"]["notify"].pop("permissions"), "notify's GITHUB_TOKEN permissions"),
        (
            lambda w: w["jobs"]["notify"]["steps"].insert(0, {"uses": "actions/checkout@v7"}),
            "checks out the repository",
        ),
        (
            lambda w: w["jobs"]["notify"]["steps"].insert(0, {"uses": "astral-sh/setup-uv@v7"}),
            "it runs no other action",
        ),
        (
            lambda w: token(w["jobs"]).update({"permission-contents": "write"}),
            "not actions write only",
        ),
        (lambda w: token(w["jobs"]).pop("permission-actions"), "not actions write only"),
        (lambda w: token(w["jobs"]).pop("repositories"), "not troupe-run/website only"),
        (
            lambda w: token(w["jobs"]).update({"repositories": "website,troupe"}),
            "not troupe-run/website only",
        ),
        (
            lambda w: token(w["jobs"]).update(
                {"private-key": "${{ secrets.TF_VAR_github_app_pem }}"}
            ),
            "minted from",
        ),
        (
            lambda w: token(w["jobs"]).update({"client-id": "${{ vars.BOARD_APP_CLIENT_ID }}"}),
            "names the App with",
        ),
        (
            lambda w: command(w["jobs"], DISPATCH.replace("--ref main", "--ref next")),
            "--ref next",
        ),
        (lambda w: command(w["jobs"], DISPATCH.replace("deploy.yml", "ci.yml")), "ci.yml"),
        (lambda w: command(w["jobs"], DISPATCH.replace("website", "troupe")), "troupe-run/troupe"),
        (lambda w: command(w["jobs"], f"{DISPATCH} -f ref=next"), "-f ref=next"),
        (lambda w: command(w["jobs"], f"{DISPATCH} -F ref=@input.json"), "-F ref=@input.json"),
        (lambda w: command(w["jobs"], f"{DISPATCH}\n{DISPATCH}"), "not 'gh workflow run"),
        (
            lambda w: w["jobs"]["notify"]["steps"].append({"run": "env"}),
            "not the one dispatch",
        ),
        (
            lambda w: dispatch(w["jobs"]).update({"env": {"GH_TOKEN": "${{ github.token }}"}}),
            "not the docs App's token only",
        ),
    ],
)
def test_each_way_the_workflow_can_go_wrong_is_named(change: Any, named: str) -> None:  # noqa: ANN401
    workflow = copy.deepcopy(notice())
    change(workflow)
    assert any(named in problem for problem in problems(workflow)), problems(workflow)
