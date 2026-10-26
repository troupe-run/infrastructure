"""scripts/plan_needed.py plans every pull request that changes something OpenTofu reads (spec:
ci-apply; required-checks design D2)."""

import copy
import re
import subprocess
import sys
from typing import Any

import pytest
import yaml
from conftest import REPO, SCRIPTS

import plan_needed

TOFU = REPO / "tofu"
FILE_CALL = re.compile(r'file(?:set)?\("\$\{path\.module\}/([^"]*)"')
TOFU_WORKFLOW = REPO / ".github" / "workflows" / "tofu.yml"
UV_RUN = re.compile(r"\buv\s+run\b(.*)")


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


@pytest.mark.tofu
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
        "pyproject.toml",
        "uv.lock",
    ]
    assert not plan_needed.plan_needed(changed)


@pytest.mark.parametrize(
    "changed",
    [["uv.lock"], ["pyproject.toml", "uv.lock"], ["pyproject.toml", "uv.lock", "docs/x.md"]],
)
def test_a_python_tooling_bump_at_the_root_isn_t_planned(changed: list[str]) -> None:
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


@pytest.mark.parametrize(
    "changed",
    [["tofu/.terraform.lock.hcl"], ["tofu/.terraform.lock.hcl", "uv.lock"]],
)
def test_the_provider_lockfile_plans_alone_or_with_the_python_lockfile(changed: list[str]) -> None:
    assert plan_needed.plan_needed(changed)


@pytest.mark.parametrize(
    "path", ["scripts/pyproject.toml", "tofu/uv.lock", "uv.lock.bak", "pyproject.toml.orig"]
)
def test_a_python_tooling_file_outside_the_root_or_renamed_plans(path: str) -> None:
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
    assert run("uv.lock\npyproject.toml\n") == "plan=false\n"
    assert run("uv.lock\ntofu/.terraform.lock.hcl\n") == "plan=true\n"


def tofu_workflow() -> dict[str, Any]:
    loaded = yaml.safe_load(TOFU_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def uv_runs(workflow: dict[str, Any]) -> list[tuple[str, str, bool]]:
    """Each `uv run` in a step's `run` text, as (job, step, whether it passes --no-project).
    Shell comment lines are left out. uv started another way (`uvx`, `uv tool run`) isn't seen."""
    found = []
    for job_id, job in workflow["jobs"].items():
        for step in job.get("steps", []):
            for line in str(step.get("run", "")).splitlines():
                match = UV_RUN.search(line)
                if match and not line.lstrip().startswith("#"):
                    name = str(step.get("name", step.get("id", "?")))
                    found.append((job_id, name, "--no-project" in match.group(1).split()))
    return found


def test_every_uv_run_in_the_tofu_workflow_passes_no_project() -> None:
    """pyproject.toml and uv.lock are skipped only because no plan or apply step runs in the
    project's environment (skip-plan-python-tooling design D3)."""
    runs = uv_runs(tofu_workflow())
    assert {job for job, _, _ in runs} >= {"pr-plan", "plan", "oob", "apply"}
    in_project = [f"{job}: {step}" for job, step, no_project in runs if not no_project]
    assert not in_project, (
        f"tofu.yml runs uv in the project's environment ({', '.join(in_project)}), so uv.lock "
        "would change what a plan or an apply runs. Pass --no-project to that step, or take "
        "pyproject.toml and uv.lock out of NEVER_READ in scripts/plan_needed.py."
    )


def test_a_uv_run_without_no_project_is_reported_naming_its_job_and_step() -> None:
    workflow = copy.deepcopy(tofu_workflow())
    step = next(
        s for s in workflow["jobs"]["apply"]["steps"] if "--no-project" in str(s.get("run"))
    )
    step["run"] = step["run"].replace("--no-project ", "", 1)
    step["run"] += "\n# uv run scripts/x.py, a comment\n"
    in_project = [(job, name) for job, name, no_project in uv_runs(workflow) if not no_project]
    assert in_project == [("apply", str(step.get("name", step.get("id"))))]
