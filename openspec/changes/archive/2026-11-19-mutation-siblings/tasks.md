# Tasks

## 1. Links at every level (design D1, D2)

- [x] 1.1 Tests first in `test_mutation_run.py`. In a fixture shaped like troupe (`packages/troupe/tests`,
      `packages/troupe-store-text/{src,tests}`, `plugins/`), while mutmut runs for `troupe-store-text`:
      - a path built as `<package>/mutants/tests/x.py`'s `parents[2] / "troupe" / "tests"` resolves to
        `packages/troupe/tests`, and the root-level reads still resolve;
      - every link is gone afterwards, after a failed run too;
      - the package's `also_copy` lists no link.
- [x] 1.2 Change `link_checkout_entries` and the package `also_copy` listing in `scripts/mutation_run.py`

## 2. Verification

- [x] 2.1 The full check passes (in the commit hook, in the orchestrator's slot, 2026-11-19)

## Workflow follow-up

- Read the pull request's plan: troupe's `mutation_run.py` updated, nothing else.
- After the merge and apply: the troupe dry run held since #341; report scores, runtime, lowest free memory and
  crashed mutants. Then #339.
