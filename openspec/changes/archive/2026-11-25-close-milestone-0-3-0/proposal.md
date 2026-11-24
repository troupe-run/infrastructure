# Proposal

Issue: #401.

## Why

troupe 0.3.0 is being released. troupe-run/troupe#491 released troupe 0.3.0, protocol 0.3.0, troupe-plugin-sdk 0.2.0,
troupe-store-text 0.2.0 and troupe-runner-anthropic 0.2.0 (merged 2026-11-24 09:23Z). troupe-run/troupe#515 pinned
them in the bundle, and troupe-run/troupe#516 releases `troupe-run-v0.3.0`. 0.3.0 has no open issues in troupe (13
closed), infrastructure, website or `.github`. The org's guide says what happens next ("When a milestone closes",
#226, #229): a pull request closes the milestone, its plan lists every open issue with no milestone, and each of those
gets an outcome so none is forgotten. 0.2.0 was closed the same way (#375, #376, change
`2026-11-20-close-milestone-0-2-0`). This change's pull request opens once `troupe-run-v0.3.0`'s install check has
passed on all twelve platform and Python legs.

## What Changes

- **0.3.0's `state` becomes `closed`** in `tofu/milestones.json`. That's the entry with key `0.2.0` and title `0.3.0`
  (the renumbering for troupe#139 moved the titles, #128); anything that reads the file goes by the title. Its title,
  description and every other milestone stay as they are.
- **The apply closes milestone 0.3.0 in place** in each of the four managed repositories (troupe, infrastructure,
  website and `.github`), and nothing else. Its issues keep it (spec: milestones, "A release ships").
- **The plan lists the open issues with no milestone** for troupe, infrastructure and website, leaving `.github` out
  because its issues are off (spec: milestones, "A plan that closes a milestone lists the open issues with no
  milestone"). CI reads that list with a token that can see issues (#261), so CI's list is the evidence, compared
  with `gh issue list --state open --search no:milestone`.
- **The owner gives each listed issue an outcome**, before the merge: into a milestone because it's now needed,
  labelled `parked` with a reason to come back, or closed as not planned. The outcomes are recorded on #401. Issues
  opened between the pull request's plan and the plan of `main` show up in the latter's list, and get an outcome
  before the apply is approved.
- **troupe.run/status/ shows 0.3.0 under its released versions**, once the merge's dispatched website deploy has run
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

- `tofu/milestones.json`: one line, 0.3.0's `state`.
- GitHub, after the owner approves the plan: four milestones updated in place, one in each managed repository, with
  only `state` changed to closed. Nothing created, destroyed or replaced, and no issue changes milestone.
- The release in progress (the lowest open milestone) becomes the one titled 0.4.0, so a Dependabot security update's
  issue gets 0.4.0 from the merge on (spec: dependency-updates). `scripts/tests/test_dependabot_issues.py` pins today's
  release in progress, and moves from 0.3.0 to 0.4.0.
- troupe.run/status/: 0.3.0 moves to the released versions after the dispatched deploy.
- The drift check stays green: a closed declared milestone is still declared.
- #401 is closed by this change's pull request once the outcomes are recorded.
