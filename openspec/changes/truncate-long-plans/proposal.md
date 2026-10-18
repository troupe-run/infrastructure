# Proposal

## Why

The pull request's plan comment puts the plan in a `<details>` block with `head -c 60000`, to stay under GitHub's
65,536-character comment limit. A longer plan is cut silently, mid-line, and the comment doesn't say so. On #96
(2026-10-18) a two-resource plan (`scripts/guard.py` delivered to troupe and website) came to more than 60 KB: the
comment stops inside troupe's diff (it is 60,430 characters, and its closing fence lands on the cut line), so website's
resource never appears. A reader can't tell the plan is incomplete, and the part lost can be the part that matters
most: which resources change (#98).

## What Changes

- **The plan is posted whole when it fits, and cut on purpose when it doesn't** (owner, #98). Before posting, the
  comment's length is checked against a limit that leaves room for the rest of the comment. A plan within it is posted
  as today, with no note.
- **Over the limit, the comment:**
  - lists every resource change (each `# … will be …` / `# … must be …` line) and the `Plan:` line in full, above
    the cut, so the summary is never what's lost;
  - cuts the plan at a line boundary, never mid-line, and closes the code block properly;
  - says the plan is truncated and how much is shown (lines and bytes shown of the total);
  - links to the full plan, uploaded as an artifact of the run.
- **A summary that can't fit is an error, not a quieter cut.** If the resource list and `Plan:` line alone don't fit,
  the step fails naming the limit, rather than dropping any of them.
- **The same applies to the plan of `main` in the run summary**, which the owner reads before approving an apply. It
  uses `head -c 900000` under GitHub's 1 MiB step-summary limit, so it has the same silent cut, at a larger size. This
  is beyond the letter of #98, and is the one scope call in this proposal: it uses the same code with a different
  limit, and the approval page is where a silently missing resource matters most. The owner can drop it from the
  change before apply.
- The rendering moves from the workflow's shell into a tested Python script, as `plan_checks.py` and `hook_modes.py`
  already do for their sections.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci-apply`: a new requirement that a plan shown on a pull request or in the plan-of-`main` run summary is shown
  whole when it fits, and otherwise cut at a line, labelled as truncated, linked to the full plan, and preceded by
  every resource change and the `Plan:` line.

## Impact

- `.github/workflows/tofu.yml`: in `pr-plan`, a step uploads `plan.txt` as an artifact (after "The plan holds no
  key"), and "Post the plan on the pull request" builds the comment with the new script. In `plan`, "Show the plan
  for approval" does the same for the run summary.
- New `scripts/plan_comment.py` and `scripts/tests/test_plan_comment.py`; a workflow test pins that no step cuts
  `plan.txt` with `head -c` any more.
- No OpenTofu resource changes, no new secret or permission (`actions/upload-artifact` needs none beyond the run's).
  The full plan's artifact is readable by anyone who can read the run's log, which already holds the same plan.
