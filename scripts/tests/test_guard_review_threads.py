"""Review findings' tiers, and which conversations an agent may resolve (spec: pr-review,
development-workflow; review-findings-by-severity design D1 and D5)."""

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

import guard

BOT = {"__typename": "Bot", "login": "troupe-run-review"}
# A person could register the App's login as a user account: only a Bot is the review.
NAMESAKE = {"__typename": "User", "login": "troupe-run-review"}
PERSON = {"__typename": "User", "login": "martin-at-hpsgd"}


def comment(author: dict[str, str], body: str) -> dict[str, Any]:
    return {"author": author, "body": body}


# The tier on a comment's first line (D1)


@pytest.mark.parametrize(
    ("body", "tier"),
    [
        ("**must-fix** · merge commits show no paths", "must-fix"),
        ("**nit** · stale path to the archived design", "nit"),
        ("**decision** · probe first, or trust the ruleset?", "decision"),
        ("**nit** · a title\n\nThe body, which can say **must-fix** anywhere.", "nit"),
        ("**must-fix** · a title\r\nA Windows line ending.", "must-fix"),
    ],
)
def test_a_first_line_in_the_fixed_form_names_its_tier(body: str, tier: str) -> None:
    assert guard.review_tier(body) == tier


@pytest.mark.parametrize(
    "body",
    [
        "",
        "merge commits show no paths",
        "**critical** · the old levels aren't tiers",
        "**minor** · nor is this one",
        "**important** · nor this",
        "**must-fix · nit** · two tiers on one line",
        "**must-fix**  ·  extra spaces",
        "**must-fix** - a different separator",
        "**must-fix** ·",
        "**Must-Fix** · another case",
        " **nit** · leading space",
        "A first line\n**nit** · a label that isn't on the first line",
    ],
)
def test_anything_else_has_no_tier(body: str) -> None:
    assert guard.review_tier(body) is None


@pytest.mark.parametrize(
    ("comments", "tier"),
    [
        ([comment(BOT, "**must-fix** · a")], "must-fix"),
        ([comment(BOT, "**nit** · a")], "nit"),
        (
            [comment(BOT, "**must-fix** · a"), comment(PERSON, "both are fine"),
             comment(BOT, "**decision** · both are defensible, so it's the owner's")],
            "decision",
        ),
        (
            [comment(BOT, "**must-fix** · a"), comment(PERSON, "it's only wording"),
             comment(BOT, "**nit** · agreed, wording only")],
            "nit",
        ),
        (
            [comment(BOT, "**nit** · a"), comment(PERSON, "resolved"),
             comment(BOT, "**must-fix** · this does matter: ...")],
            "must-fix",
        ),
        (
            [comment(BOT, "**must-fix** · a"), comment(PERSON, "**nit** · I say it's a nit")],
            "must-fix",
        ),
        (
            [comment(BOT, "**must-fix** · a"), comment(NAMESAKE, "**nit** · a user named alike")],
            "must-fix",
        ),
        (
            [comment(BOT, "**must-fix** · a"), comment(BOT, "Still open: the test is missing.")],
            "must-fix",
        ),
        ([comment(BOT, "no label at all")], None),
        ([comment(PERSON, "**nit** · a person's conversation")], None),
        ([comment(NAMESAKE, "**nit** · a user named like the App")], None),
        ([], None),
    ],
)  # fmt: skip
def test_a_conversation_s_tier_is_the_review_s_latest_label(
    comments: list[dict[str, Any]], tier: str | None
) -> None:
    assert guard.conversation_tier(comments) == tier


def test_a_comment_with_no_author_is_nobody_s() -> None:
    # GitHub gives a deleted account's comments a null author.
    assert guard.conversation_tier([{"author": None, "body": "**nit** · a"}]) is None


# Which conversations an agent may resolve (D5)

GH_RULES = ("owner-only", "gh-allow-list")


def thread(opener: dict[str, str], *comments: dict[str, Any]) -> dict[str, Any]:
    """A review conversation as the guard's lookup returns it."""
    return {
        "__typename": "PullRequestReviewThread",
        "opened": {"nodes": [{"author": opener}]},
        "latest": {"nodes": list(comments)},
    }


THREADS: dict[str, dict[str, Any]] = {
    "PRRT_nit": thread(BOT, comment(BOT, "**nit** · stale path")),
    "PRRT_mustfix": thread(BOT, comment(BOT, "**must-fix** · merge commits show no paths")),
    "PRRT_decision": thread(BOT, comment(BOT, "**decision** · probe first, or trust it?")),
    "PRRT_unlabelled": thread(BOT, comment(BOT, "Merge commits show no paths.")),
    "PRRT_person": thread(PERSON, comment(PERSON, "**nit** · my own comment")),
    "PRRT_namesake": thread(NAMESAKE, comment(NAMESAKE, "**nit** · a user named like the App")),
    "PRRT_downgraded": thread(
        BOT, comment(BOT, "**must-fix** · a"), comment(PERSON, "only wording"),
        comment(BOT, "**nit** · agreed: wording only"),
    ),
    "PRRT_upgraded": thread(
        BOT, comment(BOT, "**nit** · a"), comment(BOT, "**must-fix** · it matters: ..."),
    ),
    "PRRT_escalated": thread(
        BOT, comment(BOT, "**nit** · a"), comment(BOT, "**decision** · it's a real choice"),
    ),
    "PRRT_selfrelabelled": thread(
        BOT, comment(BOT, "**must-fix** · a"), comment(PERSON, "**nit** · I say it's a nit"),
    ),
    # The review's label has scrolled out of the last 100 comments.
    "PRRT_scrolled": thread(BOT, *[comment(PERSON, "a reply")] * 100),
}  # fmt: skip


@pytest.fixture
def lookup(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Answer the guard's lookup from THREADS, and record each conversation it read."""
    read: list[str] = []

    def fake(thread_id: str) -> dict[str, Any] | None:
        read.append(thread_id)
        return THREADS.get(thread_id)

    monkeypatch.setattr(guard, "read_review_thread", fake)
    return read


def resolve(thread_id: str) -> str:
    query = (
        f'mutation {{ resolveReviewThread(input: {{threadId: "{thread_id}"}}) '
        "{ thread { isResolved } } }"
    )
    return f"gh api graphql -f query='{query}'"


def gh_refusal(command: str) -> guard.Decision | None:
    decisions = guard.shell_decisions(command, Path.cwd())
    return next((d for d in decisions if d.rule in GH_RULES), None)


@pytest.mark.parametrize("thread_id", ["PRRT_nit", "PRRT_downgraded"])
def test_an_agent_may_resolve_a_nit(lookup: list[str], thread_id: str) -> None:
    assert gh_refusal(resolve(thread_id)) is None
    assert lookup == [thread_id]


def test_the_conversation_may_be_named_by_a_variable(lookup: list[str]) -> None:
    query = "mutation($t: ID!) { resolveReviewThread(input: {threadId: $t}) { thread { id } } }"
    assert gh_refusal(f"gh api graphql -f query='{query}' -f t=PRRT_nit") is None
    assert gh_refusal(f"gh api graphql -f query='{query}' -F t=PRRT_nit") is None
    assert lookup == ["PRRT_nit", "PRRT_nit"]


@pytest.mark.parametrize("thread_id", ["PRRT_mustfix", "PRRT_upgraded", "PRRT_selfrelabelled"])
def test_a_must_fix_is_the_review_s_to_resolve(lookup: list[str], thread_id: str) -> None:
    refused = gh_refusal(resolve(thread_id))
    assert refused is not None
    assert refused.rule == "gh-allow-list"
    assert "must-fix" in refused.problem
    assert "the review resolves it" in refused.fix
    assert "owner" in refused.fix


@pytest.mark.parametrize(
    ("thread_id", "said"),
    [
        ("PRRT_decision", "a decision"),
        ("PRRT_escalated", "a decision"),
        ("PRRT_unlabelled", "has no tier"),
        ("PRRT_scrolled", "has no tier"),
        ("PRRT_person", "the review didn't open"),
        ("PRRT_namesake", "the review didn't open"),
    ],
)
def test_anything_else_is_the_owner_s(lookup: list[str], thread_id: str, said: str) -> None:
    refused = gh_refusal(resolve(thread_id))
    assert refused is not None
    assert refused.rule == "gh-allow-list"
    assert said in refused.problem
    assert "Ask the owner" in refused.fix


def test_something_that_isn_t_a_conversation_is_refused(lookup: list[str]) -> None:
    refused = gh_refusal(resolve("PRRT_missing"))
    assert refused is not None
    assert "isn't a review conversation" in refused.problem


@pytest.mark.parametrize(
    ("args", "said"),
    [
        # Two conversations in one mutation, or two mutations.
        (
            '-f query=\'mutation { a: resolveReviewThread(input: {threadId: "PRRT_nit"}) { '
            'thread { id } } b: resolveReviewThread(input: {threadId: "PRRT_mustfix"}) { '
            "thread { id } } }'",
            "one conversation",
        ),
        (
            '-f query=\'mutation { resolveReviewThread(input: {threadId: "PRRT_nit"}) { '
            'thread { id } } addComment(input: {subjectId: "I", body: "x"}) { '
            "clientMutationId } }'",
            "one conversation",
        ),
        # A conversation named through a variable that isn't given, or comes from a file.
        (
            "-f query='mutation($t: ID!) { resolveReviewThread(input: {threadId: $t}) { "
            "thread { id } } }'",
            "can't be read",
        ),
        (
            "-f query='mutation($t: ID!) { resolveReviewThread(input: {threadId: $t}) { "
            "thread { id } } }' -F t=@thread.txt",
            "can't be read",
        ),
        # Through --input, whose variables the guard doesn't read.
        ("--input mutation.json", "can't be read"),
    ],
)
def test_a_resolve_the_guard_can_t_pin_to_one_conversation_is_refused(
    lookup: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, args: str, said: str
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "thread.txt").write_text("PRRT_nit", encoding="utf-8")
    body = {
        "query": (
            "mutation($t: ID!) { resolveReviewThread(input: {threadId: $t}) { thread { id } } }"
        ),
        "variables": {"t": "PRRT_nit"},
    }
    (tmp_path / "mutation.json").write_text(json.dumps(body), encoding="utf-8")
    refused = gh_refusal(f"gh api graphql {args}")
    assert refused is not None
    assert refused.rule == "gh-allow-list"
    assert said in refused.problem
    assert lookup == []


def test_reopening_a_conversation_is_refused(lookup: list[str]) -> None:
    query = 'mutation { unresolveReviewThread(input: {threadId: "PRRT_nit"}) { thread { id } } }'
    refused = gh_refusal(f"gh api graphql -f query='{query}'")
    assert refused is not None
    assert refused.rule == "gh-allow-list"
    assert "unresolveReviewThread" in refused.problem
    assert lookup == []


# The lookup itself, through a gh on PATH

STUB = """\
import json, os, sys, time
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "calls.jsonl"), "a", encoding="utf-8") as calls:
    calls.write(json.dumps(sys.argv[1:]) + "\\n")
with open(os.path.join(here, "stub.json"), encoding="utf-8") as file:
    config = json.load(file)
time.sleep(config.get("sleep", 0))
sys.stdout.write(config["stdout"])
sys.exit(config["status"])
"""


def stub_gh(directory: Path, stdout: str, status: int = 0, sleep: float = 0) -> Path:
    """A `gh` on PATH that prints a canned answer: a Python script behind a POSIX shell wrapper,
    or behind gh.cmd on Windows."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "stub.py").write_text(STUB, encoding="utf-8")
    config = {"stdout": stdout, "status": status, "sleep": sleep}
    (directory / "stub.json").write_text(json.dumps(config), encoding="utf-8")
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


def on_path(monkeypatch: pytest.MonkeyPatch, directory: Path) -> None:
    monkeypatch.setenv("PATH", f"{directory}{os.pathsep}{os.environ['PATH']}")


def test_the_lookup_reads_one_conversation_by_its_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    answer = {"data": {"node": THREADS["PRRT_nit"]}}
    on_path(monkeypatch, stub_gh(tmp_path / "bin", json.dumps(answer)))
    assert gh_refusal(resolve("PRRT_nit")) is None
    calls = [
        json.loads(line) for line in (tmp_path / "bin" / "calls.jsonl").read_text().splitlines()
    ]
    assert len(calls) == 1
    assert calls[0][:2] == ["api", "graphql"]
    assert "id=PRRT_nit" in calls[0]
    query = next(arg for arg in calls[0] if arg.startswith("query="))
    assert guard.graphql_mutations(query.partition("=")[2]) == []
    assert "last: 100" in query


@pytest.mark.parametrize(
    ("stdout", "status", "said"),
    [
        ("", 1, "couldn't be read"),
        ("not json", 0, "couldn't be read"),
        (
            json.dumps({"errors": [{"message": "Could not resolve to a node"}]}),
            0,
            "couldn't be read",
        ),
        (json.dumps({"data": {"node": None}}), 0, "isn't a review conversation"),
    ],
)
def test_a_lookup_that_fails_refuses_the_resolve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stdout: str, status: int, said: str
) -> None:
    on_path(monkeypatch, stub_gh(tmp_path / "bin", stdout, status))
    refused = gh_refusal(resolve("PRRT_nit"))
    assert refused is not None
    assert refused.rule == "gh-allow-list"
    assert said in refused.problem


def test_a_lookup_that_outlives_its_timeout_refuses_the_resolve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    on_path(monkeypatch, stub_gh(tmp_path / "bin", "{}", sleep=30))
    monkeypatch.setattr(guard, "REVIEW_LOOKUP_TIMEOUT_SECONDS", 1.0)
    refused = gh_refusal(resolve("PRRT_nit"))
    assert refused is not None
    assert "couldn't be read" in refused.problem
    assert "1 second" in refused.problem


# Replying in a conversation has one way: a review comment in reply to another (D5)


def test_a_reply_in_a_conversation_is_a_review_comment_in_reply_to_its_first() -> None:
    command = (
        "gh api -X POST repos/troupe-run/infrastructure/pulls/7/comments "
        "-F in_reply_to=3012345678 -f body='Fixed in 9d01b6e.'"
    )
    assert gh_refusal(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "gh api -X POST repos/troupe-run/infrastructure/pulls/7/comments/3012345678/replies "
        "-f body='Fixed in 9d01b6e.'",
        "gh api graphql -f query='mutation { addPullRequestReviewThreadReply(input: "
        '{pullRequestReviewThreadId: "PRRT_nit", body: "Fixed."}) { comment { id } } }\'',
    ],
)
def test_the_other_ways_to_reply_are_refused(command: str) -> None:
    refused = gh_refusal(command)
    assert refused is not None
    assert refused.rule == "gh-allow-list"
