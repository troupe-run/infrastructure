"""The run step drives mutmut and Stryker the way the trial showed they work (spec:
mutation-testing; lint-mutation design D3, D9). The tools themselves are faked here: the real
output they're read back from is in fixtures/mutation/ (test_mutation_report.py)."""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest

import mutation_run as run
import mutation_settings as ms

pytestmark = pytest.mark.mutation

SETTINGS = ms.load_settings(run.SETTINGS.read_text(encoding="utf-8"))


def test_a_package_with_a_src_directory_runs_mutmut_in_the_package(tmp_path: Path) -> None:
    (tmp_path / "packages" / "troupe" / "src").mkdir(parents=True)
    unit = ms.Unit("troupe", "packages/troupe/src", "packages/troupe/tests")
    assert run.mutmut_workdir(tmp_path, unit) == tmp_path / "packages" / "troupe"
    assert not (tmp_path / "src").exists()


def test_a_source_not_named_src_is_linked_as_src_at_the_root(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    unit = ms.Unit("scripts", "scripts", "scripts/tests")
    assert run.mutmut_workdir(tmp_path, unit) == tmp_path
    assert (tmp_path / "src").is_symlink()
    assert (tmp_path / "src").resolve() == (tmp_path / "scripts").resolve()


def test_a_checkout_that_already_has_a_src_is_refused(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "src").mkdir()
    with pytest.raises(run.RunError, match="already has a src"):
        run.mutmut_workdir(tmp_path, ms.Unit("scripts", "scripts", "scripts/tests"))


def test_infrastructures_config_mutates_the_linked_source_but_not_its_tests_and_copies_the_rest(
    tmp_path: Path,
) -> None:
    for name in ("scripts", "tofu", ".git", ".venv"):
        (tmp_path / name).mkdir()
    (tmp_path / ".tflint.hcl").touch()
    (tmp_path / "src").symlink_to("scripts")
    unit = SETTINGS.repositories["infrastructure"].units[0]
    config = run.mutmut_config(tmp_path, tmp_path, unit)
    assert "source_paths=src/\n" in config
    assert "pytest_add_cli_args_test_selection=src/tests\n" in config
    assert (
        "pytest_add_cli_args=\n    -o\n    addopts=-ra\n    -p\n    _mutation_children_plugin\n"
        in config
    )
    assert "do_not_mutate=\n    src/tests/*\n" in config
    assert config.endswith(
        "also_copy=\n    _mutation_children_plugin.py\n    .tflint.hcl\n    tofu\n"
    )


def test_a_failed_mutmut_run_is_an_error_not_an_empty_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    with pytest.raises(run.RunError, match="mutmut failed for scripts"):
        run.collect(
            SETTINGS.repositories["infrastructure"], tmp_path, SETTINGS, None, Recorder(code=1)
        )


def test_a_packages_config_selects_its_own_tests(tmp_path: Path) -> None:
    unit = ms.Unit("troupe", "packages/troupe/src", "packages/troupe/tests")
    config = run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit)
    assert "pytest_add_cli_args_test_selection=tests\n" in config
    assert config.endswith("also_copy=\n    _mutation_children_plugin.py\n")


# Stryker's report (the mutation testing report schema, which Stryker 10 writes)

SOURCE = "export function add(a: number, b: number) {\n  return a + b;\n}\n"


def stryker_report(*statuses: str) -> dict[str, object]:
    mutants = [
        {
            "id": str(n),
            "mutatorName": "ArithmeticOperator",
            "replacement": "a - b",
            "location": {"start": {"line": 2, "column": 10}, "end": {"line": 2, "column": 15}},
            "status": status,
        }
        for n, status in enumerate(statuses)
    ]
    return {
        "schemaVersion": "2",
        "files": {
            "src/lib/add.ts": {"language": "typescript", "source": SOURCE, "mutants": mutants}
        },
    }


def test_strykers_statuses_become_the_reports_counts() -> None:
    modules = run.from_stryker(
        stryker_report(
            "Killed", "Survived", "NoCoverage", "Timeout", "RuntimeError", "CompileError", "Ignored"
        )
    )
    add = modules["src/lib/add.ts"]
    counts = (add.killed, add.survived, add.no_tests, add.timeout, add.crashed, add.skipped)
    assert counts == (1, 1, 1, 1, 1, 2)
    assert add.finished


def test_a_stryker_survivor_shows_its_line_before_and_after() -> None:
    survivor = run.from_stryker(stryker_report("Survived"))["src/lib/add.ts"].survivors[0]
    assert (survivor.path, survivor.line) == ("src/lib/add.ts", 2)
    assert survivor.change == "-  return a + b;\n+  return a - b;"


def test_a_pending_stryker_mutant_leaves_its_file_unfinished() -> None:
    assert not run.from_stryker(stryker_report("Killed", "Pending"))["src/lib/add.ts"].finished


# The run: what it runs, and its budget


class Recorder:
    def __init__(self, code: int = 0) -> None:
        self.commands: list[tuple[list[str], Path, float]] = []
        self.code = code

    def __call__(self, command: list[str], cwd: Path, timeout: float) -> int:
        self.commands.append((command, cwd, timeout))
        (cwd / "mutants").mkdir(exist_ok=True)
        return self.code


def test_a_pull_request_run_mutates_only_the_named_functions_within_its_own_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    recorder = Recorder()
    only = {"scripts": ["mutation_settings.x_closed__mutmut_*"]}
    run.collect(SETTINGS.repositories["infrastructure"], tmp_path, SETTINGS, only, recorder)
    [(command, cwd, timeout)] = recorder.commands
    assert command == ["mutmut", "run", "mutation_settings.x_closed__mutmut_*"]
    assert cwd == tmp_path
    assert SETTINGS.pr_budget_minutes * 60 - 5 < timeout <= SETTINGS.pr_budget_minutes * 60
    assert not (tmp_path / "src").exists(), "the link is removed after the run"
    # In mutmut's copy, scripts leads to the mutated source, never an unmutated copy.
    assert (tmp_path / "mutants" / "scripts").is_symlink()
    assert str((tmp_path / "mutants" / "scripts").readlink()) == "src"


def test_a_pull_request_that_changed_no_unit_runs_nothing(tmp_path: Path) -> None:
    recorder = Recorder()
    modules = run.collect(SETTINGS.repositories["troupe"], tmp_path, SETTINGS, {}, recorder)
    assert modules == {}
    assert recorder.commands == []


def test_a_weekly_run_has_the_weekly_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    recorder = Recorder()
    run.collect(SETTINGS.repositories["infrastructure"], tmp_path, SETTINGS, None, recorder)
    [(command, _, timeout)] = recorder.commands
    assert command == ["mutmut", "run"]
    assert timeout > SETTINGS.budget_minutes * 60 - 5


def test_a_bad_only_argument_fails_naming_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "report.json"
    assert (
        run.main(
            ["infrastructure", str(tmp_path), str(out), "--only", json.dumps({"scripts": "x"})]
        )
        == 2
    )
    assert "--only" in capsys.readouterr().err
    assert not out.exists()


def test_an_unknown_repository_fails_naming_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run.main(["elsewhere", str(tmp_path), str(tmp_path / "r.json")]) == 2
    assert "elsewhere" in capsys.readouterr().err


def test_a_failed_run_still_removes_the_src_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    with pytest.raises(run.RunError):
        run.collect(
            SETTINGS.repositories["infrastructure"], tmp_path, SETTINGS, None, Recorder(code=1)
        )
    assert not (tmp_path / "src").exists()


def test_a_child_of_the_stats_pass_runs_the_original_code_and_can_import_mutmut() -> None:
    import mutation_children as children

    env = children.child_env({"MUTANT_UNDER_TEST": "stats", "PYTHONPATH": "/a"}, "/site")
    assert env == {"MUTANT_UNDER_TEST": "none.none", "PYTHONPATH": f"/a{os.pathsep}/site"}


def test_a_child_of_a_mutants_run_inherits_the_mutant() -> None:
    import mutation_children as children

    env = children.child_env({"MUTANT_UNDER_TEST": "guard.x_main__mutmut_3"}, "/site")
    assert env == {"MUTANT_UNDER_TEST": "guard.x_main__mutmut_3", "PYTHONPATH": "/site"}


def test_a_child_outside_a_mutation_run_is_left_alone() -> None:
    import mutation_children as children

    assert children.child_env({"A": "1"}, "/site") == {"A": "1"}


def test_a_deselected_test_is_named_from_mutmuts_working_directory(tmp_path: Path) -> None:
    linked = ms.Unit(
        "scripts",
        "scripts",
        "scripts/tests",
        deselect=(("scripts/tests/test_a.py::test_b[x]", "why"),),
    )
    assert run.deselected(tmp_path, tmp_path, linked) == [
        "--deselect",
        "src/tests/test_a.py::test_b[x]",
    ]
    package = ms.Unit(
        "troupe",
        "packages/troupe/src",
        "packages/troupe/tests",
        deselect=(("packages/troupe/tests/test_a.py::test_b", "why"),),
    )
    workdir = tmp_path / "packages" / "troupe"
    assert run.deselected(workdir, tmp_path, package) == ["--deselect", "tests/test_a.py::test_b"]


def limited_tree(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "calc.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8"
    )


class MetaRecorder(Recorder):
    """mutmut, as far as its meta file: one mutant run and killed, one left unrun."""

    def __call__(self, command: list[str], cwd: Path, timeout: float) -> int:
        code = super().__call__(command, cwd, timeout)
        meta = cwd / "mutants" / "src" / "calc.py.meta"
        meta.parent.mkdir(parents=True, exist_ok=True)
        codes = {"calc.x_add__mutmut_1": 1, "calc.x_add__mutmut_2": None}
        meta.write_text(json.dumps({"exit_code_by_key": codes}), encoding="utf-8")
        return code


@pytest.mark.parametrize(("code", "finished"), [(0, True), (-1, False)])
def test_a_limited_run_is_finished_unless_its_budget_stopped_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int, finished: bool
) -> None:
    limited_tree(tmp_path)
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    only = {"scripts": ["calc.x_add__mutmut_*"]}
    modules = run.collect(
        SETTINGS.repositories["infrastructure"], tmp_path, SETTINGS, only, MetaRecorder(code)
    )
    assert modules["calc"].finished is finished
    assert modules["calc"].counted == 1


def test_a_whole_run_with_unrun_mutants_isnt_finished(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    limited_tree(tmp_path)
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    modules = run.collect(
        SETTINGS.repositories["infrastructure"], tmp_path, SETTINGS, None, MetaRecorder(0)
    )
    assert not modules["calc"].finished


def test_a_unit_with_its_own_setup_cfg_is_refused_not_overwritten(tmp_path: Path) -> None:
    (tmp_path / "packages" / "troupe" / "src").mkdir(parents=True)
    (tmp_path / "packages" / "troupe" / "setup.cfg").write_text("[metadata]\n", encoding="utf-8")
    unit = ms.Unit("troupe", "packages/troupe/src", "packages/troupe/tests")
    with pytest.raises(run.RunError, match="won't overwrite"):
        run.run_mutmut(tmp_path, unit, [], 0.0, Recorder())
    assert (tmp_path / "packages" / "troupe" / "setup.cfg").read_text(
        encoding="utf-8"
    ) == "[metadata]\n"


def test_stryker_is_installed_into_the_checkout_then_run_in_place_with_one_runner() -> None:
    install, stryker = run.stryker_commands(["src/lib/a.ts:3-5", "src/lib/b.ts:9-9"], "10.1.1")
    assert install[:3] == ["npm", "install", "--no-save"]
    assert "@stryker-mutator/core@10.1.1" in install
    assert "@stryker-mutator/vitest-runner@10.1.1" in install
    assert stryker[:4] == ["npx", "--no-install", "stryker", "run"]
    assert "--inPlace" in stryker
    assert stryker[stryker.index("--concurrency") + 1] == "1"
    assert stryker[-2:] == ["--mutate", "src/lib/a.ts:3-5,src/lib/b.ts:9-9"]


def test_a_real_stryker_report_reads_back_with_every_survivor_on_its_source_line() -> None:
    fixture = Path(__file__).parent / "fixtures" / "mutation" / "stryker-10.1.1" / "mutation.json"
    report = json.loads(fixture.read_text(encoding="utf-8"))
    modules = run.from_stryker(report)
    nav = modules["src/lib/docs-nav.ts"]
    assert (nav.killed, nav.survived, nav.counted, nav.score) == (51, 39, 90, 56.7)
    assert modules["src/lib/copy.ts"].no_tests == 9
    for path, module in modules.items():
        lines = report["files"][path]["source"].splitlines()
        for survivor in module.survivors:
            assert survivor.change.splitlines()[0] == "-" + lines[survivor.line - 1], survivor.name


# What the run step writes and runs, exactly (lint-mutation 6b: the pull request report's survivors)


def test_a_linked_units_whole_config(tmp_path: Path) -> None:
    for name in ("scripts", "tofu", "mutants", "node_modules", ".venv"):
        (tmp_path / name).mkdir()
    (tmp_path / "setup.cfg").touch()
    (tmp_path / "src").symlink_to("scripts")
    unit = ms.Unit(
        "scripts", "scripts", "scripts/tests", deselect=(("scripts/tests/test_a.py::test_b", "w"),)
    )
    assert run.mutmut_config(tmp_path, tmp_path, unit) == (
        "[mutmut]\n"
        "source_paths=src/\n"
        "pytest_add_cli_args_test_selection=src/tests\n"
        "pytest_add_cli_args=\n    -o\n    addopts=-ra\n    -p\n    _mutation_children_plugin\n"
        "    --deselect\n    src/tests/test_a.py::test_b\n"
        f"max_children={run.CHILDREN}\n"
        "do_not_mutate=\n    src/tests/*\n"
        "also_copy=\n    _mutation_children_plugin.py\n    tofu\n"
    )


def test_a_packages_also_copy_is_named_from_its_own_directory(tmp_path: Path) -> None:
    unit = ms.Unit("troupe", "packages/troupe/src", "packages/troupe/tests", also_copy=("docs",))
    config = run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit)
    assert config.endswith("also_copy=\n    ../../docs\n    _mutation_children_plugin.py\n")


def test_a_deselected_parametrized_test_keeps_its_whole_node_id(tmp_path: Path) -> None:
    unit = ms.Unit(
        "scripts",
        "scripts",
        "scripts/tests",
        deselect=(
            ("scripts/tests/test_a.py::test_b[x::y]", "w"),
            ("scripts/tests/test_c.py::test_d", "w"),
        ),
    )
    assert run.deselected(tmp_path, tmp_path, unit) == [
        "--deselect",
        "src/tests/test_a.py::test_b[x::y]",
        "--deselect",
        "src/tests/test_c.py::test_d",
    ]


def test_stryker_is_run_exactly_so() -> None:
    assert run.stryker_commands(["src/a.ts"], "10.1.1") == [
        [
            "npm",
            "install",
            "--no-save",
            "--no-audit",
            "--no-fund",
            "@stryker-mutator/core@10.1.1",
            "@stryker-mutator/vitest-runner@10.1.1",
        ],
        [
            "npx",
            "--no-install",
            "stryker",
            "run",
            "--inPlace",
            "--testRunner",
            "vitest",
            "--reporters",
            "json,html",
            "--concurrency",
            "1",
            "--mutate",
            "src/a.ts",
        ],
    ]


# A run over a fake mutmut that leaves a real-shaped results tree


class FakeMutmut(Recorder):
    """mutmut, as far as its files: a meta file for calc.py with one survivor and one kill."""

    def __call__(self, command: list[str], cwd: Path, timeout: float) -> int:
        code = super().__call__(command, cwd, timeout)
        meta = cwd / "mutants" / "src" / "calc.py.meta"
        meta.parent.mkdir(parents=True, exist_ok=True)
        codes = {"calc.x_add__mutmut_1": 0, "calc.x_add__mutmut_2": 1}
        meta.write_text(json.dumps({"exit_code_by_key": codes}), encoding="utf-8")
        return code


def fake_show(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    shown: list[list[str]] = []

    class Done:
        stdout = (
            "--- src/calc.py\n+++ src/calc.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n"
            "-    return a + b\n+    return a - b"
        )

    real_run = subprocess.run

    def fake_run(args: list[str], **kwargs: Any) -> Any:  # noqa: ANN401
        if args[0] != "mutmut":
            return real_run(args, **kwargs)  # git, for the commit and blame
        shown.append([*args, str(kwargs.get("cwd"))])
        return Done()

    monkeypatch.setattr(subprocess, "run", fake_run)
    return shown


def test_a_run_maps_survivors_back_to_the_real_source_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    limited_tree(tmp_path)
    (tmp_path / "mutants" / "stale").mkdir(parents=True)
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    shown = fake_show(monkeypatch)
    unit = SETTINGS.repositories["infrastructure"].units[0]
    modules = run.run_mutmut(tmp_path, unit, [], 1e12, FakeMutmut())
    [survivor] = modules["calc"].survivors
    assert (survivor.path, survivor.line, survivor.name) == (
        "scripts/calc.py",
        2,
        "calc.x_add__mutmut_1",
    )
    assert shown == [["mutmut", "show", "calc.x_add__mutmut_1", str(tmp_path)]]
    assert not (tmp_path / "mutants" / "stale").exists(), (
        "an earlier run's mutants are removed first"
    )
    assert (tmp_path / "mutants" / "scripts").is_symlink()
    assert (tmp_path / "setup.cfg").read_text(encoding="utf-8") == run.mutmut_config(
        tmp_path, tmp_path, unit
    )
    assert not (tmp_path / "src").exists()
    assert not (tmp_path / "_mutation_children_plugin.py").exists()


def test_a_units_own_setup_cfg_is_refused_word_for_word(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "setup.cfg").write_text("[x]\n", encoding="utf-8")
    with pytest.raises(run.RunError) as raised:
        run.run_mutmut(
            tmp_path, SETTINGS.repositories["infrastructure"].units[0], [], 1e12, Recorder()
        )
    assert str(raised.value) == (
        f"{tmp_path / 'setup.cfg'} exists, and mutmut reads its configuration from there: "
        "this run writes its own, so it won't overwrite one the repository holds"
    )
    assert not (tmp_path / "src").exists(), "the link made for the run is removed"


# Stryker's report at its edges


def stryker_mutant(
    status: str, start: tuple[int, int], end: tuple[int, int], **extra: object
) -> dict[str, object]:
    return {
        "id": "7",
        "mutatorName": "StringLiteral",
        "replacement": '""',
        "status": status,
        "location": {
            "start": {"line": start[0], "column": start[1]},
            "end": {"line": end[0], "column": end[1]},
        },
        **extra,
    }


def test_a_report_without_files_is_refused_word_for_word() -> None:
    with pytest.raises(run.RunError) as raised:
        run.from_stryker({})
    assert str(raised.value) == "Stryker's report has no files"


def test_a_pending_mutant_doesnt_stop_the_others_being_counted() -> None:
    mutants = [
        stryker_mutant("Pending", (1, 1), (1, 2)),
        stryker_mutant("Killed", (1, 1), (1, 2)),
        stryker_mutant("Survived", (1, 1), (1, 2)),
    ]
    module = run.from_stryker({"files": {"a.ts": {"source": "x\n", "mutants": mutants}}})["a.ts"]
    assert (module.finished, module.killed, module.survived) == (False, 1, 1)


def test_a_mutant_spanning_lines_names_its_mutator_and_replacement() -> None:
    source = "f(\n  1,\n)\n"
    module = run.from_stryker(
        {
            "files": {
                "a.ts": {"source": source, "mutants": [stryker_mutant("Survived", (1, 1), (3, 2))]}
            }
        }
    )["a.ts"]
    [survivor] = module.survivors
    assert (survivor.name, survivor.line, survivor.change) == (
        "StringLiteral#7",
        1,
        '-f(\n+StringLiteral: ""',
    )


def test_a_mutant_past_the_source_has_no_original_line() -> None:
    module = run.from_stryker(
        {"files": {"a.ts": {"mutants": [stryker_mutant("Survived", (9, 1), (9, 2))]}}}
    )["a.ts"]
    assert module.survivors[0].change == '-\n+""'


def test_a_file_with_no_mutants_is_finished_with_nothing_counted() -> None:
    module = run.from_stryker({"files": {"a.ts": {"source": "x\n"}}})["a.ts"]
    assert (module.finished, module.counted) == (True, 0)


# The budget and what a pull request names


def test_a_unit_after_the_deadline_isnt_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    units = (
        ms.Unit("a", "packages/a/src", "packages/a/tests"),
        ms.Unit("b", "packages/b/src", "packages/b/tests"),
    )
    for unit in units:
        (tmp_path / unit.source).mkdir(parents=True)
    repository = ms.Repository("troupe", "mutmut", units=units)
    now = [100.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    settings = SETTINGS.__class__(**{**vars(SETTINGS), "budget_minutes": 1})

    class Slow(Recorder):
        """Each unit takes exactly the minute's budget: the next one starts at the deadline."""

        def __call__(self, command: list[str], cwd: Path, timeout: float) -> int:
            now[0] += 60.0
            return super().__call__(command, cwd, timeout)

    recorder = Slow()
    run.collect(repository, tmp_path, settings, None, recorder)
    assert [cwd for _, cwd, _ in recorder.commands] == [tmp_path / "packages" / "a"]


def test_a_pull_request_names_only_its_units(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    units = (
        ms.Unit("a", "packages/a/src", "packages/a/tests"),
        ms.Unit("b", "packages/b/src", "packages/b/tests"),
    )
    for unit in units:
        (tmp_path / unit.source).mkdir(parents=True)
    recorder = Recorder()
    run.collect(
        ms.Repository("troupe", "mutmut", units=units), tmp_path, SETTINGS, {"b": ["b.*"]}, recorder
    )
    assert [(command, cwd) for command, cwd, _ in recorder.commands] == [
        (["mutmut", "run", "b.*"], tmp_path / "packages" / "b")
    ]


def test_a_weekly_stryker_run_mutates_the_settings_globs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[list[str]] = []

    def fake_stryker(*args: Any) -> dict[str, object]:  # noqa: ANN401
        seen.append(list(args[2]))
        return {}

    monkeypatch.setattr(run, "run_stryker", fake_stryker)
    website = SETTINGS.repositories["website"]
    run.collect(website, tmp_path, SETTINGS, None, Recorder())
    run.collect(website, tmp_path, SETTINGS, {}, Recorder())
    run.collect(website, tmp_path, SETTINGS, {"stryker": ["src/a.ts:1-2"]}, Recorder())
    assert seen == [[], ["src/a.ts:1-2"]]


def test_stryker_installs_then_runs_the_settings_globs_when_none_are_named(tmp_path: Path) -> None:
    out = tmp_path / "reports" / "mutation" / "mutation.json"
    commands: list[list[str]] = []

    def fake(command: list[str], cwd: Path, timeout: float) -> int:
        commands.append(command)
        if command[0] == "npx":
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"files": {}}), encoding="utf-8")
        return 0

    run.run_stryker(tmp_path, SETTINGS.repositories["website"], [], 1e12, "10.1.1", fake)
    assert commands[1][-1] == ",".join(SETTINGS.repositories["website"].mutate)


def test_a_failed_stryker_install_is_named(tmp_path: Path) -> None:
    with pytest.raises(run.RunError) as raised:
        run.run_stryker(
            tmp_path, SETTINGS.repositories["website"], [], 1e12, "10.1.1", lambda c, w, t: 7
        )
    assert str(raised.value) == "installing Stryker 10.1.1 failed (exit 7)"


# The command


def scratch_checkout(tmp_path: Path) -> tuple[Path, str]:
    from conftest import git

    repo = tmp_path / "checkout"
    (repo / "scripts").mkdir(parents=True)
    (repo / "scripts" / "calc.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8"
    )
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "c", "--author=Test <test@example.invalid>")
    return repo, git(repo, "rev-parse", "HEAD").stdout.strip()


def test_a_run_writes_its_report_with_the_checkouts_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, commit = scratch_checkout(tmp_path)
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    fake_show(monkeypatch)
    out = tmp_path / "out" / "report.json"
    only = json.dumps({"scripts": ["calc.*"]})
    assert (
        run.main(
            ["infrastructure", str(repo), str(out), "--previous", commit, "--only", only],
            FakeMutmut(),
        )
        == 0
    )
    import mutation_report as mr

    report = mr.load_report(out.read_text(encoding="utf-8"), "infrastructure")
    assert (report.commit, report.previous_commit) == (commit, commit)
    assert report.modules["calc"].survivors[0].commit == commit
    assert (
        capsys.readouterr().out
        == f"mutation_run: 1 modules from infrastructure, written to {out}\n"
    )


def test_a_run_over_a_directory_that_isnt_a_checkout_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "r.json"
    assert run.main(["website", str(tmp_path), str(out), "--only", "{}"], Recorder()) == 2
    assert capsys.readouterr().err == f"mutation_run: {tmp_path} isn't a git checkout\n"
    assert not out.exists()


@pytest.mark.parametrize("only", ['["x"]', '{"a": ["x", 1]}'])
def test_only_must_be_an_object_of_lists_of_strings(
    tmp_path: Path, only: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        run.main(
            ["infrastructure", str(tmp_path), str(tmp_path / "r.json"), "--only", only], Recorder()
        )
        == 2
    )
    assert (
        capsys.readouterr().err
        == "mutation_run: --only must be a JSON object of lists of strings\n"
    )


# The children plugin


def test_a_child_given_no_environment_gets_this_ones_with_the_stats_hook_turned_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import mutation_children as children

    monkeypatch.setenv("MUTANT_UNDER_TEST", "stats")
    monkeypatch.setenv("PYTHONPATH", f"/a{os.pathsep}{os.pathsep}/b")
    env = children.child_env(None, "/site")
    assert env is not None
    assert env["MUTANT_UNDER_TEST"] == "none.none"
    assert env["PYTHONPATH"] == f"/a{os.pathsep}/b{os.pathsep}/site"


def test_a_child_outside_a_run_given_no_environment_inherits_this_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import mutation_children as children

    monkeypatch.delenv("MUTANT_UNDER_TEST", raising=False)
    assert children.child_env(None, "/site") is None


def test_mutmut_already_on_the_path_isnt_added_twice() -> None:
    import mutation_children as children

    env = children.child_env({"MUTANT_UNDER_TEST": "m.x__mutmut_1", "PYTHONPATH": "/site"}, "/site")
    assert env == {"MUTANT_UNDER_TEST": "m.x__mutmut_1", "PYTHONPATH": "/site"}


def test_loading_the_plugin_patches_how_children_start(monkeypatch: pytest.MonkeyPatch) -> None:
    import mutation_children as children

    monkeypatch.setattr(subprocess.Popen, "__init__", subprocess.Popen.__init__)
    children.pytest_configure(object())
    assert subprocess.Popen.__init__ is children._popen_init


def test_a_child_starts_with_the_adjusted_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    import mutation_children as children

    started: list[dict[str, Any]] = []
    monkeypatch.setattr(
        children, "_original_init", lambda self, *args, **kwargs: started.append(kwargs)
    )
    monkeypatch.setattr(children, "mutmut_path", lambda: "/site")
    children._popen_init(object(), ["x"], env={"MUTANT_UNDER_TEST": "stats"}, cwd="/w")  # type: ignore[arg-type]
    assert started == [
        {"env": {"MUTANT_UNDER_TEST": "none.none", "PYTHONPATH": "/site"}, "cwd": "/w"}
    ]
