"""The weekly mutation run and the pull request report hold no secret where they run code, never
block a merge, and keep their budgets and token in step with their declarations (spec:
mutation-testing, mutation-issue-credentials; lint-mutation design D3, D4, D9)."""

import json
import os
import shutil
import subprocess
import sys
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
    assert workflow[True]["schedule"] == [{"cron": "23 3 * * 0"}]
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
        "max_age_days": 8,
    } in watched


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
        "sudo --preserve-env env",
        "systemd-run --scope",
        "-p MemoryMax=",
        "-p MemorySwapMax=0",
        "-p TasksMax=",
        "unshare --pid --fork --mount-proc --kill-child",
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
        assert "setsid --wait" not in script, path.name
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


@CONTAINED
def test_a_status_above_128_is_reported_as_the_signal_it_means(tmp_path: Path) -> None:
    # The run is pid 1 of its namespace, which ignores a SIGKILL from inside it: a child dies,
    # and the run passes its 137 on.
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
    (bin_dir / "uv").write_text("#!/bin/sh\nkill -9 0\n", encoding="utf-8")
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


def test_the_pull_request_run_keeps_its_readings_when_it_fails() -> None:
    [upload] = [
        s for s in load(PR)["jobs"]["mutate"]["steps"]
        if s.get("with", {}).get("name") == "resources"
    ]  # fmt: skip
    assert upload["if"] == "${{ !cancelled() }}"
    assert upload["with"]["path"] == "out/resources-pr.log"


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
