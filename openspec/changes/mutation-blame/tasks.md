# Tasks

## 1. The locator (design D1)

- [x] 1.1 Tests first in `test_mutation_locator.py`, from real cases (mutmut 3.8.1's own diffs, copied from the check):
      - `run_flush` in a fixture copy of troupe's `cli/config.py` at 0515e2d: `x_run_flush__mutmut_64`'s diff places it
        on line 221 (today 224);
      - a method with a comment above it, and a comment followed by a blank line (mutmut 3.8.1 doesn't mutate
        decorated functions, so a comment above a decorator has no mutant to place);
      - a comment indented deeper than the `def` (the previous block's) doesn't move the start;
      - an uncommented function is unchanged.
- [x] 1.2 `function_start` counts from the first leading comment
- [x] 1.3 The differential checker is kept as `scripts/mutation_locator_check.py`: its whole-hunk matcher is tested
      here; its `check` command, run in a container over troupe's sources, places every mutant right (the numbers go
      in the design); its `diffs` command made the fixtures
- [x] 1.4 A test through mutation-pr's path: `from_mutmut` places `run_flush`'s survivor on 221, and
      `on_changed_lines` keeps it for a change on 221 (and drops it for 224)

## 2. Attribution that can't fail the report (design D2)

- [x] 2.1 Tests first:
      - `attribute` with one survivor whose blame fails returns every module, that survivor with no commit and not new,
        and the others attributed;
      - `mutation_run` logs the unattributed survivor and writes its report;
      - the weekly summary names unattributed survivors under one line, and has no such section when there are none.
- [x] 2.2 `attribute` catches each survivor's failure; `mutation_issues.summary` names them

## 3. Docs and the check

- [x] 3.1 `docs/development-workflow.md`, "Mutation testing": where a survivor's line comes from, and unattributed
      survivors
- [x] 3.2 The full check passes (in the commit hook, in the orchestrator's slot, 2026-11-21)

After the apply, the next troupe dry run writes its report.
