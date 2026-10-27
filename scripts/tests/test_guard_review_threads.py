"""Review findings' tiers, and which conversations an agent may resolve (spec: pr-review,
development-workflow; review-findings-by-severity design D1 and D5)."""

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
