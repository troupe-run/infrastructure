# Proposal

## Why

#377: troupe's dry run https://github.com/troupe-run/infrastructure/actions/runs/44717818525 ran mutmut for about four
hours, reaching mutant 9,672. Then it lost everything: `mutation_report.attribute` ran `git blame -L 224,224` on
`packages/troupe/src/troupe/cli/config.py`, which has 223 lines, and raised. The step exited 2 and wrote no report.

Two faults, the first found from the real case:

1. **Survivors are placed on the wrong line.** mutmut 3.8.1's `show` renders a function with libcst, which attaches the
   comments directly above the `def` to it. Its diff counts line 1 from the first such comment. `function_start` counts
   from the `def` (or its first decorator). In `cli/config.py`, `run_flush` has `# flush` at 205 and the `def` at 208,
   so its survivors `x_run_flush__mutmut_64`-`66` on line 221 were placed at 224, past the end.

   A differential check against real mutmut 3.8.1 covered all of troupe's 106 source files at 0515e2d: 27,492 mutants,
   with mutant text generated in a throwaway container and no mutated code run. Today's locator placed 0 of the 1,140
   mutants in commented functions right. That's every survivor or crash in a function with a comment above it,
   misplaced silently in the weekly report and in `mutation-pr`'s comments.
2. **One survivor's attribution aborts the whole report.** Attribution, the commit that last changed a survivor's line,
   is extra information. The counts and survivors are the result, and a single failed blame threw them all away.

## What Changes

- **`function_start` matches mutmut:** it starts at the first comment of the comments directly above the `def` or its
  decorators that libcst attaches. Those are comment lines at the `def`'s indent or less, with blank lines between them
  allowed and leading blank lines skipped. In the same differential check this places all 27,492 mutants right.
- **A survivor whose `git blame` fails is left unattributed,** with no commit and not new. The run logs why, the
  weekly summary names each one as unattributed, and the report is written.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: a mutant is placed on the line mutmut changed, and a survivor that can't be attributed is named
  rather than losing the report.

## Impact

- `scripts/mutation_report.py` and `scripts/mutation_issues.py` (`mutation_report.py` is delivered to troupe), and
  their tests, with a real-case fixture copied from mutmut's own output.
- The plan updates troupe's delivered `scripts/mutation_report.py`.
