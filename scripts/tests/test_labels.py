"""troupe's capability labels say what they cover (spec: labels; cap-label-descriptions design D3).

GitHub refuses a label description over 100 characters, but only when the plan is applied, after
the merge. So the declared descriptions are checked here, offline, on every pull request.
"""

import json
from typing import Any

from conftest import REPO

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
