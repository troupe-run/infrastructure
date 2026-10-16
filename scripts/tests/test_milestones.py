"""The release milestones' declaration is complete and well formed (spec: milestones;
release-milestones design D4).

The plan can't tell a repository that's missing from the list, and GitHub refuses a bad state only
when the plan is applied, after the merge. So both are checked here, offline, on every pull request.
"""

import json
import re
from typing import Any

from conftest import REPO

TOFU = REPO / "tofu"
MILESTONES = TOFU / "milestones.json"
REPOSITORIES_TF = TOFU / "repositories.tf"
STATES = ("open", "closed")


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


def declaration_problems(milestones: list[dict[str, Any]]) -> list[str]:
    """Each key or title declared twice, and each state that isn't open or closed."""
    found: list[str] = []
    for field in ("key", "title"):
        seen: set[str] = set()
        for milestone in milestones:
            value = milestone[field]
            if value in seen:
                found.append(f"{value}: {field} is declared twice in tofu/milestones.json")
            seen.add(value)
    for milestone in milestones:
        if milestone["state"] not in STATES:
            found.append(
                f"{milestone['title']}: state is {milestone['state']!r}; "
                f"valid states are {', '.join(STATES)}"
            )
    return found


def milestone(key: str, title: str | None = None, state: str = "open") -> dict[str, Any]:
    return {"key": key, "title": title or key, "state": state, "description": "x"}


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
    declared = json.loads(MILESTONES.read_text(encoding="utf-8"))
    assert declared["milestones"], "tofu/milestones.json declares no milestones"
    assert declaration_problems(declared["milestones"]) == []


def test_a_duplicate_title_is_named() -> None:
    assert declaration_problems([milestone("a", "0.2.0"), milestone("b", "0.2.0")]) == [
        "0.2.0: title is declared twice in tofu/milestones.json"
    ]


def test_a_duplicate_key_is_named() -> None:
    assert declaration_problems([milestone("0.1.0", "x"), milestone("0.1.0", "y")]) == [
        "0.1.0: key is declared twice in tofu/milestones.json"
    ]


def test_an_unknown_state_is_an_error_naming_the_valid_ones() -> None:
    assert declaration_problems([milestone("0.1.0", state="done")]) == [
        "0.1.0: state is 'done'; valid states are open, closed"
    ]


def test_a_closed_milestone_is_valid() -> None:
    assert declaration_problems([milestone("0.1.0", state="closed")]) == []
