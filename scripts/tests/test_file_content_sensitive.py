"""Each file OpenTofu writes into a repository has its content wrapped in sensitive(), so a plan
shows the hash in its commit message instead of the file (spec: ci-apply; truncate-long-plans
design D7).

This checks the configuration's text, not what a plan prints: that was probed on OpenTofu 1.13.1
and is shown by each pull request's plan. It reads every .tf file, so a new file resource is
covered too."""

import re

import pytest
from conftest import REPO

pytestmark = pytest.mark.tofu

TOFU = REPO / "tofu"
BLOCK = re.compile(
    r'^resource "github_repository_file" "(\w+)" \{\n(.*?)^\}', re.MULTILINE | re.DOTALL
)
CONTENT = re.compile(r"^\s*content\s*=\s*(.+)$", re.MULTILINE)


def file_resources() -> dict[str, str]:
    """Each github_repository_file resource's `content` expression, by file and name."""
    found = {}
    for path in sorted(TOFU.rglob("*.tf")):
        if ".terraform" in path.parts:
            continue
        for name, body in BLOCK.findall(path.read_text(encoding="utf-8")):
            content = CONTENT.search(body)
            found[f"{path.relative_to(REPO)}:{name}"] = content.group(1) if content else ""
    return found


def test_the_config_has_the_file_resources_this_test_is_for() -> None:
    assert set(file_resources()) >= {
        "tofu/guard_delivery.tf:guard",
        "tofu/org_profile.tf:org_profile",
    }


@pytest.mark.parametrize("resource", sorted(file_resources()))
def test_each_written_files_content_is_wrapped_in_sensitive_in_the_config(resource: str) -> None:
    content = file_resources()[resource]
    assert content.startswith("sensitive("), f"{resource}: content = {content}"
    assert content.endswith(")"), f"{resource}: content = {content}"


def test_a_content_not_wrapped_in_sensitive_is_caught() -> None:
    body = 'resource "github_repository_file" "x" {\n  content = file("a")\n}\n'
    [(_name, inner)] = BLOCK.findall(body)
    match = CONTENT.search(inner)
    assert match is not None
    assert not match.group(1).startswith("sensitive(")
