"""infrastructure's required checks (tofu/required-checks.json) name exactly the jobs its workflows
run on a pull request, as GitHub reports them (spec: rulesets; required-checks design D1).

A required name that no job reports blocks every pull request, and a job left out can fail
without blocking anything. troupe's and website's own jobs can't be read from here, so they are
not tested; the guard check each repository receiving the guard requires is, since its workflow is
delivered from here. troupe's list is pinned to its `check` result rather than its legs
(require-troupe-check design D3): that can't prove troupe's CI reports `check`, only that the legs
don't come back.
"""

import itertools
import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO

import plan_target

pytestmark = pytest.mark.tofu

CHECKS = REPO / "tofu" / "required-checks.json"
REPOSITORIES_TF = REPO / "tofu" / "repositories.tf"
GUARD_DELIVERY_TF = REPO / "tofu" / "guard_delivery.tf"
WORKFLOWS = REPO / ".github" / "workflows"
# The encrypted state, which the App alone commits to main after an apply.
STATE_FILE = "tofu/terraform.tfstate"

# The workflows whose pull-request jobs infrastructure requires, and the jobs deliberately left
# out: each `changes` only decides what runs, and a failure there runs everything (design D2); the
# guard's legs report through `guard tests`, because a skipped matrix job reports under its
# unexpanded name (run-checks-by-path design D6).
REQUIRED_WORKFLOWS = ("ci.yml", "guard.yml", "tofu.yml")
NOT_REQUIRED = {"changes", "guard-tests"}

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
    skipped). A condition that only excludes another event, as ci.yml's `changes` excludes merge
    groups (ci-once-per-commit design D2), doesn't confine it."""
    if "pull_request" not in triggers(workflow):
        return False
    job = workflow["jobs"][job_id]
    condition = str(job.get("if", ""))
    excludes_another = re.fullmatch(
        r"\s*github\.event_name != '(?!pull_request')[a-z_]+'\s*", condition
    )
    if (
        "event_name" in condition
        and "event_name == 'pull_request'" not in condition
        and not excludes_another
    ):
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


def guard_targets() -> set[str]:
    """The repositories guard_delivery.tf delivers the guard to, by name (spec: guard-delivery)."""
    targets = re.search(
        r"guard_targets\s*=\s*toset\(\[(.*?)\]\)",
        GUARD_DELIVERY_TF.read_text(encoding="utf-8"),
        re.S,
    )
    assert targets is not None, (
        "guard_targets isn't toset([module.<name>.name, ...]); update this test"
    )
    modules = re.findall(r"module\.(\w+)\.name", targets.group(1))
    names = dict(
        re.findall(
            r'module "(\w+)" \{\s*source\s*=\s*"[^"]*"\s*name\s*=\s*"([^"]+)"',
            REPOSITORIES_TF.read_text(encoding="utf-8"),
        )
    )
    assert modules, "guard_targets names no module; update this test"
    unknown = [module for module in modules if module not in names]
    assert not unknown, f"guard_targets names modules repositories.tf doesn't declare: {unknown}"
    return {names[module] for module in modules}


def test_guard_targets_are_read_as_repository_names() -> None:
    assert "troupe" in guard_targets()


def test_every_repository_receiving_the_guard_requires_its_check_by_its_name_here() -> None:
    """govern-website design D3: a new guard target without the guard check fails here."""
    guard_jobs = {
        name
        for job_id, job in load_yaml(WORKFLOWS / "guard.yml")["jobs"].items()
        for name in job_names(job_id, job)
    }
    missing = {
        repo: sorted(guard_jobs - required(repo, "github-actions")) for repo in guard_targets()
    }
    assert {repo: jobs for repo, jobs in missing.items() if jobs} == {}


def test_troupe_requires_its_check_result_and_none_of_its_legs() -> None:
    """require-troupe-check design D1: a skipped matrix job reports under its unexpanded name, so a
    required leg would never report on a push that skips them; troupe's `check` reports for them."""
    names = required("troupe", "github-actions")
    assert "check" in names
    assert sorted(name for name in names if name.startswith("check (")) == []


def test_every_required_check_names_an_app_opentofu_maps_to_an_id() -> None:
    block = re.search(r"check_apps = \{(.*?)\}", REPOSITORIES_TF.read_text(encoding="utf-8"), re.S)
    assert block is not None
    mapped = set(re.findall(r'"([a-z-]+)"\s*=\s*\d+', block.group(1)))
    checks = json.loads(CHECKS.read_text(encoding="utf-8"))
    assert {check["app"] for repo in checks.values() for check in repo} <= mapped


def test_a_renamed_job_no_longer_matches_the_required_names() -> None:
    workflows = real_workflows()
    workflows["ci.yml"]["jobs"]["guard-tests-result"]["name"] = "guard tests (all)"
    assert required("infrastructure", "github-actions") != pull_request_checks(workflows)


def test_the_guard_s_legs_aren_t_required_but_their_result_is() -> None:
    names = pull_request_checks(real_workflows())
    assert "guard tests" in names
    assert not [name for name in names if name.startswith("guard tests (")]


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


def events(workflow: dict[Any, Any]) -> dict[str, Any]:
    """A workflow's `on` as a mapping of event to its filters (None for a bare event)."""
    on = workflow["on"] if "on" in workflow else workflow[True]
    assert isinstance(on, dict), f"`on` isn't a mapping: {on!r}"
    return on


def ci_trigger_problems(ci: dict[Any, Any], tofu: dict[Any, Any]) -> list[str]:
    """dedupe-ci-runs design D2, D3: CI tests a pull request once, from its pull_request run, with
    no path filter (so its required checks always report), and main after every push except the
    App's state commit, which tofu.yml's plan skips by the same path."""
    problems = []
    on = events(ci)
    pull_request = on.get("pull_request") or {}
    if filtered := sorted({"paths", "paths-ignore"} & set(pull_request)):
        problems.append(f"pull_request has {filtered}; a required check would never report")
    push = on.get("push") or {}
    if push.get("branches") != ["main"]:
        problems.append(f"push runs on {push.get('branches')!r}, not ['main']")
    if push.get("paths-ignore") != [STATE_FILE]:
        problems.append(f"push ignores {push.get('paths-ignore')!r}, not [{STATE_FILE!r}]")
    # The skip lives in scripts/plan_target.py (plan-each-merge-once design D2).
    runs_target = [
        step
        for step in tofu["jobs"]["plan"]["steps"]
        if "scripts/plan_target.py" in step.get("run", "")
    ]
    if not runs_target or plan_target.STATE_PATH != STATE_FILE:
        problems.append(f"tofu.yml's state-commit skip (plan_target.py) doesn't read {STATE_FILE}")
    return problems


def plan_trigger_problems(ci: dict[Any, Any], tofu: dict[Any, Any]) -> list[str]:
    """dedupe-ci-runs design D3: main is planned after CI, so tofu.yml's workflow_run must name
    ci.yml's workflow, on branches ci.yml's pushes run on (by name: no glob matching)."""
    problems = []
    follows = events(tofu)["workflow_run"]
    if follows["workflows"] != [ci["name"]]:
        problems.append(f"tofu.yml follows {follows['workflows']!r}; ci.yml is {ci['name']!r}")
    pushed = (events(ci).get("push") or {}).get("branches", [])
    if missing := [branch for branch in follows["branches"] if branch not in pushed]:
        problems.append(f"tofu.yml follows CI on {missing}, which ci.yml's pushes don't list")
    return problems


def test_ci_tests_pull_requests_unfiltered_and_main_s_pushes_except_the_state_commit() -> None:
    workflows = real_workflows()
    assert ci_trigger_problems(workflows["ci.yml"], workflows["tofu.yml"]) == []


def test_main_s_plan_follows_the_ci_run_main_s_pushes_start() -> None:
    workflows = real_workflows()
    assert plan_trigger_problems(workflows["ci.yml"], workflows["tofu.yml"]) == []


def test_a_renamed_ci_workflow_is_named_as_no_longer_followed_by_main_s_plan() -> None:
    workflows = real_workflows()
    workflows["ci.yml"]["name"] = "Tests"
    assert plan_trigger_problems(workflows["ci.yml"], workflows["tofu.yml"]) == [
        "tofu.yml follows ['CI']; ci.yml is 'Tests'"
    ]


def test_ci_pushes_without_main_are_named_as_never_starting_main_s_plan() -> None:
    workflows = real_workflows()
    events(workflows["ci.yml"])["push"]["branches"] = ["release"]
    assert plan_trigger_problems(workflows["ci.yml"], workflows["tofu.yml"]) == [
        "tofu.yml follows CI on ['main'], which ci.yml's pushes don't list"
    ]


def test_a_state_path_that_tofu_yml_doesn_t_skip_is_named() -> None:
    workflows = real_workflows()
    events(workflows["ci.yml"])["push"]["paths-ignore"] = ["tofu/state.tfstate"]
    assert ci_trigger_problems(workflows["ci.yml"], workflows["tofu.yml"]) == [
        "push ignores ['tofu/state.tfstate'], not ['tofu/terraform.tfstate']"
    ]


def test_a_state_path_the_plan_target_doesnt_skip_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    workflows = real_workflows()
    monkeypatch.setattr(plan_target, "STATE_PATH", "tofu/state.tfstate")
    assert ci_trigger_problems(workflows["ci.yml"], workflows["tofu.yml"]) == [
        "tofu.yml's state-commit skip (plan_target.py) doesn't read tofu/terraform.tfstate"
    ]


def test_a_plan_job_without_the_plan_target_is_named() -> None:
    workflows = real_workflows()
    steps = workflows["tofu.yml"]["jobs"]["plan"]["steps"]
    steps[:] = [step for step in steps if "plan_target.py" not in step.get("run", "")]
    assert ci_trigger_problems(workflows["ci.yml"], workflows["tofu.yml"]) == [
        "tofu.yml's state-commit skip (plan_target.py) doesn't read tofu/terraform.tfstate"
    ]


def test_a_path_filter_on_pull_requests_is_named() -> None:
    workflows = real_workflows()
    events(workflows["ci.yml"])["pull_request"] = {"paths-ignore": ["docs/**"]}
    assert ci_trigger_problems(workflows["ci.yml"], workflows["tofu.yml"]) == [
        "pull_request has ['paths-ignore']; a required check would never report"
    ]


def test_guard_re_runs_when_a_pull_request_is_renamed_and_runs_on_every_push_but_a_queue_s() -> (
    None
):
    """release-please-prs design D4: the title is checked, so editing it must re-run the check. A
    merge queue's branch is judged on its merge group instead (merge-queue design D3)."""
    workflow: dict[Any, Any] = load_yaml(WORKFLOWS / "guard.yml")
    on = workflow["on"] if "on" in workflow else workflow[True]
    assert on["pull_request"]["types"] == ["opened", "edited", "synchronize", "reopened"]
    assert on["push"]["branches"] == ["**", "!gh-readonly-queue/**"]


# merge-queue design D2: a repository's queue is on only when every check it requires reports on
# the queue's commits, or the queue waits for a check that can't report until it times out.


def merge_queue_modules(text: str | None = None) -> set[str]:
    """The repositories.tf modules that turn the merge queue on, by module name."""
    text = REPOSITORIES_TF.read_text(encoding="utf-8") if text is None else text
    blocks = re.findall(r'^module "(\w+)" \{\n(.*?)^\}', text, re.S | re.M)
    assert blocks, "repositories.tf declares no module; update this test"
    return {name for name, body in blocks if re.search(r"^\s*merge_queue\s*=\s*true\b", body, re.M)}


def checks_not_on_merge_groups(workflows: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Each required job a merge queue would wait for in vain, and its workflow: a pull-request
    job whose workflow isn't triggered by merge_group."""
    return {
        name: file
        for file, workflow in workflows.items()
        if "merge_group" not in triggers(workflow)
        for job_id, job in workflow["jobs"].items()
        if job_id not in NOT_REQUIRED and runs_on_pull_requests(workflow, job_id)
        for name in job_names(job_id, job)
    }


def test_infrastructure_s_queue_is_on_only_when_its_required_checks_report_on_the_queue() -> None:
    if "repo_infrastructure" not in merge_queue_modules():
        pytest.skip("infrastructure's merge queue is off")
    blockers = checks_not_on_merge_groups(real_workflows())
    assert {name: blockers[name] for name in required("infrastructure", "github-actions")
            if name in blockers} == {}  # fmt: skip


def test_every_required_check_of_infrastructure_reports_on_merge_groups() -> None:
    """What a queue needs from this repository's workflows, whether or not its switch is on, so a
    workflow change that would stall the queue fails before the switch makes it matter."""
    assert checks_not_on_merge_groups(real_workflows()) == {}


def test_a_workflow_without_the_merge_group_trigger_is_named_with_its_checks() -> None:
    workflows = real_workflows()
    ci: dict[Any, Any] = workflows["ci.yml"]
    del ci[True]["merge_group"]  # YAML 1.1 reads the key `on` as true
    blockers = checks_not_on_merge_groups(workflows)
    assert blockers == {"check": "ci.yml", "guard tests": "ci.yml"}


def test_merge_queue_modules_reads_which_modules_turn_the_queue_on() -> None:
    text = (
        'module "repo_a" {\n  source = "./x"\n  merge_queue = true\n}\n'
        'module "repo_b" {\n  source = "./x"\n  merge_queue = false\n}\n'
        'module "repo_c" {\n  source = "./x"\n  # merge_queue = true\n}\n'
    )
    assert merge_queue_modules(text) == {"repo_a"}
