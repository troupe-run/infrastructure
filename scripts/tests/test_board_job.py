"""tofu.yml plans the board's Capability descriptions with a token that only reads, and sets them
after the approved apply with the board App's token, from its main-only environment (spec: labels;
board-capability-descriptions design D1).

GitHub evaluates the workflow, so these tests pin what it's given: when each part runs, the
environment that gives it a key, and what each token may do."""

import copy
from typing import Any

import pytest
import yaml
from conftest import REPO

TOFU = REPO / ".github" / "workflows" / "tofu.yml"
PLAN_FILE = "tofu/board-plan.json"


def tofu() -> dict[str, Any]:
    loaded = yaml.safe_load(TOFU.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def condition(value: Any) -> str:  # noqa: ANN401
    return " ".join(str(value or "").split())


def needs(job: dict[str, Any]) -> list[str]:
    value = job.get("needs", [])
    return [value] if isinstance(value, str) else list(value)


def step(job: dict[str, Any], **match: str) -> dict[str, Any] | None:
    """The one step whose fields contain these values, or None."""
    found = [
        s
        for s in job.get("steps", [])
        if all(value in str(s.get(key, "")) for key, value in match.items())
    ]
    return found[0] if len(found) == 1 else None


def granted(token: dict[str, Any] | None) -> dict[str, str]:
    inputs = (token or {}).get("with", {})
    return {k: v for k, v in inputs.items() if k.startswith("permission-")}


def token_ref(token: dict[str, Any] | None) -> str:
    return f"${{{{ steps.{(token or {}).get('id')}.outputs.token }}}}"


def plan_problems(workflow: dict[str, Any]) -> list[str]:
    job = workflow["jobs"]["plan"]
    found = []
    board = step(job, run="board_options.py plan")
    if board is None:
        return ["the plan job doesn't run board_options.py plan exactly once"]
    if board.get("id") != "board":
        found.append(f"board_options.py plan's step id is {board.get('id')!r}, not board")
    if PLAN_FILE not in str(board["run"]):
        found.append(f"board_options.py plan doesn't write {PLAN_FILE}")
    # A board that can't be read never fails the plan (design D9).
    if "board_options.py plan --ci" not in str(board["run"]):
        found.append("board_options.py plan runs without --ci, so an unread board fails the plan")
    if f"[ -f {PLAN_FILE} ]" not in str(board["run"]):
        found.append(f"the board step reads {PLAN_FILE} without checking it was written")
    token = step(job, id="board-token")
    if token is not None and token.get("continue-on-error") is not True:
        found.append("a failed board token fails the plan; it should continue on error")
    if granted(token) != {"permission-organization-projects": "read"}:
        found.append(f"the plan's board token asks for {granted(token)}, not projects: read")
    if board.get("env", {}).get("GH_TOKEN") != token_ref(token):
        found.append("board_options.py plan doesn't read with the read-only board token")
    outputs = job.get("outputs", {})
    if "steps.board.outputs.changes == 'true'" not in str(outputs.get("changes")):
        found.append("the plan's changes output doesn't count the board's changes")
    if outputs.get("board_changes") != "${{ steps.board.outputs.changes }}":
        found.append("the plan job doesn't hand over board_changes")
    keep = step(job, name="Keep the saved plan")
    if keep is None or PLAN_FILE not in str(keep.get("with", {}).get("path")):
        found.append(f"the saved plan artifact doesn't carry {PLAN_FILE}")
    elif "steps.board.outputs.changes == 'true'" not in condition(keep.get("if")):
        found.append("the saved plan isn't kept when only the board has changes")
    show = step(job, name="Show the plan for approval")
    if show is None or "board.md" not in str(show.get("run")):
        found.append("the plan's summary doesn't show the board's descriptions")
    return found


def board_problems(workflow: dict[str, Any]) -> list[str]:
    jobs = workflow["jobs"]
    if "board" not in jobs:
        return ["there is no board job"]
    job = jobs["board"]
    found = []
    if sorted(needs(job)) != ["apply", "plan"]:
        found.append(f"board needs {needs(job)}, not plan and apply")
    wanted = "needs.apply.result == 'success' && needs.plan.outputs.board_changes == 'true'"
    if condition(job.get("if")) != wanted:
        found.append(f"board runs on {condition(job.get('if'))!r}, not {wanted!r}")
    environment = job.get("environment", {})
    name = environment.get("name") if isinstance(environment, dict) else environment
    if name != "board":
        found.append(f"board's environment is {environment!r}, not board")
    if job.get("permissions") != {"contents": "read"}:
        found.append(f"board's GITHUB_TOKEN permissions are {job.get('permissions')!r}")
    token = step(job, uses="create-github-app-token")
    if granted(token) != {"permission-organization-projects": "write"}:
        found.append(f"board's token asks for {granted(token)}, not projects: write")
    inputs = (token or {}).get("with", {})
    if (
        inputs.get("client-id") != "${{ vars.BOARD_APP_CLIENT_ID }}"
        or inputs.get("private-key") != "${{ secrets.BOARD_APP_PRIVATE_KEY }}"
    ):
        found.append("board's token isn't the board App's")
    run = step(job, run="board_options.py apply")
    if run is None or f"--board-plan {PLAN_FILE}" not in str(run.get("run")):
        found.append(f"board doesn't run board_options.py apply on {PLAN_FILE}")
    elif run.get("env", {}).get("GH_TOKEN") != token_ref(token):
        found.append("board_options.py apply doesn't send with the board App's token")
    checkout = step(job, uses="actions/checkout")
    if checkout is None or checkout.get("with", {}).get("ref") != "${{ needs.plan.outputs.sha }}":
        found.append("board doesn't check out the commit that was planned")
    return found


def test_the_plan_job_plans_the_board_s_descriptions_reading_only() -> None:
    assert plan_problems(tofu()) == []


def test_the_board_job_sets_them_after_the_apply_from_the_board_environment() -> None:
    assert board_problems(tofu()) == []


def board_token(jobs: dict[str, Any]) -> dict[str, Any]:
    found = step(jobs["board"], uses="create-github-app-token")
    assert found is not None
    return found


def plan_token(jobs: dict[str, Any]) -> dict[str, Any]:
    found = step(jobs["plan"], id="board-token")
    assert found is not None
    return found


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (lambda jobs: jobs.pop("board"), "there is no board job"),
        (lambda jobs: jobs["board"].update({"needs": "plan"}), "not plan and apply"),
        (
            lambda jobs: jobs["board"].update({"if": "needs.plan.outputs.board_changes == 'true'"}),
            "board runs on",
        ),
        (lambda jobs: jobs["board"].update({"environment": "apply"}), "not board"),
        (
            lambda jobs: jobs["board"].update({"permissions": {"contents": "write"}}),
            "GITHUB_TOKEN permissions",
        ),
        (
            lambda jobs: board_token(jobs)["with"].update({"permission-issues": "write"}),
            "board's token asks for",
        ),
        (
            lambda jobs: board_token(jobs)["with"].update(
                {"private-key": "${{ secrets.TF_VAR_github_app_pem }}"}
            ),
            "isn't the board App's",
        ),
        (
            lambda jobs: jobs["board"]["steps"][-1].update({"env": {"GH_TOKEN": "x"}}),
            "doesn't send with the board App's token",
        ),
        (
            lambda jobs: jobs["board"]["steps"][0].update({"with": {"ref": "main"}}),
            "the commit that was planned",
        ),
    ],
)
def test_each_way_the_board_job_can_go_wrong_is_named(change: Any, named: str) -> None:  # noqa: ANN401
    workflow = copy.deepcopy(tofu())
    change(workflow["jobs"])
    assert any(named in problem for problem in board_problems(workflow)), board_problems(workflow)


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (
            lambda jobs: plan_token(jobs)["with"].update(
                {"permission-organization-projects": "write"}
            ),
            "not projects: read",
        ),
        (
            lambda jobs: jobs["plan"]["outputs"].update(
                {"changes": "${{ steps.plan.outputs.changes == 'true' }}"}
            ),
            "doesn't count the board's changes",
        ),
        (lambda jobs: jobs["plan"]["outputs"].pop("board_changes"), "board_changes"),
        (
            lambda jobs: step(jobs["plan"], run="board_options.py plan").update(  # type: ignore[union-attr]
                {"run": "uv run scripts/board_options.py plan --out tofu/board-plan.json"}
            ),
            "without --ci",
        ),
        (lambda jobs: plan_token(jobs).pop("continue-on-error"), "continue on error"),
        (
            lambda jobs: step(jobs["plan"], name="Keep the saved plan")["with"].update(  # type: ignore[index]
                {"path": "tofu/main.tfplan"}
            ),
            "doesn't carry",
        ),
        (
            lambda jobs: step(jobs["plan"], run="board_options.py plan")["env"].update(  # type: ignore[index]
                {"GH_TOKEN": "${{ github.token }}"}
            ),
            "read-only board token",
        ),
    ],
)
def test_each_way_the_plan_s_board_part_can_go_wrong_is_named(change: Any, named: str) -> None:  # noqa: ANN401
    workflow = copy.deepcopy(tofu())
    change(workflow["jobs"])
    assert any(named in problem for problem in plan_problems(workflow)), plan_problems(workflow)
