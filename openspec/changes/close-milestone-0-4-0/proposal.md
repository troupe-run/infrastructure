# Proposal

Issue: #423.

## Why

troupe 0.4.0 ("Gates") is being released. troupe-run/troupe#533 released troupe 0.4.0 and protocol 0.4.0 (merged
2026-11-27 02:47Z, "Creating 2 releases"), after troupe-run/troupe#536 took changelogs out of troupe's size gate.
troupe-run/troupe#539 pinned troupe 0.4.0 in the bundle, and troupe-run/troupe#541 releases `troupe-run-v0.4.0`. 0.4.0
has no open issues in troupe, infrastructure, website or `.github`. The org's guide says what happens next ("When a
milestone closes", #226, #229): a pull request closes the milestone, its plan lists every open issue with no
milestone, and each of those gets an outcome so none is forgotten. 0.3.0 was closed the same way (#401, #403, change
`2026-11-25-close-milestone-0-3-0`). This change's pull request opens once `troupe-run-v0.4.0`'s install check has
passed on all twelve platform and Python legs.

## What Changes

- **0.4.0's `state` becomes `closed`** in `tofu/milestones.json`. That's the entry with key `0.3.0` and title `0.4.0`
  (the renumbering for troupe#139 moved the titles, #128). Anything that reads the file goes by the title. Its title,
  its description and every other milestone stay as they are.
- **The apply closes milestone 0.4.0 in place** in each of the four managed repositories (troupe, infrastructure,
  website and `.github`), and nothing else. Its issues keep it (spec: milestones, "A release ships").
- **The plan lists the open issues with no milestone** for troupe, infrastructure and website. It leaves `.github`
  out because that repository has issues turned off (spec: milestones, "A plan that closes a milestone lists the open
  issues with no milestone"). CI reads that list with a token that can see issues (#261), so CI's list is the
  evidence, compared with `gh issue list --state open --search no:milestone`.
- **The owner gives each listed issue an outcome** before the merge: into a milestone because it's now needed,
  labelled `parked` with a reason to come back, or closed as not planned. The outcomes are recorded on #423. Issues
  opened between the pull request's plan and the plan of `main` show up in the latter's list, and get an outcome
  before the apply is approved.
- **troupe.run/status/ shows 0.4.0 under its released versions** once the merge's dispatched website deploy has run
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

- `tofu/milestones.json`: one line, 0.4.0's `state`.
- GitHub, after the owner approves the plan: four milestones updated in place, one in each managed repository, with
  only `state` changed to closed. Nothing is created, destroyed or replaced, and no issue changes milestone.
- The release in progress (the lowest open milestone) becomes the one titled 0.5.0, so a Dependabot security update's
  issue gets 0.5.0 from the merge on (spec: dependency-updates). `scripts/tests/test_dependabot_issues.py` pins today's
  release in progress, and that pin moves from 0.4.0 to 0.5.0.
- troupe.run/status/: 0.4.0 moves to the released versions after the dispatched deploy.
- The drift check stays green: a closed declared milestone is still declared.
- #423 is closed by this change's pull request once the outcomes are recorded.
