# Tasks

## 1. Delivered files are left out by the gates (#333; design D1–D3)

- [ ] 1.1 Copy troupe's delivered list at 4ffa922d to `scripts/tests/fixtures/quality-gates/troupe-guard-delivery.json`
  and write the failing test from design D3 (troupe's `scripts` package, baseline 88.4, an uncovered
  `scripts/mutation_run.py`); verify it fails on the current script for that reason
- [ ] 1.2 Read `.github/guard-delivery.json` strictly (missing: nothing delivered; malformed: `GateError` naming the
  file and problem) and drop delivered paths in the coverage gate before packages are mapped; verify 1.1 passes, plus
  tests for "in no package", a missing list and each malformed shape
- [ ] 1.3 Skip delivered paths in the complexity gate; verify with a lizard test where a complex function in a
  delivered, non-excluded file passes, and the same file undelivered fails
- [ ] 1.4 Update `docs/development-workflow.md` ("The merge gates": delivered files are left out by the gates
  themselves, not by each repository's config) and the comments in `quality-gates.toml`; verify `uv run
  scripts/check.py` passes (ask the orchestrator before running it)

## 2. The size gate (#271; design D4–D7)

- [ ] 2.1 Owner sets the thresholds (D5) and the exception list's shape (D6); record the decision and its date in
  design.md, and update the spec delta and these tasks if it differs from the proposal
- [ ] 2.2 Parse an optional `[size]` table (`block_above`, `warn_above`, `exclude`, `allow`) strictly; verify config
  tests for each key's type and range, `warn_above` above `block_above`, a ceiling at or under `block_above`, and no
  table
- [ ] 2.3 Add the `size` gate: measured files (not delivered, excluded or binary), limit by allowance, fail when above
  and new or grown, note above `warn_above`, stale-entry check; verify tests on scratch git repositories for each
  spec scenario
- [ ] 2.4 Run it from `scripts/check.py` after complexity, with `--base`; verify `test_check.py` covers the step
- [ ] 2.5 Add `[size]` to infrastructure's `quality-gates.toml` with the owner's thresholds, `exclude` and
  `[size.allow]` (today's files over the limit); verify `uv run scripts/quality_gates.py size` passes on this branch
- [ ] 2.6 List the size gate in `docs/development-workflow.md` ("The merge gates" table and notes); verify the doc
  names the rule, where it runs, and the fix

## 3. Integration

- [ ] 3.1 Full `uv run scripts/check.py` passes (one heavy run, after the orchestrator says go)
- [ ] 3.2 Raise the follow-up issues on the board: troupe and website add `[size]` and drop their delivered-file
  patterns after the apply; infrastructure makes `[size]` required once both have it (D7)

## Workflow follow-up

- Draft pull request closing #333 and #271; act on Claude's review; mark ready; the owner approves the plan run.
- Archive the change on the branch before merging.
- After the merge and the apply: comment on #333 and #271 with the PR and archived change; check the cards are Done.
