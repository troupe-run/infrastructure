"""infrastructure's required checks (tofu/required-checks.json) name exactly the jobs its workflows
run on a pull request, as GitHub reports them (spec: rulesets; required-checks design D1).

A required name that no job reports blocks every pull request, and a job left out can fail
without blocking anything. troupe's and website's names can't be read from here, so they are
not tested.
"""

import itertools
import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO

CHECKS = REPO / "tofu" / "required-checks.json"
REPOSITORIES_TF = REPO / "tofu" / "repositories.tf"
WORKFLOWS = REPO / ".github" / "workflows"

# The workflows whose pull-request jobs infrastructure requires, and the jobs deliberately left
# out: `changes` only decides whether to plan, and a failure there makes the plan run (design D2).
REQUIRED_WORKFLOWS = ("ci.yml", "guard.yml", "tofu.yml")
NOT_REQUIRED = {"changes"}

MATRIX_REF = re.compile(r"\$\{\{\s*matrix\.([A-Za-z0-9_-]+)\s*\}\}")
EXPRESSION = re.compile(r"\$\{\{.*?\}\}")


def load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def triggers(workflow: dict[str, Any]) -> list[str]:
    """The events a workflow runs on. YAML 1.1 reads a bare `on` key as the boolean True."""
    keys: dict[Any, Any] = workflow
    on = keys["on"] if "on" in keys else keys.get(True)
    if isinstance(on, str):
        return [on]
    if isinstance(on, dict | list):
        return [str(event) for event in on]
    raise ValueError(f"unexpected `on`: {on!r}")


def runs_on_pull_requests(workflow: dict[str, Any], job_id: str) -> bool:
    """Whether a job runs on a pull request: its workflow is triggered by one, its `if` doesn't
    confine it to other events, and every job it needs runs too (a job whose needs are skipped is
    skipped)."""
    if "pull_request" not in triggers(workflow):
        return False
    job = workflow["jobs"][job_id]
    condition = str(job.get("if", ""))
    if "event_name" in condition and "event_name == 'pull_request'" not in condition:
        return False
    needs = job.get("needs", [])
    return all(
        runs_on_pull_requests(workflow, need)
        for need in ([needs] if isinstance(needs, str) else needs)
    )


def matrix_combinations(matrix: dict[str, Any]) -> list[dict[str, str]]:
    """GitHub's expansion: the product of the matrix's keys, less `exclude`, plus `include`."""
    keys = [key for key in matrix if key not in ("include", "exclude")]
    for key in keys:
        if not isinstance(matrix[key], list):
            raise ValueError(f"matrix.{key} isn't a literal list; this test can't expand it")
    combos = [
        {key: str(value) for key, value in zip(keys, values, strict=True)}
        for values in itertools.product(*(matrix[key] for key in keys))
    ]
    for excluded in matrix.get("exclude", []):
        combos = [
            combo
            for combo in combos
            if not all(combo.get(key) == str(value) for key, value in excluded.items())
        ]
    for included in matrix.get("include", []):
        extra = {key: str(value) for key, value in included.items()}
        matched = [
            combo
            for combo in combos
            if all(combo[key] == value for key, value in extra.items() if key in keys)
        ]
        for combo in matched:
            combo.update({key: value for key, value in extra.items() if key not in keys})
        if not matched:
            combos.append(extra)
    return combos


def substitute(name: str, combo: dict[str, str]) -> str:
    def value(ref: re.Match[str]) -> str:
        return combo[ref.group(1)]

    return MATRIX_REF.sub(value, name)


def job_names(job_id: str, job: dict[str, Any]) -> list[str]:
    """The names GitHub reports for a job: one per matrix leg."""
    name = str(job.get("name", job_id))
    matrix = job.get("strategy", {}).get("matrix")
    if not matrix:
        if EXPRESSION.search(name):
            raise ValueError(f"job {job_id}'s name has an expression this test can't evaluate")
        return [name]
    names = []
    for combo in matrix_combinations(matrix):
        if MATRIX_REF.search(name):
            names.append(substitute(name, combo))
        else:
            # A matrix job whose name doesn't use the matrix gets its values appended.
            names.append(f"{name} ({', '.join(combo.values())})")
    for reported in names:
        if EXPRESSION.search(reported):
            raise ValueError(f"job {job_id}'s name has an expression this test can't evaluate")
    return names


def pull_request_checks(workflows: dict[str, dict[str, Any]]) -> set[str]:
    return {
        name
        for workflow in workflows.values()
        for job_id, job in workflow["jobs"].items()
        if job_id not in NOT_REQUIRED and runs_on_pull_requests(workflow, job_id)
        for name in job_names(job_id, job)
    }


def real_workflows() -> dict[str, dict[str, Any]]:
    return {name: load_yaml(WORKFLOWS / name) for name in REQUIRED_WORKFLOWS}


def required(repo: str, app: str) -> set[str]:
    checks = json.loads(CHECKS.read_text(encoding="utf-8"))
    return {check["context"] for check in checks[repo] if check["app"] == app}


def test_infrastructure_requires_exactly_its_pull_request_jobs() -> None:
    assert required("infrastructure", "github-actions") == pull_request_checks(real_workflows())


def test_infrastructure_requires_dco_from_the_dco_app() -> None:
    assert required("infrastructure", "dco") == {"DCO"}


def test_troupe_requires_the_delivered_guard_check_by_its_name_here() -> None:
    guard_jobs = {
        name
        for job_id, job in load_yaml(WORKFLOWS / "guard.yml")["jobs"].items()
        for name in job_names(job_id, job)
    }
    assert guard_jobs <= required("troupe", "github-actions")


def test_every_required_check_names_an_app_opentofu_maps_to_an_id() -> None:
    block = re.search(r"check_apps = \{(.*?)\}", REPOSITORIES_TF.read_text(encoding="utf-8"), re.S)
    assert block is not None
    mapped = set(re.findall(r'"([a-z-]+)"\s*=\s*\d+', block.group(1)))
    checks = json.loads(CHECKS.read_text(encoding="utf-8"))
    assert {check["app"] for repo in checks.values() for check in repo} <= mapped


def test_a_renamed_matrix_leg_no_longer_matches_the_required_names() -> None:
    workflows = real_workflows()
    workflows["ci.yml"]["jobs"]["guard-tests"]["strategy"]["matrix"]["os"][0] = "ubuntu-24.04"
    assert required("infrastructure", "github-actions") != pull_request_checks(workflows)


def test_a_required_name_dropped_from_the_list_no_longer_matches() -> None:
    names = required("infrastructure", "github-actions")
    names.discard("check")
    assert names != pull_request_checks(real_workflows())


def test_a_job_confined_to_other_events_isn_t_counted() -> None:
    workflows = real_workflows()
    names = pull_request_checks(workflows)
    assert "plan (main)" not in names
    assert "apply (main)" not in names


def test_the_matrix_expands_with_exclude_and_include() -> None:
    matrix = {
        "os": ["a", "b"],
        "python": ["1", "2"],
        "exclude": [{"os": "a", "python": "1"}],
        "include": [{"os": "b", "python": "2", "extra": "x"}, {"os": "c", "python": "3"}],
    }
    assert matrix_combinations(matrix) == [
        {"os": "a", "python": "2"},
        {"os": "b", "python": "1"},
        {"os": "b", "python": "2", "extra": "x"},
        {"os": "c", "python": "3"},
    ]


def test_a_matrix_job_without_matrix_in_its_name_gets_the_values_appended() -> None:
    job = {"name": "build", "strategy": {"matrix": {"os": ["a", "b"]}}}
    assert job_names("build", job) == ["build (a)", "build (b)"]


def test_a_name_it_can_t_evaluate_is_refused_rather_than_guessed() -> None:
    job = {"name": "build ${{ github.ref }}"}
    with pytest.raises(ValueError, match="can't evaluate"):
        job_names("build", job)


def test_guard_re_runs_when_a_pull_request_is_renamed_and_still_runs_on_every_push() -> None:
    """release-please-prs design D4: the title is checked, so editing it must re-run the check."""
    workflow: dict[Any, Any] = load_yaml(WORKFLOWS / "guard.yml")
    on = workflow["on"] if "on" in workflow else workflow[True]
    assert on["pull_request"]["types"] == ["opened", "edited", "synchronize", "reopened"]
    assert on["push"]["branches"] == ["**"]
