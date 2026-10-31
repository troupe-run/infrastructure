# Proposal

Issue: #236. It arose from #230's re-sort of the milestones.

## Why

0.1.0's description in `tofu/milestones.json` ends "Installed with uv from a tag", but there's no tag before 0.1.0 is
cut. troupe-run/troupe#189 does the work that doesn't need a tag in 0.1.0, and switching the documented install to
the real tag comes after the release, in troupe-run/troupe#208 (owner, 2026-10-31, in #230). The description should
say what's true when 0.1.0 is cut.

## What Changes

- **0.1.0's description ends "Installed with uv"**, with "from a tag" dropped. The rest of the sentence, and every
  other milestone, stays as it is.
- **The apply updates the description in place** on milestone 0.1.0 in each of the four managed repositories
  (troupe, infrastructure, website and `.github`), and nothing else.
- **troupe.run/status/ shows the new wording.** The merge dispatches the website's deploy (spec: milestones, "A change
  to the milestones rebuilds troupe.run"), and the page is checked once that deploy and the apply have both run.

Out of scope:

- Switching the documented install to the tag. That's troupe-run/troupe#208, after 0.1.0 is cut.
- Which issues are in 0.1.0. #230 did the re-sort.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The milestones spec already covers a changed description ("A declared description changes"), and no
requirement says what a description reads, so `.openspec.yaml` sets `skip_specs: true`.

## Impact

- `tofu/milestones.json`: one line, 0.1.0's `description`.
- GitHub, after the owner approves the plan: four milestones updated in place, one in each managed repository, with
  only the description changed. Nothing created, destroyed or replaced, and no issue changes milestone.
- troupe.run/status/: shows "Installed with uv" after the dispatched deploy. It shows "Installed with uv from a tag"
  today.
- #236 is closed by this change's pull request.
