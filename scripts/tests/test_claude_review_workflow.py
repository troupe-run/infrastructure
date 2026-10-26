"""claude-review.yml reviews each member's pull request and can't change the repository (spec:
pr-review; claude-pr-review design D1 to D4, D7, D8).

GitHub evaluates the workflow, so these tests pin what it's given: when it runs and what it
skips, what its token may do, which credentials reach the action, and which tools Claude has."""

import copy
import re
import shlex
from typing import Any

import pytest
import yaml
from conftest import REPO

REVIEW = REPO / ".github" / "workflows" / "claude-review.yml"
EVENTS = ["opened", "synchronize", "reopened", "ready_for_review"]
# The run's own token only checks out the code (design D1). No id-token: without it the action can't
# swap OIDC for a Claude App token that writes contents.
PERMISSIONS = {"contents": "read"}
# Every write is made with the review App's token, minted for this repository with exactly these.
MINTER = "actions/create-github-app-token"
# The review App's client ID, written in the workflow: it isn't a secret (minting also needs the
# key), and a variable set by an apply wouldn't exist for a pull request's run before its merge.
REVIEW_APP_CLIENT_ID = re.compile(r"^Iv[0-9A-Za-z]{16,}$")
TOKEN_INPUTS = {
    "private-key": "${{ secrets.REVIEW_APP_PRIVATE_KEY }}",
    "owner": "${{ github.repository_owner }}",
    "repositories": "${{ github.event.repository.name }}",
    "permission-contents": "read",
    "permission-pull-requests": "write",
}
# Bots' pull requests and forks' are skipped, not failed (design D2).
SKIP = (
    "github.event.pull_request.user.type != 'Bot' && "
    "github.event.pull_request.head.repo.full_name == github.repository"
)
CONCURRENCY = {
    "group": "claude-review-${{ github.event.pull_request.number }}",
    "cancel-in-progress": True,
}
ACTION = "anthropics/claude-code-action"
# What reaches the action: the review App's token for GitHub, the org secret for Claude (design
# D1, D3).
CREDENTIALS = {
    "github_token": "${{ steps.app-token.outputs.token }}",
    "claude_code_oauth_token": "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}",
}
# Inputs that would widen what the action does or who can start it, or print what it saw.
REFUSED_INPUTS = {
    "anthropic_api_key",
    "anthropic_federation_rule_id",
    "allowed_bots",
    "allowed_non_write_users",
    "additional_permissions",
    "show_full_output",
    "display_report",
    "use_commit_signing",
    "ssh_signing_key",
}
# Read the pull request and the checkout, comment on it, nothing else (design D4). No Edit, Write,
# git or `gh pr review`, which is what keeps the review advisory.
TOOLS = {
    "mcp__github_inline_comment__create_inline_comment",
    "Bash(gh pr comment:*)",
    "Bash(gh pr diff:*)",
    "Bash(gh pr view:*)",
    "Bash(gh issue view:*)",
    "Read",
    "Grep",
    "Glob",
}
# Settings from the user scope only, which the action writes itself: none from the repository, so
# the guard's Claude Code hooks in .claude/settings.json don't load. They're written for an agent
# in the owner's terminal, and they grant gh writes the review mustn't have (owner, 2026-10-26;
# design D8).
SETTING_SOURCES = "user"
PINNED = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")


def review() -> dict[str, Any]:
    loaded = yaml.safe_load(REVIEW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    # YAML 1.1 reads the key `on` as true.
    loaded["on"] = loaded.pop(True, loaded.get("on"))
    return loaded


def claude_args(inputs: dict[str, Any]) -> tuple[set[str], str | None, list[str]]:
    """The allowed tools, the setting sources, and every other flag, in the action's claude_args."""
    words = shlex.split(str(inputs.get("claude_args", "")))
    tools: set[str] = set()
    sources = None
    others = []
    i = 0
    while i < len(words):
        if words[i] == "--allowedTools" and i + 1 < len(words):
            tools |= {tool.strip() for tool in words[i + 1].split(",") if tool.strip()}
            i += 2
        elif words[i] == "--max-turns" and i + 1 < len(words) and words[i + 1].isdigit():
            i += 2
        elif words[i] == "--setting-sources" and i + 1 < len(words):
            sources = words[i + 1]
            i += 2
        else:
            others.append(words[i])
            i += 1
    return tools, sources, others


def problems(workflow: dict[str, Any]) -> list[str]:
    found = []
    on = workflow.get("on") or {}
    if set(on) != {"pull_request"}:
        found.append(f"it runs on {sorted(on)}, not on pull_request only")
    types = (on.get("pull_request") or {}).get("types")
    if types != EVENTS:
        found.append(f"it runs on pull_request {types!r}, not {EVENTS!r}")
    if workflow.get("permissions") != PERMISSIONS:
        found.append(
            f"the default permissions are {workflow.get('permissions')!r}, not {PERMISSIONS!r}"
        )

    jobs = workflow.get("jobs") or {}
    if set(jobs) != {"review"}:
        return [*found, f"its jobs are {sorted(jobs)}, not review only"]
    job = jobs["review"]

    if job.get("if") != SKIP:
        found.append(f"review runs when {job.get('if')!r}, not skipping bots and forks")
    if job.get("permissions") != PERMISSIONS:
        found.append(
            f"review's GITHUB_TOKEN permissions are {job.get('permissions')!r}, not {PERMISSIONS!r}"
        )
    if "environment" in job:
        found.append(f"review runs in environment {job['environment']!r}; it needs none")
    concurrency = workflow.get("concurrency")
    if concurrency != CONCURRENCY:
        found.append(
            f"its concurrency is {concurrency!r}, not one run per pull request, cancelling the last"
        )
    if not isinstance(job.get("timeout-minutes"), int):
        found.append("review has no timeout-minutes")

    steps = job.get("steps") or []
    for step in steps:
        uses = step.get("uses")
        if uses is not None and not PINNED.match(str(uses)):
            found.append(f"{uses!r} isn't pinned to a full commit SHA")
        if "run" in step:
            found.append(
                f"review runs a command of its own ({step['run']!r}); only the action runs"
            )
    tokens = [step for step in steps if str(step.get("uses", "")).startswith(f"{MINTER}@")]
    actions = [step for step in steps if str(step.get("uses", "")).startswith(f"{ACTION}@")]
    if len(tokens) != 1:
        found.append(f"review mints {len(tokens)} App tokens, not the review App's one")
    else:
        token = tokens[0]
        if token.get("id") != "app-token":
            found.append(f"the token step's id is {token.get('id')!r}, not app-token")
        given = dict(token.get("with") or {})
        client_id = str(given.pop("client-id", ""))
        if not REVIEW_APP_CLIENT_ID.match(client_id):
            found.append(f"the review App's client ID is {client_id!r}, not one written here")
        if given != TOKEN_INPUTS:
            found.append(f"the review App's token is minted with {given!r}, not {TOKEN_INPUTS!r}")
        if actions and steps.index(token) > steps.index(actions[0]):
            found.append("the review App's token is minted after the action runs")
    if len(actions) != 1:
        return [*found, f"review uses {ACTION} {len(actions)} times, not once"]
    inputs = actions[0].get("with") or {}

    for name, value in CREDENTIALS.items():
        if inputs.get(name) != value:
            found.append(f"the action's {name} is {inputs.get(name)!r}, not {value!r}")
    for name in sorted(REFUSED_INPUTS & set(inputs)):
        found.append(f"the action is given {name}")
    if not str(inputs.get("prompt", "")).strip():
        found.append("the action has no prompt, so nothing says what the review checks")
    tools, sources, others = claude_args(inputs)
    if sources != SETTING_SOURCES:
        found.append(f"Claude loads settings from {sources!r}, not {SETTING_SOURCES!r} only")
    if tools != TOOLS:
        found.append(f"Claude's tools add {sorted(tools - TOOLS)} and drop {sorted(TOOLS - tools)}")
    if others:
        found.append(
            f"claude_args has {others!r} besides --allowedTools, --max-turns and --setting-sources"
        )
    if "--max-turns" not in str(inputs.get("claude_args", "")):
        found.append("claude_args has no --max-turns")
    return found


def test_the_workflow_is_as_designed() -> None:
    assert problems(review()) == []


def test_it_starts_with_its_source() -> None:
    first = REVIEW.read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("# Source: troupe-run/infrastructure."), first


def job(w: dict[str, Any]) -> dict[str, Any]:
    return w["jobs"]["review"]  # type: ignore[no-any-return]


def action(w: dict[str, Any]) -> dict[str, Any]:
    step = next(s for s in job(w)["steps"] if str(s.get("uses", "")).startswith(ACTION))
    return step["with"]  # type: ignore[no-any-return]


def token(w: dict[str, Any]) -> dict[str, Any]:
    step = next(s for s in job(w)["steps"] if str(s.get("uses", "")).startswith(MINTER))
    return step  # type: ignore[no-any-return]


def tools(w: dict[str, Any], change: str) -> None:
    action(w)["claude_args"] = str(action(w)["claude_args"]).replace("Bash(gh pr view:*)", change)


def sources(w: dict[str, Any], change: str) -> None:
    action(w)["claude_args"] = str(action(w)["claude_args"]).replace(
        "--setting-sources user", change
    )


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (lambda w: w.update({"on": {"pull_request_target": None}}), "not on pull_request only"),
        (lambda w: w["on"].update({"push": None}), "not on pull_request only"),
        (lambda w: w["on"]["pull_request"]["types"].append("edited"), "not ['opened'"),
        (lambda w: w["on"]["pull_request"]["types"].remove("synchronize"), "not ['opened'"),
        (lambda w: w["on"]["pull_request"]["types"].remove("ready_for_review"), "not ['opened'"),
        (lambda w: w.update({"permissions": {"contents": "write"}}), "default permissions"),
        (lambda w: w.pop("permissions"), "default permissions"),
        (lambda w: job(w).pop("if"), "not skipping bots and forks"),
        (
            lambda w: job(w).update({"if": "github.event.pull_request.user.type != 'Bot'"}),
            "not skipping bots and forks",
        ),
        (
            lambda w: job(w)["permissions"].update({"id-token": "write"}),
            "review's GITHUB_TOKEN permissions",
        ),
        (
            lambda w: job(w)["permissions"].update({"contents": "write"}),
            "review's GITHUB_TOKEN permissions",
        ),
        (
            lambda w: job(w)["permissions"].update({"pull-requests": "write"}),
            "review's GITHUB_TOKEN permissions",
        ),
        (
            lambda w: token(w)["with"].update({"permission-contents": "write"}),
            "the review App's token is minted with",
        ),
        (
            lambda w: token(w)["with"].update({"permission-issues": "write"}),
            "the review App's token is minted with",
        ),
        (
            lambda w: token(w)["with"].pop("repositories"),
            "the review App's token is minted with",
        ),
        (
            lambda w: token(w)["with"].update(
                {"private-key": "${{ secrets.DOCS_APP_PRIVATE_KEY }}"}
            ),
            "the review App's token is minted with",
        ),
        (lambda w: token(w).update({"id": "token"}), "not app-token"),
        (
            lambda w: token(w)["with"].update({"client-id": "${{ vars.REVIEW_APP_CLIENT_ID }}"}),
            "client ID is",
        ),
        (
            lambda w: job(w)["steps"].remove(token(w)),
            "review mints 0 App tokens",
        ),
        (
            lambda w: job(w)["steps"].append(job(w)["steps"].pop(job(w)["steps"].index(token(w)))),
            "minted after the action runs",
        ),
        (lambda w: job(w).pop("permissions"), "review's GITHUB_TOKEN permissions"),
        (lambda w: job(w).update({"environment": "plan-pr"}), "it needs none"),
        (lambda w: w.pop("concurrency"), "one run per pull request"),
        (lambda w: w["concurrency"].update({"cancel-in-progress": False}), "cancelling the last"),
        (lambda w: job(w).pop("timeout-minutes"), "no timeout-minutes"),
        (lambda w: w["jobs"].update({"other": {}}), "not review only"),
        (
            lambda w: job(w)["steps"].append({"run": "git push"}),
            "runs a command of its own",
        ),
        (
            lambda w: job(w)["steps"][0].update({"uses": "actions/checkout@v7"}),
            "isn't pinned",
        ),
        (
            lambda w: job(w)["steps"][-1].update({"uses": f"{ACTION}@v1"}),
            "isn't pinned",
        ),
        (lambda w: action(w).pop("github_token"), "github_token"),
        (
            lambda w: action(w).update({"github_token": "${{ secrets.SOME_PAT }}"}),
            "github_token",
        ),
        (
            lambda w: action(w).update({"github_token": "${{ secrets.GITHUB_TOKEN }}"}),
            "github_token",
        ),
        (lambda w: action(w).pop("claude_code_oauth_token"), "claude_code_oauth_token"),
        (
            lambda w: action(w).update({"anthropic_api_key": "${{ secrets.ANTHROPIC_API_KEY }}"}),
            "given anthropic_api_key",
        ),
        (lambda w: action(w).update({"allowed_bots": "*"}), "given allowed_bots"),
        (
            lambda w: action(w).update({"allowed_non_write_users": "*"}),
            "given allowed_non_write_users",
        ),
        (
            lambda w: action(w).update({"additional_permissions": "contents: write"}),
            "given additional_permissions",
        ),
        (lambda w: action(w).update({"show_full_output": "true"}), "given show_full_output"),
        (lambda w: action(w).pop("prompt"), "no prompt"),
        (lambda w: tools(w, "Bash(gh pr view:*),Edit"), "add ['Edit']"),
        (lambda w: tools(w, "Bash(gh pr view:*),Write"), "add ['Write']"),
        (lambda w: tools(w, "Bash(gh pr view:*),Bash(git push:*)"), "add ['Bash(git push:*)']"),
        (
            lambda w: tools(w, "Bash(gh pr view:*),Bash(gh pr review:*)"),
            "add ['Bash(gh pr review:*)']",
        ),
        (lambda w: tools(w, "Bash(gh:*)"), "add ['Bash(gh:*)']"),
        (lambda w: tools(w, 'Bash(gh pr view:*)" --dangerously-skip-permissions "'), "besides"),
        (
            lambda w: action(w).update(
                {"claude_args": re.sub(r"--max-turns \d+", "", str(action(w)["claude_args"]))}
            ),
            "no --max-turns",
        ),
        (lambda w: sources(w, ""), "from None"),
        (lambda w: sources(w, "--setting-sources user,project"), "from 'user,project'"),
        (lambda w: sources(w, "--setting-sources project"), "from 'project'"),
    ],
)
def test_each_way_the_workflow_can_go_wrong_is_named(change: Any, named: str) -> None:  # noqa: ANN401
    workflow = copy.deepcopy(review())
    change(workflow)
    assert any(named in problem for problem in problems(workflow)), problems(workflow)
