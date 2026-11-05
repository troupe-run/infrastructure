"""claude-review.yml reviews each member's pull request and can't change the repository (spec:
pr-review; claude-pr-review design D1 to D4, D7, D8; review-denials-and-guide design D1 to D4;
review-findings-by-severity design D1 to D4; review-completed-check design D2 to D5;
review-covers-the-diff design D2 to D7).

GitHub evaluates the workflow, so these tests pin what it's given: when it runs and what it
skips, what its token may do, which credentials reach the action, which tools Claude has, what
it checks out, and its seven steps of its own: before Claude, one checks the model, one writes
each changed file's diff and the list of what to read, and one reads the review conversations;
after it, one names the tool calls Claude was refused, one measures what the review read, and
one resolves and re-tiers what Claude names; and the required check says whether the review of
the head completed and read the code."""

import ast
import copy
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO, clean_env, git

import guard

REVIEW = REPO / ".github" / "workflows" / "claude-review.yml"
FIXTURES = Path(__file__).parent / "fixtures"
# Real execution files, captured with `claude -p --output-format stream-json` and stripped of the
# owner's local setup; the result messages are as captured (review-denials-and-guide design D3).
DENIED = FIXTURES / "claude-execution-denied.json"
CLEAN = FIXTURES / "claude-execution-clean.json"
# Not ready_for_review: marking a draft ready doesn't review its head again (ci-once-per-commit
# design D5).
EVENTS = ["opened", "synchronize", "reopened"]
# A person's reply in a review conversation starts the review too, when it's posted
# (review-judge-reply-on-post design D2). Only `created`: an edit is judged on the next run.
COMMENT_EVENTS = ["created"]
TRIGGERS = {
    "pull_request": {"types": EVENTS},
    "pull_request_review_comment": {"types": COMMENT_EVENTS},
    # Only so the required check reports on a merge queue's commit, skipped (review-completed-check
    # design D5): every job's `if:` is false there.
    "merge_group": None,
}
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
# Bots' pull requests and forks' are skipped, not failed (design D2). A review comment goes on
# to the gate only when it's a reply, not a bot's (the review's own comments would start it
# again). Write access is the gate's step to ask: a comment's author_association can't say, since
# a member whose membership is private comments as a CONTRIBUTOR (review-judge-reply-on-post
# design D2, Probe results).
SKIP = (
    "github.event.pull_request.user.type != 'Bot' && "
    "github.event.pull_request.head.repo.full_name == github.repository && "
    "(github.event_name == 'pull_request' || "
    "(github.event.comment.in_reply_to_id != null && "
    "github.event.comment.user.type != 'Bot'))"
)
# On each job, never the workflow: a run whose review is skipped, such as the one each of the
# review's own comments starts, mustn't join the group and cancel the review that posted it
# (review-judge-reply-on-post design D3).
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
# Before Claude: what each changed file needs read, its diff in the workspace, and the turn budget
# that follows (review-covers-the-diff design D2, D5). Its constants are in the pinned script.
DIFF_NAME = "Write each changed file's diff"
DIFF = {"id": "diff", "shell": "python3 {0}"}
DIFF_SHA256 = "cd9c50c494bdba4de08e435d8b9fc0e526321a49b0606411615b23e9e45dea3c"
# The pull request's checkout keeps the merge commit's parents, so the diff step can diff against
# the base's tip (D2).
CHECKOUT_DEPTH = 2
# --max-turns comes from the diff step, never a fixed number (D5). GitHub substitutes it before
# the action reads claude_args.
MAX_TURNS = "${{ steps.diff.outputs.max_turns }}"
# The model is the repository variable OpenTofu declares (tofu/review.tf), checked by a step of
# its own and passed on as its output, never pasted from vars into claude_args (D6).
MODEL_NAME = "Check the review's model"
MODEL = {"id": "model", "shell": "python3 {0}", "env": {"MODEL": "${{ vars.CLAUDE_REVIEW_MODEL }}"}}
MODEL_SHA256 = "1566ed73c892e39e9531b83bb147ed5778ed215c939496f13718ae7e7b3424a2"
MODEL_ARG = "${{ steps.model.outputs.model }}"
# What the prompt must say about reading (D7, D7a): the list, reading every target in full, and
# the uses of what changed. And it mustn't send the review to `gh pr diff` for the diff.
PROMPT_READS = [
    "`.review-diff/files.json` lists every changed file",
    "Read every target in full with Read",
    "search the checkout for its uses with Grep",
    "a review that didn't read them all isn't a clean review",
    "make every one, as Read with the target's `path` and that `offset` and `limit`",
    "don't take a file's diff for the file",
]
PROMPT_NOT = "Read the diff with"
# After Claude: what it read, from the execution file only, never its structured output or its
# summary (D3). It can't fail the job; an output it didn't set fails the check (D4).
COVERAGE_NAME = "Measure what the review read"
COVERAGE = {
    "id": "coverage",
    "if": "${{ !cancelled() }}",
    "continue-on-error": True,
    "shell": "python3 {0}",
    "env": {"EXECUTION_FILE": "${{ steps.review.outputs.execution_file }}"},
}
COVERAGE_SHA256 = "5cddb61a0067b32b2ef66b94cd6fa2211c5296732f3f37dd95cfec8bcbacf013"
# Long enough for MAX_TURNS' cap (D5).
REVIEW_TIMEOUT = 90
# After Claude, in a job of its own, only when the review succeeded: resolve and re-tier what Claude
# names, checked against conversations read again in that job (design D4, D4a).
RESOLVER_NAME = "Resolve and re-tier what Claude named"
RESOLVER = {
    "shell": "python3 {0}",
    "env": {**STEP_ENV, "STRUCTURED_OUTPUT": "${{ needs.review.outputs.structured_output }}"},
}
REVIEW_OUTPUTS = {
    "structured_output": "${{ steps.review.outputs.structured_output }}",
    # What the review read, for the check (review-covers-the-diff design D4).
    "coverage": "${{ steps.coverage.outputs.coverage }}",
    "unread": "${{ steps.coverage.outputs.unread }}",
}
# The resolving job: after the review, only when it succeeded, with nothing checked out and no
# Claude, and the one token that can write contents, which resolving a conversation needs (D4a).
RESOLVE_NEEDS = "review"
RESOLVE_IF = "needs.review.result == 'success'"
RESOLVE_TOKEN_INPUTS = {
    **TOKEN_INPUTS,
    "permission-contents": "write",
}
RESOLVER_SHA256 = "0e693536e81d5708d820bac881ae42469381c98ce15b4d5d55e2935514e13ef3"
# The gate: before the review, outside its concurrency group, with D2's skip, it decides whether
# the event needs a review: a pull request event always, a reply only in an open must-fix the
# review opened. A no there costs no Claude run and cancels nothing (review-judge-reply-on-post
# design D2a).
GATE_NAME = "Decide whether this event needs a review"
GATE = {
    "id": "gate",
    "shell": "python3 {0}",
    "env": {
        **STEP_ENV,
        "EVENT": "${{ github.event_name }}",
        "REPLY_TO": "${{ github.event.comment.in_reply_to_id }}",
        "COMMENTER": "${{ github.event.comment.user.login }}",
    },
}
GATE_SHA256 = "508cbf7979901b76813676b9704755dd06954a5097aaf2d45360dc526227ba35"
GATE_OUTPUTS = {"review": "${{ steps.gate.outputs.review }}"}
GATE_TOKEN_INPUTS = {**TOKEN_INPUTS, "permission-pull-requests": "read"}
REVIEW_NEEDS = "gate"
REVIEW_IF = "needs.gate.outputs.review == 'true'"
OWN_STEPS = {REPORT_NAME, SNAPSHOT_NAME, DIFF_NAME, MODEL_NAME, COVERAGE_NAME}
# The required check that the review of the head completed (review-completed-check design D2 to
# D5): after every other job, whatever became of them, on pull request events only, since GitHub
# ignores a comment's run for a pull request (Probe results). No token, no secret, no checkout,
# and outside the concurrency group, so a newer review can't cancel it.
COMPLETED_NAME = "claude review completed"
COMPLETED_NEEDS = ["gate", "review", "resolve"]
COMPLETED_IF = "always() && github.event_name == 'pull_request'"
COMPLETED_STEP_NAME = "Did the review of this head complete?"
COMPLETED_STEP = {
    "shell": "python3 {0}",
    "env": {
        "REPOSITORY": "${{ github.repository }}",
        "RUN_ID": "${{ github.run_id }}",
        "AUTHOR_TYPE": "${{ github.event.pull_request.user.type }}",
        "HEAD_REPOSITORY": "${{ github.event.pull_request.head.repo.full_name }}",
        "GATE": "${{ needs.gate.result }}",
        "WANTS_REVIEW": "${{ needs.gate.outputs.review }}",
        "REVIEW": "${{ needs.review.result }}",
        "RESOLVE": "${{ needs.resolve.result }}",
        # What the review read (review-covers-the-diff design D4).
        "COVERAGE": "${{ needs.review.outputs.coverage }}",
        "UNREAD": "${{ needs.review.outputs.unread }}",
    },
}
COMPLETED_SHA256 = "a2375ac39af83706374874ab7fb319664a589b9309bdaa9b1141598798d9cffa"
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
    # The expressions GitHub substitutes before the action reads them, as one word each.
    text = str(inputs.get("claude_args", "")).replace(MAX_TURNS, "MAX_TURNS")
    text = text.replace(MODEL_ARG, "MODEL")
    words = shlex.split(text)
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
        elif words[i] in ("--max-turns", "--model") and i + 1 < len(words):
            # Each checked against its expression in problems().
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


def gate_job_problems(job: dict[str, Any]) -> list[str]:
    """The gate: D2's skip, no concurrency group, minting a read-only token, then its one step
    (design D2a)."""
    found = []
    if job.get("if") != SKIP:
        found.append(
            f"gate runs when {job.get('if')!r}, not skipping bots, forks, outsiders and "
            "comments that aren't replies"
        )
    if "concurrency" in job:
        found.append(
            "gate is in a concurrency group, so a reply it turns away would cancel a running review"
        )
    if "needs" in job:
        found.append(f"gate needs {job['needs']!r}; it runs first")
    if job.get("permissions") != PERMISSIONS:
        found.append(
            f"gate's GITHUB_TOKEN permissions are {job.get('permissions')!r}, not {PERMISSIONS!r}"
        )
    if "environment" in job:
        found.append(f"gate runs in environment {job['environment']!r}; it needs none")
    if not isinstance(job.get("timeout-minutes"), int):
        found.append("gate has no timeout-minutes")
    if job.get("outputs") != GATE_OUTPUTS:
        found.append(f"gate's outputs are {job.get('outputs')!r}, not {GATE_OUTPUTS!r}")
    steps = job.get("steps") or []
    shape = [
        "token"
        if str(s.get("uses", "")).startswith(f"{MINTER}@")
        else s.get("name") or s.get("uses")
        for s in steps
    ]
    if shape != ["token", GATE_NAME]:
        return [*found, f"gate's steps are {shape!r}, not the token and {GATE_NAME!r}"]
    minted, deciding = steps
    if not PINNED.match(str(minted.get("uses"))):
        found.append(f"{minted.get('uses')!r} isn't pinned to a full commit SHA")
    if minted.get("id") != "app-token":
        found.append(f"gate's token step's id is {minted.get('id')!r}, not app-token")
    given = dict(minted.get("with") or {})
    client_id = str(given.pop("client-id", ""))
    if not REVIEW_APP_CLIENT_ID.match(client_id):
        found.append(f"gate's client ID is {client_id!r}, not one written here")
    if given != GATE_TOKEN_INPUTS:
        found.append(f"gate's token is minted with {given!r}, not {GATE_TOKEN_INPUTS!r}")
    found += own_step_problems(deciding, GATE, GATE_SHA256, repr(GATE_NAME))
    return found


def completed_job_problems(job: dict[str, Any]) -> list[str]:
    """The required check: its name, after every job whatever their result, on pull request events
    only, no permissions, no concurrency group, and its one step (review-completed-check design
    D2 to D4)."""
    found = []
    if job.get("name") != COMPLETED_NAME:
        found.append(
            f"the check's job is named {job.get('name')!r}, not {COMPLETED_NAME!r}, the name "
            "tofu/required-checks.json requires"
        )
    if job.get("needs") != COMPLETED_NEEDS:
        found.append(f"completed needs {job.get('needs')!r}, not {COMPLETED_NEEDS!r}")
    if job.get("if") != COMPLETED_IF:
        found.append(
            f"completed runs when {job.get('if')!r}, not {COMPLETED_IF!r}: after a cancelled "
            "review too, and never for a comment's run or a merge group"
        )
    if job.get("permissions") != {}:
        found.append(
            f"completed's GITHUB_TOKEN permissions are {job.get('permissions')!r}, not none"
        )
    if "concurrency" in job:
        found.append("completed is in a concurrency group, so a newer review could cancel it")
    if "environment" in job:
        found.append(f"completed runs in environment {job['environment']!r}; it needs none")
    if not isinstance(job.get("timeout-minutes"), int):
        found.append("completed has no timeout-minutes")
    steps = job.get("steps") or []
    if [s.get("name") for s in steps] != [COMPLETED_STEP_NAME] or "uses" in steps[0]:
        return [*found, f"completed's steps aren't the one step {COMPLETED_STEP_NAME!r}"]
    found += own_step_problems(
        steps[0], COMPLETED_STEP, COMPLETED_SHA256, repr(COMPLETED_STEP_NAME)
    )
    return found


def problems(workflow: dict[str, Any]) -> list[str]:
    found = []
    on = workflow.get("on") or {}
    if set(on) != set(TRIGGERS):
        found.append(
            f"it runs on {sorted(on)}, not on pull_request, pull_request_review_comment and "
            "merge_group only"
        )
    for event, wanted in TRIGGERS.items():
        if wanted is None:
            if on.get(event) is not None:
                found.append(f"it runs on {event} {on.get(event)!r}, not every {event}")
            continue
        types = (on.get(event) or {}).get("types")
        if types != wanted["types"]:
            found.append(f"it runs on {event} {types!r}, not {wanted['types']!r}")
    if workflow.get("permissions") != PERMISSIONS:
        found.append(
            f"the default permissions are {workflow.get('permissions')!r}, not {PERMISSIONS!r}"
        )

    jobs = workflow.get("jobs") or {}
    if set(jobs) != {"gate", "review", "resolve", "completed"}:
        return [*found, f"its jobs are {sorted(jobs)}, not gate, review, resolve and completed"]
    job = jobs["review"]
    found += gate_job_problems(jobs["gate"])
    found += resolve_job_problems(jobs["resolve"])
    found += completed_job_problems(jobs["completed"])
    if job.get("needs") != REVIEW_NEEDS:
        found.append(f"review needs {job.get('needs')!r}, not {REVIEW_NEEDS!r}")
    if job.get("outputs") != REVIEW_OUTPUTS:
        found.append(f"review's outputs are {job.get('outputs')!r}, not {REVIEW_OUTPUTS!r}")

    if job.get("if") != REVIEW_IF:
        found.append(f"review runs when {job.get('if')!r}, not only on the gate's yes")
    if job.get("permissions") != PERMISSIONS:
        found.append(
            f"review's GITHUB_TOKEN permissions are {job.get('permissions')!r}, not {PERMISSIONS!r}"
        )
    if "environment" in job:
        found.append(f"review runs in environment {job['environment']!r}; it needs none")
    if "concurrency" in workflow:
        found.append(
            "its concurrency group is at the workflow level, where a run whose review is skipped "
            "joins it and cancels a running review"
        )
    for name in ("review", "resolve"):
        if jobs[name].get("concurrency") != CONCURRENCY:
            found.append(
                f"{name}'s concurrency is {jobs[name].get('concurrency')!r}, not one run per pull "
                "request, cancelling the last"
            )
    if not isinstance(job.get("timeout-minutes"), int):
        found.append("review has no timeout-minutes")
    elif job["timeout-minutes"] != REVIEW_TIMEOUT:
        found.append(
            f"review's timeout-minutes is {job['timeout-minutes']}, not {REVIEW_TIMEOUT}, "
            "which the turn cap needs"
        )

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
        elif own.get("fetch-depth") != CHECKOUT_DEPTH:
            found.append(
                f"the pull request's checkout has fetch-depth {own.get('fetch-depth')!r}, not "
                f"{CHECKOUT_DEPTH}, so the diff step has no base to diff against"
            )
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
    diffs = [step for step in steps if step.get("name") == DIFF_NAME and "run" in step]
    if len(diffs) != 1:
        found.append(f"review has {len(diffs)} steps named {DIFF_NAME!r}, not one")
    else:
        found += own_step_problems(diffs[0], DIFF, DIFF_SHA256, repr(DIFF_NAME))
        at = steps.index(diffs[0])
        if checkouts and not (steps.index(checkouts[-1]) < at < steps.index(actions[0])):
            found.append(f"{DIFF_NAME!r} doesn't run between the checkouts and the action")
    measures = [step for step in steps if step.get("name") == COVERAGE_NAME and "run" in step]
    if len(measures) != 1:
        found.append(f"review has {len(measures)} steps named {COVERAGE_NAME!r}, not one")
    else:
        found += own_step_problems(measures[0], COVERAGE, COVERAGE_SHA256, repr(COVERAGE_NAME))
        if steps.index(measures[0]) < steps.index(actions[0]):
            found.append(f"{COVERAGE_NAME!r} runs before the action")
    models = [step for step in steps if step.get("name") == MODEL_NAME and "run" in step]
    if len(models) != 1:
        found.append(f"review has {len(models)} steps named {MODEL_NAME!r}, not one")
    else:
        found += own_step_problems(models[0], MODEL, MODEL_SHA256, repr(MODEL_NAME))
        if steps.index(models[0]) > steps.index(actions[0]):
            found.append(f"{MODEL_NAME!r} runs after the action")
    if json_schema(inputs) != SCHEMA:
        found.append("Claude's structured output isn't the schema this test pins (SCHEMA)")

    prompt = str(inputs.get("prompt", ""))
    for path in (".org-guide/CONTRIBUTING.md", "org-profile/CONTRIBUTING.md"):
        if path not in prompt:
            found.append(f"the prompt doesn't name {path}")
    if GUIDE_URL in prompt:
        found.append("the prompt names the guide by URL, which the review has no tool to fetch")
    flat = " ".join(prompt.split())
    for sentence in PROMPT_READS:
        if sentence not in flat:
            found.append(f"the prompt doesn't say {sentence!r}")
    if PROMPT_NOT in flat:
        found.append(f"the prompt still says {PROMPT_NOT!r} with `gh pr diff`")

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
            f"claude_args has {others!r} besides --allowedTools, --max-turns, --model, "
            "--setting-sources and --json-schema"
        )
    if "--max-turns" not in str(inputs.get("claude_args", "")):
        found.append("claude_args has no --max-turns")
    elif f"--max-turns {MAX_TURNS}" not in str(inputs.get("claude_args", "")):
        found.append(f"--max-turns isn't {MAX_TURNS}, the turns the diff needs (D5)")
    if f"--model {MODEL_ARG}" not in str(inputs.get("claude_args", "")):
        found.append(f"--model isn't {MODEL_ARG}, the checked repository variable (D6)")
    return found


def test_the_workflow_is_as_designed() -> None:
    assert problems(review()) == []


def test_it_starts_with_its_source() -> None:
    first = REVIEW.read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("# Source: troupe-run/infrastructure."), first


def job(w: dict[str, Any]) -> dict[str, Any]:
    return w["jobs"]["review"]  # type: ignore[no-any-return]


def gate_job(w: dict[str, Any]) -> dict[str, Any]:
    return w["jobs"]["gate"]  # type: ignore[no-any-return]


def gate(w: dict[str, Any]) -> dict[str, Any]:
    step = next(s for s in gate_job(w)["steps"] if s.get("name") == GATE_NAME)
    return step  # type: ignore[no-any-return]


def gate_token(w: dict[str, Any]) -> dict[str, Any]:
    return gate_job(w)["steps"][0]  # type: ignore[no-any-return]


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


def diff_step(w: dict[str, Any]) -> dict[str, Any]:
    step = next(s for s in job(w)["steps"] if s.get("name") == DIFF_NAME)
    return step  # type: ignore[no-any-return]


def coverage_step(w: dict[str, Any]) -> dict[str, Any]:
    step = next(s for s in job(w)["steps"] if s.get("name") == COVERAGE_NAME)
    return step  # type: ignore[no-any-return]


def model_step(w: dict[str, Any]) -> dict[str, Any]:
    step = next(s for s in job(w)["steps"] if s.get("name") == MODEL_NAME)
    return step  # type: ignore[no-any-return]


def diff_script(w: dict[str, Any], old: str, new: str) -> None:
    assert old in str(diff_step(w)["run"]), old
    diff_step(w)["run"] = str(diff_step(w)["run"]).replace(old, new)


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


def completed_job(w: dict[str, Any]) -> dict[str, Any]:
    return w["jobs"]["completed"]  # type: ignore[no-any-return]


def completed(w: dict[str, Any]) -> dict[str, Any]:
    return completed_job(w)["steps"][0]  # type: ignore[no-any-return]


def tools(w: dict[str, Any], change: str) -> None:
    action(w)["claude_args"] = str(action(w)["claude_args"]).replace("Bash(gh pr view:*)", change)


def unskip(w: dict[str, Any], part: str, to: str = "") -> None:
    assert part in str(gate_job(w)["if"]), part
    gate_job(w)["if"] = str(gate_job(w)["if"]).replace(part, to)


def sources(w: dict[str, Any], change: str) -> None:
    action(w)["claude_args"] = str(action(w)["claude_args"]).replace(
        "--setting-sources user", change
    )


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (lambda w: w.update({"on": {"pull_request_target": None}}), "not on pull_request, pull"),
        (lambda w: w["on"].update({"push": None}), "not on pull_request, pull"),
        (lambda w: w["on"].update({"issue_comment": None}), "not on pull_request, pull"),
        (lambda w: w["on"].update({"pull_request_review": None}), "not on pull_request, pull"),
        (lambda w: w["on"].pop("pull_request_review_comment"), "not on pull_request, pull"),
        (
            lambda w: w["on"]["pull_request_review_comment"]["types"].append("edited"),
            "pull_request_review_comment ['created', 'edited'], not ['created']",
        ),
        (
            lambda w: w["on"]["pull_request_review_comment"].pop("types"),
            "pull_request_review_comment None",
        ),
        (lambda w: w["on"]["pull_request"]["types"].append("edited"), "not ['opened'"),
        (lambda w: w["on"]["pull_request"]["types"].remove("synchronize"), "not ['opened'"),
        (lambda w: w["on"]["pull_request"]["types"].append("ready_for_review"), "not ['opened'"),
        (lambda w: w.update({"permissions": {"contents": "write"}}), "default permissions"),
        (lambda w: w.pop("permissions"), "default permissions"),
        (lambda w: gate_job(w).pop("if"), "not skipping bots, forks, outsiders"),
        (
            lambda w: gate_job(w).update({"if": "github.event.pull_request.user.type != 'Bot'"}),
            "not skipping bots, forks, outsiders",
        ),
        (lambda w: job(w).pop("if"), "not only on the gate's yes"),
        (lambda w: job(w).update({"if": "always()"}), "not only on the gate's yes"),
        (lambda w: job(w).pop("needs"), "review needs None"),
        (lambda w: w["jobs"].pop("gate"), "not gate, review, resolve"),
        (
            lambda w: gate_job(w).update({"concurrency": copy.deepcopy(CONCURRENCY)}),
            "gate is in a concurrency group",
        ),
        (lambda w: gate_job(w).update({"needs": "review"}), "it runs first"),
        (
            lambda w: gate_job(w)["permissions"].update({"pull-requests": "read"}),
            "gate's GITHUB_TOKEN permissions",
        ),
        (
            lambda w: gate_token(w)["with"].update({"permission-pull-requests": "write"}),
            "gate's token is minted with",
        ),
        (
            lambda w: gate_token(w)["with"].update({"permission-contents": "write"}),
            "gate's token is minted with",
        ),
        (lambda w: gate_job(w).pop("outputs"), "gate's outputs are None"),
        (lambda w: gate_job(w).pop("timeout-minutes"), "gate has no timeout-minutes"),
        (
            lambda w: gate(w).update({"run": str(gate(w)["run"]) + "\nprint()\n"}),
            "script isn't the one this test pins",
        ),
        (
            lambda w: gate(w)["env"].update({"REPLY_TO": "${{ github.event.comment.id }}"}),
            f"{GATE_NAME!r} is given",
        ),
        (
            lambda w: gate_job(w)["steps"].append({"run": "echo hi"}),
            "gate's steps are",
        ),
        (
            lambda w: unskip(w, "github.event.comment.in_reply_to_id != null && "),
            "not skipping bots, forks, outsiders",
        ),
        (
            lambda w: unskip(w, " && github.event.comment.user.type != 'Bot'"),
            "not skipping bots, forks, outsiders",
        ),
        (
            lambda w: unskip(
                w,
                "github.event.comment.user.type != 'Bot'",
                "github.event.comment.user.type != 'Bot' && "
                "github.event.comment.author_association != 'NONE'",
            ),
            "not skipping bots, forks, outsiders",
        ),
        (
            lambda w: gate(w)["env"].update({"COMMENTER": "${{ github.actor }}"}),
            f"{GATE_NAME!r} is given",
        ),
        (
            lambda w: unskip(
                w, "github.event.pull_request.head.repo.full_name == github.repository && "
            ),
            "not skipping bots, forks, outsiders",
        ),
        (
            lambda w: unskip(w, "github.event_name == 'pull_request' || "),
            "not skipping bots, forks, outsiders",
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
        (lambda w: job(w).pop("concurrency"), "review's concurrency is None"),
        (lambda w: resolve_job(w).pop("concurrency"), "resolve's concurrency is None"),
        (
            lambda w: job(w)["concurrency"].update({"cancel-in-progress": False}),
            "review's concurrency",
        ),
        (
            lambda w: resolve_job(w)["concurrency"].update({"group": "claude-resolve"}),
            "resolve's concurrency",
        ),
        (
            lambda w: w.update({"concurrency": job(w).pop("concurrency")}),
            "at the workflow level",
        ),
        (lambda w: job(w).pop("timeout-minutes"), "no timeout-minutes"),
        (lambda w: w["jobs"].update({"other": {}}), "not gate, review, resolve"),
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
                {
                    "claude_args": str(action(w)["claude_args"]).replace(
                        f"--max-turns {MAX_TURNS}", ""
                    )
                }
            ),
            "no --max-turns",
        ),
        (lambda w: job(w)["steps"].remove(snapshot(w)), '0 steps named "Read the pull'),
        (lambda w: resolve_job(w)["steps"].remove(resolver(w)), "resolve's steps are"),
        (lambda w: w["jobs"].pop("resolve"), "not gate, review, resolve"),
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
                {
                    "run": str(resolver(w)["run"]).replace(
                        'if current not in ("must-fix", "nit"):', "if False:"
                    )
                }
            ),
            "'Resolve and re-tier what Claude named''s script isn't the one this test pins",
        ),
        # Widened to decisions, which are the owner's (review-resolves-fixed-nits design D2).
        (
            lambda w: resolver(w).update(
                {
                    "run": str(resolver(w)["run"]).replace(
                        '("must-fix", "nit")', '("must-fix", "nit", "decision")'
                    )
                }
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
        (lambda w: w["on"].pop("merge_group"), "not on pull_request, pull"),
        (lambda w: w["on"].update({"merge_group": {"types": ["checks_requested"]}}), "not every"),
        (lambda w: w["jobs"].pop("completed"), "not gate, review, resolve"),
        (lambda w: completed_job(w).update({"name": "review completed"}), "required-checks.json"),
        (lambda w: completed_job(w).update({"needs": ["review", "resolve"]}), "completed needs"),
        (lambda w: completed_job(w).update({"needs": "resolve"}), "completed needs"),
        # Without always(), a cancelled or failed review skips it, which counts as passed.
        (
            lambda w: completed_job(w).update({"if": "github.event_name == 'pull_request'"}),
            "after a cancelled review too",
        ),
        (lambda w: completed_job(w).pop("if"), "after a cancelled review too"),
        # A merge group or a comment's run reporting it: a merge group must skip it, and a
        # comment's run reports what GitHub ignores (design D4, D5).
        (lambda w: completed_job(w).update({"if": "always()"}), "never for a comment's run"),
        (
            lambda w: completed_job(w).update(
                {"if": "always() && github.event_name != 'merge_group'"}
            ),
            "never for a comment's run",
        ),
        (
            lambda w: completed_job(w).update({"permissions": {"actions": "read"}}),
            "completed's GITHUB_TOKEN permissions",
        ),
        (lambda w: completed_job(w).pop("permissions"), "completed's GITHUB_TOKEN permissions"),
        (
            lambda w: completed_job(w).update({"concurrency": copy.deepcopy(CONCURRENCY)}),
            "completed is in a concurrency group",
        ),
        (lambda w: completed_job(w).pop("timeout-minutes"), "completed has no timeout-minutes"),
        (
            lambda w: completed_job(w)["steps"].insert(
                0, {"uses": "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"}
            ),
            "completed's steps aren't the one step",
        ),
        (
            lambda w: completed(w)["env"].update(
                {"TOKEN": "${{ secrets.REVIEW_APP_PRIVATE_KEY }}"}
            ),
            f"{COMPLETED_STEP_NAME!r} is given",
        ),
        (
            lambda w: completed(w)["env"].update({"REVIEW": "${{ needs.gate.result }}"}),
            f"{COMPLETED_STEP_NAME!r} is given",
        ),
        (
            lambda w: completed(w).update({"run": str(completed(w)["run"]) + "\nsys.exit(0)\n"}),
            "complete?''s script isn't the one this test pins",
        ),
        # The diff the review reads, and the turns it needs (review-covers-the-diff D2, D5).
        (lambda w: job(w)["steps"][0]["with"].update({"fetch-depth": 1}), "fetch-depth 1, not 2"),
        (lambda w: job(w)["steps"].remove(diff_step(w)), '0 steps named "Write each'),
        (lambda w: move(w, diff_step(w), len(job(w)["steps"])), "between the checkouts and"),
        (lambda w: move(w, diff_step(w), 0), "between the checkouts and the action"),
        (lambda w: diff_step(w).update({"id": "files"}), '"Write each changed file\'s diff" is'),
        (
            lambda w: diff_step(w).update({"env": {"T": "${{ secrets.GITHUB_TOKEN }}"}}),
            "also has ['env']",
        ),
        (lambda w: diff_script(w, '"uv.lock", ', '"uv.lock", "x.py", '), "this test pins"),
        (lambda w: diff_script(w, "MAX_TURNS = 400", "MAX_TURNS = 9999"), "this test pins"),
        (lambda w: diff_script(w, "READ_CHUNK_BYTES = 20_000", "READ_CHUNK_BYTES = 10**9"), "pins"),
        (
            lambda w: action(w).update(
                {"claude_args": str(action(w)["claude_args"]).replace(MAX_TURNS, "30")}
            ),
            "--max-turns isn't",
        ),
        # What the prompt says about reading (D7, D7a).
        *[
            (
                lambda w, s=sentence: action(w).update(
                    {"prompt": " ".join(str(action(w)["prompt"]).split()).replace(s, "")}
                ),
                f"the prompt doesn't say {sentence!r}",
            )
            for sentence in PROMPT_READS
        ],
        (
            lambda w: action(w).update(
                {"prompt": str(action(w)["prompt"]) + "\nRead the diff with `gh pr diff`.\n"}
            ),
            "the prompt still says",
        ),
        # What the review read (D3, D4).
        (lambda w: job(w)["steps"].remove(coverage_step(w)), "0 steps named 'Measure what"),
        (lambda w: move(w, coverage_step(w), 0), "runs before the action"),
        (
            lambda w: coverage_step(w)["env"].update(
                {"EXECUTION_FILE": "${{ steps.review.outputs.structured_output }}"}
            ),
            "'Measure what the review read' is given",
        ),
        (
            lambda w: coverage_step(w)["env"].update(
                {"SAID": "${{ steps.review.outputs.structured_output }}"}
            ),
            "'Measure what the review read' is given",
        ),
        (lambda w: coverage_step(w).pop("continue-on-error"), "the review read' is given"),
        (lambda w: coverage_step(w).update({"if": "${{ success() }}"}), "review read' is given"),
        (
            lambda w: coverage_step(w).update(
                {"run": str(coverage_step(w)["run"]) + "print(text)\n"}
            ),
            "the review read''s script isn't the one this test pins",
        ),
        (lambda w: job(w)["outputs"].pop("coverage"), "review's outputs are"),
        (lambda w: job(w).update({"timeout-minutes": 20}), "timeout-minutes is 20, not 90"),
        # The model, from the checked variable (D6).
        (lambda w: job(w)["steps"].remove(model_step(w)), '0 steps named "Check the review'),
        (lambda w: move(w, model_step(w), len(job(w)["steps"])), "runs after the action"),
        (
            lambda w: model_step(w)["env"].update({"MODEL": "claude-opus-5-5"}),
            '"Check the review\'s model" is given',
        ),
        (
            lambda w: action(w).update(
                {
                    "claude_args": str(action(w)["claude_args"]).replace(
                        MODEL_ARG, "${{ vars.CLAUDE_REVIEW_MODEL }}"
                    )
                }
            ),
            "--model isn't",
        ),
        (
            lambda w: action(w).update(
                {"claude_args": str(action(w)["claude_args"]).replace(f"--model {MODEL_ARG}", "")}
            ),
            "--model isn't",
        ),
        # The check judges what the review read (D4).
        (lambda w: completed(w)["env"].pop("COVERAGE"), f"{COMPLETED_STEP_NAME!r} is given"),
        (
            lambda w: completed(w)["env"].update({"COVERAGE": "complete"}),
            f"{COMPLETED_STEP_NAME!r} is given",
        ),
        (
            lambda w: completed(w)["env"].update(
                {"COVERAGE": "${{ needs.review.outputs.structured_output }}"}
            ),
            f"{COMPLETED_STEP_NAME!r} is given",
        ),
        (
            lambda w: completed(w).update(
                {"run": str(completed(w)["run"]).replace('if coverage != "complete":', "if False:")}
            ),
            "complete?''s script isn't the one this test pins",
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


def run_completed(tmp_path: Path, **results: str) -> subprocess.CompletedProcess[str]:
    """Run the required check's step, as a pull request event's run of a member's own pull request
    would, with the needs' results given here instead of a completed review's."""
    env = {
        "RUN_ID": "41258918187",
        "AUTHOR_TYPE": "User",
        "HEAD_REPOSITORY": "troupe-run/infrastructure",
        "GATE": "success",
        "WANTS_REVIEW": "true",
        "REVIEW": "success",
        "RESOLVE": "success",
        "COVERAGE": "complete",
        "UNREAD": "[]",
        **results,
    }
    return run_step(completed(review()), tmp_path, tmp_path, env)


def test_the_check_passes_when_the_review_and_its_resolving_job_succeeded(tmp_path: Path) -> None:
    done = run_completed(tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "::error" not in done.stdout


@pytest.mark.parametrize(
    ("results", "named"),
    [
        ({"REVIEW": "cancelled", "RESOLVE": "cancelled"}, "claude review (cancelled)"),
        ({"REVIEW": "failure", "RESOLVE": "skipped"}, "claude review (failure)"),
        ({"RESOLVE": "failure"}, "resolve review conversations (failure)"),
        ({"RESOLVE": "cancelled"}, "resolve review conversations (cancelled)"),
        ({"REVIEW": "", "RESOLVE": ""}, "claude review (no result)"),
    ],
)
def test_a_review_that_didn_t_complete_fails_naming_the_run_to_re_run(
    tmp_path: Path, results: dict[str, str], named: str
) -> None:
    done = run_completed(tmp_path, **results)
    assert done.returncode == 1
    errors = [line for line in done.stdout.splitlines() if line.startswith("::error")]
    assert len(errors) == 1, done.stdout
    assert named in errors[0]
    assert "gh run rerun 41258918187" in errors[0]


@pytest.mark.parametrize(
    "results",
    [
        {"GATE": "failure", "WANTS_REVIEW": "", "REVIEW": "skipped", "RESOLVE": "skipped"},
        {"GATE": "cancelled", "WANTS_REVIEW": "", "REVIEW": "skipped", "RESOLVE": "skipped"},
        # A pull request event's gate always says yes; anything else isn't an answer to trust.
        {"WANTS_REVIEW": "false", "REVIEW": "skipped", "RESOLVE": "skipped"},
        {"WANTS_REVIEW": "", "REVIEW": "skipped", "RESOLVE": "skipped"},
        # Skipped by the gate's own if:, but the pull request is a member's, not a bot's or fork's.
        {"GATE": "skipped", "WANTS_REVIEW": "", "REVIEW": "skipped", "RESOLVE": "skipped"},
    ],
)
def test_a_gate_that_didn_t_say_yes_fails_the_check(
    tmp_path: Path, results: dict[str, str]
) -> None:
    done = run_completed(tmp_path, **results)
    assert done.returncode == 1
    assert "::error title=Review not started::" in done.stdout
    assert "gh run rerun 41258918187" in done.stdout


@pytest.mark.parametrize(
    "who",
    [
        {"AUTHOR_TYPE": "Bot"},
        {"HEAD_REPOSITORY": "someone/infrastructure"},
        # A fork that's since been deleted has no head repository.
        {"HEAD_REPOSITORY": ""},
    ],
)
def test_a_bot_s_or_a_fork_s_pull_request_passes_with_its_review_skipped(
    tmp_path: Path, who: dict[str, str]
) -> None:
    skipped = {"GATE": "skipped", "WANTS_REVIEW": "", "REVIEW": "skipped", "RESOLVE": "skipped"}
    done = run_completed(tmp_path, **skipped, **who)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "isn't reviewed" in done.stdout


def test_without_a_run_id_the_check_still_says_how_to_re_run(tmp_path: Path) -> None:
    done = run_completed(tmp_path, RUN_ID="", REVIEW="cancelled", RESOLVE="cancelled")
    assert done.returncode == 1
    assert "gh run rerun <this run's ID>" in done.stdout


def test_an_input_that_holds_a_workflow_command_stays_inside_the_check_s_one_error(
    tmp_path: Path,
) -> None:
    done = run_completed(tmp_path, GATE="failure\n::notice::injected", WANTS_REVIEW="")
    assert done.returncode == 1
    assert [line for line in done.stdout.splitlines() if line.startswith("::")] == [
        line for line in done.stdout.splitlines() if line.startswith("::error")
    ]
    assert "%0A::notice::injected" in done.stdout


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


def resolver_constants(step: dict[str, Any] | None = None) -> tuple[re.Pattern[str], object]:
    """The LABEL and BOT the resolving step's script, or another step's, defines, read without
    running it."""
    tree = ast.parse(str((step or resolver(review()))["run"]))
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


def test_the_prompt_tells_the_review_to_resolve_a_nit_only_on_a_fix_and_never_a_decision() -> None:
    # The step checks the tier; only the prompt can say a nit needs a fix in the diff, not a reply
    # (review-resolves-fixed-nits design D1).
    prompt = " ".join(str(action(review())["prompt"]).split())
    assert "Never resolve a decision or a nit" not in prompt
    assert "a nit whose problem is gone from the diff: name its ID in `resolve`" in prompt
    assert "A reply alone doesn't settle a nit" in prompt
    assert "Never resolve a decision, nor anyone else's conversation" in prompt


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


def test_only_the_review_s_open_must_fixes_and_nits_are_resolved(tmp_path: Path) -> None:
    # PRRT_selflabel is a nit: a person's label counts for nothing.
    allowed = ["PRRT_mustfix", "PRRT_upgraded", "PRRT_downgraded", "PRRT_nit", "PRRT_selflabel"]
    refused = ["PRRT_decision", "PRRT_unlabelled", "PRRT_person", "PRRT_done", "PRRT_elsewhere"]
    done, calls = resolve_run(tmp_path, {"resolve": allowed + refused, "retier": []})
    assert done.returncode == 0, done.stdout + done.stderr
    assert resolved(calls) == allowed
    for call in calls:
        query = next(arg for arg in call if arg.startswith("query=")).partition("=")[2]
        assert guard.graphql_mutations(query) == ["resolveReviewThread"]
    warnings = [line for line in done.stdout.splitlines() if line.startswith("::warning")]
    assert len(warnings) == len(refused)
    for ident in refused:
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


def test_the_gate_reads_a_label_and_the_review_as_the_resolving_step_does() -> None:
    label, bot = resolver_constants(gate(review()))
    assert (label.pattern, bot) == (resolver_constants()[0].pattern, resolver_constants()[1])


def run_gate(
    tmp_path: Path, answers: dict[str, Any], env: dict[str, str]
) -> tuple[subprocess.CompletedProcess[str], str | None, list[list[str]]]:
    """Run the gate's step against the stub gh, and read what it wrote to GITHUB_OUTPUT."""
    output = tmp_path / "github-output"
    output.write_text("", encoding="utf-8")
    bin_dir = stub_gh(tmp_path / "bin", answers)
    done = run_step(gate(review()), tmp_path, bin_dir, {"GITHUB_OUTPUT": str(output), **env})
    said = [
        line.partition("=")[2]
        for line in output.read_text(encoding="utf-8").splitlines()
        if line.startswith("review=")
    ]
    assert len(said) <= 1, said
    return done, said[0] if said else None, gh_calls(bin_dir)


REPLY = {"EVENT": "pull_request_review_comment", "REPLY_TO": "100", "COMMENTER": "martin-at-hpsgd"}
PUSHER = {"permission": "admin"}


def test_the_gate_lets_every_pull_request_event_through_without_reading_anything(
    tmp_path: Path,
) -> None:
    done, said, calls = run_gate(tmp_path, {}, {"EVENT": "pull_request", "REPLY_TO": ""})
    assert done.returncode == 0, done.stdout + done.stderr
    assert said == "true"
    assert calls == []


def resolved_conversation(thread: Any) -> Any:  # noqa: ANN401
    return {**thread, "isResolved": True}


B, P = BOT_AUTHOR, PERSON
MUST_FIX, NIT, DECISION = "**must-fix** · x", "**nit** · x", "**decision** · x"
GATE_CASES = [
    ("must-fix", conversation("T", B, (B, MUST_FIX), (P, "it's right")), "true"),
    ("nit made must-fix", conversation("T", B, (B, NIT), (P, "r"), (B, MUST_FIX)), "true"),
    ("nit", conversation("T", B, (B, NIT), (P, "fixed")), "false"),
    ("decision", conversation("T", B, (B, DECISION), (P, "a or b?")), "false"),
    ("must-fix made nit", conversation("T", B, (B, MUST_FIX), (P, "r"), (B, NIT)), "false"),
    ("a person's label", conversation("T", B, (B, NIT), (P, MUST_FIX)), "false"),
    ("a person's conversation", conversation("T", P, (P, MUST_FIX), (P, "r")), "false"),
    ("resolved", resolved_conversation(conversation("T", B, (B, MUST_FIX))), "false"),
]


@pytest.mark.parametrize(("what", "thread", "expected"), GATE_CASES, ids=[c[0] for c in GATE_CASES])
def test_the_gate_lets_through_only_a_reply_to_an_open_must_fix_of_the_review_s(
    tmp_path: Path,
    what: str,
    thread: dict[str, Any],
    expected: str,
) -> None:
    other = conversation("U", PERSON, (PERSON, "elsewhere"))
    other["opened"]["nodes"][0]["databaseId"] = 200
    other["comments"]["nodes"][0]["databaseId"] = 200
    pages = [PUSHER, page([other], True, "C1"), page([thread], False, None)]
    done, said, calls = run_gate(tmp_path, {"pages": pages}, REPLY)
    assert done.returncode == 0, done.stdout + done.stderr
    assert said == expected, what
    assert calls[0] == [
        "api", "repos/troupe-run/infrastructure/collaborators/martin-at-hpsgd/permission"
    ]  # fmt: skip
    assert len(calls) == 3
    assert all(call[:2] == ["api", "graphql"] for call in calls[1:])
    query = next(arg for arg in calls[1] if arg.startswith("query=")).partition("=")[2]
    assert guard.graphql_mutations(query) == []


@pytest.mark.parametrize("permission", ["admin", "write"])
def test_a_pusher_s_reply_to_a_must_fix_is_reviewed(tmp_path: Path, permission: str) -> None:
    thread = conversation("T", B, (B, MUST_FIX), (P, "it's right"))
    pages = [{"permission": permission}, page([thread], False, None)]
    done, said, _ = run_gate(tmp_path, {"pages": pages}, REPLY)
    assert done.returncode == 0, done.stdout + done.stderr
    assert said == "true"


@pytest.mark.parametrize("permission", ["read", "none", "triage", "maintain"])
def test_a_reply_by_someone_who_can_t_push_starts_no_review_and_reads_nothing_more(
    tmp_path: Path, permission: str
) -> None:
    done, said, calls = run_gate(tmp_path, {"pages": [{"permission": permission}]}, REPLY)
    assert done.returncode == 0, done.stdout + done.stderr
    assert said == "false"
    assert len(calls) == 1


def test_a_reply_to_a_comment_in_no_conversation_read_starts_no_review(tmp_path: Path) -> None:
    thread = conversation("T", BOT_AUTHOR, (BOT_AUTHOR, "**must-fix** · x"))
    done, said, _ = run_gate(tmp_path, {"pages": [PUSHER, page([thread], False, None)]},
                             {**REPLY, "REPLY_TO": "999"})  # fmt: skip
    assert done.returncode == 0, done.stdout + done.stderr
    assert said == "false"


@pytest.mark.parametrize(
    ("answers", "env"),
    [
        ({"status": 1}, REPLY),
        ({"pages": [PUSHER, "not a page"]}, REPLY),
        ({"pages": [PUSHER, {"data": None}]}, REPLY),
        ({"pages": [PUSHER], "fail_when": "query="}, REPLY),
        ({"pages": [{"permission": None}]}, REPLY),
        ({"pages": ["not an answer"]}, REPLY),
        ({"fail_when": "/permission"}, REPLY),
        ({}, {**REPLY, "REPLY_TO": ""}),
        ({}, {**REPLY, "REPLY_TO": "12a"}),
        ({}, {**REPLY, "COMMENTER": ""}),
        ({}, {**REPLY, "COMMENTER": "a/../../x"}),
    ],
)
def test_a_gate_that_can_t_tell_fails_and_says_nothing(
    tmp_path: Path, answers: dict[str, Any], env: dict[str, str]
) -> None:
    done, said, _ = run_gate(tmp_path, answers, env)
    assert done.returncode == 1
    assert done.stdout.startswith("::error title=")
    assert said is None


# The diff step, run on a repository whose HEAD is a merge commit, as GitHub's checkout of a pull
# request is (review-covers-the-diff design D2, D5).
DIFF_READ_CHUNK = 20_000


def merged(tmp_path: Path, base: Mapping[str, bytes], head: Mapping[str, bytes | None]) -> Path:
    """A workspace whose HEAD merges a branch into main: `base` is main's files, `head` what the
    branch writes over them (None deletes one)."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    git(workspace, "init", "-q", "-b", "main")
    git(workspace, "config", "user.email", "tester@example.com")
    git(workspace, "config", "user.name", "Tester")
    git(workspace, "config", "commit.gpgsign", "false")
    for name, contents in {"README.md": b"base\n", **base}.items():
        (workspace / name).parent.mkdir(parents=True, exist_ok=True)
        (workspace / name).write_bytes(contents)
    git(workspace, "add", "-A")
    git(workspace, "commit", "-q", "-m", "chore: base")
    git(workspace, "switch", "-q", "-c", "pr")
    for name, data in head.items():
        if data is None:
            git(workspace, "rm", "-q", name)
        else:
            (workspace / name).parent.mkdir(parents=True, exist_ok=True)
            (workspace / name).write_bytes(data)
    git(workspace, "add", "-A")
    git(workspace, "commit", "-q", "-m", "feat: the pull request")
    git(workspace, "switch", "-q", "main")
    git(workspace, "commit", "-q", "--allow-empty", "-m", "chore: main moves on")
    git(workspace, "merge", "-q", "--no-ff", "--no-edit", "pr")
    return workspace


Ran = tuple[subprocess.CompletedProcess[str], dict[str, Any] | None, str]


def run_diff(workspace: Path) -> Ran:
    """Run the diff step in the workspace: its result, the list it left in RUNNER_TEMP, and its
    outputs."""
    runner_temp = workspace.parent / "runner-temp"
    runner_temp.mkdir(exist_ok=True)
    outputs = workspace.parent / "outputs"
    outputs.write_text("", encoding="utf-8")
    script = workspace.parent / "diff.py"
    script.write_text(str(diff_step(review())["run"]), encoding="utf-8")
    env = {**clean_env(), "RUNNER_TEMP": str(runner_temp), "GITHUB_OUTPUT": str(outputs)}
    done = subprocess.run(
        [sys.executable, str(script)], cwd=workspace, capture_output=True, text=True,
        encoding="utf-8", env=env, check=False,
    )  # fmt: skip
    listed = runner_temp / "review-files.json"
    data = json.loads(listed.read_text(encoding="utf-8")) if listed.exists() else None
    return done, data, outputs.read_text(encoding="utf-8")


def targets(data: dict[str, Any]) -> dict[str, list[str]]:
    return {f["path"]: [t["path"] for t in f["targets"]] for f in data["files"]}


def test_each_change_lists_what_it_needs_read(tmp_path: Path) -> None:
    workspace = merged(
        tmp_path,
        {"keep.py": b"a\nb\n", "gone.py": b"old\n", "move_me.py": b"x = 1\n"},
        {"keep.py": b"a\nB\n", "gone.py": None, "added.py": b"new\n", "move_me.py": None,
         "moved.py": b"x = 1\n"},
    )  # fmt: skip
    done, data, _ = run_diff(workspace)
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    assert targets(data) == {
        "keep.py": ["keep.py", ".review-diff/keep.py.diff"],
        "gone.py": [".review-diff/gone.py.diff"],
        "added.py": ["added.py"],
        "moved.py": ["moved.py", ".review-diff/moved.py.diff"],
    }
    statuses = {f["path"]: f["status"] for f in data["files"]}
    assert statuses == {
        "keep.py": "modified", "gone.py": "deleted", "added.py": "added", "moved.py": "renamed"
    }  # fmt: skip
    removed = (workspace / ".review-diff" / "gone.py.diff").read_text(encoding="utf-8")
    assert "-old" in removed


def test_a_target_s_lines_are_counted_as_read_numbers_them(tmp_path: Path) -> None:
    workspace = merged(tmp_path, {}, {"three.txt": b"a\nb\nc\n", "no_newline.txt": b"a\nb"})
    done, data, _ = run_diff(workspace)
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    counts = {t["path"]: t["lines"] for f in data["files"] for t in f["targets"]}
    assert counts == {"three.txt": 3, "no_newline.txt": 2}


def test_a_lockfile_and_a_binary_file_need_nothing_read(tmp_path: Path) -> None:
    workspace = merged(
        tmp_path,
        {"uv.lock": b"a\n", "tofu/terraform.tfstate": b"{}\n"},
        {"uv.lock": b"b\n", "tofu/terraform.tfstate": b'{"v": 2}\n', "blob.bin": bytes(range(256))},
    )
    done, data, _ = run_diff(workspace)
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    assert {f["path"]: (f["targets"], f.get("skipped")) for f in data["files"]} == {
        "uv.lock": ([], "on the skip list"),
        "tofu/terraform.tfstate": ([], "on the skip list"),
        "blob.bin": ([], "binary"),
    }


@pytest.mark.parametrize(
    "attributes", [b"*.py -diff\n", b"*.py binary\n", b'*.py diff=hide\n[diff "hide"]\n']
)
def test_gitattributes_can_t_make_code_binary(tmp_path: Path, attributes: bytes) -> None:
    """#274's review: .gitattributes in the pull request, or the repository, mustn't turn its code
    into "Binary files differ" and so exempt it from the read."""
    workspace = merged(
        tmp_path,
        {"code.py": b"x = 1\n", "old.py": b"y = 2\n"},
        {".gitattributes": attributes, "code.py": b"x = 2\n", "old.py": None},
    )
    git(workspace, "config", "diff.hide.textconv", "true")
    done, data, _ = run_diff(workspace)
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    assert targets(data)["code.py"] == ["code.py", ".review-diff/code.py.diff"]
    assert targets(data)["old.py"] == [".review-diff/old.py.diff"]
    written = (workspace / ".review-diff" / "code.py.diff").read_text(encoding="utf-8")
    assert "-x = 1" in written
    assert "+x = 2" in written


def test_a_path_the_action_restores_is_read_from_its_copy_of_the_pull_request(
    tmp_path: Path,
) -> None:
    """#274's review: the action puts CLAUDE.md, .claude/ and the rest back from the base before
    Claude starts, keeping the pull request's copies under .claude-pr/. So their whole-file targets
    are those copies, counted from the pull request's blob, not the base's file."""
    workspace = merged(
        tmp_path,
        {"CLAUDE.md": b"one\n", ".claude/settings.json": b"{}\n", "src/x.py": b"a\n"},
        {
            "CLAUDE.md": b"one\ntwo\nthree\n",
            ".claude/settings.json": b'{\n  "a": 1\n}\n',
            ".husky/pre-commit": b"#!/bin/sh\nexit 0\n",
            "src/CLAUDE.md": b"nested\n",
        },
    )
    done, data, _ = run_diff(workspace)
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    assert targets(data) == {
        "CLAUDE.md": [".claude-pr/CLAUDE.md", ".review-diff/CLAUDE.md.diff"],
        ".claude/settings.json": [
            ".claude-pr/.claude/settings.json",
            ".review-diff/.claude/settings.json.diff",
        ],
        ".husky/pre-commit": [".claude-pr/.husky/pre-commit"],
        # Only the paths at the top of the checkout are restored.
        "src/CLAUDE.md": ["src/CLAUDE.md"],
    }
    counts = {t["path"]: t["lines"] for f in data["files"] for t in f["targets"]}
    assert counts[".claude-pr/CLAUDE.md"] == 3
    assert counts[".claude-pr/.claude/settings.json"] == 3


def test_a_nul_byte_planted_in_a_text_file_doesn_t_make_it_binary(tmp_path: Path) -> None:
    """#274's review: a NUL is something the pull request controls, and it's valid UTF-8. A text
    file with one planted near its top is still read; a file that isn't UTF-8 with a NUL isn't."""
    planted = b"// \0 a comment\nconst x = 1;\n"
    image = b"\x89PNG\r\n\x1a\n\0\0\0\rIHDR\xff\xfe"
    workspace = merged(tmp_path, {}, {"app.js": planted, "logo.png": image})
    done, data, _ = run_diff(workspace)
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    assert targets(data)["app.js"] == ["app.js"]
    assert {f["path"]: f.get("skipped") for f in data["files"]}["logo.png"] == "binary"


def test_a_deleted_binary_file_needs_nothing_read(tmp_path: Path) -> None:
    done, data, _ = run_diff(merged(tmp_path, {"blob.bin": bytes(range(256))}, {"blob.bin": None}))
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    assert [(f["path"], f["targets"], f.get("skipped")) for f in data["files"]] == [
        ("blob.bin", [], "binary")
    ]


def test_nothing_to_read_gets_the_base_turns(tmp_path: Path) -> None:
    done, data, outputs = run_diff(merged(tmp_path, {"uv.lock": b"a\n"}, {"uv.lock": b"b\n"}))
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    assert (data["reads"], outputs) == (0, "max_turns=40\n")


def test_the_turns_follow_the_reads_planned_up_to_the_cap(tmp_path: Path) -> None:
    # One added file of 600 lines of 100 bytes: three Reads of 200 lines, so 40 + 2 x 3 turns.
    big = (b"x" * 99 + b"\n") * 600
    done, data, outputs = run_diff(merged(tmp_path, {}, {"big.txt": big}))
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    assert (data["reads"], outputs) == (3, "max_turns=46\n")
    huge = {f"f{i}.txt": (b"y" * 99 + b"\n") * 800 for i in range(60)}
    done, _, outputs = run_diff(merged(tmp_path / "huge", {}, huge))
    assert done.returncode == 0, done.stdout + done.stderr
    assert outputs == "max_turns=400\n"


def test_each_target_lists_the_reads_that_cover_it(tmp_path: Path) -> None:
    """#274: a session left a long file at its first, capped Read. Each target lists consecutive
    Reads of at most DIFF_READ_CHUNK bytes that cover it, a longer line on its own."""
    lines_100 = (b"z" * 99 + b"\n") * 450
    one_long = b"a\n" + b"w" * (DIFF_READ_CHUNK * 2) + b"\nb"
    workspace = merged(tmp_path, {}, {"many.txt": lines_100, "long_line.txt": one_long})
    done, data, _ = run_diff(workspace)
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    plans = {t["path"]: t["reads"] for f in data["files"] for t in f["targets"]}
    assert plans["many.txt"] == [
        {"offset": 1, "limit": 200},
        {"offset": 201, "limit": 200},
        {"offset": 401, "limit": 50},
    ]
    assert plans["long_line.txt"] == [
        {"offset": 1, "limit": 1},
        {"offset": 2, "limit": 1},
        {"offset": 3, "limit": 1},
    ]
    assert data["reads"] == 6


def test_a_diff_larger_than_one_read_is_written_whole(tmp_path: Path) -> None:
    before = "".join(f"line {i}\n" for i in range(5000)).encode()
    after = "".join(f"line {i} changed\n" for i in range(5000)).encode()
    workspace = merged(tmp_path, {"long.txt": before}, {"long.txt": after})
    done, data, _ = run_diff(workspace)
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    written = (workspace / ".review-diff" / "long.txt.diff").read_bytes()
    assert written.count(b"\n+line ") == 5000
    assert written.count(b"\n-line ") == 5000


def test_a_planted_review_diff_is_refused(tmp_path: Path) -> None:
    workspace = merged(tmp_path, {}, {".review-diff/files.json": b'{"files": []}\n'})
    done, data, _ = run_diff(workspace)
    assert done.returncode == 1
    assert done.stdout.startswith("::error title=Diff not made::")
    assert data is None


def test_a_checkout_with_no_base_fails_saying_so(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    git(workspace, "init", "-q", "-b", "main")
    done, data, _ = run_diff(workspace)
    assert done.returncode == 1
    assert done.stdout.startswith("::error title=Diff not made::git diff exited with")
    assert data is None


# The model step: the variable checked before Claude starts (D6).
def run_model(tmp_path: Path, value: str | None) -> tuple[subprocess.CompletedProcess[str], str]:
    outputs = tmp_path / "outputs"
    outputs.write_text("", encoding="utf-8")
    env = {"GITHUB_OUTPUT": str(outputs)}
    if value is not None:
        env["MODEL"] = value
    done = run_step(model_step(review()), tmp_path, tmp_path, env)
    return done, outputs.read_text(encoding="utf-8")


@pytest.mark.parametrize("value", ["claude-sonnet-5-5", "claude-opus-5-5", "claude-x-4-5-20250929"])
def test_a_model_name_is_passed_on(tmp_path: Path, value: str) -> None:
    done, outputs = run_model(tmp_path, value)
    assert done.returncode == 0, done.stdout + done.stderr
    assert outputs == f"model={value}\n"


@pytest.mark.parametrize("value", [None, ""])
def test_an_unset_model_fails_naming_the_variable(tmp_path: Path, value: str | None) -> None:
    done, outputs = run_model(tmp_path, value)
    assert done.returncode == 1
    assert done.stdout.startswith(
        "::error title=Review model unknown::CLAUDE_REVIEW_MODEL isn't set."
    )
    assert outputs == ""


@pytest.mark.parametrize(
    "value",
    [
        "claude-x --allowedTools Bash",
        "claude-sonnet-5-5\n::error::forged",
        "--dangerously-skip-permissions",
        "claude-sonnet-5-5[1m]",
        "gpt-5",
    ],
)
def test_a_value_that_isn_t_a_model_name_fails_and_reaches_nothing(
    tmp_path: Path, value: str
) -> None:
    done, outputs = run_model(tmp_path, value)
    assert done.returncode == 1
    assert len(done.stdout.splitlines()) == 1, done.stdout
    assert "which isn't a model name" in done.stdout
    assert outputs == ""


# The coverage step, run on execution files shaped as the probe recorded (review-covers-the-diff
# design D3, Probe results): a Read is a tool_use block in an assistant message, its result a
# tool_result block in the next user message, each returned line numbered "<n>" and a tab.
def call(ident: str, name: str, given: dict[str, Any]) -> dict[str, Any]:
    block = {"type": "tool_use", "id": ident, "name": name, "input": given, "caller": {}}
    return {"type": "assistant", "message": {"content": [block]}}


def result(ident: str, text: str, *, error: bool = False) -> dict[str, Any]:
    block: dict[str, Any] = {"type": "tool_result", "tool_use_id": ident, "content": text}
    if error:
        block["is_error"] = True
    return {"type": "user", "message": {"content": [block]}}


class Session:
    """A workspace, the list the diff step left in RUNNER_TEMP, and the session's messages."""

    def __init__(self, tmp_path: Path, files: list[dict[str, Any]]) -> None:
        self.tmp_path = tmp_path
        self.workspace = tmp_path / "workspace"
        self.workspace.mkdir(parents=True)
        (tmp_path / "runner-temp").mkdir()
        listed = tmp_path / "runner-temp" / "review-files.json"
        listed.write_text(json.dumps({"files": files}), encoding="utf-8")
        self.messages: list[dict[str, Any]] = []
        self.count = 0

    def read(self, path: str, lines: range, *, arrow: bool = False, error: bool = False) -> None:
        self.count += 1
        ident = f"toolu_{self.count}"
        mark = "→" if arrow else "\t"
        text = "\n".join(f"{n}{mark}text {n}" for n in lines)
        self.messages += [
            call(ident, "Read", {"file_path": str(self.workspace / path)}),
            result(ident, "File does not exist." if error else text, error=error),
        ]

    def grep(self, pattern: str) -> None:
        self.count += 1
        ident = f"toolu_{self.count}"
        self.messages += [
            call(ident, "Grep", {"pattern": pattern, "path": str(self.workspace)}),
            result(ident, "1:found"),
        ]

    def finish(self, text: str = "Done.") -> None:
        self.messages.append({"type": "result", "subtype": "success", "result": text})

    def run(self, content: str | None = None) -> tuple[str, list[Any], str, str]:
        """The coverage and unread outputs, the run summary, and the log."""
        execution = self.tmp_path / "claude-execution-output.json"
        execution.write_text(
            json.dumps(self.messages) if content is None else content, encoding="utf-8"
        )
        outputs = self.tmp_path / "outputs"
        summary = self.tmp_path / "summary.md"
        outputs.write_text("", encoding="utf-8")
        env = {
            "EXECUTION_FILE": str(execution),
            "GITHUB_OUTPUT": str(outputs),
            "GITHUB_STEP_SUMMARY": str(summary),
        }
        done = run_step(coverage_step(review()), self.tmp_path, self.tmp_path, env)
        assert done.returncode == 0, done.stdout + done.stderr
        said = dict(line.split("=", 1) for line in outputs.read_text(encoding="utf-8").splitlines())
        return (
            said["coverage"],
            json.loads(said["unread"]),
            summary.read_text(encoding="utf-8"),
            done.stdout,
        )


def listed(path: str, status: str, *targets: tuple[str, int]) -> dict[str, Any]:
    return {
        "path": path,
        "status": status,
        "targets": [{"path": p, "lines": n, "bytes": n * 10} for p, n in targets],
    }


MODIFIED = listed("src/a.py", "modified", ("src/a.py", 30), (".review-diff/src/a.py.diff", 12))
ADDED = listed("src/b.py", "added", ("src/b.py", 2500))
SKIPPED = {"path": "uv.lock", "status": "modified", "skipped": "on the skip list", "targets": []}


def test_every_target_read_is_complete(tmp_path: Path) -> None:
    session = Session(tmp_path, [MODIFIED, ADDED, SKIPPED])
    session.read("src/a.py", range(1, 31))
    session.read(".review-diff/src/a.py.diff", range(1, 13))
    session.read("src/b.py", range(1, 2005))
    session.read("src/b.py", range(2001, 2502))
    session.finish()
    coverage, unread, summary, _ = session.run()
    assert (coverage, unread) == ("complete", [])
    assert "| src/a.py | modified | in full |" in summary
    assert "| uv.lock | on the skip list | nothing to read |" in summary


def test_two_reads_that_leave_a_gap_are_in_part(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED])
    session.read("src/b.py", range(1, 1001))
    session.read("src/b.py", range(1501, 2501))
    coverage, unread, _, out = session.run()
    assert (coverage, unread) == ("incomplete", [{"path": "src/b.py", "read": "in part"}])
    assert "  in part: src/b.py" in out.splitlines()


def test_a_modified_file_whose_diff_was_read_but_not_the_file_is_in_part(tmp_path: Path) -> None:
    session = Session(tmp_path, [MODIFIED])
    session.read(".review-diff/src/a.py.diff", range(1, 13))
    assert session.run()[:2] == ("incomplete", [{"path": "src/a.py", "read": "in part"}])


def test_a_read_that_failed_counts_for_nothing(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED])
    session.read("src/b.py", range(1, 2501), error=True)
    assert session.run()[:2] == ("incomplete", [{"path": "src/b.py", "read": "not read"}])


def test_the_earlier_arrow_numbering_counts_too(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED])
    session.read("src/b.py", range(1, 2501), arrow=True)
    assert session.run()[:2] == ("complete", [])


def test_an_unchanged_file_read_is_reported_not_counted(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED])
    session.read("src/caller.py", range(1, 2501))
    session.read(".review-threads.json", range(1, 5))
    coverage, unread, summary, _ = session.run()
    assert (coverage, unread) == ("incomplete", [{"path": "src/b.py", "read": "not read"}])
    assert "- Read src/caller.py, which the pull request didn't change" in summary
    assert ".review-threads.json" not in summary


def test_a_read_outside_the_workspace_counts_for_nothing(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED])
    session.read("../src/b.py", range(1, 2501))
    coverage, _, summary, _ = session.run()
    assert coverage == "incomplete"
    assert "../" not in summary


def test_searches_are_reported_and_a_hostile_one_stays_in_its_line(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED])
    session.read("src/b.py", range(1, 2501))
    session.grep("def resolve(")
    session.grep("x |\n## Approved <b>")
    coverage, _, summary, _ = session.run()
    assert coverage == "complete"
    assert "- Searched for def resolve\\(" in summary
    assert "- Searched for x \\| \\#\\# Approved \\<b\\>" in summary
    assert not any(line.startswith("## Approved") for line in summary.splitlines())


def test_no_search_is_reported_and_doesn_t_fail_the_coverage(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED])
    session.read("src/b.py", range(1, 2501))
    coverage, _, summary, _ = session.run()
    assert coverage == "complete"
    assert "- No search." in summary
    assert "- Read no file the pull request didn't change." in summary


def test_a_list_planted_in_the_workspace_is_ignored(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED])
    planted = session.workspace / ".review-diff" / "files.json"
    planted.parent.mkdir()
    planted.write_text(json.dumps({"files": []}), encoding="utf-8")
    assert session.run()[:2] == ("incomplete", [{"path": "src/b.py", "read": "not read"}])


@pytest.mark.parametrize("content", ["not json", '{"type": "result"}', ""])
def test_an_unreadable_record_counts_nothing_as_read(tmp_path: Path, content: str) -> None:
    session = Session(tmp_path, [MODIFIED, SKIPPED])
    coverage, unread, summary, _ = session.run(content)
    assert (coverage, unread) == ("unknown", [{"path": "src/a.py", "read": "not read"}])
    assert "Coverage isn't known" in summary


def test_no_execution_file_counts_nothing_as_read(tmp_path: Path) -> None:
    Session(tmp_path, [MODIFIED])
    outputs = tmp_path / "outputs"
    outputs.write_text("", encoding="utf-8")
    env = {"EXECUTION_FILE": "", "GITHUB_OUTPUT": str(outputs)}
    done = run_step(coverage_step(review()), tmp_path, tmp_path, env)
    assert done.returncode == 0, done.stdout + done.stderr
    assert outputs.read_text(encoding="utf-8") == (
        'coverage=unknown\nunread=[{"path":"src/a.py","read":"not read"}]\n'
    )


def test_a_path_that_holds_a_workflow_command_stays_inside_its_line(tmp_path: Path) -> None:
    hostile = listed("x\n::error::forged", "added", ("x\n::error::forged", 3))
    session = Session(tmp_path, [hostile])
    _, unread, _, out = session.run()
    assert unread == [{"path": "x\n::error::forged", "read": "not read"}]
    assert not any(line.startswith("::") for line in out.splitlines()), out


# The check judges what the review read (review-covers-the-diff design D4).
@pytest.mark.parametrize(
    ("coverage", "said"),
    [
        ("incomplete", "didn't read every changed file in full"),
        ("unknown", "couldn't be measured, so nothing counts as read"),
        ("", "wasn't measured"),
        ("complete-ish", "wasn't measured"),
    ],
)
def test_a_review_that_didn_t_read_everything_fails_naming_the_files(
    tmp_path: Path, coverage: str, said: str
) -> None:
    unread = [{"path": "src/a.py", "read": "in part"}, {"path": "src/b.py", "read": "not read"}]
    done = run_completed(tmp_path, COVERAGE=coverage, UNREAD=json.dumps(unread))
    assert done.returncode == 1
    assert done.stdout.startswith("::error title=Review didn't read the code::")
    assert f"it {said}: src/a.py (in part), src/b.py (not read)." in done.stdout
    assert "gh run rerun 41258918187" in done.stdout


def test_an_unread_list_that_isn_t_one_still_fails(tmp_path: Path) -> None:
    done = run_completed(tmp_path, COVERAGE="incomplete", UNREAD="not json")
    assert done.returncode == 1
    assert ": files unnamed." in done.stdout


def test_more_than_fifty_unread_files_are_cut_short(tmp_path: Path) -> None:
    unread = [{"path": f"f{i}.py", "read": "not read"} for i in range(60)]
    done = run_completed(tmp_path, COVERAGE="incomplete", UNREAD=json.dumps(unread))
    assert done.returncode == 1
    assert "f49.py (not read), and 10 more." in done.stdout
    assert "f50.py" not in done.stdout


def test_a_hostile_unread_path_stays_inside_the_one_error(tmp_path: Path) -> None:
    unread = [{"path": "x\n::notice::forged", "read": "not read"}]
    done = run_completed(tmp_path, COVERAGE="incomplete", UNREAD=json.dumps(unread))
    assert done.returncode == 1
    assert len(done.stdout.splitlines()) == 1, done.stdout


def test_a_bot_s_pull_request_passes_whatever_the_coverage(tmp_path: Path) -> None:
    done = run_completed(tmp_path, AUTHOR_TYPE="Bot", REVIEW="skipped", COVERAGE="")
    assert done.returncode == 0, done.stdout


def test_a_review_that_says_it_didn_t_read_the_code_fails_the_check(tmp_path: Path) -> None:
    """#268: troupe#283's reviews said "not checked" for its code and still passed. A session
    that reads only the task list, and says so in its result, leaves the check failed, naming
    the files, whatever its summary says."""
    files = [
        MODIFIED,
        ADDED,
        listed(
            "openspec/changes/x/tasks.md",
            "modified",
            ("openspec/changes/x/tasks.md", 20),
            (".review-diff/openspec/changes/x/tasks.md.diff", 8),
        ),
    ]
    session = Session(tmp_path / "session", files)
    session.read("openspec/changes/x/tasks.md", range(1, 21))
    session.read(".review-diff/openspec/changes/x/tasks.md.diff", range(1, 9))
    session.finish(
        "No must-fix found. **Not checked:** the diff is about 9,000 lines, and I read the task "
        "list, the file list and the task/code pairing. I did not read the implementation line "
        "by line."
    )
    coverage, unread, _, _ = session.run()
    assert coverage == "incomplete"
    done = run_completed(tmp_path, COVERAGE=coverage, UNREAD=json.dumps(unread))
    assert done.returncode == 1
    assert "src/a.py (not read), src/b.py (not read)." in done.stdout
    assert "tasks.md" not in done.stdout
