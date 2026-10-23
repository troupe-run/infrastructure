# Design: declare troupe#139's release milestones and allocate every issue to them

## Context

See proposal.md for why. What shapes the approach:

- **Live state, read 2026-10-23.** Every managed repository (troupe, infrastructure, website, `.github`) has the three
  declared milestones, all open. Their numbers differ by repository (troupe: 0.1.0 is 1, 1.0.0 is 2, 0.2.0 is 3). Issues
  are in troupe (103), infrastructure (64) and website (15). `.github` has issues turned on but none.
- **The mechanism exists.** `tofu/milestones.tf` declares `github_repository_milestone.release` for each
  (repository, key) in `tofu/milestones.json`, with `prevent_destroy`. A milestone's key never changes, so a title or
  description change is an in-place update (release-milestones design D1–D3, proved on a throwaway repository then).
  `scripts/tests/test_milestones.py` checks the repository list and that keys, titles and states are well formed.
  `scripts/oob.py` reports a title on GitHub that isn't declared. None of these needs to change.
- **Allocation isn't OpenTofu's.** The provider has no resource for an issue's milestone, and release-milestones made
  assigning issues triage, done on GitHub. #119 keeps that: apply first, then `gh issue edit`. `gh issue edit` takes
  several issues of one repository in one command, and the guard allows it (`issue edit` is a write it permits).
- **Nothing else names the milestones.** Searched 2026-10-23: troupe's, website's and `.github`'s files don't mention
  milestones or their titles (troupe's `contributing/releasing.md` says "the first release of every component is
  0.1.0", which stays true). In this repository, only `README.md`'s milestones row names them. No file tells a
  contributor what a milestone means or which one an issue goes in; the rules are only on troupe#139.
- **Plan size.** The plan touches 84 milestones. The pull request's plan comment is cut with a note and a link when it's
  too long, and every resource line and the `Plan:` line are kept (ci-apply spec), so the comment is enough evidence.

## Goals / Non-Goals

**Goals:**
- Every managed repository has #119's 21 milestones, with #119's descriptions, and no milestone is destroyed.
- Every issue in troupe, infrastructure and website is in the milestone #119 gives it, or in none.
- Whatever names the milestones still matches them.
- The allocation rules are written where issues get filed.

**Non-Goals:**
- A check that issues are in the right milestone. The owner chose to document the rules and not automate a check
  (2026-10-23).
- Due dates, zero-padded titles, or any change to the milestone mechanism, its tests or the drift check.
- Cutting troupe's 0.1.0 release, or changing troupe#89.

## Decisions

### D1. `tofu/milestones.json` holds the 21 milestones, in release order, with #119's descriptions

Each milestone's `key` equals its `title`, as today, and the three existing keys don't change. The file lists them in
release order (0.1.0 to 0.20.0, then 1.0.0) so it reads as the roadmap. The order doesn't affect the plan:
`for_each` keys on `"<repository>/<key>"`. Every state is `open`. Descriptions are #119's table, word for word.

- Not new keys for the re-described three: a new key would be a new address, so the plan would try to destroy the old
  milestone (refused by `prevent_destroy`) and create one with no issues.
- Not a due date per milestone: #119 sets none, and the decision says plans will change.

### D2. The plan must read `72 to add, 13 to change, 0 to destroy`

18 new milestones in each of 4 repositories is 72 creates. 0.1.0, 0.2.0 and 1.0.0 change only their descriptions, in 4
repositories, which is 12 in-place updates. The 13th is `.github`'s `CONTRIBUTING.md` (D6), shown as
`content = (sensitive value)`. Anything else (a destroy, a replacement, a title or state change, an import)
means the declaration is wrong, and the change stops there. The evidence is the pull request's `plan-pr` comment.

### D3. Allocate after the apply, by repository, then check every issue against #119's tables

Milestones must exist before an issue can be put in one, so allocation follows the apply on `main`. For each target
milestone, one `gh issue edit <n>... -R troupe-run/<repo> --milestone <title>` per repository; for "no milestone",
`--remove-milestone`. Then the whole of each repository's issue list is compared with the tables, not only the issues
that were edited.

The 54 moves, read from live state on 2026-10-23 against #119's tables:

**troupe (48)**

| From | To | Issues |
|---|---|---|
| 0.2.0 | 0.1.0 | #51, #55, #60, #135, #136, #137, #140, #141 |
| none | 0.1.0 | #139, #144 |
| 0.1.0 | 0.2.0 | #5 |
| 1.0.0 | 0.3.0 | #62 |
| 1.0.0 | 0.4.0 | #124 |
| 1.0.0 | 0.5.0 | #126 |
| 1.0.0 | 0.6.0 | #44, #61 |
| none | 0.6.0 | #148 |
| none | 0.7.0 | #145 |
| 1.0.0 | 0.8.0 | #125 |
| 0.1.0 | 0.9.0 | #2, #73 |
| 1.0.0 | 0.9.0 | #63, #118 |
| 0.1.0 | 0.10.0 | #14 |
| 1.0.0 | 0.10.0 | #64, #121, #122 |
| none | 0.10.0 | #143 |
| none | 0.11.0 | #146 |
| none | 0.12.0 | #147 |
| 1.0.0 | 0.13.0 | #11, #65 |
| 1.0.0 | 0.14.0 | #56 |
| 0.1.0 | 0.15.0 | #37 |
| 1.0.0 | 0.15.0 | #57, #58 |
| 1.0.0 | 0.16.0 | #8, #59, #71 |
| 1.0.0 | 0.17.0 | #38, #67, #127 |
| 0.1.0 | 0.18.0 | #13 |
| 1.0.0 | 0.18.0 | #66 |
| 1.0.0 | 0.19.0 | #12, #69 |
| 1.0.0 | 0.20.0 | #10, #68 |

The six closed issues leaving 0.1.0 (#2, #5, #13, #14, #37, #73) are Decisions that go with the work they shaped, as
#119's rules say. 1.0.0 is left empty in troupe.

**infrastructure (3):** #116 0.2.0 → 0.1.0; #103 1.0.0 → none; #119 → 0.1.0 once it's closed.

**website (3):** #30 0.2.0 → 0.1.0; #11 none → 0.1.0; #8 0.1.0 → none.

Recorded assumption: infrastructure's other open issues, #72 (DNSSEC, parked), #73 (one-list DNS read, waiting on the
provider) and #117 (scheduled workflows stopped), aren't in #119's table. They're open and not planned for a release,
so by #119's rule they have no milestone, which is where they are. The owner can change that in review.

If an issue has been opened or closed since 2026-10-23, it's placed by #119's rules (completed work goes with the work
it arose from, or 0.1.0; open unplanned work goes in none), and the pull request names it.

### D4. README's milestones row names the range, not the members

The row says "(0.1.0, 0.2.0, 1.0.0)" today. It becomes "(0.1.0 to 0.20.0, and 1.0.0; each a planned troupe release
described by what a user gets)", so the next re-plan doesn't need a README edit. The descriptions live in one place,
`tofu/milestones.json`.

### D5. Text sorting is checked and reported, not fixed

After the apply, check how the roadmap board's Milestone grouping and the issues page's milestone filter order
0.10.0–0.20.0 against 0.2.0–0.9.0. If either sorts as text, say so on troupe-run/troupe#139, as #119 asks. Titles
aren't zero-padded: that changes every title and needs the owner's say.

### D6. The org's CONTRIBUTING gets a Milestones section

`org-profile/CONTRIBUTING.md` is the guide for every repository without its own, troupe and infrastructure among them,
so that's where the rules go: a `## Milestones` section after "How work flows". It describes the rules and doesn't list
the milestones, so a re-plan doesn't need an edit there; it links to `tofu/milestones.json` for the list and to
troupe#139 for why. The text:

```markdown
## Milestones

Each milestone is a planned troupe release, and its description says what a user gets from it. Every repository
has the same milestones, so an issue anywhere is filed under the troupe release it's needed for. When a milestone's
last issue is closed, that version is released.

- **Planned work** goes in the release it's needed for.
- **Completed work** always has a milestone: the one of the work it arose from or, when nothing fits, the release
  that was in progress when it was done. That includes development process, org upkeep and flaky tests.
- **Open work that isn't planned** has no milestone. 1.0.0 holds only the stability promise.
- **A Decision** goes in the milestone of the earliest work it blocks or, when it blocks nothing, of the work it
  shaped.

Milestones may be renumbered, reordered or re-described as plans change. They're declared in
[`tofu/milestones.json`](https://github.com/troupe-run/infrastructure/blob/main/tofu/milestones.json), and
[troupe#139](https://github.com/troupe-run/troupe/issues/139) records why.
```

- Not a check: the owner chose documentation only (2026-10-23).
- Not website's own `CONTRIBUTING.md`: the owner chose one guide for every repository (2026-10-23). #120 makes the
  org guide cover website's licence, sign-off and outside-fix rules, then troupe-run/website#31 moves website's setup
  notes to its README and deletes its guide. Until then, website's contributors read its own guide, which doesn't
  mention milestones.

## Risks / Trade-offs

- **An issue edited by hand between the table and the allocation.** → D3 compares every issue with the tables after
  allocating, and lists any issue it had to place by rule.
- **A release with only fixes.** troupe's release-please bumps the minor version only for a `feat:` before 1.0, so a
  milestone whose work holds no `feat:` would be cut as a patch, not as its title. → Not this change's to solve: it's
  troupe's release process, and troupe#139 says milestones may be renumbered. Noted on the pull request for the owner.
- **The board briefly shows the old grouping.** Between the apply and the allocation, the new milestones are empty and
  1.0.0 still holds 27 troupe issues. → Allocate straight after the apply.
