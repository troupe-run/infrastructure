# Proposal

Issue: #244.

## Why

troupe 0.1.0 is released (2026-11-01): troupe-run/troupe#231 published `troupe-run-v0.1.0`, its install check passed
on all twelve platform and Python legs, and 0.1.0 has no open issues in troupe, infrastructure or website. The org's
guide says what happens next ("When a milestone closes", #226, #229): a pull request closes the milestone, its plan
lists every open issue with no milestone, and each of those gets an outcome so none is forgotten.

## What Changes

- **0.1.0's `state` becomes `closed`** in `tofu/milestones.json`. Its title, description and every other milestone
  stay as they are.
- **The apply closes milestone 0.1.0 in place** in each of the four managed repositories (troupe, infrastructure,
  website and `.github`), and nothing else. Its issues keep it (spec: milestones, "A release ships").
- **The plan lists the open issues with no milestone.** The pull request's plan comment and the plan of `main` list
  them for troupe, infrastructure and website, and leave `.github` out because its issues are off (spec: milestones,
  "A plan that closes a milestone lists the open issues with no milestone"). On 2026-11-01 there are 8 in troupe, 5 in
  infrastructure and 5 in website; the plan's list is the one that counts.
- **The owner gives each listed issue an outcome**, before the merge: into a milestone because it's now needed,
  labelled `parked` with a reason to come back, or closed as not planned. The outcomes are recorded on #244. Issues
  opened between the pull request's plan and the plan of `main` show up in the latter's list, and get an outcome
  before the apply is approved.
- **troupe.run/status/ shows 0.1.0 under its released versions.** The merge dispatches the website's deploy (spec:
  milestones, "A change to the milestones rebuilds troupe.run"); the page reads the milestones and the bundle's
  `troupe-run-v*` tags (troupe-run/website#82, closed). It's checked once that deploy and the apply have both run.

Out of scope:

- Carrying out each outcome where it isn't a milestone, label or close on the issue itself. Work an outcome starts
  is its own issue.
- Switching the documented install to the tag: troupe-run/troupe#208, still open. The issue names it as best done
  first, not as a dependency, so the owner chooses when to merge. Closing 0.1.0 doesn't change the install docs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The milestones spec already covers closing a release's milestone ("A release ships") and the list of issues
with no milestone that its plan shows, so `.openspec.yaml` sets `skip_specs: true`.

## Impact

- `tofu/milestones.json`: one line, 0.1.0's `state`.
- GitHub, after the owner approves the plan: four milestones updated in place, one in each managed repository, with
  only `state` changed to closed. Nothing created, destroyed or replaced, and no issue changes milestone.
- Open issues with no milestone in troupe, infrastructure and website: each gets an outcome from the owner, recorded on
  #244. Any that go into a milestone or are labelled `parked` are changed on GitHub by hand (or by an agent at the
  owner's word), not by this change's files.
- troupe.run/status/: 0.1.0 moves to the released versions after the dispatched deploy.
- The release in progress (the lowest open milestone) becomes the one titled 0.2.0, so a Dependabot security update's
  issue gets 0.2.0 from the merge on (spec: dependency-updates). `scripts/tests/test_dependabot_issues.py` pins today's
  release in progress, and moves from 0.1.0 to 0.2.0.
- The drift check stays green: a closed declared milestone is still declared.
- #244 is closed by this change's pull request once the outcomes are recorded.
