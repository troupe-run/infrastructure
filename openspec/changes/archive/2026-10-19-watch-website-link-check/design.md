# Design

## Context

See proposal.md (Why). What exists today:

- **website's weekly check** (`links-weekly.yml` in troupe-run/website, from website#5 and website#18) runs at
  `17 3 * * 1` and by hand. A failing run opens or comments on one "Broken external links" issue; a clean run closes
  it. A separate `board` job, in website's main-only `board` environment, adds the issue to project 1 with the
  `troupe-run-board` App's token. It finds its issue by listing every open issue and matching title and author,
  because GitHub's search API missed a bot-opened issue minutes after it was made and the next run opened a
  duplicate.
- **The org's scheduled workflows** (read 2026-10-19): website's `links-weekly.yml` and infrastructure's `tofu.yml`
  (daily plan and drift check). troupe has none. Every workflow in all three repositories is `active`.
- **The Actions API on a public repository is readable without a token.** `GET
  /repos/troupe-run/website/actions/workflows/links-weekly.yml` gave `state: active`, and `.../runs?event=schedule`
  lists the scheduled runs, both unauthenticated on 2026-10-19. The scheduled run for Monday 03:17 UTC began at 08:52,
  so a scheduled run can start hours late.
- **GitHub's workflow states** are `active`, `disabled_inactivity`, `disabled_manually`, `disabled_fork` and
  `deleted`.
- **The board App** has "Projects: read and write" on the organisation and nothing else, and is installed on no
  repository: it adds public issues without being installed on their repository (add-link-issue-to-board D6). Its key
  is in 1Password (`troupe.run/troupe-run-board`) and in website's `board` environment.
- **The drift check** (`oob.py`, in `tofu.yml`'s `drift (out of band)` job) runs daily and fails its job on a
  difference. That failure reaches the owner only by email, and only if their notification settings send failed
  Actions runs (oob/README.md).
- **`scripts/tests/test_main_only_environments.py`** keys `MAIN_ONLY` by environment name, so a second `board` can't
  be added without changing its shape.

## Goals / Non-Goals

**Goals:**
- A stopped watched workflow shows as an open issue on the board within about a day of passing its age limit.
- Nothing the watch can't read is reported as fine.
- The watch's logic is tested offline with payloads copied from the real API.

**Non-Goals:**
- Turning a stopped workflow back on (proposal).
- Finding every scheduled workflow in the org by reading each repository's workflow files. That needs a YAML parser
  or the run of every workflow, and the guard's Python is standard library only. A new scheduled workflow is watched
  by adding a line to the declaration, which the change that adds it can do.
- Watching whether a watched workflow's runs succeed. Each check reports its own failures; this watch reports only
  that it stopped running.

## Decisions

### D1. A workflow of its own, not a job in `tofu.yml` or a check in `oob.py`

The watch is `.github/workflows/schedules.yml`, scheduled daily at 12:00 UTC and runnable by hand.

- **Not an `oob.py` check.** That would reuse a daily job, but its only signal is a failed job, which reaches the
  owner by email if their settings allow. #60 asks for an issue, and an issue is on the board, where the owner looks.
  `oob.py` also compares declarations with GitHub; a stopped schedule isn't a declaration drifting.
- **Not a job in `tofu.yml`.** That workflow also runs after every merge, shares one never-cancelled concurrency
  group with the apply, and its jobs hold the infrastructure App's key. The watch needs none of that, and a separate
  file keeps its token to `issues: write`.
- **12:00 UTC** leaves room for a Monday run that starts hours late, though the 8-day limit (D3) is what absorbs that.

### D2. The watched workflows are declared as data; today, only website's check

`scripts/watched-schedules.json` holds a list of `{repository, workflow, max_age_days}`, `repository` being the name
inside troupe-run and `workflow` the file name under `.github/workflows/`. It's the one place that says what's watched
(spec: schedule-watch). The script refuses an entry with a missing, unknown or malformed field rather than skip it.

The one entry is `website`, `links-weekly.yml`, 8 days.

**Not watched: infrastructure's `tofu.yml`.** Inactivity in infrastructure turns off this watch along with it, so the
watch could only ever catch someone turning `tofu.yml` off by hand. That's cheap to add but would claim more coverage
than it gives; the line can go in later if the owner wants it.

**Alternative: one hard-coded workflow.** #60's first shape. The declaration costs little more and answers #60's
"whether to generalise" without building discovery (Non-Goals).

### D3. What counts as stopped

For each entry, two reads:

1. `GET repos/troupe-run/<repository>/actions/workflows/<workflow>` → `state`.
2. `GET repos/troupe-run/<repository>/actions/workflows/<workflow>/runs?event=schedule&per_page=1` → the newest
   scheduled run's `created_at`.

A problem is one of four kinds: `not-active` (with the state), `not-found` (404 on read 1), `never-ran` (no scheduled
run), or `too-old` (newest scheduled run older than `max_age_days`). Runs started by hand don't count: a manual run
proves nothing about the schedule, and website's check is started by hand to prove its own issue path.

8 days is one weekly interval plus a day for a late start. With a daily watch, a check that stops is reported within
about 9 days of its last run, two days after the first missed run.

**Errors are not problems.** Any other failed read (403, 5xx, a network error, a body that doesn't parse) fails the
run, naming the entry and the error, and leaves the issue alone (spec: schedule-watch). The run can't tell whether the
check is running, so it says neither.

### D4. One tracking issue in infrastructure, found by title and author

The issue is opened in troupe-run/infrastructure with the run's `GITHUB_TOKEN`, titled "Scheduled workflows stopped
running", labelled `bug`. Each run lists every open issue (`gh issue list --state open --limit 1000`) and keeps those
with that title opened by `app/github-actions`, oldest first, as website does and for website's reason.

**Alternative: open it in the stopped workflow's repository.** The issue would sit by the check it's about, but
opening it there needs a write token for that repository in an unattended job, the infrastructure App's being the only
one. One issue in the repository that runs the watch keeps the token to `GITHUB_TOKEN`, and covers several watched
workflows at once. The owner can move this if they'd rather see it on website.

| Problems found | Open tracking issue | Action |
|---|---|---|
| some | none | open it |
| some | yes, same set | nothing |
| some | yes, different set | comment |
| none | yes | close with a comment |
| none | none | nothing |

**"The same set"** compares a fingerprint: the sorted list of `(repository, workflow, kind)`, written into the body
of each issue or comment the watch posts as an HTML comment (`<!-- schedule-watch: ... -->`), and read back from the
newest one the watch posted. Ages aren't in it, so a problem growing a day older isn't a change. This keeps a daily
watch from commenting daily, which website's weekly check does.

The run fails when it found a problem, after the issue is updated (spec: schedule-watch). While a problem lasts the
run fails daily, which is what a red history should say.

### D5. The board job reuses the board App, from a `board` environment on infrastructure

As on website: the watch job hands the issue's URL to a `board` job as an output, only when it opened or commented.
The board job runs in a `board` environment on infrastructure, has `permissions: {}`, checks out nothing, checks the
URL against `^https://github\.com/troupe-run/infrastructure/issues/[0-9]+$`, mints a token with
`permission-organization-projects: write` and runs `gh project item-add 1 --owner troupe-run --url "$ISSUE_URL"`.

`tofu/board.tf` gains the environment, its `main` deployment policy and the `BOARD_APP_CLIENT_ID` variable on
infrastructure. The client ID stays one local, used by both repositories' variables. The key is the same 1Password
item, set into infrastructure's environment by the owner with the documented command (oob/README.md).

**Why split the job here, when the watch runs only this repository's code?** website splits because its check runs
npm packages. Here the reason is narrower: the key reaches only a job that makes one call. It also makes the two
workflows read alike.

**Alternative: give the infrastructure App "Projects: write".** That App administers the org; widening it for an
unattended daily job is the opposite of why the board App exists.

**`MAIN_ONLY` is keyed by `(repository module, environment)`** so `board` can be listed for both repositories. The
existing tests keep their names and assertions; one more names a deleted infrastructure `board` declaration.

### D6. Reading with `GITHUB_TOKEN`

The watch job's token has `contents: read` and `issues: write`. The watched repositories are public, and the reads
in D3 need no permission on them. If a run shows the installation token refused for another repository (to be seen
in the first proof run, tasks 5), the fallback is the read-only infrastructure App token the drift check already mints,
and this decision is updated.

**Found (2026-10-19, task 5.2):** it reads. A run in `troupe-run/infra-probe-schedule-watch` with a job token of
`contents: read, issues: write` read website's `links-weekly.yml` and its scheduled runs, and reported it running
on its schedule (run 39229499413). No fallback is needed.

### D7. A hand-started run can name one extra workflow

`workflow_dispatch` takes `extra-workflow`, in the form `troupe-run/<repository>/<workflow file>`, checked against
`^troupe-run/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+\.ya?ml$` before anything is read. It's watched for that run only, with
8 days. This proves the issue path, board included, against a throwaway `troupe-run/infra-probe-*` repository with a
disabled scheduled workflow, without stopping website's check (as website's `extra-url` does).

### D8. Script shape

`scripts/watch_schedules.py`, standard library, run with `uv run --no-project`. Pure functions take the declaration,
the API's answers and the open issues, and return problems, the issue action and the text. A thin layer calls `gh`.
Outside GitHub Actions (`GITHUB_ACTIONS` unset) it prints the results and the action it would take, and changes
nothing. Tests feed it payloads copied from the real API (a workflow, a runs page, an empty runs page, a 404) rather
than hand-written shapes. A workflow test pins the schedule, the permissions, the board job's environment and
condition, and the URL check, as `test_oob_job.py` does for the drift job.

## Risks / Trade-offs

- [If infrastructure goes 60 days without activity, the watch stops too] → Its own state commits keep it active
  today. Proposal: a reverse watch from website, as a website issue.
- [A daily failing run while a problem lasts sends a daily email, if the owner's settings send them] → That's the
  point of a red run. The fix is one command, named in the issue.
- [GitHub changes the API's shape] → A body that doesn't parse is an error (D3), so the run fails loudly rather than
  reporting all clear.
- [The board secret isn't set yet when the first issue opens] → The board job fails, visibly, and the issue still
  opens. Migration sets the secret before the proof run.
- [The fingerprint marker is edited out of the issue by hand] → The next run sees no previous set and comments once
  with the current one. Harmless.

## Migration Plan

1. Merge; the owner approves the plan, which creates infrastructure's `board` environment, its deployment policy and
   `BOARD_APP_CLIENT_ID`. Nothing else in the plan.
2. The owner sets `BOARD_APP_PRIVATE_KEY` on infrastructure's `board` environment from 1Password, and its name is
   checked.
3. Proof: create `troupe-run/infra-probe-schedule-watch` with a scheduled workflow, turn it off, and run
   `gh workflow run schedules.yml -f extra-workflow=troupe-run/infra-probe-schedule-watch/<file>`. Check the issue
   opened, the run failed and the issue's card is on the board. Run again without the input: the issue closes. Delete
   the probe repository.

**Rollback:** delete `schedules.yml`. The `board` environment on infrastructure is harmless unused; removing it is a
change to `board.tf` and `MAIN_ONLY` together, which the test enforces.
