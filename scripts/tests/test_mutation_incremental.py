"""The scheduled run resumes from mutmut's kept state (#378, mutation-incremental design D2, D3)."""

import json
from pathlib import Path
from typing import Any

import pytest
from test_mutation_run import SETTINGS_THREE, FakeMutmut, fake_show, scratch_checkout

import mutation_run as run
import mutation_settings as ms

pytestmark = pytest.mark.mutation


@pytest.fixture(autouse=True)
def three_repositories(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() reads the settings from run.SETTINGS: give it the fixture's three repositories."""
    monkeypatch.setattr(run, "SETTINGS", SETTINGS_THREE)


def weekly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, previous: dict[str, Any] | None = None
) -> tuple[int, Path, Path]:
    """A scheduled run of infrastructure's one unit, keeping state in tmp_path/state."""
    repo, _ = scratch_checkout(tmp_path)
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    fake_show(monkeypatch)
    state = tmp_path / "state"
    monkeypatch.setenv("MUTATION_STATE", str(state))
    monkeypatch.setenv("MUTATION_RUN_ID", "42")
    if previous is not None:
        record = tmp_path / "previous" / "state-infrastructure.json"
        record.parent.mkdir()
        record.write_text(json.dumps(previous), encoding="utf-8")
        monkeypatch.setenv("MUTATION_PREVIOUS_STATE", str(record))
    out = tmp_path / "out" / "report-infrastructure.json"
    return run.main(["infrastructure", str(repo), str(out)], FakeMutmut()), out, state


def test_a_first_fill_saves_the_state_and_records_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    code, out, state = weekly(tmp_path, monkeypatch)
    assert code == 0
    assert out.exists()
    assert (state / "scripts" / "src" / "calc.py.meta").exists()
    manifest = json.loads((state / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["units"]["scripts"]["saved_by"] == "42"
    record = json.loads((out.parent / "state-infrastructure.json").read_text(encoding="utf-8"))
    unit = record["units"]["scripts"]
    assert (unit["saved"], unit["lost"], unit["tested"]) == (True, False, 2)
    assert unit["discarded"] == ["no state kept yet: a first fill"]


def test_state_the_previous_run_saved_but_gone_fails_the_run_after_its_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An evicted cache must show, never pass silently: the report is still written."""
    previous = {"version": 1, "repository": "infrastructure", "units": {"scripts": {"saved": True}}}
    code, out, _ = weekly(tmp_path, monkeypatch, previous)
    assert code == 3
    assert out.exists()
    record = json.loads((out.parent / "state-infrastructure.json").read_text(encoding="utf-8"))
    assert record["units"]["scripts"]["lost"]
    assert (
        "mutation_run: scripts: the state the previous run saved is gone (the cache entry was "
        "evicted or lost): filling afresh" in capsys.readouterr().err
    )


def test_a_dispatch_naming_one_unit_runs_only_that_unit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ran: list[str] = []

    def fake(
        checkout: Path, unit: ms.Unit, names: object, *args: object, **kw: object
    ) -> dict[str, object]:
        ran.append(unit.name)
        assert names == []  # no mutant names, so mutmut resumes rather than re-runs
        return {}

    monkeypatch.setattr(run, "run_mutmut", fake)
    settings = ms.load_settings(SETTINGS_THREE.read_text(encoding="utf-8"))
    run.collect(
        settings.repositories["troupe"], tmp_path, settings, None, FakeMutmut(), unit="troupe"
    )
    assert ran == ["troupe"]
    with pytest.raises(run.RunError) as raised:
        run.collect(
            settings.repositories["troupe"], tmp_path, settings, None, FakeMutmut(), unit="nope"
        )
    assert str(raised.value).startswith("troupe has no unit 'nope'; its units are ['troupe'")


def test_state_merge_takes_the_units_the_run_recorded(tmp_path: Path) -> None:
    mine, newest = tmp_path / "mine", tmp_path / "newest"
    for root, code in ((mine, 1), (newest, 0)):
        for unit in ("scripts", "other"):
            (root / unit).mkdir(parents=True)
            (root / unit / "a.meta").write_text(
                json.dumps({"exit_code_by_key": {"k": code}}), encoding="utf-8"
            )
        (root / "manifest.json").write_text(
            json.dumps({"version": 1, "mutmut": "3.8.1", "units": {"scripts": {}, "other": {}}}),
            encoding="utf-8",
        )
    record = tmp_path / "state-infrastructure.json"
    record.write_text(
        json.dumps({"version": 1, "units": {"scripts": {"saved": True}}}), encoding="utf-8"
    )
    assert run.main(["state-merge", str(mine), str(newest), str(record)]) == 0
    assert '"k": 1' in (newest / "scripts" / "a.meta").read_text(encoding="utf-8")
    assert '"k": 0' in (newest / "other" / "a.meta").read_text(encoding="utf-8")
