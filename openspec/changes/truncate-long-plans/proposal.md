# Proposal

## Why

The pull request's plan comment puts the plan in a `<details>` block with `head -c 60000`, to stay under GitHub's
65,536-character comment limit. A longer plan is cut silently, mid-line, and the comment doesn't say so. On #96
(2026-10-18) a two-resource plan (`scripts/guard.py` delivered to troupe and website) came to more than 60 KB: the
comment stops inside troupe's diff (it is 60,430 characters, and its closing fence lands on the cut line), so website's
resource never appears. A reader can't tell the plan is incomplete, and the part lost can be the part that matters
most: which resources change (#98).

Most of that size is file content. OpenTofu prints each delivered file's whole content, old and new: #96's 256 KB plan
covered two resources, and nearly all of it was `scripts/guard.py`, printed twice. The owner chose (2026-10-18, on
#98) to hide that content in this change too, so that long plans become rare rather than only cut well.

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
  already do for their sections. The plan's code block gets a fence longer than any run of backticks in the plan, so
  file content in it can't close the block early.
- **A file OpenTofu writes is shown by its content's hash, not its content** (owner, 2026-10-18). `content` is
  wrapped in `sensitive()` on `github_repository_file.guard` and `github_repository_file.org_profile`. The plan shows
  `~ content = (sensitive value)`. Each resource's commit message already carries the content's hash, so the plan
  still shows which content each change delivers, old → new. The content is reviewed where it already is: in the
  pull request's diff of its source in this repository.
  - Probed offline on OpenTofu 1.13.1: making a value sensitive plans no change, so turning this on makes no commit
    and reuses no commit message. `tofu show -json` keeps the value, marked sensitive, so `hook_modes.py` still reads
    it.
  - Trade-off: when a delivered file drifts in a target, the plan shows it will be restored, but not what was changed.
    The target's commit history on GitHub still shows that.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci-apply`: two new requirements.
  - A plan shown on a pull request or in the plan-of-`main` run summary is shown whole when it fits. Otherwise it is
    cut at a line, labelled as truncated, linked to the full plan, and preceded by every resource change and the
    `Plan:` line.
  - A plan identifies a file OpenTofu writes into a repository by its content's hash, never by printing the content.
    It sits here, not in `guard-delivery` or `org-profile`, so one requirement covers every file resource, including
    later ones. Those specs' "the plan shows the file returning to its source content" still holds: the resource is
    shown as being restored.

## Impact

- `.github/workflows/tofu.yml`: in `pr-plan`, a step uploads `plan.txt` as an artifact (after "The plan holds no
  key"), and "Post the plan on the pull request" builds the comment with the new script. In `plan`, "Show the plan
  for approval" does the same for the run summary.
- `tofu/guard_delivery.tf` and `tofu/org_profile.tf`: `content = sensitive(...)`. The switch plans no change.
- New `scripts/plan_comment.py` and `scripts/tests/test_plan_comment.py`; a workflow test pins that no step cuts
  `plan.txt` with `head -c` any more.
- No OpenTofu resource changes, no new secret or permission (`actions/upload-artifact` needs none beyond the run's).
  The full plan's artifact is readable by anyone who can read the run's log, which already holds the same plan.
- With file content hidden, a plan over the limit needs many resources, such as a large adoption. The cut is still
  needed for those, so it stays in scope.
