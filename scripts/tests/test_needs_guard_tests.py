"""scripts/guard_tests_needed.py runs the guard's matrix when a pull request changes what the
guard's tests depend on, and only then (spec: ci-apply; run-checks-by-path design D5).

Named so it isn't one of the guard's own tests (test_guard_*.py), which the matrix runs."""

import re
import subprocess
import sys

import pytest
from conftest import REPO, SCRIPTS

import guard_tests_needed

GUARD_DELIVERY_TF = REPO / "tofu" / "guard_delivery.tf"


def delivered_files(text: str) -> list[str]:
    """The `guard_files` list in guard_delivery.tf's text."""
    found = re.search(r"guard_files = toset\(\[(.*?)\]\)", text, re.S)
    assert found is not None, "guard_files isn't toset([...]); update this test"
    files = re.findall(r'"([^"]+)"', found.group(1))
    assert files, "guard_files lists no file; update this test"
    return files


def uncovered(files: list[str]) -> list[str]:
    return [path for path in files if not guard_tests_needed.depends_on(path)]


@pytest.mark.parametrize(
    "path",
    [
        "scripts/guard.py",
        "scripts/guard_pytest.py",
        ".githooks/pre-commit",
        ".claude/settings.json",
        ".github/workflows/guard.yml",
        "scripts/tests/test_guard_git_hooks.py",
        "scripts/tests/conftest.py",
        "scripts/check-paths.toml",
        "pyproject.toml",
        "uv.lock",
        ".github/workflows/ci.yml",
    ],
)
def test_a_path_the_guard_s_tests_depend_on_needs_them(path: str) -> None:
    assert guard_tests_needed.guard_tests_needed(["openspec/x.md", path])


def test_every_guard_test_and_its_fixtures_need_them() -> None:
    tests = sorted((SCRIPTS / "tests").glob("test_guard_*.py"))
    assert tests
    for path in [*tests, SCRIPTS / "tests" / "conftest.py"]:
        assert guard_tests_needed.guard_tests_needed([str(path.relative_to(REPO))]), path


def test_declarations_scripts_and_specs_don_t_need_them() -> None:
    changed = [
        "tofu/dns.json",
        "tofu/dns.tf",
        "tofu/labels/troupe.json",
        "scripts/tofu.py",
        "scripts/plan_checks.py",
        "scripts/guard_tests_needed.py",
        "scripts/tests/test_dns.py",
        "openspec/changes/x/tasks.md",
        "docs/development-workflow.md",
        "README.md",
    ]
    assert not guard_tests_needed.guard_tests_needed(changed)


def test_an_empty_list_needs_them() -> None:
    assert guard_tests_needed.guard_tests_needed([])
    assert guard_tests_needed.guard_tests_needed(["", "\n"])


@pytest.mark.parametrize(
    "path",
    ["scripts/guard.py.bak", "x/scripts/guard.py", ".githooks", "pyproject.toml.orig"],
)
def test_a_path_is_matched_by_prefix_or_whole_name_not_substring(path: str) -> None:
    assert not guard_tests_needed.guard_tests_needed([path])


@pytest.mark.tofu
def test_every_file_the_guard_delivers_needs_them() -> None:
    files = delivered_files(GUARD_DELIVERY_TF.read_text(encoding="utf-8"))
    assert uncovered(files) == []


def test_a_delivered_file_missing_from_the_list_is_named() -> None:
    text = 'guard_files = toset([\n  "scripts/guard.py",\n  "scripts/guard_hooks.toml",\n])'
    assert uncovered(delivered_files(text)) == ["scripts/guard_hooks.toml"]


def test_the_script_prints_a_github_output_line() -> None:
    def run(stdin: str) -> str:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "guard_tests_needed.py")],
            input=stdin,
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    assert run("tofu/dns.json\nopenspec/x.md\n") == "guard=false\n"
    assert run("tofu/dns.json\nscripts/guard.py\n") == "guard=true\n"
    assert run("") == "guard=true\n"
