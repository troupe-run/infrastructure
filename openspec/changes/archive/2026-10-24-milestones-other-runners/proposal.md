# Proposal

Issue: #128. It's the second of two changes. #129 (`milestone-interim-titles`) goes first.

## Why

troupe-run/troupe#139's amendment of 2026-10-24 puts a new 0.2.0, "other runners", straight after 0.1.0, and moves
the old 0.2.0 to 0.13.0 up one. #129 makes the first apply: the declaration already has the final titles and the new
description, and the 13 milestones on GitHub carry interim titles, because a cycle of renames can't be applied in one
go. This change makes the second apply, which gives them their final titles, and checks the result where people see
it: the issues in each milestone, and troupe.run/status/.

## What Changes

- **The 13 interim titles are removed** from `tofu/milestones.json`. The apply renames each milestone in place, from
  its interim title to its declared one, in every managed repository (design D1).
- **The result is checked on GitHub.** In each repository the milestone titled 0.2.0 is key `0.14.0` and the one
  titled 0.3.0 is key `0.2.0`. In troupe, #56 and #162 are in 0.2.0, and what was in 0.2.0 (config by hand) is in 0.3.0
  (design D2).
- **troupe.run/status/ is rebuilt and checked.** Nothing in this repository triggers a website build when the
  milestones change, so the owner runs the website's deploy, and that gap is reported on troupe-run/troupe#139
  (design D3).

Out of scope:

- The interim-title mechanism, its checks and its probe. #129 does those.
- Renaming keys to match titles. It's a separate, deliberate migration and the owner's call (#128).
- Triggering a website build from this repository. It's reported on troupe#139, not built here.
- Moving issues between milestones. They stay in their milestone through the rename.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. #129 adds the interim-title requirement. This change only removes the interim titles, as that requirement's
"The interim titles are removed" scenario describes, so `.openspec.yaml` sets `skip_specs: true`.

## Impact

- `tofu/milestones.json`: 13 `interim_title` fields removed.
- GitHub, after the owner approves the plan: 52 milestones renamed in place (13 in each of troupe, infrastructure,
  website and `.github`), and nothing created, destroyed or replaced. No issue changes milestone.
- troupe.run/status/: no change in what it reads, since `title` was already final. It shows the new order once it's
  rebuilt.
- troupe-run/troupe#139: a comment saying the renumbering is done and that milestone changes don't rebuild the
  website.
- #128 is closed by this change's pull request.
