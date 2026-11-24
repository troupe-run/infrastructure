"""The run step drives mutmut and Stryker the way the trial showed they work (spec:
mutation-testing; lint-mutation design D3, D9). The tools themselves are faked here: the real
output they're read back from is in fixtures/mutation/ (test_mutation_report.py)."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

import mutation_run as run
import mutation_settings as ms

pytestmark = pytest.mark.mutation

# The settings as they were with three repositories and both tools (#332 cut the real list to
# troupe), so every tool's code stays tested.
SETTINGS_THREE = Path(__file__).parent / "fixtures" / "mutation" / "settings-three.json"
SETTINGS = ms.load_settings(SETTINGS_THREE.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def three_repositories(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() reads the settings from run.SETTINGS: give it the same three repositories."""
    monkeypatch.setattr(run, "SETTINGS", SETTINGS_THREE)


def test_a_package_with_a_src_directory_runs_mutmut_in_the_package(tmp_path: Path) -> None:
    (tmp_path / "packages" / "troupe" / "src").mkdir(parents=True)
    unit = ms.Unit("troupe", "packages/troupe/src", "packages/troupe/tests", "unit")
    assert run.mutmut_workdir(tmp_path, unit) == tmp_path / "packages" / "troupe"
    assert not (tmp_path / "src").exists()


def test_a_source_not_named_src_is_linked_as_src_at_the_root(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    unit = ms.Unit("scripts", "scripts", "scripts/tests", "unit")
    assert run.mutmut_workdir(tmp_path, unit) == tmp_path
    assert (tmp_path / "src").is_symlink()
    assert (tmp_path / "src").resolve() == (tmp_path / "scripts").resolve()


def test_a_checkout_that_already_has_a_src_is_refused(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "src").mkdir()
    with pytest.raises(run.RunError, match="already has a src"):
        run.mutmut_workdir(tmp_path, ms.Unit("scripts", "scripts", "scripts/tests", "unit"))


def test_a_root_units_config_runs_only_its_selected_tests_and_mutates_none_of_its_tests(
    tmp_path: Path,
) -> None:
    """mutmut runs src/tests/unit, while do_not_mutate still covers all of src/tests: the helpers
    both kinds of test import are run, never mutated (#394, design D1)."""
    for name in ("scripts", "tofu", ".git", ".venv"):
        (tmp_path / name).mkdir()
    (tmp_path / ".tflint.hcl").touch()
    (tmp_path / "src").symlink_to("scripts")
    unit = SETTINGS.repositories["infrastructure"].units[0]
    config = run.mutmut_config(tmp_path, tmp_path, unit, children=2)
    assert "source_paths=src/\n" in config
    assert "pytest_add_cli_args_test_selection=src/tests/unit\n" in config
    assert (
        "pytest_add_cli_args=\n    -o\n    addopts=-ra\n    -p\n    _mutation_children_plugin\n"
        in config
    )
    assert "do_not_mutate=\n    src/tests/*\n" in config
    assert config.endswith(
        "also_copy=\n    _mutation_children_plugin.py\n"
        "    _mutation_children_plugin.json\n    .tflint.hcl\n    tofu\n"
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


def test_a_packages_config_runs_only_its_selected_tests_but_keeps_all_of_them(
    tmp_path: Path,
) -> None:
    """mutmut runs tests/unit; the whole tests directory stays out of also_copy, since mutmut
    copies it itself, so the helpers both kinds import are there too (#394, design D1)."""
    package = tmp_path / "packages" / "troupe"
    (package / "tests" / "unit").mkdir(parents=True)
    (package / "tests" / "integration").mkdir()
    (package / "tests" / "cli_shared.py").touch()
    unit = ms.Unit("troupe", "packages/troupe/src", "packages/troupe/tests", "unit")
    config = run.mutmut_config(package, tmp_path, unit, children=2)
    assert "pytest_add_cli_args_test_selection=tests/unit\n" in config
    assert config.endswith(
        "also_copy=\n    _mutation_children_plugin.py\n    _mutation_children_plugin.json\n"
    )


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


def test_a_stryker_runtime_error_is_named_with_no_exit_code() -> None:
    """Stryker reports a crash as RuntimeError, without an exit code (#361)."""
    [crash] = run.from_stryker(stryker_report("RuntimeError"))["src/lib/add.ts"].crashed_mutants
    assert (crash.path, crash.line, crash.exit_code) == ("src/lib/add.ts", 2, None)
    assert crash.name == "ArithmeticOperator#0"
    assert "a - b" in crash.change


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
        "unit",
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
        "unit",
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
    unit = ms.Unit("troupe", "packages/troupe/src", "packages/troupe/tests", "unit")
    with pytest.raises(run.RunError, match="won't overwrite"):
        run.run_mutmut(tmp_path, unit, [], 0.0, Recorder(), children=2, memory_mb=None)
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
        "scripts",
        "scripts",
        "scripts/tests",
        "unit",
        deselect=(("scripts/tests/test_a.py::test_b", "w"),),
    )
    assert run.mutmut_config(tmp_path, tmp_path, unit, children=2) == (
        "[mutmut]\n"
        "source_paths=src/\n"
        "pytest_add_cli_args_test_selection=src/tests/unit\n"
        "pytest_add_cli_args=\n    -o\n    addopts=-ra\n    -p\n    _mutation_children_plugin\n"
        "    --deselect\n    src/tests/test_a.py::test_b\n"
        "max_children=2\n"
        "do_not_mutate=\n    src/tests/*\n"
        "also_copy=\n    _mutation_children_plugin.py\n"
        "    _mutation_children_plugin.json\n    tofu\n"
    )


def test_a_packages_unit_copies_its_packages_own_files(tmp_path: Path) -> None:
    """A plugin's tests read its tools/ and fixtures/ from their own file (#337)."""
    package = tmp_path / "plugins" / "runner-a"
    for name in ("src", "tests", "tools", "fixtures", ".venv", "mutants", ".pytest_cache",
                 ".mypy_cache", "dist", "build", "troupe_runner_a.egg-info"):  # fmt: skip
        (package / name).mkdir(parents=True)
    for name in ("LICENSE", "pyproject.toml", "uv.lock", "setup.cfg",
                 "_mutation_children_plugin.py", ".coverage"):  # fmt: skip
        (package / name).touch()
    unit = ms.Unit("runner-a", "plugins/runner-a/src", "plugins/runner-a/tests", "unit")
    config = run.mutmut_config(package, tmp_path, unit, children=2)
    assert config.endswith(
        "also_copy=\n    _mutation_children_plugin.py\n"
        "    _mutation_children_plugin.json\n    LICENSE\n    fixtures\n"
        "    pyproject.toml\n    tools\n    uv.lock\n"
    )


def test_the_config_runs_as_many_mutants_at_once_as_the_settings_say(tmp_path: Path) -> None:
    (tmp_path / "packages" / "troupe").mkdir(parents=True)
    unit = ms.Unit("troupe", "packages/troupe/src", "packages/troupe/tests", "unit")
    config = run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=3)
    assert "\nmax_children=3\n" in config


def test_a_run_takes_max_children_from_the_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[int] = []

    def fake(checkout: Path, unit: ms.Unit, names: object, deadline: float, run_: object,
             *, children: int, memory_mb: int | None, state: object = None,
             ) -> dict[str, object]:  # fmt: skip
        seen.append(children)
        return {}

    monkeypatch.setattr(run, "run_mutmut", fake)
    settings = SETTINGS.__class__(**{**vars(SETTINGS), "max_children": 3})
    run.collect(SETTINGS.repositories["troupe"], tmp_path, settings, None, Recorder())
    assert seen
    assert set(seen) == {3}


def test_a_packages_also_copy_is_named_from_its_own_directory(tmp_path: Path) -> None:
    (tmp_path / "packages" / "troupe").mkdir(parents=True)
    unit = ms.Unit(
        "troupe", "packages/troupe/src", "packages/troupe/tests", "unit", also_copy=("docs",)
    )
    config = run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=2)
    assert config.endswith(
        "also_copy=\n    ../../docs\n    _mutation_children_plugin.py\n"
        "    _mutation_children_plugin.json\n"
    )


def test_a_deselected_parametrized_test_keeps_its_whole_node_id(tmp_path: Path) -> None:
    unit = ms.Unit(
        "scripts",
        "scripts",
        "scripts/tests",
        "unit",
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


class CrashingMutmut(Recorder):
    """mutmut, as far as its files: a meta file for calc.py with one crash (SIGKILL)."""

    def __call__(self, command: list[str], cwd: Path, timeout: float) -> int:
        code = super().__call__(command, cwd, timeout)
        meta = cwd / "mutants" / "src" / "calc.py.meta"
        meta.parent.mkdir(parents=True, exist_ok=True)
        codes = {"calc.x_add__mutmut_1": -9}
        meta.write_text(json.dumps({"exit_code_by_key": codes}), encoding="utf-8")
        return code


def test_a_run_maps_crashed_mutants_back_to_the_real_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    limited_tree(tmp_path)
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    fake_show(monkeypatch)
    unit = SETTINGS.repositories["infrastructure"].units[0]
    modules = run.run_mutmut(tmp_path, unit, [], 1e12, CrashingMutmut(), children=2, memory_mb=None)
    [crash] = modules["calc"].crashed_mutants
    assert (crash.path, crash.line, crash.name, crash.exit_code) == (
        "scripts/calc.py",
        2,
        "calc.x_add__mutmut_1",
        -9,
    )


def test_a_run_maps_survivors_back_to_the_real_source_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    limited_tree(tmp_path)
    (tmp_path / "mutants" / "stale").mkdir(parents=True)
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    shown = fake_show(monkeypatch)
    unit = SETTINGS.repositories["infrastructure"].units[0]
    modules = run.run_mutmut(tmp_path, unit, [], 1e12, FakeMutmut(), children=2, memory_mb=None)
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
        tmp_path, tmp_path, unit, children=2
    )
    assert not (tmp_path / "src").exists()
    assert not (tmp_path / "_mutation_children_plugin.py").exists()


class ConfigSeeingMutmut(FakeMutmut):
    """FakeMutmut that keeps the plugin's config as it stood while mutmut ran."""

    seen: object = None

    def __call__(self, command: list[str], cwd: Path, timeout: float) -> int:
        self.seen = json.loads((cwd / "_mutation_children_plugin.json").read_text(encoding="utf-8"))
        return super().__call__(command, cwd, timeout)


@pytest.mark.parametrize("memory_mb", [None, 3072])
def test_a_run_hands_the_plugin_its_cap_and_where_to_record_peaks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, memory_mb: int | None
) -> None:
    """The cap and the peaks file reach the plugin in a file beside its copy, which mutmut copies
    into mutants/ with it, never through the environment (#366, design D2)."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "calc.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8"
    )
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    fake_show(monkeypatch)
    unit = SETTINGS.repositories["infrastructure"].units[0]
    mutmut = ConfigSeeingMutmut()
    run.run_mutmut(tmp_path, unit, [], 1e12, mutmut, children=2, memory_mb=memory_mb)
    assert mutmut.seen == {
        "mutant_memory_mb": memory_mb,
        "peaks": str(tmp_path / "_mutation_children_peaks.log"),
    }
    assert "    _mutation_children_plugin.json\n" in (tmp_path / "setup.cfg").read_text(
        encoding="utf-8"
    )
    assert not (tmp_path / "_mutation_children_plugin.json").exists()
    assert not (tmp_path / "_mutation_children_peaks.log").exists()


def test_a_run_takes_the_per_mutant_cap_from_the_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caps: list[int | None] = []

    def fake(checkout: Path, unit: ms.Unit, names: object, deadline: float, run_: object,
             *, children: int, memory_mb: int | None, state: object = None,
             ) -> dict[str, object]:  # fmt: skip
        caps.append(memory_mb)
        return {}

    monkeypatch.setattr(run, "run_mutmut", fake)
    settings = SETTINGS.__class__(**{**vars(SETTINGS), "mutant_memory_mb": 3072})
    run.collect(SETTINGS.repositories["troupe"], tmp_path, settings, None, Recorder())
    assert caps
    assert set(caps) == {3072}


def package_checkout(tmp_path: Path) -> ms.Unit:
    """troupe's shape: packages beside plugins/ and scripts/, under a root pyproject.toml."""
    for name in ("plugins/runner/fixtures", "scripts", ".git", "packages/troupe/src",
                 "packages/troupe/tests", "packages/other"):  # fmt: skip
        (tmp_path / name).mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    return ms.Unit("troupe", "packages/troupe/src", "packages/troupe/tests", "unit")


class LinkRecorder(Recorder):
    """What a test counting one directory too many from inside mutmut's copy finds (#332)."""

    def __call__(self, command: list[str], cwd: Path, timeout: float) -> int:
        packages = cwd.parent
        self.seen = {
            "plugins": (packages / "plugins" / "runner" / "fixtures").is_dir(),
            "packages": (packages / "packages" / "troupe" / "src").is_dir(),
            "pyproject": (packages / "pyproject.toml").is_file(),
            "git": (packages / ".git").exists(),
            "own": not (packages / "troupe").is_symlink() and not (packages / "other").is_symlink(),
        }
        return super().__call__(command, cwd, timeout)


class SiblingRecorder(Recorder):
    """What troupe-store-text's test_processes.py finds from inside mutmut's copy: its child's
    path is `Path(__file__).resolve().parents[2] / "troupe" / "tests"` (#343)."""

    def __call__(self, command: list[str], cwd: Path, timeout: float) -> int:
        test_file = cwd / "mutants" / "tests" / "test_processes.py"
        self.sibling = (test_file.parents[2] / "troupe" / "tests").is_dir()
        self.root = (test_file.parents[3] / "plugins" / "runner" / "fixtures").is_dir()
        self.config = (cwd / "setup.cfg").read_text(encoding="utf-8")
        return super().__call__(command, cwd, timeout)


@pytest.mark.parametrize("code", [0, 1])
def test_a_packages_run_finds_its_sibling_packages_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    package_checkout(tmp_path)
    for name in ("packages/troupe-store-text/src", "packages/troupe-store-text/tests"):
        (tmp_path / name).mkdir(parents=True)
    unit = ms.Unit(
        "troupe-store-text",
        "packages/troupe-store-text/src",
        "packages/troupe-store-text/tests",
        "unit",
    )
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    recorder = SiblingRecorder(code)
    if code:
        with pytest.raises(run.RunError):
            run.run_mutmut(tmp_path, unit, [], 1e12, recorder, children=2, memory_mb=None)
    else:
        fake_show(monkeypatch)
        run.run_mutmut(tmp_path, unit, [], 1e12, recorder, children=2, memory_mb=None)
    assert recorder.sibling, "a test counting up to packages/ didn't find its sibling package"
    assert recorder.root, "a test counting up to the root no longer finds the checkout's files"
    also_copy = recorder.config.split("also_copy=", 1)[1].split()
    assert not {"troupe", "other", "troupe-store-text"} & set(also_copy), also_copy
    links = [p for p in (tmp_path / "packages").rglob("*") if p.is_symlink()]
    assert links == [], links


@pytest.mark.parametrize("code", [0, 1])
def test_a_packages_run_finds_the_checkouts_files_from_one_level_up_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    unit = package_checkout(tmp_path)
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    recorder = LinkRecorder(code)
    if code:
        with pytest.raises(run.RunError):
            run.run_mutmut(tmp_path, unit, [], 1e12, recorder, children=2, memory_mb=None)
    else:
        fake_show(monkeypatch)
        run.run_mutmut(tmp_path, unit, [], 1e12, recorder, children=2, memory_mb=None)
    assert recorder.seen == {
        "plugins": True, "packages": True, "pyproject": True, "git": False, "own": True,
    }  # fmt: skip
    assert sorted(p.name for p in (tmp_path / "packages").iterdir()) == ["other", "troupe"]


def write_addopts(tmp_path: Path, addopts: str) -> None:
    text = f"[tool.pytest.ini_options]\naddopts = {addopts}\n"
    (tmp_path / "pyproject.toml").write_text(text, encoding="utf-8")


def test_a_run_keeps_the_repositorys_pytest_options_but_those_the_copy_cant_honour(
    tmp_path: Path,
) -> None:
    """troupe's own plugins load; strict markers and the guard's tag plugin, which finds its
    declarations from the repository's root, don't (#332)."""
    unit = package_checkout(tmp_path)
    write_addopts(
        tmp_path,
        '["-ra", "--strict-markers", "--strict-config", "-p", "protocol_guard", '
        '"-p", "guard_pytest", "-p", "gitrepo"]',
    )
    config = run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=2)
    assert "\n    addopts=-ra --strict-config -p protocol_guard -p gitrepo\n" in config


def test_addopts_as_one_string_is_split_as_pytest_splits_it(tmp_path: Path) -> None:
    unit = package_checkout(tmp_path)
    write_addopts(tmp_path, "\"-ra --strict-markers -p guard_pytest -k 'a or b'\"")
    config = run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=2)
    assert "\n    addopts=-ra -k 'a or b'\n" in config


def test_the_joined_plugin_form_is_left_out_too(tmp_path: Path) -> None:
    unit = package_checkout(tmp_path)
    write_addopts(tmp_path, '["-ra", "-pguard_pytest", "-pgitrepo"]')
    config = run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=2)
    assert "\n    addopts=-ra -pgitrepo\n" in config


def test_no_addopts_gives_ra(tmp_path: Path) -> None:
    unit = package_checkout(tmp_path)
    config = run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=2)
    assert "\n    addopts=-ra\n" in config


def test_a_pyproject_that_isnt_toml_is_refused_naming_it(tmp_path: Path) -> None:
    unit = package_checkout(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[tool.pytest\n", encoding="utf-8")
    with pytest.raises(run.RunError, match=r"pyproject.toml isn't valid TOML"):
        run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=2)


def test_links_made_before_a_failed_link_are_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unit = package_checkout(tmp_path)
    real = Path.symlink_to
    made: list[Path] = []

    def second_fails(self: Path, target: Path | str, target_is_directory: bool = False) -> None:
        if made:
            raise OSError("no room for a link")
        real(self, target, target_is_directory)
        made.append(self)

    monkeypatch.setattr(Path, "symlink_to", second_fails)
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    with pytest.raises(OSError, match="no room for a link"):
        run.run_mutmut(tmp_path, unit, [], 1e12, Recorder(), children=2, memory_mb=None)
    assert made
    assert not any(link.is_symlink() for link in made)
    assert sorted(p.name for p in (tmp_path / "packages").iterdir()) == ["other", "troupe"]


def test_addopts_of_another_type_is_refused_naming_it(tmp_path: Path) -> None:
    unit = package_checkout(tmp_path)
    write_addopts(tmp_path, "3")
    with pytest.raises(run.RunError, match=r"pyproject.toml's addopts is 3; it must be"):
        run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=2)


def test_a_units_own_setup_cfg_is_refused_word_for_word(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "setup.cfg").write_text("[x]\n", encoding="utf-8")
    with pytest.raises(run.RunError) as raised:
        run.run_mutmut(
            tmp_path,
            SETTINGS.repositories["infrastructure"].units[0],
            [],
            1e12,
            Recorder(),
            children=2,
            memory_mb=None,
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
        ms.Unit("a", "packages/a/src", "packages/a/tests", "unit"),
        ms.Unit("b", "packages/b/src", "packages/b/tests", "unit"),
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
        ms.Unit("a", "packages/a/src", "packages/a/tests", "unit"),
        ms.Unit("b", "packages/b/src", "packages/b/tests", "unit"),
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
    # The committer too, not only the author: a fresh runner has no git identity of its own.
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
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
        capsys.readouterr().out == "memory: scripts no peaks recorded\n"
        f"mutation_run: 1 modules from infrastructure, written to {out}\n"
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


@pytest.mark.parametrize(
    ("mutant", "own_session"),
    [
        ("troupe.core.x_f__mutmut_3", True),
        ("stats", False),
        ("", False),
        ("fail", False),
        ("list_all_tests", False),
        ("none.none", False),
    ],
)
def test_only_a_mutants_test_process_starts_its_own_session(
    monkeypatch: pytest.MonkeyPatch, mutant: str, own_session: bool
) -> None:
    """A mutant that signals its own process group then ends only itself (#341, design D1).
    mutmut's stats, clean and listing passes run in its own process, which stays where it is."""
    import mutation_children as children

    calls: list[str] = []
    monkeypatch.setattr(subprocess.Popen, "__init__", subprocess.Popen.__init__)
    monkeypatch.setattr(os, "setsid", lambda: calls.append("setsid"))
    monkeypatch.setenv("MUTANT_UNDER_TEST", mutant)
    children.pytest_configure(object())
    assert calls == (["setsid"] if own_session else [])


PEAKS = """\
mutmut 1468004 412300
mutmut 1500000 450000
m.a__mutmut_1 1600000 300000
m.a__mutmut_2 1610000 310000
m.a__mutmut_3 5818044 5175188
m.a__mutmut_4 1620000 320000
m.a__mutmut_5 1500000 300000
m.a__mutmut_6 1400000 290000
not a line
m.a__mutmut_7 x 1
"""


def test_a_units_peaks_are_logged_largest_first_in_megabytes() -> None:
    """What sets the cap: mutmut's own peak, which every mutant's process starts from, and the
    largest mutant processes, by name, so a runaway stands out from the ordinary ones (D3, D4)."""
    assert run.memory_lines("troupe", PEAKS) == [
        "memory: troupe mutmut VmPeak=1465 MB VmHWM=439 MB",
        "memory: troupe mutant m.a__mutmut_3 VmPeak=5682 MB VmHWM=5054 MB",
        "memory: troupe mutant m.a__mutmut_4 VmPeak=1582 MB VmHWM=313 MB",
        "memory: troupe mutant m.a__mutmut_2 VmPeak=1572 MB VmHWM=303 MB",
        "memory: troupe mutant m.a__mutmut_1 VmPeak=1563 MB VmHWM=293 MB",
        "memory: troupe mutant m.a__mutmut_5 VmPeak=1465 MB VmHWM=293 MB",
        "memory: troupe 8 processes recorded (2 malformed lines skipped)",
    ]


@pytest.mark.parametrize("text", ["", None])
def test_a_unit_with_no_peaks_says_so(text: str | None) -> None:
    assert run.memory_lines("troupe", text) == ["memory: troupe no peaks recorded"]


def test_a_unit_whose_run_fails_still_logs_its_peaks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A run that stops is when the peaks matter most: the runaway's dry run never finished."""

    class PeakingMutmut(Recorder):
        def __call__(self, command: list[str], cwd: Path, timeout: float) -> int:
            super().__call__(command, cwd, timeout)
            (cwd / "_mutation_children_peaks.log").write_text("mutmut 1048576 524288\n")
            return 3

    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(run, "mutmut_bin", lambda: "mutmut")
    unit = SETTINGS.repositories["infrastructure"].units[0]
    with pytest.raises(run.RunError):
        run.run_mutmut(tmp_path, unit, [], 1e12, PeakingMutmut(), children=2, memory_mb=None)
    out = capsys.readouterr().out
    assert "memory: scripts mutmut VmPeak=1024 MB VmHWM=512 MB\n" in out
    assert not (tmp_path / "_mutation_children_peaks.log").exists()


GROUP_KILL = """
import os, signal, sys
sys.path.insert(0, sys.argv[1])
pid = os.fork()
if pid == 0:
    if sys.argv[2] == "hook":
        os.environ["MUTANT_UNDER_TEST"] = "troupe.core.x_f__mutmut_3"
        import mutation_children
        mutation_children.pytest_configure(object())
    os.killpg(0, signal.SIGKILL)  # what a mutant of troupe's _kill_group can do
    os._exit(0)
_, status = os.waitpid(pid, 0)
print("survived", -os.WTERMSIG(status) if os.WIFSIGNALED(status) else os.WEXITSTATUS(status))
"""


def group_kill(hook: str) -> subprocess.CompletedProcess[str]:
    """The script runs in a fresh session of its own, so a kill the plugin didn't contain ends
    only that script, never this test process."""
    return subprocess.run(
        [sys.executable, "-c", GROUP_KILL, str(Path(run.__file__).parent), hook],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        start_new_session=True,
    )


@pytest.mark.skipif(not hasattr(os, "setsid"), reason="POSIX sessions only")
def test_a_mutant_that_kills_its_own_process_group_kills_only_itself() -> None:
    control = group_kill("none")
    if control.stdout.strip() == "survived -9":
        # macOS spares the killer's parent; Linux, where the runner was lost (#341), doesn't.
        pytest.skip(
            "this OS doesn't deliver a group kill to the sender's parent: CI's Linux checks it"
        )
    assert control.returncode == -9, (control.returncode, control.stdout, control.stderr)
    done = group_kill("hook")
    assert done.stdout.strip() == "survived -9", (done.returncode, done.stdout, done.stderr)


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
