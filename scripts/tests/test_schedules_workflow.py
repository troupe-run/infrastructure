"""schedules.yml runs the schedule watch daily, and only its board job can read the board App's key
(spec: schedule-watch, board-credentials; watch-website-link-check design D1, D5 to D7).

GitHub evaluates the workflow, so these tests pin what it's given: when it runs, what each job's
token may do, the environment that holds the key, and the check on the URL the board job is
handed."""

import copy
import re
from typing import Any

import pytest
import yaml
from conftest import REPO

SCHEDULES = REPO / ".github" / "workflows" / "schedules.yml"
BOARD_IF = "!cancelled() && needs.watch.outputs.issue-url != ''"
# The URLs the board job's check must accept and refuse (design D5).
ACCEPTED = ["https://github.com/troupe-run/infrastructure/issues/12"]
REFUSED = [
    "",
    "https://github.com/troupe-run/website/issues/12",
    "https://github.com/troupe-run/infrastructure/pull/12",
    "https://github.com/troupe-run/infrastructure/issues/12/x",
    "https://github.com/troupe-run/infrastructure/issues/",
    "http://github.com/troupe-run/infrastructure/issues/12",
]


def schedules() -> dict[str, Any]:
    loaded = yaml.safe_load(SCHEDULES.read_text(encoding="utf-8"))
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


def url_pattern(job: dict[str, Any]) -> str | None:
    """The pattern the board job's script checks ISSUE_URL against, if it has exactly one."""
    script = "\n".join(str(step.get("run", "")) for step in job.get("steps", []))
    found = re.findall(r'\[\[ ! "\$ISSUE_URL" =~ (\S+) \]\]', script)
    return found[0] if len(found) == 1 else None


def problems(workflow: dict[str, Any]) -> list[str]:
    found = []
    on = workflow.get("on") or {}
    if set(on) != {"schedule", "workflow_dispatch"}:
        found.append(f"it runs on {sorted(on)}, not a schedule and by hand only")
    crons = [entry.get("cron") for entry in on.get("schedule") or []]
    if len(crons) != 1 or not re.fullmatch(r"\d+ \d+ \* \* \*", str(crons[0])):
        found.append(f"its schedule is {crons}, not once a day")
    inputs = (on.get("workflow_dispatch") or {}).get("inputs") or {}
    if set(inputs) != {"extra-workflow"}:
        found.append(f"a hand-started run takes {sorted(inputs)}, not extra-workflow only")
    if workflow.get("permissions") != {}:
        found.append(f"the default permissions are {workflow.get('permissions')!r}, not {{}}")

    jobs = workflow.get("jobs") or {}
    if set(jobs) != {"watch", "board"}:
        return [*found, f"its jobs are {sorted(jobs)}, not watch and board"]
    watch, board = jobs["watch"], jobs["board"]

    if watch.get("permissions") != {"contents": "read", "issues": "write"}:
        found.append(f"watch's GITHUB_TOKEN permissions are {watch.get('permissions')!r}")
    if "environment" in watch:
        found.append("watch has an environment, so it could read a secret")
    runs = [step for step in watch.get("steps", []) if "watch_schedules.py" in str(step.get("run"))]
    if len(runs) != 1:
        found.append("watch doesn't run scripts/watch_schedules.py exactly once")
    else:
        step = runs[0]
        if step.get("id") != "watch":
            found.append("the step that runs the watch isn't id watch, so issue-url isn't read")
        if (step.get("env") or {}).get("GH_TOKEN") != "${{ github.token }}":
            found.append("the watch doesn't run with GITHUB_TOKEN")
        if "${{" in str(step.get("run")):
            found.append("the watch's command line holds an expression; pass it through env")
    outputs = watch.get("outputs") or {}
    if outputs.get("issue-url") != "${{ steps.watch.outputs.issue-url }}":
        found.append(f"watch's issue-url output is {outputs.get('issue-url')!r}")

    if board.get("needs") not in ("watch", ["watch"]):
        found.append(f"board needs {board.get('needs')!r}, not watch")
    if condition(board) != BOARD_IF:
        found.append(f"board runs on {condition(board)!r}, not {BOARD_IF!r}")
    environment = board.get("environment")
    name = environment.get("name") if isinstance(environment, dict) else environment
    if name != "board":
        found.append(f"board's environment is {environment!r}, not board")
    if board.get("permissions") != {}:
        found.append(f"board's GITHUB_TOKEN permissions are {board.get('permissions')!r}")
    if steps_using(board, "actions/checkout"):
        found.append("board checks out the repository; it needs no code")
    tokens = steps_using(board, "create-github-app-token")
    if len(tokens) != 1:
        found.append("board doesn't mint exactly one App token")
    else:
        inputs = tokens[0].get("with") or {}
        granted = {key: value for key, value in inputs.items() if key.startswith("permission-")}
        if granted != {"permission-organization-projects": "write"}:
            found.append(f"board's token asks for {granted}")
        if inputs.get("private-key") != "${{ secrets.BOARD_APP_PRIVATE_KEY }}":
            found.append(f"board's token is minted from {inputs.get('private-key')!r}")
        if inputs.get("client-id") != "${{ vars.BOARD_APP_CLIENT_ID }}":
            found.append(f"board's token names the App with {inputs.get('client-id')!r}")
    pattern = url_pattern(board)
    if pattern is None:
        found.append("board doesn't check ISSUE_URL against one pattern")
    else:
        for url in ACCEPTED:
            if not re.search(pattern, url):
                found.append(f"board's check refuses {url!r}")
        for url in REFUSED:
            if re.search(pattern, url):
                found.append(f"board's check accepts {url!r}")
    script = "\n".join(str(step.get("run", "")) for step in board.get("steps", []))
    if 'gh project item-add 1 --owner troupe-run --url "$ISSUE_URL"' not in script:
        found.append("board doesn't add ISSUE_URL to project 1")
    return found


def test_the_workflow_is_as_designed() -> None:
    assert problems(schedules()) == []


def board_token(jobs: dict[str, Any]) -> dict[str, Any]:
    return steps_using(jobs["board"], "create-github-app-token")[0]["with"]  # type: ignore[no-any-return]


def board_script(jobs: dict[str, Any]) -> dict[str, Any]:
    return next(step for step in jobs["board"]["steps"] if "run" in step)


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (lambda w: w["on"].update({"pull_request": None}), "not a schedule and by hand only"),
        (lambda w: w["on"].update({"schedule": [{"cron": "0 * * * *"}]}), "not once a day"),
        (
            lambda w: w["on"]["workflow_dispatch"]["inputs"].update({"other": {}}),
            "not extra-workflow only",
        ),
        (lambda w: w.update({"permissions": {"issues": "write"}}), "not {}"),
        (lambda w: w["jobs"].pop("board"), "not watch and board"),
        (
            lambda w: w["jobs"]["watch"]["permissions"].update({"actions": "write"}),
            "watch's GITHUB_TOKEN permissions",
        ),
        (lambda w: w["jobs"]["watch"].update({"environment": "board"}), "could read a secret"),
        (lambda w: w["jobs"]["watch"].update({"outputs": {}}), "issue-url output"),
        (
            lambda w: w["jobs"]["watch"]["steps"][-1]["env"].update({"GH_TOKEN": "x"}),
            "doesn't run with GITHUB_TOKEN",
        ),
        (
            lambda w: w["jobs"]["watch"]["steps"][-1].update(
                {"run": "uv run scripts/watch_schedules.py ${{ inputs.extra-workflow }}"}
            ),
            "holds an expression",
        ),
        (lambda w: w["jobs"]["board"].update({"if": "always()"}), "board runs on"),
        (lambda w: w["jobs"]["board"].update({"needs": []}), "board needs"),
        (lambda w: w["jobs"]["board"].update({"environment": "plan-main"}), "not board"),
        (
            lambda w: w["jobs"]["board"].update({"permissions": {"issues": "write"}}),
            "board's GITHUB_TOKEN permissions",
        ),
        (
            lambda w: w["jobs"]["board"]["steps"].insert(0, {"uses": "actions/checkout@v7"}),
            "board checks out",
        ),
        (
            lambda w: board_token(w["jobs"]).update({"permission-issues": "write"}),
            "board's token asks for",
        ),
        (
            lambda w: board_token(w["jobs"]).update(
                {"private-key": "${{ secrets.TF_VAR_github_app_pem }}"}
            ),
            "minted from",
        ),
        (
            lambda w: board_script(w["jobs"]).update(
                {"run": board_script(w["jobs"])["run"].replace("infrastructure", "[a-z]+")}
            ),
            "board's check accepts 'https://github.com/troupe-run/website/issues/12'",
        ),
        (
            lambda w: board_script(w["jobs"]).update(
                {"run": board_script(w["jobs"])["run"].replace("[0-9]+$ ", "[0-9]+ ")}
            ),
            "board's check accepts 'https://github.com/troupe-run/infrastructure/issues/12/x'",
        ),
        (
            lambda w: board_script(w["jobs"]).update(
                {"run": board_script(w["jobs"])["run"].replace("item-add 1", "item-add 2")}
            ),
            "doesn't add ISSUE_URL to project 1",
        ),
    ],
)
def test_each_way_the_workflow_can_go_wrong_is_named(change: Any, named: str) -> None:  # noqa: ANN401
    workflow = copy.deepcopy(schedules())
    change(workflow)
    assert any(named in problem for problem in problems(workflow)), problems(workflow)
