"""tofu.yml shows each plan through plan_comment.py, linked to the full plan it uploads, and never
cuts plan.txt with `head -c` (spec: ci-apply; truncate-long-plans design D1, D5).

GitHub runs the workflow, so these tests pin what it's given: which step uploads plan.txt, after
the check that it holds no key, and which step passes that upload's link to plan_comment.py."""

import copy
from collections.abc import Callable
from typing import Any

import pytest
import yaml
from conftest import REPO

TOFU = REPO / ".github" / "workflows" / "tofu.yml"

# Each job that shows a plan: the step that shows it, and plan_comment.py's target there.
SHOWN = {
    "pr-plan": ("Post the plan on the pull request", "comment"),
    "plan": ("Show the plan for approval", "summary"),
}
CHECKED = "The plan holds no key"


def tofu() -> dict[str, Any]:
    loaded = yaml.safe_load(TOFU.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def index(steps: list[dict[str, Any]], name: str) -> int | None:
    found = [i for i, step in enumerate(steps) if step.get("name") == name]
    return found[0] if len(found) == 1 else None


def problems(workflow: dict[str, Any]) -> list[str]:
    found = []
    for job_name, job in workflow["jobs"].items():
        for step in job.get("steps", []):
            run = str(step.get("run", ""))
            if "head -c" in run and "plan.txt" in run:
                found.append(f"{job_name}: {step.get('name')!r} cuts plan.txt with head -c")
    for job_name, (shown_name, target) in SHOWN.items():
        steps = workflow["jobs"][job_name]["steps"]
        uploads = [
            i
            for i, step in enumerate(steps)
            if "actions/upload-artifact" in str(step.get("uses", ""))
            and str(step.get("with", {}).get("path", "")).endswith("/plan.txt")
        ]
        if len(uploads) != 1:
            found.append(f"{job_name}: {len(uploads)} steps upload plan.txt, not one")
            continue
        upload = steps[uploads[0]]
        if upload.get("with", {}).get("archive") is not False:
            found.append(f"{job_name}: plan.txt is uploaded zipped")
        checked, shown = index(steps, CHECKED), index(steps, shown_name)
        if checked is None or shown is None:
            found.append(f"{job_name}: no single {CHECKED!r} and {shown_name!r} step")
            continue
        if not checked < uploads[0] < shown:
            found.append(f"{job_name}: plan.txt isn't uploaded between {CHECKED!r} and showing it")
        step = steps[shown]
        link = f"${{{{ steps.{upload.get('id')}.outputs.artifact-url }}}}"
        if step.get("env", {}).get("PLAN_URL") != link:
            found.append(f"{job_name}: {shown_name!r} doesn't get the upload's artifact-url")
        run = " ".join(str(step.get("run", "")).replace("\\\n", " ").split())
        if f"scripts/plan_comment.py --target {target}" not in run:
            found.append(
                f"{job_name}: {shown_name!r} doesn't run plan_comment.py --target {target}"
            )
        if '--plan-url "$PLAN_URL"' not in run:
            found.append(f"{job_name}: {shown_name!r} doesn't pass $PLAN_URL to plan_comment.py")
    return found


def test_every_plan_is_shown_through_plan_comment_with_its_upload_linked() -> None:
    assert problems(tofu()) == []


def step(workflow: dict[str, Any], job: str, name: str) -> dict[str, Any]:
    steps = workflow["jobs"][job]["steps"]
    found = index(steps, name)
    assert found is not None
    result = steps[found]
    assert isinstance(result, dict)
    return result


def upload(workflow: dict[str, Any], job: str) -> dict[str, Any]:
    return step(workflow, job, "Keep the full plan")


def cut_with_head(workflow: dict[str, Any], job: str) -> None:
    step(workflow, job, SHOWN[job][0])["run"] += 'head -c 60000 "$RUNNER_TEMP/plan.txt"\n'


def drop_upload(workflow: dict[str, Any], job: str) -> None:
    workflow["jobs"][job]["steps"].remove(upload(workflow, job))


def zip_upload(workflow: dict[str, Any], job: str) -> None:
    del upload(workflow, job)["with"]["archive"]


def upload_before_the_check(workflow: dict[str, Any], job: str) -> None:
    steps = workflow["jobs"][job]["steps"]
    moved = upload(workflow, job)
    steps.remove(moved)
    steps.insert(0, moved)


def wrong_link(workflow: dict[str, Any], job: str) -> None:
    step(workflow, job, SHOWN[job][0])["env"]["PLAN_URL"] = "${{ github.server_url }}"


def wrong_target(workflow: dict[str, Any], job: str) -> None:
    shown = step(workflow, job, SHOWN[job][0])
    other = "summary" if SHOWN[job][1] == "comment" else "comment"
    shown["run"] = shown["run"].replace(f"--target {SHOWN[job][1]}", f"--target {other}")


def no_link_passed(workflow: dict[str, Any], job: str) -> None:
    shown = step(workflow, job, SHOWN[job][0])
    shown["run"] = shown["run"].replace('--plan-url "$PLAN_URL"', '--plan-url "$RUN_URL"')


@pytest.mark.parametrize("job", sorted(SHOWN))
@pytest.mark.parametrize(
    "mutate",
    [
        cut_with_head,
        drop_upload,
        zip_upload,
        upload_before_the_check,
        wrong_link,
        wrong_target,
        no_link_passed,
    ],
)
def test_each_way_of_breaking_it_is_caught(
    job: str, mutate: Callable[[dict[str, Any], str], None]
) -> None:
    workflow = copy.deepcopy(tofu())
    mutate(workflow, job)
    assert problems(workflow) != []
