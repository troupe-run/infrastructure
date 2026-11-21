# Tasks

## 1. The locator (design D1)

- [ ] 1.1 Tests first in `test_mutation_report.py`, from real cases (mutmut 3.8.1's own diffs, copied from the check):
      - `run_flush` in a fixture copy of troupe's `cli/config.py` at 0515e2d: `x_run_flush__mutmut_64`'s diff places it on
        line 221 (today 224);
      - a method with a comment above it, and a decorated function with a comment above its decorator;
      - a comment indented deeper than the `def` (the previous block's) doesn't move the start;
      - an uncommented function is unchanged.
- [ ] 1.2 `function_start` counts from the first leading comment

## 2. Attribution that can't fail the report (design D2)

- [ ] 2.1 Tests first:
      - `attribute` with one survivor whose blame fails returns every module, that survivor with no commit and not new,
        and the others attributed;
      - `mutation_run` logs the unattributed survivor and writes its report;
      - the weekly summary names unattributed survivors under one line, and has no such section when there are none.
- [ ] 2.2 `attribute` catches each survivor's failure; `mutation_issues.summary` names them

## 3. Docs and the check

- [ ] 3.1 `docs/development-workflow.md`, "Mutation testing": where a survivor's line comes from, and unattributed
      survivors
- [ ] 3.2 The full check passes (in the orchestrator's slot)

After the apply, the next troupe dry run writes its report.
