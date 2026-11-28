"""Auto-merge is on in the three governed repositories (spec: auto-merge, "Auto-merge is on in the
three governed repositories"; auto-merge-on design D2). The owner switched it on after the dry-run
week (#320, 2026-11-28). This test reads tofu/auto_merge.tf as text, so turning one back to dry-run
or off, or switching another repository, is a change to SWITCHES below in the diff the owner
reviews. Setting a variable to off on GitHub stays the break-glass, and drift reports it."""

import re

import pytest
from conftest import REPO

pytestmark = pytest.mark.tofu

TF = REPO / "tofu" / "auto_merge.tf"
SWITCHES = {"troupe": "on", "infrastructure": "on", "website": "on"}


def declared_switches() -> dict[str, str]:
    text = TF.read_text(encoding="utf-8")
    block = re.search(r"auto_merge_switches\s*=\s*\{(?P<body>[^}]*)\}", text)
    assert block, f"{TF.name} no longer declares local.auto_merge_switches"
    body = re.sub(r"#.*", "", block["body"])
    return dict(re.findall(r'^\s*(\w+)\s*=\s*"([^"]*)"\s*$', body, flags=re.MULTILINE))


def test_auto_merge_is_on_in_the_three_governed_repositories() -> None:
    assert declared_switches() == SWITCHES


def test_every_switch_is_read_from_the_one_map() -> None:
    """The variable resource takes its values from the map, so the map is the whole declaration."""
    text = TF.read_text(encoding="utf-8")
    assert text.count('variable_name = "AUTO_MERGE"') == 1
    assert re.search(r"for_each\s*=\s*local\.auto_merge_switches", text)
