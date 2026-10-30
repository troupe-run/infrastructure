# Design

## Context

See proposal.md for why. Today:

- `org-profile/CONTRIBUTING.md` ("How issues are related", "Milestones") has both readings, including "Completed work
  always has a milestone". The org-profile spec pins only the link from the milestone rule to the "arose from" line.
- `scripts/dependabot_issues.py` finds the release in progress per repository (`read_repository`, dependabot-issues
  design D5), and `act` opens every issue with it. Relinking leaves the milestone alone.
- A Dependabot security update and a version update look the same through the API. On website, #44 (zod, alert first
  patched in 4.6.6), #46 (fast-uri) and #54 (postcss-selector-parser) were security updates. Each has a
  `dependabot/npm_and_yarn/…` branch, the `dependencies` and `javascript` labels, and a `Bump X from A to B` title, as
  a version update has. Website has 14 alerts (5 open, real fixtures for the tests). troupe and infrastructure have
  none.
- `tofu.yml`'s `plan (pull request)` job already reads troupe and website with the job's `GITHUB_TOKEN`
  (`hook_modes.py`), and puts generated Markdown sections (`checks.md`, `modes.md`) into the plan comment's head, which
  `plan_comment.py` measures with the plan. The `plan (main)` job does the same for the run summary.
- `.github` is a milestone repository with `has_issues = false` (`tofu/repositories.tf`).

## Goals / Non-Goals

**Goals:**

- Say the rule once in the guide, and have the two places that set milestones automatically (Dependabot's issues and
  the standard change's sub-issue) follow it.
- Make the release-time review impossible to miss without making it a gate.

**Non-Goals:**

- Re-sorting existing issues, Dependabot's included (#230). This change takes no milestone off any issue.
- A check that refuses a milestone on an issue that doesn't need it. "Needed" is a judgement, not a rule a check can
  read.
- Changing troupe.run's `/status/`, which reads only titles and descriptions (#226).
- A board view filtered to "no milestone". Views aren't managed as code. The list on the pull request does the job.

## Decisions

### D1. A security update is told by the repository's open Dependabot alerts (owner, 2026-10-30)

For each repository with an open Dependabot pull request, the run reads
`repos/troupe-run/<repo>/dependabot/alerts?state=open&per_page=100`, all pages. A pull request is a security update when
an open alert matches it:

- **Ecosystem:** the branch's segment mapped to the alert's ecosystem: `npm_and_yarn` → `npm`, `uv` and `pip` → `pip`,
  `github_actions` → `actions`. One map, next to `BRANCH`. A segment not in the map is an error for that repository
  (spec: an ecosystem with no known alert ecosystem). Counting it as a version update would be a guess that loses the
  milestone, so the error names the segment and the map.
- **Package:** for `pip`, both names normalised as PEP 503 does (lowercase, runs of `-_.` to `-`), since the branch says
  `uv-build` where PyPI says `uv_build`. For `actions`, case-insensitive. For `npm`, exact.
- **Version:** the alert's `security_vulnerability.first_patched_version.identifier` is at or below the pull request's
  new version, compared as dotted digits, as `_raised` already does. An alert with no patched version can't be fixed
  by any update, so it matches nothing. When the new version can't be read (a requirement range, or an unknown title),
  a matching package with a patched version counts as security. A release then waits for a bump it may not need, which
  costs less than shipping a known vulnerability.
- **A title the run can't read** (no package to match, such as a grouped update) counts as security while the
  repository has any open alert with a patched version. Found while writing the tests (apply, 2.1). The spec's first
  draft didn't cover it, and the conservative answer is the same as for a version it can't read.
- **Directory** isn't compared. An alert's `manifest_path` (`package-lock.json`) and the branch's directory are
  written differently, and the same package in two directories of one repository is rare. If it happens, the
  conservative answer (security) is the one this gives.

This also counts a version update that happens to fix an open alert, which matches the rule's purpose: a release
shouldn't ship a vulnerability it could have fixed.

Alternatives:

- **Read a marker on the pull request.** None is documented, and the three website security updates have none in
  branch, labels or title. A probe could look for one in the description, but relying on undocumented text is the
  kind of guess the run refuses to make elsewhere.
- **Dependabot's `fetch-metadata` action.** It runs on the pull request's own workflow, in each product repository,
  and does the same alert lookup. This run already holds the App's token in one place.

### D2. The App gets Dependabot alerts read

The `troupe-run-dependabot` App gains the repository permission "Dependabot alerts: read" (`vulnerability_alerts` in
the installations API). `oob/app-installations.json` declares it, so the drift check holds it both ways. The owner
changes the App's permissions in its settings and accepts the new permission on the org's installation. That's a hand
step (App permissions aren't managed as code), done before the merge, so the first run after the merge can read alerts.
Until then the drift check reports the difference, and that red is expected. The token stays unable to push, merge or
change settings: alerts read adds no write.

### D3. When the milestone is set, and that it's never taken away

- `open`: `milestone` is the release in progress for a security update, and is left out of the request for a version
  update.
- `relink`: when the new pull request is a security update and the issue has no milestone, the same PATCH that
  retitles the issue sets the milestone. Otherwise the PATCH doesn't name `milestone`, so whatever is there stays.
- Nothing else touches a milestone. A person's choice stands, and #230 does the re-sort, not the bot.

The release in progress is still looked up in every repository with work, as now (spec unchanged): a repository whose
milestone is missing fails loudly even if it has only version updates that run. Finding drift early is worth it, and
it keeps one code path.

Alerts are read in `read_repository`, after the pull requests, and only when the repository has an open Dependabot pull
request. A read failure is a `ReadError`, so that repository does nothing and the run goes on to the others (existing
D2 behaviour). The plan works out `security` per pull request, and `Action` carries it, so `describe` can say "open the
issue … in 0.1.0 (security update)" in the local dry run.

### D4. The list is made from the plan, by a new script

`scripts/milestone_review.py --plan-json plan.json --summary review.md`:

1. Reads `resource_changes` for `github_repository_milestone.release` instances whose `change.before.state` is `open`
   and `change.after.state` is `closed`. The plan is the truth about what the apply will close: it covers a pull
   request that sets `closed`, and leaves out one whose milestone is already closed on GitHub. One closing title is
   shown once, however many repositories it closes in.
2. If none closes, it writes an empty file, and the workflow's `cat` adds nothing to the comment.
3. Otherwise, for each repository in `tofu/milestones.json`'s `repositories`, it reads `repos/troupe-run/<repo>`
   (`has_issues`), then `repos/troupe-run/<repo>/issues?milestone=none&state=open&per_page=100`, all pages, and drops
   anything with a `pull_request` key. A repository with issues off is named as left out.
4. Writes a section: which milestone closes, then per repository a count and a line per issue (`#n title` linked),
   or "none", and the three outcomes, linking CONTRIBUTING's Milestones section.

Any failed read exits non-zero with the repository named (spec: never silently short). The step runs before "Post the
plan", so a failed read leaves the comment from the last good run rather than a wrong one, and the job goes red.

It reads through `gh api` with the job's `GITHUB_TOKEN` (`GH_TOKEN: ${{ github.token }}`, as `hook_modes.py`). The repos
are public, so the token reads their issues. The plan job keeps `contents: read`, with no new permission.

Titles go into Markdown, so the script escapes what Markdown would read as markup. An issue title is someone's text,
and is never run.

Alternatives:

- **Diff `tofu/milestones.json` against the base branch.** It needs the base checked out, and it would list issues
  for a milestone already closed by hand. The plan answers the question directly.
- **A CI job in `ci.yml`.** That needs no approval, but it would show in a job log nobody reads. The plan comment is
  what the owner reads before approving.
- **Fail the plan when the list isn't empty.** #226 asked for a list, not a gate. Some issues may rightly stay
  unmilestoned at release (a ticket 4 with no reason to park it), which a gate would force into a wrong outcome.

### D5. Size

The section goes in the head that `plan_comment.py` measures. At about 120 bytes a line, the 65,000-byte comment limit
holds about 500 issues alongside a plan. troupe has 4 open issues with no milestone today. If the head ever outgrew the
limit, `plan_comment.py` fails loudly (`TooLongError`). Nothing is cut silently, so no cap is added now.

### D6. The docs' wording

- CONTRIBUTING "Milestones": the rule ("would that release wait for it?"), follow-ups, Decisions, and the release
  review with its three outcomes and where the list shows. "How issues are related" keeps its structure, and its
  sentence about the milestone rule points at the follow-up rule. Org-profile's existing checks (types, links) keep
  passing.
- `docs/standard-changes.md`: the sub-issue takes the needing issue's milestone *because the needing issue waits for
  it* (it's blocked by the sub-issue). The step and checklist commands don't change.
- `docs/development-workflow.md` "Dependabot pull requests": only a security update's issue gets the release in
  progress, told by the alerts.

## Risks / Trade-offs

- [Alerts lag a new advisory: Dependabot may open the security pull request before the alert is readable] → The run
  that Dependabot's event starts could see no alert, and open the issue with no milestone. A later relink, or the
  person triaging, sets it. The never-remove rule (D3) means the fix sticks. Dependabot opens a security update in
  answer to an alert, so the alert should come first. This change doesn't probe it, because no throwaway repository
  has the App installed. The first real security update after the merge shows it.
- [The App's new permission is a hand step] → Done and checked by the owner before the merge (task 1). The drift check
  holds it from then on. Without it, every repository with a Dependabot pull request fails loudly, and nothing is
  mis-milestoned.
- [Every open Dependabot issue in 0.1.0 stays there] → By design. #230 re-sorts them.
- [A milestone closed by hand on GitHub skips the list] → The plan then reopens it, since the declaration says open,
  so no release closes without a declared close that lists the issues.

## Migration Plan

1. Owner: add "Dependabot alerts: read" to the App, accept it on the installation, and confirm with
   `gh api orgs/troupe-run/installations --jq '.installations[] | select(.app_slug=="troupe-run-dependabot") | .permissions'`.
2. Merge. The apply delivers CONTRIBUTING to `.github`. The next `dependabot-issues` run uses alerts.
3. Rollback: revert the pull request. The extra permission is harmless until removed by hand, along with the
   declaration.
