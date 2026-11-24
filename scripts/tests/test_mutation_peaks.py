"""Memory peaks that survive the run being killed (#371, mutation-peaks design D1, D2).

In CI the workflows name the peaks file (PEAKS) in out/, which the job uploads, and the step's exit
trap, outside the contained run, prints the summary: an OOM kill of the run took a summary printed
by the run itself down with it (dry run 44673717060).
"""

import json
from pathlib import Path

import pytest
from test_mutation_run import SETTINGS, Recorder

import mutation_report as mr
import mutation_run as run

pytestmark = pytest.mark.mutation


class PeakingMutmut(Recorder):
    """mutmut, as far as the peaks: its process records into the file the plugin is handed."""

    def __call__(self, command: list[str], cwd: Path, timeout: float, **_: object) -> int:
        super().__call__(command, cwd, timeout)
        config = json.loads((cwd / "_mutation_children_plugin.json").read_text(encoding="utf-8"))
        with Path(config["peaks"]).open("a", encoding="utf-8") as peaks:
            peaks.write("mutmut 1048576 524288\n")
        return 0


def test_with_peaks_named_the_run_records_into_that_file_and_leaves_the_summary_to_the_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The run marks where each unit starts and leaves the file for the upload and the trap."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    peaks = tmp_path / "out" / "peaks-infrastructure.log"
    peaks.parent.mkdir()
    peaks.write_text("unit earlier\nmutmut 1 1\n", encoding="utf-8")
    monkeypatch.setenv("PEAKS", str(peaks))
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    monkeypatch.setattr(mr, "from_mutmut", lambda *a, **k: {})
    unit = SETTINGS.repositories["infrastructure"].units[0]
    run.run_mutmut(tmp_path, unit, [], 1e12, PeakingMutmut(), children=2, memory_mb=None)
    assert peaks.read_text(encoding="utf-8") == (
        "unit earlier\nmutmut 1 1\nunit scripts\nmutmut 1048576 524288\n"
    )
    assert "memory:" not in capsys.readouterr().out
    assert not (tmp_path / "_mutation_children_peaks.log").exists()


PEAKS = """\
mutmut 1048576 524288
unit troupe
mutmut 2097152 1048576
m.a__mutmut_1 3145728 1048576
unit troupe-vcs-git
mutmut 1048576 524288
"""


def test_the_peaks_command_summarises_each_unit(capsys: pytest.CaptureFixture[str]) -> None:
    """What the step's exit trap runs: lines before any unit (a run killed before its first) go
    under `?`."""
    assert run.peaks_summary(PEAKS) == [
        "memory: ? mutmut VmPeak=1024 MB VmHWM=512 MB",
        "memory: ? 1 processes recorded",
        "memory: troupe mutmut VmPeak=2048 MB VmHWM=1024 MB",
        "memory: troupe mutant m.a__mutmut_1 VmPeak=3072 MB VmHWM=1024 MB",
        "memory: troupe 2 processes recorded",
        "memory: troupe-vcs-git mutmut VmPeak=1024 MB VmHWM=512 MB",
        "memory: troupe-vcs-git 1 processes recorded",
    ]


def test_a_unit_that_recorded_nothing_says_so_rather_than_vanishing() -> None:
    """A run killed early in a unit leaves its marker with no lines after it: the summary names
    that unit, which also says where the kill happened (#372's review)."""
    assert run.peaks_summary("unit troupe\nmutmut 1048576 524288\nunit troupe-vcs-git\n") == [
        "memory: troupe mutmut VmPeak=1024 MB VmHWM=512 MB",
        "memory: troupe 1 processes recorded",
        "memory: troupe-vcs-git no peaks recorded",
    ]


def test_the_peaks_command_prints_and_never_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    peaks = tmp_path / "peaks.log"
    peaks.write_text("unit troupe\nmutmut 1048576 524288\n", encoding="utf-8")
    assert run.main(["peaks", str(peaks)]) == 0
    assert capsys.readouterr().out == (
        "memory: troupe mutmut VmPeak=1024 MB VmHWM=512 MB\nmemory: troupe 1 processes recorded\n"
    )
    assert run.main(["peaks", str(tmp_path / "missing.log")]) == 0
    assert capsys.readouterr().out == "memory: no peaks recorded\n"
    peaks.write_text("", encoding="utf-8")
    assert run.main(["peaks", str(peaks)]) == 0
    assert capsys.readouterr().out == "memory: no peaks recorded\n"
