"""A scheduled run re-tests the kept results its changed tests could change (#418,
mutation-retest-changed-tests design D1-D6).

Node ids and the shape of `mutmut-stats.json` are as mutmut 3.8.1 wrote them in the change's
reproduction (`tests/test_calc.py::test_add_value`, functions as `<module>.x_<name>`)."""

import datetime
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import mutation_settings as ms
import mutation_state as st

pytestmark = pytest.mark.mutation

UNIT = ms.Unit("troupe", "packages/troupe/src", "packages/troupe/tests", "unit")
TODAY = datetime.date(2026, 11, 27)
ADD, DOUBLE, HALF = "troupe.calc.x_add", "troupe.calc.x_double", "troupe.calc.x_half"


def write(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(content, encoding="utf-8")


TESTS = {
    "conftest.py": "",
    "runtesting.py": "import storetesting\n",
    "storetesting.py": "VALUE = 1\n",
    "unit/test_add.py": "from troupe.calc import add\n",
    "unit/test_double.py": "import runtesting\n",
    "unit/test_half.py": "from storetesting import VALUE\n",
    "unit/sub/conftest.py": "",
    "unit/sub/test_deep.py": "",
    "integration/test_slow.py": "import runtesting\n",
    "data/schema.json": "{}",
}


# D1: the fingerprint and what changed


def test_a_fingerprint_hashes_every_file_under_the_tests_but_caches(tmp_path: Path) -> None:
    write(tmp_path, {"a.py": "x", "unit/test_b.py": "y"})
    write(tmp_path, {"__pycache__/a.cpython-312.pyc": "z", "unit/test_b.pyc": "z"})
    printed = st.fingerprint(tmp_path)
    assert sorted(printed) == ["a.py", "unit/test_b.py"]
    (tmp_path / "a.py").write_text("changed", encoding="utf-8")
    assert st.fingerprint(tmp_path)["a.py"] != printed["a.py"]
    assert st.fingerprint(tmp_path)["unit/test_b.py"] == printed["unit/test_b.py"]


def test_the_changed_files_are_those_added_edited_or_removed() -> None:
    old = {"same.py": "1", "edited.py": "1", "removed.py": "1"}
    new = {"same.py": "1", "edited.py": "2", "added.py": "1"}
    assert st.changed_files(old, new) == ["added.py", "edited.py", "removed.py"]
    assert st.changed_files(new, new) == []


# D2: the test files a change names


def named(changed: list[str], tmp_path: Path, removed: set[str] | None = None) -> set[str]:
    write(tmp_path, TESTS)
    result = st.named_test_files(tmp_path, changed, removed=removed or set())
    assert result is not None
    return result


def test_a_changed_test_file_names_itself(tmp_path: Path) -> None:
    assert named(["unit/test_add.py"], tmp_path) == {"unit/test_add.py"}


def test_a_helper_names_the_test_files_that_import_it_through_other_helpers(
    tmp_path: Path,
) -> None:
    """test_double imports runtesting, which imports storetesting; test_half imports storetesting
    with `from`. The integration test is named too: it's in no kept stats, so it clears nothing."""
    assert named(["storetesting.py"], tmp_path) == {
        "unit/test_double.py",
        "unit/test_half.py",
        "integration/test_slow.py",
    }


def test_a_relative_import_names_its_importer(tmp_path: Path) -> None:
    write(tmp_path, {"unit/pkg/__init__.py": "", "unit/pkg/helper.py": ""})
    write(tmp_path, {"unit/pkg/test_rel.py": "from . import helper\n"})
    write(tmp_path, {"unit/test_pkg.py": "from pkg.helper import thing\n"})
    assert named(["unit/pkg/helper.py"], tmp_path) == {"unit/pkg/test_rel.py", "unit/test_pkg.py"}


def test_a_removed_helper_names_the_test_files_that_still_import_it(tmp_path: Path) -> None:
    write(tmp_path, TESTS)
    (tmp_path / "runtesting.py").unlink()
    result = st.named_test_files(tmp_path, ["runtesting.py"], removed={"runtesting.py"})
    assert result == {"unit/test_double.py", "integration/test_slow.py"}


def test_a_changed_conftest_names_the_test_files_under_its_directory_only(
    tmp_path: Path,
) -> None:
    assert named(["unit/sub/conftest.py"], tmp_path) == {"unit/sub/test_deep.py"}


def test_a_file_that_isnt_python_names_every_test_file(tmp_path: Path) -> None:
    write(tmp_path, TESTS)
    assert st.named_test_files(tmp_path, ["data/schema.json"], removed=set()) is None


@pytest.mark.parametrize(
    ("node", "local", "expected"),
    [
        ("tests/unit/test_add.py::test_add_value", "tests", "unit/test_add.py"),
        ("tests/unit/test_add.py::TestAdd::test_x[1-2]", "tests", "unit/test_add.py"),
        # infrastructure's root unit: its tests are reached through the linked source (D2)
        ("src/tests/test_check.py::test_y", "src/tests", "test_check.py"),
        ("elsewhere/test_z.py::test_z", "tests", None),
    ],
)
def test_a_node_id_maps_to_its_file_under_the_units_tests(
    node: str, local: str, expected: str | None
) -> None:
    assert st.test_file_of(node, local) == expected


# D3-D5: clearing before and after the run


def meta(codes: Mapping[str, int | None]) -> str:
    return json.dumps(
        {
            "exit_code_by_key": codes,
            "hash_by_function_name": {},
            "type_check_error_by_key": {},
            "durations_by_key": {},
            "estimated_durations_by_key": {},
        }
    )


def stats(tests: dict[str, list[str]], hashes: dict[str, str] | None = None) -> str:
    names = sorted({t for ts in tests.values() for t in ts})
    return json.dumps(
        {
            "tests_by_mangled_function_name": tests,
            "duration_by_test": {name: 0.01 for name in names},
            "stats_time": 1.0,
            "function_hashes": hashes or {f: "h" for f in tests},
            "function_dependencies": {},
            "config_fingerprint": {},
            "watched_file_hashes": {},
            "git_commit": "a" * 40,
        }
    )


KEPT_CODES = {
    f"{ADD}__mutmut_1": 1,  # killed
    f"{ADD}__mutmut_2": 0,  # survived
    f"{DOUBLE}__mutmut_1": 1,
    f"{HALF}__mutmut_1": 33,  # reached by no test
}
KEPT_TESTS = {
    ADD: ["tests/unit/test_add.py::test_add_runs"],
    DOUBLE: ["tests/unit/test_double.py::test_double_runs"],
}


def setup(
    tmp_path: Path,
    *,
    old_tests: dict[str, str],
    new_tests: dict[str, str],
    recorded: bool = True,
) -> tuple[Path, Path, Path]:
    """A kept state saved against `old_tests`, and a checkout whose tests are `new_tests`."""
    old_dir, checkout_tests = tmp_path / "old", tmp_path / "checkout" / UNIT.tests
    write(old_dir, old_tests)
    write(checkout_tests, new_tests)
    state = tmp_path / "state"
    write(
        state / UNIT.name,
        {"src/troupe/calc.py.meta": meta(KEPT_CODES), "mutmut-stats.json": stats(KEPT_TESTS)},
    )
    entry: dict[str, object] = {
        "source": UNIT.source,
        "tests": UNIT.tests,
        "select": UNIT.select,
        "filled_since": "2026-11-20",
        "saved_by": "41",
        "commit": "a" * 40,
    }
    if recorded:
        entry["tests_fingerprint"] = st.fingerprint(old_dir)
    manifest = {"version": 1, "mutmut": "3.8.1", "units": {UNIT.name: entry}}
    write(state, {"manifest.json": json.dumps(manifest)})
    mutants = tmp_path / "mutants"
    mutants.mkdir()
    return state, mutants, checkout_tests


def restore(state: Path, mutants: Path, tests: Path) -> st.UnitState:
    return st.restore(
        state,
        UNIT,
        mutants,
        mutmut="3.8.1",
        today=TODAY,
        full_refresh_days=28,
        full_refresh=False,
        previously_saved=True,
        tests=tests,
        local_tests="tests",
    )


def codes(mutants: Path) -> dict[str, int | None]:
    data = json.loads((mutants / "src/troupe/calc.py.meta").read_text(encoding="utf-8"))
    return dict(data["exit_code_by_key"])


BASE = {"unit/test_add.py": "def test_add_runs(): ...\n", "unit/test_double.py": "x = 1\n"}


def test_nothing_changed_clears_nothing_and_leaves_the_stats_as_they_were(tmp_path: Path) -> None:
    state, mutants, tests = setup(tmp_path, old_tests=BASE, new_tests=BASE)
    unit = restore(state, mutants, tests)
    assert codes(mutants) == KEPT_CODES
    kept = (state / UNIT.name / "mutmut-stats.json").read_text(encoding="utf-8")
    assert (mutants / "mutmut-stats.json").read_text(encoding="utf-8") == kept
    assert (unit.tests_changed, unit.cleared_for_tests, unit.carried) == ([], 0, 4)


def test_an_edited_test_clears_every_result_its_tests_reached_and_forgets_what_they_reached(
    tmp_path: Path,
) -> None:
    edited = {**BASE, "unit/test_add.py": "def test_add_runs(): assert False\n"}
    state, mutants, tests = setup(tmp_path, old_tests=BASE, new_tests=edited)
    unit = restore(state, mutants, tests)
    assert codes(mutants) == {
        f"{ADD}__mutmut_1": None,  # killed, but by a test that changed
        f"{ADD}__mutmut_2": None,
        f"{DOUBLE}__mutmut_1": 1,  # no changed test reached it
        f"{HALF}__mutmut_1": 33,
    }
    data = json.loads((mutants / "mutmut-stats.json").read_text(encoding="utf-8"))
    assert data["tests_by_mangled_function_name"][ADD] == []
    assert "tests/unit/test_add.py::test_add_runs" not in data["duration_by_test"]
    assert (unit.tests_changed, unit.cleared_for_tests) == (["unit/test_add.py"], 2)
    assert unit.carried == 2  # a cleared result is tested again, not carried


def test_state_without_a_record_of_its_tests_counts_every_test_as_changed(
    tmp_path: Path,
) -> None:
    state, mutants, tests = setup(tmp_path, old_tests=BASE, new_tests=BASE, recorded=False)
    unit = restore(state, mutants, tests)
    assert codes(mutants)[f"{DOUBLE}__mutmut_1"] is None
    assert codes(mutants)[f"{HALF}__mutmut_1"] == 33  # no test reached it: nothing to redo
    assert unit.tests_unrecorded
    assert unit.cleared_for_tests == 3


def test_a_new_test_file_clears_the_carried_results_of_what_it_reaches(tmp_path: Path) -> None:
    """The #418 case: troupe#524 added unit tests, and the night kept the survivors."""
    added = {**BASE, "unit/test_half.py": "def test_half_value(): ...\n"}
    state, mutants, tests = setup(tmp_path, old_tests=BASE, new_tests=added)
    unit = restore(state, mutants, tests)
    # A new file has no kept tests, so nothing is cleared before the run
    assert codes(mutants) == KEPT_CODES
    gained = {**KEPT_TESTS, HALF: ["tests/unit/test_half.py::test_half_value"]}
    gained[ADD] = [*KEPT_TESTS[ADD], "tests/unit/test_half.py::test_half_value"]
    write(mutants, {"mutmut-stats.json": stats(gained)})
    assert st.clear_gained(mutants, unit) == (3, False)
    assert codes(mutants) == {
        f"{ADD}__mutmut_1": None,
        f"{ADD}__mutmut_2": None,
        f"{DOUBLE}__mutmut_1": 1,
        f"{HALF}__mutmut_1": None,
    }
    assert unit.cleared_for_tests == 3


def test_a_function_whose_code_changed_or_was_tested_this_run_isnt_cleared_again(
    tmp_path: Path,
) -> None:
    edited = {**BASE, "unit/test_double.py": "x = 2\n"}
    state, mutants, tests = setup(tmp_path, old_tests=BASE, new_tests=edited)
    unit = restore(state, mutants, tests)
    assert codes(mutants)[f"{DOUBLE}__mutmut_1"] is None
    # mutmut re-collected test_double (it reaches DOUBLE again) and tested DOUBLE's mutant;
    # ADD's code changed, so mutmut re-tested it against every test it knows
    after = {
        ADD: [*KEPT_TESTS[ADD], "tests/unit/test_new.py::test_n"],
        DOUBLE: ["tests/unit/test_double.py::test_double_runs"],
    }
    write(mutants, {"mutmut-stats.json": stats(after, {ADD: "changed", DOUBLE: "h"})})
    now = {**codes(mutants), f"{DOUBLE}__mutmut_1": 0, f"{ADD}__mutmut_1": 1}
    write(mutants, {"src/troupe/calc.py.meta": meta(now)})
    assert st.clear_gained(mutants, unit) == (0, True)
    assert codes(mutants)[f"{DOUBLE}__mutmut_1"] == 0


def test_a_save_records_the_tests_fingerprint_the_results_now_stand_for(tmp_path: Path) -> None:
    edited = {**BASE, "unit/test_add.py": "changed\n"}
    state, mutants, tests = setup(tmp_path, old_tests=BASE, new_tests=edited)
    unit = restore(state, mutants, tests)
    st.clear_gained(mutants, unit)
    unit.settle(completed=True)
    st.save(state, UNIT, mutants, unit, mutmut="3.8.1", run_id="42", commit="b" * 40, today=TODAY)
    manifest = json.loads((state / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["units"][UNIT.name]["tests_fingerprint"] == st.fingerprint(tests)


def test_a_run_whose_stats_may_be_unfinished_keeps_the_old_fingerprint(tmp_path: Path) -> None:
    """The budget stopped mutmut before it tested anything: its stats of the new tests may be
    partial, so the next run looks at the same changes again."""
    edited = {**BASE, "unit/test_add.py": "changed\n"}
    state, mutants, tests = setup(tmp_path, old_tests=BASE, new_tests=edited)
    old = json.loads((state / "manifest.json").read_text(encoding="utf-8"))
    unit = restore(state, mutants, tests)
    _, progressed = st.clear_gained(mutants, unit)
    unit.settle(completed=progressed)
    st.save(state, UNIT, mutants, unit, mutmut="3.8.1", run_id="42", commit="b" * 40, today=TODAY)
    manifest = json.loads((state / "manifest.json").read_text(encoding="utf-8"))
    kept = old["units"][UNIT.name]["tests_fingerprint"]
    assert manifest["units"][UNIT.name]["tests_fingerprint"] == kept


def test_a_first_fill_records_the_tests_it_ran_against(tmp_path: Path) -> None:
    tests = tmp_path / "checkout" / UNIT.tests
    write(tests, BASE)
    mutants = tmp_path / "mutants"
    mutants.mkdir()
    unit = st.restore(
        tmp_path / "state",
        UNIT,
        mutants,
        mutmut="3.8.1",
        today=TODAY,
        full_refresh_days=28,
        full_refresh=False,
        previously_saved=False,
        tests=tests,
        local_tests="tests",
    )
    write(mutants, {"src/a.py.meta": meta({"a.x_f__mutmut_1": 1})})
    st.save(tmp_path / "state", UNIT, mutants, unit, mutmut="3.8.1", run_id="1",
            commit="c" * 40, today=TODAY)  # fmt: skip
    manifest = json.loads((tmp_path / "state" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["units"][UNIT.name]["tests_fingerprint"] == st.fingerprint(tests)


# D4: run_mutmut runs mutmut once more for what it cleared after the run

KEY = "calc.x_add__mutmut_1"
OLD_TEST = "src/tests/unit/test_old.py::test_add_runs"
NEW_TEST = "src/tests/unit/test_new.py::test_add_value"


class GainingMutmut:
    """mutmut, as far as its files: the first run collects a new test reaching `add` and tests
    nothing (the kept survivor is carried); a second run tests the cleared mutant and kills it."""

    def __init__(self, first: int = 0, gain: bool = True, stop: str | None = None) -> None:
        self.calls = 0
        self.first, self.gain, self.stop = first, gain, stop

    def __call__(
        self, command: list[str], cwd: Path, timeout: float, *, tail: list[str] | None = None
    ) -> int:
        self.calls += 1
        mutants = cwd / "mutants"
        if self.calls == 1:
            tests = [OLD_TEST, NEW_TEST] if self.gain else [OLD_TEST]
            write(mutants, {"mutmut-stats.json": stats({"calc.x_add": tests})})
            if self.stop is not None and tail is not None:
                tail.append(self.stop)
            return self.first
        assert codes_of(mutants) == {KEY: None}
        write(mutants, {"src/calc.py.meta": meta({KEY: 1})})
        return 0


def codes_of(mutants: Path) -> dict[str, int | None]:
    data = json.loads((mutants / "src/calc.py.meta").read_text(encoding="utf-8"))
    return dict(data["exit_code_by_key"])


def scheduled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutmut: GainingMutmut
) -> tuple[dict[str, Any], st.UnitState, Path]:
    """infrastructure's root unit, its state saved with one survivor and before test_new.py."""
    from test_mutation_run import SETTINGS, fake_show, limited_tree

    import mutation_run as run

    limited_tree(tmp_path)
    write(tmp_path / "scripts/tests", {"unit/test_old.py": "def test_add_runs(): ...\n"})
    unit = SETTINGS.repositories["infrastructure"].units[0]
    state = tmp_path / "state"
    write(
        state / unit.name,
        {
            "src/calc.py.meta": meta({KEY: 0}),
            "mutmut-stats.json": stats({"calc.x_add": [OLD_TEST]}),
        },
    )
    entry = {
        "source": unit.source,
        "tests": unit.tests,
        "select": unit.select,
        "filled_since": "2026-11-20",
        "saved_by": "41",
        "commit": "a" * 40,
        "tests_fingerprint": st.fingerprint(tmp_path / "scripts/tests"),
    }
    write(state, {"manifest.json": json.dumps({"version": 1, "mutmut": "3.8.1",
                                               "units": {unit.name: entry}})})  # fmt: skip
    write(tmp_path / "scripts/tests", {"unit/test_new.py": "def test_add_value(): ...\n"})
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    fake_show(monkeypatch)
    kept = run.StateRun(state, "3.8.1", "42", "b" * 40, TODAY, 28, False, frozenset({unit.name}))
    modules = run.run_mutmut(
        tmp_path, unit, [], 1e12, mutmut, children=2, memory_mb=None, state=kept
    )
    return modules, kept.records[0], state / unit.name


def test_a_new_test_reaching_a_kept_survivor_gets_it_tested_again_in_the_same_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The #418 night: mutmut alone carries the survivor; the run re-tests it and the report
    counts the new test's kill."""
    mutmut = GainingMutmut()
    modules, record, saved = scheduled(tmp_path, monkeypatch, mutmut)
    assert mutmut.calls == 2
    assert modules["calc"].survivors == ()
    assert (record.cleared_for_tests, record.retested, record.tests_changed) == (
        1,
        True,
        ["unit/test_new.py"],
    )
    assert codes_of(saved) == {KEY: 1}
    assert "1 kept results reached by changed or new tests were cleared" in capsys.readouterr().out


def test_a_run_whose_tests_reach_nothing_new_runs_mutmut_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mutmut = GainingMutmut(gain=False)
    modules, record, saved = scheduled(tmp_path, monkeypatch, mutmut)
    assert mutmut.calls == 1
    assert len(modules["calc"].survivors) == 1
    assert (record.cleared_for_tests, record.retested) == (0, False)
    assert codes_of(saved) == {KEY: 0}


def test_a_run_the_budget_stopped_saves_the_cleared_results_for_the_next_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mutmut = GainingMutmut(first=-1)
    _, record, saved = scheduled(tmp_path, monkeypatch, mutmut)
    assert mutmut.calls == 1
    assert (record.cleared_for_tests, record.retested, record.left_for_next_run) == (1, False, 1)
    assert codes_of(saved) == {KEY: None}


# D6: the summary


def test_the_summary_names_the_changed_tests_and_what_they_cleared() -> None:
    import mutation_issues as mi

    changed = [f"unit/test_{n}.py" for n in range(7)]
    unit = {"tested": 3, "tests_changed": changed, "cleared_for_tests": 12, "retested": True}
    lines = mi.state_section({"units": {"troupe": unit}})
    files = ", ".join(f"`unit/test_{n}.py`" for n in range(5))
    assert f"  - test files changed since its state was saved: {files} and 2 more" in lines
    again = "  - 12 kept results cleared for changed or new tests, mutmut ran again for them"
    assert again in lines
    waiting = {"tests_unrecorded": True, "cleared_for_tests": 4, "left_for_next_run": 4}
    lines = mi.state_section({"units": {"troupe": waiting}})
    assert (
        "  - no record of the unit's tests in its kept state: every test counts as changed" in lines
    )
    assert "  - 4 of them are left for the next run to test" in lines


def test_a_units_record_carries_the_test_counts_but_not_the_fingerprint() -> None:
    unit = st.UnitState("troupe", tests_fingerprint={"a.py": "h"}, cleared_for_tests=2)
    record = unit.record()
    assert record["cleared_for_tests"] == 2
    assert "tests_fingerprint" not in record
    assert "kept_tests" not in record


def test_a_unit_whose_tests_reach_none_of_its_code_runs_mutmut_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mutmut stopped for a unit its tests don't reach (#399): nothing is cleared after it and it
    isn't run again, though the stats it left would show a gained test."""
    from test_mutation_unreached import STOP

    mutmut = GainingMutmut(first=1, stop=STOP)
    _, record, _ = scheduled(tmp_path, monkeypatch, mutmut)
    assert mutmut.calls == 1
    assert (record.unreached, record.retested, record.left_for_next_run) == (True, False, 0)


# A run killed outright: the harvest keeps the fingerprint the results were saved against (D4)


def harvest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, printed: dict[str, str] | None
) -> dict[str, object]:
    from test_mutation_run import SETTINGS_THREE, scratch_checkout

    import mutation_run as run

    monkeypatch.setattr(run, "SETTINGS", SETTINGS_THREE)
    repo, _ = scratch_checkout(tmp_path)
    write(repo / "scripts/tests", {"unit/test_new.py": "def test_add_value(): ...\n"})
    write(repo / "mutants", {"src/calc.py.meta": meta({KEY: 1})})
    entry: dict[str, object] = {"filled_since": "2026-11-20"}
    if printed is not None:
        entry["tests_fingerprint"] = printed
    state = tmp_path / "state"
    manifest = {"version": 1, "mutmut": "3.8.1", "units": {"scripts": entry}}
    write(state, {"manifest.json": json.dumps(manifest), "scripts/.keep": ""})
    record = tmp_path / "out" / "state-infrastructure.json"
    assert run.main(["state-harvest", "infrastructure", str(repo), str(state), str(record)]) == 0
    saved = json.loads((state / "manifest.json").read_text(encoding="utf-8"))
    unit: dict[str, object] = saved["units"]["scripts"]
    return unit


def test_a_harvested_run_keeps_the_fingerprint_its_state_was_saved_against(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Not the checkout's (test_new.py is new): the next run then looks at the same changes."""
    old = {"unit/test_old.py": "h"}
    assert harvest(tmp_path, monkeypatch, old)["tests_fingerprint"] == old


def test_a_harvested_run_with_no_fingerprint_writes_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert "tests_fingerprint" not in harvest(tmp_path, monkeypatch, None)
