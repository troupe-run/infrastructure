"""Where a survivor is placed, against mutmut 3.8.1's own diffs (#377, mutation-blame design D1).

mutmut's `show` renders a function with libcst, which attaches the comments directly above the
`def` to it, so its diff counts line 1 from the first such comment. The diffs in
fixtures/mutation/locator/diffs.json are mutmut's, made by scripts/mutation_locator_check.py; the
sources beside them are troupe's cli/config.py at 0515e2d (whose `run_flush` has `# flush` three
lines above its `def`) and a file of cases.
"""

import ast
import json
from pathlib import Path

import pytest

import mutation_locator_check as check
import mutation_pr as pr
import mutation_report as mr

pytestmark = pytest.mark.mutation

FIXTURES = Path(__file__).parent / "fixtures" / "mutation" / "locator"
DIFFS = json.loads((FIXTURES / "diffs.json").read_text(encoding="utf-8"))


def source(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("file", "mutant", "line"),
    [
        # The real case: run_flush's print("Rehearsal: ...") on 221 was placed at 224, one past the
        # end of the file, and the git blame of it lost dry run 44717818525's report.
        ("config.py.txt", "x_run_flush__mutmut_64", 221),
        ("cases.py.txt", "x_plain__mutmut_1", 7),
        ("cases.py.txt", "x_commented__mutmut_1", 12),
        ("cases.py.txt", "x_spaced__mutmut_1", 18),
        # The comment in first's body is first's, as libcst assigns it: second starts at its def.
        ("cases.py.txt", "xǁHolderǁsecond__mutmut_1", 34),
        ("cases.py.txt", "xǁHolderǁthird__mutmut_1", 40),
    ],
)
def test_each_mutant_is_placed_on_the_line_mutmut_changed(
    file: str, mutant: str, line: int
) -> None:
    text = source(file)
    start = mr.function_start(ast.parse(text), mutant.rsplit("__mutmut_", 1)[0], text.splitlines())
    assert start is not None
    assert mr.mutated_line(DIFFS[file][mutant], start)[0] == line


def test_the_checker_finds_every_fixture_mutant_placed_right() -> None:
    """The committed form of the differential check: each diff's old lines are the file's lines
    where the locator puts them (all 27,492 of troupe's mutants at 0515e2d were, in a container)."""
    for file in ("config.py.txt", "cases.py.txt"):
        text = source(file)
        tree, lines = ast.parse(text), text.splitlines()
        for mutant, diff in DIFFS[file].items():
            mangled = mutant.rsplit("__mutmut_", 1)[0]
            node = check.function_node(tree, mangled)
            start = mr.function_start(tree, mangled, lines)
            assert node is not None
            assert start is not None
            assert check.hunk_matches(diff, start, lines, node.col_offset), mutant


def test_the_checker_rejects_a_placement_a_few_lines_off() -> None:
    """A whole hunk can't match in the wrong place, as a stripped `return ExitCode.OK` could."""
    text = source("config.py.txt")
    lines = text.splitlines()
    diff = DIFFS["config.py.txt"]["x_run_flush__mutmut_64"]
    assert check.hunk_matches(diff, 205, lines, 0)
    assert not check.hunk_matches(diff, 208, lines, 0)
    assert not check.hunk_matches(diff, 202, lines, 0)


def test_a_methods_string_lines_match_as_they_stand_and_its_code_dedented() -> None:
    """mutmut renders a method dedented, but keeps a multi-line string's continuation lines as they
    stand: third's docstring line keeps its eight spaces."""
    text = source("cases.py.txt")
    diff = DIFFS["cases.py.txt"]["xǁHolderǁthird__mutmut_1"]
    assert "        over two lines." in diff
    # third has a comment above it, so mutmut's line 1 is that comment, on 36.
    assert check.hunk_matches(diff, 36, text.splitlines(), 4)
    assert not check.hunk_matches(diff, 37, text.splitlines(), 4)


def test_a_pull_requests_comment_keeps_a_survivor_on_its_changed_line(tmp_path: Path) -> None:
    """mutation-pr reports only survivors on the pull request's changed lines, so a survivor placed
    three lines late was dropped from its comment, or kept for a line it isn't on."""
    (tmp_path / "src" / "troupe" / "cli").mkdir(parents=True)
    (tmp_path / "src" / "troupe" / "cli" / "config.py").write_text(source("config.py.txt"))
    meta = tmp_path / "mutants" / "src" / "troupe" / "cli" / "config.py.meta"
    meta.parent.mkdir(parents=True)
    name = "troupe.cli.config.x_run_flush__mutmut_64"
    meta.write_text(json.dumps({"exit_code_by_key": {name: 0}}), encoding="utf-8")
    shown = {name: DIFFS["config.py.txt"]["x_run_flush__mutmut_64"]}
    modules = mr.from_mutmut(tmp_path, "src", shown.__getitem__)
    [survivor] = modules["troupe.cli.config"].survivors
    assert survivor.line == 221
    path = survivor.path
    assert pr.on_changed_lines(modules, {path: [221]}) == [survivor]
    assert pr.on_changed_lines(modules, {path: [224]}) == []
