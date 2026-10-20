"""The org profile says what tofu/descriptions.json says, and the one-line description fits
(spec: descriptions; align-troupe-descriptions design D1, D2).

OpenTofu reads the tagline and sentence for the org's description and troupe's repository
description. The profile is hand-written Markdown delivered byte for byte, so nothing makes it
follow the declaration: this test does. GitHub refuses an over-long org description only when the
plan is applied, after the merge, so the length is checked here too.
"""

import json

import pytest
from conftest import REPO

pytestmark = pytest.mark.descriptions

DESCRIPTIONS = REPO / "tofu" / "descriptions.json"
PROFILE = REPO / "org-profile" / "profile" / "README.md"

# What GitHub's settings page allows for an org's description.
ORG_DESCRIPTION_LIMIT = 160


def one_line(descriptions: dict[str, str]) -> str:
    """The org's description and troupe's repository description, as OpenTofu joins them."""
    return f"{descriptions['tagline']} {descriptions['sentence']}"


def paragraphs(markdown: str) -> list[str]:
    """Each blank-line-separated block, its wrapped lines joined with single spaces."""
    blocks = [block.split("\n") for block in markdown.replace("\r\n", "\n").split("\n\n")]
    return [" ".join(line.strip() for line in block if line.strip()) for block in blocks]


def profile_problems(profile: str, descriptions: dict[str, str]) -> list[str]:
    """Each declared string the profile doesn't carry where it should. Empty when it matches."""
    found = paragraphs(profile)
    problems = []
    if f"**{descriptions['tagline']}**" not in found:
        problems.append(f"the tagline isn't the profile's bold line: **{descriptions['tagline']}**")
    if not any(paragraph.startswith(descriptions["sentence"]) for paragraph in found):
        problems.append(f"no paragraph starts with the sentence: {descriptions['sentence']}")
    if descriptions["status"] not in found:
        problems.append(f"the status line isn't a paragraph of its own: {descriptions['status']}")
    return problems


def length_problems(descriptions: dict[str, str]) -> list[str]:
    length = len(one_line(descriptions))
    if length <= ORG_DESCRIPTION_LIMIT:
        return []
    return [
        f"the tagline and sentence come to {length} characters; "
        f"an org's description allows {ORG_DESCRIPTION_LIMIT}"
    ]


def load() -> dict[str, str]:
    loaded: dict[str, str] = json.loads(DESCRIPTIONS.read_text(encoding="utf-8"))
    return loaded


def test_the_declaration_has_exactly_the_three_strings() -> None:
    assert sorted(load()) == ["sentence", "status", "tagline"]


def test_the_profile_carries_the_declared_text() -> None:
    assert profile_problems(PROFILE.read_text(encoding="utf-8"), load()) == []


def test_the_one_line_description_fits_the_org_limit() -> None:
    assert length_problems(load()) == []


EXAMPLE = {
    "tagline": "Your agents need a director.",
    "sentence": "troupe runs your development process with a team of agents.",
    "status": "Pre-alpha: there's nothing to install yet.",
}

MATCHING = """# troupe

**Your agents need a director.**

troupe runs your development process with a team of agents. Work branches
and loops.

Pre-alpha: there's nothing to install yet.
"""


def test_a_matching_profile_has_no_problems() -> None:
    assert profile_problems(MATCHING, EXAMPLE) == []


def test_a_profile_with_the_old_sentence_names_the_new_one() -> None:
    old = MATCHING.replace("with a team of agents.", "with agents and people in named roles.")
    assert profile_problems(old, EXAMPLE) == [
        f"no paragraph starts with the sentence: {EXAMPLE['sentence']}"
    ]


def test_a_missing_tagline_and_status_line_are_each_named() -> None:
    bare = "# troupe\n\ntroupe runs your development process with a team of agents.\n"
    assert profile_problems(bare, EXAMPLE) == [
        f"the tagline isn't the profile's bold line: **{EXAMPLE['tagline']}**",
        f"the status line isn't a paragraph of its own: {EXAMPLE['status']}",
    ]


def test_an_over_long_sentence_gives_the_length_and_the_limit() -> None:
    long = {**EXAMPLE, "sentence": "x" * 140}
    assert length_problems(long) == [
        "the tagline and sentence come to 169 characters; an org's description allows 160"
    ]


def test_a_description_at_the_limit_is_accepted() -> None:
    assert length_problems({**EXAMPLE, "sentence": "x" * 131}) == []
