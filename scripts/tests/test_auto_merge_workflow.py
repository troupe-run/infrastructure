"""auto-merge.yml runs the evaluator on infrastructure's main, as the troupe-run-merge App, and
carries nothing from what started it (spec: auto-merge, merge-credentials; auto-merge design D1,
D10). GitHub evaluates the workflow, so these tests pin what it's given."""

import copy
import json
import re
from typing import Any

import pytest
import yaml
from conftest import REPO

pytestmark = pytest.mark.oob

WORKFLOW = REPO / ".github" / "workflows" / "auto-merge.yml"
INSTALLATIONS = REPO / "oob" / "app-installations.json"
TRIGGERS = {
    "workflow_run": {"workflows": ["CI", "guard", "claude review"], "types": ["completed"]},
    "pull_request_target": {"types": ["labeled", "unlabeled"]},
    "schedule": [{"cron": "7,22,37,52 * * * *"}],
    "workflow_dispatch": None,
}
COMMAND = "uv run --locked scripts/auto_merge.py run"
MINTED = "${{ steps.app-token.outputs.token }}"


def workflow() -> dict[str, Any]:
    loaded = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    loaded["on"] = loaded.pop(True, loaded.get("on"))
    return loaded


# Permissions the App has that the token step can't ask for: create-github-app-token takes no input
# for them, and warns about and ignores one it doesn't know (#363). Every token has metadata. The
# Variables read works without an input: the 2026-11-19 probe (auto-merge design D10) and every
# dry-run run since read AUTO_MERGE in all three repositories.
UNREQUESTED = {"metadata", "actions_variables"}


def declared_permissions() -> dict[str, str]:
    """The merge App's permissions as oob declares them, as create-github-app-token's inputs."""
    apps = json.loads(INSTALLATIONS.read_text(encoding="utf-8"))
    (app,) = [app for app in apps if app["app_slug"] == "troupe-run-merge"]
    return {
        f"permission-{name.replace('_', '-')}": level
        for name, level in app["permissions"].items()
        if name not in UNREQUESTED
    }


def problems(w: dict[str, Any]) -> list[str]:
    found = []
    if w.get("on") != TRIGGERS:
        found.append(f"it runs on {w.get('on')!r}, not {TRIGGERS!r}")
    if w.get("permissions") != {}:
        found.append(f"the default permissions are {w.get('permissions')!r}, not {{}}")
    if w.get("concurrency") != {"group": "auto-merge", "cancel-in-progress": False}:
        found.append(f"its concurrency is {w.get('concurrency')!r}, not one queue of runs")
    if re.search(r"github\.event\b", yaml.safe_dump(w)):
        found.append("an expression reads github.event: a run carries nothing from its trigger")
    jobs = w.get("jobs") or {}
    if set(jobs) != {"judge"}:
        return [*found, f"its jobs are {sorted(jobs)}, not judge only"]
    job = jobs["judge"]
    environment = job.get("environment") or {}
    if environment != {"name": "auto-merge", "deployment": False}:
        found.append(f"judge's environment is {environment!r}, not auto-merge")
    if job.get("permissions") != {"contents": "read"}:
        found.append(f"judge's GITHUB_TOKEN permissions are {job.get('permissions')!r}")
    steps = job.get("steps") or []
    checkouts = [s for s in steps if "actions/checkout" in str(s.get("uses", ""))]
    if len(checkouts) != 1 or checkouts[0].get("with") != {
        "ref": "main",
        "persist-credentials": False,
    }:
        found.append("judge doesn't check out main alone, without credentials")
    tokens = [s for s in steps if "create-github-app-token" in str(s.get("uses", ""))]
    if len(tokens) != 1:
        return [*found, "judge doesn't mint exactly one App token"]
    inputs = tokens[0].get("with") or {}
    granted = {key: value for key, value in inputs.items() if key.startswith("permission-")}
    if granted != declared_permissions():
        found.append(f"the token asks for {granted}, not the App's declared permissions")
    if inputs.get("repositories") != "troupe,infrastructure,website":
        found.append(f"the token is for {inputs.get('repositories')!r}, not the three repositories")
    if inputs.get("private-key") != "${{ secrets.MERGE_APP_PRIVATE_KEY }}":
        found.append(f"the token is minted from {inputs.get('private-key')!r}")
    if inputs.get("client-id") != "${{ vars.MERGE_APP_CLIENT_ID }}":
        found.append(f"the token names the App with {inputs.get('client-id')!r}")
    runs = [s for s in steps if "run" in s]
    if [" ".join(str(s["run"]).split()) for s in runs] != [COMMAND]:
        found.append(f"judge runs {[s['run'] for s in runs]!r}, not {COMMAND!r}")
    elif (runs[0].get("env") or {}) != {"GH_TOKEN": MINTED}:
        found.append(f"the evaluator runs with {runs[0].get('env')!r}, not the App's token only")
    return found


def test_the_workflow_is_as_designed() -> None:
    assert problems(workflow()) == []


def test_the_merge_app_is_declared_with_the_probed_permissions() -> None:
    """Queueing needs contents write (design D10's probe); nothing org-wide."""
    assert declared_permissions() == {
        "permission-actions": "read",
        "permission-checks": "read",
        "permission-contents": "write",
        "permission-issues": "read",
        "permission-merge-queues": "write",
        "permission-pull-requests": "write",
    }


def judge(w: dict[str, Any]) -> dict[str, Any]:
    return w["jobs"]["judge"]  # type: ignore[no-any-return]


def token(w: dict[str, Any]) -> dict[str, Any]:
    step = next(s for s in judge(w)["steps"] if "create-github-app-token" in str(s.get("uses")))
    return step["with"]  # type: ignore[no-any-return]


def command(w: dict[str, Any]) -> dict[str, Any]:
    return next(s for s in judge(w)["steps"] if "run" in s)


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (lambda w: w["on"].update({"pull_request": None}), "it runs on"),
        (lambda w: w["on"].pop("schedule"), "it runs on"),
        (lambda w: w.update({"permissions": {"contents": "write"}}), "default permissions"),
        (lambda w: w.update({"concurrency": {"group": "x"}}), "one queue of runs"),
        (lambda w: judge(w).pop("environment"), "not auto-merge"),
        (lambda w: judge(w).update({"environment": "apply"}), "not auto-merge"),
        (lambda w: judge(w).update({"permissions": {"contents": "write"}}), "GITHUB_TOKEN"),
        (
            lambda w: judge(w)["steps"][0]["with"].update({"ref": "${{ github.head_ref }}"}),
            "check out main alone",
        ),
        (
            lambda w: judge(w)["steps"][0]["with"].update(
                {"ref": "${{ github.event.pull_request.head.sha }}"}
            ),
            "reads github.event",
        ),
        (lambda w: token(w).update({"permission-administration": "write"}), "declared permissions"),
        (lambda w: token(w).pop("permission-contents"), "declared permissions"),
        (lambda w: token(w).update({"repositories": "troupe"}), "the three repositories"),
        (
            lambda w: token(w).update({"private-key": "${{ secrets.TF_VAR_github_app_pem }}"}),
            "minted from",
        ),
        (lambda w: command(w).update({"run": f"{COMMAND} --as-if on"}), "judge runs"),
        (
            lambda w: command(w).update({"env": {"GH_TOKEN": "${{ github.token }}"}}),
            "the App's token only",
        ),
    ],
)
def test_each_way_the_workflow_can_go_wrong_is_named(change: Any, named: str) -> None:  # noqa: ANN401
    w = copy.deepcopy(workflow())
    change(w)
    assert any(named in problem for problem in problems(w)), problems(w)
