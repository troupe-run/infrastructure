"""scripts/check.py stops at the first failing gate and returns its exit code."""

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
