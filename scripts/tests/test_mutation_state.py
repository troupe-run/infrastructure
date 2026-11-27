"""mutmut's kept state between scheduled runs (#378, mutation-incremental design D1a-D4)."""

import datetime
import json
import subprocess
from pathlib import Path

import pytest

import mutation_settings as ms
import mutation_state as st

pytestmark = pytest.mark.mutation

UNIT = ms.Unit("troupe", "packages/troupe/src", "packages/troupe/tests", "unit")
OTHER = ms.Unit(
    "troupe-vcs-git", "packages/troupe-vcs-git/src", "packages/troupe-vcs-git/tests", "unit"
)
TODAY = datetime.date(2026, 11, 22)


def meta(codes: dict[str, int | None]) -> str:
    """A `.meta` file shaped as mutmut 3.8.1 writes it (mutation/data.py)."""
    return json.dumps(
        {
            "exit_code_by_key": codes,
            "hash_by_function_name": {},
            "type_check_error_by_key": {},
            "durations_by_key": {},
            "estimated_durations_by_key": {},
        }
    )


def kept(
    tmp_path: Path,
    units: dict[str, dict[str, str]],
    *,
    mutmut: str = "3.8.1",
    filled_since: str = "2026-11-20",
    source: str | None = None,
    select: str | None = "unit",
) -> Path:
    """A state directory as a previous run saved it: each unit's files under state/<unit>/."""
    state = tmp_path / "state"
    manifest: dict[str, object] = {"version": 1, "mutmut": mutmut, "units": {}}
    for name, files in units.items():
        unit = UNIT if name == UNIT.name else OTHER
        for rel, content in files.items():
            (state / name / rel).parent.mkdir(parents=True, exist_ok=True)
            (state / name / rel).write_text(content, encoding="utf-8")
        entry: dict[str, str] = {
            "source": source or unit.source,
            "tests": unit.tests,
            "filled_since": filled_since,
            "saved_by": "41",
            "commit": "a" * 40,
        }
        if select is not None:  # None: a manifest saved before units had a selection (#394)
            entry["select"] = select
        manifest["units"][name] = entry  # type: ignore[index]
    state.mkdir(exist_ok=True)
    (state / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return state


def restore(
    state: Path, mutants: Path, *, previously_saved: bool = True, full_refresh: bool = False
) -> st.UnitState:
    mutants.mkdir(parents=True, exist_ok=True)
    return st.restore(
        state,
        UNIT,
        mutants,
        mutmut="3.8.1",
        today=TODAY,
        full_refresh_days=28,
        full_refresh=full_refresh,
        previously_saved=previously_saved,
        tests=mutants.parent / "no-tests",
        local_tests="tests",
    )


CALC = {
    "src/troupe/calc.py.meta": meta(
        {"troupe.calc.x_add__mutmut_1": 1, "troupe.calc.x_add__mutmut_2": None}
    )
}
STATS = {"mutmut-stats.json": json.dumps({"tests_by_mangled_function_name": {}})}


def test_a_units_state_is_copied_into_mutants_and_its_results_counted(tmp_path: Path) -> None:
    state = kept(tmp_path, {"troupe": {**CALC, **STATS}})
    mutants = tmp_path / "mutants"
    unit = restore(state, mutants)
    assert (mutants / "src/troupe/calc.py.meta").read_text(encoding="utf-8") == CALC[
        "src/troupe/calc.py.meta"
    ]
    assert (mutants / "mutmut-stats.json").exists()
    assert (unit.restored_from, unit.carried, unit.lost, unit.unfit) == ("41", 1, False, False)


def test_a_first_fill_starts_empty_and_doesnt_fail(tmp_path: Path) -> None:
    unit = restore(tmp_path / "state", tmp_path / "mutants", previously_saved=False)
    assert unit.restored_from is None
    assert not unit.lost
    assert not unit.unfit
    assert unit.discarded == ["no state kept yet: a first fill"]


def test_state_the_previous_run_saved_but_this_one_cant_restore_is_lost(tmp_path: Path) -> None:
    """An evicted cache entry: nothing in the cache can say so; the previous run's record can."""
    unit = restore(tmp_path / "state", tmp_path / "mutants", previously_saved=True)
    assert unit.lost
    assert unit.discarded == [
        "the state the previous run saved is gone (the cache entry was evicted or lost): "
        "filling afresh"
    ]


def test_state_from_another_mutmut_version_is_discarded_and_unfit(tmp_path: Path) -> None:
    state = kept(tmp_path, {"troupe": CALC}, mutmut="3.7.0")
    unit = restore(state, tmp_path / "mutants")
    assert unit.unfit
    assert unit.discarded == ["state from mutmut 3.7.0, not 3.8.1: discarded, filling afresh"]
    assert not (tmp_path / "mutants" / "src").exists()


def test_a_unit_whose_sources_changed_in_the_settings_is_discarded_and_unfit(
    tmp_path: Path,
) -> None:
    state = kept(tmp_path, {"troupe": CALC}, source="packages/old/src")
    unit = restore(state, tmp_path / "mutants")
    assert unit.unfit
    assert unit.discarded == [
        "the settings moved the unit's sources, tests or test selection since its state was "
        "saved: discarded, filling afresh"
    ]


@pytest.mark.parametrize("select", [None, "integration"])
def test_a_unit_whose_test_selection_changed_is_discarded_and_unfit(
    tmp_path: Path, select: str | None
) -> None:
    """Results an integration test killed would otherwise be carried as killed: the first run
    after #394 (a manifest with no selection) starts each unit afresh, named, and fails visibly."""
    state = kept(tmp_path, {"troupe": CALC}, select=select)
    unit = restore(state, tmp_path / "mutants")
    assert unit.unfit
    assert unit.discarded == [
        "the settings moved the unit's sources, tests or test selection since its state was "
        "saved: discarded, filling afresh"
    ]
    assert not (tmp_path / "mutants" / "src").exists()


def test_an_unreadable_meta_drops_only_that_file_and_is_named(tmp_path: Path) -> None:
    """mutmut keeps one .meta per source file, so that file's mutants are tested again."""
    files = {**CALC, "src/troupe/cut.py.meta": '{"exit_code_by_key": {"troupe.cut.x_f__mut'}
    unit = restore(kept(tmp_path, {"troupe": files}), tmp_path / "mutants")
    assert unit.unfit
    assert unit.discarded == ["src/troupe/cut.py.meta can't be read: its mutants are tested again"]
    assert (tmp_path / "mutants" / "src/troupe/calc.py.meta").exists()
    assert not (tmp_path / "mutants" / "src/troupe/cut.py.meta").exists()
    assert unit.carried == 1


@pytest.mark.parametrize(
    ("filled_since", "full_refresh"), [("2026-10-24", False), ("2026-11-20", True)]
)
def test_a_refresh_discards_the_state_on_purpose_and_doesnt_fail(
    tmp_path: Path, filled_since: str, full_refresh: bool
) -> None:
    state = kept(tmp_path, {"troupe": CALC}, filled_since=filled_since)
    unit = restore(state, tmp_path / "mutants", full_refresh=full_refresh)
    assert unit.refreshed
    assert not unit.unfit
    assert not unit.lost
    assert unit.discarded == [
        "a full refresh: the kept state is discarded on purpose, filling afresh"
        if full_refresh
        else "a full refresh: the state was filled from 2026-10-24, over 28 days ago, "
        "filling afresh"
    ]


def test_a_save_writes_back_the_units_results_and_stats_and_counts_what_was_tested(
    tmp_path: Path,
) -> None:
    state = kept(tmp_path, {"troupe": {**CALC, **STATS}})
    mutants = tmp_path / "mutants"
    unit = restore(state, mutants)
    after = meta({"troupe.calc.x_add__mutmut_1": 1, "troupe.calc.x_add__mutmut_2": 0})
    (mutants / "src/troupe/calc.py.meta").write_text(after, encoding="utf-8")
    (mutants / "src/troupe/calc.py").write_text("mutated source, not state\n", encoding="utf-8")
    st.save(state, UNIT, mutants, unit, mutmut="3.8.1", run_id="42", commit="b" * 40, today=TODAY)
    assert (state / "troupe" / "src/troupe/calc.py.meta").read_text(encoding="utf-8") == after
    assert not (state / "troupe" / "src/troupe/calc.py").exists()
    manifest = json.loads((state / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["units"]["troupe"]["saved_by"] == "42"
    assert manifest["units"]["troupe"]["select"] == "unit"
    assert manifest["units"]["troupe"]["filled_since"] == "2026-11-20"
    assert (unit.carried, unit.tested, unit.saved) == (1, 1, True)


def test_a_fill_started_today_records_today(tmp_path: Path) -> None:
    state, mutants = tmp_path / "state", tmp_path / "mutants"
    unit = restore(state, mutants, previously_saved=False)
    (mutants / "src").mkdir()
    (mutants / "src/a.py.meta").write_text(meta({"a.x_f__mutmut_1": 1}), encoding="utf-8")
    st.save(state, UNIT, mutants, unit, mutmut="3.8.1", run_id="1", commit="c" * 40, today=TODAY)
    manifest = json.loads((state / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["units"]["troupe"]["filled_since"] == "2026-11-22"


def test_a_merge_takes_only_the_units_this_run_ran_and_every_other_unit_from_the_newest_entry(
    tmp_path: Path,
) -> None:
    """Two runs overlapping, despite the concurrency group: a unit dispatch saving after a
    nightly run must not drop the nightly run's progress on a unit the dispatch never ran."""
    mine = kept(
        tmp_path / "mine",
        {"troupe": {"a.meta": meta({"x": 1})}, "troupe-vcs-git": {"b.meta": meta({"y": None})}},
    )
    newest = kept(
        tmp_path / "newest",
        {"troupe": {"a.meta": meta({"x": None})}, "troupe-vcs-git": {"b.meta": meta({"y": 0})}},
    )
    newest_other = (newest / "troupe-vcs-git" / "b.meta").read_bytes()
    st.merge(mine, newest, ran=["troupe"])
    assert (newest / "troupe" / "a.meta").read_text(encoding="utf-8") == meta({"x": 1})
    assert (newest / "troupe-vcs-git" / "b.meta").read_bytes() == newest_other
    manifest = json.loads((newest / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["units"]) == {"troupe", "troupe-vcs-git"}


def test_a_merge_with_no_newest_entry_keeps_its_own(tmp_path: Path) -> None:
    mine = kept(tmp_path / "mine", {"troupe": {"a.meta": meta({"x": 1})}})
    newest = tmp_path / "newest" / "state"
    st.merge(mine, newest, ran=["troupe"])
    assert (newest / "troupe" / "a.meta").read_text(encoding="utf-8") == meta({"x": 1})


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def test_non_python_changes_since_the_last_full_run_are_listed_as_mutmut_would_warn(
    tmp_path: Path,
) -> None:
    """mutmut keeps cached results and warns ("warn"); the run names the same files (design D4)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    for name, content in {"uv.lock": "1\n", "README.md": "a\n", "a.py": "x = 1\n"}.items():
        (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", ".")
    git(
        repo, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-q", "-m", "one"
    )
    base = git(repo, "rev-parse", "HEAD")
    for name in ("uv.lock", "README.md", "a.py"):
        (repo / name).write_text("changed\n", encoding="utf-8")
    stats = tmp_path / "mutants" / "mutmut-stats.json"
    stats.parent.mkdir()
    stats.write_text(json.dumps({"git_commit": base}), encoding="utf-8")
    assert st.non_python_changes(repo, stats) == ["uv.lock"]
    stats.write_text(json.dumps({"git_commit": None}), encoding="utf-8")
    assert st.non_python_changes(repo, stats) == []
