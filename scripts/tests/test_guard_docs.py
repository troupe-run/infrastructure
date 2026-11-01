"""The rules doc (docs/development-workflow.md) lists exactly the guard's rules, and names the
review's required check."""

import re

import pytest
import yaml
from conftest import REPO

import guard

pytestmark = pytest.mark.docs

DOC = REPO / "docs" / "development-workflow.md"
ROW = re.compile(r"^\| `([a-z-]+)` \| (git|Claude|GitHub) \|", re.MULTILINE)


def test_the_docs_list_exactly_the_guard_s_rules() -> None:
    documented = ROW.findall(DOC.read_text(encoding="utf-8"))
    assert sorted(rule for rule, _ in documented) == sorted(guard.RULES)


def test_the_docs_say_the_tamper_rule_can_t_be_overridden() -> None:
    row = next(
        line
        for line in DOC.read_text(encoding="utf-8").splitlines()
        if f"`{guard.TAMPER_RULE}`" in line
    )
    assert "No override unlocks this rule" in row


def test_the_docs_example_declaration_is_one_the_guard_reads() -> None:
    text = DOC.read_text(encoding="utf-8")
    example = text.split("```toml\nversion = 1\n", 1)[1].split("```", 1)[0]
    declaration = guard.check_paths("version = 1\n" + example)
    assert ("vcs_git", ("packages/troupe-vcs-git/tests/**", "packages/troupe/tests/**")) in (
        declaration.tests
    )


def test_the_docs_name_the_review_s_required_check_and_how_to_re_run_it() -> None:
    """review-completed-check (#242): where the docs say to act on the review of the last push,
    they name the job that holds a pull request until that review completed, by the name its
    workflow gives it, and how to re-run a review that didn't."""
    workflow = yaml.safe_load(
        (REPO / ".github" / "workflows" / "claude-review.yml").read_text(encoding="utf-8")
    )
    name = workflow["jobs"]["completed"]["name"]
    text = DOC.read_text(encoding="utf-8")
    section = text[text.index("## Claude's review") :]
    section = section[: section.index("\n## ", 1)]
    assert f"`{name}`" in section
    assert "gh run rerun <id>" in section
    assert "review of the last push has completed" in section
