"""Every managed repository's main ruleset requires each review conversation to be resolved
before a merge (spec: rulesets; review-findings-by-severity design D2, D8).

The setting is one switch in the repository module, on by default, and no repository in the live
root turns it off. These read the HCL as text, as plan_target's tests do: a plan needs the App's
key, which a test doesn't have."""

import re

import pytest
from conftest import REPO

pytestmark = pytest.mark.tofu

MODULE = REPO / "tofu" / "modules" / "repository"
ROOT = REPO / "tofu"


def variable_default(text: str, name: str) -> str | None:
    """The default of a variable block, as written, or None if the block or its default is
    missing."""
    block = re.search(rf'variable "{name}" \{{(.*?)\n\}}', text, re.DOTALL)
    if block is None:
        return None
    default = re.search(r"^\s*default\s*=\s*(\S+)", block.group(1), re.MULTILINE)
    return default.group(1) if default else None


def test_the_switch_is_on_by_default() -> None:
    text = (MODULE / "variables.tf").read_text(encoding="utf-8")
    assert variable_default(text, "review_thread_resolution") == "true"


def test_the_main_ruleset_takes_its_setting_from_the_switch() -> None:
    text = (MODULE / "main.tf").read_text(encoding="utf-8")
    ruleset = re.search(r'resource "github_repository_ruleset" "main" \{(.*?)\n\}', text, re.DOTALL)
    assert ruleset is not None
    pull_request = re.search(r"pull_request \{(.*?)\}", ruleset.group(1), re.DOTALL)
    assert pull_request is not None
    assert re.search(
        r"^\s*required_review_thread_resolution\s*=\s*var\.review_thread_resolution\s*$",
        pull_request.group(1),
        re.MULTILINE,
    )


def test_no_repository_in_the_live_root_turns_it_off() -> None:
    for path in sorted(ROOT.glob("*.tf")):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*review_thread_resolution\s*=", text, re.MULTILINE), path.name


def test_the_default_is_read_as_written() -> None:
    text = (MODULE / "variables.tf").read_text(encoding="utf-8")
    off = re.sub(
        r'(variable "review_thread_resolution" \{.*?default\s*=\s*)true',
        r"\1false",
        text,
        flags=re.DOTALL,
    )
    assert variable_default(off, "review_thread_resolution") == "false"
