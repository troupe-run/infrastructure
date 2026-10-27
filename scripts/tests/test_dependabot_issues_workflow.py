"""dependabot-issues.yml runs from main on a schedule, never touches a pull request's code, and only
its jobs' environments hold the Apps' keys (spec: dependency-updates, dependabot-issue-credentials;
dependabot-issues design D1, D6, D7).

GitHub evaluates the workflow, so these tests pin what it's given: when it runs, what it checks out,
what each job's token may do, the environment that holds each key, and the check on the URLs the
board job is handed."""

import copy
import re
from collections.abc import Callable
from typing import Any

import pytest
import yaml
from conftest import REPO

WORKFLOW = REPO / ".github" / "workflows" / "dependabot-issues.yml"
BOARD_IF = (
    "!cancelled() && needs.issues.outputs.issue-urls != '' && "
    "needs.issues.outputs.issue-urls != '[]'"
)
ACCEPTED = [
    "https://github.com/troupe-run/troupe/issues/1",
    "https://github.com/troupe-run/website/issues/12",
    "https://github.com/troupe-run/infrastructure/issues/123",
]
REFUSED = [
    "",
    "https://github.com/troupe-run/.github/issues/12",
    "https://github.com/troupe-run/website/pull/12",
    "https://github.com/troupe-run/website/issues/12/x",
    "https://github.com/troupe-run/website/issues/",
    "http://github.com/troupe-run/website/issues/12",
    "https://github.com/other/website/issues/12",
]


def workflow() -> dict[str, Any]:
    loaded = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    # YAML 1.1 reads the key `on` as true.
    loaded["on"] = loaded.pop(True, loaded.get("on"))
    return loaded


def condition(job: dict[str, Any]) -> str:
    text = str(job.get("if", "")).strip()
    if text.startswith("${{") and text.endswith("}}"):
        text = text[3:-2]
    return " ".join(text.split())


def steps_using(job: dict[str, Any], action: str) -> list[dict[str, Any]]:
    return [step for step in job.get("steps", []) if action in str(step.get("uses", ""))]


def environment_of(job: dict[str, Any]) -> object:
    environment = job.get("environment")
    return environment.get("name") if isinstance(environment, dict) else environment


def token_problems(
    job: dict[str, Any], name: str, key: str, client: str, granted: dict[str, str]
) -> list[str]:
    tokens = steps_using(job, "create-github-app-token")
    if len(tokens) != 1:
        return [f"{name} doesn't mint exactly one App token"]
    inputs = tokens[0].get("with") or {}
    found = []
    asked = {k: v for k, v in inputs.items() if k.startswith("permission-")}
    if asked != granted:
        found.append(f"{name}'s token asks for {asked}")
    if inputs.get("private-key") != f"${{{{ secrets.{key} }}}}":
        found.append(f"{name}'s token is minted from {inputs.get('private-key')!r}")
    if inputs.get("client-id") != f"${{{{ vars.{client} }}}}":
        found.append(f"{name}'s token names the App with {inputs.get('client-id')!r}")
    if "repositories" in inputs:
        found.append(f"{name}'s token lists repositories; the installation is the one list")
    return found


def url_pattern(job: dict[str, Any]) -> str | None:
    """The pattern the board job checks each ISSUE_URL against, if it has exactly one."""
    script = "\n".join(str(step.get("run", "")) for step in job.get("steps", []))
    found = re.findall(r'\[\[ ! "\$ISSUE_URL" =~ (\S+) \]\]', script)
    return found[0] if len(found) == 1 else None


def problems(w: dict[str, Any]) -> list[str]:
    found = []
    on = w.get("on") or {}
    if set(on) != {"schedule", "workflow_dispatch"}:
        found.append(f"it runs on {sorted(on)}, not a schedule and by hand only")
    crons = [entry.get("cron") for entry in on.get("schedule") or []]
    if crons != ["*/10 * * * *"]:
        found.append(f"its schedule is {crons}, not every 10 minutes")
    if w.get("permissions") != {}:
        found.append(f"the default permissions are {w.get('permissions')!r}, not {{}}")
    if w.get("concurrency") != {"group": "dependabot-issues", "cancel-in-progress": False}:
        found.append(f"its concurrency is {w.get('concurrency')!r}: two runs could overlap")
    text = WORKFLOW.read_text(encoding="utf-8")
    if re.search(r"\$\{\{[^}]*github\.event", yaml.safe_dump(w)) or "github.event" in text:
        found.append("an expression reads github.event: a pull request's text could reach a step")

    jobs = w.get("jobs") or {}
    if set(jobs) != {"issues", "board"}:
        return [*found, f"its jobs are {sorted(jobs)}, not issues and board"]
    issues, board = jobs["issues"], jobs["board"]

    checkouts = [step for job in jobs.values() for step in steps_using(job, "actions/checkout")]
    if len(checkouts) != 1:
        found.append(f"it has {len(checkouts)} checkouts, not one of this repository")
    for step in checkouts:
        given = step.get("with") or {}
        if "ref" in given or "repository" in given:
            found.append(f"a checkout chooses what it checks out: {given!r}")
    if not steps_using(issues, "actions/checkout"):
        found.append("issues doesn't check out this repository to run the script")

    if environment_of(issues) != "dependabot-issues":
        found.append(f"issues' environment is {issues.get('environment')!r}")
    if issues.get("permissions") != {"contents": "read"}:
        found.append(f"issues' GITHUB_TOKEN permissions are {issues.get('permissions')!r}")
    found += token_problems(
        issues,
        "issues",
        "DEPENDABOT_APP_PRIVATE_KEY",
        "DEPENDABOT_APP_CLIENT_ID",
        {"permission-issues": "write", "permission-pull-requests": "write"},
    )
    runs = [s for s in issues.get("steps", []) if "dependabot_issues.py" in str(s.get("run"))]
    if len(runs) != 1:
        found.append("issues doesn't run scripts/dependabot_issues.py exactly once")
    else:
        step = runs[0]
        if step.get("id") != "issues":
            found.append("the step that runs the script isn't id issues, so issue-urls isn't read")
        if (step.get("env") or {}).get("GH_TOKEN") != "${{ steps.app-token.outputs.token }}":
            found.append("the script doesn't run with the App's token")
        if "${{" in str(step.get("run")):
            found.append("the script's command line holds an expression")
    if (issues.get("outputs") or {}).get("issue-urls") != "${{ steps.issues.outputs.issue-urls }}":
        found.append(f"issues' issue-urls output is {issues.get('outputs')!r}")

    if board.get("needs") not in ("issues", ["issues"]):
        found.append(f"board needs {board.get('needs')!r}, not issues")
    if condition(board) != BOARD_IF:
        found.append(f"board runs on {condition(board)!r}, not {BOARD_IF!r}")
    if environment_of(board) != "board":
        found.append(f"board's environment is {board.get('environment')!r}, not board")
    if board.get("permissions") != {}:
        found.append(f"board's GITHUB_TOKEN permissions are {board.get('permissions')!r}")
    found += token_problems(
        board,
        "board",
        "BOARD_APP_PRIVATE_KEY",
        "BOARD_APP_CLIENT_ID",
        {"permission-organization-projects": "write"},
    )
    pattern = url_pattern(board)
    if pattern is None:
        found.append("board doesn't check ISSUE_URL against one pattern")
    else:
        found += [f"board's check refuses {u!r}" for u in ACCEPTED if not re.search(pattern, u)]
        found += [f"board's check accepts {u!r}" for u in REFUSED if re.search(pattern, u)]
    script = "\n".join(str(step.get("run", "")) for step in board.get("steps", []))
    if 'gh project item-add 1 --owner troupe-run --url "$ISSUE_URL"' not in script:
        found.append("board doesn't add ISSUE_URL to project 1")
    return found


def test_the_workflow_is_as_designed() -> None:
    assert problems(workflow()) == []


def token(jobs: dict[str, Any], job: str) -> dict[str, Any]:
    return steps_using(jobs[job], "create-github-app-token")[0]["with"]  # type: ignore[no-any-return]


def script(jobs: dict[str, Any]) -> dict[str, Any]:
    return next(step for step in jobs["board"]["steps"] if "run" in step)


def checkout(jobs: dict[str, Any]) -> dict[str, Any]:
    return steps_using(jobs["issues"], "actions/checkout")[0]


HEAD = "${{ github.event.pull_request.head.sha }}"
Change = Callable[[dict[str, Any]], object]


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (lambda w: w["on"].update({"pull_request_target": None}), "not a schedule and by hand"),
        (lambda w: w["on"].update({"pull_request": None}), "not a schedule and by hand"),
        (lambda w: w["on"].update({"workflow_run": None}), "not a schedule and by hand"),
        (lambda w: w["on"].update({"schedule": [{"cron": "0 * * * *"}]}), "every 10 minutes"),
        (lambda w: w.update({"permissions": {"issues": "write"}}), "not {}"),
        (lambda w: w["concurrency"].update({"cancel-in-progress": True}), "could overlap"),
        (lambda w: w.pop("concurrency"), "could overlap"),
        (lambda w: checkout(w["jobs"]).update({"with": {"ref": HEAD}}), "chooses what it checks"),
        (
            lambda w: checkout(w["jobs"]).update({"with": {"repository": "troupe-run/website"}}),
            "chooses what it checks",
        ),
        (lambda w: w["jobs"]["board"]["steps"].insert(0, checkout(w["jobs"])), "2 checkouts"),
        (
            lambda w: w["jobs"]["issues"]["steps"][-1]["env"].update({"TITLE": HEAD}),
            "reads github.event",
        ),
        (lambda w: w["jobs"]["issues"].update({"environment": "board"}), "issues' environment"),
        (
            lambda w: w["jobs"]["issues"]["permissions"].update({"pull-requests": "write"}),
            "issues' GITHUB_TOKEN permissions",
        ),
        (
            lambda w: token(w["jobs"], "issues").update({"permission-contents": "write"}),
            "issues's token asks for",
        ),
        (
            lambda w: token(w["jobs"], "issues").update({"repositories": "website"}),
            "lists repositories",
        ),
        (
            lambda w: token(w["jobs"], "issues").update(
                {"private-key": "${{ secrets.BOARD_APP_PRIVATE_KEY }}"}
            ),
            "issues's token is minted from",
        ),
        (
            lambda w: w["jobs"]["issues"]["steps"][-1]["env"].update(
                {"GH_TOKEN": "${{ github.token }}"}
            ),
            "doesn't run with the App's token",
        ),
        (
            lambda w: w["jobs"]["issues"]["steps"][-1].update(
                {"run": "uv run scripts/dependabot_issues.py ${{ inputs.x }}"}
            ),
            "holds an expression",
        ),
        (lambda w: w["jobs"]["issues"].update({"outputs": {}}), "issue-urls output"),
        (lambda w: w["jobs"]["board"].update({"if": "always()"}), "board runs on"),
        (lambda w: w["jobs"]["board"].update({"needs": []}), "board needs"),
        (lambda w: w["jobs"]["board"].update({"environment": "dependabot-issues"}), "not board"),
        (
            lambda w: token(w["jobs"], "board").update({"permission-issues": "write"}),
            "board's token asks for",
        ),
        (
            lambda w: script(w["jobs"]).update(
                {"run": script(w["jobs"])["run"].replace("(troupe|website|infrastructure)", ".+")}
            ),
            "board's check accepts 'https://github.com/troupe-run/.github/issues/12'",
        ),
        (
            lambda w: script(w["jobs"]).update(
                {"run": script(w["jobs"])["run"].replace("item-add 1", "item-add 2")}
            ),
            "doesn't add ISSUE_URL to project 1",
        ),
    ],
)
def test_each_departure_is_named(change: Change, named: str) -> None:
    w = copy.deepcopy(workflow())
    change(w)
    assert any(named in problem for problem in problems(w)), problems(w)
