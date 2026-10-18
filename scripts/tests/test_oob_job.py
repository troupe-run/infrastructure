"""tofu.yml's oob job checks what OpenTofu can't manage whenever main is planned, with a token that
only reads (spec: ci-apply; run-oob-check-daily design D1, D2).

GitHub evaluates the workflow, so these tests pin what it's given: when the job runs, the
environment that gives it the App's key, and the permissions its token and GITHUB_TOKEN get."""

import copy
import json
from typing import Any

import pytest
import yaml
from conftest import REPO

TOFU = REPO / ".github" / "workflows" / "tofu.yml"

# What oob.py reads, and so all the token may hold (design D2's table).
PERMISSIONS = {
    "permission-contents",
    "permission-issues",
    "permission-administration",
    "permission-organization-administration",
    "permission-organization-projects",
    "permission-issue-types",
}


def tofu() -> dict[str, Any]:
    loaded = yaml.safe_load(TOFU.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def condition(job: dict[str, Any]) -> str:
    return " ".join(str(job.get("if", "")).split())


def needs(job: dict[str, Any]) -> list[str]:
    value = job.get("needs", [])
    return [value] if isinstance(value, str) else list(value)


def token_step(job: dict[str, Any]) -> dict[str, Any] | None:
    steps = [s for s in job.get("steps", []) if "create-github-app-token" in str(s.get("uses", ""))]
    return steps[0] if len(steps) == 1 else None


def problems(workflow: dict[str, Any]) -> list[str]:
    jobs = workflow["jobs"]
    if "oob" not in jobs:
        return ["there is no oob job"]
    job = jobs["oob"]
    found = []
    if condition(job) != condition(jobs["plan"]):
        found.append(f"oob runs on {condition(job)!r}, not whenever main is planned")
    environment = job.get("environment", {})
    if not isinstance(environment, dict) or environment.get("name") != "plan-main":
        found.append(f"oob's environment is {environment!r}, not plan-main")
    if job.get("permissions") != {"contents": "read"}:
        found.append(f"oob's GITHUB_TOKEN permissions are {job.get('permissions')!r}")
    if needs(job):
        found.append(f"oob needs {needs(job)}, so a failure there would stop it")
    for name, other in jobs.items():
        if "oob" in needs(other):
            found.append(f"{name} needs oob, so drift outside OpenTofu would stop it")
    step = token_step(job)
    if step is None:
        found.append("oob doesn't mint exactly one App token")
        return found
    inputs = step.get("with", {})
    granted = {k for k in inputs if k.startswith("permission-")}
    if granted != PERMISSIONS:
        found.append(f"oob's token asks for {sorted(granted)}, not {sorted(PERMISSIONS)}")
    for key in sorted(granted):
        if inputs[key] != "read":
            found.append(f"oob's token asks for {key}: {inputs[key]!r}, not read")
    script = "\n".join(str(s.get("run", "")) for s in job["steps"])
    if "scripts/oob.py --ci" not in script:
        found.append("oob doesn't run scripts/oob.py --ci")
    tokens = [
        s.get("env", {}).get("GH_TOKEN") for s in job["steps"] if "oob.py" in str(s.get("run"))
    ]
    if tokens != [f"${{{{ steps.{step.get('id')}.outputs.token }}}}"]:
        found.append(f"oob.py reads with {tokens}, not the read-only token")
    return found


def test_the_oob_job_is_as_designed() -> None:
    assert problems(tofu()) == []


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (lambda jobs: jobs.pop("oob"), "there is no oob job"),
        (
            lambda jobs: jobs["oob"].update({"if": "github.event_name == 'schedule'"}),
            "not whenever main is planned",
        ),
        (lambda jobs: jobs["oob"].update({"environment": "plan-pr"}), "not plan-main"),
        (
            lambda jobs: jobs["oob"].update(
                {"permissions": {"contents": "read", "issues": "write"}}
            ),
            "GITHUB_TOKEN permissions",
        ),
        (lambda jobs: jobs["oob"].update({"needs": "plan"}), "oob needs ['plan']"),
        (lambda jobs: jobs["apply"].update({"needs": ["plan", "oob"]}), "apply needs oob"),
        (
            lambda jobs: token_step(jobs["oob"])["with"].update({"permission-contents": "write"}),  # type: ignore[index]
            "permission-contents: 'write', not read",
        ),
        (
            lambda jobs: token_step(jobs["oob"])["with"].update({"permission-pages": "read"}),  # type: ignore[index]
            "oob's token asks for",
        ),
        (
            lambda jobs: token_step(jobs["oob"])["with"].pop("permission-issue-types"),  # type: ignore[index]
            "oob's token asks for",
        ),
        (
            lambda jobs: jobs["oob"]["steps"][-1].update({"run": "uv run scripts/oob.py"}),
            "doesn't run scripts/oob.py --ci",
        ),
        (
            lambda jobs: jobs["oob"]["steps"][-1].update(
                {"env": {"GH_TOKEN": "${{ github.token }}"}}
            ),
            "not the read-only token",
        ),
    ],
)
def test_each_way_the_job_can_go_wrong_is_named(change: Any, named: str) -> None:  # noqa: ANN401
    workflow = copy.deepcopy(tofu())
    change(workflow["jobs"])
    assert any(named in problem for problem in problems(workflow)), problems(workflow)


@pytest.mark.milestones
def test_the_token_reaches_every_repository_oob_reads() -> None:
    step = token_step(tofu()["jobs"]["oob"])
    assert step is not None
    granted = set(step["with"]["repositories"].split(","))
    code_security = json.loads((REPO / "oob" / "code-security.json").read_text())
    milestones = json.loads((REPO / "tofu" / "milestones.json").read_text())
    read = {
        ".github",
        "troupe",
        *(r["repository"] for r in code_security["repositories"]),
        *milestones["repositories"],
    }
    assert read <= granted, sorted(read - granted)
