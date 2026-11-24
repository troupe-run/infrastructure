"""A unit whose selected tests reach none of its code is judged, not a failed run (#399,
mutation-unreached-unit design D1-D4). mutmut itself is faked, as in test_mutation_run.py."""

import json
import sys
from pathlib import Path

import pytest
from test_mutation_run import SETTINGS_THREE, Recorder, fake_show, scratch_checkout

import mutation_issues as mi
import mutation_run as run
import mutation_settings as ms
import mutation_state as st

pytestmark = pytest.mark.mutation

STOP = (
    "Stopping early, because we could not find any test case for any mutant. It seems that the "
    "selected tests do not cover any code that we mutated."
)
"""mutmut 3.8.1's own words for the stop, as #398's trial printed them."""


@pytest.fixture(autouse=True)
def three_repositories(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run, "SETTINGS", SETTINGS_THREE)


# D1: the output's tail


def test_a_kept_tail_holds_the_last_lines_and_every_line_still_reaches_the_log(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    tail: list[str] = []
    command = [sys.executable, "-c", "import sys\nfor n in range(60): print(n)\nsys.exit(4)"]
    assert run.run_command(command, tmp_path, 30, tail=tail) == 4
    assert tail == [str(n) for n in range(10, 60)]
    assert capfd.readouterr().out.split() == [str(n) for n in range(60)]


def test_without_a_tail_the_output_goes_straight_to_the_log(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    assert run.run_command([sys.executable, "-c", "print('x')"], tmp_path, 30) == 0
    assert capfd.readouterr().out == "x\n"


def test_a_command_that_runs_out_of_time_with_a_tail_is_minus_one(tmp_path: Path) -> None:
    tail: list[str] = []
    command = [sys.executable, "-c", "import time\nprint('a', flush=True)\ntime.sleep(30)"]
    assert run.run_command(command, tmp_path, 0.5, tail=tail) == -1


# D2, D3: recognising the stop, and counting every mutant as reached by no test


def package(root: Path, name: str) -> ms.Unit:
    (root / "packages" / name / "src").mkdir(parents=True)
    (root / "packages" / name / "src" / f"{name}.py").write_text(
        "def f(a):\n    return a + 1\n", encoding="utf-8"
    )
    return ms.Unit(name, f"packages/{name}/src", f"packages/{name}/tests", "unit")


class Stopping(Recorder):
    """mutmut for unit a: generated, then `code` with `said` on its output. Unit b runs as usual,
    one mutant killed."""

    def __init__(self, code: int, said: str) -> None:
        super().__init__()
        self.stop_code, self.said = code, said

    def __call__(
        self,
        command: list[str],
        cwd: Path,
        timeout: float,
        *,
        tail: list[str] | None = None,
        **_: object,
    ) -> int:
        super().__call__(command, cwd, timeout)
        name = cwd.name
        meta = cwd / "mutants" / "src" / f"{name}.py.meta"
        meta.parent.mkdir(parents=True, exist_ok=True)
        if name == "a":
            codes: dict[str, int | None] = {"a.x_f__mutmut_1": None, "a.x_f__mutmut_2": None}
            meta.write_text(json.dumps({"exit_code_by_key": codes}), encoding="utf-8")
            if tail is not None:
                tail += ["    done", f"\r⠋ Running stats\r{self.said}", "You can set debug=true"]
            return self.stop_code
        meta.write_text(json.dumps({"exit_code_by_key": {"b.x_f__mutmut_1": 1}}), encoding="utf-8")
        return 0


def two_units(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, run_: Stopping) -> object:
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    repository = ms.Repository(
        "troupe", "mutmut", units=(package(tmp_path, "a"), package(tmp_path, "b"))
    )
    return run.collect(
        repository, tmp_path, ms.load_settings(SETTINGS_THREE.read_text()), None, run_
    )


def test_the_stop_counts_every_mutant_as_reached_by_no_test_and_the_run_goes_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    modules = two_units(tmp_path, monkeypatch, Stopping(1, STOP))
    assert isinstance(modules, dict)
    a, b = modules["a"], modules["b"]
    assert (a.finished, a.no_tests, a.killed, a.survived, a.counted) == (True, 2, 0, 0, 2)
    assert (b.finished, b.killed) == (True, 1)
    assert (
        "mutation_run: a: its selected tests reach none of its code; every mutant counted as "
        "reached by no test" in capsys.readouterr().out
    )


@pytest.mark.parametrize(
    ("code", "said"),
    [
        (1, "failed to collect stats. runner returned 1"),  # its tests failed in the copy
        (1, STOP.replace("any test case", "a test case")),  # not mutmut's exact words
        (2, STOP),  # the words with another exit code
    ],
)
def test_any_other_failure_still_fails_the_run_naming_the_unit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int, said: str
) -> None:
    with pytest.raises(run.RunError, match=rf"mutmut failed for a \(exit {code}\)"):
        two_units(tmp_path, monkeypatch, Stopping(code, said))


def test_the_words_on_a_run_that_succeeded_change_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    modules = two_units(tmp_path, monkeypatch, Stopping(0, STOP))
    assert isinstance(modules, dict)
    assert (modules["a"].finished, modules["a"].no_tests) == (False, 0)


# D4: named in the state record and the summary


class StoppingScripts(Recorder):
    """mutmut stopping for infrastructure's one unit, scripts, whose calc.py has two mutants."""

    def __call__(
        self,
        command: list[str],
        cwd: Path,
        timeout: float,
        *,
        tail: list[str] | None = None,
        **_: object,
    ) -> int:
        super().__call__(command, cwd, timeout)
        meta = cwd / "mutants" / "src" / "calc.py.meta"
        meta.parent.mkdir(parents=True, exist_ok=True)
        codes = {"calc.x_add__mutmut_1": None, "calc.x_add__mutmut_2": None}
        meta.write_text(json.dumps({"exit_code_by_key": codes}), encoding="utf-8")
        if tail is not None:
            tail.append(STOP)
        return 1


def test_the_scheduled_runs_record_and_summary_name_the_unit_and_why(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _ = scratch_checkout(tmp_path)
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    fake_show(monkeypatch)
    monkeypatch.setenv("MUTATION_STATE", str(tmp_path / "state"))
    monkeypatch.setenv("MUTATION_RUN_ID", "45")
    out = tmp_path / "out" / "report-infrastructure.json"
    assert run.main(["infrastructure", str(repo), str(out)], StoppingScripts()) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    calc = report["modules"]["calc"]
    assert (calc["no_tests"], calc["finished"]) == (2, True)
    record = json.loads((out.parent / "state-infrastructure.json").read_text(encoding="utf-8"))
    assert record["units"]["scripts"]["unreached"] is True
    lines = mi.state_section(record)
    assert (
        "  - its selected tests reach none of its code: every mutant counted as reached by no test"
        in lines
    )


def test_a_unit_its_tests_reach_isnt_marked() -> None:
    assert st.UnitState("troupe").record()["unreached"] is False
