"""claude-review.yml reviews each member's pull request and can't change the repository (spec:
pr-review; claude-pr-review design D1 to D4, D7, D8; review-denials-and-guide design D1 to D4;
review-findings-by-severity design D1 to D4).

GitHub evaluates the workflow, so these tests pin what it's given: when it runs and what it
skips, what its token may do, which credentials reach the action, which tools Claude has, what
it checks out, and its three steps of its own: one reads the review conversations before Claude
starts, one resolves and re-tiers what Claude names, and one names the tool calls Claude was
refused."""

import ast
import copy
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO

import guard

REVIEW = REPO / ".github" / "workflows" / "claude-review.yml"
FIXTURES = Path(__file__).parent / "fixtures"
# Real execution files, captured with `claude -p --output-format stream-json` and stripped of the
# owner's local setup; the result messages are as captured (review-denials-and-guide design D3).
DENIED = FIXTURES / "claude-execution-denied.json"
CLEAN = FIXTURES / "claude-execution-clean.json"
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
    # Inside the checkout only: unscoped, Read reaches /proc/self/environ, which holds the Claude
    # token, and a misled review could post it (probed: Read outside ./ is denied only when scoped).
    "Read(./**)",
    "Grep(./**)",
    "Glob(./**)",
}
# Settings from the user scope only, which the action writes itself: none from the repository, so
# the guard's Claude Code hooks in .claude/settings.json don't load. They're written for an agent
# in the owner's terminal, and they grant gh writes the review mustn't have (owner, 2026-10-26;
# design D8).
SETTING_SOURCES = "user"
PINNED = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")
# The org's contributing guide, checked out where Read(./**) reaches it, keeping no token: the
# review has no tool that fetches a URL (review-denials-and-guide design D4).
GUIDE = {
    "repository": "troupe-run/.github",
    "ref": "main",
    "path": ".org-guide",
    "sparse-checkout": "CONTRIBUTING.md",
    "sparse-checkout-cone-mode": False,
    "fetch-depth": 1,
    "persist-credentials": False,
}
GUIDE_URL = "https://github.com/troupe-run/.github/blob/main/CONTRIBUTING.md"
# The one step that runs a command: it names each tool call Claude was refused, from the action's
# execution file, and shows nothing else of the session (design D1, D2). Its script is pinned by
# hash, so changing it changes this test in the same diff.
REPORT_NAME = "Name the tool calls Claude was refused"
REPORT = {
    "if": "${{ !cancelled() }}",
    "continue-on-error": True,
    "shell": "python3 {0}",
    "env": {"EXECUTION_FILE": "${{ steps.review.outputs.execution_file }}"},
}
REPORT_SHA256 = "0226ac402c3987ad33791bf8b0176f07585e3f5059fab9541c473e56ccf9fcf6"
# The review App's token, the only one the two conversation steps hold (design D3, D4).
STEP_ENV = {
    "GH_TOKEN": "${{ steps.app-token.outputs.token }}",
    "REPOSITORY": "${{ github.repository }}",
    "NUMBER": "${{ github.event.pull_request.number }}",
}
# Before Claude: the pull request's review conversations, for Claude and for the resolving step.
SNAPSHOT_NAME = "Read the pull request's review conversations"
SNAPSHOT = {"shell": "python3 {0}", "env": STEP_ENV}
SNAPSHOT_SHA256 = "881c6b51fbc892399d33e02bcfc14f93611d0f293eab577dd415b1bd6e5757c9"
# After Claude, in a job of its own, only when the review succeeded: resolve and re-tier what Claude
# names, checked against conversations read again in that job (design D4, D4a).
RESOLVER_NAME = "Resolve and re-tier what Claude named"
RESOLVER = {
    "shell": "python3 {0}",
    "env": {**STEP_ENV, "STRUCTURED_OUTPUT": "${{ needs.review.outputs.structured_output }}"},
}
REVIEW_OUTPUTS = {"structured_output": "${{ steps.review.outputs.structured_output }}"}
# The resolving job: after the review, only when it succeeded, with nothing checked out and no
# Claude, and the one token that can write contents, which resolving a conversation needs (D4a).
RESOLVE_NEEDS = "review"
RESOLVE_IF = "needs.review.result == 'success'"
RESOLVE_TOKEN_INPUTS = {
    **TOKEN_INPUTS,
    "permission-contents": "write",
}
RESOLVER_SHA256 = "0edb8face669593a9f3bff916607df894a1eddb85579f0dd4604c9275ba68269"
OWN_STEPS = {REPORT_NAME, SNAPSHOT_NAME}
# What Claude returns, and all the resolving step reads from it (design D4).
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["resolve", "retier"],
    "properties": {
        "resolve": {"type": "array", "items": {"type": "string"}},
        "retier": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["thread", "tier", "title", "reason"],
                "properties": {
                    "thread": {"type": "string"},
                    "tier": {"type": "string", "enum": list(guard.REVIEW_TIERS)},
                    "title": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        },
    },
}


def review() -> dict[str, Any]:
    loaded = yaml.safe_load(REVIEW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    # YAML 1.1 reads the key `on` as true.
    loaded["on"] = loaded.pop(True, loaded.get("on"))
    return loaded


def claude_args(inputs: dict[str, Any]) -> tuple[set[str], str | None, list[str]]:
    """The allowed tools, the setting sources, and every other flag, in the action's claude_args.
    The --json-schema is read by json_schema."""
    words = shlex.split(str(inputs.get("claude_args", "")))
    tools: set[str] = set()
    sources = None
    others = []
    i = 0
    while i < len(words):
        if words[i] == "--json-schema" and i + 1 < len(words):
            i += 2
        elif words[i] == "--allowedTools" and i + 1 < len(words):
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


def json_schema(inputs: dict[str, Any]) -> object:
    """The structured output's schema in claude_args, or None."""
    words = shlex.split(str(inputs.get("claude_args", "")))
    if "--json-schema" not in words or words.index("--json-schema") + 1 >= len(words):
        return None
    try:
        return json.loads(words[words.index("--json-schema") + 1])
    except ValueError:
        return None


def own_step_problems(
    step: dict[str, Any], expected: dict[str, Any], sha256: str, what: str
) -> list[str]:
    found = []
    given = {key: step.get(key) for key in expected}
    if given != expected:
        found.append(f"{what} is given {given!r}, not {expected!r}")
    others = sorted(set(step) - {*expected, "name", "run"})
    if others:
        found.append(f"{what} also has {others}")
    script = str(step["run"])
    if "${{" in script:
        found.append(f"{what}'s script interpolates an expression; use its env")
    if hashlib.sha256(script.encode()).hexdigest() != sha256:
        found.append(f"{what}'s script isn't the one this test pins")
    return found


def resolve_job_problems(job: dict[str, Any]) -> list[str]:
    """The resolving job: after the review, on its success only, minting the write token, reading
    the conversations again, then resolving; no checkout, no Claude, nothing else (design D4a)."""
    found = []
    if job.get("needs") != RESOLVE_NEEDS:
        found.append(f"resolve needs {job.get('needs')!r}, not {RESOLVE_NEEDS!r}")
    if job.get("if") != RESOLVE_IF:
        found.append(f"resolve runs when {job.get('if')!r}, not {RESOLVE_IF!r}")
    if job.get("permissions") != PERMISSIONS:
        found.append(
            f"resolve's GITHUB_TOKEN permissions are {job.get('permissions')!r}, "
            f"not {PERMISSIONS!r}"
        )
    if "environment" in job:
        found.append(f"resolve runs in environment {job['environment']!r}; it needs none")
    if not isinstance(job.get("timeout-minutes"), int):
        found.append("resolve has no timeout-minutes")
    steps = job.get("steps") or []
    shape = [
        "token"
        if str(s.get("uses", "")).startswith(f"{MINTER}@")
        else s.get("name") or s.get("uses")
        for s in steps
    ]
    if shape != ["token", SNAPSHOT_NAME, RESOLVER_NAME]:
        return [*found, f"resolve's steps are {shape!r}, not the token, {SNAPSHOT_NAME!r} and "
                f"{RESOLVER_NAME!r}, in that order"]  # fmt: skip
    minted, read, resolving = steps
    if not PINNED.match(str(minted.get("uses"))):
        found.append(f"{minted.get('uses')!r} isn't pinned to a full commit SHA")
    if minted.get("id") != "app-token":
        found.append(f"resolve's token step's id is {minted.get('id')!r}, not app-token")
    given = dict(minted.get("with") or {})
    client_id = str(given.pop("client-id", ""))
    if not REVIEW_APP_CLIENT_ID.match(client_id):
        found.append(f"resolve's client ID is {client_id!r}, not one written here")
    if given != RESOLVE_TOKEN_INPUTS:
        found.append(f"resolve's token is minted with {given!r}, not {RESOLVE_TOKEN_INPUTS!r}")
    found += own_step_problems(read, SNAPSHOT, SNAPSHOT_SHA256, f"resolve's {SNAPSHOT_NAME!r}")
    found += own_step_problems(resolving, RESOLVER, RESOLVER_SHA256, repr(RESOLVER_NAME))
    return found


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
    if set(jobs) != {"review", "resolve"}:
        return [*found, f"its jobs are {sorted(jobs)}, not review and resolve"]
    job = jobs["review"]
    found += resolve_job_problems(jobs["resolve"])
    if job.get("outputs") != REVIEW_OUTPUTS:
        found.append(f"review's outputs are {job.get('outputs')!r}, not {REVIEW_OUTPUTS!r}")

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
    reports = []
    for step in steps:
        uses = step.get("uses")
        if uses is not None and not PINNED.match(str(uses)):
            found.append(f"{uses!r} isn't pinned to a full commit SHA")
        if "run" in step and step.get("name") == REPORT_NAME:
            reports.append(step)
        elif "run" in step and step.get("name") not in OWN_STEPS:
            found.append(
                f"review runs a command of its own ({step['run']!r}); only the action, the "
                "conversation steps and the denials report run"
            )
    checkouts = [s for s in steps if str(s.get("uses", "")).startswith("actions/checkout@")]
    for step in checkouts:
        if (step.get("with") or {}).get("persist-credentials") is not False:
            found.append(
                "the checkout leaves its token in .git/config (persist-credentials isn't false)"
            )
    if len(checkouts) != 2:
        found.append(
            f"review checks out {len(checkouts)} times, not the pull request and the guide"
        )
    else:
        own, guide = (dict(step.get("with") or {}) for step in checkouts)
        if "repository" in own:
            found.append(f"the first checkout is {own['repository']!r}, not the pull request's own")
        if guide != GUIDE:
            found.append(f"the guide's checkout is {guide!r}, not {GUIDE!r}")
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

    if actions[0].get("id") != "review":
        found.append(f"the action's step id is {actions[0].get('id')!r}, not review")
    if len(reports) != 1:
        found.append(f"review has {len(reports)} denials reports, not one")
    for report in reports:
        given = {key: report.get(key) for key in REPORT}
        if given != REPORT:
            found.append(f"the denials report is given {given!r}, not {REPORT!r}")
        others = sorted(set(report) - {*REPORT, "name", "run"})
        if others:
            found.append(f"the denials report also has {others}")
        script = str(report["run"])
        if "${{" in script:
            found.append("the denials report's script interpolates an expression; use its env")
        if hashlib.sha256(script.encode()).hexdigest() != REPORT_SHA256:
            found.append("the denials report's script isn't the one this test pins (REPORT_SHA256)")
        if steps.index(report) < steps.index(actions[0]):
            found.append("the denials report runs before the action")
    named = [step for step in steps if step.get("name") == SNAPSHOT_NAME and "run" in step]
    if len(named) != 1:
        found.append(f"review has {len(named)} steps named {SNAPSHOT_NAME!r}, not one")
    else:
        found += own_step_problems(named[0], SNAPSHOT, SNAPSHOT_SHA256, repr(SNAPSHOT_NAME))
        at = steps.index(named[0])
        if not (tokens and steps.index(tokens[0]) < at < steps.index(actions[0])):
            found.append(f"{SNAPSHOT_NAME!r} doesn't run between minting the token and the action")
    if json_schema(inputs) != SCHEMA:
        found.append("Claude's structured output isn't the schema this test pins (SCHEMA)")

    prompt = str(inputs.get("prompt", ""))
    for path in (".org-guide/CONTRIBUTING.md", "org-profile/CONTRIBUTING.md"):
        if path not in prompt:
            found.append(f"the prompt doesn't name {path}")
    if GUIDE_URL in prompt:
        found.append("the prompt names the guide by URL, which the review has no tool to fetch")

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
            f"claude_args has {others!r} besides --allowedTools, --max-turns, --setting-sources "
            "and --json-schema"
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


def action_step(w: dict[str, Any]) -> dict[str, Any]:
    step = next(s for s in job(w)["steps"] if str(s.get("uses", "")).startswith(ACTION))
    return step  # type: ignore[no-any-return]


def action(w: dict[str, Any]) -> dict[str, Any]:
    return action_step(w)["with"]  # type: ignore[no-any-return]


def report(w: dict[str, Any]) -> dict[str, Any]:
    step = next(s for s in job(w)["steps"] if s.get("name") == REPORT_NAME)
    return step  # type: ignore[no-any-return]


def guide(w: dict[str, Any]) -> dict[str, Any]:
    step = next(s for s in job(w)["steps"] if (s.get("with") or {}).get("repository"))
    return step["with"]  # type: ignore[no-any-return]


def move(w: dict[str, Any], step: dict[str, Any], to: int) -> None:
    steps = job(w)["steps"]
    steps.insert(to, steps.pop(steps.index(step)))


def snapshot(w: dict[str, Any]) -> dict[str, Any]:
    step = next(s for s in job(w)["steps"] if s.get("name") == SNAPSHOT_NAME)
    return step  # type: ignore[no-any-return]


def resolve_job(w: dict[str, Any]) -> dict[str, Any]:
    return w["jobs"]["resolve"]  # type: ignore[no-any-return]


def resolver(w: dict[str, Any]) -> dict[str, Any]:
    step = next(s for s in resolve_job(w)["steps"] if s.get("name") == RESOLVER_NAME)
    return step  # type: ignore[no-any-return]


def resolve_token(w: dict[str, Any]) -> dict[str, Any]:
    step = resolve_job(w)["steps"][0]
    return step  # type: ignore[no-any-return]


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
        (lambda w: w["jobs"].update({"other": {}}), "not review and resolve"),
        (
            lambda w: job(w)["steps"].append({"run": "git push"}),
            "runs a command of its own",
        ),
        (
            lambda w: job(w)["steps"][0].update({"uses": "actions/checkout@v7"}),
            "isn't pinned",
        ),
        (lambda w: action_step(w).update({"uses": f"{ACTION}@v1"}), "isn't pinned"),
        (lambda w: action_step(w).update({"id": "claude"}), "not review"),
        (lambda w: job(w)["steps"].remove(report(w)), "0 denials reports"),
        (
            lambda w: job(w)["steps"].append({**report(w), "run": "print('x')"}),
            "2 denials reports",
        ),
        (
            lambda w: report(w).update(
                {"run": str(report(w)["run"]) + "print(open('x').read())\n"}
            ),
            "isn't the one this test pins",
        ),
        (
            lambda w: report(w).update(
                {
                    "run": str(report(w)["run"]).replace(
                        'os.environ.get("EXECUTION_FILE", "")',
                        '"${{ steps.review.outputs.execution_file }}"',
                    )
                }
            ),
            "interpolates an expression",
        ),
        (lambda w: report(w).pop("continue-on-error"), "the denials report is given"),
        (lambda w: report(w).update({"if": "${{ always() }}"}), "the denials report is given"),
        (lambda w: report(w).update({"shell": "bash"}), "the denials report is given"),
        (
            lambda w: report(w)["env"].update({"TOKEN": "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}"}),
            "the denials report is given",
        ),
        (
            lambda w: report(w).update({"working-directory": ".org-guide"}),
            "also has ['working-directory']",
        ),
        (lambda w: move(w, report(w), 0), "runs before the action"),
        (lambda w: action(w).update({"display_report": "true"}), "given display_report"),
        (lambda w: guide(w).update({"persist-credentials": True}), "persist-credentials"),
        (lambda w: guide(w).update({"repository": "troupe-run/troupe"}), "the guide's checkout"),
        (lambda w: guide(w).update({"path": "../guide"}), "the guide's checkout"),
        (lambda w: guide(w).update({"path": "/tmp/guide"}), "the guide's checkout"),  # noqa: S108
        (lambda w: guide(w).pop("sparse-checkout"), "the guide's checkout"),
        (lambda w: move(w, job(w)["steps"][0], 2), "the first checkout is 'troupe-run/.github'"),
        (
            lambda w: job(w)["steps"].insert(0, copy.deepcopy(job(w)["steps"][0])),
            "checks out 3 times",
        ),
        (lambda w: tools(w, "Bash(gh pr view:*),WebFetch"), "add ['WebFetch']"),
        (
            lambda w: action(w).update(
                {
                    "prompt": str(action(w)["prompt"]).replace(
                        ".org-guide/CONTRIBUTING.md", GUIDE_URL
                    )
                }
            ),
            "names the guide by URL",
        ),
        (
            lambda w: action(w).update(
                {"prompt": str(action(w)["prompt"]).replace("org-profile/CONTRIBUTING.md", "")}
            ),
            "doesn't name org-profile/CONTRIBUTING.md",
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
        (lambda w: tools(w, "Bash(gh pr view:*),Read"), "add ['Read']"),
        (
            lambda w: action(w).update(
                {"claude_args": str(action(w)["claude_args"]).replace("Grep(./**)", "Grep")}
            ),
            "add ['Grep']",
        ),
        (
            lambda w: job(w)["steps"][0]["with"].pop("persist-credentials"),
            "persist-credentials isn't false",
        ),
        (
            lambda w: job(w)["steps"][0]["with"].update({"persist-credentials": True}),
            "persist-credentials isn't false",
        ),
        (lambda w: tools(w, 'Bash(gh pr view:*)" --dangerously-skip-permissions "'), "besides"),
        (
            lambda w: action(w).update(
                {"claude_args": re.sub(r"--max-turns \d+", "", str(action(w)["claude_args"]))}
            ),
            "no --max-turns",
        ),
        (lambda w: job(w)["steps"].remove(snapshot(w)), '0 steps named "Read the pull'),
        (lambda w: resolve_job(w)["steps"].remove(resolver(w)), "resolve's steps are"),
        (lambda w: w["jobs"].pop("resolve"), "not review and resolve"),
        (lambda w: resolve_job(w).pop("needs"), "resolve needs None"),
        (lambda w: resolve_job(w).update({"if": "always()"}), "resolve runs when 'always()'"),
        (
            lambda w: resolve_job(w)["permissions"].update({"contents": "write"}),
            "resolve's GITHUB_TOKEN permissions",
        ),
        (
            lambda w: resolve_job(w)["steps"].insert(0, copy.deepcopy(job(w)["steps"][0])),
            "resolve's steps are",
        ),
        (
            lambda w: resolve_job(w)["steps"].append(copy.deepcopy(action_step(w))),
            "resolve's steps are",
        ),
        (
            lambda w: resolve_token(w)["with"].update({"permission-administration": "write"}),
            "resolve's token is minted with",
        ),
        (
            lambda w: resolve_token(w)["with"].update({"permission-contents": "read"}),
            "resolve's token is minted with",
        ),
        (lambda w: job(w).pop("outputs"), "review's outputs are None"),
        (lambda w: job(w)["steps"].append(copy.deepcopy(resolver(w))), "runs a command of its own"),
        (lambda w: move(w, snapshot(w), len(job(w)["steps"])), "doesn't run between minting"),
        (lambda w: move(w, snapshot(w), 0), "doesn't run between minting"),
        (
            lambda w: resolve_job(w)["steps"].insert(
                1, resolve_job(w)["steps"].pop(resolve_job(w)["steps"].index(resolver(w)))
            ),
            "resolve's steps are",
        ),
        (
            lambda w: resolver(w)["env"].update({"GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}"}),
            "'Resolve and re-tier what Claude named' is given",
        ),
        (
            lambda w: snapshot(w)["env"].update(
                {"CLAUDE": "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}"}
            ),
            'review conversations" is given',
        ),
        (
            lambda w: resolver(w).update({"if": "${{ always() }}"}),
            "'Resolve and re-tier what Claude named' also has ['if']",
        ),
        (
            lambda w: resolver(w).update({"continue-on-error": True}),
            "also has ['continue-on-error']",
        ),
        (
            lambda w: resolver(w).update(
                {"run": str(resolver(w)["run"]).replace('if current != "must-fix":', "if False:")}
            ),
            "'Resolve and re-tier what Claude named''s script isn't the one this test pins",
        ),
        (
            lambda w: resolver(w).update(
                {
                    "run": str(resolver(w)["run"]).replace(
                        'os.environ.get("STRUCTURED_OUTPUT", "")',
                        "'${{ steps.review.outputs.structured_output }}'",
                    )
                }
            ),
            "interpolates an expression",
        ),
        (
            lambda w: snapshot(w).update({"run": str(snapshot(w)["run"]) + "print(1)\n"}),
            "review conversations\"'s script isn't the one this test pins",
        ),
        (lambda w: tools(w, "Bash(gh pr view:*),Bash(gh api:*)"), "add ['Bash(gh api:*)']"),
        (
            lambda w: action(w).update(
                {"claude_args": re.sub(r"--json-schema '[^']*'", "", str(action(w)["claude_args"]))}
            ),
            "isn't the schema this test pins",
        ),
        (
            lambda w: action(w).update(
                {
                    "claude_args": str(action(w)["claude_args"]).replace(
                        '"decision"]', '"decision","owner"]'
                    )
                }
            ),
            "isn't the schema this test pins",
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


def run_report(tmp_path: Path, content: str | None, set_path: bool = True) -> tuple[int, str]:
    """Run the workflow's own denials report, as the runner would, against an execution file."""
    script = tmp_path / "report.py"
    script.write_text(str(report(review())["run"]), encoding="utf-8")
    env = {key: value for key, value in os.environ.items() if key != "EXECUTION_FILE"}
    execution = tmp_path / "claude-execution-output.json"
    if content is not None:
        execution.write_text(content, encoding="utf-8")
    if set_path:
        env["EXECUTION_FILE"] = str(execution)
    done = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, env=env, check=False
    )
    return done.returncode, done.stdout


def test_a_refused_call_is_named_in_one_warning(tmp_path: Path) -> None:
    code, out = run_report(tmp_path, DENIED.read_text(encoding="utf-8"))
    assert code == 0
    assert out.splitlines() == [
        "::warning title=Claude was refused a tool call::WebFetch "
        + json.dumps(
            {
                "prompt": "What is the first heading in this document? Quote it exactly.",
                "url": GUIDE_URL,
            },
            sort_keys=True,
        )
    ]


def test_a_review_with_no_denial_says_so_and_warns_of_nothing(tmp_path: Path) -> None:
    code, out = run_report(tmp_path, CLEAN.read_text(encoding="utf-8"))
    assert (code, out) == (0, "No tool call was refused.\n")


def test_the_session_s_messages_are_not_shown(tmp_path: Path) -> None:
    _, out = run_report(tmp_path, DENIED.read_text(encoding="utf-8"))
    # The fixture's own reply and the denial's message are in the file, never in the log.
    assert "couldn't fetch it" not in out
    assert "haven't granted it" not in out


@pytest.mark.parametrize("set_path", [False, True])
def test_no_execution_file_warns_that_the_denials_are_unknown(
    tmp_path: Path, set_path: bool
) -> None:
    code, out = run_report(tmp_path, None, set_path=set_path)
    assert code == 0
    assert out.startswith(
        "::warning title=Claude's denials are unknown::The action left no execution"
    )


@pytest.mark.parametrize(
    ("content", "named"),
    [
        ("not json", "isn't readable JSON"),
        ('{"type": "result", "permission_denials": []}', "isn't a list of messages"),
        ('[{"type": "assistant"}]', "with a result message"),
        ('[{"type": "result", "permission_denials": 3}]', "aren't each a tool call"),
        ('[{"type": "result", "permission_denials": [{"tool_input": {}}]}]', "each a tool call"),
    ],
)
def test_a_malformed_execution_file_is_named_and_fails_the_step(
    tmp_path: Path, content: str, named: str
) -> None:
    code, out = run_report(tmp_path, content)
    assert code == 1
    assert out.startswith("::warning title=Claude's denials are unknown::")
    assert named in out
    assert "No tool call was refused" not in out


def test_an_input_that_holds_a_workflow_command_stays_inside_one_warning(tmp_path: Path) -> None:
    messages = json.loads(DENIED.read_text(encoding="utf-8"))
    result = next(m for m in messages if m["type"] == "result")
    hostile = "a\n::error::x\r%0A" + "y" * 1000
    result["permission_denials"][0]["tool_input"] = {"command": hostile}
    code, out = run_report(tmp_path, json.dumps(messages))
    assert code == 0
    lines = out.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("::warning title=Claude was refused a tool call::WebFetch ")
    message = lines[0].split("::", 2)[2]
    # The runner unescapes a message as the toolkit escaped it; the input never begins a line.
    shown = message.replace("%0A", "\n").replace("%0D", "\r").replace("%25", "%")
    expected = "WebFetch " + json.dumps({"command": hostile}, sort_keys=True)
    assert shown == expected[:300] + "..."
    assert "\n" not in shown
    assert "\r" not in shown
    assert "%250A" in message


# The resolving step's copy of the guard's tier parser (design D1)


def resolver_constants() -> tuple[re.Pattern[str], object]:
    """The LABEL and BOT the resolving step's script defines, read without running it."""
    tree = ast.parse(str(resolver(review())["run"]))
    found: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name == "LABEL" and isinstance(node.value, ast.Call):
                found[name] = re.compile(ast.literal_eval(node.value.args[0]))
            elif name == "BOT":
                found[name] = ast.literal_eval(node.value)
    return found["LABEL"], found["BOT"]


FIRST_LINES = [
    "**must-fix** · a", "**nit** · a", "**decision** · a", "**critical** · a", "**minor** · a",
    "**must-fix · nit** · a", "**must-fix**  ·  a", "**must-fix** - a", "**must-fix** ·",
    "**Must-Fix** · a", " **nit** · a", "nit · a", "",
]  # fmt: skip


@pytest.mark.parametrize("line", FIRST_LINES)
def test_the_resolving_step_reads_a_label_as_the_guard_does(line: str) -> None:
    label, bot = resolver_constants()
    match = label.fullmatch(line)
    assert (match.group(1) if match else None) == guard.review_tier(line)
    assert bot == guard.REVIEW_BOT


def test_the_prompt_s_examples_are_labels_of_each_tier() -> None:
    prompt = str(action(review())["prompt"])
    examples = [line.strip() for line in prompt.splitlines() if line.strip().startswith("**")]
    assert examples
    assert [guard.review_tier(line) for line in examples] == list(guard.REVIEW_TIERS)


# The two steps, run as the runner would, with a gh on PATH that answers from a script

GH_STUB = """\
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "calls.jsonl"), "a", encoding="utf-8") as calls:
    calls.write(json.dumps(sys.argv[1:]) + "\\n")
with open(os.path.join(here, "answers.json"), encoding="utf-8") as file:
    answers = json.load(file)
count = sum(1 for _ in open(os.path.join(here, "calls.jsonl"), encoding="utf-8"))
fail = answers.get("fail_when", "")
if fail and any(fail in arg for arg in sys.argv[1:]):
    sys.exit(1)
pages = answers.get("pages", [])
sys.stdout.write(json.dumps(pages[count - 1]) if count <= len(pages) else "{}")
sys.exit(answers.get("status", 0))
"""


def stub_gh(directory: Path, answers: dict[str, Any]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "stub.py").write_text(GH_STUB, encoding="utf-8")
    (directory / "answers.json").write_text(json.dumps(answers), encoding="utf-8")
    if os.name == "nt":
        (directory / "gh.cmd").write_text(
            f'@"{sys.executable}" "{directory / "stub.py"}" %*\r\n', encoding="utf-8"
        )
    else:
        wrapper = directory / "gh"
        wrapper.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{directory / "stub.py"}" "$@"\n',
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
    return directory


def gh_calls(directory: Path) -> list[list[str]]:
    path = directory / "calls.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def run_step(
    step: dict[str, Any], tmp_path: Path, bin_dir: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run one of the workflow's own steps in a workspace, with RUNNER_TEMP and the step's env."""
    workspace = tmp_path / "workspace"
    runner_temp = tmp_path / "runner-temp"
    workspace.mkdir(exist_ok=True)
    runner_temp.mkdir(exist_ok=True)
    script = tmp_path / "step.py"
    script.write_text(str(step["run"]), encoding="utf-8")
    full = {key: value for key, value in os.environ.items() if not key.startswith("GH_")}
    full |= {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(runner_temp),
        "GH_TOKEN": "app-token",
        "REPOSITORY": "troupe-run/infrastructure",
        "NUMBER": "7",
        **env,
    }
    return subprocess.run(
        [sys.executable, str(script)], cwd=workspace, capture_output=True, text=True,
        encoding="utf-8", env=full, check=False,
    )  # fmt: skip


BOT_AUTHOR = {"__typename": "Bot", "login": "troupe-run-review"}
PERSON = {"__typename": "User", "login": "martin-at-hpsgd"}


def conversation(ident: str, opener: dict[str, str], *bodies: tuple[dict[str, str], str]) -> Any:  # noqa: ANN401
    return {
        "id": ident, "isResolved": False, "isOutdated": False, "path": "scripts/guard.py",
        "line": 10, "opened": {"nodes": [{"databaseId": 100, "author": opener}]},
        "comments": {"nodes": [
            {"databaseId": 100 + i, "author": author, "body": body}
            for i, (author, body) in enumerate(bodies)
        ]},
    }  # fmt: skip


def page(nodes: list[Any], more: bool, cursor: str | None) -> dict[str, Any]:
    threads = {"pageInfo": {"hasNextPage": more, "endCursor": cursor}, "nodes": nodes}
    return {"data": {"repository": {"pullRequest": {"reviewThreads": threads}}}}


def test_the_snapshot_reads_every_page_into_the_workspace_and_runner_temp(tmp_path: Path) -> None:
    one = conversation("PRRT_1", BOT_AUTHOR, (BOT_AUTHOR, "**nit** · a"))
    two = conversation("PRRT_2", PERSON, (PERSON, "a person's comment"))
    bin_dir = stub_gh(
        tmp_path / "bin", {"pages": [page([one], True, "C1"), page([two], False, None)]}
    )
    done = run_step(snapshot(review()), tmp_path, bin_dir, {})
    assert done.returncode == 0, done.stdout + done.stderr
    assert "2 review conversation(s) read." in done.stdout
    for path in (tmp_path / "workspace" / ".review-threads.json",
                 tmp_path / "runner-temp" / "review-threads.json"):  # fmt: skip
        assert [t["id"] for t in json.loads(path.read_text(encoding="utf-8"))] == [
            "PRRT_1",
            "PRRT_2",
        ]
    calls = gh_calls(bin_dir)
    assert len(calls) == 2
    assert all(call[:2] == ["api", "graphql"] for call in calls)
    assert "cursor=C1" not in calls[0]
    assert "cursor=C1" in calls[1]
    assert {"owner=troupe-run", "name=infrastructure", "number=7"} <= set(calls[0])
    query = next(arg for arg in calls[0] if arg.startswith("query=")).partition("=")[2]
    assert guard.graphql_mutations(query) == []


@pytest.mark.parametrize(
    "answers", [{"status": 1}, {"pages": ["not a page"]}, {"pages": [{"data": None}]}]
)
def test_a_snapshot_that_can_t_be_read_fails_the_run(
    tmp_path: Path, answers: dict[str, Any]
) -> None:
    done = run_step(snapshot(review()), tmp_path, stub_gh(tmp_path / "bin", answers), {})
    assert done.returncode == 1
    assert done.stdout.startswith("::error title=Review conversations unread::")
    assert not (tmp_path / "runner-temp" / "review-threads.json").exists()


SNAPSHOT_THREADS = [
    conversation("PRRT_mustfix", BOT_AUTHOR, (BOT_AUTHOR, "**must-fix** · a bug")),
    # First posted as a nit, re-tiered by the review.
    conversation("PRRT_upgraded", BOT_AUTHOR, (BOT_AUTHOR, "**nit** · a"),
                 (BOT_AUTHOR, "**must-fix** · it matters")),
    conversation("PRRT_downgraded", BOT_AUTHOR, (BOT_AUTHOR, "**must-fix** · a"),
                 (BOT_AUTHOR, "**nit** · wording only")),
    conversation("PRRT_nit", BOT_AUTHOR, (BOT_AUTHOR, "**nit** · stale path")),
    conversation("PRRT_decision", BOT_AUTHOR, (BOT_AUTHOR, "**decision** · a choice")),
    conversation("PRRT_unlabelled", BOT_AUTHOR, (BOT_AUTHOR, "An earlier finding.")),
    conversation("PRRT_person", PERSON, (PERSON, "**must-fix** · a person's")),
    conversation("PRRT_selflabel", BOT_AUTHOR, (BOT_AUTHOR, "**nit** · a"),
                 (PERSON, "**must-fix** · the author says so")),
    {**conversation("PRRT_done", BOT_AUTHOR, (BOT_AUTHOR, "**must-fix** · a")), "isResolved": True},
]  # fmt: skip


def resolve_run(
    tmp_path: Path, answer: object, fail_when: str = ""
) -> tuple[subprocess.CompletedProcess[str], list[list[str]]]:
    temp = tmp_path / "runner-temp"
    temp.mkdir(parents=True, exist_ok=True)
    (temp / "review-threads.json").write_text(json.dumps(SNAPSHOT_THREADS), encoding="utf-8")
    bin_dir = stub_gh(tmp_path / "bin", {"fail_when": fail_when})
    output = answer if isinstance(answer, str) else json.dumps(answer)
    done = run_step(resolver(review()), tmp_path, bin_dir, {"STRUCTURED_OUTPUT": output})
    return done, gh_calls(bin_dir)


def resolved(calls: list[list[str]]) -> list[str]:
    return [arg[3:] for call in calls if "graphql" in call for arg in call if arg.startswith("id=")]


def test_only_the_review_s_open_must_fixes_are_resolved(tmp_path: Path) -> None:
    named = [
        "PRRT_mustfix", "PRRT_upgraded", "PRRT_downgraded", "PRRT_nit", "PRRT_decision",
        "PRRT_unlabelled", "PRRT_person", "PRRT_selflabel", "PRRT_done", "PRRT_elsewhere",
    ]  # fmt: skip
    done, calls = resolve_run(tmp_path, {"resolve": named, "retier": []})
    assert done.returncode == 0, done.stdout + done.stderr
    assert resolved(calls) == ["PRRT_mustfix", "PRRT_upgraded"]
    for call in calls:
        query = next(arg for arg in call if arg.startswith("query=")).partition("=")[2]
        assert guard.graphql_mutations(query) == ["resolveReviewThread"]
    warnings = [line for line in done.stdout.splitlines() if line.startswith("::warning")]
    assert len(warnings) == len(named) - 2
    for ident in named[2:]:
        assert any(ident in line for line in warnings), ident


def test_a_resolve_that_fails_warns_and_the_rest_go_ahead(tmp_path: Path) -> None:
    answer = {"resolve": ["PRRT_mustfix", "PRRT_upgraded"], "retier": []}
    done, calls = resolve_run(tmp_path, answer, fail_when="id=PRRT_mustfix")
    assert done.returncode == 0
    assert resolved(calls) == ["PRRT_mustfix", "PRRT_upgraded"]
    assert "PRRT_mustfix couldn't be resolved." in done.stdout
    assert "PRRT_upgraded: resolved." in done.stdout


def test_a_re_tier_is_a_labelled_reply_from_the_review(tmp_path: Path) -> None:
    answer = {"resolve": [], "retier": [
        {"thread": "PRRT_mustfix", "tier": "decision", "title": "trust the\nruleset?",
         "reason": "Both are defensible."},
    ]}  # fmt: skip
    done, calls = resolve_run(tmp_path, answer)
    assert done.returncode == 0, done.stdout + done.stderr
    assert len(calls) == 1
    call = calls[0]
    assert call[:4] == ["api", "-X", "POST", "repos/troupe-run/infrastructure/pulls/7/comments"]
    assert "in_reply_to=100" in call
    body = next(arg for arg in call if arg.startswith("body=")).partition("=")[2]
    assert body == "**decision** · trust the ruleset?\n\nBoth are defensible."
    assert guard.review_tier(body) == "decision"


@pytest.mark.parametrize(
    ("item", "said"),
    [
        ({"thread": "PRRT_person", "tier": "nit", "title": "a", "reason": "r"}, "wasn't opened"),
        ({"thread": "PRRT_done", "tier": "nit", "title": "a", "reason": "r"}, "already resolved"),
        (
            {"thread": "PRRT_gone", "tier": "nit", "title": "a", "reason": "r"},
            "isn't a conversation",
        ),
        ({"thread": "PRRT_nit", "tier": "nit", "title": "a", "reason": "r"}, "already a nit"),
        ({"thread": "PRRT_nit", "tier": "owner", "title": "a", "reason": "r"}, "needs a tier"),
        ({"thread": "PRRT_nit", "tier": "must-fix", "title": " ", "reason": "r"}, "needs a tier"),
        ({"thread": "PRRT_nit", "tier": "must-fix", "title": "a", "reason": ""}, "needs a tier"),
    ],
)
def test_a_re_tier_the_review_may_not_make_is_skipped(
    tmp_path: Path, item: dict[str, str], said: str
) -> None:
    done, calls = resolve_run(tmp_path, {"resolve": [], "retier": [item]})
    assert done.returncode == 0
    assert calls == []
    assert said in done.stdout


def test_a_conversation_named_to_resolve_and_re_tier_is_only_resolved(tmp_path: Path) -> None:
    item = {"thread": "PRRT_mustfix", "tier": "nit", "title": "a", "reason": "r"}
    done, calls = resolve_run(tmp_path, {"resolve": ["PRRT_mustfix"], "retier": [item]})
    assert resolved(calls) == ["PRRT_mustfix"]
    assert len(calls) == 1
    assert "it was only resolved" in done.stdout


@pytest.mark.parametrize(
    "answer", ["", "not json", {"resolve": "PRRT_mustfix", "retier": []}, {"retier": []}]
)
def test_an_unreadable_answer_resolves_nothing_and_fails_the_step(
    tmp_path: Path, answer: object
) -> None:
    done, calls = resolve_run(tmp_path, answer)
    assert done.returncode == 1
    assert calls == []
    assert done.stdout.startswith("::warning title=Nothing resolved::")


def test_a_hostile_id_stays_inside_one_warning(tmp_path: Path) -> None:
    done, _ = resolve_run(tmp_path, {"resolve": ["x\n::error::y"], "retier": []})
    lines = done.stdout.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("::warning title=A review conversation was left as it is::x%0A")
