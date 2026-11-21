"""Check mutation_report's locator against mutmut itself (#377, mutation-blame design D1).

`mutation_report` places each survivor from `mutmut show`'s diff and `function_start`. Whether
that's right depends on how mutmut renders a function, which is libcst's business, so it's checked
against real mutmut rather than a reading of it. mutmut generates every mutant of the named sources
as text (`mutate_file_contents`): no mutated code runs, so this is no mutation run. Each mutant is
then diffed exactly as `mutmut show` does, located, and counted right only when the hunk's whole old
side (context and removed lines, in order) equals the file's consecutive lines there.

It needs mutmut, which this repository doesn't install, so it runs in a throwaway container, for
example over troupe's sources at a commit:

    docker run --rm --cpus 3 -v "$PWD/scripts:/infra/scripts:ro" \\
      -v "<troupe checkout>:/troupe:ro" \\
      python:3.13-slim sh -c "pip install -q mutmut==3.8.1 && \\
      python /infra/scripts/mutation_locator_check.py check /troupe/packages"

Run it again whenever `scripts/mutation.json` moves mutmut to a new version. Its other command,
`diffs <file> [<text>]`, prints mutmut's diffs for a file's mutants as JSON, which is how the
locator's test fixtures were made (scripts/tests/fixtures/mutation/locator/).
"""

import argparse
import ast
import json
import re
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mutation_report as mr  # the locator under check

HUNK = re.compile(r"^@@ -(\d+)")


def hunk_matches(diff: str, start: int, lines: Sequence[str], dedent: int) -> bool:
    """Whether the diff's old side equals `lines` from where `start` (the function's first line,
    as the locator counts it) puts the hunk. Code lines compare after removing the function's own
    `dedent` (mutmut renders a method dedented); a multi-line string's continuation lines, which
    libcst keeps as they stand, compare as they stand. Nothing compares stripped, so a common line
    such as `return None` can't match in the wrong place."""
    old: list[str] = []
    first = None
    for line in diff.splitlines():
        hunk = HUNK.match(line)
        if hunk:
            first = int(hunk.group(1))
            continue
        if first is None or line.startswith(("---", "+++")):
            continue
        if line.startswith((" ", "-")) or not line:
            old.append(line[1:])
    if first is None or not old:
        return False
    at = start + first - 1
    for offset, text in enumerate(old):
        number = at + offset
        if not 1 <= number <= len(lines):
            return False
        filed = lines[number - 1]
        dedented = filed[dedent:] if not filed[:dedent].strip() else filed
        if text not in (dedented, filed):
            return False
    return True


def function_node(tree: ast.Module, mangled: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """The function mutmut's mangled name `x_f` or `x<sep>C<sep>m` names."""
    if mangled.startswith("x_"):
        wanted, scope = mangled[2:], tree.body
    else:
        _, owner, wanted = mangled.split("ǁ")
        classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == owner]
        scope = classes[0].body if classes else []
    for node in scope:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == wanted:
            return node
    return None


def show_diffs(path: Path) -> dict[str, str]:
    """Every mutant of `path` and the diff `mutmut show` prints for it (mutmut 3.8.1's
    get_diff_for_mutant), parsing the mutated module once rather than once per mutant."""
    from difflib import unified_diff

    import libcst as cst  # type: ignore[import-not-found]
    from mutmut.mutation.diff_apply import (  # type: ignore[import-not-found]
        read_mutant_function,
        read_original_function,
    )
    from mutmut.mutation.file_mutation import (  # type: ignore[import-not-found]
        mutate_file_contents,
    )

    code = path.read_text(encoding="utf-8")
    mutated = mutate_file_contents(str(path), code)
    module = cst.parse_module(mutated.code)
    diffs: dict[str, str] = {}
    for name in mutated.mutant_names:
        orig, mutant = (
            str(cst.Module([function]).code).strip()
            for function in (
                read_original_function(module, name),
                read_mutant_function(module, name),
            )
        )
        diff = unified_diff(
            orig.split("\n"), mutant.split("\n"), fromfile=str(path), tofile=str(path), lineterm=""
        )
        diffs[str(name)] = "\n".join(diff)
    return diffs


def check_file(path: Path) -> tuple[Counter[str], list[str]]:
    """One file's mutants, each located and checked; the first misses named."""
    counts: Counter[str] = Counter()
    misses: list[str] = []
    code = path.read_text(encoding="utf-8")
    lines = code.splitlines()
    tree = ast.parse(code)
    try:
        diffs = show_diffs(path)
    except Exception as error:  # a file mutmut can't mutate has no mutant to locate
        counts["files mutmut couldn't mutate"] += 1
        misses.append(f"{path}: {type(error).__name__}")
        return counts, misses
    for name, diff in diffs.items():
        if not any(
            line.startswith("-") and not line.startswith("---") for line in diff.splitlines()
        ):
            counts["mutants with no removed line"] += 1
            continue
        mangled = name.rsplit("__mutmut_", 1)[0]
        node = function_node(tree, mangled)
        start = mr.function_start(tree, mangled, lines)
        if node is None or start is None:
            counts["mutants whose function wasn't found"] += 1
            continue
        counts["mutants"] += 1
        if hunk_matches(diff, start, lines, node.col_offset):
            counts["placed right"] += 1
        elif len(misses) < 20:
            misses.append(f"{path}: {name} placed from line {start}")
    return counts, misses


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="locate every mutant of the sources under each path")
    check.add_argument("paths", nargs="+", type=Path)
    check.add_argument("--processes", type=int, default=3)
    show = commands.add_parser("diffs", help="print mutmut's diffs for a file's mutants as JSON")
    show.add_argument("file", type=Path)
    show.add_argument("text", nargs="?", default="", help="only mutants whose name holds this")
    args = parser.parse_args(argv)
    if args.command == "diffs":
        chosen = {k: v for k, v in show_diffs(args.file).items() if args.text in k}
        print(json.dumps(chosen, indent=2, ensure_ascii=False))
        return 0
    from multiprocessing import Pool

    # A named file is checked as it is; under a directory, only package sources (src/, not tests).
    files = sorted(
        file
        for path in args.paths
        for file in ([path] if path.is_file() else path.rglob("*.py"))
        if path.is_file() or ("/src/" in str(file) and "/tests/" not in str(file))
    )
    total: Counter[str] = Counter()
    misses: list[str] = []
    with Pool(args.processes) as pool:
        for counts, found in pool.imap_unordered(check_file, files):
            total.update(counts)
            misses.extend(found)
    for key, value in sorted(total.items()):
        print(f"{key}: {value}")
    for miss in misses[:20]:
        print(f"miss: {miss}")
    return 0 if total["placed right"] == total["mutants"] else 1


if __name__ == "__main__":
    sys.exit(main())
