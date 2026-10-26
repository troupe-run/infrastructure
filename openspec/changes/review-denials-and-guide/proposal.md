# Name the review's permission denials, and let it read the org guide

## Why

Confirming Claude's review (#159) turned up two gaps (#161):

- **A denial can't be traced.** #157's review run 40299015647 counted 1 permission denial. The action hides its
  output, and `show_full_output` stays refused because the full output can hold what the review saw. The workflow's
  test allows no step but the action. So no run, here or in troupe or website, can say which call was refused, and
  #159 can't find the cause as it asks.
- **The prompt names a guide the review can't read.** Check 5 points at the org's contributing guide by URL. The review
  has no tool that fetches a URL, and `Read(./**)` reaches only the checkout. That's a defect whatever caused the
  denial: the review is told to check against something it can't open. The URL fetch may also be the denial itself.

## What Changes

- **A report step after the action** reads only `permission_denials` from the action's `execution_file`. It prints
  each denied call's tool name and input, escaped and cut short, as a warning annotation. With no denial it prints one
  plain line saying so. It can't fail the job. Owner's choice, 2026-10-26.
- **The test's "only the action runs" rule** becomes "the action, plus that one report step, byte for byte". Any other
  `run` step is still refused. `show_full_output` and `display_report` stay refused.
- **A second checkout of troupe-run/.github**, sparse to `CONTRIBUTING.md`, under a path inside the workspace with
  `persist-credentials: false`. The prompt's check 5 names that path instead of the URL. In infrastructure it also
  says `org-profile/CONTRIBUTING.md` is the guide's source, which a pull request may change. Owner's choice,
  2026-10-26.
- **Delivery:** `.github/workflows/claude-review.yml` changes, so the owner-approved apply delivers it again to
  **troupe and website**, the two `guard_targets`.
- **#159 stays open.** Its first reviews in troupe and website check this version, and it's closed by comment once
  they're seen. This change's pull request closes #161.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pr-review`: a new requirement that a review run names each permission denial in its log without showing its
  output, and a new requirement that the review can read the org's contributing guide from its checkout. Both are
  ADDED requirements, so no existing requirement's text grows.

## Impact

- `.github/workflows/claude-review.yml`: an `id` on the action step, the second checkout, the report step, and
  check 5 of the prompt.
- `scripts/tests/test_claude_review_workflow.py`: the step rules (one checkout of each repository, both without
  credentials; the report step pinned exactly), plus tests that run the report step's script against real execution
  files.
- New test fixtures under `scripts/tests/`: execution files captured from a real `claude -p` run, one with a denial and
  one without.
- `tofu/guard_delivery.tf` itself doesn't change. The plan after merge updates the file's content in troupe and
  website (2 changes). Before delivery, troupe's `uv run scripts/check.py` and website's
  `npx vitest run tests/unit/workflow-node-version.test.ts` run with the new file in place (claude-pr-review design
  D6).
- No secret, App permission or tool changes. The report step uses the job's existing `contents: read` token and no
  secret.
