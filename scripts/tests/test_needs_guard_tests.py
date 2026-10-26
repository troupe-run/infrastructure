"""scripts/guard_tests_needed.py runs the guard's matrix when a pull request changes what the
guard's tests depend on, and only then (spec: ci-apply; run-checks-by-path design D5).

Named so it isn't one of the guard's own tests (test_guard_*.py), which the matrix runs."""

import subprocess
import sys

import pytest
from conftest import REPO, SCRIPTS

import guard_tests_needed
import tofu_text

GUARD_DELIVERY_TF = REPO / "tofu" / "guard_delivery.tf"


def delivered_files(text: str) -> list[str]:
    """The `guard_files` list in guard_delivery.tf's text."""
    return tofu_text.guard_files(text)


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


@pytest.mark.parametrize(
    ("legs", "changes", "guard"),
    [
        ("success", "success", "true"),
        ("success", "skipped", ""),  # a push to main: no `changes` job, every leg runs
        ("success", "failure", ""),  # the decision failed, so the legs ran
        ("skipped", "success", "false"),
    ],
)
def test_the_result_passes_when_the_legs_passed_or_weren_t_needed(
    legs: str, changes: str, guard: str
) -> None:
    assert guard_tests_needed.result_problem(legs, changes, guard) is None


@pytest.mark.parametrize(
    ("legs", "changes", "guard", "named"),
    [
        ("failure", "success", "true", "is failure"),
        ("cancelled", "success", "true", "is cancelled"),
        ("skipped", "success", "true", "guard=true"),
        ("skipped", "failure", "", "was failure"),
        ("skipped", "skipped", "", "was skipped"),
        ("skipped", "success", "", "guard=(nothing)"),
        ("", "success", "false", "is (none)"),
    ],
)
def test_the_result_fails_and_says_why_otherwise(
    legs: str, changes: str, guard: str, named: str
) -> None:
    problem = guard_tests_needed.result_problem(legs, changes, guard)
    assert problem is not None
    assert named in problem


def test_the_result_mode_exits_with_the_verdict() -> None:
    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "guard_tests_needed.py"), "--result", *args],
            capture_output=True,
            text=True,
            check=False,
        )

    assert run("skipped", "success", "false").returncode == 0
    failed = run("failure", "success", "true")
    assert failed.returncode == 1
    assert "guard tests: the legs' result is failure" in failed.stderr
    assert run("success", "success").returncode == 2
