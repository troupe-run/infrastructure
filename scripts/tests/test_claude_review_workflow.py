"""claude-review.yml reviews each member's pull request and can't change the repository (spec:
pr-review; claude-pr-review design D1 to D4, D7, D8; review-denials-and-guide design D1 to D4;
review-findings-by-severity design D1 to D4; review-completed-check design D2 to D5;
review-covers-the-diff design D2 to D7; review-splits-large-prs design D1 to D11).

GitHub evaluates the workflow, so these tests pin what it's given: when it runs and what it
skips, what each token may do, which credentials reach the action, which tools Claude has, what
it checks out, and its steps of its own. The plan job checks the model and plans what each
session reads. Each session (one a part, in up to three rounds that share one list of steps)
checks its list, reads the review conversations, runs Claude, names the tool calls Claude was
refused, measures what it read and keeps what Claude named. Each follow-up planner gathers what
the sessions read and plans the next round. The report job gathers again, resolves and re-tiers
what Claude named, and posts the review's one summary. The required check says whether the
review of the head completed and read every changed source and test file."""

import ast
import copy
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from collections.abc import Callable, Mapping
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
# The run's own token only checks out the code and reads the run's artifacts (design D1). No
# id-token: without it the action can't swap OIDC for a Claude App token that writes contents.
PERMISSIONS = {"contents": "read"}
# Every write is made with the review App's token, minted for this repository with exactly these.
MINTER = "actions/create-github-app-token"
CHECKOUT = "actions/checkout"
UPLOAD = "actions/upload-artifact"
DOWNLOAD = "actions/download-artifact"
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
# review's own comments starts, mustn't join a group and cancel the review that posted it
# (review-judge-reply-on-post design D3). One group per job; a session's per round and part, since
# the sessions of one matrix can't share one (review-splits-large-prs design D8).
PR = "${{ github.event.pull_request.number }}"
GROUPS = {
    "plan": f"claude-review-{PR}-plan",
    "review": f"claude-review-{PR}-${{{{ matrix.round }}}}-${{{{ matrix.part }}}}",
    "follow-1": f"claude-review-{PR}-follow-1",
    "review-2": f"claude-review-{PR}-${{{{ matrix.round }}}}-${{{{ matrix.part }}}}",
    "follow-2": f"claude-review-{PR}-follow-2",
    "review-3": f"claude-review-{PR}-${{{{ matrix.round }}}}-${{{{ matrix.part }}}}",
    "resolve": f"claude-review-{PR}-report",
}
JOBS = {"gate", "plan", "review", "follow-1", "review-2", "follow-2", "review-3", "resolve",
        "completed"}  # fmt: skip
SESSIONS = ("review", "review-2", "review-3")
PLANNERS = ("follow-1", "follow-2")
# Each job's needs and when it runs (review-splits-large-prs design D4, D10): a session round runs
# only when its planner listed parts; the report after the last round that ran.
NEEDS = {
    "plan": "gate",
    "review": "plan",
    "follow-1": ["plan", "review"],
    "review-2": ["plan", "follow-1"],
    "follow-2": ["plan", "follow-1", "review-2"],
    "review-3": ["plan", "follow-2"],
    "resolve": ["plan", "review", "follow-1", "review-2", "follow-2", "review-3"],
}
IFS = {
    "plan": "needs.gate.outputs.review == 'true'",
    "review": "needs.plan.result == 'success'",
    "follow-1": "needs.review.result == 'success'",
    "review-2": "needs.follow-1.result == 'success' && needs.follow-1.outputs.parts != '[]'",
    "follow-2": "needs.review-2.result == 'success'",
    "review-3": "needs.follow-2.result == 'success' && needs.follow-2.outputs.parts != '[]'",
    "resolve": (
        "!cancelled() && needs.follow-1.result == 'success' && "
        "(needs.follow-1.outputs.parts == '[]' || (needs.review-2.result == 'success' && "
        "needs.follow-2.result == 'success' && (needs.follow-2.outputs.parts == '[]' || "
        "needs.review-3.result == 'success')))"
    ),
}
MATRICES = {
    "review": "${{ fromJSON(needs.plan.outputs.parts) }}",
    "review-2": "${{ fromJSON(needs.follow-1.outputs.parts) }}",
    "review-3": "${{ fromJSON(needs.follow-2.outputs.parts) }}",
}
NEXT_ROUNDS = {"follow-1": "2", "follow-2": "3"}
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
# Read the pull request and the checkout, comment inline, nothing else (design D4). No Edit,
# Write, git or `gh pr review`, which is what keeps the review advisory, and no `gh pr comment`:
# the report job posts the review's one summary (review-splits-large-prs design D6).
TOOLS = {
    "mcp__github_inline_comment__create_inline_comment",
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
# The plan job's checkout keeps the merge commit's parents, so the plan step can diff against the
# base's tip (review-covers-the-diff design D2). A session's checkout needs none.
PLAN_CHECKOUT = {"fetch-depth": 2, "persist-credentials": False}
SESSION_CHECKOUT = {"persist-credentials": False}
# The steps of our own, each pinned by hash, so changing one changes this test in the same diff.
MODEL_NAME = "Check the review's model"
MODEL = {"id": "model", "shell": "python3 {0}", "env": {"MODEL": "${{ vars.CLAUDE_REVIEW_MODEL }}"}}
MODEL_SHA256 = "1566ed73c892e39e9531b83bb147ed5778ed215c939496f13718ae7e7b3424a2"
PLAN_NAME = "Plan what each session reads"
PLAN = {"id": "plan", "shell": "python3 {0}"}
PLAN_SHA256 = "21a6a5d21940357fece81bacd035082a31701842820b9c077ed24b9802ee3c9c"
SESSION_NAME = "Choose this session's files"
SESSION = {
    "id": "session",
    "shell": "python3 {0}",
    "env": {
        "ROUND": "${{ matrix.round }}",
        "PART": "${{ matrix.part }}",
        "OF": "${{ matrix.of }}",
        "FILES_SHA256": "${{ matrix.files_sha256 }}",
        "ROUND_SHA256": "${{ matrix.round_sha256 }}",
    },
}
SESSION_SHA256 = "ae5d98ed215d15aa85b973061307be90c6d0b4b75edc39d94b9c554caf3db9c6"
# The review App's token, the only one the conversation steps hold (design D3, D4).
STEP_ENV = {
    "GH_TOKEN": "${{ steps.app-token.outputs.token }}",
    "REPOSITORY": "${{ github.repository }}",
    "NUMBER": "${{ github.event.pull_request.number }}",
}
# Before Claude: the pull request's review conversations, for Claude and for the resolving step.
SNAPSHOT_NAME = "Read the pull request's review conversations"
SNAPSHOT = {"shell": "python3 {0}", "env": STEP_ENV}
SNAPSHOT_SHA256 = "881c6b51fbc892399d33e02bcfc14f93611d0f293eab577dd415b1bd6e5757c9"
# After Claude: each tool call it was refused, and nothing else of the session (design D1, D2).
REPORT_NAME = "Name the tool calls Claude was refused"
REPORT = {
    "if": "${{ !cancelled() }}",
    "continue-on-error": True,
    "shell": "python3 {0}",
    "env": {"EXECUTION_FILE": "${{ steps.review.outputs.execution_file }}"},
}
REPORT_SHA256 = "0226ac402c3987ad33791bf8b0176f07585e3f5059fab9541c473e56ccf9fcf6"
# After Claude: what the session read, from the execution file only, never its structured output
# or its summary (review-covers-the-diff design D3). It can't fail the job; a record it didn't
# make leaves its part's files unread (review-splits-large-prs design D4).
MEASURE_NAME = "Measure what the session read"
MEASURE = {
    "if": "${{ !cancelled() }}",
    "continue-on-error": True,
    "shell": "python3 {0}",
    "env": {
        "EXECUTION_FILE": "${{ steps.review.outputs.execution_file }}",
        # The session's own outcome: a lead that failed fails the check (#299's review).
        "OUTCOME": "${{ steps.review.outcome }}",
        "ROUND": "${{ matrix.round }}",
        "PART": "${{ matrix.part }}",
    },
}
MEASURE_SHA256 = "550a3e167f200dc1be6f3864a62b438986ce9d904fcf3d123ceff959601943ab"
# After Claude: its summary and what it named, kept apart from the measurement (D6).
ANSWER_NAME = "Keep what Claude named"
ANSWER = {
    "if": "${{ !cancelled() }}",
    "shell": "python3 {0}",
    "env": {
        "STRUCTURED_OUTPUT": "${{ steps.review.outputs.structured_output }}",
        "ROUND": "${{ matrix.round }}",
        "PART": "${{ matrix.part }}",
    },
}
ANSWER_SHA256 = "815aaab9d79a0f0870bc3aa850f069eae46423fc60c5f1a96272e39328ff18ae"
# What the sessions read together, in each planner and in the report job: one script (D4).
GATHER_NAME = "Gather what the sessions read"
GATHER = {"id": "gather", "shell": "python3 {0}"}
GATHER_SHA256 = "52a06084aa8757969d851243fbb985d55646ffefbf34e868928784c012c8610f"
# Resolve and re-tier what Claude names, checked against conversations read again in the report
# job, and only on a file of that session's list (design D4, D4a; review-splits-large-prs D7).
RESOLVER_NAME = "Resolve and re-tier what Claude named"
RESOLVER = {"shell": "python3 {0}", "env": STEP_ENV}
RESOLVER_SHA256 = "7a3c5d59d692083eb11c4239d0ede333716419301cce5f825f874550b560e9f7"
# The review's one top-level comment (review-splits-large-prs design D6).
POST_NAME = "Post the review's summary"
POST = {
    "shell": "python3 {0}",
    "env": {**STEP_ENV, "HEAD_SHA": "${{ github.event.pull_request.head.sha }}"},
}
POST_SHA256 = "288bbcc9b97b51ee5b1200de0038c91f17d323689a587d376a1f21aa97899631"
# The artifacts that carry the plan and the records between jobs, written only by these steps
# (review-splits-large-prs design D4).
PLAN_UPLOADS: list[dict[str, Any]] = [
    {"name": "review-plan", "path": ".review-diff/", "include-hidden-files": True,
     "if-no-files-found": "error", "retention-days": 1},
    {"name": "review-round-1", "path": ".review-diff/round-1.json",
     "include-hidden-files": True, "if-no-files-found": "error", "retention-days": 1},
]  # fmt: skip
SESSION_DOWNLOADS: list[dict[str, Any]] = [
    {"name": "review-plan", "path": ".review-diff"},
    {"name": "review-round-${{ matrix.round }}", "path": ".review-diff"},
]
RECORD_UPLOAD = {
    "name": "review-record-${{ matrix.round }}-${{ matrix.part }}",
    "path": "${{ runner.temp }}/review/records/",
    "if-no-files-found": "error",
    "retention-days": 1,
}
GATHER_DOWNLOADS: list[dict[str, Any]] = [
    {"name": "review-plan", "path": "${{ runner.temp }}/review"},
    {"pattern": "review-round-*", "merge-multiple": True, "path": "${{ runner.temp }}/review"},
    {"pattern": "review-record-*", "merge-multiple": True,
     "path": "${{ runner.temp }}/review/records"},
]  # fmt: skip
ROUND_UPLOAD = {
    "name": "review-round-${{ env.NEXT_ROUND }}",
    "path": "${{ runner.temp }}/next/round-${{ env.NEXT_ROUND }}.json",
    "if-no-files-found": "error",
    "retention-days": 1,
}
ROUND_UPLOAD_IF = "steps.gather.outputs.parts != '[]'"
# --max-turns is the session's own, from its matrix entry, never a fixed number (review-covers-the-
# diff design D5; review-splits-large-prs design D11). --model is the plan job's checked variable
# (D6). GitHub substitutes both before the action reads claude_args.
MAX_TURNS = "${{ matrix.max_turns }}"
MODEL_ARG = "${{ needs.plan.outputs.model }}"
# What the prompt must say about reading (D7, D7a; review-splits-large-prs design D5): the
# session's list, reading every target in full, and the uses of what changed. And it mustn't send
# the review to `gh pr diff` for the diff.
PROMPT_READS = [
    "Read `.review-diff/session.json` first",
    "`read` is your list, the files you must read",
    "If your role is `lead`, you also do checks 2 to 5 below",
    "If your role is `part`, other sessions read the rest of the pull request",
    "If your role is `follow-up`, an earlier session didn't read the files on your list",
    "Read every target in full with Read",
    "search the checkout for its uses with Grep",
    "a review that didn't read them all isn't a clean review",
    "make every one, as Read with the target's `path` and that `offset` and `limit`",
    "don't take a file's diff for the file",
    # Its summary names what it didn't read; what was measured is in the report (review-coverage-
    # floor design D5).
    "name each file on your list you didn't read in full",
    # One summary for the review, from the report job (review-splits-large-prs design D6).
    "Don't post a top-level comment",
    "Give yours in the structured output's `summary`",
]
PROMPT_NOT = "Read the diff with"
# Long enough for MAX_TURNS' cap (D5).
REVIEW_TIMEOUT = 90
# The report job's outputs, which the check judges (review-splits-large-prs design D9).
RESOLVE_OUTPUTS = {
    "coverage": "${{ steps.gather.outputs.coverage }}",
    "code": "${{ steps.gather.outputs.code }}",
    "unread": "${{ steps.gather.outputs.unread }}",
    "unmeasured": "${{ steps.gather.outputs.unmeasured }}",
}
PLAN_OUTPUTS = {
    "parts": "${{ steps.plan.outputs.parts }}",
    "model": "${{ steps.model.outputs.model }}",
}
PLANNER_OUTPUTS = {"parts": "${{ steps.gather.outputs.parts }}"}
RESOLVE_TOKEN_INPUTS = {
    **TOKEN_INPUTS,
    "permission-contents": "write",
}
# The gate: before the review, outside every concurrency group, with D2's skip, it decides whether
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
# The required check that the review of the head completed (review-completed-check design D2 to
# D5): after every other job, whatever became of them, on pull request events only, since GitHub
# ignores a comment's run for a pull request (Probe results). No token, no secret, no checkout,
# and outside every concurrency group, so a newer review can't cancel it.
COMPLETED_NAME = "claude review completed"
COMPLETED_NEEDS = ["gate", "plan", "review", "follow-1", "review-2", "follow-2", "review-3",
                   "resolve"]  # fmt: skip
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
        "PLAN": "${{ needs.plan.result }}",
        "REVIEW": "${{ needs.review.result }}",
        "FOLLOW_1": "${{ needs.follow-1.result }}",
        "FOLLOW_1_PARTS": "${{ needs.follow-1.outputs.parts }}",
        "REVIEW_2": "${{ needs.review-2.result }}",
        "FOLLOW_2": "${{ needs.follow-2.result }}",
        "FOLLOW_2_PARTS": "${{ needs.follow-2.outputs.parts }}",
        "REVIEW_3": "${{ needs.review-3.result }}",
        "RESOLVE": "${{ needs.resolve.result }}",
        # What the sessions read together (review-splits-large-prs design D9).
        "COVERAGE": "${{ needs.resolve.outputs.coverage }}",
        "CODE": "${{ needs.resolve.outputs.code }}",
        "UNREAD": "${{ needs.resolve.outputs.unread }}",
        "UNMEASURED": "${{ needs.resolve.outputs.unmeasured }}",
    },
}
COMPLETED_SHA256 = "5a5583f59cca88275099a99086dcb1be8f65e20c72efd93693f6eef85871b561"
# What Claude returns, and all the report job reads from it (design D4; review-splits-large-prs
# design D6).
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "resolve", "retier"],
    "properties": {
        "summary": {"type": "string"},
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
    script = str(step.get("run", ""))
    if "${{" in script:
        found.append(f"{what}'s script interpolates an expression; use its env")
    if hashlib.sha256(script.encode()).hexdigest() != sha256:
        found.append(f"{what}'s script isn't the one this test pins")
    return found


def label(step: dict[str, Any]) -> str:
    """What a step is, for comparing a job's steps with the order it needs."""
    uses = str(step.get("uses", ""))
    if uses.startswith(f"{CHECKOUT}@"):
        return "guide checkout" if (step.get("with") or {}).get("repository") else "checkout"
    for prefix, said in ((MINTER, "token"), (UPLOAD, "upload"), (DOWNLOAD, "download")):
        if uses.startswith(f"{prefix}@"):
            return said
    if uses.startswith(f"{ACTION}@"):
        return "action"
    return str(step.get("name") or uses or step.get("run", "")[:40])


def used_step_problems(
    step: dict[str, Any], given: dict[str, Any], what: str, condition: str | None = None
) -> list[str]:
    """An action's step: pinned, given exactly these inputs, and run only on this condition."""
    found = []
    if not PINNED.match(str(step.get("uses"))):
        found.append(f"{step.get('uses')!r} isn't pinned to a full commit SHA")
    if (step.get("with") or {}) != given:
        found.append(f"{what} is given {step.get('with')!r}, not {given!r}")
    if step.get("if") != condition:
        found.append(f"{what} runs when {step.get('if')!r}, not {condition!r}")
    others = sorted(set(step) - {"uses", "with", "if", "id", "name"})
    if others:
        found.append(f"{what} also has {others}")
    return found


def token_problems(step: dict[str, Any], expected: dict[str, Any], what: str) -> list[str]:
    found = []
    if not PINNED.match(str(step.get("uses"))):
        found.append(f"{step.get('uses')!r} isn't pinned to a full commit SHA")
    if step.get("id") != "app-token":
        found.append(f"{what}'s token step's id is {step.get('id')!r}, not app-token")
    given = dict(step.get("with") or {})
    client_id = str(given.pop("client-id", ""))
    if not REVIEW_APP_CLIENT_ID.match(client_id):
        found.append(f"{what}'s client ID is {client_id!r}, not one written here")
    if given != expected:
        found.append(f"{what}'s token is minted with {given!r}, not {expected!r}")
    return found


def job_problems(name: str, job: dict[str, Any], permissions: object = PERMISSIONS) -> list[str]:
    """What every job of the review shares: its needs, its condition, its token, its group, no
    environment, and a timeout."""
    found = []
    if name in NEEDS and job.get("needs") != NEEDS[name]:
        found.append(f"{name} needs {job.get('needs')!r}, not {NEEDS[name]!r}")
    if name in IFS and job.get("if") != IFS[name]:
        found.append(f"{name} runs when {job.get('if')!r}, not {IFS[name]!r}")
    if job.get("permissions") != permissions:
        found.append(
            f"{name}'s GITHUB_TOKEN permissions are {job.get('permissions')!r}, not {permissions!r}"
        )
    if "environment" in job:
        found.append(f"{name} runs in environment {job['environment']!r}; it needs none")
    if not isinstance(job.get("timeout-minutes"), int):
        found.append(f"{name} has no timeout-minutes")
    if name in GROUPS:
        wanted = {"group": GROUPS[name], "cancel-in-progress": True}
        if job.get("concurrency") != wanted:
            found.append(
                f"{name}'s concurrency is {job.get('concurrency')!r}, not {wanted!r}: one run of "
                "it per pull request, the newest cancelling the last"
            )
    elif "concurrency" in job:
        found.append(f"{name} is in a concurrency group, so a newer run could cancel it")
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
    found += job_problems("gate", job)
    if job.get("outputs") != GATE_OUTPUTS:
        found.append(f"gate's outputs are {job.get('outputs')!r}, not {GATE_OUTPUTS!r}")
    steps = job.get("steps") or []
    shape = [label(s) for s in steps]
    if shape != ["token", GATE_NAME]:
        return [*found, f"gate's steps are {shape!r}, not the token and {GATE_NAME!r}"]
    found += token_problems(steps[0], GATE_TOKEN_INPUTS, "gate")
    found += own_step_problems(steps[1], GATE, GATE_SHA256, repr(GATE_NAME))
    return found


def plan_job_problems(job: dict[str, Any]) -> list[str]:
    """The plan job: the pull request's checkout with its base, the model checked, the plan made,
    and the plan uploaded; no token, no Claude (review-splits-large-prs design D4)."""
    found = job_problems("plan", job)
    if job.get("outputs") != PLAN_OUTPUTS:
        found.append(f"plan's outputs are {job.get('outputs')!r}, not {PLAN_OUTPUTS!r}")
    steps = job.get("steps") or []
    shape = [label(s) for s in steps]
    wanted = ["checkout", MODEL_NAME, PLAN_NAME, "upload", "upload"]
    if shape != wanted:
        return [*found, f"plan's steps are {shape!r}, not {wanted!r}"]
    checkout, model, plan, *uploads = steps
    found += used_step_problems(checkout, PLAN_CHECKOUT, "plan's checkout")
    found += own_step_problems(model, MODEL, MODEL_SHA256, repr(MODEL_NAME))
    found += own_step_problems(plan, PLAN, PLAN_SHA256, repr(PLAN_NAME))
    for step, given in zip(uploads, PLAN_UPLOADS, strict=True):
        found += used_step_problems(step, given, f"plan's upload of {given['name']}")
    return found


def session_job_problems(name: str, job: dict[str, Any]) -> list[str]:
    """A round of sessions: a matrix of the planner's parts, the session's own steps in order, and
    the action given only what it needs (design D1 to D9; review-splits-large-prs design D4 to
    D8, D11)."""
    found = job_problems(name, job)
    if "outputs" in job:
        found.append(f"{name} has outputs {job['outputs']!r}; its records are artifacts")
    wanted = {"fail-fast": False, "matrix": {"include": MATRICES[name]}}
    if job.get("strategy") != wanted:
        found.append(f"{name}'s strategy is {job.get('strategy')!r}, not {wanted!r}")
    if job.get("timeout-minutes") != REVIEW_TIMEOUT:
        found.append(
            f"{name}'s timeout-minutes is {job.get('timeout-minutes')}, not {REVIEW_TIMEOUT}, "
            "which the turn cap needs"
        )
    steps = job.get("steps") or []
    shape = [label(s) for s in steps]
    order = ["checkout", "guide checkout", "download", "download", SESSION_NAME, "token",
             SNAPSHOT_NAME, "action", REPORT_NAME, MEASURE_NAME, ANSWER_NAME, "upload"]  # fmt: skip
    if shape != order:
        return [*found, f"{name}'s steps are {shape!r}, not {order!r}"]
    (checkout, guide_, plan, round_, session, token_, snapshot_, action_, report_, measure,
     answer, upload) = steps  # fmt: skip
    found += used_step_problems(checkout, SESSION_CHECKOUT, f"{name}'s checkout")
    found += used_step_problems(guide_, GUIDE, "the guide's checkout")
    for step, given in zip((plan, round_), SESSION_DOWNLOADS, strict=True):
        found += used_step_problems(step, given, f"{name}'s download of {given['name']}")
    found += own_step_problems(session, SESSION, SESSION_SHA256, repr(SESSION_NAME))
    found += token_problems(token_, TOKEN_INPUTS, name)
    found += own_step_problems(snapshot_, SNAPSHOT, SNAPSHOT_SHA256, repr(SNAPSHOT_NAME))
    found += own_step_problems(report_, REPORT, REPORT_SHA256, "the denials report")
    found += own_step_problems(measure, MEASURE, MEASURE_SHA256, repr(MEASURE_NAME))
    found += own_step_problems(answer, ANSWER, ANSWER_SHA256, repr(ANSWER_NAME))
    found += used_step_problems(upload, RECORD_UPLOAD, f"{name}'s record", "${{ !cancelled() }}")
    found += action_problems(action_)
    return found


def action_problems(step: dict[str, Any]) -> list[str]:
    found = []
    if not PINNED.match(str(step.get("uses"))):
        found.append(f"{step.get('uses')!r} isn't pinned to a full commit SHA")
    if step.get("id") != "review":
        found.append(f"the action's step id is {step.get('id')!r}, not review")
    # A session that runs out of turns leaves its files to the follow-up (D10).
    if step.get("continue-on-error") is not True:
        found.append("the action can fail its job, so a session that stops leaves no record")
    others = sorted(set(step) - {"uses", "id", "with", "continue-on-error", "name"})
    if others:
        found.append(f"the action's step also has {others}")
    inputs = step.get("with") or {}
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
    if not prompt.strip():
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
        found.append(f"--max-turns isn't {MAX_TURNS}, the turns the session's part needs (D11)")
    if f"--model {MODEL_ARG}" not in str(inputs.get("claude_args", "")):
        found.append(f"--model isn't {MODEL_ARG}, the checked repository variable (D6)")
    return found


def planner_job_problems(name: str, job: dict[str, Any]) -> list[str]:
    """A follow-up planner: the plan, the rounds and the records downloaded, gathered, and the
    next round's list uploaded when it has parts; no token, no checkout, no Claude
    (review-splits-large-prs design D4, D10)."""
    found = job_problems(name, job)
    if job.get("outputs") != PLANNER_OUTPUTS:
        found.append(f"{name}'s outputs are {job.get('outputs')!r}, not {PLANNER_OUTPUTS!r}")
    if job.get("env") != {"NEXT_ROUND": NEXT_ROUNDS[name]}:
        found.append(f"{name}'s env is {job.get('env')!r}, not round {NEXT_ROUNDS[name]}'s")
    steps = job.get("steps") or []
    shape = [label(s) for s in steps]
    wanted = ["download", "download", "download", GATHER_NAME, "upload"]
    if shape != wanted:
        return [*found, f"{name}'s steps are {shape!r}, not {wanted!r}"]
    *downloads, gather_, upload = steps
    for step, given in zip(downloads, GATHER_DOWNLOADS, strict=True):
        found += used_step_problems(step, given, f"{name}'s download")
    found += own_step_problems(gather_, GATHER, GATHER_SHA256, f"{name}'s {GATHER_NAME!r}")
    found += used_step_problems(upload, ROUND_UPLOAD, f"{name}'s upload", ROUND_UPLOAD_IF)
    return found


def resolve_job_problems(job: dict[str, Any]) -> list[str]:
    """The report job: after the last round, minting the write token, reading the conversations
    again, gathering what every session read, then resolving and posting the one summary; no
    checkout, no Claude, nothing else (design D4a; review-splits-large-prs design D6, D7, D9)."""
    found = job_problems("resolve", job)
    if job.get("outputs") != RESOLVE_OUTPUTS:
        found.append(f"resolve's outputs are {job.get('outputs')!r}, not {RESOLVE_OUTPUTS!r}")
    steps = job.get("steps") or []
    shape = [label(s) for s in steps]
    wanted = ["token", SNAPSHOT_NAME, "download", "download", "download", GATHER_NAME,
              RESOLVER_NAME, POST_NAME]  # fmt: skip
    if shape != wanted:
        return [*found, f"resolve's steps are {shape!r}, not {wanted!r}, in that order"]
    minted, read, *rest = steps
    downloads, (gather_, resolving, posting) = rest[:3], rest[3:]
    found += token_problems(minted, RESOLVE_TOKEN_INPUTS, "resolve")
    found += own_step_problems(read, SNAPSHOT, SNAPSHOT_SHA256, f"resolve's {SNAPSHOT_NAME!r}")
    for step, given in zip(downloads, GATHER_DOWNLOADS, strict=True):
        found += used_step_problems(step, given, "resolve's download")
    found += own_step_problems(gather_, GATHER, GATHER_SHA256, f"resolve's {GATHER_NAME!r}")
    found += own_step_problems(resolving, RESOLVER, RESOLVER_SHA256, repr(RESOLVER_NAME))
    found += own_step_problems(posting, POST, POST_SHA256, repr(POST_NAME))
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
    found += job_problems("completed", job, permissions={})
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
    if "concurrency" in workflow:
        found.append(
            "its concurrency group is at the workflow level, where a run whose review is skipped "
            "joins it and cancels a running review"
        )
    jobs = workflow.get("jobs") or {}
    if set(jobs) != JOBS:
        return [*found, f"its jobs are {sorted(jobs)}, not {sorted(JOBS)}"]
    found += gate_job_problems(jobs["gate"])
    found += plan_job_problems(jobs["plan"])
    for name in SESSIONS:
        found += session_job_problems(name, jobs[name])
    # One list of steps for every round, so a follow-up session is a session (D10).
    for name in SESSIONS[1:]:
        if jobs[name].get("steps") != jobs["review"].get("steps"):
            found.append(f"{name}'s steps aren't the first round's")
    for name in PLANNERS:
        found += planner_job_problems(name, jobs[name])
    found += resolve_job_problems(jobs["resolve"])
    found += completed_job_problems(jobs["completed"])
    return found


def test_the_workflow_is_as_designed() -> None:
    assert problems(review()) == []


def test_it_starts_with_its_source() -> None:
    first = REVIEW.read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("# Source: troupe-run/infrastructure."), first


def step_named(w: dict[str, Any], job_name: str, name: str) -> dict[str, Any]:
    step = next(s for s in w["jobs"][job_name]["steps"] if label(s) == name)
    return step  # type: ignore[no-any-return]


def job(w: dict[str, Any]) -> dict[str, Any]:
    return w["jobs"]["review"]  # type: ignore[no-any-return]


def plan_job(w: dict[str, Any]) -> dict[str, Any]:
    return w["jobs"]["plan"]  # type: ignore[no-any-return]


def gate_job(w: dict[str, Any]) -> dict[str, Any]:
    return w["jobs"]["gate"]  # type: ignore[no-any-return]


def gate(w: dict[str, Any]) -> dict[str, Any]:
    return step_named(w, "gate", GATE_NAME)


def gate_token(w: dict[str, Any]) -> dict[str, Any]:
    return gate_job(w)["steps"][0]  # type: ignore[no-any-return]


def action_step(w: dict[str, Any]) -> dict[str, Any]:
    return step_named(w, "review", "action")


def action(w: dict[str, Any]) -> dict[str, Any]:
    return action_step(w)["with"]  # type: ignore[no-any-return]


def report(w: dict[str, Any]) -> dict[str, Any]:
    return step_named(w, "review", REPORT_NAME)


def guide(w: dict[str, Any]) -> dict[str, Any]:
    return step_named(w, "review", "guide checkout")["with"]  # type: ignore[no-any-return]


def move(w: dict[str, Any], step: dict[str, Any], to: int, job_name: str = "review") -> None:
    steps = w["jobs"][job_name]["steps"]
    steps.insert(to, steps.pop(steps.index(step)))


def snapshot(w: dict[str, Any]) -> dict[str, Any]:
    return step_named(w, "review", SNAPSHOT_NAME)


def plan_step(w: dict[str, Any]) -> dict[str, Any]:
    return step_named(w, "plan", PLAN_NAME)


def model_step(w: dict[str, Any]) -> dict[str, Any]:
    return step_named(w, "plan", MODEL_NAME)


def session_step(w: dict[str, Any]) -> dict[str, Any]:
    return step_named(w, "review", SESSION_NAME)


def measure_step(w: dict[str, Any]) -> dict[str, Any]:
    return step_named(w, "review", MEASURE_NAME)


def answer_step(w: dict[str, Any]) -> dict[str, Any]:
    return step_named(w, "review", ANSWER_NAME)


def gather_step(w: dict[str, Any], job_name: str = "resolve") -> dict[str, Any]:
    return step_named(w, job_name, GATHER_NAME)


def plan_script(w: dict[str, Any], old: str, new: str) -> None:
    assert old in str(plan_step(w)["run"]), old
    plan_step(w)["run"] = str(plan_step(w)["run"]).replace(old, new)


def script(step: dict[str, Any], old: str, new: str) -> None:
    assert old in str(step["run"]), old
    step["run"] = str(step["run"]).replace(old, new)


def resolve_job(w: dict[str, Any]) -> dict[str, Any]:
    return w["jobs"]["resolve"]  # type: ignore[no-any-return]


def resolver(w: dict[str, Any]) -> dict[str, Any]:
    return step_named(w, "resolve", RESOLVER_NAME)


def poster(w: dict[str, Any]) -> dict[str, Any]:
    return step_named(w, "resolve", POST_NAME)


def resolve_token(w: dict[str, Any]) -> dict[str, Any]:
    return resolve_job(w)["steps"][0]  # type: ignore[no-any-return]


def token(w: dict[str, Any]) -> dict[str, Any]:
    return step_named(w, "review", "token")


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


def claude(w: dict[str, Any], old: str, new: str) -> None:
    assert old in str(action(w)["claude_args"]), old
    action(w)["claude_args"] = str(action(w)["claude_args"]).replace(old, new)


def prompt(w: dict[str, Any], old: str, new: str) -> None:
    flat = " ".join(str(action(w)["prompt"]).split())
    assert old in flat, old
    action(w)["prompt"] = flat.replace(old, new)


def unshare(w: dict[str, Any], name: str) -> list[dict[str, Any]]:
    """A copy of a round's steps of its own, which a change can then make differ."""
    w["jobs"][name]["steps"] = copy.deepcopy(w["jobs"][name]["steps"])
    return w["jobs"][name]["steps"]  # type: ignore[no-any-return]


Change = Callable[[dict[str, Any]], object]
CASES: list[tuple[Change, str]] = [
    (lambda w: w.update({"on": {"pull_request_target": None}}), "not on pull_request, pull"),
    (lambda w: w["on"].update({"push": None}), "not on pull_request, pull"),
    (lambda w: w["on"].update({"issue_comment": None}), "not on pull_request, pull"),
    (lambda w: w["on"].update({"pull_request_review": None}), "not on pull_request, pull"),
    (lambda w: w["on"].pop("pull_request_review_comment"), "not on pull_request, pull"),
    (
        lambda w: w["on"]["pull_request_review_comment"]["types"].append("edited"),
        "pull_request_review_comment ['created', 'edited'], not ['created']",
    ),
    (lambda w: w["on"]["pull_request_review_comment"].pop("types"), "review_comment None"),
    (lambda w: w["on"]["pull_request"]["types"].append("edited"), "not ['opened'"),
    (lambda w: w["on"]["pull_request"]["types"].remove("synchronize"), "not ['opened'"),
    (lambda w: w["on"]["pull_request"]["types"].append("ready_for_review"), "not ['opened'"),
    (lambda w: w["on"].pop("merge_group"), "not on pull_request, pull"),
    (lambda w: w["on"].update({"merge_group": {"types": ["checks_requested"]}}), "not every"),
    (lambda w: w.update({"permissions": {"contents": "write"}}), "default permissions"),
    (lambda w: w.pop("permissions"), "default permissions"),
    (lambda w: w.update({"concurrency": job(w)["concurrency"]}), "at the workflow level"),
    (lambda w: w["jobs"].update({"other": {}}), "its jobs are"),
    *[(lambda w, n=n: w["jobs"].pop(n), "its jobs are") for n in sorted(JOBS)],
    # The gate (review-judge-reply-on-post design D2, D2a).
    (lambda w: gate_job(w).pop("if"), "not skipping bots, forks, outsiders"),
    (
        lambda w: gate_job(w).update({"if": "github.event.pull_request.user.type != 'Bot'"}),
        "not skipping bots, forks, outsiders",
    ),
    (
        lambda w: gate_job(w).update({"concurrency": copy.deepcopy(job(w)["concurrency"])}),
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
    (lambda w: gate_job(w)["steps"].append({"run": "echo hi"}), "gate's steps are"),
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
    # When each job runs, and what it waits for (review-splits-large-prs design D4, D10).
    *[(lambda w, n=n: w["jobs"][n].pop("if"), f"{n} runs when None") for n in IFS],
    *[
        (lambda w, n=n: w["jobs"][n].update({"if": "always()"}), f"{n} runs when 'always()'")
        for n in IFS
    ],
    *[(lambda w, n=n: w["jobs"][n].pop("needs"), f"{n} needs None") for n in NEEDS],
    (
        lambda w: w["jobs"]["resolve"].update(
            {"if": str(IFS["resolve"]).replace("needs.follow-1.outputs.parts == '[]' || ", "")}
        ),
        "resolve runs when",
    ),
    # Each job's token and group (design D1, D3; review-splits-large-prs design D8).
    *[
        (
            lambda w, n=n: w["jobs"][n]["permissions"].update({"contents": "write"}),
            f"{n}'s GITHUB_TOKEN permissions",
        )
        for n in ("plan", "review", "follow-1", "resolve")
    ],
    (lambda w: job(w)["permissions"].update({"id-token": "write"}), "review's GITHUB_TOKEN"),
    (lambda w: job(w)["permissions"].update({"pull-requests": "write"}), "review's GITHUB_TOKEN"),
    (lambda w: job(w).pop("permissions"), "review's GITHUB_TOKEN permissions"),
    (lambda w: job(w).update({"environment": "plan-pr"}), "it needs none"),
    *[
        (lambda w, n=n: w["jobs"][n].pop("concurrency"), f"{n}'s concurrency is None")
        for n in GROUPS
    ],
    (
        lambda w: job(w).update(
            {"concurrency": {"group": f"claude-review-{PR}", "cancel-in-progress": True}}
        ),
        "review's concurrency is",
    ),
    (
        lambda w: job(w)["concurrency"].update({"cancel-in-progress": False}),
        "review's concurrency",
    ),
    (
        lambda w: resolve_job(w)["concurrency"].update({"group": "claude-resolve"}),
        "resolve's concurrency",
    ),
    (lambda w: job(w).pop("timeout-minutes"), "no timeout-minutes"),
    (lambda w: job(w).update({"timeout-minutes": 20}), "timeout-minutes is 20, not 90"),
    # The plan job (review-splits-large-prs design D1 to D4).
    (lambda w: plan_job(w).pop("outputs"), "plan's outputs are None"),
    (lambda w: plan_job(w)["outputs"].pop("model"), "plan's outputs are"),
    (lambda w: plan_job(w)["steps"][0]["with"].update({"fetch-depth": 1}), "plan's checkout"),
    (
        lambda w: plan_job(w)["steps"][0]["with"].update({"persist-credentials": True}),
        "plan's checkout",
    ),
    (lambda w: plan_job(w)["steps"].remove(plan_step(w)), "plan's steps are"),
    (lambda w: move(w, plan_step(w), 0, "plan"), "plan's steps are"),
    (lambda w: plan_step(w).update({"id": "files"}), f"{PLAN_NAME!r} is given"),
    (lambda w: plan_step(w).update({"env": {"T": "${{ secrets.GITHUB_TOKEN }}"}}), "also has"),
    (lambda w: plan_script(w, '"uv.lock", ', '"uv.lock", "x.py", '), "this test pins"),
    (lambda w: plan_script(w, "MAX_TURNS = 400", "MAX_TURNS = 9999"), "this test pins"),
    (lambda w: plan_script(w, "READ_CHUNK_BYTES = 20_000", "READ_CHUNK_BYTES = 10**9"), "pins"),
    (lambda w: plan_script(w, "PART_READS = 100", "PART_READS = 4000"), "this test pins"),
    (
        lambda w: plan_script(w, '"data suffixes": (".json"', '"data suffixes": (".py", ".json"'),
        "this test pins",
    ),
    (lambda w: plan_script(w, "and not named(path)", ""), "this test pins"),
    (
        lambda w: plan_job(w)["steps"][3]["with"].update({"include-hidden-files": False}),
        "plan's upload of review-plan",
    ),
    (
        lambda w: plan_job(w)["steps"][3]["with"].update({"retention-days": 90}),
        "plan's upload of review-plan",
    ),
    (lambda w: plan_job(w)["steps"].pop(4), "plan's steps are"),
    # The model, from the checked variable (review-covers-the-diff design D6).
    (lambda w: plan_job(w)["steps"].remove(model_step(w)), "plan's steps are"),
    (
        lambda w: model_step(w)["env"].update({"MODEL": "claude-opus-5-5"}),
        f"{MODEL_NAME!r} is given",
    ),
    (lambda w: claude(w, MODEL_ARG, "${{ vars.CLAUDE_REVIEW_MODEL }}"), "--model isn't"),
    (lambda w: claude(w, f"--model {MODEL_ARG}", ""), "--model isn't"),
    # A session (design D1 to D9; review-splits-large-prs design D4 to D8, D11).
    (lambda w: job(w).pop("strategy"), "review's strategy is None"),
    (lambda w: job(w)["strategy"].update({"fail-fast": True}), "review's strategy is"),
    (
        lambda w: job(w)["strategy"]["matrix"].update({"include": MATRICES["review-2"]}),
        "review's strategy is",
    ),
    (lambda w: job(w).update({"outputs": {"x": "y"}}), "its records are artifacts"),
    (lambda w: unshare(w, "review-2").pop(), "review-2's steps"),
    (lambda w: unshare(w, "review-3")[0]["with"].update({"fetch-depth": 2}), "review-3's steps"),
    (lambda w: job(w)["steps"].remove(token(w)), "review's steps are"),
    (lambda w: move(w, token(w), len(job(w)["steps"])), "review's steps are"),
    (lambda w: token(w)["with"].update({"permission-contents": "write"}), "token is minted"),
    (lambda w: token(w)["with"].update({"permission-issues": "write"}), "token is minted"),
    (lambda w: token(w)["with"].pop("repositories"), "token is minted"),
    (
        lambda w: token(w)["with"].update({"private-key": "${{ secrets.DOCS_APP_PRIVATE_KEY }}"}),
        "token is minted",
    ),
    (lambda w: token(w).update({"id": "token"}), "not app-token"),
    (
        lambda w: token(w)["with"].update({"client-id": "${{ vars.REVIEW_APP_CLIENT_ID }}"}),
        "client ID is",
    ),
    (lambda w: job(w)["steps"].append({"run": "git push"}), "review's steps are"),
    (lambda w: job(w)["steps"][0].update({"uses": "actions/checkout@v7"}), "isn't pinned"),
    (lambda w: job(w)["steps"][0]["with"].pop("persist-credentials"), "review's checkout"),
    (
        lambda w: job(w)["steps"][0]["with"].update({"persist-credentials": True}),
        "review's checkout",
    ),
    (lambda w: action_step(w).update({"uses": f"{ACTION}@v1"}), "isn't pinned"),
    (lambda w: action_step(w).update({"id": "claude"}), "not review"),
    (lambda w: action_step(w).pop("continue-on-error"), "leaves no record"),
    (lambda w: action_step(w).update({"if": "${{ always() }}"}), "the action's step also has"),
    # The plan and the round's list, checked before Claude (review-splits-large-prs design D4).
    (lambda w: job(w)["steps"].remove(session_step(w)), "review's steps are"),
    (lambda w: move(w, session_step(w), 0), "review's steps are"),
    (
        lambda w: session_step(w)["env"].update({"FILES_SHA256": ""}),
        f"{SESSION_NAME!r} is given",
    ),
    (
        lambda w: script(session_step(w), "!= os.environ.get(digest", "== os.environ.get(digest"),
        "this test pins",
    ),
    (
        lambda w: job(w)["steps"][2]["with"].update({"name": "review-plan-elsewhere"}),
        "download of review-plan",
    ),
    (
        lambda w: job(w)["steps"][3]["with"].update({"name": "review-round-1"}),
        "download of review-round",
    ),
    # The denials report (review-denials-and-guide design D1 to D3).
    (lambda w: job(w)["steps"].remove(report(w)), "review's steps are"),
    (
        lambda w: report(w).update({"run": str(report(w)["run"]) + "print(open('x').read())\n"}),
        "isn't the one this test pins",
    ),
    (
        lambda w: script(
            report(w),
            'os.environ.get("EXECUTION_FILE", "")',
            '"${{ steps.review.outputs.execution_file }}"',
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
    (lambda w: report(w).update({"working-directory": ".org-guide"}), "also has ['working"),
    (lambda w: move(w, report(w), 0), "review's steps are"),
    # The guide (review-denials-and-guide design D4).
    (lambda w: guide(w).update({"persist-credentials": True}), "the guide's checkout"),
    (lambda w: guide(w).update({"repository": "troupe-run/troupe"}), "the guide's checkout"),
    (lambda w: guide(w).update({"path": "../guide"}), "the guide's checkout"),
    (lambda w: guide(w).update({"path": "/tmp/guide"}), "the guide's checkout"),  # noqa: S108
    (lambda w: guide(w).pop("sparse-checkout"), "the guide's checkout"),
    (
        lambda w: job(w)["steps"].insert(0, copy.deepcopy(job(w)["steps"][0])),
        "review's steps are",
    ),
    # The action's inputs (design D1, D3, D4, D8, D9).
    (lambda w: action(w).update({"display_report": "true"}), "given display_report"),
    (lambda w: prompt(w, ".org-guide/CONTRIBUTING.md", GUIDE_URL), "names the guide by URL"),
    (lambda w: prompt(w, "org-profile/CONTRIBUTING.md", ""), "doesn't name org-profile"),
    (lambda w: action(w).pop("github_token"), "github_token"),
    (lambda w: action(w).update({"github_token": "${{ secrets.SOME_PAT }}"}), "github_token"),
    (lambda w: action(w).update({"github_token": "${{ secrets.GITHUB_TOKEN }}"}), "github_token"),
    (lambda w: action(w).pop("claude_code_oauth_token"), "claude_code_oauth_token"),
    (
        lambda w: action(w).update({"anthropic_api_key": "${{ secrets.ANTHROPIC_API_KEY }}"}),
        "given anthropic_api_key",
    ),
    (lambda w: action(w).update({"allowed_bots": "*"}), "given allowed_bots"),
    (lambda w: action(w).update({"allowed_non_write_users": "*"}), "given allowed_non_write"),
    (
        lambda w: action(w).update({"additional_permissions": "contents: write"}),
        "given additional_permissions",
    ),
    (lambda w: action(w).update({"show_full_output": "true"}), "given show_full_output"),
    (lambda w: action(w).pop("prompt"), "no prompt"),
    (lambda w: tools(w, "Bash(gh pr view:*),WebFetch"), "add ['WebFetch']"),
    (lambda w: tools(w, "Bash(gh pr view:*),Edit"), "add ['Edit']"),
    (lambda w: tools(w, "Bash(gh pr view:*),Write"), "add ['Write']"),
    (lambda w: tools(w, "Bash(gh pr view:*),Bash(git push:*)"), "add ['Bash(git push:*)']"),
    (lambda w: tools(w, "Bash(gh pr view:*),Bash(gh pr review:*)"), "add ['Bash(gh pr review"),
    # One summary, posted by the report job (review-splits-large-prs design D6).
    (lambda w: tools(w, "Bash(gh pr view:*),Bash(gh pr comment:*)"), "add ['Bash(gh pr comment"),
    (lambda w: tools(w, "Bash(gh:*)"), "add ['Bash(gh:*)']"),
    (lambda w: tools(w, "Bash(gh pr view:*),Read"), "add ['Read']"),
    (lambda w: tools(w, "Bash(gh pr view:*),Bash(gh api:*)"), "add ['Bash(gh api:*)']"),
    (lambda w: claude(w, "Grep(./**)", "Grep"), "add ['Grep']"),
    (lambda w: tools(w, 'Bash(gh pr view:*)" --dangerously-skip-permissions "'), "besides"),
    (lambda w: claude(w, f"--max-turns {MAX_TURNS}", ""), "no --max-turns"),
    (lambda w: claude(w, MAX_TURNS, "30"), "--max-turns isn't"),
    (lambda w: claude(w, '"required":["summary",', '"required":['), "the schema this test pins"),
    (lambda w: claude(w, '"decision"]', '"decision","owner"]'), "the schema this test pins"),
    (
        lambda w: action(w).update(
            {"claude_args": re.sub(r"--json-schema '[^']*'", "", str(action(w)["claude_args"]))}
        ),
        "the schema this test pins",
    ),
    (lambda w: sources(w, ""), "from None"),
    (lambda w: sources(w, "--setting-sources user,project"), "from 'user,project'"),
    (lambda w: sources(w, "--setting-sources project"), "from 'project'"),
    # What the prompt says about reading (D7, D7a; review-splits-large-prs design D5, D6).
    *[
        (lambda w, s=sentence: prompt(w, s, ""), f"the prompt doesn't say {sentence!r}")
        for sentence in PROMPT_READS
    ],
    (
        lambda w: action(w).update(
            {"prompt": str(action(w)["prompt"]) + "\nRead the diff with `gh pr diff`.\n"}
        ),
        "the prompt still says",
    ),
    # What the session read, and what Claude named (review-covers-the-diff design D3, D4;
    # review-splits-large-prs design D4, D6).
    (lambda w: job(w)["steps"].remove(measure_step(w)), "review's steps are"),
    (lambda w: move(w, measure_step(w), 0), "review's steps are"),
    (
        lambda w: measure_step(w)["env"].update(
            {"EXECUTION_FILE": "${{ steps.review.outputs.structured_output }}"}
        ),
        f"{MEASURE_NAME!r} is given",
    ),
    (
        lambda w: measure_step(w)["env"].update(
            {"SAID": "${{ steps.review.outputs.structured_output }}"}
        ),
        f"{MEASURE_NAME!r} is given",
    ),
    (lambda w: measure_step(w).pop("continue-on-error"), f"{MEASURE_NAME!r} is given"),
    (lambda w: measure_step(w)["env"].pop("OUTCOME"), f"{MEASURE_NAME!r} is given"),
    (
        lambda w: measure_step(w)["env"].update({"OUTCOME": "success"}),
        f"{MEASURE_NAME!r} is given",
    ),
    (lambda w: measure_step(w).update({"if": "${{ success() }}"}), f"{MEASURE_NAME!r} is given"),
    (
        lambda w: measure_step(w).update({"run": str(measure_step(w)["run"]) + "print(text)\n"}),
        f"{MEASURE_NAME!r}'s script isn't the one this test pins",
    ),
    (lambda w: job(w)["steps"].remove(answer_step(w)), "review's steps are"),
    (
        lambda w: answer_step(w)["env"].update({"EXECUTION_FILE": "x"}),
        f"{ANSWER_NAME!r} is given",
    ),
    (lambda w: job(w)["steps"].pop(), "review's steps are"),
    (lambda w: job(w)["steps"][-1].pop("if"), "review's record runs when None"),
    (
        lambda w: job(w)["steps"][-1]["with"].update({"name": "review-record"}),
        "review's record is given",
    ),
    # The planners (review-splits-large-prs design D4, D10).
    (lambda w: w["jobs"]["follow-1"].pop("env"), "follow-1's env is None"),
    (lambda w: w["jobs"]["follow-2"].update({"env": {"NEXT_ROUND": "2"}}), "follow-2's env is"),
    (lambda w: w["jobs"]["follow-1"].pop("outputs"), "follow-1's outputs are None"),
    (lambda w: w["jobs"]["follow-1"]["steps"][-1].pop("if"), "follow-1's upload runs when None"),
    (
        lambda w: script(gather_step(w, "follow-1"), "MAX_PARTS = 3", "MAX_PARTS = 60"),
        "this test pins",
    ),
    (
        lambda w: script(
            gather_step(w, "follow-1"),
            "elif unmeasured and code_unread:",
            "elif False:",
        ),
        "this test pins",
    ),
    (lambda w: w["jobs"]["follow-1"]["steps"].pop(2), "follow-1's steps are"),
    # The report job (design D4a; review-splits-large-prs design D6, D7, D9).
    (lambda w: resolve_job(w).pop("outputs"), "resolve's outputs are None"),
    (lambda w: resolve_job(w)["outputs"].pop("unread"), "resolve's outputs are"),
    (lambda w: resolve_job(w)["steps"].remove(resolver(w)), "resolve's steps are"),
    (lambda w: resolve_job(w)["steps"].remove(poster(w)), "resolve's steps are"),
    (lambda w: resolve_job(w)["steps"].remove(gather_step(w)), "resolve's steps are"),
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
    (lambda w: move(w, resolver(w), 1, "resolve"), "resolve's steps are"),
    (
        lambda w: resolver(w)["env"].update({"GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}"}),
        f"{RESOLVER_NAME!r} is given",
    ),
    (
        lambda w: resolver(w)["env"].update(
            {"STRUCTURED_OUTPUT": "${{ needs.review.outputs.structured_output }}"}
        ),
        f"{RESOLVER_NAME!r} is given",
    ),
    (lambda w: resolver(w).update({"if": "${{ always() }}"}), f"{RESOLVER_NAME!r} also has"),
    (lambda w: resolver(w).update({"continue-on-error": True}), "also has ['continue-on-error']"),
    (
        lambda w: script(resolver(w), 'if current not in ("must-fix", "nit"):', "if False:"),
        f"{RESOLVER_NAME!r}'s script isn't the one this test pins",
    ),
    # Widened to decisions, which are the owner's (review-resolves-fixed-nits design D2).
    (
        lambda w: script(resolver(w), '("must-fix", "nit")', '("must-fix", "nit", "decision")'),
        f"{RESOLVER_NAME!r}'s script isn't the one this test pins",
    ),
    # Widened past the session's part (review-splits-large-prs design D7).
    (
        lambda w: script(resolver(w), "elif not ours(thread, round_, part):", "elif False:"),
        f"{RESOLVER_NAME!r}'s script isn't the one this test pins",
    ),
    (
        lambda w: snapshot(w)["env"].update({"CLAUDE": "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}"}),
        f"{SNAPSHOT_NAME!r} is given",
    ),
    (
        lambda w: snapshot(w).update({"run": str(snapshot(w)["run"]) + "print(1)\n"}),
        f"{SNAPSHOT_NAME!r}'s script isn't the one this test pins",
    ),
    (lambda w: move(w, snapshot(w), len(job(w)["steps"])), "review's steps are"),
    (lambda w: poster(w)["env"].update({"HEAD_SHA": "${{ github.sha }}"}), f"{POST_NAME!r} is"),
    (
        lambda w: poster(w).update({"run": str(poster(w)["run"]) + "print(1)\n"}),
        f"{POST_NAME!r}'s script isn't the one this test pins",
    ),
    # The required check (review-completed-check design D2 to D5; review-splits-large-prs D9).
    (lambda w: completed_job(w).update({"name": "review completed"}), "required-checks.json"),
    (lambda w: completed_job(w).update({"needs": ["review", "resolve"]}), "completed needs"),
    (lambda w: completed_job(w).update({"needs": "resolve"}), "completed needs"),
    # Without always(), a cancelled or failed review skips it, which counts as passed.
    (
        lambda w: completed_job(w).update({"if": "github.event_name == 'pull_request'"}),
        "after a cancelled review too",
    ),
    (lambda w: completed_job(w).pop("if"), "after a cancelled review too"),
    # A merge group or a comment's run reporting it: a merge group must skip it, and a comment's
    # run reports what GitHub ignores (design D4, D5).
    (lambda w: completed_job(w).update({"if": "always()"}), "never for a comment's run"),
    (
        lambda w: completed_job(w).update({"if": "always() && github.event_name != 'merge_group'"}),
        "never for a comment's run",
    ),
    (
        lambda w: completed_job(w).update({"permissions": {"actions": "read"}}),
        "completed's GITHUB_TOKEN permissions",
    ),
    (lambda w: completed_job(w).pop("permissions"), "completed's GITHUB_TOKEN permissions"),
    (
        lambda w: completed_job(w).update({"concurrency": copy.deepcopy(job(w)["concurrency"])}),
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
        lambda w: completed(w)["env"].update({"TOKEN": "${{ secrets.REVIEW_APP_PRIVATE_KEY }}"}),
        f"{COMPLETED_STEP_NAME!r} is given",
    ),
    (
        lambda w: completed(w)["env"].update({"REVIEW": "${{ needs.gate.result }}"}),
        f"{COMPLETED_STEP_NAME!r} is given",
    ),
    (
        lambda w: completed(w).update({"run": str(completed(w)["run"]) + "\nsys.exit(0)\n"}),
        f"{COMPLETED_STEP_NAME!r}'s script isn't the one this test pins",
    ),
    *[
        (lambda w, k=k: completed(w)["env"].pop(k), f"{COMPLETED_STEP_NAME!r} is given")
        for k in ("COVERAGE", "CODE", "UNREAD", "FOLLOW_1_PARTS", "REVIEW_3")
    ],
    (lambda w: completed(w)["env"].update({"CODE": "all"}), f"{COMPLETED_STEP_NAME!r} is given"),
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
    # A source or test file left unread passes (review-splits-large-prs design D9).
    (
        lambda w: script(completed(w), 'if code == "unread":', "if False:"),
        f"{COMPLETED_STEP_NAME!r}'s script isn't the one this test pins",
    ),
    # A follow-up round that was needed but skipped passes (D10).
    (
        lambda w: script(completed(w), 'first != "[]"),', "False),"),
        f"{COMPLETED_STEP_NAME!r}'s script isn't the one this test pins",
    ),
]


@pytest.mark.parametrize(("change", "named"), CASES)
def test_each_way_the_workflow_can_go_wrong_is_named(change: Change, named: str) -> None:
    workflow = copy.deepcopy(review())
    change(workflow)
    assert any(named in problem for problem in problems(workflow)), problems(workflow)


def run_completed(tmp_path: Path, **results: str) -> subprocess.CompletedProcess[str]:
    """Run the required check's step, as a pull request event's run of a member's own pull request
    would, with the needs' results given here instead of a completed review's: by default, one
    round that read everything, so no follow-up ran."""
    env = {
        "RUN_ID": "41258918187",
        "AUTHOR_TYPE": "User",
        "HEAD_REPOSITORY": "troupe-run/infrastructure",
        "GATE": "success",
        "WANTS_REVIEW": "true",
        "PLAN": "success",
        "REVIEW": "success",
        "FOLLOW_1": "success",
        "FOLLOW_1_PARTS": "[]",
        "REVIEW_2": "skipped",
        "FOLLOW_2": "skipped",
        "FOLLOW_2_PARTS": "",
        "REVIEW_3": "skipped",
        "RESOLVE": "success",
        "COVERAGE": "complete",
        "CODE": "all",
        "UNREAD": "[]",
        "UNMEASURED": '""',
        **results,
    }
    return run_step(completed(review()), tmp_path, tmp_path, env)


SKIPPED_ALL = {"PLAN": "skipped", "REVIEW": "skipped", "FOLLOW_1": "skipped", "FOLLOW_1_PARTS": "",
               "RESOLVE": "skipped"}  # fmt: skip
PARTS = '[{"round":2,"part":1}]'


def test_the_check_passes_when_the_review_and_its_resolving_job_succeeded(tmp_path: Path) -> None:
    done = run_completed(tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "::error" not in done.stdout


def test_the_check_passes_after_both_follow_up_rounds_ran(tmp_path: Path) -> None:
    done = run_completed(tmp_path, FOLLOW_1_PARTS=PARTS, REVIEW_2="success", FOLLOW_2="success",
                         FOLLOW_2_PARTS=PARTS, REVIEW_3="success")  # fmt: skip
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.parametrize(
    ("results", "named"),
    [
        ({"REVIEW": "cancelled", "FOLLOW_1": "skipped"}, "claude review (cancelled)"),
        ({"REVIEW": "failure"}, "claude review (failure)"),
        ({"PLAN": "failure"}, "plan the review (failure)"),
        ({"FOLLOW_1": "failure"}, "plan follow-up 1 (failure)"),
        ({"RESOLVE": "failure"}, "resolve and report (failure)"),
        ({"RESOLVE": "cancelled"}, "resolve and report (cancelled)"),
        ({"REVIEW": "", "RESOLVE": ""}, "claude review (no result)"),
        # A follow-up round its planner asked for that didn't run, or failed (D10).
        ({"FOLLOW_1_PARTS": PARTS}, "claude review, follow-up 1 (skipped)"),
        ({"FOLLOW_1_PARTS": PARTS, "REVIEW_2": "failure"}, "claude review, follow-up 1 (failure)"),
        ({"FOLLOW_1_PARTS": PARTS, "REVIEW_2": "success"}, "plan follow-up 2 (skipped)"),
        (
            {
                "FOLLOW_1_PARTS": PARTS,
                "REVIEW_2": "success",
                "FOLLOW_2": "success",
                "FOLLOW_2_PARTS": PARTS,
            },
            "claude review, follow-up 2 (skipped)",
        ),
        # A planner whose answer isn't there can't say no round was needed.
        ({"FOLLOW_1_PARTS": ""}, "claude review, follow-up 1 (skipped)"),
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
        {"GATE": "failure", "WANTS_REVIEW": "", **SKIPPED_ALL},
        {"GATE": "cancelled", "WANTS_REVIEW": "", **SKIPPED_ALL},
        # A pull request event's gate always says yes; anything else isn't an answer to trust.
        {"WANTS_REVIEW": "false", **SKIPPED_ALL},
        {"WANTS_REVIEW": "", **SKIPPED_ALL},
        # Skipped by the gate's own if:, but the pull request is a member's, not a bot's or fork's.
        {"GATE": "skipped", "WANTS_REVIEW": "", **SKIPPED_ALL},
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
    done = run_completed(tmp_path, GATE="skipped", WANTS_REVIEW="", **SKIPPED_ALL, **who)
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


# A SHA a rebase removed is no finding, and why; a task's run id is still evidence
# (review-rebased-shas design D1 to D3, #294). Like the tests above, this checks what the prompt
# says, not what the model does with it.
PROMPT_REBASED_SHAS = [
    "A commit SHA cited in the pull request that names no commit on its branch isn't a finding,"
    " at any tier",
    "don't ask for it to be re-cited",
    "pull requests merge by rebase, which rewrites every SHA, so no cited SHA survives the merge",
    "A ticked task is still judged by its code and verification,"
    " and a CI run id it cites is still evidence",
]


@pytest.mark.parametrize("sentence", PROMPT_REBASED_SHAS)
def test_the_prompt_says_a_sha_missing_from_the_branch_is_no_finding_and_a_run_id_is_evidence(
    sentence: str,
) -> None:
    prompt = " ".join(str(action(review())["prompt"]).split())
    assert sentence in prompt, f"the prompt doesn't say {sentence!r}"


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


def kept_answer(answer: object) -> object:
    """An answer as the step that keeps it stores it: parsed, or null when it isn't an object."""
    if isinstance(answer, str):
        try:
            answer = json.loads(answer)
        except ValueError:
            return None
    return answer if isinstance(answer, dict) else None


def resolve_run(
    tmp_path: Path,
    answer: object,
    fail_when: str = "",
    *,
    sessions: Mapping[tuple[int, int], object] | None = None,
    rounds: Mapping[int, dict[str, int]] | None = None,
) -> tuple[subprocess.CompletedProcess[str], list[list[str]]]:
    """Run the resolving step on the snapshot, with each session's kept answer and each round's
    list in RUNNER_TEMP; by default one session, whose list holds the conversations' file."""
    temp = tmp_path / "runner-temp"
    records = temp / "review" / "records"
    records.mkdir(parents=True, exist_ok=True)
    (temp / "review-threads.json").write_text(json.dumps(SNAPSHOT_THREADS), encoding="utf-8")
    for number, assign in (rounds if rounds is not None else {1: {"scripts/guard.py": 1}}).items():
        plan = {"round": number, "assign": assign, "parts": []}
        (temp / "review" / f"round-{number}.json").write_text(json.dumps(plan), encoding="utf-8")
    for (number, part), given in (sessions or {(1, 1): answer}).items():
        kept = {"round": number, "part": part, "answer": kept_answer(given)}
        (records / f"answer-{number}-{part}.json").write_text(json.dumps(kept), encoding="utf-8")
    bin_dir = stub_gh(tmp_path / "bin", {"fail_when": fail_when})
    done = run_step(resolver(review()), tmp_path, bin_dir, {})
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
def test_an_unreadable_answer_resolves_nothing_and_says_so(tmp_path: Path, answer: object) -> None:
    done, calls = resolve_run(tmp_path, answer)
    assert done.returncode == 0, done.stdout + done.stderr
    assert calls == []
    assert done.stdout.startswith("::warning title=Nothing resolved::Round 1 part 1's answer")


def test_without_the_plan_nothing_is_resolved_and_the_step_fails(tmp_path: Path) -> None:
    done, calls = resolve_run(tmp_path, {"resolve": ["PRRT_mustfix"], "retier": []}, rounds={})
    assert done.returncode == 1
    assert calls == []
    assert done.stdout.startswith("::warning title=Nothing resolved::")


# A session judges only the conversations on its own files (review-splits-large-prs design D7).
TWO_PARTS = {1: {"scripts/guard.py": 1, "README.md": 1, "scripts/check.py": 2}}


def test_a_session_can_t_resolve_a_conversation_on_another_part_s_file(tmp_path: Path) -> None:
    sessions = {(1, 1): {"resolve": [], "retier": []},
                (1, 2): {"resolve": ["PRRT_mustfix"], "retier": []}}  # fmt: skip
    done, calls = resolve_run(tmp_path, None, sessions=sessions, rounds=TWO_PARTS)
    assert done.returncode == 0, done.stdout + done.stderr
    assert calls == []
    assert "isn't on the list of round 1 part 2, the session that named it" in done.stdout


def test_the_session_whose_list_holds_the_file_resolves_it(tmp_path: Path) -> None:
    sessions = {(1, 1): {"resolve": ["PRRT_mustfix"], "retier": []},
                (1, 2): {"resolve": [], "retier": []}}  # fmt: skip
    _, calls = resolve_run(tmp_path, None, sessions=sessions, rounds=TWO_PARTS)
    assert resolved(calls) == ["PRRT_mustfix"]


def test_a_conversation_on_a_file_on_no_list_is_the_lead_s(tmp_path: Path) -> None:
    rounds = {1: {"src/elsewhere.py": 1, "scripts/check.py": 2}}
    sessions = {(1, 1): {"resolve": ["PRRT_nit"], "retier": []},
                (1, 2): {"resolve": ["PRRT_mustfix"], "retier": []}}  # fmt: skip
    done, calls = resolve_run(tmp_path, None, sessions=sessions, rounds=rounds)
    assert resolved(calls) == ["PRRT_nit"]
    assert "the session that named it" in done.stdout


def test_a_follow_up_session_resolves_on_the_files_it_was_given(tmp_path: Path) -> None:
    rounds = {1: {"scripts/guard.py": 1}, 2: {"scripts/guard.py": 1}}
    sessions = {(1, 1): {"resolve": [], "retier": []},
                (2, 1): {"resolve": ["PRRT_mustfix"], "retier": []}}  # fmt: skip
    _, calls = resolve_run(tmp_path, None, sessions=sessions, rounds=rounds)
    assert resolved(calls) == ["PRRT_mustfix"]


def test_a_conversation_two_sessions_name_is_resolved_once(tmp_path: Path) -> None:
    rounds = {1: {"scripts/guard.py": 1}, 2: {"scripts/guard.py": 1}}
    sessions = {(1, 1): {"resolve": ["PRRT_nit"], "retier": []},
                (2, 1): {"resolve": ["PRRT_nit"], "retier": []}}  # fmt: skip
    _, calls = resolve_run(tmp_path, None, sessions=sessions, rounds=rounds)
    assert resolved(calls) == ["PRRT_nit"]


def test_one_session_s_resolve_beats_another_s_re_tier(tmp_path: Path) -> None:
    rounds = {1: {"scripts/guard.py": 1}, 2: {"scripts/guard.py": 1}}
    item = {"thread": "PRRT_mustfix", "tier": "nit", "title": "a", "reason": "r"}
    sessions = {(1, 1): {"resolve": [], "retier": [item]},
                (2, 1): {"resolve": ["PRRT_mustfix"], "retier": []}}  # fmt: skip
    done, calls = resolve_run(tmp_path, None, sessions=sessions, rounds=rounds)
    assert resolved(calls) == ["PRRT_mustfix"]
    assert len(calls) == 1
    assert "it was only resolved" in done.stdout


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


def run_plan(
    workspace: Path,
) -> tuple[
    subprocess.CompletedProcess[str],
    dict[str, Any] | None,
    dict[str, Any] | None,
    list[dict[str, Any]] | None,
]:
    """Run the plan step in the workspace: its result, the list and round 1's parts it left in
    .review-diff/, and the matrix it output."""
    outputs = workspace.parent / "outputs"
    outputs.write_text("", encoding="utf-8")
    script = workspace.parent / "plan.py"
    script.write_text(str(plan_step(review())["run"]), encoding="utf-8")
    env = {**clean_env(), "GITHUB_OUTPUT": str(outputs)}
    done = subprocess.run(
        [sys.executable, str(script)], cwd=workspace, capture_output=True, text=True,
        encoding="utf-8", env=env, check=False,
    )  # fmt: skip
    if done.returncode != 0:
        return done, None, None, None
    folder = workspace / ".review-diff"
    data = json.loads((folder / "files.json").read_text(encoding="utf-8"))
    plan = json.loads((folder / "round-1.json").read_text(encoding="utf-8"))
    said = dict(line.split("=", 1) for line in outputs.read_text(encoding="utf-8").splitlines())
    return done, data, plan, json.loads(said["parts"])


def run_diff(workspace: Path) -> Ran:
    """The plan step's result, its list, and the turn limits of its parts, as one string."""
    done, data, _, matrix = run_plan(workspace)
    turns = ",".join(str(p["max_turns"]) for p in matrix or [])
    return done, data, f"max_turns={turns}\n" if matrix is not None else ""


def reads(data: dict[str, Any]) -> int:
    return sum(len(t["reads"]) for f in data["files"] for t in f["targets"])


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
    assert (reads(data), outputs) == (0, "max_turns=40\n")


def test_the_turns_follow_the_reads_planned_up_to_the_cap(tmp_path: Path) -> None:
    # One added file of 600 lines of 100 bytes: three Reads of 200 lines, so 40 + 2 x 3 turns.
    big = (b"x" * 99 + b"\n") * 600
    done, data, outputs = run_diff(merged(tmp_path, {}, {"big.txt": big}))
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    assert (reads(data), outputs) == (3, "max_turns=46\n")
    # One 8 MB file needs 400 Reads, in one part of its own, whose turns stop at the cap.
    huge = {"huge.py": (b"y" * 99 + b"\n") * 80_000}
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
    assert reads(data) == 6


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


# Each changed file's kind, and the parts the plan splits them into (review-splits-large-prs
# design D1 to D3).
def kinds(data: dict[str, Any]) -> dict[str, str | None]:
    return {f["path"]: f.get("kind") for f in data["files"]}


USES = b"open('replies.json'); open('events.json'); open('stream-error'); load('run.jsonl')\n"


@pytest.mark.parametrize(
    ("path", "kind"),
    [
        ("src/runner/conversation.py", "source and test"),
        ("tests/test_conversation.py", "source and test"),
        (".github/workflows/ci.yml", "source and test"),
        ("src/pages/index.astro", "source and test"),
        ("pyproject.toml", "source and test"),
        ("README.md.py", "source and test"),
        ("fixtures.py", "source and test"),
        # Code in a fixtures folder is code.
        ("tests/fixtures/conftest.py", "source and test"),
        # JSON that configures something (owner, 2026-11-11).
        ("package.json", "source and test"),
        ("web/tsconfig.base.json", "source and test"),
        ("tofu/required-checks.json", "source and test"),
        (".github/dependabot.json", "source and test"),
        # Prose.
        ("README.md", "prose"),
        ("contributing/runners.md", "prose"),
        ("docs/page.mdx", "prose"),
        ("notes.txt", "prose"),
        ("public/logo.svg", "prose"),
        ("LICENSE", "prose"),
        ("plugins/runner-openai/LICENSE-CONTENT", "prose"),
        ("openspec/changes/x/.openspec.yaml", "prose"),
        ("openspec/specs/pr-review/spec.md", "prose"),
        # Data that a test names.
        ("fixtures/responses/refusal/replies.json", "data"),
        ("plugins/r/fixtures/ollama/thinking/events.json", "data"),
        ("plugins/r/fixtures/claude/stream-error", "data"),
        ("streams/run.jsonl", "data"),
    ],
)
def test_each_file_s_kind_comes_from_the_declared_list(
    tmp_path: Path, path: str, kind: str
) -> None:
    workspace = merged(tmp_path, {}, {path: b"a\nb\n", "tests/test_uses.py": USES})
    done, data, _ = run_diff(workspace)
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    assert kinds(data)[path] == kind


def test_files_with_nothing_to_read_have_no_kind(tmp_path: Path) -> None:
    workspace = merged(
        tmp_path,
        {"uv.lock": b"a\n"},
        {"uv.lock": b"b\n", "logo.png": b"\x89PNG\r\n\x1a\n\0\xff\xfe", "pkg/__init__.py": b""},
    )
    done, data, _ = run_diff(workspace)
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    assert kinds(data) == {"uv.lock": None, "logo.png": None, "pkg/__init__.py": None}


@pytest.mark.parametrize(
    ("files", "why"),
    [
        # Nothing names it, or its folder.
        ({"notes/old-export.json": b"{}\n"}, "nothing names it"),
        # Named only by another data file and by a proposal: neither is a use (D3).
        (
            {"export/old-export.json": b"{}\n", "fixtures/index.json": b'["old-export.json"]\n',
             "openspec/changes/x/proposal.md": b"old-export.json, in export\n"},
            "nothing names it",
        ),
    ],
)  # fmt: skip
def test_data_that_nothing_names_is_read_as_source_and_test(
    tmp_path: Path, files: dict[str, bytes], why: str
) -> None:
    path = next(iter(files))
    done, data, _ = run_diff(merged(tmp_path, {}, files))
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    entry = next(f for f in data["files"] if f["path"] == path)
    assert (entry["kind"], entry["why"]) == ("source and test", why)


def test_data_whose_folder_a_test_names_is_left_to_its_tests(tmp_path: Path) -> None:
    files = {
        "fixtures/responses/refusal/replies.json": b"{}\n",
        "tests/test_replay.py": b"@pytest.mark.parametrize('case', ['refusal', 'rate-limit'])\n",
    }
    done, data, _ = run_diff(merged(tmp_path, {}, files))
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    entry = data["files"][0]
    assert (entry["path"], entry["kind"], "why" in entry) == (
        "fixtures/responses/refusal/replies.json",
        "data",
        False,
    )


def lines_of(count: int) -> bytes:
    # A file that needs `count` Reads, of 200 lines of 100 bytes each.
    return (b"q" * 99 + b"\n") * (200 * count)


def test_a_small_pull_request_is_one_part_holding_its_prose(tmp_path: Path) -> None:
    files = {"a.py": b"a\n", "b.py": b"b\n", "c.py": b"c\n", "README.md": b"r\n"}
    done, data, plan, matrix = run_plan(merged(tmp_path, {"README.md": b"base\n"}, files))
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    assert plan is not None
    assert matrix is not None
    assert plan["assign"] == {"a.py": 1, "b.py": 1, "c.py": 1, "README.md": 1}
    # Three added files, and the modified README and its diff.
    assert [(p["part"], p["of"], p["reads"]) for p in plan["parts"]] == [(1, 1, 5)]
    assert [p["round"] for p in matrix] == [1]
    assert {f["path"]: f.get("part") for f in data["files"]}["README.md"] == 1


def test_one_session_reads_what_one_session_reliably_covers(tmp_path: Path) -> None:
    """troupe#297's committed sessions read 133 and 151 Reads in one go, so up to 100 Reads of
    source and test is one part (owner, 2026-11-12)."""
    files = {f"src/m{i:02}.py": lines_of(5) for i in range(20)}
    done, _, plan, matrix = run_plan(merged(tmp_path, {}, files))
    assert done.returncode == 0, done.stdout + done.stderr
    assert plan is not None
    assert matrix is not None
    assert [(p["reads"], p["max_turns"]) for p in plan["parts"]] == [(100, 240)]
    assert [(m["part"], m["of"]) for m in matrix] == [(1, 1)]


def test_source_and_test_files_are_split_into_parts_of_at_most_a_hundred_reads(
    tmp_path: Path,
) -> None:
    files = {f"src/m{i:02}.py": lines_of(5) for i in range(26)}
    done, _, plan, matrix = run_plan(merged(tmp_path, {}, files))
    assert done.returncode == 0, done.stdout + done.stderr
    assert plan is not None
    assert matrix is not None
    # 130 Reads: one part of 100 and one of 30, each file in one part, in path order.
    assert [p["reads"] for p in plan["parts"]] == [100, 30]
    assert [p["max_turns"] for p in plan["parts"]] == [240, 100]
    assert sorted(plan["assign"]) == sorted(files)
    assert [plan["assign"][f"src/m{i:02}.py"] for i in (0, 19, 20, 25)] == [1, 1, 2, 2]
    assert [(m["part"], m["of"]) for m in matrix] == [(1, 2), (2, 2)]
    assert len({m["files_sha256"] for m in matrix}) == 1
    assert len({m["round_sha256"] for m in matrix}) == 1


def test_more_than_three_parts_of_reads_make_three_larger_parts(tmp_path: Path) -> None:
    files = {f"src/m{i:02}.py": lines_of(5) for i in range(80)}
    done, _, plan, _ = run_plan(merged(tmp_path, {}, files))
    assert done.returncode == 0, done.stdout + done.stderr
    assert plan is not None
    assert len(plan["parts"]) == 3
    assert sum(p["reads"] for p in plan["parts"]) == 400
    assert sorted(plan["assign"]) == sorted(files)


def test_a_file_larger_than_a_part_gets_a_part_of_its_own(tmp_path: Path) -> None:
    files = {"a.py": lines_of(2), "big.py": lines_of(120), "c.py": lines_of(2)}
    done, _, plan, _ = run_plan(merged(tmp_path, {}, files))
    assert done.returncode == 0, done.stdout + done.stderr
    assert plan is not None
    assert plan["assign"] == {"a.py": 1, "big.py": 2, "c.py": 3}
    assert [p["reads"] for p in plan["parts"]] == [2, 120, 2]


def test_prose_and_data_alone_make_one_part_with_no_source(tmp_path: Path) -> None:
    files = {"README.md": b"r\n", "openspec/x/tasks.md": b"t\n", "fixtures/a/events.json": b"{}\n"}
    # The test that loads the fixture is on the base branch, unchanged.
    base = {"tests/test_x.py": b"open('events.json')\n"}
    done, data, plan, matrix = run_plan(merged(tmp_path, base, files))
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    assert plan is not None
    assert matrix is not None
    assert plan["assign"] == {"README.md": 1, "openspec/x/tasks.md": 1}
    assert len(matrix) == 1
    assert kinds(data)["fixtures/a/events.json"] == "data"


def test_nothing_to_read_still_gets_one_session(tmp_path: Path) -> None:
    done, _, plan, matrix = run_plan(merged(tmp_path, {"uv.lock": b"a\n"}, {"uv.lock": b"b\n"}))
    assert done.returncode == 0, done.stdout + done.stderr
    assert plan is not None
    assert matrix is not None
    assert (plan["assign"], [p["max_turns"] for p in plan["parts"]]) == ({}, [40])


# troupe#325's 39 files (run 43017411898): a protocol change whose 16 Python files are source and
# test, whose 10 JSON schemas are data that its tests load, and whose docs and OpenSpec are prose.
PR_325_CODE = [
    "packages/troupe-plugin-sdk/src/troupe_plugin_sdk/runner.py",
    "packages/troupe-plugin-sdk/tests/test_runner_types.py",
    *[f"packages/troupe/src/troupe/core/{m}.py" for m in
      ("client/messages", "runners/outcome", "runs/aggregate", "runs/projections")],
    *[f"packages/troupe/tests/test_{m}.py" for m in
      ("cli_runs", "client_messages", "client_schemas", "event_payloads", "event_schemas",
       "perform", "run_aggregate", "run_changes_recording", "run_notices", "run_queries")],
]  # fmt: skip
PR_325_SCHEMAS = [
    f"{root}/{name}.schema.json"
    for root in ("packages/troupe/src/troupe/protocol", "protocol/schemas")
    for name in ("client/run", "events/run-ended", "events/run-started",
                 "events/run-worktree-made", "runner/run-event")
]  # fmt: skip
PR_325_PROSE = [
    "contributing/runners.md", "contributing/runs.md", "docs/prompt-book/events.md",
    *[f"openspec/changes/archive/2026-11-08-require-always-written-fields/{n}" for n in
      (".openspec.yaml", "design.md", "proposal.md", "specs/client-protocol/spec.md",
       "specs/runner-protocol/spec.md", "specs/runs/spec.md", "tasks.md")],
    "openspec/specs/client-protocol/spec.md", "openspec/specs/runner-protocol/spec.md",
    "openspec/specs/runs/spec.md",
]  # fmt: skip


def test_troupe_325_s_files_make_one_part_of_code_with_its_schemas_left_to_its_tests(
    tmp_path: Path,
) -> None:
    paths = PR_325_CODE + PR_325_SCHEMAS + PR_325_PROSE
    assert len(paths) == 39
    base = {p: b"before\n" for p in paths}
    head = {p: b"after\n" for p in paths}
    # The schemas' tests load them by folder, as troupe's do.
    head["packages/troupe/tests/test_event_schemas.py"] = (
        b"SCHEMAS / 'events'; 'client'; 'runner'\n"
    )
    done, data, plan, matrix = run_plan(merged(tmp_path, base, head))
    assert done.returncode == 0, done.stdout + done.stderr
    assert data is not None
    assert plan is not None
    assert matrix is not None
    found = kinds(data)
    assert {p for p, k in found.items() if k == "data"} == set(PR_325_SCHEMAS)
    assert {p for p, k in found.items() if k == "source and test"} == set(PR_325_CODE)
    assert {p for p, k in found.items() if k == "prose"} == set(PR_325_PROSE)
    assert len(matrix) == 1


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


# The measuring step, run on execution files shaped as the probe recorded (review-covers-the-diff
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
    """A workspace, the plan in RUNNER_TEMP as each session's step keeps it, and the messages of
    each session of the review, by round and part; it measures each, then gathers what they read
    together, as the report job does (review-splits-large-prs design D4)."""

    def __init__(
        self, tmp_path: Path, files: list[dict[str, Any]], parts: Mapping[str, int] | None = None
    ) -> None:
        self.tmp_path = tmp_path
        self.workspace = tmp_path / "workspace"
        self.workspace.mkdir(parents=True)
        self.kept = tmp_path / "runner-temp" / "review"
        (self.kept / "records").mkdir(parents=True)
        self.files = files
        (self.kept / "files.json").write_text(json.dumps({"files": files}), encoding="utf-8")
        assign = (
            dict(parts)
            if parts is not None
            else {f["path"]: 1 for f in files if f.get("kind") in ("source and test", "prose")}
        )
        self.plan_round(1, assign)
        self.messages: dict[tuple[int, int], list[dict[str, Any]]] = {(1, 1): []}
        self.current = (1, 1)
        self.count = 0
        # The check's outputs after run(): code is none, all, unread or unknown (design D9).
        self.code = ""
        self.unmeasured = ""

    def plan_round(self, number: int, assign: Mapping[str, int]) -> None:
        count = max(assign.values(), default=1)
        plan = {"round": number, "assign": dict(assign),
                "parts": [{"part": p, "of": count, "reads": 1, "max_turns": 42}
                          for p in range(1, count + 1)]}  # fmt: skip
        (self.kept / f"round-{number}.json").write_text(json.dumps(plan), encoding="utf-8")

    def session(self, number: int, part: int) -> None:
        """Make the messages that follow the given session's."""
        self.current = (number, part)
        self.messages.setdefault(self.current, [])

    def read(self, path: str, lines: range, *, arrow: bool = False, error: bool = False) -> None:
        self.count += 1
        ident = f"toolu_{self.count}"
        mark = "→" if arrow else "\t"
        text = "\n".join(f"{n}{mark}text {n}" for n in lines)
        self.messages[self.current] += [
            call(ident, "Read", {"file_path": str(self.workspace / path)}),
            result(ident, "File does not exist." if error else text, error=error),
        ]

    def grep(self, pattern: str) -> None:
        self.count += 1
        ident = f"toolu_{self.count}"
        self.messages[self.current] += [
            call(ident, "Grep", {"pattern": pattern, "path": str(self.workspace)}),
            result(ident, "1:found"),
        ]

    def finish(self, text: str = "Done.") -> None:
        self.messages[self.current].append({"type": "result", "subtype": "success", "result": text})

    def measure(
        self, number: int, part: int, content: str | None = None, outcome: str = "success"
    ) -> str:
        """Run the measuring step for one session, whose action step ended with the outcome
        given; its log."""
        execution = self.tmp_path / f"claude-execution-{number}-{part}.json"
        execution.write_text(
            json.dumps(self.messages.get((number, part), [])) if content is None else content,
            encoding="utf-8",
        )
        env = {"EXECUTION_FILE": str(execution), "ROUND": str(number), "PART": str(part),
               "OUTCOME": outcome}  # fmt: skip
        done = run_step(measure_step(review()), self.tmp_path, self.tmp_path, env)
        assert done.returncode == 0, done.stdout + done.stderr
        return done.stdout

    def gather(self, next_round: str = "") -> tuple[dict[str, str], str, str]:
        """Run the gathering step; its outputs, the run summary and the log."""
        outputs = self.tmp_path / "outputs"
        summary = self.tmp_path / "summary.md"
        outputs.write_text("", encoding="utf-8")
        summary.write_text("", encoding="utf-8")
        env = {"GITHUB_OUTPUT": str(outputs), "GITHUB_STEP_SUMMARY": str(summary)}
        if next_round:
            env["NEXT_ROUND"] = next_round
        done = run_step(gather_step(review()), self.tmp_path, self.tmp_path, env)
        assert done.returncode == 0, done.stdout + done.stderr
        said = dict(line.split("=", 1) for line in outputs.read_text(encoding="utf-8").splitlines())
        return said, summary.read_text(encoding="utf-8"), done.stdout

    def run(self, content: str | None = None) -> tuple[str, list[Any], str, str]:
        """Measure every session planned, then gather: the coverage and unread outputs, the run
        summary, and the log."""
        for number in (1, 2, 3):
            path = self.kept / f"round-{number}.json"
            if path.exists():
                plan = json.loads(path.read_text(encoding="utf-8"))
                for item in plan["parts"]:
                    self.measure(number, item["part"], content)
        said, summary, out = self.gather()
        self.code = said["code"]
        self.unmeasured = json.loads(said["unmeasured"])
        return said["coverage"], json.loads(said["unread"]), summary, out

    def follow_up(self, next_round: str) -> list[dict[str, Any]]:
        """Measure the sessions so far, then plan the next round: its matrix, and its list kept
        where its sessions find it."""
        for number in range(1, int(next_round)):
            path = self.kept / f"round-{number}.json"
            plan = json.loads(path.read_text(encoding="utf-8"))
            for item in plan["parts"]:
                self.measure(number, item["part"])
        said, _, _ = self.gather(next_round)
        made = self.tmp_path / "runner-temp" / "next" / f"round-{next_round}.json"
        if made.exists():
            (self.kept / made.name).write_bytes(made.read_bytes())
        return json.loads(said["parts"])  # type: ignore[no-any-return]


def listed(
    path: str, status: str, *targets: tuple[str, int], kind: str | None = ""
) -> dict[str, Any]:
    """A listed file, as the plan step lists it; its kind source and test unless given, or none
    when it has no line to read."""
    lines = sum(n for _, n in targets)
    entry: dict[str, Any] = {
        "path": path,
        "status": status,
        "targets": [
            {"path": p, "lines": n, "bytes": n * 10,
             "reads": [{"offset": 1, "limit": n}] if n else []}
            for p, n in targets
        ],
    }  # fmt: skip
    if kind is None or not lines:
        return entry
    return {**entry, "kind": kind or "source and test"}


def code(path: str, read: str) -> dict[str, str]:
    return {"path": path, "read": read, "kind": "source and test"}


MODIFIED = listed("src/a.py", "modified", ("src/a.py", 30), (".review-diff/src/a.py.diff", 12))
ADDED = listed("src/b.py", "added", ("src/b.py", 2500))
SKIPPED = {"path": "uv.lock", "status": "modified", "skipped": "on the skip list", "targets": []}
PROSE_ONLY = listed(
    "README.md", "modified", ("README.md", 40), (".review-diff/README.md.diff", 6), kind="prose"
)


def test_every_target_read_is_complete(tmp_path: Path) -> None:
    session = Session(tmp_path, [MODIFIED, ADDED, SKIPPED])
    session.read("src/a.py", range(1, 31))
    session.read(".review-diff/src/a.py.diff", range(1, 13))
    session.read("src/b.py", range(1, 2005))
    session.read("src/b.py", range(2001, 2502))
    session.finish()
    coverage, unread, summary, _ = session.run()
    assert (coverage, unread, session.code) == ("complete", [], "all")
    assert "| src/a.py | modified | source and test | in full |" in summary
    assert "| uv.lock | on the skip list | - | nothing to read |" in summary
    assert "Source and test files read in full: 2 of 2." in summary


def test_two_reads_that_leave_a_gap_are_in_part(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED])
    session.read("src/b.py", range(1, 1001))
    session.read("src/b.py", range(1501, 2501))
    coverage, unread, _, out = session.run()
    assert (coverage, unread) == ("incomplete", [code("src/b.py", "in part")])
    assert "  in part (source and test): src/b.py" in out.splitlines()


def test_a_modified_file_whose_diff_was_read_but_not_the_file_is_in_part(tmp_path: Path) -> None:
    session = Session(tmp_path, [MODIFIED])
    session.read(".review-diff/src/a.py.diff", range(1, 13))
    assert session.run()[:2] == ("incomplete", [code("src/a.py", "in part")])
    assert session.code == "unread"


def test_a_read_that_failed_counts_for_nothing(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED])
    session.read("src/b.py", range(1, 2501), error=True)
    assert session.run()[:2] == ("incomplete", [code("src/b.py", "not read")])


def test_the_earlier_arrow_numbering_counts_too(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED])
    session.read("src/b.py", range(1, 2501), arrow=True)
    assert session.run()[:2] == ("complete", [])


def test_an_unchanged_file_read_is_reported_not_counted(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED])
    session.read("src/caller.py", range(1, 2501))
    session.read(".review-threads.json", range(1, 5))
    session.read(".review-diff/session.json", range(1, 5))
    coverage, unread, summary, _ = session.run()
    assert (coverage, unread) == ("incomplete", [code("src/b.py", "not read")])
    assert "- Read src/caller.py, which the pull request didn't change" in summary
    assert ".review-threads.json" not in summary
    assert "session.json" not in summary


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
    assert session.run()[:2] == ("incomplete", [code("src/b.py", "not read")])


@pytest.mark.parametrize("content", ["not json", '{"type": "result"}', ""])
def test_an_unreadable_record_counts_nothing_as_read(tmp_path: Path, content: str) -> None:
    session = Session(tmp_path, [MODIFIED, SKIPPED])
    coverage, unread, summary, _ = session.run(content)
    assert (coverage, unread, session.code) == (
        "unknown",
        [code("src/a.py", "not read")],
        "unknown",
    )
    assert session.unmeasured == "round 1 part 1"
    assert "Coverage isn't known: no completed record of what round 1 part 1 read" in summary


def test_a_missing_record_leaves_coverage_unknown_naming_the_session(tmp_path: Path) -> None:
    session = Session(tmp_path, [MODIFIED, ADDED], parts={"src/a.py": 1, "src/b.py": 2})
    session.read("src/a.py", range(1, 31))
    session.read(".review-diff/src/a.py.diff", range(1, 13))
    session.measure(1, 1)
    said, _, _ = session.gather()
    assert (said["coverage"], said["code"]) == ("unknown", "unknown")
    assert json.loads(said["unmeasured"]) == "round 1 part 2"


def test_a_missing_record_doesn_t_matter_once_everything_is_read(tmp_path: Path) -> None:
    session = Session(tmp_path, [MODIFIED, ADDED], parts={"src/a.py": 1, "src/b.py": 2})
    session.read("src/a.py", range(1, 31))
    session.read(".review-diff/src/a.py.diff", range(1, 13))
    session.read("src/b.py", range(1, 2501))
    session.measure(1, 1)
    said, _, _ = session.gather()
    assert (said["coverage"], said["code"]) == ("complete", "all")


# A session that fails doesn't fail its job (D10), so the lead's failure must still fail the check,
# even when nothing it was to read is source or test (#299's review).
@pytest.mark.parametrize("outcome", ["failure", "cancelled", ""])
def test_a_lead_session_that_failed_leaves_coverage_unknown(tmp_path: Path, outcome: str) -> None:
    session = Session(tmp_path, [PROSE_ONLY])
    session.read("README.md", range(1, 41))
    session.read(".review-diff/README.md.diff", range(1, 7))
    session.measure(1, 1, outcome=outcome)
    said, summary, _ = session.gather()
    assert (said["coverage"], said["code"]) == ("unknown", "unknown")
    assert json.loads(said["unmeasured"]) == "round 1 part 1"
    assert "no completed record of what round 1 part 1 read" in summary
    done = run_completed(tmp_path, COVERAGE=said["coverage"], CODE=said["code"],
                         UNREAD=said["unread"], UNMEASURED=said["unmeasured"])  # fmt: skip
    assert done.returncode == 1
    assert "no completed record of what round 1 part 1 read" in done.stdout


@pytest.mark.parametrize("files", [[], [SKIPPED]])
def test_a_lead_session_that_left_no_record_fails_even_with_nothing_to_read(
    tmp_path: Path, files: list[dict[str, Any]]
) -> None:
    session = Session(tmp_path, files)
    said, _, _ = session.gather()
    assert (said["coverage"], said["code"]) == ("unknown", "unknown")
    assert json.loads(said["unmeasured"]) == "round 1 part 1"


def test_another_part_that_failed_is_caught_up_by_its_follow_up(tmp_path: Path) -> None:
    session = Session(tmp_path, [MODIFIED, ADDED], parts={"src/a.py": 1, "src/b.py": 2})
    session.read("src/a.py", range(1, 31))
    session.read(".review-diff/src/a.py.diff", range(1, 13))
    session.measure(1, 1)
    session.measure(1, 2, outcome="failure")
    said, _, _ = session.gather("2")
    assert [m["part"] for m in json.loads(said["parts"])] == [1]
    made = tmp_path / "runner-temp" / "next" / "round-2.json"
    (session.kept / made.name).write_bytes(made.read_bytes())
    session.session(2, 1)
    session.read("src/b.py", range(1, 2501))
    session.measure(2, 1)
    said, _, _ = session.gather()
    assert (said["coverage"], said["code"]) == ("complete", "all")


def test_the_measurement_keeps_the_session_s_outcome(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED])
    session.measure(1, 1, outcome="failure")
    kept = json.loads((session.kept / "records" / "coverage-1-1.json").read_text("utf-8"))
    assert (kept["status"], kept["outcome"]) == ("measured", "failure")


def test_a_path_that_holds_a_workflow_command_stays_inside_its_line(tmp_path: Path) -> None:
    hostile = listed("x\n::error::forged", "added", ("x\n::error::forged", 3))
    session = Session(tmp_path, [hostile])
    _, unread, _, out = session.run()
    assert unread == [code("x\n::error::forged", "not read")]
    assert not any(line.startswith("::") for line in out.splitlines()), out


# What the check needs read: every source and test file; prose is reported, and data is left to
# its tests (review-splits-large-prs design D2, D9).
PROSE = listed("README.md", "modified", ("README.md", 40), (".review-diff/README.md.diff", 6),
               kind="prose")  # fmt: skip
SPEC = listed("openspec/changes/x/tasks.md", "added", ("openspec/changes/x/tasks.md", 20),
              kind="prose")  # fmt: skip
FIXTURE = listed(
    "plugins/r/fixtures/ollama/thinking/events.json",
    "modified",
    ("plugins/r/fixtures/ollama/thinking/events.json", 300),
    (".review-diff/plugins/r/fixtures/ollama/thinking/events.json.diff", 40),
    kind="data",
)


def test_every_source_file_read_beside_unread_data_and_prose_needs_only_the_prose(
    tmp_path: Path,
) -> None:
    session = Session(tmp_path, [ADDED, FIXTURE, PROSE, MODIFIED])
    session.read("src/b.py", range(1, 2501))
    session.read("src/a.py", range(1, 31))
    session.read(".review-diff/src/a.py.diff", range(1, 13))
    coverage, unread, summary, out = session.run()
    assert (coverage, session.code) == ("incomplete", "all")
    assert unread == [{"path": "README.md", "read": "not read", "kind": "prose"}]
    assert "| data | left to its tests |" in summary
    assert "Source and test files read in full: 2 of 2." in summary
    assert "1 data file(s) left to their tests" in out


def test_source_read_only_in_part_leaves_the_code_unread(tmp_path: Path) -> None:
    session = Session(tmp_path, [MODIFIED, SPEC])
    session.read("openspec/changes/x/tasks.md", range(1, 21))
    session.read(".review-diff/src/a.py.diff", range(1, 13))
    coverage, unread, _, _ = session.run()
    assert (coverage, session.code) == ("incomplete", "unread")
    assert unread == [code("src/a.py", "in part")]


def test_one_source_file_read_of_two_leaves_the_code_unread(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED, MODIFIED])
    session.read("src/b.py", range(1, 2501))
    coverage, unread, _, _ = session.run()
    assert (coverage, session.code) == ("incomplete", "unread")
    assert unread == [code("src/a.py", "not read")]


def test_everything_read_is_complete(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED, SPEC])
    session.read("src/b.py", range(1, 2501))
    session.read("openspec/changes/x/tasks.md", range(1, 21))
    assert session.run()[:2] == ("complete", [])
    assert session.code == "all"


def test_an_empty_file_read_for_nothing_counts_for_nothing(tmp_path: Path) -> None:
    """An added empty file has one target of 0 lines, which counts as read in full with no Read.
    It has no kind, so it doesn't count among the source and test files (design D2)."""
    empty = listed("src/pkg/__init__.py", "added", ("src/pkg/__init__.py", 0))
    session = Session(tmp_path, [empty, ADDED])
    coverage, unread, summary, _ = session.run()
    assert (coverage, session.code) == ("incomplete", "unread")
    assert unread == [code("src/b.py", "not read")]
    assert "| src/pkg/\\_\\_init\\_\\_.py | added | - | in full |" in summary


def test_only_files_with_nothing_to_read_leave_nothing_to_check(tmp_path: Path) -> None:
    binary = {"path": "img/logo.png", "status": "added", "skipped": "binary", "targets": []}
    session = Session(tmp_path, [SKIPPED, binary])
    assert session.run()[:2] == ("complete", [])
    assert session.code == "none"


def test_no_source_or_test_file_changed_leaves_only_prose_to_report(tmp_path: Path) -> None:
    session = Session(tmp_path, [PROSE, SPEC, FIXTURE])
    session.read("openspec/changes/x/tasks.md", range(1, 21))
    coverage, unread, _, _ = session.run()
    assert (coverage, session.code) == ("incomplete", "none")
    assert unread == [{"path": "README.md", "read": "not read", "kind": "prose"}]


# The follow-up rounds (review-splits-large-prs design D4, D10).
def test_a_follow_up_round_takes_only_the_source_and_test_files_left_unread(
    tmp_path: Path,
) -> None:
    session = Session(tmp_path, [ADDED, MODIFIED, PROSE, FIXTURE])
    session.read("src/b.py", range(1, 2501))
    session.read(".review-diff/src/a.py.diff", range(1, 13))
    matrix = session.follow_up("2")
    plan = json.loads((session.kept / "round-2.json").read_text(encoding="utf-8"))
    assert plan["assign"] == {"src/a.py": 1}
    assert [(m["round"], m["part"], m["of"]) for m in matrix] == [(2, 1, 1)]
    # Its turns are its own: the base and two Reads, the file and its diff.
    assert matrix[0]["max_turns"] == 44
    listing = (session.kept / "files.json").read_bytes()
    assert matrix[0]["files_sha256"] == hashlib.sha256(listing).hexdigest()
    assert (
        matrix[0]["round_sha256"]
        == hashlib.sha256((session.kept / "round-2.json").read_bytes()).hexdigest()
    )


def test_no_follow_up_when_every_source_and_test_file_was_read(tmp_path: Path) -> None:
    session = Session(tmp_path, [ADDED, PROSE])
    session.read("src/b.py", range(1, 2501))
    assert session.follow_up("2") == []
    assert not (session.kept / "round-2.json").exists()


def test_a_session_whose_record_is_missing_has_its_files_read_again(tmp_path: Path) -> None:
    session = Session(tmp_path, [MODIFIED, ADDED], parts={"src/a.py": 1, "src/b.py": 2})
    session.read("src/a.py", range(1, 31))
    session.read(".review-diff/src/a.py.diff", range(1, 13))
    session.measure(1, 1)
    said, _, out = session.gather("2")
    assert [m["part"] for m in json.loads(said["parts"])] == [1]
    plan = json.loads((tmp_path / "runner-temp" / "next" / "round-2.json").read_text("utf-8"))
    assert plan["assign"] == {"src/b.py": 1}
    assert "by session(s) whose record is missing: round 1 part 2" in out


def test_a_file_read_across_two_rounds_is_read_in_full(tmp_path: Path) -> None:
    session = Session(tmp_path, [MODIFIED])
    session.read(".review-diff/src/a.py.diff", range(1, 13))
    assert session.follow_up("2") != []
    session.session(2, 1)
    session.read("src/a.py", range(1, 31))
    coverage, unread, summary, _ = session.run()
    assert (coverage, unread, session.code) == ("complete", [], "all")
    assert "Sessions: round 1 part 1, round 2 part 1." in summary


def test_round_three_takes_what_round_two_left(tmp_path: Path) -> None:
    session = Session(tmp_path, [MODIFIED, ADDED])
    assert len(session.follow_up("2")) == 1
    session.session(2, 1)
    session.read("src/b.py", range(1, 2501))
    matrix = session.follow_up("3")
    plan = json.loads((session.kept / "round-3.json").read_text(encoding="utf-8"))
    assert plan["assign"] == {"src/a.py": 1}
    assert [m["round"] for m in matrix] == [3]


def test_source_unread_after_round_three_leaves_the_code_unread(tmp_path: Path) -> None:
    session = Session(tmp_path, [MODIFIED])
    session.follow_up("2")
    session.follow_up("3")
    coverage, unread, _, _ = session.run()
    assert (coverage, session.code) == ("incomplete", "unread")
    assert unread == [code("src/a.py", "not read")]


@pytest.mark.parametrize("value", ["4", "x", "1"])
def test_a_round_that_isn_t_two_or_three_fails_the_planner(tmp_path: Path, value: str) -> None:
    Session(tmp_path, [ADDED])
    outputs = tmp_path / "outputs"
    outputs.write_text("", encoding="utf-8")
    env = {"GITHUB_OUTPUT": str(outputs), "NEXT_ROUND": value}
    done = run_step(gather_step(review(), "follow-1"), tmp_path, tmp_path, env)
    assert done.returncode == 1
    assert done.stdout.startswith("::error title=Round unknown::")


def test_the_planners_and_the_report_gather_with_one_script() -> None:
    w = review()
    scripts = {str(gather_step(w, name)["run"]) for name in ("follow-1", "follow-2", "resolve")}
    assert len(scripts) == 1


def function(source: str, name: str) -> str:
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.unparse(node)


def constants(source: str, names: set[str]) -> dict[str, object]:
    found = {}
    for node in ast.parse(source).body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in names
        ):
            found[node.targets[0].id] = ast.literal_eval(node.value)
    return found


def test_the_planners_split_and_budget_as_the_plan_step_does() -> None:
    w = review()
    plan, gathered = str(plan_step(w)["run"]), str(gather_step(w)["run"])
    for name in ("pack", "size"):
        assert function(plan, name) == function(gathered, name), name
    limits = {"BASE_TURNS", "TURNS_PER_READ", "MAX_TURNS", "PART_READS", "MAX_PARTS"}
    assert constants(plan, limits) == constants(gathered, limits)
    assert set(constants(plan, limits)) == limits


# The session's own list, checked against its matrix entry before Claude starts
# (review-splits-large-prs design D4, D5).
def run_session(
    tmp_path: Path, files: list[dict[str, Any]], plan: dict[str, Any], **env: str
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any] | None]:
    folder = tmp_path / "workspace" / ".review-diff"
    folder.mkdir(parents=True, exist_ok=True)
    listing = json.dumps({"files": files}).encode()
    number = int(env["ROUND"]) if env.get("ROUND", "").isdigit() else 1
    rounds = json.dumps(plan).encode()
    (folder / "files.json").write_bytes(listing)
    (folder / f"round-{number}.json").write_bytes(rounds)
    given = {"ROUND": "1", "PART": "1", "OF": "1",
             "FILES_SHA256": hashlib.sha256(listing).hexdigest(),
             "ROUND_SHA256": hashlib.sha256(rounds).hexdigest(), **env}  # fmt: skip
    done = run_step(session_step(review()), tmp_path, tmp_path, given)
    made = folder / "session.json"
    return done, json.loads(made.read_text(encoding="utf-8")) if made.exists() else None


THREE = [ADDED, MODIFIED, PROSE, FIXTURE]
THREE_PLAN = {"round": 1, "assign": {"src/b.py": 1, "README.md": 1, "src/a.py": 2}, "parts": []}


@pytest.mark.parametrize(
    ("number", "part", "role", "paths"),
    [
        ("1", "1", "lead", ["src/b.py", "README.md"]),
        ("1", "2", "part", ["src/a.py"]),
        ("2", "1", "follow-up", ["src/b.py", "README.md"]),
    ],
)
def test_each_session_is_told_its_role_and_its_own_list(
    tmp_path: Path, number: str, part: str, role: str, paths: list[str]
) -> None:
    done, made = run_session(tmp_path, THREE, THREE_PLAN, ROUND=number, PART=part, OF="2")
    assert done.returncode == 0, done.stdout + done.stderr
    assert made is not None
    assert (made["role"], made["round"], made["part"], made["of"]) == (role, int(number),
                                                                       int(part), 2)  # fmt: skip
    assert [f["path"] for f in made["read"]] == sorted(paths, key=[f["path"] for f in THREE].index)
    assert made["data"] == [FIXTURE["path"]]
    kept = tmp_path / "runner-temp" / "review"
    assert (kept / "files.json").exists()
    assert (kept / f"round-{number}.json").exists()


@pytest.mark.parametrize(
    ("env", "said"),
    [
        ({"FILES_SHA256": "0" * 64}, "files.json isn't the file its job planned"),
        ({"ROUND_SHA256": ""}, "round-1.json isn't the file its job planned"),
        ({"ROUND": "x"}, "ROUND is 'x', not a number"),
        ({"PART": "0"}, "PART is '0', not a number"),
    ],
)
def test_a_plan_that_isn_t_the_one_planned_fails_before_claude(
    tmp_path: Path, env: dict[str, str], said: str
) -> None:
    done, made = run_session(tmp_path, THREE, THREE_PLAN, **env)
    assert done.returncode == 1
    assert done.stdout.startswith("::error title=Plan not read::")
    assert said in done.stdout
    assert made is None


# What Claude gave back, kept for the report (review-splits-large-prs design D6).
@pytest.mark.parametrize(
    ("given", "kept"),
    [
        ('{"summary": "s", "resolve": [], "retier": []}', {"summary": "s", "resolve": [],
                                                           "retier": []}),
        ("", None),
        ("not json", None),
        ("[1]", None),
    ],
)  # fmt: skip
def test_claude_s_answer_is_kept_or_kept_as_missing(
    tmp_path: Path, given: str, kept: object
) -> None:
    env = {"STRUCTURED_OUTPUT": given, "ROUND": "2", "PART": "3"}
    done = run_step(answer_step(review()), tmp_path, tmp_path, env)
    assert done.returncode == 0, done.stdout + done.stderr
    path = tmp_path / "runner-temp" / "review" / "records" / "answer-2-3.json"
    assert json.loads(path.read_text(encoding="utf-8")) == {"round": 2, "part": 3, "answer": kept}


def test_the_measurement_never_reads_claude_s_answer() -> None:
    w = review()
    assert "STRUCTURED_OUTPUT" not in str(measure_step(w)["run"])
    assert "STRUCTURED_OUTPUT" not in measure_step(w)["env"]
    assert "structured_output" not in str(gather_step(w)["run"])


# The review's one summary (review-splits-large-prs design D6).
def run_post(
    tmp_path: Path, answers: Mapping[tuple[int, int], object], gathered: dict[str, Any]
) -> tuple[subprocess.CompletedProcess[str], str, list[list[str]]]:
    records = tmp_path / "runner-temp" / "review" / "records"
    records.mkdir(parents=True, exist_ok=True)
    (records.parent / "gathered.json").write_text(json.dumps(gathered), encoding="utf-8")
    for (number, part), answer in answers.items():
        kept = {"round": number, "part": part, "answer": answer}
        (records / f"answer-{number}-{part}.json").write_text(json.dumps(kept), encoding="utf-8")
    bin_dir = stub_gh(tmp_path / "bin", {})
    done = run_step(poster(review()), tmp_path, bin_dir, {"HEAD_SHA": "0123456789abcdef"})
    body = tmp_path / "runner-temp" / "review-summary.md"
    return done, body.read_text(encoding="utf-8") if body.exists() else "", gh_calls(bin_dir)


GATHERED = {"coverage": "incomplete", "code": 3, "read_code": 3, "unmeasured": "",
            "unread": [{"path": "README.md", "read": "not read", "kind": "prose"}],
            "data": ["fixtures/a.json"], "sessions": [[1, 1], [1, 2], [2, 1]]}  # fmt: skip


def test_one_comment_holds_every_session_s_summary_and_what_was_read(tmp_path: Path) -> None:
    answers = {(1, 1): {"summary": "No findings in part one."},
               (1, 2): {"summary": "One must-fix in part two."},
               (2, 1): {"summary": "Read what was left."}}  # fmt: skip
    done, body, calls = run_post(tmp_path, answers, GATHERED)
    assert done.returncode == 0, done.stdout + done.stderr
    assert len(calls) == 1
    assert calls[0][:5] == ["pr", "comment", "7", "-R", "troupe-run/infrastructure"]
    assert calls[0][5:] == ["--body-file", str(tmp_path / "runner-temp" / "review-summary.md")]
    assert body.startswith("## Claude's review of 0123456789ab\n")
    order = ["### Part 1 of 2", "No findings in part one.", "### Part 2 of 2",
             "One must-fix in part two.", "### Follow-up 1, part 1 of 1", "Read what was left.",
             "Source and test files read in full: 3 of 3", "Prose not read in full: `README.md`",
             "Data left to the code and tests that use it: `fixtures/a.json`"]  # fmt: skip
    at = [body.index(text) for text in order]
    assert at == sorted(at)


def test_a_missing_summary_is_named_in_the_comment(tmp_path: Path) -> None:
    done, body, _ = run_post(tmp_path, {(1, 1): {"summary": "x"}, (1, 2): None}, GATHERED)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "_Part 2 of 2's summary is missing: the session gave back no summary._" in body
    assert "_Follow-up 1, part 1 of 1's summary is missing" in body


def test_one_session_s_summary_stands_alone(tmp_path: Path) -> None:
    gathered = {**GATHERED, "sessions": [[1, 1]], "unread": [], "data": []}
    done, body, _ = run_post(tmp_path, {(1, 1): {"summary": "Nothing found."}}, gathered)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "### Part" not in body
    assert "Nothing found." in body


def test_unknown_coverage_is_said_in_the_comment(tmp_path: Path) -> None:
    gathered = {**GATHERED, "coverage": "unknown", "unmeasured": "round 1 part 2",
                "unread": [code("src/a.py", "not read")]}  # fmt: skip
    _, body, _ = run_post(tmp_path, {}, gathered)
    assert "Coverage isn't known: no completed record of what round 1 part 2 read." in body
    assert "Source and test files not read in full: `src/a.py`." in body


def test_without_what_was_gathered_nothing_is_posted(tmp_path: Path) -> None:
    (tmp_path / "runner-temp" / "review").mkdir(parents=True)
    bin_dir = stub_gh(tmp_path / "bin", {})
    done = run_step(poster(review()), tmp_path, bin_dir, {"HEAD_SHA": "x"})
    assert done.returncode == 1
    assert gh_calls(bin_dir) == []


# The check judges what the sessions read together (review-splits-large-prs design D9).
SOURCE_UNREAD = [
    code("src/a.py", "in part"),
    {"path": "README.md", "read": "not read", "kind": "prose"},
    code("src/b.py", "not read"),
]


def warnings_and_errors(out: str) -> list[str]:
    return [line for line in out.splitlines() if line.startswith(("::warning", "::error"))]


@pytest.mark.parametrize(
    ("results", "said"),
    [
        (
            {"COVERAGE": "unknown", "CODE": "unknown", "UNMEASURED": '"round 1 part 2"'},
            "couldn't be measured (no completed record of what round 1 part 2 read), so nothing "
            "they were to read counts as read",
        ),
        (
            {"COVERAGE": "unknown", "CODE": "all"},
            "couldn't be measured, so nothing they were to read counts as read",
        ),
        ({"COVERAGE": "", "CODE": "all"}, "wasn't measured"),
        ({"COVERAGE": "complete-ish", "CODE": "all"}, "wasn't measured"),
        ({"COVERAGE": "incomplete", "CODE": ""}, "wasn't measured"),
        # The floor's word from before: no longer one the check accepts.
        ({"COVERAGE": "complete", "CODE": "read"}, "wasn't measured"),
    ],
)
def test_coverage_that_wasn_t_measured_fails_naming_the_files(
    tmp_path: Path, results: dict[str, str], said: str
) -> None:
    done = run_completed(tmp_path, **results, UNREAD=json.dumps(SOURCE_UNREAD))
    assert done.returncode == 1
    assert done.stdout.startswith("::error title=Review didn't read the code::")
    assert (
        f"what it read {said}: src/a.py (in part), README.md (not read), src/b.py (not read)."
        in done.stdout
    )
    assert "gh run rerun 41258918187" in done.stdout


def test_a_review_that_left_code_unread_fails_naming_only_the_code(tmp_path: Path) -> None:
    done = run_completed(
        tmp_path, COVERAGE="incomplete", CODE="unread", UNREAD=json.dumps(SOURCE_UNREAD)
    )
    assert done.returncode == 1
    assert warnings_and_errors(done.stdout) == done.stdout.splitlines()[:1]
    assert done.stdout.startswith("::error title=Review didn't read the code::")
    assert (
        "its sessions didn't read every changed source and test file in full: src/a.py (in "
        "part), src/b.py (not read)." in done.stdout
    )
    assert "README.md" not in done.stdout
    assert "smaller" not in done.stdout
    assert "gh run rerun 41258918187" in done.stdout


def test_code_unread_fails_even_when_coverage_says_complete(tmp_path: Path) -> None:
    done = run_completed(tmp_path, COVERAGE="complete", CODE="unread", UNREAD="[]")
    assert done.returncode == 1
    assert ": files unnamed." in done.stdout


def test_a_review_that_left_only_prose_unread_passes_with_one_warning(tmp_path: Path) -> None:
    unread = [{"path": "README.md", "read": "not read", "kind": "prose"}]
    done = run_completed(tmp_path, COVERAGE="incomplete", CODE="all", UNREAD=json.dumps(unread))
    assert done.returncode == 0, done.stdout
    found = warnings_and_errors(done.stdout)
    assert len(found) == 1, done.stdout
    assert found[0].startswith("::warning title=Review didn't read every changed file::")
    assert "didn't read every changed prose file in full: README.md (not read)." in found[0]


def test_a_pull_request_with_no_changed_code_passes_with_a_warning(tmp_path: Path) -> None:
    unread = [{"path": "README.md", "read": "not read", "kind": "prose"}]
    done = run_completed(tmp_path, COVERAGE="incomplete", CODE="none", UNREAD=json.dumps(unread))
    assert done.returncode == 0, done.stdout
    found = warnings_and_errors(done.stdout)
    assert len(found) == 1, done.stdout
    assert found[0].startswith("::warning"), done.stdout
    assert "README.md (not read)" in found[0]


@pytest.mark.parametrize("found_code", ["all", "none"])
def test_a_review_that_read_everything_passes_with_no_warning(
    tmp_path: Path, found_code: str
) -> None:
    done = run_completed(tmp_path, COVERAGE="complete", CODE=found_code, UNREAD="[]")
    assert done.returncode == 0, done.stdout
    assert warnings_and_errors(done.stdout) == []


@pytest.mark.parametrize(("results", "outcome"), [({"CODE": "all"}, 0), ({"CODE": "unread"}, 1)])
def test_an_unread_list_that_isn_t_one_names_files_unnamed(
    tmp_path: Path, results: dict[str, str], outcome: int
) -> None:
    done = run_completed(tmp_path, COVERAGE="incomplete", UNREAD="not json", **results)
    assert done.returncode == outcome
    assert ": files unnamed." in done.stdout


def test_an_unread_item_without_its_kind_names_files_unnamed(tmp_path: Path) -> None:
    unread = [{"path": "src/a.py", "read": "in part"}]
    done = run_completed(tmp_path, COVERAGE="incomplete", CODE="unread", UNREAD=json.dumps(unread))
    assert done.returncode == 1
    assert ": files unnamed." in done.stdout


@pytest.mark.parametrize(
    ("found_code", "kind", "outcome"), [("all", "prose", 0), ("unread", "source and test", 1)]
)
def test_more_than_fifty_unread_files_are_cut_short(
    tmp_path: Path, found_code: str, kind: str, outcome: int
) -> None:
    unread = [{"path": f"f{i}.py", "read": "not read", "kind": kind} for i in range(60)]
    done = run_completed(
        tmp_path, COVERAGE="incomplete", CODE=found_code, UNREAD=json.dumps(unread)
    )
    assert done.returncode == outcome
    assert "f49.py (not read), and 10 more." in done.stdout
    assert "f50.py" not in done.stdout


@pytest.mark.parametrize(
    ("found_code", "kind", "outcome"), [("all", "prose", 0), ("unread", "source and test", 1)]
)
def test_a_hostile_unread_path_stays_inside_its_one_line(
    tmp_path: Path, found_code: str, kind: str, outcome: int
) -> None:
    unread = [{"path": "x\n::notice::forged", "read": "not read", "kind": kind}]
    done = run_completed(
        tmp_path, COVERAGE="incomplete", CODE=found_code, UNREAD=json.dumps(unread)
    )
    assert done.returncode == outcome
    assert len([line for line in done.stdout.splitlines() if line.startswith("::")]) == 1
    assert "::notice" not in "\n".join(
        line for line in done.stdout.splitlines() if not line.startswith(("::warning", "::error"))
    )


def test_a_bot_s_pull_request_passes_whatever_the_coverage(tmp_path: Path) -> None:
    done = run_completed(tmp_path, AUTHOR_TYPE="Bot", REVIEW="skipped", COVERAGE="", CODE="")
    assert done.returncode == 0, done.stdout


def test_a_review_that_says_it_didn_t_read_the_code_fails_the_check(tmp_path: Path) -> None:
    """#268: troupe#283's reviews said "not checked" for its code and still passed. A review whose
    sessions read only the task list, and say so, leaves the check failed, naming the code they
    didn't read, whatever their summaries say."""
    files = [
        MODIFIED,
        ADDED,
        listed(
            "openspec/changes/x/tasks.md",
            "modified",
            ("openspec/changes/x/tasks.md", 20),
            (".review-diff/openspec/changes/x/tasks.md.diff", 8),
            kind="prose",
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
    assert (coverage, session.code) == ("incomplete", "unread")
    done = run_completed(tmp_path, COVERAGE=coverage, CODE=session.code, UNREAD=json.dumps(unread))
    assert done.returncode == 1
    assert "src/a.py (not read), src/b.py (not read)." in done.stdout
    assert "tasks.md" not in done.stdout


# troupe#318's 23 files (troupe-run/infrastructure#281): four of its five review runs failed on
# coverage alone with nothing open. Each is rebuilt from its run's unread list. Its fixtures are
# data now; what's left is its code (review-splits-large-prs design D2).
PR_318_SOURCE = [
    "plugins/runner-ollama/src/troupe_runner_ollama/conversation.py",
]
PR_318_TESTS = [
    "plugins/runner-ollama/tests/fake_ollama.py",
    "plugins/runner-ollama/tests/test_ollama_conversation.py",
    "plugins/runner-ollama/tests/test_ollama_conversation_properties.py",
    "plugins/runner-ollama/tests/test_ollama_fake.py",
]
PR_318_FIXTURES = [
    f"plugins/runner-ollama/fixtures/ollama/{case}/{name}.json"
    for case in (
        "network-retries",
        "refused-by-effects",
        "server-retries",
        "success-with-tools",
        "thinking",
    )
    for name in ("events", "provenance")
]
PR_318_PROSE = ["contributing/runners.md", "plugins/runner-ollama/README.md"]
PR_318_SPECS = [
    f"openspec/changes/archive/2026-11-07-ollama-cache-read-tokens/{name}"
    for name in (
        ".openspec.yaml",
        "design.md",
        "proposal.md",
        "specs/ollama-runner/spec.md",
        "tasks.md",
    )
] + ["openspec/specs/ollama-runner/spec.md"]


def pr_318_kind(path: str) -> str:
    if path in PR_318_FIXTURES:
        return "data"
    return "prose" if path in PR_318_PROSE + PR_318_SPECS else "source and test"


def pr_318_session(tmp_path: Path, in_part: list[str], not_read: list[str]) -> Session:
    """A session over #318's files, each modified (the file and its diff), that read every one in
    full except those given: the diff alone for one in part, nothing for one not read."""
    paths = PR_318_SOURCE + PR_318_TESTS + PR_318_FIXTURES + PR_318_PROSE + PR_318_SPECS
    assert len(paths) == 23
    session = Session(
        tmp_path / "session",
        [listed(p, "modified", (p, 50), (f".review-diff/{p}.diff", 10), kind=pr_318_kind(p))
         for p in paths],
    )  # fmt: skip
    for path in paths:
        if path in not_read:
            continue
        session.read(f".review-diff/{path}.diff", range(1, 11))
        if path not in in_part:
            session.read(path, range(1, 51))
    return session


@pytest.mark.parametrize(
    ("run", "in_part", "not_read"),
    [
        # c6c651b, run 42378496586, and f6566be, run 42379121357: the 10 fixtures not read.
        ("c6c651b", [], PR_318_FIXTURES),
        # c6c651b's re-run: the 10 fixtures in part.
        ("c6c651b re-run", PR_318_FIXTURES, []),
        ("f6566be", [], PR_318_FIXTURES),
    ],
)
def test_troupe_318_s_runs_that_skipped_only_fixtures_pass_with_no_warning(
    tmp_path: Path, run: str, in_part: list[str], not_read: list[str]
) -> None:
    session = pr_318_session(tmp_path, in_part, not_read)
    session.finish("No findings.")
    assert session.follow_up("2") == [], run
    coverage, unread, _, _ = session.run()
    assert (coverage, session.code, unread) == ("complete", "all", []), run
    done = run_completed(tmp_path, COVERAGE=coverage, CODE=session.code, UNREAD=json.dumps(unread))
    assert done.returncode == 0, done.stdout
    assert warnings_and_errors(done.stdout) == []


def test_troupe_318_s_run_that_skimmed_its_tests_gets_a_follow_up_over_them(
    tmp_path: Path,
) -> None:
    # 78688ad, run 42369296173: 16 in part (fixtures, the README, contributing/runners.md and the
    # four test files).
    session = pr_318_session(tmp_path, PR_318_FIXTURES + PR_318_PROSE + PR_318_TESTS, [])
    matrix = session.follow_up("2")
    plan = json.loads((session.kept / "round-2.json").read_text(encoding="utf-8"))
    assert sorted(plan["assign"]) == sorted(PR_318_TESTS)
    assert len(matrix) == 1
    session.session(2, 1)
    for path in PR_318_TESTS:
        session.read(path, range(1, 51))
    coverage, unread, _, _ = session.run()
    assert (coverage, session.code) == ("incomplete", "all")
    assert sorted(u["path"] for u in unread) == sorted(PR_318_PROSE)
    done = run_completed(tmp_path, COVERAGE=coverage, CODE=session.code, UNREAD=json.dumps(unread),
                         FOLLOW_1_PARTS=json.dumps(matrix), REVIEW_2="success",
                         FOLLOW_2="success", FOLLOW_2_PARTS="[]")  # fmt: skip
    assert done.returncode == 0, done.stdout
    assert len(warnings_and_errors(done.stdout)) == 1


# troupe#325 (run 43017411898): each of three attempts' sessions stopped by itself after 13 to 47
# of 210 turns, having read some prose and none of its 16 source and test files in full. A
# follow-up round now reads them (review-splits-large-prs design D10, proposal's table).
def pr_325_session(tmp_path: Path) -> Session:
    files = (
        [listed(p, "modified", (p, 40), (f".review-diff/{p}.diff", 8)) for p in PR_325_CODE]
        + [listed(p, "modified", (p, 30), (f".review-diff/{p}.diff", 6), kind="data")
           for p in PR_325_SCHEMAS]
        + [listed(p, "modified", (p, 60), (f".review-diff/{p}.diff", 9), kind="prose")
           for p in PR_325_PROSE]
    )  # fmt: skip
    session = Session(tmp_path / "session", files)
    # Attempt 3: seven prose files in full, and the diffs of the source files.
    for path in PR_325_PROSE[:7]:
        session.read(path, range(1, 61))
        session.read(f".review-diff/{path}.diff", range(1, 10))
    for path in PR_325_CODE:
        session.read(f".review-diff/{path}.diff", range(1, 9))
    session.finish("No findings.")
    return session


def test_troupe_325_s_stopped_session_is_followed_by_one_over_its_code(tmp_path: Path) -> None:
    session = pr_325_session(tmp_path)
    matrix = session.follow_up("2")
    plan = json.loads((session.kept / "round-2.json").read_text(encoding="utf-8"))
    assert sorted(plan["assign"]) == sorted(PR_325_CODE)
    assert [(m["round"], m["part"]) for m in matrix] == [(2, 1)]
    session.session(2, 1)
    for path in PR_325_CODE:
        session.read(path, range(1, 41))
    coverage, unread, summary, _ = session.run()
    assert (coverage, session.code) == ("incomplete", "all")
    assert {u["kind"] for u in unread} == {"prose"}
    assert "Source and test files read in full: 16 of 16." in summary
    done = run_completed(tmp_path, COVERAGE=coverage, CODE=session.code, UNREAD=json.dumps(unread),
                         FOLLOW_1_PARTS=json.dumps(matrix), REVIEW_2="success",
                         FOLLOW_2="success", FOLLOW_2_PARTS="[]")  # fmt: skip
    assert done.returncode == 0, done.stdout


def test_troupe_325_fails_if_its_follow_ups_stop_early_too(tmp_path: Path) -> None:
    session = pr_325_session(tmp_path)
    first = session.follow_up("2")
    second = session.follow_up("3")
    assert len(first) == len(second) == 1
    coverage, unread, _, _ = session.run()
    assert (coverage, session.code) == ("incomplete", "unread")
    done = run_completed(tmp_path, COVERAGE=coverage, CODE=session.code, UNREAD=json.dumps(unread),
                         FOLLOW_1_PARTS=json.dumps(first), REVIEW_2="success", FOLLOW_2="success",
                         FOLLOW_2_PARTS=json.dumps(second), REVIEW_3="success")  # fmt: skip
    assert done.returncode == 1
    assert all(path in done.stdout for path in PR_325_CODE[:10])
