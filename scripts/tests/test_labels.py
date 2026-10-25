"""troupe's capability labels say what they cover (spec: labels; cap-label-descriptions design D3).

GitHub refuses a label description over 100 characters, but only when the plan is applied, after
the merge. So the declared descriptions are checked here, offline, on every pull request.
"""

import json
import re
from typing import Any

import pytest
from conftest import REPO

pytestmark = pytest.mark.labels

TROUPE_LABELS = REPO / "tofu" / "labels" / "troupe.json"
GITHUB_LIMIT = 100


def description_problems(labels: list[dict[str, Any]]) -> list[str]:
    """Each cap: label whose description is too long, or only repeats its name."""
    found: list[str] = []
    for label in labels:
        name, description = label["name"], label["description"]
        if not name.startswith("cap:"):
            continue
        if len(description) > GITHUB_LIMIT:
            found.append(
                f"{name}: description is {len(description)} characters, over {GITHUB_LIMIT}"
            )
        if description == f"Capability: {name.removeprefix('cap:')}":
            found.append(
                f"{name}: description only repeats the name; say what the capability covers"
            )
    return found


def label(name: str, description: str) -> dict[str, Any]:
    return {"name": name, "color": "1D76DB", "description": description}


def test_every_declared_cap_label_says_what_it_covers_within_the_limit() -> None:
    labels = json.loads(TROUPE_LABELS.read_text(encoding="utf-8"))
    assert description_problems(labels) == []


def test_a_description_over_the_limit_is_named_with_its_length() -> None:
    assert description_problems([label("cap:runs", "x" * 101)]) == [
        "cap:runs: description is 101 characters, over 100"
    ]


def test_a_description_of_exactly_the_limit_passes() -> None:
    assert description_problems([label("cap:runs", "x" * 100)]) == []


def test_a_description_that_only_repeats_the_name_is_named() -> None:
    assert description_problems([label("cap:runs", "Capability: runs")]) == [
        "cap:runs: description only repeats the name; say what the capability covers"
    ]


def test_tbd_passes_for_a_capability_troupe_has_not_defined() -> None:
    assert description_problems([label("cap:flows", "TBD")]) == []


# release-please finds its release pull request by these exact names, so a misspelt declaration
# would leave troupe's releases stuck with no error (spec: labels; release-app design D5).
RELEASE_LABELS = REPO / "tofu" / "labels" / "release.json"
RELEASE_PLEASE_LABELS = {"autorelease: pending", "autorelease: tagged"}


def test_the_release_set_is_exactly_release_pleases_two_labels_within_the_limit() -> None:
    labels = json.loads(RELEASE_LABELS.read_text(encoding="utf-8"))
    assert {entry["name"] for entry in labels} == RELEASE_PLEASE_LABELS
    assert len(labels) == len(RELEASE_PLEASE_LABELS)
    assert [entry["name"] for entry in labels if len(entry["description"]) > GITHUB_LIMIT] == []


# Kinds of work GitHub's default labels don't cover, such as speed, which every managed
# repository gets (spec: labels; label-troupe-specs design D4). GitHub refuses a description over
# the limit only at apply time.
KIND_LABELS = REPO / "tofu" / "labels" / "kinds.json"


def over_the_limit(labels: list[dict[str, Any]]) -> list[str]:
    """Each label whose description GitHub would refuse, with its length."""
    return [
        f"{entry['name']}: description is {length} characters, over {GITHUB_LIMIT}"
        for entry in labels
        if (length := len(entry["description"])) > GITHUB_LIMIT
    ]


def test_every_declared_kind_label_is_within_the_limit() -> None:
    labels = json.loads(KIND_LABELS.read_text(encoding="utf-8"))
    assert labels, "tofu/labels/kinds.json declares no labels"
    assert over_the_limit(labels) == []


def test_a_kind_label_over_the_limit_is_named_with_its_length() -> None:
    assert over_the_limit([{"name": "speed", "color": "FBCA04", "description": "x" * 101}]) == [
        "speed: description is 101 characters, over 100"
    ]


# The labels Dependabot applies, which it creates when a repository doesn't have them, and the
# ecosystems each repository's dependency graph lists (spec: labels; declare-dependabot-labels
# design D1, D4). Dependabot finds a label by its name, so a declared one is used, not recreated.
DEPENDABOT_LABELS = REPO / "tofu" / "labels" / "dependabot.json"
REPOSITORIES_TF = REPO / "tofu" / "repositories.tf"


def undeclared_ecosystems(dependabot: dict[str, Any]) -> list[str]:
    """Each repository's ecosystem that the set doesn't declare a label for."""
    return [
        f"{repo}: ecosystem {ecosystem!r} isn't declared in tofu/labels/dependabot.json"
        for repo, ecosystems in dependabot["repositories"].items()
        for ecosystem in ecosystems
        if ecosystem not in dependabot["ecosystems"]
    ]


def managed_repositories(tf: str) -> set[str]:
    """The name of each module "repo_*" block in repositories.tf."""
    return set(re.findall(r'module "repo_\w+" \{.*?\n  name\s+= "([^"]+)"', tf, re.DOTALL))


def test_every_declared_dependabot_label_is_within_the_limit() -> None:
    dependabot = json.loads(DEPENDABOT_LABELS.read_text(encoding="utf-8"))
    labels = [dependabot["dependencies"], *dependabot["ecosystems"].values()]
    assert over_the_limit(labels) == []


def test_every_repositorys_ecosystems_are_declared() -> None:
    dependabot = json.loads(DEPENDABOT_LABELS.read_text(encoding="utf-8"))
    assert undeclared_ecosystems(dependabot) == []


def test_an_undeclared_ecosystem_is_named_with_its_repository() -> None:
    dependabot = {"ecosystems": {"npm": {}}, "repositories": {"website": ["npm", "cargo"]}}
    assert undeclared_ecosystems(dependabot) == [
        "website: ecosystem 'cargo' isn't declared in tofu/labels/dependabot.json"
    ]


@pytest.mark.tofu
def test_the_set_names_exactly_the_managed_repositories() -> None:
    dependabot = json.loads(DEPENDABOT_LABELS.read_text(encoding="utf-8"))
    managed = managed_repositories(REPOSITORIES_TF.read_text(encoding="utf-8"))
    assert managed, 'found no module "repo_*" in tofu/repositories.tf'
    assert set(dependabot["repositories"]) == managed


def test_managed_repositories_reads_each_modules_name() -> None:
    tf = (
        'module "repo_a" {\n  source = "./x"\n  name   = "a"\n}\n'
        'module "repo_b" {\n  source       = "./x"\n  name         = ".b"\n}\n'
        'module "other" {\n  name = "c"\n}\n'
    )
    assert managed_repositories(tf) == {"a", ".b"}
