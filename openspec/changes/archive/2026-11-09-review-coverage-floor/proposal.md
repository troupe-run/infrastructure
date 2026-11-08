# Proposal

## Why

`claude review completed` fails any review that didn't read every listed file in full (#268, built in #274). On
troupe#318 it failed four of five runs, and on troupe#297 nine of eleven, each time on a review that left nothing
open. Most of those files were fixtures that hadn't changed since an earlier run read them. Getting past it now takes
the owner's bypass or paid re-runs, and that's the normal path for runner pull requests. Decision #281 (owner,
2026-11-08) makes coverage advisory with a floor until #280 and #279 land. This change builds that (#282). It's
urgent: the check is blocking runner pull requests now.

## What Changes

- `claude review completed` no longer fails because coverage is short of `complete`. It still fails in two cases:
  - **The floor.** The pull request changes at least one source or test file, and the review read none of them in
    full. That's troupe#283's failure, which #268 was raised for.
  - **Coverage `unknown`.** The measurement failed, or its outputs are missing or malformed, so nothing counts as
    read.
- Otherwise the check passes. If any listed file wasn't read in full, it passes with one `::warning` that names
  them (up to the existing 50, then "and n more"). A pull request that changes no source or test file (docs,
  OpenSpec, spec records or data only) has nothing for the floor to check, so it passes once the review completes.
- Which changed files count as source and test is decided in one named list in the coverage step. Every listed file
  counts **unless** the list marks it as data or prose: Markdown and text, JSON and recorded streams (`.json`,
  `.jsonl`, `.ndjson`), SVG, licence files, anything under `openspec/`, and anything in a `fixtures/` directory. An
  unknown kind counts as code, so the floor fails closed.
- The coverage step also outputs whether the floor is met (`code`: `none`, `read` or `unread`), and marks which
  unread files count toward it. The run's summary keeps its table, adds a column saying whether each file counts,
  and says how many source and test files were read in full.
- The prompt asks the review's summary comment to name each listed file it didn't read in full. That's what the
  review says about itself. The measured list is in the warning and the run's summary.
- The docs that describe the check say what a pass means for now, and that full blocking comes back with #280:
  `docs/development-workflow.md` ("Claude's review" and the required-checks paragraph), `CLAUDE.md`, `README.md` and
  `org-profile/CONTRIBUTING.md`.
- Tests in `scripts/tests/test_claude_review_workflow.py`: #318's runs pass with a warning, a review that read no code
  fails, `unknown` fails, a pull request with no source or test file passes, and the list's edges are covered. The
  hash pins of the coverage and `completed` steps move.

Out of scope: carrying coverage forward across runs (#280), and leaving data to tests and splitting large pull
requests (#279). #280's change turns the gate back to blocking.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pr-review`: the coverage check becomes advisory with a floor (it fails only when no changed source or test file
  was read in full, or coverage is unknown, and warns otherwise). The coverage step classifies files and reports the
  floor. The summary comment names the files it didn't read. The turn-budget scenario past the cap follows the floor.
- `development-workflow`: the workflow docs say what a passing review means while coverage is advisory, and what to
  do when the check passes with a warning or fails on the floor.

## Impact

- `.github/workflows/claude-review.yml`: the coverage step (a new `code` output, the list, the table column), the
  review job's outputs, the `completed` job's env and script, and one sentence of the prompt. The workflow is
  delivered to troupe and website, so the merge's plan shows two deliveries. The owner approves the apply, and the
  runner pull requests are unblocked after that.
- `scripts/tests/test_claude_review_workflow.py`: pins, the named-weakening cases, and the new and changed tests.
- `org-profile/CONTRIBUTING.md` is delivered to troupe-run/.github, so the same plan shows that too.
- `docs/development-workflow.md`, `CLAUDE.md` and `README.md`.
- No new secret, permission, tool or dependency. Claude's tools don't change.
