"""The release milestones' declaration is complete and well formed (spec: milestones;
release-milestones design D4).

The plan can't tell a repository that's missing from the list, and GitHub refuses a bad state only
when the plan is applied, after the merge. troupe.run's build reads the file from main and refuses
it on rules of its own, which stops every deploy of the site (check-milestones-json). So all of
these are checked here, offline, on every pull request.
"""

import json
import re
from typing import Any, TypeGuard

import pytest
from conftest import REPO

pytestmark = [pytest.mark.milestones, pytest.mark.tofu]

TOFU = REPO / "tofu"
MILESTONES = TOFU / "milestones.json"
REPOSITORIES_TF = TOFU / "repositories.tf"
STATES = ("open", "closed")
# The typographic quotes a description uses instead of straight ones. They're named because ruff
# (RUF001) rightly flags the characters themselves as easy to mistake
# (typographic-milestone-quotes design D2).
RSQUO = "\N{RIGHT SINGLE QUOTATION MARK}"
LSQUO = "\N{LEFT SINGLE QUOTATION MARK}"
LDQUO = "\N{LEFT DOUBLE QUOTATION MARK}"
RDQUO = "\N{RIGHT DOUBLE QUOTATION MARK}"
APOSTROPHE_FIX = f"use {RSQUO} for an apostrophe or closing quote and {LSQUO} for an opening one"
DOUBLE_QUOTE_FIX = f"use {LDQUO} and {RDQUO}"
# The website's title rule and its messages' fixes (check-milestones-json design D1, D3).
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
BOM = "\N{ZERO WIDTH NO-BREAK SPACE}"
TITLE_FIX = 'title it MAJOR.MINOR.PATCH, with no leading zeros or "v", as in "0.3.0"'
DESCRIPTION_FIX = "describe what the milestone adds for a user"


def refuse_constant(constant: str) -> object:
    raise ValueError(
        f"tofu/milestones.json: {constant} isn't JSON, and troupe.run's build refuses it; "
        "use a number or a string"
    )


def read_declaration(text: str) -> object:
    """The file, parsed as strictly as JSON.parse: Python's json would accept NaN, Infinity and
    -Infinity, which the website's build refuses (check-milestones-json design D1)."""
    return json.loads(text, parse_constant=refuse_constant)


def managed_repositories(repositories_tf: str) -> set[str]:
    """The name given to each top-level `module "repo_*"` call. A text reading, not HCL."""
    names = set()
    for block in re.split(r'^(?=module ")', repositories_tf, flags=re.MULTILINE)[1:]:
        if not block.startswith('module "repo_'):
            continue
        name = re.search(r'^  name\s*=\s*"([^"]+)"', block, re.MULTILINE)
        if name:
            names.add(name.group(1))
    return names


def repository_problems(listed: list[str], managed: set[str]) -> list[str]:
    """Each repository that's managed and not listed, or listed and not managed."""
    found = [
        f"{name}: managed in tofu/repositories.tf but has no milestones; "
        "add it to tofu/milestones.json's repositories"
        for name in sorted(managed - set(listed))
    ]
    found += [
        f"{name}: in tofu/milestones.json's repositories but not managed in tofu/repositories.tf; "
        "remove it from tofu/milestones.json"
        for name in sorted(set(listed) - managed)
    ]
    return found


def shape_problems(declared: object) -> list[str]:
    """The one problem with a file whose top level isn't an object with a milestones array, or none.

    With a shape problem, no other rule runs (check-milestones-json design D3)."""
    if isinstance(declared, dict) and isinstance(declared.get("milestones"), list):
        return []
    return [
        "tofu/milestones.json: isn't an object with a milestones array; "
        "give it a top-level object whose milestones is an array of milestones"
    ]


def is_version(title: object) -> TypeGuard[str]:
    """MAJOR.MINOR.PATCH, ASCII digits only, with no leading zeros and nothing before or after.

    The website's regex is ASCII-only and anchored at the very end; Python's \\d and $ aren't, so
    this uses [0-9] and fullmatch (check-milestones-json design D1)."""
    return isinstance(title, str) and VERSION.fullmatch(title) is not None


def is_blank(text: str) -> bool:
    """Empty, or only whitespace by Python's reckoning or JavaScript's trim(), which also strips
    U+FEFF (check-milestones-json design D1)."""
    return all(char.isspace() or char == BOM for char in text)


def declaration_problems(milestones: list[Any]) -> list[str]:
    """Each entry that isn't an object, each title that isn't a version, each description that's
    empty, each key or title declared twice, each state that isn't open or closed, each interim
    title that's malformed or already taken, and each straight quote in a description.

    A field that's missing or the wrong type is reported by the rule that owns it, and skipped by
    the others, so one bad milestone never crashes the check or hides another's problems."""
    found: list[str] = []
    entries: list[tuple[str, dict[str, Any]]] = []
    for position, entry in enumerate(milestones, start=1):
        if isinstance(entry, dict):
            title = entry.get("title")
            entries.append((title if is_version(title) else f"milestone {position}", entry))
        else:
            found.append(
                f"milestone {position}: isn't an object; "
                "each milestone must be an object with a title and a description"
            )
    # The rules troupe.run's build enforces: readRoadmap in troupe-run/website's
    # scripts/roadmap-lib.mjs (its status-roadmap-releases design D4). A rule changed here must
    # change there too, and the other way round (check-milestones-json design D4).
    for name, entry in entries:
        if "title" not in entry:
            found.append(f"{name}: has no title; {TITLE_FIX}")
        elif not is_version(entry["title"]):
            found.append(f"{name}: title {entry['title']!r} isn't a version; {TITLE_FIX}")
        if "description" not in entry:
            found.append(f"{name}: has no description; {DESCRIPTION_FIX}")
        elif not isinstance(entry["description"], str):
            found.append(
                f"{name}: description is {entry['description']!r}, not text; {DESCRIPTION_FIX}"
            )
        elif is_blank(entry["description"]):
            found.append(f"{name}: description is empty; {DESCRIPTION_FIX}")
    for field in ("key", "title"):
        seen: set[str] = set()
        for _, entry in entries:
            value = entry.get(field)
            if not isinstance(value, str):
                continue
            if value in seen:
                found.append(f"{value}: {field} is declared twice in tofu/milestones.json")
            seen.add(value)
    for name, entry in entries:
        if "state" in entry and entry["state"] not in STATES:
            found.append(
                f"{name}: state is {entry['state']!r}; valid states are {', '.join(STATES)}"
            )
    # Titles and interim titles share GitHub's one namespace per repository
    # (milestone-interim-titles design D3). An interim title that's present but malformed is an
    # error, not "use the title".
    taken = {entry["title"] for _, entry in entries if isinstance(entry.get("title"), str)}
    for name, entry in entries:
        if "interim_title" not in entry:
            continue
        interim = entry["interim_title"]
        if not isinstance(interim, str) or not interim.strip():
            found.append(
                f"{name}: interim title is {interim!r}; an interim title must be a non-empty string"
            )
        elif interim in taken:
            found.append(
                f"{name}: interim title {interim!r} is already a title or interim title in "
                "tofu/milestones.json; an interim title must be one no milestone has"
            )
        else:
            taken.add(interim)
    # troupe.run/status/ shows each description verbatim, and the rest of the site uses
    # typographic quotes (typographic-milestone-quotes design D2). Which one a straight quote
    # should be depends on the sentence, so the message names the choices and fixes nothing.
    for name, entry in entries:
        description = entry.get("description")
        if not isinstance(description, str):
            continue
        if "'" in description:
            found.append(f"{name}: description has a straight apostrophe ('); {APOSTROPHE_FIX}")
        if '"' in description:
            found.append(f'{name}: description has a straight double quote ("); {DOUBLE_QUOTE_FIX}')
    return found


def milestone(
    key: str, title: str | None = None, state: str = "open", **extra: object
) -> dict[str, Any]:
    return {"key": key, "title": title or key, "state": state, "description": "x", **extra}


def test_every_managed_repository_gets_the_milestones_and_no_other() -> None:
    declared = json.loads(MILESTONES.read_text(encoding="utf-8"))
    managed = managed_repositories(REPOSITORIES_TF.read_text(encoding="utf-8"))
    assert managed, "no managed repositories found in tofu/repositories.tf"
    assert repository_problems(declared["repositories"], managed) == []


def test_a_managed_repository_missing_from_the_list_is_named_with_the_file() -> None:
    managed = managed_repositories(REPOSITORIES_TF.read_text(encoding="utf-8"))
    listed = sorted(managed - {"website"})
    assert repository_problems(listed, managed) == [
        "website: managed in tofu/repositories.tf but has no milestones; "
        "add it to tofu/milestones.json's repositories"
    ]


def test_a_listed_repository_that_is_not_managed_is_named() -> None:
    assert repository_problems(["troupe", "gone"], {"troupe"}) == [
        "gone: in tofu/milestones.json's repositories but not managed in tofu/repositories.tf; "
        "remove it from tofu/milestones.json"
    ]


def test_the_declared_milestones_are_well_formed() -> None:
    declared = read_declaration(MILESTONES.read_text(encoding="utf-8"))
    assert shape_problems(declared) == []
    assert isinstance(declared, dict)
    assert declared["milestones"], "tofu/milestones.json declares no milestones"
    assert declaration_problems(declared["milestones"]) == []


def test_a_duplicate_title_is_named() -> None:
    assert declaration_problems([milestone("a", "0.2.0"), milestone("b", "0.2.0")]) == [
        "0.2.0: title is declared twice in tofu/milestones.json"
    ]


def test_a_duplicate_key_is_named() -> None:
    assert declaration_problems([milestone("0.1.0", "0.2.0"), milestone("0.1.0", "0.3.0")]) == [
        "0.1.0: key is declared twice in tofu/milestones.json"
    ]


def test_an_unknown_state_is_an_error_naming_the_valid_ones() -> None:
    assert declaration_problems([milestone("0.1.0", state="done")]) == [
        "0.1.0: state is 'done'; valid states are open, closed"
    ]


def test_a_closed_milestone_is_valid() -> None:
    assert declaration_problems([milestone("0.1.0", state="closed")]) == []


# milestone-interim-titles design D3: titles and interim titles share GitHub's one namespace per
# repository, and a malformed interim title is an error, never a fall-through to the title.


def test_an_interim_title_that_is_another_milestones_title_is_named() -> None:
    found = declaration_problems(
        [milestone("0.2.0", "0.3.0", interim_title="0.4.0"), milestone("0.4.0")]
    )
    assert found == [
        "0.3.0: interim title '0.4.0' is already a title or interim title in "
        "tofu/milestones.json; an interim title must be one no milestone has"
    ]


def test_an_interim_title_that_is_its_own_title_is_named() -> None:
    assert declaration_problems([milestone("0.2.0", interim_title="0.2.0")]) == [
        "0.2.0: interim title '0.2.0' is already a title or interim title in "
        "tofu/milestones.json; an interim title must be one no milestone has"
    ]


def test_two_milestones_with_the_same_interim_title_are_named() -> None:
    found = declaration_problems(
        [
            milestone("0.2.0", "0.3.0", interim_title="moving"),
            milestone("0.3.0", "0.4.0", interim_title="moving"),
        ]
    )
    assert found == [
        "0.4.0: interim title 'moving' is already a title or interim title in "
        "tofu/milestones.json; an interim title must be one no milestone has"
    ]


@pytest.mark.parametrize("value", ["", "   ", None, 2])
def test_an_interim_title_that_is_not_a_non_empty_string_is_named(value: object) -> None:
    assert declaration_problems([milestone("0.2.0", interim_title=value)]) == [
        f"0.2.0: interim title is {value!r}; an interim title must be a non-empty string"
    ]


def test_a_straight_apostrophe_in_a_description_is_named_with_the_typographic_ones() -> None:
    found = declaration_problems([milestone("0.6.0", description="an actor that can't decide")])
    assert found == [
        "0.6.0: description has a straight apostrophe ('); "
        "use \N{RIGHT SINGLE QUOTATION MARK} for an apostrophe or closing quote "
        "and \N{LEFT SINGLE QUOTATION MARK} for an opening one"
    ]


def test_a_straight_double_quote_in_a_description_is_named_with_the_typographic_ones() -> None:
    found = declaration_problems([milestone("0.6.0", description='a "gate" by hand')])
    assert found == [
        '0.6.0: description has a straight double quote ("); '
        "use \N{LEFT DOUBLE QUOTATION MARK} and \N{RIGHT DOUBLE QUOTATION MARK}"
    ]


def test_a_description_with_both_straight_quotes_gets_a_message_for_each() -> None:
    found = declaration_problems([milestone("0.6.0", description='it\'s a "gate"')])
    assert found == [
        "0.6.0: description has a straight apostrophe ('); "
        "use \N{RIGHT SINGLE QUOTATION MARK} for an apostrophe or closing quote "
        "and \N{LEFT SINGLE QUOTATION MARK} for an opening one",
        '0.6.0: description has a straight double quote ("); '
        "use \N{LEFT DOUBLE QUOTATION MARK} and \N{RIGHT DOUBLE QUOTATION MARK}",
    ]


def test_a_description_with_typographic_quotes_is_valid() -> None:
    found = declaration_problems(
        [milestone("0.6.0", description=f"it{RSQUO}s a {LSQUO}gate{RSQUO}, a {LDQUO}gate{RDQUO}")]
    )
    assert found == []


def test_a_unique_interim_title_is_valid() -> None:
    found = declaration_problems(
        [
            milestone("0.2.0", "0.3.0", interim_title="0.3.0 (renumbering)"),
            milestone("0.3.0", "0.2.0", interim_title="0.2.0 (renumbering)"),
        ]
    )
    assert found == []


# check-milestones-json design D1, D3: every rule troupe.run's build enforces on the file, copied
# from troupe-run/website's scripts/roadmap-lib.mjs. A milestone with a valid version for a title
# is named by it; any other by its position, counting from 1.


@pytest.mark.parametrize("declared", [[], {"repositories": []}, {"milestones": {}}, None, "x"])
def test_a_file_without_a_milestones_array_gives_the_one_shape_problem(declared: object) -> None:
    assert shape_problems(declared) == [
        "tofu/milestones.json: isn't an object with a milestones array; "
        "give it a top-level object whose milestones is an array of milestones"
    ]


def test_an_object_with_a_milestones_array_has_no_shape_problem() -> None:
    assert shape_problems({"milestones": [], "repositories": []}) == []


@pytest.mark.parametrize("entry", ["0.3.0", None, [], 3])
def test_a_milestone_that_is_not_an_object_is_named_by_position_and_nothing_else(
    entry: object,
) -> None:
    assert declaration_problems([milestone("0.1.0"), entry, milestone("0.2.0")]) == [
        "milestone 2: isn't an object; "
        "each milestone must be an object with a title and a description"
    ]


@pytest.mark.parametrize(
    "title",
    [
        "v0.3.0",
        "0.3",
        "0.03.0",
        "0.3.0.0",
        "0.3.0 ",
        " 0.3.0",
        "0.3.0\n",
        "\N{ARABIC-INDIC DIGIT THREE}.0.0",
        "",
    ],
)
def test_a_title_that_is_not_a_version_is_named_by_position_with_the_title(title: str) -> None:
    entry = {**milestone("k"), "title": title}
    assert declaration_problems([milestone("0.1.0"), entry]) == [
        f"milestone 2: title {title!r} isn't a version; {TITLE_FIX}"
    ]


@pytest.mark.parametrize("title", [3, None, 0.3])
def test_a_title_that_is_not_a_string_is_named_by_position(title: object) -> None:
    entry = {**milestone("k"), "title": title}
    assert declaration_problems([milestone("0.1.0"), entry]) == [
        f"milestone 2: title {title!r} isn't a version; {TITLE_FIX}"
    ]


def test_a_missing_title_is_named_by_position() -> None:
    entry = milestone("k")
    del entry["title"]
    assert declaration_problems([milestone("0.1.0"), entry]) == [
        f"milestone 2: has no title; {TITLE_FIX}"
    ]


@pytest.mark.parametrize("title", ["0.0.0", "0.3.0", "10.20.30"])
def test_a_version_title_is_valid(title: str) -> None:
    assert declaration_problems([milestone("k", title)]) == []


@pytest.mark.parametrize("description", ["", "   ", "\N{ZERO WIDTH NO-BREAK SPACE}", "\t\n"])
def test_an_empty_description_is_named_with_the_fix(description: str) -> None:
    assert declaration_problems([milestone("0.4.0", description=description)]) == [
        f"0.4.0: description is empty; {DESCRIPTION_FIX}"
    ]


@pytest.mark.parametrize("description", [3, None, ["words"]])
def test_a_description_that_is_not_a_string_is_named_with_the_fix(description: object) -> None:
    assert declaration_problems([milestone("0.4.0", description=description)]) == [
        f"0.4.0: description is {description!r}, not text; {DESCRIPTION_FIX}"
    ]


def test_a_missing_description_is_named_with_the_fix() -> None:
    entry = milestone("0.4.0")
    del entry["description"]
    assert declaration_problems([entry]) == [f"0.4.0: has no description; {DESCRIPTION_FIX}"]


def test_a_bad_title_and_an_empty_description_each_get_a_message() -> None:
    assert declaration_problems([milestone("k", "v1", description=" ")]) == [
        f"milestone 1: title 'v1' isn't a version; {TITLE_FIX}",
        f"milestone 1: description is empty; {DESCRIPTION_FIX}",
    ]


def test_one_bad_milestone_does_not_hide_another() -> None:
    found = declaration_problems(
        [milestone("a", "0.1"), "not a milestone", milestone("0.3.0", description="")]
    )
    assert found == [
        "milestone 2: isn't an object; "
        "each milestone must be an object with a title and a description",
        f"milestone 1: title '0.1' isn't a version; {TITLE_FIX}",
        f"0.3.0: description is empty; {DESCRIPTION_FIX}",
    ]


@pytest.mark.parametrize("field", ["key", "state"])
def test_a_missing_key_or_state_does_not_crash_the_check(field: str) -> None:
    entry = milestone("0.1.0")
    del entry[field]
    assert declaration_problems([entry, milestone("0.2.0")]) == []


def test_unhashable_titles_and_keys_do_not_crash_the_duplicate_check() -> None:
    entry = {**milestone("0.1.0"), "key": ["k"], "title": ["t"]}
    assert declaration_problems([entry, entry]) == [
        f"milestone 1: title ['t'] isn't a version; {TITLE_FIX}",
        f"milestone 2: title ['t'] isn't a version; {TITLE_FIX}",
    ]


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_a_constant_json_parse_refuses_is_refused_naming_the_file(constant: str) -> None:
    with pytest.raises(ValueError, match=rf"^tofu/milestones.json: {constant} isn't JSON"):
        read_declaration(f'{{"milestones": [], "x": {constant}}}')
