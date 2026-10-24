"""Rule: openspec-strict, the guard check's strict OpenSpec validation (#123).

The fixtures under fixtures/openspec-strict/ were captured from OpenSpec 1.14.3 on 2026-10-24 (task
1.1): each holds the OpenSpec tree it was run on, and `openspec validate --all --strict --json
--no-interactive`'s output, exit status and error output there, with the root path in the report
replaced by /probe/<name>. In `fail`, the main spec `steps` has a third requirement over the length
limit, and the active change `add-thing` adds a requirement with no scenario.
"""

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import SCRIPTS, Repo, clean_env, git

import guard

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "openspec-strict"
FAIL = FIXTURES / "fail"
PASS = FIXTURES / "pass"


def captured(name: str) -> guard.OpenSpecRun:
    base = FIXTURES / name
    return guard.OpenSpecRun(
        status=int((base / "status").read_text(encoding="utf-8")),
        stdout=(base / "report.json").read_text(encoding="utf-8"),
        stderr=(base / "stderr").read_text(encoding="utf-8"),
        version="1.14.3",
    )


def running(result: guard.OpenSpecRun) -> Callable[[Path], guard.OpenSpecRun]:
    return lambda root: result


def never(root: Path) -> guard.OpenSpecRun:
    raise AssertionError("OpenSpec was run")


def scope(
    *paths: str, branch: str = "add-thing", pull_request: bool = True, exists: bool = True
) -> guard.OpenSpecScope:
    return guard.openspec_scope(paths, branch, pull_request, lambda path: exists)


EVERYTHING = guard.OpenSpecScope(everything=True)


# The scope (design D3)


@pytest.mark.parametrize(
    ("paths", "branch", "pull_request", "exists", "expected"),
    [
        pytest.param(["README.md"], "x", True, True, guard.OpenSpecScope(), id="no-spec"),
        pytest.param(
            ["openspec/specs/steps/spec.md"],
            "x",
            True,
            True,
            guard.OpenSpecScope(specs=frozenset({"steps"})),
            id="a-spec",
        ),
        pytest.param(
            ["openspec/changes/x/proposal.md", "openspec/changes/x/specs/steps/spec.md"],
            "x",
            False,
            True,
            guard.OpenSpecScope(changes=frozenset({"x"})),
            id="an-active-change-on-a-branch-push",
        ),
        pytest.param(
            ["openspec/changes/x/tasks.md"], "x", True, False, guard.OpenSpecScope(), id="deleted"
        ),
        pytest.param(
            ["openspec/changes/archive/2026-10-24-x/tasks.md"],
            "x",
            True,
            True,
            guard.OpenSpecScope(),
            id="archived",
        ),
        pytest.param(["openspec/config.yaml"], "x", True, True, guard.OpenSpecScope(), id="config"),
        pytest.param(["scripts/guard.py"], "x", True, True, EVERYTHING, id="the-guard"),
        pytest.param([".github/workflows/guard.yml"], "x", True, True, EVERYTHING, id="the-pin"),
        pytest.param(["README.md"], "main", False, True, EVERYTHING, id="a-push-to-main"),
        pytest.param([], "main", False, True, EVERYTHING, id="an-empty-push-to-main"),
        pytest.param(["README.md"], "main", True, True, guard.OpenSpecScope(), id="a-pr-from-main"),
    ],
)
def test_the_scope_is_what_the_range_touches(
    paths: list[str],
    branch: str,
    pull_request: bool,
    exists: bool,
    expected: guard.OpenSpecScope,
) -> None:
    assert guard.openspec_scope(paths, branch, pull_request, lambda path: exists) == expected


def test_archiving_puts_the_specs_it_syncs_in_scope_but_not_the_moved_change() -> None:
    moved = "openspec/changes/x"
    paths = [
        f"{moved}/tasks.md",
        "openspec/changes/archive/2026-10-24-x/tasks.md",
        "openspec/specs/steps/spec.md",
    ]
    assert guard.openspec_scope(paths, "x", True, lambda path: path != moved) == (
        guard.OpenSpecScope(specs=frozenset({"steps"}))
    )


# Reading OpenSpec's report (design D2)


def test_the_captured_reports_are_read() -> None:
    failing = guard.read_openspec_report(captured("fail"))
    assert [(i.kind, i.name, i.valid) for i in failing] == [
        ("change", "add-thing", False),
        ("spec", "steps", False),
    ]
    assert failing[1].issues[0].path == "requirements[2]"
    assert [(i.kind, i.name, i.valid) for i in guard.read_openspec_report(captured("pass"))] == [
        ("spec", "steps", True)
    ]


@pytest.mark.parametrize(
    ("stdout", "status", "said"),
    [
        pytest.param("Error: something broke\n", 1, "isn't JSON", id="not-json"),
        pytest.param('{"version": "1.0"}', 0, "no items list", id="no-items"),
        pytest.param(
            '{"items": [{"id": "a", "type": "spec", "issues": []}]}',
            0,
            "boolean valid",
            id="no-valid",
        ),
        pytest.param(
            '{"items": [{"id": "a", "type": "module", "valid": true, "issues": []}]}',
            0,
            "'spec' or 'change'",
            id="unknown-type",
        ),
        pytest.param(
            '{"items": [{"id": "a", "type": "spec", "valid": false, "issues": [{}]}]}',
            1,
            "no string level",
            id="bad-issue",
        ),
        pytest.param(
            captured("pass").stdout,
            1,
            "exited 1 but reported no failing item",
            id="failure-with-nothing-failing",
        ),
        pytest.param(
            captured("fail").stdout,
            0,
            "exited 0 but reported a failing item",
            id="success-with-a-failure",
        ),
    ],
)
def test_a_report_that_can_t_be_read_fails_naming_the_exit_status_and_error_output(
    stdout: str, status: int, said: str
) -> None:
    run = guard.OpenSpecRun(status, stdout, "something on stderr\n", "1.14.3")
    with pytest.raises(guard.UnreadableOpenSpecReportError, match=said):
        guard.read_openspec_report(run)
    decision = guard.openspec_strict(FAIL, EVERYTHING, running(run))
    assert decision.rule == "openspec-strict"
    assert said in decision.problem
    assert f"It exited {status}" in decision.problem
    assert "something on stderr" in decision.problem
    assert "Re-run the check" in decision.fix


# Naming the requirement (design D4)


def test_a_spec_s_requirement_is_named_by_its_heading_counted_from_zero() -> None:
    assert guard.requirement_name(FAIL, "steps", 0) == "Runs start"
    assert guard.requirement_name(FAIL, "steps", 2) == "Steps are reported"
    assert guard.requirement_name(FAIL, "steps", 3) is None
    assert guard.requirement_name(FAIL, "missing", 0) is None


def test_the_refusal_names_the_requirement_and_the_change_s_delta_file() -> None:
    decision = guard.openspec_strict(FAIL, EVERYTHING, running(captured("fail")))
    assert decision.rule == "openspec-strict"
    assert (
        'spec steps: requirement "Steps are reported" (requirements[2]): [warning] Requirement '
        "text is very long (>500 characters)." in decision.problem
    )
    assert (
        "change add-thing: openspec/changes/add-thing/specs/steps/spec.md: [error] ADDED "
        '"Runs pause" must include at least one scenario' in decision.problem
    )


def test_a_requirement_whose_heading_can_t_be_found_is_named_by_its_position(
    tmp_path: Path,
) -> None:
    shutil.copytree(FAIL / "openspec", tmp_path / "openspec")
    spec = tmp_path / "openspec" / "specs" / "steps" / "spec.md"
    spec.write_text(spec.read_text(encoding="utf-8").split("### Requirement: Runs stop")[0])
    decision = guard.openspec_strict(tmp_path, EVERYTHING, running(captured("fail")))
    assert "spec steps: requirements[2]: [warning] Requirement text" in decision.problem
    assert "Steps are reported" not in decision.problem


# The refusal (design D5)


def test_one_failing_spec_s_fix_reproduces_it_with_the_version_that_ran() -> None:
    decision = guard.openspec_strict(
        FAIL, guard.OpenSpecScope(specs=frozenset({"steps"})), running(captured("fail"))
    )
    assert decision.problem.startswith("1 item(s) fail OpenSpec's strict validation: spec steps:")
    assert "add-thing" not in decision.problem
    assert decision.fix.startswith(
        "Run `openspec validate steps --type spec --strict` with OpenSpec 1.14.3"
    )
    assert "split it" in decision.fix


def test_one_failing_change_s_fix_names_the_change() -> None:
    decision = guard.openspec_strict(
        FAIL, guard.OpenSpecScope(changes=frozenset({"add-thing"})), running(captured("fail"))
    )
    assert decision.problem.startswith("1 item(s) fail OpenSpec's strict validation: change ")
    assert "Run `openspec validate add-thing --type change --strict`" in decision.fix


def test_several_failing_items_are_listed_and_the_fix_validates_everything() -> None:
    decision = guard.openspec_strict(FAIL, EVERYTHING, running(captured("fail")))
    assert decision.problem.startswith("2 item(s) fail")
    assert "Run `openspec validate --all --strict` with OpenSpec 1.14.3" in decision.fix


def test_a_failing_spec_outside_the_scope_doesn_t_fail_the_check() -> None:
    touched = guard.OpenSpecScope(specs=frozenset({"runs"}))
    assert guard.openspec_strict(FAIL, touched, running(captured("fail"))) == guard.ALLOW


def test_everything_passing_passes() -> None:
    assert guard.openspec_strict(PASS, EVERYTHING, running(captured("pass"))) == guard.ALLOW


# Running OpenSpec (design D1, D2)


def test_an_empty_scope_doesn_t_run_openspec() -> None:
    assert guard.openspec_strict(FAIL, guard.OpenSpecScope(), never) == guard.ALLOW


def test_a_repository_without_openspec_doesn_t_run_it(tmp_path: Path) -> None:
    assert guard.openspec_strict(tmp_path, EVERYTHING, never) == guard.ALLOW


def test_a_missing_cli_fails_naming_where_the_version_is_pinned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    decision = guard.openspec_strict(FAIL, EVERYTHING)
    assert decision.rule == "openspec-strict"
    assert "wasn't found on PATH" in decision.problem
    assert ".github/workflows/guard.yml" in decision.fix
    assert "OPENSPEC_VERSION" in decision.fix


STUB = """\
import json, os, sys, time
from pathlib import Path
config = json.loads(Path(__file__).with_name("stub.json").read_text(encoding="utf-8"))
log = Path(__file__).with_name("calls.jsonl")
with log.open("a", encoding="utf-8") as calls:
    calls.write(json.dumps({"args": sys.argv[1:], "cwd": os.getcwd(),
        "telemetry": os.environ.get("OPENSPEC_TELEMETRY"),
        "dnt": os.environ.get("DO_NOT_TRACK")}) + "\\n")
if sys.argv[1:] == ["--version"]:
    print("1.14.3")
    sys.exit(0)
time.sleep(config.get("sleep", 0))
sys.stdout.write(config["stdout"])
sys.stderr.write(config.get("stderr", ""))
sys.exit(config["status"])
"""


def stub_openspec(directory: Path, run: guard.OpenSpecRun, sleep: float = 0) -> Path:
    """An `openspec` on PATH that prints a captured run: a Python script behind a POSIX shell
    wrapper, or behind openspec.cmd on Windows, which is how npm installs it there."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "stub.py").write_text(STUB, encoding="utf-8")
    config = {"stdout": run.stdout, "stderr": run.stderr, "status": run.status, "sleep": sleep}
    (directory / "stub.json").write_text(json.dumps(config), encoding="utf-8")
    if os.name == "nt":
        (directory / "openspec.cmd").write_text(
            f'@"{sys.executable}" "{directory / "stub.py"}" %*\r\n', encoding="utf-8"
        )
    else:
        wrapper = directory / "openspec"
        wrapper.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{directory / "stub.py"}" "$@"\n',
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
    return directory


def stub_calls(directory: Path) -> list[dict[str, object]]:
    lines = (directory / "calls.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_the_cli_runs_strict_json_validation_at_the_root_with_telemetry_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = stub_openspec(tmp_path / "bin", captured("pass"))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    assert guard.openspec_strict(PASS, EVERYTHING) == guard.ALLOW
    calls = stub_calls(bin_dir)
    assert [call["args"] for call in calls] == [
        ["--version"],
        ["validate", "--all", "--strict", "--json", "--no-interactive"],
    ]
    assert all(Path(str(call["cwd"])).resolve() == PASS.resolve() for call in calls)
    assert all(call["telemetry"] == "0" and call["dnt"] == "1" for call in calls)


def test_a_validation_that_outlives_the_timeout_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = stub_openspec(tmp_path / "bin", captured("pass"), sleep=30)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(guard, "OPENSPEC_TIMEOUT_SECONDS", 2.0)
    decision = guard.openspec_strict(PASS, EVERYTHING)
    assert decision.rule == "openspec-strict"
    assert "ran for more than 2 seconds" in decision.problem


# End to end: guard.py ci, as the guard check runs it


def ci_repo(make_repo: Callable[[], Repo]) -> tuple[Repo, str]:
    """A branch add-thing that adds the failing fixture's tree: its change and its main spec."""
    repo = make_repo()
    base = repo.head()
    repo.switch("add-thing")
    shutil.copytree(FAIL / "openspec", repo.path / "openspec")
    made = repo.commit("docs(openspec): propose add-thing")
    assert made.returncode == 0, made.stderr
    return repo, base


def run_ci(repo: Repo, base: str, bin_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = clean_env()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["CLAUDE_PROJECT_DIR"] = str(repo.path)
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "guard.py"),
            "ci",
            "--base",
            base,
            "--head",
            repo.head(),
            *extra,
        ],
        cwd=repo.path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_the_ci_entry_fails_a_pull_request_naming_the_requirement(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = ci_repo(make_repo)
    bin_dir = stub_openspec(tmp_path / "bin", captured("fail"))
    result = run_ci(repo, base, bin_dir, "--branch", "add-thing", "--title", "docs: add-thing")
    assert result.returncode == 1, result.stderr
    assert "guard: openspec-strict: 2 item(s) fail" in result.stderr
    assert 'requirement "Steps are reported" (requirements[2])' in result.stderr
    assert "with OpenSpec 1.14.3" in result.stderr


def test_the_ci_entry_passes_a_pull_request_that_touches_no_spec(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, _ = ci_repo(make_repo)
    base = repo.head()
    repo.write("notes.txt", "notes\n")
    assert repo.commit("docs: add notes").returncode == 0
    bin_dir = stub_openspec(tmp_path / "bin", captured("fail"))
    result = run_ci(repo, base, bin_dir, "--branch", "add-thing", "--title", "docs: add notes")
    assert result.returncode == 0, result.stderr
    assert not (bin_dir / "calls.jsonl").exists()


def test_the_ci_entry_validates_everything_on_a_push_to_main(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, _ = ci_repo(make_repo)
    git(repo.path, "switch", "-q", "main")
    git(repo.path, "merge", "-q", "--ff-only", "add-thing")
    base = repo.head()
    repo.write("notes.txt", "notes\n")
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "--no-verify", "-m", "docs: add notes")
    bin_dir = stub_openspec(tmp_path / "bin", captured("fail"))
    result = run_ci(repo, base, bin_dir, "--branch", "main")
    assert result.returncode == 1
    assert "guard: openspec-strict: 2 item(s) fail" in result.stderr
