## Context

`mutated_line(diff, start)` turns `mutmut show`'s diff into a file line: the hunk's start, counted from `start`, plus
its context lines up to the first change. `start` comes from `function_start`, the `def`'s line or its first
decorator's. mutmut 3.8.1's `get_diff_for_mutant` renders the original and mutant functions with
`cst.Module([function]).code.strip()` and diffs them with `difflib.unified_diff`. libcst attaches the comments (and
blank lines) between a function and the statement before it to the function as its leading lines, and `.strip()`
removes only the blank lines before the first comment. So mutmut's line 1 is the first leading comment, when there is
one.

## Goals / Non-Goals

**Goals:** every mutant placed where mutmut changed it; a blame failure never loses the report.

**Non-Goals:** the run's time budget (#378); changing what attribution means.

## Decisions

### D1. Count from the first leading comment, as mutmut does

`function_start` walks up from the `def` (or its first decorator) over blank lines and comment lines at the `def`'s
indent or less, and starts at the first comment it passes. A comment indented deeper than the `def` belongs to the
previous block, as libcst assigns it, and stops the walk, as any code line does.

Checked against mutmut itself rather than a reading of libcst. The check generated the mutants of all 106 troupe source
files at 0515e2d with real mutmut 3.8.1 (`mutate_file_contents`, mutant text only), and diffed them exactly as
`get_diff_for_mutant` does. A placement counted as right only when the hunk's whole old side, context and removed lines
in order, equals the file's consecutive lines there. Code lines were compared after removing the function's indent
(mutmut renders a method dedented); a multi-line string's continuation lines were compared as they stand; nothing was
compared stripped.

| | today | this change |
|---|---|---|
| mutants in uncommented functions (26,352) | 26,352 | 26,352 |
| mutants in commented functions (1,140) | 0 | 1,140 |

Hits on a line that occurs more than once in its function: 623 today, 633 with the change, and none can be an
accidental match under the whole-hunk rule.

The checker is kept as `scripts/mutation_locator_check.py`, so the claim can be checked again whenever mutmut or libcst
moves. Run with the fixed locator, its `check` command placed all 27,492 mutants right (exit 0). It needs mutmut, which
this repository doesn't install, so it runs in a throwaway container. No mutated code runs, so it isn't a mutation run:

    docker run --rm --cpus 3 -v "$PWD/scripts:/infra/scripts:ro" -v "<troupe checkout>:/troupe:ro" \
      python:3.13-slim sh -c "pip install -q mutmut==<version> && \
      python /infra/scripts/mutation_locator_check.py check /troupe/packages"

Its matcher is tested here. Its `diffs` command printed mutmut's diffs for the test fixtures
(`scripts/tests/fixtures/mutation/locator/`): troupe's `cli/config.py` at 0515e2d and a file of cases. One test goes
through mutation-pr's path, `from_mutmut` then `on_changed_lines`, because the pull request comment keeps only
survivors on changed lines, so a misplaced survivor was dropped from it or kept for a line it isn't on.

### D2. A blame failure leaves one survivor unattributed

`attribute` catches `ReportError` from `last_changed` per survivor. That survivor keeps `commit` null and `new` false,
which the report's schema already allows, so the report's version doesn't change. The run prints
`mutation_run: <path>:<line> unattributed: <reason>`. After attribution a null commit can only mean a failed blame,
so the weekly summary lists those survivors under one line saying they couldn't be attributed. Losing four hours of
results to one survivor's attribution is the opposite of refusing to guess: nothing is guessed, and the gap is named.

## Risks / Trade-offs

- A future mutmut renders differently → the version is pinned (`scripts/mutation.json`); a change of version reruns
  `scripts/mutation_locator_check.py check`, and its `diffs` command refreshes the fixtures.
- mutmut 3.8.1 doesn't mutate decorated functions, so a comment above a decorator has no mutant to check; the locator
  still starts at it, as libcst attaches it.
