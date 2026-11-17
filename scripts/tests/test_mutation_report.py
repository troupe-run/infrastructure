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


def report(modules: dict[str, Any], **overrides: object) -> str:
    fields: dict[str, Any] = {
        "version": 1,
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
        report({"m": module(killed=6, timeout=2, crashed=2, skipped=30)}), "troupe"
    )
    assert loaded.modules["m"].score == 100.0
    assert loaded.modules["m"].counted == 10


def test_a_report_round_trips() -> None:
    source = report(
        {"m": module(killed=3, survived=1, survivors=[survivor(commit="d" * 40, new=True)])}
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
        (report({}, version=2), "version"),
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
