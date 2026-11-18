"""scripts/check.py stops at the first failing gate and returns its exit code."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import check


def step(label: str, code: int, marker: Path) -> tuple[str, list[str]]:
    """A gate that records it ran (by touching `marker`) and exits with `code`."""
    script = f"import pathlib, sys; pathlib.Path({str(marker)!r}).touch(); sys.exit({code})"
    return (label, [sys.executable, "-c", script])


def test_all_gates_passing_returns_zero(tmp_path: Path) -> None:
    gates = [step("a", 0, tmp_path / "a"), step("b", 0, tmp_path / "b")]
    assert check.run_gates(gates, tmp_path) == 0
    assert (tmp_path / "a").exists()
    assert (tmp_path / "b").exists()


def test_a_failing_gate_returns_its_code_and_stops_the_rest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gates = [
        step("a", 0, tmp_path / "a"),
        step("b", 3, tmp_path / "b"),
        step("c", 0, tmp_path / "c"),
    ]
    assert check.run_gates(gates, tmp_path) == 3
    assert (tmp_path / "b").exists()
    assert not (tmp_path / "c").exists()
    assert "check: b failed (exit 3)" in capsys.readouterr().out


# --scope (commit-check-paths task 4.5, design D8)

DECLARED = """\
version = 1

[skip]
paths = ["openspec/**"]

[scopes.docs]
paths = ["docs/**"]

[scopes.api]
paths = ["api/**"]
"""


def test_an_undeclared_scope_is_refused_naming_it_and_the_declaration() -> None:
    import guard

    with pytest.raises(SystemExit) as refused:
        check.requested_scopes(["docs", "nope"], guard.check_paths(DECLARED))
    assert "`nope`" in str(refused.value.code)
    assert "scripts/check-paths.toml" in str(refused.value.code)


def test_without_a_declaration_every_scope_is_refused() -> None:
    with pytest.raises(SystemExit) as refused:
        check.requested_scopes(["docs"], None)
    assert "`docs`" in str(refused.value.code)


def test_declared_scopes_are_returned_sorted_and_once() -> None:
    import guard

    assert check.requested_scopes(["docs", "api", "docs"], guard.check_paths(DECLARED)) == (
        "api",
        "docs",
    )


def test_an_undeclared_scope_stops_the_check_before_any_gate_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ran: list[object] = []

    def run_gates(steps: object, cwd: Path) -> int:
        ran.append(steps)
        return 0

    monkeypatch.setattr(check, "activate_git_hooks", lambda root: None)
    monkeypatch.setattr(check, "run_gates", run_gates)
    with pytest.raises(SystemExit):
        check.main(["--scope", "nope"])
    assert ran == []


def pytest_command(scopes: tuple[str, ...]) -> list[str]:
    return dict(check.gates(scopes))["tests"]


def test_a_scoped_check_keeps_every_gate_and_narrows_only_pytest() -> None:
    full = check.gates()
    scoped = check.gates(("docs",))
    assert [label for label, _ in scoped] == [label for label, _ in full]
    assert [command for label, command in scoped if label != "tests"] == [
        command for label, command in full if label != "tests"
    ]
    assert pytest_command(("docs",))[-2:] == ["-m", "docs"]


def test_two_scopes_select_tests_tagged_with_either() -> None:
    assert pytest_command(("api", "docs"))[-2:] == ["-m", "api or docs"]


def test_the_full_check_gives_pytest_no_marker_expression() -> None:
    assert "-m" not in pytest_command(())


# Parallel test workers (check-time design D1)


def test_the_full_check_runs_its_tests_in_the_named_number_of_workers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(os, "cpu_count", lambda: check.TEST_WORKERS + 4)
    command = pytest_command(())
    assert command[1:3] == ["-n", str(check.TEST_WORKERS)]


@pytest.mark.parametrize(("cpus", "workers"), [(2, "2"), (1, "1"), (None, "1")])
def test_fewer_cpus_than_the_named_count_run_one_worker_per_cpu(
    monkeypatch: pytest.MonkeyPatch, cpus: int | None, workers: str
) -> None:
    monkeypatch.setattr(os, "cpu_count", lambda: cpus)
    assert pytest_command(())[1:3] == ["-n", workers]


def test_a_scoped_check_runs_its_tagged_tests_in_workers_too() -> None:
    command = pytest_command(("dns",))
    assert "-n" in command
    assert command[-2:] == ["-m", "dns"]


def test_xdist_keeps_pytests_nothing_selected_exit_code(tmp_path: Path) -> None:
    """A scope no test is tagged with exits 5 under workers too, which run_gates passes."""
    (tmp_path / "pytest.ini").write_text("[pytest]\nmarkers = nothing_has_this\n")
    (tmp_path / "test_one.py").write_text("def test_one():\n    pass\n")
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "xdist", "-n", "2", "-m", "nothing_has_this"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == check.NO_TESTS_RAN, done.stdout + done.stderr


# A scope no test is tagged with (commit-check-paths task 4.7, design D8)


def test_a_scoped_test_run_that_selects_nothing_passes_and_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gates = [step("tests", 5, tmp_path / "tests"), step("after", 0, tmp_path / "after")]
    assert check.run_gates(gates, tmp_path, scopes=("api", "docs")) == 0
    assert (tmp_path / "after").exists()
    assert "no test is tagged `api` or `docs`, so there was nothing to test" in (
        capsys.readouterr().out
    )


def test_a_full_test_run_that_collects_nothing_still_fails(tmp_path: Path) -> None:
    assert check.run_gates([step("tests", 5, tmp_path / "tests")], tmp_path) == 5


def test_exit_5_from_another_gate_still_fails_a_scoped_run(tmp_path: Path) -> None:
    gates = [step("mypy --strict", 5, tmp_path / "mypy")]
    assert check.run_gates(gates, tmp_path, scopes=("docs",)) == 5


# The quality gates (spec: quality-gates; quality-gates design D5)


def labels(steps: list[tuple[str, list[str]]]) -> list[str]:
    return [label for label, _ in steps]


def test_a_local_check_runs_complexity_but_never_coverage_or_audit() -> None:
    steps = check.gates()
    assert "complexity" in labels(steps)
    assert "coverage" not in labels(steps)
    assert "audit" not in labels(steps)
    assert not any(arg.startswith("--cov") for arg in dict(steps)["tests"])


def test_complexity_runs_before_the_tests_and_takes_the_base() -> None:
    steps = check.gates(base="abc123")
    assert labels(steps).index("complexity") < labels(steps).index("tests")
    assert dict(steps)["complexity"][-3:] == ["complexity", "--base", "abc123"]


def test_the_leg_measures_coverage_from_the_full_test_run_and_audits() -> None:
    steps = check.gates(base="abc123", leg=True)
    report = str(check.coverage_report())
    assert f"--cov-report=json:{report}" in dict(steps)["tests"]
    assert dict(steps)["coverage"][-3:] == ["coverage", "--coveragepy", report]
    assert dict(steps)["audit"][-3:] == ["audit", "--base", "abc123"]
    assert labels(steps).index("tests") < labels(steps).index("coverage")


def test_a_scoped_check_on_the_leg_says_coverage_wasnt_measured() -> None:
    steps = check.gates(("dns",), leg=True)
    assert not any(arg.startswith("--cov") for arg in dict(steps)["tests"])
    assert "coverage not measured: the tests were scoped" in dict(steps)["coverage"][-1]
    assert "audit" in labels(steps)


def test_the_leg_is_off_unless_its_variable_is_set() -> None:
    assert check.on_leg({}) is False
    assert check.on_leg({"GITHUB_ACTIONS": "true"}) is False
    assert check.on_leg({check.LEG: "true", "GITHUB_ACTIONS": "true"}) is True


def test_the_leg_variable_outside_github_actions_stops_the_check() -> None:
    with pytest.raises(SystemExit) as refused:
        check.on_leg({check.LEG: "true"})
    assert "isn't GitHub Actions" in str(refused.value.code)
    assert f"unset {check.LEG}" in str(refused.value.code)


def test_a_malformed_leg_value_stops_the_check() -> None:
    with pytest.raises(SystemExit) as refused:
        check.on_leg({check.LEG: "yes", "GITHUB_ACTIONS": "true"})
    assert "QUALITY_GATES_LEG='yes' isn't valid" in str(refused.value.code)


# tflint (lint-mutation design D1, D2)


def fake_path(tmp_path: Path, *names: str) -> str:
    """A PATH for tflint's lookup holding only executables with these names."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    for name in names:
        exe = tmp_path / name
        exe.write_text("#!/bin/sh\nexit 0\n")
        exe.chmod(0o755)
    return str(tmp_path)


def test_tflint_runs_after_tofu_validate_over_tofu_with_the_root_rules(tmp_path: Path) -> None:
    env = {"PATH": fake_path(tmp_path, "tflint")}
    steps = check.gates((), env=env)
    labels = [label for label, _ in steps]
    assert labels.index("tflint") == labels.index("tofu validate") + 1
    command = dict(steps)["tflint"]
    assert command[0] == str(tmp_path / "tflint")
    assert command[1:] == ["--chdir=tofu", "--recursive", f"--config={check.ROOT / '.tflint.hcl'}"]


def test_a_scoped_check_still_runs_tflint(tmp_path: Path) -> None:
    env = {"PATH": fake_path(tmp_path, "tflint")}
    assert "tflint" in dict(check.gates(("dns",), env=env))


def test_a_missing_tflint_in_github_actions_fails_naming_it(tmp_path: Path) -> None:
    env = {"PATH": fake_path(tmp_path), "GITHUB_ACTIONS": "true"}
    with pytest.raises(SystemExit) as stopped:
        check.gates((), env=env)
    assert "tflint" in str(stopped.value)
    assert "PATH" in str(stopped.value)


def test_a_missing_tflint_locally_skips_only_that_gate_and_says_how_to_install_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with_it = check.gates((), env={"PATH": fake_path(tmp_path / "a", "tflint")})
    without = check.gates((), env={"PATH": fake_path(tmp_path / "b"), "GITHUB_ACTIONS": "false"})
    assert [label for label, _ in without] == [label for label, _ in with_it if label != "tflint"]
    out = capsys.readouterr().out
    assert "tflint gate is skipped" in out
    assert f"go install github.com/terraform-linters/tflint@{check.tflint_version()}" in out


def test_the_tflint_version_is_read_from_the_rules_file() -> None:
    assert check.tflint_version().startswith("v")
    assert check.tflint_version() in (check.ROOT / ".tflint.hcl").read_text()


def test_an_installed_tflint_that_fails_fails_the_check(tmp_path: Path) -> None:
    failing = tmp_path / "tflint"
    finding = "tofu/x.tf:1:1: Warning: unused variable (terraform_unused_declarations)"
    failing.write_text(f"#!/bin/sh\necho '{finding}'\nexit 2\n")
    failing.chmod(0o755)
    gate = dict(check.gates((), env={"PATH": str(tmp_path), "GITHUB_ACTIONS": "false"}))["tflint"]
    assert check.run_gates([("tflint", gate)], tmp_path) == 2


def test_a_missing_tflint_in_github_actions_says_how_ci_installs_it(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as stopped:
        check.gates((), env={"PATH": fake_path(tmp_path), "GITHUB_ACTIONS": "true"})
    assert str(stopped.value) == (
        "check: tflint is not on the PATH. Fix: install it in the workflow "
        "(terraform-linters/setup-tflint, the version in .tflint.hcl)."
    )


def test_the_local_skip_notice_word_for_word(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    check.gates((), env={"PATH": fake_path(tmp_path)})
    assert capsys.readouterr().out == (
        "check: tflint isn't installed, so the tflint gate is skipped here; CI runs it. "
        "To run it locally: go install "
        f"github.com/terraform-linters/tflint@{check.tflint_version()}\n"
    )


def test_rules_without_a_version_line_stop_the_check_saying_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rules = tmp_path / ".tflint.hcl"
    rules.write_text('plugin "terraform" {}\n', encoding="utf-8")
    monkeypatch.setattr(check, "TFLINT_RULES", rules)
    with pytest.raises(SystemExit) as stopped:
        check.tflint_version()
    assert (
        str(stopped.value) == "check: .tflint.hcl has no `# tflint v<version>` line. Fix: add it."
    )


# Only tflint may be missing locally (owner, 2026-11-18): every other tool stays an error.


def test_a_missing_tofu_stops_the_check_even_locally(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name, path=None: None)
    with pytest.raises(SystemExit) as stopped:
        check.gates((), env={"PATH": "", "GITHUB_ACTIONS": "false"})
    assert str(stopped.value) == (
        "check: tofu is not installed in the PATH. Fix: install OpenTofu (brew install opentofu)."
    )


def test_a_missing_python_tool_stops_the_check_saying_to_sync(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as stopped:
        check.tool("ruff", path=str(tmp_path))
    assert str(stopped.value) == f"check: ruff is not installed in {check.BIN}. Fix: run `uv sync`."
