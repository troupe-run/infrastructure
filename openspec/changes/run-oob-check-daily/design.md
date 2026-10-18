## Context

`scripts/oob.py` makes every read through `gh` with whatever login it's given, today the owner's. In CI, `tofu.yml`'s
`plan` job runs daily at 06:00 UTC, after CI passes on a merge, and on a manual run, in the `plan-main` environment.
That environment is limited to `main` and holds `TF_VAR_github_app_pem`, the infrastructure App's key. The `apply`
job already mints installation tokens from that key with `actions/create-github-app-token`, narrowed to named
repositories and permissions. The App's declared permissions (`oob/app-installations.json`) are actions_variables,
administration, contents, issues, members, organization_administration, pages and workflows, all write, plus metadata
read. GitHub has no API for changing an App's permissions, so they're set by hand in the App's settings, and OpenTofu
doesn't manage them.

### What each check reads, and which credential can read it

"No credentials" was probed on 2026-10-18 with unauthenticated `curl`. "Job's token" was probed on 2026-10-18
(task 3.2), after the owner's grants (D6): an installation token minted from the App's key with exactly the job's
repositories and read permissions. GitHub issued it with `issue_types`, `organization_administration`,
`organization_projects`, `administration`, `contents` and `issues` read, plus `metadata` read. `GITHUB_TOKEN` wasn't
probed: the job doesn't use it to read.

| Check | API | No credentials | Job's token |
|---|---|---|---|
| `.github` files | `GET repos/troupe-run/.github/git/trees/main` | 200 (public repository) | 200 |
| org settings (2FA) | `GET orgs/troupe-run`, field `two_factor_requirement_enabled` | 200, but the field is absent | 200, the field reads `false` |
| App installations | `GET orgs/troupe-run/installations` | 401 | **200**, against the 403 recorded on 2026-10-11 (adopt-org design D9); see below |
| issue types | `GET orgs/troupe-run/issue-types` | 401 | 200 |
| projects | GraphQL `organization.projectsV2` | 403 | 200, with the roadmap project's linked repositories |
| troupe specs → `cap:` labels | `GET repos/troupe-run/troupe/contents/openspec/specs` | 200 | 200 |
| troupe spec Purposes | `GET repos/troupe-run/troupe/contents/openspec/specs/<name>/spec.md` | 200 | read by `oob.py --ci`, no difference |
| code security configurations, defaults | `GET orgs/troupe-run/code-security/configurations` (and `/defaults`) | 401 | 200, 200 |
| code security attachment, per repository | `GET repos/troupe-run/<repo>/code-security-configuration` | 401 (all four) | 200 (all four) |
| dependency graph, per repository | `GET repos/troupe-run/<repo>/dependency-graph/sbom` | 200 (all four) | 200 (all four) |
| undeclared milestones, per repository | `GET repos/troupe-run/<repo>/milestones?state=all` | 200 (all four) | 200 (all four) |

`uv run scripts/oob.py --ci` with that token reported no unreadable check and no difference.

**The installations read.** It returned 200 to the job's token, listing all four installations (`total_count` 4:
`dco`, `troupe-run-infrastructure`, `troupe-run-release`, `troupe-run-board`), each with its repository selection and
full permissions, the same as the owner's login sees. A full `uv run scripts/oob.py` with that token, App
installations included, found only `troupe-run-board` undeclared, which #59's change declares. So the 403 that
adopt-org design D9 recorded on 2026-10-11 doesn't hold for this token. Which repositories each App covers is still
unreadable to any token, and stays hand-confirmed (spec: teams-and-access).

## Goals / Non-Goals

**Goals:**
- Every check CI can read runs whenever `main` is planned, daily included, and a difference fails a run the owner
  sees.
- A read that fails, or a value the credential can't see, is an error that names the check. It's never "no
  difference", and never a difference.
- What CI doesn't check is stated on every run, never silently left out.

**Non-Goals:**
- Fixing drift automatically. `oob.py` stays read-only, so its token gets no write permission.
- Reading which repositories each App is installed on. No token can (2026-10-11), and the README's hand-confirmed
  table stays.
- A separate read-only App. One was tried for PR plans and the owner chose to leave it (2026-10-12).
- Running `oob.py` on pull requests. A pull request's run holds no key without the owner's approval, and a pull
  request that edits `oob/` gets the manual run quoted in its description, as today.

## Decisions

### D1. A separate `oob` job in `tofu.yml`, in `plan-main`, whenever main is planned

The job's `if` is the `plan` job's `if`, so it runs on `schedule`, on `workflow_dispatch` on `main`, and after CI
passes on `main`. It runs in the `plan-main` environment (`deployment: false`). It doesn't need the plan, and the plan
doesn't need it. `plan-main` already limits the App's key to `main` without asking for approval, which is what a
daily read needs. "Only main can apply" (spec: ci-apply) is unchanged. Running after a merge means a merged change to
`oob/` that GitHub doesn't match yet shows up straight away, not the next morning.

*Alternatives:* running only on `schedule` and `workflow_dispatch`. That's what the first draft of this design said,
and it's closer to the issue's "alongside the 06:00 UTC plan". It was dropped because it leaves a merged `oob/` change
unchecked for up to a day, and the extra reads cost nothing. A step inside `plan` would let an oob failure stop the
plan (or the reverse), and would mix the plan's summary with this one. A new environment would be one more copy of
the key to rotate for no gain. A separate workflow file would duplicate the triggers and the environment wiring.

### D2. A read-only token minted for the job

`actions/create-github-app-token` with `owner: troupe-run` and the four managed repositories. The job sets a
`permission-*: read` input only for what the table needs: contents, issues, administration, organization
administration, issue types and organization projects. GitHub issues a token with exactly those permissions, so the
job can't write even though the App can. `oob.py` reads the token through `GH_TOKEN`. The job's `permissions:` is
`contents: read`.

The action's inputs (v3.2.0, and v3.3.0 the latest) include `permission-organization-projects` but nothing for issue
types. GitHub's "permissions required for GitHub Apps" page says `GET /orgs/{org}/issue-types` needs the organization
"Issue Types" permission (read), and its OpenAPI `app-permissions` schema doesn't list that permission yet. The
action doesn't limit itself to its declared inputs: `lib/get-permissions-from-inputs.js` turns every
`INPUT_PERMISSION-*` variable into a key of the token request (`permission-issue-types` → `issue_types`). So the job
passes `permission-issue-types: read`, and the runner warns "Unexpected input". Task 3.2 confirms that GitHub
accepts `issue_types` and that the token reads issue types. If it doesn't, issue types goes in `BY_HAND` rather than
the token being widened.

*Alternative:* `GITHUB_TOKEN` alone. It can read only the public-repository checks, and none of the code security
ones that motivated #62.

### D3. Every unreadable value is an `UnreadableError` naming the check

Today:
- the dependency-graph and milestones reads wrap a failure in `UnreadableError`;
- every other read lets `subprocess.CalledProcessError` escape as a traceback, which exits 1 but doesn't say which
  check failed or that its state is unknown;
- a field the credential can't see comes back `null`. The 2FA setting reads `null` without the owner's login, and
  `differences` reports that as a difference ("is None on GitHub, declared False"), which is wrong.

The change: `run` reads each check through one wrapper that turns any fetch failure into `UnreadableError(check name,
cause)`. That covers GraphQL too: `gh api graphql` exits 1 when the answer carries `errors` (checked 2026-10-18 with
an undefined field), so the wrapper sees it as a failed read. `run` goes on with the other checks after one fails, and
`main` reports every unreadable check, so one bad read doesn't hide another.

A field GitHub hides from a reader that can't see it comes back `null`. A check whose fields GitHub hides that way
carries `null_is_unreadable`, and a declared non-null field that reads back `null` is then an `UnreadableError`, not a
difference. Today only org settings carries it (2FA is owner-only). It's not a rule for every check, because `null`
can be a real value: `oob/projects.json` declares the roadmap project's `shortDescription` as `null`, and a project
description cleared by hand reads `null` too, which is a real difference. (The first draft said "`null` is never a
declared value in `oob/`". That was wrong, and was found while implementing task 1.)

*Alternative:* letting the traceback stand. It exits non-zero, but nobody reading the run can tell a refused token
from a bug.

### D4. Which checks run only by hand is declared in `oob.py`, and `--ci` leaves them out

`oob.py`'s `BY_HAND` maps a check's name to the reason CI can't run it. Every check has a name in `CHECK_NAMES`,
the `Check`s and the four that aren't a single declaration (troupe specs, troupe label descriptions, code security,
milestones), and a test fails if a `BY_HAND` key isn't one of them. Today only App installations is in it: "no token
CI holds can read the org's installations (403, adopt-org design D9)". (A `by_hand` field on `Check` was the first
idea, but it couldn't mark the four checks that aren't `Check`s.)

`uv run scripts/oob.py` runs every check, as now. `uv run scripts/oob.py --ci` makes no read for a check in
`BY_HAND`, and names each one with its reason. Any argument other than `--ci` exits 2 with the usage, before anything
is read (rule: malformed input is an error). The reasons live in `oob.py` with the checks, in one named place, and a
test pins that App installations is in `BY_HAND`. If the probe (task 3.2) finds the App can't read
another check either, that check goes in `BY_HAND` too, and this design says so.

*Alternative:* `oob.py --skip "<check>"`, with the skip list on the workflow's `run:` line. That's the first draft's
D4. It puts the list where CI is defined, but then the reason lives somewhere else (a comment or the README), and a
test has to parse a shell line in YAML to check it.

### D5. A difference fails the job, and the summary and annotations list it

Owner's choice (#62, 2026-10-18): a failed run, not an issue. The job runs `oob.py --ci`, writes its report to
`$GITHUB_STEP_SUMMARY`, prints each difference and each unreadable check as an `::error::` annotation, and exits with
`oob.py`'s code. It needs no write permission, so it fits D2's read-only token.

**Who GitHub tells.** For a scheduled run, GitHub emails the user who last changed the workflow's `cron` line. For a
run after a merge (`workflow_run`), it emails the user whose action triggered it. In both cases it only does that if
that user's notification settings allow failed Actions runs. The `cron` line was last written by the owner (Martin
Lau, `39dc0aa`), so today the email reaches the owner. Nothing in the repository can make sure it stays that way, so:
- `oob/README.md` says the owner should keep "Actions: failed workflows only" (or broader) email notifications on,
  and that a change to the `cron` line moves the notifications to whoever makes it;
- task 3.3 checks the owner's setting with the owner before merge.

*Alternative:* the App opens or updates an issue (as website's weekly link check does, #59). That's more durable, but
it needs an issues-write token, and the App can't add the issue to the roadmap board, which every issue must be on
(it has no projects write). The owner chose the failed run.

### D6. The App gets org "Issue types: read" and "Projects: read"

Owner's choice (#62, 2026-10-18). The owner grants both in the App's settings and accepts them on the installation.
A pull request declares them in `oob/app-installations.json`, because OpenTofu can't manage an App's permissions. Both
are read-only, and they let CI check the org's issue types and the roadmap project, two of the declarations in
`oob/`. Until the owner has accepted the grants, the hand-run App-installations check reports them as declared but
missing, which is the reminder.

## Risks / Trade-offs

- [The "documented" cells are wrong. For example, org administration read might not show the 2FA field] → Task 3.2
  mints the job's exact token locally and runs `oob.py --ci` with it before merge. D3 makes a wrong guess fail
  loudly, never pass quietly. A check the App truly can't read goes in `BY_HAND` (D4).
- [GraphQL returns a partial answer, such as only public projects, with no `errors`] → The token has "Projects: read"
  (D6), so it sees private projects too. The probe confirms that the roadmap project's linked repositories read in
  full.
- [The failure email doesn't reach the owner] → D5: the `cron` author is the owner today, the README says what moves
  it, and task 3.3 checks the owner's notification setting.
- [A failure that comes back every day looks the same each time] → Accepted with the owner's choice. The summary
  names each difference, so a new one is visible next to an old one.
- [A GitHub outage fails the run] → It shows as unreadable, not as drift. The next day's run or a manual dispatch
  retries.
- [The schedule pauses after 60 days without repository activity] → It's the same workflow as the daily plan, so
  `gh workflow enable tofu.yml` restores both (README).

## Migration Plan

The owner grants D6's two permissions, then the pull request declares them and adds the job. Merging runs the job
for the first time after CI passes. No state, no apply. To roll back, revert the job. `oob.py`'s hardening stands on
its own.

This design was first drafted by an earlier session. The owner's answers to its three open questions (2026-10-18)
are in D4, D5 and D6, and its `--skip` and schedule-only choices are kept above as alternatives.
