"""The run step drives mutmut and Stryker the way the trial showed they work (spec:
mutation-testing; lint-mutation design D3, D9). The tools themselves are faked here: the real
output they're read back from is in fixtures/mutation/ (test_mutation_report.py)."""

import json
import os
from pathlib import Path

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
