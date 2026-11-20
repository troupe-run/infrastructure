# Proposal

Issue: #375.

## Why

troupe 0.2.0 is released (2026-11-20): troupe-run/troupe#487 published `troupe-run-v0.2.0` at 08:44Z, its install
check passed on all twelve platform and Python legs, and 0.2.0 has no open issues in troupe (81 closed),
infrastructure (14) or website (6). The org's guide says what happens next ("When a milestone closes", #226, #229): a
pull request closes the milestone, its plan lists every open issue with no milestone, and each of those gets an
outcome so none is forgotten. 0.1.0 was closed the same way (#244, #245, change `2026-11-01-close-0-1-0`).

## What Changes

- **0.2.0's `state` becomes `closed`** in `tofu/milestones.json`. That's the entry with key `0.14.0` and title `0.2.0`
  (the renumbering for troupe#139 moved the title, #128); anything that reads the file goes by the title. Its title,
  description and every other milestone stay as they are.
- **The apply closes milestone 0.2.0 in place** in each of the four managed repositories (troupe, infrastructure,
  website and `.github`), and nothing else. Its issues keep it (spec: milestones, "A release ships").
- **The plan lists the open issues with no milestone** for troupe, infrastructure and website, leaving `.github` out
  because its issues are off (spec: milestones, "A plan that closes a milestone lists the open issues with no
  milestone"). Since #261 CI reads that list with a token that can see issues and fails a short read, so CI's list is
  the first real one; a local run of `scripts/milestone_review.py` is compared with it once.
- **The owner gives each listed issue an outcome**, before the merge: into a milestone because it's now needed,
  labelled `parked` with a reason to come back, or closed as not planned. The outcomes are recorded on #375. Issues
  opened between the pull request's plan and the plan of `main` show up in the latter's list, and get an outcome
  before the apply is approved.
- **troupe.run/status/ shows 0.2.0 under its released versions**, once the merge's dispatched website deploy has run
  (spec: milestones, "A change to the milestones rebuilds troupe.run").

Out of scope:

- Carrying out an outcome beyond a milestone, label or close on the issue itself. Work an outcome starts is its own
  issue.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The milestones spec already covers closing a release's milestone and the list its plan shows, so
`.openspec.yaml` sets `skip_specs: true`.

## Impact

- `tofu/milestones.json`: one line, 0.2.0's `state`.
- GitHub, after the owner approves the plan: four milestones updated in place, one in each managed repository, with
  only `state` changed to closed. Nothing created, destroyed or replaced, and no issue changes milestone.
- The release in progress (the lowest open milestone) becomes the one titled 0.3.0, so a Dependabot security update's
  issue gets 0.3.0 from the merge on (spec: dependency-updates). `scripts/tests/test_dependabot_issues.py` pins today's
  release in progress, and moves from 0.2.0 to 0.3.0.
- troupe.run/status/: 0.2.0 moves to the released versions after the dispatched deploy.
- The drift check stays green: a closed declared milestone is still declared.
- #375 is closed by this change's pull request once the outcomes are recorded.
