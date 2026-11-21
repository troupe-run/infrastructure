"""A survivor whose `git blame` fails doesn't cost the run its report (#377, mutation-blame D2)."""

import json
from pathlib import Path

import pytest
from test_mutation_run import SETTINGS_THREE, FakeMutmut, fake_show, scratch_checkout

import mutation_report as mr
import mutation_run as run

pytestmark = pytest.mark.mutation


@pytest.fixture(autouse=True)
def three_repositories(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() reads the settings from run.SETTINGS: give it the fixture's three repositories."""
    monkeypatch.setattr(run, "SETTINGS", SETTINGS_THREE)


def test_a_run_whose_blame_fails_logs_the_survivor_and_writes_its_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Dry run 44717818525's blame of a line past the end of a file exited 2 after four hours of
    mutmut, and wrote nothing."""
    repo, commit = scratch_checkout(tmp_path)
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    fake_show(monkeypatch)

    def no_blame(root: Path, at: str, path: str, line: int) -> str:
        raise mr.ReportError(f"git blame of {path}:{line} at {at[:12]} failed: fatal: too short")

    monkeypatch.setattr(mr, "last_changed", no_blame)
    out = tmp_path / "out" / "report.json"
    only = json.dumps({"scripts": ["calc.*"]})
    argv = ["infrastructure", str(repo), str(out), "--previous", commit, "--only", only]
    assert run.main(argv, FakeMutmut()) == 0
    report = mr.load_report(out.read_text(encoding="utf-8"), "infrastructure")
    [survivor] = report.modules["calc"].survivors
    assert (survivor.commit, survivor.new) == (None, False)
    assert (
        f"mutation_run: scripts/calc.py:2 unattributed: git blame of scripts/calc.py:2 at "
        f"{commit[:12]} failed: fatal: too short\n" in capsys.readouterr().out
    )
