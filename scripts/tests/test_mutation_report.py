"""A mutation report is read against a closed schema, and a module's score counts untested code
against it (spec: mutation-testing; lint-mutation design D3)."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from conftest import git

import mutation_report as mr

SHA = "c" * 40


def module(**overrides: object) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "killed": 10,
        "survived": 0,
        "no_tests": 0,
        "timeout": 0,
        "crashed": 0,
        "skipped": 0,
        "finished": True,
        "survivors": [],
        "crashed_mutants": [],
    }
    fields.update(overrides)
    return fields


def survivor(**overrides: object) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "name": "troupe.store.events.x_append__mutmut_3",
        "path": "packages/troupe/src/troupe/store/events.py",
        "line": 12,
        "change": "-    return a + b\n+    return a - b",
        "commit": None,
        "new": False,
    }
    fields.update(overrides)
    return fields


def crashed(**overrides: object) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "name": "troupe.platform.processes.x__kill_group__mutmut_4",
        "path": "packages/troupe/src/troupe/platform/processes.py",
        "line": 389,
        "change": "-    os.killpg(pid, signal.SIGKILL)\n+    os.killpg(0, signal.SIGKILL)",
        "exit_code": -9,
    }
    fields.update(overrides)
    return fields


def report(modules: dict[str, Any], **overrides: object) -> str:
    fields: dict[str, Any] = {
        "version": 2,
        "repository": "troupe",
        "commit": SHA,
        "previous_commit": None,
        "modules": modules,
    }
    fields.update(overrides)
    return json.dumps(fields)


def test_a_module_with_an_untested_function_scores_against_it() -> None:
    # The spec's scenario: 20 mutants, 10 killed, 4 survive, 6 in a function no test calls.
    survivors = [survivor(line=n) for n in range(1, 5)]
    loaded = mr.load_report(
        report({"m": module(killed=10, survived=4, no_tests=6, survivors=survivors)}), "troupe"
    )
    assert loaded.modules["m"].score == 50.0
    assert loaded.modules["m"].counted == 20


def test_timeouts_and_crashes_count_as_caught_and_skipped_ones_dont_count() -> None:
    loaded = mr.load_report(
        report(
            {
                "m": module(
                    killed=6,
                    timeout=2,
                    crashed=2,
                    skipped=30,
                    crashed_mutants=[crashed(), crashed(name="m.x_g__mutmut_1")],
                )
            }
        ),
        "troupe",
    )
    assert loaded.modules["m"].score == 100.0
    assert loaded.modules["m"].counted == 10


def test_a_report_round_trips() -> None:
    source = report(
        {
            "m": module(
                killed=3,
                survived=1,
                survivors=[survivor(commit="d" * 40, new=True)],
                crashed=2,
                crashed_mutants=[crashed(), crashed(name="m.x_g__mutmut_1", exit_code=None)],
            )
        }
    )
    loaded = mr.load_report(source, "troupe")
    assert mr.load_report(mr.dump_report(loaded), "troupe") == loaded


@pytest.mark.parametrize(
    ("source", "named"),
    [
        (report({"m": module(extra=1)}), "extra"),
        (report({"m": {k: v for k, v in module().items() if k != "skipped"}}), "skipped"),
        (report({"m": module(killed=-1)}), "killed"),
        (report({"m": module(survived=1, survivors=[])}), "1 survived"),
        (report({"m": module(survived=1, survivors=[survivor(line=0)])}), "line"),
        (report({"m": module(survived=1, survivors=[survivor(new="yes")])}), "new"),
        (report({}, commit="main"), "commit"),
        (report({}, version=1), "version"),
        (report({"m": module(crashed=1)}), "1 crashed"),
        (
            report({"m": {k: v for k, v in module().items() if k != "crashed_mutants"}}),
            "crashed_mutants",
        ),
        (report({"m": module(crashed=1, crashed_mutants=[crashed(exit_code="x")])}), "exit_code"),
        (report({}, repository="website"), "website"),
        (report({}, surprise=True), "surprise"),
        ("{", "JSON"),
    ],
)
def test_a_malformed_report_fails_naming_the_repository_and_the_field(
    source: str, named: str
) -> None:
    with pytest.raises(mr.ReportError, match=f"troupe's report.*{named}"):
        mr.load_report(source, "troupe")


# W: attribution (design D8)


def commit_file(repo: Path, text: str, message: str) -> str:
    (repo / "m.py").write_text(text, encoding="utf-8")
    git(repo, "add", "m.py")
    git(repo, "commit", "-q", "-m", message, "--author=Test <test@example.invalid>")
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def scratch(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    old = commit_file(repo, "a = 1\n", "old")
    new = commit_file(repo, "a = 1\nb = 2\n", "new")
    return repo, old, new


def survivor_at(line: int) -> mr.Survivor:
    return mr.Survivor(f"m.x__mutmut_{line}", "m.py", line, "-x\n+y")


def weekly(commit: str) -> mr.Report:
    one = mr.Module(1, 2, 0, 0, 0, 0, True, (survivor_at(1), survivor_at(2)))
    return mr.Report("troupe", commit, None, {"m": one})


def test_a_survivor_on_a_line_changed_since_the_last_run_is_new(tmp_path: Path) -> None:
    repo, old, new = scratch(tmp_path)
    attributed = mr.attribute(weekly(new), repo, previous=old)
    first, second = attributed.modules["m"].survivors
    assert (first.commit, first.new) == (old, False)
    assert (second.commit, second.new) == (new, True)
    assert attributed.previous_commit == old


def test_without_a_previous_run_no_survivor_is_new(tmp_path: Path) -> None:
    repo, _, new = scratch(tmp_path)
    attributed = mr.attribute(weekly(new), repo, previous=None)
    assert [s.new for s in attributed.modules["m"].survivors] == [False, False]
    assert all(s.commit for s in attributed.modules["m"].survivors)


def test_a_line_blame_cant_read_fails_naming_it(tmp_path: Path) -> None:
    repo, old, new = scratch(tmp_path)
    broken = mr.Report(
        "troupe", new, None, {"m": mr.Module(0, 1, 0, 0, 0, 0, True, (survivor_at(9),))}
    )
    with pytest.raises(mr.ReportError, match=r"m\.py:9"):
        mr.attribute(broken, repo, previous=old)


# mutmut's results (design D3). The meta file and diff are shaped as mutmut 3.8.1 writes them
# (mutation/data.py, mutation/diff_apply.py).

SOURCE = """\
import os


def add(a, b):
    return a + b


class Store:
    @property
    def size(self):
        total = 0
        return total + 1
"""


def mutmut_tree(tmp_path: Path, codes: dict[str, int | None]) -> Path:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "calc.py").write_text(SOURCE, encoding="utf-8")
    meta = tmp_path / "mutants" / "src" / "pkg" / "calc.py.meta"
    meta.parent.mkdir(parents=True)
    meta.write_text(
        json.dumps(
            {"exit_code_by_key": codes, "durations_by_key": {}, "estimated_durations_by_key": {}}
        ),
        encoding="utf-8",
    )
    return tmp_path


DIFFS = {
    "pkg.calc.x_add__mutmut_6": (
        "--- src/pkg/calc.py\n+++ src/pkg/calc.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n"
        "-    return a + b\n+    return a * b"
    ),
    "pkg.calc.x_add__mutmut_1": (
        "--- src/pkg/calc.py\n+++ src/pkg/calc.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n"
        "-    return a + b\n+    return a - b"
    ),
    "pkg.calc.xǁStoreǁsize__mutmut_2": (
        "--- src/pkg/calc.py\n+++ src/pkg/calc.py\n@@ -1,4 +1,4 @@\n @property\n def size(self):\n"
        "     total = 0\n-    return total + 1\n+    return total - 1"
    ),
}


def test_mutmut_results_become_one_module_with_counts_and_located_survivors(tmp_path: Path) -> None:
    root = mutmut_tree(
        tmp_path,
        {
            "pkg.calc.x_add__mutmut_1": 0,
            "pkg.calc.xǁStoreǁsize__mutmut_2": 0,
            "pkg.calc.x_add__mutmut_3": 1,
            "pkg.calc.x_add__mutmut_4": 33,
            "pkg.calc.x_add__mutmut_5": 36,
            "pkg.calc.x_add__mutmut_6": -11,
            "pkg.calc.x_add__mutmut_7": 34,
            "pkg.calc.x_add__mutmut_8": 35,
        },
    )
    modules = mr.from_mutmut(root, "src", DIFFS.__getitem__)
    calc = modules["pkg.calc"]
    assert (
        calc.killed,
        calc.survived,
        calc.no_tests,
        calc.timeout,
        calc.crashed,
        calc.skipped,
    ) == (1, 2, 1, 1, 1, 2)
    assert calc.finished
    add, size = sorted(calc.survivors, key=lambda s: s.line)
    assert (add.path, add.line, add.change) == (
        "src/pkg/calc.py",
        5,
        "-    return a + b\n+    return a - b",
    )
    assert size.line == 12  # from the decorator on line 9, `return` is the 4th line
    # A crash is named as a survivor is, with mutmut's exit code (#361).
    [crash] = calc.crashed_mutants
    assert (crash.name, crash.path, crash.line, crash.change, crash.exit_code) == (
        "pkg.calc.x_add__mutmut_6",
        "src/pkg/calc.py",
        5,
        "-    return a + b\n+    return a * b",
        -11,
    )


def test_a_mutant_not_yet_run_leaves_its_module_unfinished(tmp_path: Path) -> None:
    root = mutmut_tree(tmp_path, {"pkg.calc.x_add__mutmut_1": 1, "pkg.calc.x_add__mutmut_2": None})
    assert not mr.from_mutmut(root, "src", DIFFS.__getitem__)["pkg.calc"].finished


def test_a_package_init_is_named_by_its_package() -> None:
    assert (
        mr.module_name("packages/troupe/src/troupe/store/__init__.py", "packages/troupe/src")
        == "troupe.store"
    )


def test_a_real_mutmut_run_reads_back_with_every_survivor_on_its_source_line(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "mutation" / "mutmut-3.8.1"
    shutil.copytree(fixture / "mutants", tmp_path / "mutants")
    (tmp_path / "src").mkdir()
    source = (fixture / "src" / "mutation_settings.py.fixture").read_text(encoding="utf-8")
    (tmp_path / "src" / "mutation_settings.py").write_text(source, encoding="utf-8")
    shows = json.loads((fixture / "show.json").read_text(encoding="utf-8"))
    modules = mr.from_mutmut(tmp_path, "src", shows.__getitem__)
    settings = modules["mutation_settings"]
    assert (settings.killed, settings.survived, settings.counted) == (323, 58, 381)
    assert settings.score == 84.8
    lines = source.splitlines()
    for survivor in settings.survivors:
        removed = survivor.change.splitlines()[0]
        assert removed.startswith("-"), survivor.name
        assert lines[survivor.line - 1].strip() == removed[1:].strip(), survivor.name


def test_mutmut_files_under_the_tests_are_skipped(tmp_path: Path) -> None:
    root = mutmut_tree(tmp_path, {"pkg.calc.x_add__mutmut_1": 1})
    fixture = root / "mutants" / "src" / "tests" / "fixtures" / "other.py.meta"
    fixture.parent.mkdir(parents=True)
    fixture.write_text(json.dumps({"exit_code_by_key": {}}), encoding="utf-8")
    modules = mr.from_mutmut(root, "src", DIFFS.__getitem__, skip=("src/tests/",))
    assert list(modules) == ["pkg.calc"]


# Every refusal, word for word, and the reading edges (lint-mutation 6b)


def test_each_crashed_refusal_word_for_word() -> None:
    """The crashed list is held to its count as survivors are to theirs (#361)."""
    cases = {
        report({"m": module(crashed=2, crashed_mutants=[crashed()])}):
            "troupe's report: modules.m lists 1 crashed mutants but counts 2 crashed",
        report({"m": module(crashed_mutants={})}):
            "troupe's report: modules.m.crashed_mutants must be a list",
        report({}, version=1):
            "troupe's report: its version is 1; this reads version 2",
    }  # fmt: skip
    for source, message in cases.items():
        with pytest.raises(mr.ReportError) as raised:
            mr.load_report(source, "troupe")
        assert str(raised.value) == message


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("[]", "troupe's report: it isn't an object"),
        (
            report({}).replace('"modules": {}', '"modules": []'),
            "troupe's report: its modules isn't an object",
        ),
        (report({}, commit=None), "troupe's report: commit is None; it must be a full commit SHA"),
        (
            report({}, previous_commit="x"),
            "troupe's report: previous_commit is 'x'; it must be a full commit SHA",
        ),
        (report({"m": "x"}), "troupe's report: modules.m isn't an object"),
        (
            report({"m": module(killed=-1)}),
            "troupe's report: modules.m.killed is -1; it must be a whole number from 0 to 10000000",
        ),
        (
            report({"m": module(finished="yes")}),
            "troupe's report: modules.m.finished is 'yes'; it must be true or false",
        ),
        (
            report({"m": module(survivors={})}),
            "troupe's report: modules.m.survivors must be a list",
        ),
        (
            report({"m": module(survived=1, survivors=[survivor(name="")])}),
            "troupe's report: modules.m.survivors[0].name is ''; it must be a non-empty string",
        ),
        (
            report({"m": module(survived=1, survivors=[survivor(path="")])}),
            "troupe's report: modules.m.survivors[0].path is ''; it must be a non-empty string",
        ),
        (
            report({"m": module(survived=1, survivors=[survivor(line=0)])}),
            "troupe's report: modules.m.survivors[0].line is 0; "
            "it must be a whole number from 1 to 10000000",
        ),
        (
            report({"m": module(survived=1, survivors=[survivor(change="")])}),
            "troupe's report: modules.m.survivors[0].change is ''; it must be a non-empty string",
        ),
        (
            report({"m": module(survived=1, survivors=[survivor(commit="x")])}),
            "troupe's report: modules.m.survivors[0].commit is 'x'; it must be a full commit SHA",
        ),
    ],
)
def test_each_report_refusal_word_for_word(source: str, message: str) -> None:
    with pytest.raises(mr.ReportError) as raised:
        mr.load_report(source, "troupe")
    assert str(raised.value) == message


def test_a_dumped_report_is_indented_and_sorted_by_module() -> None:
    loaded = mr.load_report(report({"b": module(), "a": module()}), "troupe")
    text = mr.dump_report(loaded)
    assert text.startswith('{\n  "version": 2,\n  "repository": "troupe",')
    assert text.index('"a": {') < text.index('"b": {')


def test_a_failed_blame_names_the_line_the_commit_and_gits_reason(tmp_path: Path) -> None:
    repo, _, new = scratch(tmp_path)
    with pytest.raises(mr.ReportError) as raised:
        mr.last_changed(repo, new, "m.py", 9)
    assert str(raised.value).startswith(f"git blame of m.py:9 at {new[:12]} failed: fatal: ")


def test_a_mutants_line_counts_from_the_hunks_start() -> None:
    diff = "--- a\n+++ a\n@@ -3,4 +3,4 @@\n x\n y\n-old\n+new\n z"
    assert mr.mutated_line(diff, 10) == (14, "-old\n+new")


def test_lines_before_the_first_hunk_are_never_read_as_the_change() -> None:
    assert mr.mutated_line("-not a change\n+nor this\n@@ -1 +1 @@\n-a\n+b", 5) == (5, "-a\n+b")


def test_an_unreadable_diff_still_gives_the_survivor_a_change(tmp_path: Path) -> None:
    root = mutmut_tree(tmp_path, {"pkg.calc.x_add__mutmut_1": 0})
    [survivor] = mr.from_mutmut(root, "src", lambda name: "")["pkg.calc"].survivors
    assert (survivor.line, survivor.change) == (4, "pkg.calc.x_add__mutmut_1")


def test_a_mutant_named_unlike_mutmuts_falls_back_to_the_files_first_line(tmp_path: Path) -> None:
    root = mutmut_tree(tmp_path, {"pkg.calc.oddname": 0})
    [survivor] = mr.from_mutmut(root, "src", lambda name: "@@ -1 +1 @@\n-a\n+b")[
        "pkg.calc"
    ].survivors
    assert survivor.line == 1


def test_a_meta_file_without_its_source_is_skipped_not_fatal(tmp_path: Path) -> None:
    root = mutmut_tree(tmp_path, {"pkg.calc.x_add__mutmut_1": 1})
    orphan = root / "mutants" / "src" / "pkg" / "gone.py.meta"
    orphan.write_text(json.dumps({"exit_code_by_key": {}}), encoding="utf-8")
    later = root / "mutants" / "src" / "pkg" / "later.py.meta"
    later.write_text(
        json.dumps({"exit_code_by_key": {"pkg.later.x_f__mutmut_1": 1}}), encoding="utf-8"
    )
    (root / "src" / "pkg" / "later.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    assert sorted(mr.from_mutmut(root, "src", DIFFS.__getitem__)) == ["pkg.calc", "pkg.later"]


def test_an_unrun_mutant_leaves_the_rest_of_the_file_counted(tmp_path: Path) -> None:
    root = mutmut_tree(tmp_path, {"pkg.calc.x_add__mutmut_1": None, "pkg.calc.x_add__mutmut_2": 1})
    calc = mr.from_mutmut(root, "src", DIFFS.__getitem__)["pkg.calc"]
    assert (calc.finished, calc.killed) == (False, 1)
