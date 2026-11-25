"""The weekly mutation run and the pull request report hold no secret where they run code, never
block a merge, and keep their budgets and token in step with their declarations (spec:
mutation-testing, mutation-issue-credentials; lint-mutation design D3, D4, D9)."""

import io
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO
from test_dependabot_issues_workflow import (
    apps,
    declared_inputs,
    environment_of,
    steps_using,
    token_problems,
)

import mutation_pr as pr
import mutation_settings as ms

pytestmark = [pytest.mark.mutation, pytest.mark.oob, pytest.mark.tofu, pytest.mark.schedules]

WEEKLY = REPO / ".github" / "workflows" / "mutation.yml"
PR = REPO / ".github" / "workflows" / "mutation-pr.yml"
SETTINGS = ms.load_settings((REPO / "scripts" / "mutation.json").read_text(encoding="utf-8"))
APP = "troupe-run-test-quality"


def load(path: Path) -> dict[Any, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def triggers(workflow: dict[Any, Any]) -> set[str]:
    # PyYAML reads the key `on` as True.
    return set(workflow.get(True) or workflow.get("on") or {})


# The weekly run


def test_the_weekly_run_runs_on_its_schedule_and_by_hand_only() -> None:
    workflow = load(WEEKLY)
    assert triggers(workflow) == {"schedule", "workflow_dispatch"}
    # Nightly: each run resumes from the last one's kept state (#378).
    assert workflow[True]["schedule"] == [{"cron": "23 3 * * *"}]
    assert workflow["permissions"] == {}
    assert workflow["concurrency"] == {"group": "mutation", "cancel-in-progress": False}


def test_the_mutate_job_holds_no_secret_and_has_the_budget() -> None:
    mutate = load(WEEKLY)["jobs"]["mutate"]
    assert mutate["permissions"] == {"contents": "read", "actions": "read"}
    assert "environment" not in mutate
    assert "secrets." not in json.dumps(mutate)
    timeout, budget = mutate["timeout-minutes"], SETTINGS.budget_minutes
    assert timeout == budget + 30, f"mutate's timeout is {timeout}; budget_minutes is {budget}"
    assert mutate["needs"] == "targets"
    assert mutate["strategy"]["matrix"]["repository"] == (
        "${{ fromJSON(needs.targets.outputs.repositories) }}"
    )


def run_targets(tmp_path: Path, named: str) -> tuple[subprocess.CompletedProcess[str], str]:
    """The targets step, over this repository's scripts/mutation.json."""
    out = tmp_path / "github-output"
    out.touch()
    env = dict(os.environ) | {"NAMED": named, "GITHUB_OUTPUT": str(out)}
    script = step_script(WEEKLY, "targets", "The repositories the list names")
    done = subprocess.run(
        ["bash", "-c", script], cwd=REPO, env=env, capture_output=True, text=True, check=False
    )
    return done, out.read_text(encoding="utf-8")


def test_the_weekly_runs_repositories_are_the_lists(tmp_path: Path) -> None:
    """One list names the repositories that get mutation testing (#332): the jobs follow it."""
    done, output = run_targets(tmp_path, "all")
    assert done.returncode == 0, done.stderr
    assert (
        output == f"repositories={json.dumps(list(SETTINGS.repositories), separators=(',', ':'))}\n"
    )


def test_a_dispatch_naming_a_listed_repository_runs(tmp_path: Path) -> None:
    done, output = run_targets(tmp_path, "troupe")
    assert done.returncode == 0, done.stderr
    assert output.startswith("repositories=")


def test_a_dispatch_naming_a_repository_the_list_doesnt_fails_naming_the_list(
    tmp_path: Path,
) -> None:
    done, output = run_targets(tmp_path, "website")
    assert done.returncode == 1
    assert "website isn't in scripts/mutation.json's repositories" in done.stdout
    assert '["troupe"]' in done.stdout
    assert output == ""


def test_the_dispatch_names_its_repository_as_text_not_a_fixed_choice() -> None:
    inputs = load(WEEKLY)[True]["workflow_dispatch"]["inputs"]
    assert inputs["repository"] == {
        "description": "One repository scripts/mutation.json lists, or all",
        "type": "string",
        "default": "all",
    }


def test_the_issues_job_checks_out_only_this_repository_and_asks_for_the_apps_permissions() -> None:
    issues = load(WEEKLY)["jobs"]["issues"]
    assert environment_of(issues) == "mutation-issues"
    assert issues["permissions"] == {"contents": "read", "pull-requests": "read"}
    for step in steps_using(issues, "actions/checkout"):
        given = step.get("with") or {}
        assert "repository" not in given, given
        assert "ref" not in given, given
    granted = declared_inputs(apps(), APP)
    assert granted == {"permission-issues": "write"}, f"{APP} is declared with {granted}"
    problems = token_problems(
        issues, "issues", "TEST_QUALITY_APP_PRIVATE_KEY", "TEST_QUALITY_APP_CLIENT_ID", granted
    )
    assert problems == []


def test_the_token_asking_for_more_than_the_app_is_granted_is_named() -> None:
    issues = load(WEEKLY)["jobs"]["issues"]
    [mint] = steps_using(issues, "create-github-app-token")
    mint["with"]["permission-pull-requests"] = "write"
    problems = token_problems(
        issues,
        "issues",
        "TEST_QUALITY_APP_PRIVATE_KEY",
        "TEST_QUALITY_APP_CLIENT_ID",
        {"permission-issues": "write"},
    )
    assert problems == [
        "issues's token asks for permission-pull-requests: write, which it isn't granted"
    ]


def test_the_board_job_adds_only_issues_in_the_three_repositories() -> None:
    board = load(WEEKLY)["jobs"]["board"]
    assert environment_of(board) == "board"
    script = board["steps"][-1]["run"]
    assert (
        "^https://github\\.com/troupe-run/(troupe|website|infrastructure)/issues/[0-9]+$" in script
    )


def test_the_weekly_run_is_watched_for_stopping() -> None:
    watched = json.loads((REPO / "scripts" / "watched-schedules.json").read_text(encoding="utf-8"))
    assert {
        "repository": "infrastructure",
        "workflow": "mutation.yml",
        "max_age_days": 2,
    } in watched


# The kept state (#378, mutation-incremental design D1, D1a)

CACHE = "actions/cache"


def mutate_steps() -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = load(WEEKLY)["jobs"]["mutate"]["steps"]
    return steps


def weekly_step(name: str) -> dict[str, Any]:
    [step] = [s for s in mutate_steps() if s.get("name") == name]
    return step


def test_a_dispatch_can_name_one_unit_or_ask_for_a_full_refresh() -> None:
    inputs = load(WEEKLY)[True]["workflow_dispatch"]["inputs"]
    assert inputs["unit"]["type"] == "string"
    assert inputs["unit"]["default"] == ""
    assert inputs["full-refresh"] == {
        "description": "Discard the kept mutmut state and fill afresh",
        "type": "boolean",
        "default": False,
    }
    mutate = weekly_step("Mutate")
    assert mutate["env"]["UNIT"] == "${{ inputs.unit }}"
    assert mutate["env"]["MUTATION_FULL_REFRESH"] == "${{ inputs.full-refresh }}"
    assert 'args+=(--unit "$UNIT")' in mutate["run"]


def test_the_state_is_restored_before_mutating_newest_first_by_repository_and_mutmut_version() -> (
    None
):
    steps = mutate_steps()
    names = [s.get("name") for s in steps]
    [key] = [s for s in steps if s.get("name") == "The kept state's cache key"]
    assert 'prefix="mutmut-state-$REPOSITORY-mutmut$mutmut-"' in key["run"]
    assert "key=$prefix$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT" in key["run"]
    [restore] = [s for s in steps if s.get("name") == "Restore the kept state"]
    assert restore["uses"].startswith(f"{CACHE}/restore@")
    assert restore["with"] == {
        "path": "state",
        "key": "${{ steps.state.outputs.key }}",
        "restore-keys": "${{ steps.state.outputs.prefix }}",
    }
    assert names.index("Restore the kept state") < names.index("Mutate")
    env = weekly_step("Mutate")["env"]
    assert env["MUTATION_STATE"] == "${{ github.workspace }}/state"
    assert env["MUTATION_PREVIOUS_STATE"] == (
        "${{ runner.temp }}/previous/state-${{ matrix.repository }}.json"
    )
    assert env["MUTATION_RUN_ID"] == "${{ github.run_id }}"


def test_the_repositorys_baselines_are_kept_before_the_run_whatever_it_exits() -> None:
    """A run that exits 3 for lost state still hands on its report, so the issues job must get
    the baselines too: copied before the run, or a below-baseline issue is closed (#380)."""
    script = weekly_step("Mutate")["run"]
    assert script.index('cp quality-gates.toml "../out/quality-gates-$REPOSITORY.toml"') < (
        script.index("run_contained python3")
    )


def test_the_save_keeps_only_this_runs_units_over_the_newest_entry_on_any_outcome() -> None:
    """Two runs overlapping, despite the concurrency group, can't drop each other's progress on a
    unit only one ran: the newest entry is restored again just before the save (D1a)."""
    steps = mutate_steps()
    names = [s.get("name") for s in steps]
    after = [
        "Keep what a killed run finished",
        "Set this run's state aside",
        "Restore the newest kept state again",
        "Keep this run's units over the newest kept state",
        "Save the kept state",
        "Check the kept state was saved",
    ]
    assert [n for n in names if n in after] == after
    assert names.index("Mutate") < names.index(after[0])
    by_name = {s.get("name"): s for s in steps}
    for name in after:
        assert by_name[name]["if"].startswith("always() && steps.skip.outputs.skip != 'true'")
    # A run killed outright wrote no record: its finished results are harvested first (#380).
    harvest = by_name["Keep what a killed run finished"]
    assert "hashFiles('out/state-*.json') == ''" in harvest["if"]
    assert "steps.mutate.outcome != 'skipped'" in harvest["if"]
    assert "state-harvest" in harvest["run"]
    # A killed full-refresh dispatch is a fresh fill, which the harvest can only tell from this.
    assert harvest["env"]["MUTATION_FULL_REFRESH"] == "${{ inputs.full-refresh }}"
    for name in after[1:]:
        assert "hashFiles('out/state-*.json') != ''" in by_name[name]["if"]
    again = by_name["Restore the newest kept state again"]
    assert again["uses"].startswith(f"{CACHE}/restore@")
    assert again["with"]["path"] == "state"
    assert again["with"]["restore-keys"] == "${{ steps.state.outputs.prefix }}"
    assert "state-merge" in by_name["Keep this run's units over the newest kept state"]["run"]
    save = by_name["Save the kept state"]
    assert save["uses"].startswith(f"{CACHE}/save@")
    assert save["with"] == {"path": "state", "key": "${{ steps.state.outputs.key }}"}
    assert "gh cache list" in by_name["Check the kept state was saved"]["run"]


# The pull request report


def test_the_pull_request_report_runs_on_pull_requests_only() -> None:
    workflow = load(PR)
    assert triggers(workflow) == {"pull_request"}
    assert workflow["permissions"] == {}


def test_the_job_that_runs_the_pull_requests_code_holds_no_write_token() -> None:
    mutate = load(PR)["jobs"]["mutate"]
    assert mutate["permissions"] == {"contents": "read"}
    assert "environment" not in mutate
    assert "secrets." not in json.dumps(mutate)
    assert mutate["needs"] == "listed"
    assert mutate["if"] == (
        "${{ !github.event.pull_request.draft && needs.listed.outputs.listed == 'true' }}"
    )
    assert mutate["timeout-minutes"] == SETTINGS.pr_budget_minutes + 30


def mutate_step(name: str) -> dict[str, Any]:
    [step] = [s for s in load(PR)["jobs"]["mutate"]["steps"] if s.get("name") == name]
    found: dict[str, Any] = step
    return found


def test_the_mutate_job_tests_the_merge_with_the_base_not_the_branch_alone() -> None:
    """A branch made before a delivery lacks scripts/mutation.json and the scripts; the merge with
    the base has them, as the pull request's merge would (troupe#444's run; #332)."""
    [checkout] = steps_using(load(PR)["jobs"]["mutate"], "actions/checkout")
    assert checkout["with"] == {"ref": "${{ github.sha }}", "fetch-depth": 0}
    mutate = mutate_step("Mutate what changed")
    assert mutate["env"] == {
        "MERGE": "${{ github.sha }}",
        "RESOURCES": "${{ github.workspace }}/out/resources-pr.log",
        "PEAKS": "${{ github.workspace }}/out/peaks-pr.log",
        "MUTATION_SCRIPTS": "${{ github.workspace }}/scripts",
    }
    assert 'BASE=$(git rev-parse "$MERGE^1")' in mutate["run"]
    assert "pull_request.head.sha" not in json.dumps(load(PR)["jobs"]["mutate"])


def git(cwd: Path, *args: str) -> str:
    identity = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}  # fmt: skip
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | identity
    done = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def test_the_merges_first_parent_gives_only_the_pull_requests_lines(tmp_path: Path) -> None:
    """Diffing the merge against its first parent, as the job does, reports only what the pull
    request changed, while the checkout holds what main delivered after the branch was made."""
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "a.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "switch", "-q", "-c", "branch")
    (tmp_path / "a.py").write_text("x = 1\ny = 3\n", encoding="utf-8")
    git(tmp_path, "commit", "-q", "-am", "the pull request")
    git(tmp_path, "switch", "-q", "main")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "mutation.json").write_text("{}\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "a delivery after the branch was made")
    git(tmp_path, "merge", "-q", "--no-ff", "-m", "merge", "branch")
    merge = git(tmp_path, "rev-parse", "HEAD")
    base = git(tmp_path, "rev-parse", f"{merge}^1")
    assert pr.changed_lines(pr.git_diff(tmp_path, base, merge)) == {"a.py": {2}}
    assert git(tmp_path, "ls-tree", "--name-only", "-r", merge).splitlines() == [
        "a.py",
        "scripts/mutation.json",
    ]


def run_listed(tmp_path: Path, repository: str) -> tuple[subprocess.CompletedProcess[str], str]:
    """The gate step, over this repository's scripts/mutation.json."""
    out = tmp_path / "github-output"
    out.touch()
    env = dict(os.environ) | {"GITHUB_REPOSITORY": repository, "GITHUB_OUTPUT": str(out)}
    script = str(load(PR)["jobs"]["listed"]["steps"][-1]["run"])
    done = subprocess.run(
        ["bash", "-c", script], cwd=REPO, env=env, capture_output=True, text=True, check=False
    )
    return done, out.read_text(encoding="utf-8")


def test_a_listed_repositorys_pull_request_is_mutated(tmp_path: Path) -> None:
    done, output = run_listed(tmp_path, "troupe-run/troupe")
    assert done.returncode == 0, done.stderr
    assert output == "listed=true\n"


def test_an_unlisted_repositorys_pull_request_runs_nothing_and_says_why(tmp_path: Path) -> None:
    """infrastructure holds the workflow as its source but isn't on the list (#332): its own pull
    requests mutate nothing, rather than fail."""
    done, output = run_listed(tmp_path, "troupe-run/infrastructure")
    assert done.returncode == 0, done.stderr
    assert output == "listed=false\n"
    assert "infrastructure isn't in scripts/mutation.json's repositories" in done.stdout


def test_the_gate_reads_the_list_from_the_merge_only() -> None:
    listed = load(PR)["jobs"]["listed"]
    assert listed["permissions"] == {"contents": "read"}
    [checkout] = steps_using(listed, "actions/checkout")
    assert checkout["with"] == {
        "ref": "${{ github.sha }}",
        "sparse-checkout": "scripts/mutation.json",
        "sparse-checkout-cone-mode": False,
    }


BEGIN, END = "# resources: begin", "# resources: end"


def sampler_block(path: Path, job: str, step: str) -> str:
    script = step_script(path, job, step)
    assert BEGIN in script, f"{path.name}'s {step!r} step doesn't record the runner's resources"
    return script[script.index(BEGIN) : script.index(END) + len(END)]


def test_both_runs_record_the_runners_resources_the_same_way() -> None:
    """Both mutate jobs carry the one sampler, so a lost runner leaves readings either way
    (#337; mutation-resources design D1)."""
    weekly = sampler_block(WEEKLY, "mutate", "Mutate")
    pr = sampler_block(PR, "mutate", "Mutate what changed")
    assert weekly == pr


def test_the_sampler_logs_and_files_a_reading_a_minute_and_reports_the_lowest(
    tmp_path: Path,
) -> None:
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(
        "MemTotal:       16000000 kB\nMemAvailable:    2048000 kB\nSwapFree:        1024000 kB\n",
        encoding="utf-8",
    )
    loadavg = tmp_path / "loadavg"
    loadavg.write_text("3.50 2.00 1.00 1/200 999\n", encoding="utf-8")
    summary = tmp_path / "summary.md"
    readings = tmp_path / "out" / "resources.log"
    # Earlier readings on both sides of the live one (2000): only the true minimum, with its own
    # time, passes, not the first, the last or the largest.
    readings.parent.mkdir()
    earlier = ("09:00:00 mem_available_mb=3000", "09:01:00 mem_available_mb=1500",
               "09:02:00 mem_available_mb=2500")  # fmt: skip
    readings.write_text("\n".join(earlier) + "\n", encoding="utf-8")
    script = "set -euo pipefail\n" + sampler_block(WEEKLY, "mutate", "Mutate") + "\nsleep 2.5\n"
    env = dict(os.environ) | {
        "RESOURCES": str(readings),
        "RESOURCES_MEMINFO": str(meminfo),
        "RESOURCES_LOADAVG": str(loadavg),
        "RESOURCES_SECONDS": "1",
        "GITHUB_STEP_SUMMARY": str(summary),
    }
    done = subprocess.run(
        ["bash", "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True,
        check=False, timeout=30,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    lines = readings.read_text(encoding="utf-8").splitlines()[3:]
    assert len(lines) >= 2
    fields = dict(field.split("=", 1) for field in lines[0].split()[1:])
    assert fields["mem_available_mb"] == "2000"
    assert fields["swap_free_mb"] == "1000"
    assert fields["load1"] == "3.50"
    assert int(fields["disk_free_mb"]) > 0
    assert fields["mutmut_processes"].isdigit()
    logged = [line for line in done.stdout.splitlines() if line.startswith("resources: ")]
    assert len(logged) >= len(lines)
    assert "resources: lowest mem_available_mb=1500 at 09:01:00" in done.stdout
    assert "lowest free memory: 1500 MB at 09:01:00 UTC" in summary.read_text(encoding="utf-8")


def test_the_weekly_run_keeps_its_readings_with_its_report_whatever_the_outcome() -> None:
    """The readings file is inside out/, which the report upload carries on any outcome but
    cancelled (#337)."""
    steps = load(WEEKLY)["jobs"]["mutate"]["steps"]
    [mutate] = [s for s in steps if s.get("name") == "Mutate"]
    assert mutate["env"]["RESOURCES"] == (
        "${{ github.workspace }}/out/resources-${{ matrix.repository }}.log"
    )
    [upload] = [
        s for s in steps
        if s.get("with", {}).get("name") == "report-${{ matrix.repository }}"
    ]  # fmt: skip
    assert upload["if"] == "${{ !cancelled() }}"
    assert upload["with"]["path"] == "out/"


RUNS = {
    (WEEKLY, "Mutate"): (
        'python3 ../infra/scripts/mutation_run.py "${args[@]}"',
        'uv run --no-sync python ../infra/scripts/mutation_run.py "${args[@]}"',
    ),
    (PR, "Mutate what changed"): (
        'python3 scripts/mutation_pr.py run "$BASE" "$HEAD" out/pr-report.json',
        'uv run --no-sync python scripts/mutation_pr.py run "$BASE" "$HEAD" out/pr-report.json',
    ),
}


CONTAIN_BEGIN, CONTAIN_END = "# containment: begin", "# containment: end"


def containment_block(path: Path, step: str) -> str:
    script = step_script(path, "mutate", step)
    assert CONTAIN_BEGIN in script, f"{path.name}'s {step!r} step doesn't contain its run"
    return script[script.index(CONTAIN_BEGIN) : script.index(CONTAIN_END) + len(CONTAIN_END)]


def test_both_runs_mutate_in_their_own_namespace_and_cgroup() -> None:
    """A mutant that signals every process (kill -1), or starvation, lost the runner four times;
    the run is contained instead, the same way in both workflows, after the sampler, which stays
    in the step's shell (#345, mutation-container design D2)."""
    blocks = {containment_block(path, step) for path, step in RUNS}
    assert len(blocks) == 1, "the two workflows' containment blocks differ"
    [block] = blocks
    for part in (
        'export -p > "$saved"',
        "systemd-run --scope --quiet --expand-environment=no",
        "-p MemoryMax=",
        "-p MemorySwapMax=0",
        "-p TasksMax=",
        "unshare --pid --fork --mount-proc --kill-child",
        "setsid --wait",
        "setpriv --reuid=",
        "MUTATION_MEMORY_MAX:-12G",
        "MUTATION_TASKS_MAX:-8192",
        "journalctl -k",
    ):
        assert part in block, part
    for (path, step), lines in RUNS.items():
        script = step_script(path, "mutate", step)
        for line in lines:
            assert f"run_contained {line}" in script, (path.name, line)
            assert f"setsid --wait {line}" not in script, (path.name, "#341's prefix is left", line)
        assert script.index(END) < script.index(CONTAIN_BEGIN), path.name


def can_contain() -> bool:
    """Linux with passwordless sudo and the tools: CI's runners, never a laptop (design D4)."""
    tools = ("sudo", "systemd-run", "unshare", "setpriv", "journalctl")
    if sys.platform != "linux" or any(shutil.which(t) is None for t in tools):
        return False
    return subprocess.run(["sudo", "-n", "true"], capture_output=True, check=False).returncode == 0


def containment_required(env: dict[str, str] | os._Environ[str], platform: str) -> bool:
    """Where the containment tests must run, never skip: GitHub Actions on Linux, CI's check leg,
    whose runner has passwordless sudo and systemd-run (#345)."""
    return env.get("GITHUB_ACTIONS") == "true" and platform == "linux"


@pytest.mark.parametrize(
    ("env", "platform", "required"),
    [
        ({"GITHUB_ACTIONS": "true"}, "linux", True),
        ({"GITHUB_ACTIONS": "true"}, "darwin", False),
        ({}, "linux", False),
        ({"GITHUB_ACTIONS": "false"}, "linux", False),
    ],
)
def test_the_containment_tests_are_required_on_ci_linux_only(
    env: dict[str, str], platform: str, required: bool
) -> None:
    assert containment_required(env, platform) is required


def test_the_containment_tests_run_where_they_must() -> None:
    """They skip without Linux, passwordless sudo and systemd-run. On CI's check leg that would
    make them no tests at all, so it fails here instead."""
    if containment_required(os.environ, sys.platform):
        assert can_contain(), (
            "CI's check leg can't run the containment tests (sudo -n, systemd-run, unshare, "
            "setpriv or journalctl missing): they'd all skip"
        )


CONTAINED = pytest.mark.skipif(
    not can_contain(), reason="needs Linux with passwordless sudo and systemd-run: CI runs this"
)


def run_contained(tmp_path: Path, command: str, **env: str) -> subprocess.CompletedProcess[str]:
    """The block, run in a fresh session of its own, so nothing it does reaches this test."""
    script = "set -euo pipefail\n" + containment_block(WEEKLY, "Mutate") + "\n" + command + "\n"
    return subprocess.run(
        ["bash", "-c", script], cwd=tmp_path, env=dict(os.environ) | env,
        capture_output=True, text=True, check=False, timeout=120, start_new_session=True,
    )  # fmt: skip


@CONTAINED
def test_the_contained_run_sees_only_its_own_processes_as_the_runner_with_the_steps_variables(
    tmp_path: Path,
) -> None:
    done = run_contained(
        tmp_path,
        "run_contained bash -c "
        "'echo \"pid=$$ uid=$(id -u) var=$PROBE_VAR path=$PATH\"; ps -e -o pid= | wc -l'",
        PROBE_VAR="kept",
    )
    assert done.returncode == 0, (done.stdout, done.stderr)
    first, count = done.stdout.split("\n")[:2]
    fields = dict(field.split("=", 1) for field in first.split())
    assert fields["pid"] in {"1", "2"}, first
    assert fields["uid"] == str(os.getuid())
    assert fields["var"] == "kept"
    assert fields["path"] == os.environ["PATH"], "sudo's secure path replaced the step's PATH"
    assert int(count) <= 5, f"the run sees {count} processes: not a namespace of its own"


@CONTAINED
def test_a_run_over_its_memory_limit_ends_and_says_it_ran_out_of_memory(tmp_path: Path) -> None:
    done = run_contained(
        tmp_path,
        "run_contained python3 -c 'b = bytearray(512 * 1024 * 1024)'",
        MUTATION_MEMORY_MAX="64M",
    )
    assert done.returncode == 137, (done.returncode, done.stdout, done.stderr)
    assert "::error::the mutation run ran out of memory (MemoryMax 64M)" in done.stdout


@CONTAINED
def test_a_kill_of_every_process_inside_reaches_nothing_outside(tmp_path: Path) -> None:
    """The case #345 is about: a mutant's kill(-1). A process of the same user outside the
    namespace stands in for the runner agent, and survives. Inside, everything but the run's init
    dies; the init (pid 1) is spared, as kill(-1) always spares it, so the run ends normally."""
    sentinel = subprocess.Popen(["sleep", "300"], start_new_session=True)
    try:
        done = run_contained(
            tmp_path, "run_contained bash -c 'sleep 30 & kill -9 -1; wait; echo inside-done'"
        )
        assert sentinel.poll() is None, "kill -9 -1 inside reached a process outside the namespace"
        assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
        assert "inside-done" in done.stdout
    finally:
        sentinel.kill()
        sentinel.wait()


STATE_OF = """
def state_of(pid):
    # None once the process is gone: the open fails (ENOENT), the read fails because it was reaped
    # after the open (ESRCH, ProcessLookupError), or the read comes back empty (#407).
    try:
        with open(f"/proc/{pid}/stat") as stat:
            line = stat.read()
    except (FileNotFoundError, ProcessLookupError):
        return None
    if not line:
        return None
    if ")" not in line:
        raise ValueError(f"/proc/{pid}/stat has no ')' after the name: {line!r}")
    return line.rsplit(")", 1)[1].split()[0]
"""

ORPHAN = (
    STATE_OF
    + """
import os, signal, subprocess, sys, time
start = ["sh", "-c", "sleep 300 >/dev/null 2>&1 & echo $!"]
out = subprocess.run(start, capture_output=True, text=True, check=True).stdout
# Its parent, sh, has exited: it's an orphan, reparented to the namespace's pid 1.
grandchild = int(out)
os.kill(grandchild, signal.SIGKILL)
for _ in range(50):
    state = state_of(grandchild)
    if state is None:
        print("reaped")
        sys.exit(0)
    time.sleep(0.1)
print("left as", state)
sys.exit(1)
"""
)


def state_of_reading(read: Callable[[], str]) -> Callable[[int], str | None]:
    """ORPHAN's `state_of`, with `open` replaced by a stub whose file's `read` calls `read`. The
    function looks `open` up in its own namespace before the builtins, so nothing global changes."""

    class Stat(io.StringIO):
        def read(self, size: int | None = -1) -> str:
            return str(read())

    namespace: dict[str, Any] = {"open": lambda path: Stat()}
    exec(STATE_OF, namespace)  # noqa: S102 (this file's own constant, the code under test)
    state_of: Callable[[int], str | None] = namespace["state_of"]
    return state_of


def vanished_mid_read() -> str:
    raise ProcessLookupError(3, "No such process")


def test_a_process_reaped_between_the_open_and_the_read_counts_as_reaped() -> None:
    """The read of /proc/<pid>/stat fails with ESRCH when the reap lands after the open (#407)."""
    assert state_of_reading(vanished_mid_read)(42) is None


def test_an_empty_read_of_stat_counts_as_reaped() -> None:
    assert state_of_reading(lambda: "")(42) is None


def test_a_stat_line_gives_the_state_letter_even_with_a_paren_in_the_name() -> None:
    assert state_of_reading(lambda: "42 (sl) eep) Z 1 42 42 0 -1\n")(42) == "Z"


def test_a_stat_line_with_no_closing_paren_is_an_error_not_reaped() -> None:
    with pytest.raises(ValueError, match="/proc/42/stat"):
        state_of_reading(lambda: "42 sleep Z 1")(42)


def test_the_runs_init_waits_for_the_command_rather_than_becoming_it() -> None:
    """The restoring bash stays pid 1 of the namespace, so it reaps orphans (#347, design D1)."""
    block = containment_block(WEEKLY, "Mutate")
    assert """bash -c 'source "$1"; shift; "$@"; exit $?' restore""" in block
    assert 'exec "$@"' not in block


@CONTAINED
def test_the_command_keeps_its_stdin_and_default_sigint(tmp_path: Path) -> None:
    """A backgrounded command would get /dev/null and an ignored SIGINT, inherited by every test
    process (from the review of #360); the init runs it in the foreground instead."""
    script = tmp_path / "signals.py"
    script.write_text(
        "import signal, sys\n"
        "print('sigint', signal.getsignal(signal.SIGINT) is signal.default_int_handler)\n"
        "print('stdin', sys.stdin.read().strip())\n",
        encoding="utf-8",
    )
    block = containment_block(WEEKLY, "Mutate")
    done = subprocess.run(
        ["bash", "-c", f"set -euo pipefail\n{block}\nrun_contained python3 {script}\n"],
        cwd=tmp_path, input="piped\n", capture_output=True, text=True, check=False, timeout=120,
        start_new_session=True,
    )  # fmt: skip
    assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
    assert "sigint True" in done.stdout
    assert "stdin piped" in done.stdout


@CONTAINED
def test_an_orphan_reparented_to_the_runs_init_is_reaped(tmp_path: Path) -> None:
    """troupe's grandchild test, in small: a Python command (as mutation_run.py is) orphans a
    grandchild and kills it. Unless pid 1 reaps it, it stays a zombie, which troupe counts as
    running (#347)."""
    script = tmp_path / "orphan.py"
    script.write_text(ORPHAN, encoding="utf-8")
    done = run_contained(tmp_path, f"run_contained python3 {script}")
    assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
    assert "reaped" in done.stdout


@CONTAINED
@pytest.mark.parametrize(
    ("command", "status"),
    [("sh -c 'exit 3'", 3), ("sh -c 'kill -9 $$'", 137)],
)
def test_the_commands_status_passes_through_the_init(
    tmp_path: Path, command: str, status: int
) -> None:
    done = run_contained(tmp_path, f"run_contained {command}")
    assert done.returncode == status, (done.returncode, done.stdout, done.stderr)


@CONTAINED
def test_a_status_above_128_is_reported_as_the_signal_it_means(tmp_path: Path) -> None:
    # The command (pid 2, under the init bash) kills a child of its own and passes its 137 on,
    # which the init returns.
    done = run_contained(tmp_path, "run_contained bash -c 'sh -c \"kill -9 \\$\\$\"; exit $?'")
    assert done.returncode == 137, (done.returncode, done.stdout, done.stderr)
    assert "::error::the mutation run was killed by signal 9" in done.stdout


@CONTAINED
def test_a_run_that_kills_its_own_group_fails_the_step_and_spares_its_shell(
    tmp_path: Path,
) -> None:
    """The weekly step itself, with a stand-in run that kills its own process group. The script
    runs in a fresh session, so even a broken step can't reach this test."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # A child kills its group, the run's session: the stand-in run dies with it, and the init bash
    # (pid 1, which ignores a SIGKILL from inside its namespace) reports the 137.
    (bin_dir / "uv").write_text("#!/bin/sh\nsh -c 'kill -9 0'\nexit $?\n", encoding="utf-8")
    (bin_dir / "uv").chmod(0o755)
    (tmp_path / "target").mkdir()
    readings = tmp_path / "out" / "resources-troupe.log"
    readings.parent.mkdir()
    readings.write_text("09:00:00 mem_available_mb=1500\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")} | {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "REPOSITORY": "troupe",
        "PREVIOUS": "",
        "RESOURCES": str(readings),
        "RESOURCES_SECONDS": "30",
    }
    done = subprocess.run(
        ["bash", "-e", "-c", step_script(WEEKLY, "mutate", "Mutate")],
        cwd=tmp_path / "target", env=env, capture_output=True, text=True, check=False,
        timeout=60, start_new_session=True,
    )  # fmt: skip
    assert done.returncode == 137, (done.returncode, done.stdout, done.stderr)
    # The step's own shell lived to run its exit trap: the readings' summary.
    assert "resources: lowest mem_available_mb=1500 at 09:00:00" in done.stdout


JOURNAL = """\
2026-11-19T23:20:00+00:00 runner sshd[5]: Accepted publickey for runner
2026-11-19T23:26:23+00:00 runner kernel: Out of memory: Killed process 123 (python)
2026-11-19T23:26:23+00:00 runner systemd-oomd[1]: Killed /system.slice/x.scope: memory pressure
2026-11-19T23:26:24+00:00 runner systemd[1]: Stopping actions.runner.service...
2026-11-19T23:26:25+00:00 runner CRON[9]: (root) CMD (true)
2026-11-19T23:21:00+00:00 runner systemd[1]: Stopped apt-daily.timer.
2026-11-19T23:21:01+00:00 runner systemd[1]: run-docker-runtime.mount: Deactivated successfully.
2026-11-19T23:21:02+00:00 runner kernel: no room left in the ring buffer
2026-11-19T23:26:26+00:00 runner systemd[1]: mutation-1-m-2.scope: Killing process 4 (SIGKILL).
"""


def run_sampler_exit(
    tmp_path: Path,
    journal: str | None,
    readings_name: str = "resources-troupe.log",
    extra_env: dict[str, str] | None = None,
) -> tuple[str, Path]:
    """The sampler block, exiting at once, with a stand-in sudo that prints `journal` for
    journalctl (or fails, as sudo -n does where it can't run)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fixture = tmp_path / "journal.txt"
    fixture.write_text(journal or "", encoding="utf-8")
    body = f'case "$*" in *journalctl*) cat "{fixture}";; esac\n' if journal else "exit 1\n"
    (bin_dir / "sudo").write_text("#!/bin/sh\n" + body, encoding="utf-8")
    (bin_dir / "sudo").chmod(0o755)
    readings = tmp_path / "out" / readings_name
    script = "set -euo pipefail\n" + sampler_block(WEEKLY, "mutate", "Mutate") + "\nexit 0\n"
    env = (
        dict(os.environ)
        | {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "RESOURCES": str(readings),
            "RESOURCES_MEMINFO": str(tmp_path / "meminfo"),
            "RESOURCES_LOADAVG": str(tmp_path / "loadavg"),
            "RESOURCES_SECONDS": "30",
        }
        | (extra_env or {})
    )
    (tmp_path / "meminfo").write_text("MemAvailable: 1024 kB\nSwapFree: 0 kB\n", encoding="utf-8")
    (tmp_path / "loadavg").write_text("0.10 0 0 1/1 1\n", encoding="utf-8")
    done = subprocess.run(
        ["bash", "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True,
        check=False, timeout=30,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    return done.stdout, tmp_path / "out" / "journal-troupe.log"


def test_the_step_saves_the_journal_lines_that_say_who_ended_the_run(tmp_path: Path) -> None:
    """A SIGTERM to the step itself (dry run 44633465646) left no trace of its sender: the exit
    trap now keeps the lines since the step began from the sources that can name one (the kernel's
    OOM lines, systemd-oomd, and systemd on the runner's service or the run's own scope), and not
    other units stopping or words that merely contain "oom" (#361)."""
    stdout, journal = run_sampler_exit(tmp_path, JOURNAL)
    kept = journal.read_text(encoding="utf-8").splitlines()
    assert kept == [
        "2026-11-19T23:26:23+00:00 runner kernel: Out of memory: Killed process 123 (python)",
        "2026-11-19T23:26:23+00:00 runner systemd-oomd[1]: "
        "Killed /system.slice/x.scope: memory pressure",
        "2026-11-19T23:26:24+00:00 runner systemd[1]: Stopping actions.runner.service...",
        "2026-11-19T23:26:26+00:00 runner systemd[1]: mutation-1-m-2.scope: "
        "Killing process 4 (SIGKILL).",
    ]
    assert [line for line in stdout.splitlines() if line.startswith("journal: ")] == [
        f"journal: {line}" for line in kept
    ]


@pytest.mark.parametrize("readings_name", ["readings.log", "resources.log"])
def test_the_journal_file_is_never_the_readings_file(tmp_path: Path, readings_name: str) -> None:
    """A readings file not named resources-<repository>.log once became the journal's own path, so
    the capture overwrote the readings and then deleted them (#361's review)."""
    readings = tmp_path / "out" / readings_name
    readings.parent.mkdir()
    reading = "23:06:49 mem_available_mb=14708 swap_free_mb=3071 disk_free_mb=88678 load1=0.37\n"
    readings.write_text(reading, encoding="utf-8")
    run_sampler_exit(tmp_path, JOURNAL, readings_name)
    assert readings.read_text(encoding="utf-8").startswith(reading), "the readings were lost"
    journals = sorted(p.name for p in (tmp_path / "out").glob("journal-*"))
    assert len(journals) == 1, journals
    assert journals[0] != readings_name
    assert "Out of memory" in (tmp_path / "out" / journals[0]).read_text(encoding="utf-8")


def test_without_a_readable_journal_the_step_saves_nothing_and_still_ends_cleanly(
    tmp_path: Path,
) -> None:
    stdout, journal = run_sampler_exit(tmp_path, None)
    assert not journal.exists()
    assert "journal: " not in stdout


def test_the_pull_request_run_keeps_its_readings_when_it_fails() -> None:
    [upload] = [
        s for s in load(PR)["jobs"]["mutate"]["steps"]
        if s.get("with", {}).get("name") == "resources"
    ]  # fmt: skip
    assert upload["if"] == "${{ !cancelled() }}"
    assert upload["with"]["path"].split() == [
        "out/resources-pr.log",
        "out/journal-pr.log",
        "out/peaks-pr.log",
    ]


def test_the_comment_job_checks_out_the_base_commit_only() -> None:
    comment = load(PR)["jobs"]["comment"]
    assert comment["permissions"] == {"contents": "read", "pull-requests": "write"}
    [checkout] = steps_using(comment, "actions/checkout")
    assert checkout["with"] == {"ref": "${{ github.event.pull_request.base.sha }}"}


def test_neither_workflow_is_a_required_check() -> None:
    required = json.loads((REPO / "tofu" / "required-checks.json").read_text(encoding="utf-8"))
    contexts = {check["context"] for checks in required.values() for check in checks}
    names = {
        job.get("name", key) for path in (WEEKLY, PR) for key, job in load(path)["jobs"].items()
    }
    assert not contexts & names, contexts & names


def test_the_pull_request_report_and_what_it_runs_are_delivered() -> None:
    import tofu_text

    delivered = set(
        tofu_text.mutation_report_files(
            (REPO / "tofu" / "guard_delivery.tf").read_text(encoding="utf-8")
        )
    )
    needed = {
        ".github/workflows/mutation-pr.yml",
        "scripts/mutation.json",
        "scripts/mutation_children.py",
        "scripts/mutation_pr.py",
        "scripts/mutation_report.py",
        "scripts/mutation_run.py",
        "scripts/mutation_settings.py",
        # mutation_run.py runs it for the survivors' diffs (#404): without it troupe's report fails.
        "scripts/mutation_show.py",
        # mutation_run.py imports it (#378): without it troupe's copy fails on import.
        "scripts/mutation_state.py",
    }
    assert needed <= delivered, needed - delivered
    # The weekly run, its issue upkeep and the App's credential stay here.
    assert not {".github/workflows/mutation.yml", "scripts/mutation_issues.py"} & delivered
    # Only to the targets the one list names (#332): the delivery reads it, and nothing else.
    tf = (REPO / "tofu" / "guard_delivery.tf").read_text(encoding="utf-8")
    assert (
        'mutation_listed = toset(keys(jsondecode(file("${path.module}/../scripts/mutation.json"))'
        ".repositories))" in tf
    )
    assert (
        "contains(local.mutation_listed, repository) ? local.mutation_report_files : toset([])"
        in tf
    )


# The steps' own scripts, run with gh faked on the PATH (bash, jq and unzip as on the runner)


def step_script(path: Path, job: str, name: str) -> str:
    [step] = [s for s in load(path)["jobs"][job]["steps"] if s.get("name") == name]
    return str(step["run"])


def fake_gh(tmp_path: Path, script: str) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text("#!/bin/sh\n" + script, encoding="utf-8")
    gh.chmod(0o755)
    # This interpreter's directory before the system's, so python3 is 3.12+ as on the runner.
    python = Path(sys.executable).parent
    return {"PATH": f"{bin_dir}:{python}:/usr/bin:/bin:/opt/homebrew/bin", "HOME": str(tmp_path)}


def test_a_previous_run_that_skipped_the_repository_calls_nothing_new_and_doesnt_fail(
    tmp_path: Path,
) -> None:
    import subprocess
    import zipfile

    with zipfile.ZipFile(tmp_path / "artifact.zip", "w") as archive:
        archive.writestr("skipped-troupe", "")
    env = fake_gh(
        tmp_path,
        'case "$*" in\n'
        '  "run list"*) echo 41;;\n'
        '  *"/runs/41/artifacts"*) echo 7;;\n'
        f'  *"/artifacts/7/zip"*) cat "{tmp_path}/artifact.zip";;\n'
        "esac\n",
    )
    out = tmp_path / "github-output"
    out.touch()
    env |= {
        "GH_TOKEN": "x",
        "REPOSITORY": "troupe",
        "GITHUB_REPOSITORY": "troupe-run/infrastructure",
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_OUTPUT": str(out),
    }
    script = step_script(WEEKLY, "mutate", "The previous run's tested commit")
    done = subprocess.run(
        ["bash", "-c", script], env=env, capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
    assert "didn't mutate troupe: nothing is called new" in done.stdout
    assert out.read_text(encoding="utf-8") == ""


def run_comment_step(tmp_path: Path, nothing: bool, existing: str) -> list[str]:
    import subprocess

    calls = tmp_path / "calls"
    env = fake_gh(
        tmp_path,
        f'echo "$*" >> "{calls}"\ncase "$*" in *"--paginate"*) printf "{existing}";; esac\n',
    )
    (tmp_path / "out").mkdir()
    fields = {
        "version": 1,
        "repository": "troupe",
        "nothing": nothing,
        "finished": True,
        "mutants": 0,
        "caught": 0,
        "survivors": [],
        "timings": {"total": 1.0},
    }
    (tmp_path / "out" / "pr-report.json").write_text(json.dumps(fields), encoding="utf-8")
    (tmp_path / "scripts").symlink_to(REPO / "scripts")
    env |= {
        "GH_TOKEN": "x",
        "NUMBER": "5",
        "GITHUB_REPOSITORY": "troupe-run/troupe",
        "RUNNER_TEMP": str(tmp_path),
    }
    script = step_script(PR, "comment", "Keep one comment on the pull request")
    done = subprocess.run(
        ["bash", "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
    return calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []


def test_a_pull_request_with_nothing_to_mutate_and_no_comment_gets_none(tmp_path: Path) -> None:
    calls = run_comment_step(tmp_path, nothing=True, existing="")
    assert [call for call in calls if "--paginate" not in call] == []


def test_a_pull_request_with_an_earlier_comment_has_it_edited_even_when_nothing_was_mutated(
    tmp_path: Path,
) -> None:
    calls = run_comment_step(tmp_path, nothing=True, existing="99")
    assert [call.split()[:4] for call in calls if "--paginate" not in call] == [
        ["api", "-X", "PATCH", "repos/troupe-run/troupe/issues/comments/99"]
    ]


def test_a_pull_request_with_mutants_gets_a_new_comment(tmp_path: Path) -> None:
    calls = run_comment_step(tmp_path, nothing=False, existing="")
    assert [call.split()[:2] for call in calls if "--paginate" not in call] == [
        ["api", "repos/troupe-run/troupe/issues/5/comments"]
    ]


def test_every_tflint_and_tofu_install_matches_ci() -> None:
    import check

    ci = load(REPO / ".github" / "workflows" / "ci.yml")
    [ci_tofu] = [
        s
        for s in ci["jobs"]["check"]["steps"]
        if str(s.get("uses", "")).startswith("opentofu/setup-opentofu@")
    ]
    for path, job in ((WEEKLY, "mutate"), (PR, "mutate")):
        steps = load(path)["jobs"][job]["steps"]
        tflint = [
            s for s in steps if str(s.get("uses", "")).startswith("terraform-linters/setup-tflint@")
        ]
        tofu = [s for s in steps if str(s.get("uses", "")).startswith("opentofu/setup-opentofu@")]
        assert [s["with"]["tflint_version"] for s in tflint] == [check.tflint_version()], path.name
        assert [s["with"]["tofu_version"] for s in tofu] == [ci_tofu["with"]["tofu_version"]], (
            path.name
        )


KILLED_WRITER = """
import os, signal, sys
with open(sys.argv[1], "a") as peaks:
    peaks.write("unit troupe\\nmutmut 2097152 1048576\\nm.a__mutmut_9 5818072 5132328\\n")
os.kill(os.getpid(), signal.SIGKILL)
"""


def test_the_step_prints_the_memory_summary_even_when_the_run_was_killed(tmp_path: Path) -> None:
    """The run's cgroup OOM kill took a summary printed by the run down with it (dry run
    44673717060). The step's exit trap, outside the run, prints it from the uploaded file (#371)."""
    peaks = tmp_path / "out" / "peaks-troupe.log"
    peaks.parent.mkdir()
    killed = subprocess.run([sys.executable, "-c", KILLED_WRITER, str(peaks)], check=False)
    assert killed.returncode == -9
    stdout, _ = run_sampler_exit(
        tmp_path,
        None,
        extra_env={"PEAKS": str(peaks), "MUTATION_SCRIPTS": str(REPO / "scripts")},
    )
    assert [line for line in stdout.splitlines() if line.startswith("memory: ")] == [
        "memory: troupe mutmut VmPeak=2048 MB VmHWM=1024 MB",
        "memory: troupe mutant m.a__mutmut_9 VmPeak=5682 MB VmHWM=5012 MB",
        "memory: troupe 2 processes recorded",
    ]


@pytest.mark.parametrize("peaks", [None, ""])
def test_without_peaks_the_step_prints_no_summary_and_ends_cleanly(
    tmp_path: Path, peaks: str | None
) -> None:
    extra = {"MUTATION_SCRIPTS": str(REPO / "scripts")}
    if peaks is not None:
        (tmp_path / "out").mkdir()
        (tmp_path / "out" / "peaks-troupe.log").write_text(peaks, encoding="utf-8")
        extra["PEAKS"] = str(tmp_path / "out" / "peaks-troupe.log")
    stdout, _ = run_sampler_exit(tmp_path, None, extra_env=extra)
    assert "memory: " not in stdout


def test_both_runs_name_their_peaks_file_and_scripts_and_keep_the_file() -> None:
    [weekly] = [s for s in load(WEEKLY)["jobs"]["mutate"]["steps"] if s.get("name") == "Mutate"]
    assert (
        weekly["env"]["PEAKS"] == "${{ github.workspace }}/out/peaks-${{ matrix.repository }}.log"
    )
    assert weekly["env"]["MUTATION_SCRIPTS"] == "${{ github.workspace }}/infra/scripts"
    [upload] = [
        s for s in load(PR)["jobs"]["mutate"]["steps"]
        if s.get("with", {}).get("name") == "resources"
    ]  # fmt: skip
    assert "out/peaks-pr.log" in upload["with"]["path"].split()
