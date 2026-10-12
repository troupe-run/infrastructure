"""scripts/plan_needed.py plans every pull request that changes something OpenTofu reads (spec:
ci-apply; required-checks design D2)."""

import re
import subprocess
import sys

import pytest
from conftest import REPO, SCRIPTS

import plan_needed

TOFU = REPO / "tofu"
FILE_CALL = re.compile(r'file(?:set)?\("\$\{path\.module\}/([^"]*)"')


def paths_opentofu_reads() -> set[str]:
    """Every repository path the root configuration reads: its own files, the literal paths in its
    file() calls (up to the first interpolation), the guard's delivered files and org-profile/."""
    read = {str(path.relative_to(REPO)) for path in TOFU.rglob("*") if path.is_file()}
    read -= {str(path.relative_to(REPO)) for path in (TOFU / ".terraform").rglob("*")}
    for tf in TOFU.glob("*.tf"):
        for argument in FILE_CALL.findall(tf.read_text(encoding="utf-8")):
            literal = argument.split("${", 1)[0]
            if literal.startswith("../"):
                read.add(literal.removeprefix("../") or ".")
    guard_files = re.search(
        r"guard_files = toset\(\[(.*?)\]\)",
        (TOFU / "guard_delivery.tf").read_text(encoding="utf-8"),
        re.S,
    )
    assert guard_files is not None
    read |= set(re.findall(r'"([^"]+)"', guard_files.group(1)))
    read |= {
        str(path.relative_to(REPO)) for path in (REPO / "org-profile").rglob("*") if path.is_file()
    }
    return read


def test_every_path_opentofu_reads_is_planned() -> None:
    read = paths_opentofu_reads()
    assert "scripts/guard.py" in read
    assert ".claude/settings.json" in read
    assert "org-profile/CONTRIBUTING.md" in read
    assert "tofu/required-checks.json" in read
    for path in sorted(read):
        assert plan_needed.plan_needed([path]), path


def test_a_pull_request_of_only_never_read_files_isn_t_planned() -> None:
    changed = [
        "openspec/changes/x/tasks.md",
        "docs/development-workflow.md",
        "oob/projects.json",
        "scripts/tests/test_x.py",
        "README.md",
        "CLAUDE.md",
    ]
    assert not plan_needed.plan_needed(changed)


def test_one_read_file_among_never_read_ones_plans() -> None:
    assert plan_needed.plan_needed(["docs/x.md", "tofu/org.tf", "README.md"])


def test_an_empty_list_plans() -> None:
    assert plan_needed.plan_needed([])
    assert plan_needed.plan_needed(["", "\n"])


@pytest.mark.parametrize(
    "path",
    ["docs-old/x.md", "openspec", "README.md.bak", "sub/README.md", "scripts/tests.py"],
)
def test_a_path_is_matched_by_prefix_or_whole_name_not_substring(path: str) -> None:
    assert plan_needed.plan_needed([path])


def test_a_new_top_level_directory_plans() -> None:
    assert plan_needed.plan_needed(["infra2/main.tf"])


def test_the_script_prints_a_github_output_line() -> None:
    def run(stdin: str) -> str:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "plan_needed.py")],
            input=stdin,
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    assert run("docs/a.md\nREADME.md\n") == "plan=false\n"
    assert run("docs/a.md\ntofu/org.tf\n") == "plan=true\n"
