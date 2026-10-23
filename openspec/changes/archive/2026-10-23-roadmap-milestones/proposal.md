# Proposal

Issue: #119.

## Why

troupe-run/troupe#139 decided (2026-10-23) what troupe's milestones are: each one is a planned release that describes
something a user gets, and closing its last issue means that version gets cut. It laid out 21 releases, 0.1.0 to 0.20.0
and 1.0.0, and where every issue goes. What's declared today is three milestones written before that decision: 0.1.0
still says "Walking skeleton", 0.2.0 holds work the decision moved, and 1.0.0 holds 27 open troupe issues that are
now spread over 0.2.0 to 0.20.0. So the board's Milestone grouping doesn't show the plan, and troupe's release pull
request (troupe#89) has no milestone whose last issue says when to merge it.

## What Changes

- **0.1.0, 0.2.0 and 1.0.0 are re-described in place** in `tofu/milestones.json`, with #119's descriptions. Their keys
  and titles don't change, so they keep their numbers and their issues (design D1).
- **0.3.0 to 0.20.0 are declared**, open, with #119's descriptions, so every managed repository gets all 18 of them
  (design D1).
- **Every issue in troupe, infrastructure and website is put in the milestone #119's tables give it, or in none**,
  after the apply. Assigning an issue isn't something OpenTofu manages, so this is done with `gh issue edit` and
  checked against the tables (design D3).
- **The org's CONTRIBUTING gains a Milestones section** (`org-profile/CONTRIBUTING.md`, delivered to
  `troupe-run/.github`), saying what a milestone is and where an issue goes, so the rules are where issues get filed
  (design D6; owner, 2026-10-23).
- **This repository's README** lists the milestones by range rather than naming the three (design D4).
- **The milestones spec's examples** stop using `0.3.0` as a milestone that isn't declared, since it now is, and the
  spec gains the two plans this change relies on: a description changed in place, and a milestone added (see specs).

Out of scope:

- Any check that an issue is in the right milestone. Allocation stays triage, documented but not automated (owner,
  2026-10-23).
- Making the org guide cover website, and deleting website's own guide (owner, 2026-10-23): #120, then
  troupe-run/website#31. #120 edits the same file, so it merges after this change.
- Due dates. #119 sets none.
- Zero-padding the titles. #119 says to report text sorting on troupe#139 rather than pad without asking (design D5).
- Cutting troupe's 0.1.0 release. troupe#89 stays unmerged until 0.1.0's last issue is closed, and that's troupe's work.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `milestones`: two scenarios are added to "Every listed repository has the same release milestones" (a declared
  description changes; a milestone is added), and the "made by hand" scenario's example title changes from `0.3.0`,
  which this change declares, to one that stays undeclared.

## Impact

- `tofu/milestones.json`: 3 milestones → 21; three descriptions changed.
- `README.md`: the milestones row.
- `org-profile/CONTRIBUTING.md`: a Milestones section.
- `openspec/specs/milestones/spec.md`, at archive.
- GitHub, after the owner approves the plan: 72 milestones created (18 in each of troupe, infrastructure, website and
  `.github`) and 12 re-described (3 in each), nothing destroyed, and `.github`'s `CONTRIBUTING.md` updated. Then 54 issues change milestone across the three
  repositories with issues (design D3 lists them).
- The drift check's milestone report keeps passing: every title on GitHub is declared.
- #119 is closed by this change's pull request, and goes in 0.1.0 once it's done.
