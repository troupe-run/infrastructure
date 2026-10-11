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
