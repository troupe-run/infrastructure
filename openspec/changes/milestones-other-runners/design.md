# Design

## Context

By the time this change is planned, #129 (`milestone-interim-titles`) has merged and applied:

- `tofu/milestones.json` already has the final titles. Key `0.14.0` is titled 0.2.0, with "Other runners: …" as its
  description, and keys `0.2.0` to `0.13.0` are titled 0.3.0 to 0.14.0. Each of the 13 also has an `interim_title`,
  such as `0.2.0 (renumbering)`.
- On GitHub, those 13 milestones carry their interim titles in all four managed repositories. Keys `0.1.0`,
  `0.15.0` to `0.20.0` and `1.0.0` are unchanged.

Why the rename takes two applies is in #129's proposal. What's left is the second apply and the checks #128 asks for.

What troupe's two moving milestones held on 2026-10-24, before either apply, by milestone number:

- milestone 20, key `0.14.0`, becoming 0.2.0: #56 and #162, both open;
- milestone 3, key `0.2.0`, becoming 0.3.0: #5 (closed), #45, #119 and #138 (open).

Website `scripts/roadmap-lib.mjs` reads `title` and `description` from this repository's `main`, ignores other fields,
and orders by version from `title`. It doesn't read keys. The site rebuilds only on a push to website's `main` (CI,
then `deploy.yml` on `workflow_run`) or a `workflow_dispatch` of `deploy.yml`. Nothing in this repository starts
either.

## Goals / Non-Goals

**Goals:**

- One apply that leaves every managed repository with the 21 milestones under their declared titles, and every issue
  where it was.
- Evidence for each of #128's "Done when" points: the plan, the milestones' contents on GitHub, and /status/.

**Non-Goals:**

- Removing the interim-title mechanism. It stays for the next renumbering (#129 design, goals).
- Automating the website rebuild (D3).

## Decisions

### D1. Remove the interim titles, change nothing else

Only the 13 `interim_title` fields go from `tofu/milestones.json`. No title, description, state or key changes, so
the plan shows 52 updates in place, each a title change from `<version> (renumbering)` to `<version>`, and nothing
else. When this plan runs, no milestone holds any of the 13 final titles (#129 moved them all off them), so no rename
collides, in any order.

Before planning, the branch is rebased onto `main` after #129's state commit, and GitHub is checked for the interim
titles. A plan against #129's merge but not its apply would show renames from the old titles, which collide.

### D2. Check the contents by milestone number, not by title

A title only shows the rename worked. The issues show nothing was lost. For each repository, the milestones titled
0.2.0 and 0.3.0 must be the numbers that were keys `0.14.0` and `0.2.0` before (troupe: 20 and 3), and each must
hold exactly the issues listed in Context. The other three repositories' moving milestones are empty, so for them the
check is the number and the title. Every milestone's open and closed counts in all four repositories are compared with
a snapshot taken before the apply, so a move anywhere shows.

### D3. Rebuild /status/ by hand, and report the gap

/status/ reads only `title`, which has been final since #129 merged, so this change doesn't change what it shows. A
build since #129's merge already has the new order. If no website build has run since then, the owner runs the
website's deploy workflow (`gh workflow run deploy.yml -R troupe-run/website`, the site's own
`workflow_dispatch` route) and the page is checked. Running a deploy is an outward step, so it's the owner's call,
not something an agent starts.

#128 asks for the gap to be reported on troupe#139 rather than fixed: the comment says milestone changes here don't
rebuild the website, and that /status/ shows them at its next build. Making a milestone change trigger the build
would mean a cross-repository dispatch and a credential for it, which is a change of its own if the owner wants one.

## Risks / Trade-offs

- **[#129 hasn't applied when this is planned]** → D1's check before planning. The plan would show renames from the
  old titles, which is the sign.
- **[Something renamed a milestone by hand in between]** → the plan shows the extra title change, and the drift check
  reports it. The plan is read for exactly 52 title changes before the owner approves it.
- **[The apply partly fails]** → the final titles are free, so retrying renames only what's left. D2's check runs
  after the apply that completes.

## Migration Plan

1. Rebase onto `main` after #129's state commit, and check the interim titles are on GitHub.
2. Remove the interim titles, plan, open the pull request, archive, then the owner merges and approves the apply.
3. Run D2's checks, rebuild and check /status/ (D3), and comment on troupe#139 and #128.

Rollback: put the interim titles back. That plan renames the 13 back to their interim titles, which are free.
