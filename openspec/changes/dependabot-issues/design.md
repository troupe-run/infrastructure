# Design

## Context

See proposal.md for why. Section 2 of #170's design is the source. What this builds on:

- **Dependabot's pull requests today**, read 2026-10-27:
  - 9 open in website (#44 to #46, #54 to #59), 4 in troupe (#172 to #175) and 5 in infrastructure (#182 to #186).
  - Titles follow the config, `chore(deps): Bump zod from 4.6.5 to 4.6.7`, with a capital `Bump`. Some say `Update X
    requirement from <range> to <range>` (troupe #175). Some were opened before the config and start `build(deps):`
    (website #54).
  - Branches are `dependabot/<package-manager>/<dependency>-<version>`, for example
    `dependabot/npm_and_yarn/axe-core/playwright-4.14.0`. A scoped name puts a `/` inside the dependency.
  - Descriptions carry the release notes, with upstream links rewritten to `redirect.github.com`.
- **`guard` re-runs on `edited`** (`guard.yml`), and since #173 it refuses a pull request whose description closes no
  issue. `ci.yml` uses the default `pull_request` types, so an edit to the description doesn't re-run it, or
  infrastructure's `plan (pull request)`.
- **The schedule watch (`schedules.yml`, spec schedule-watch) is the pattern.** It's a scheduled workflow in
  infrastructure that reads other repositories. It acts on GitHub in a Python script with an injectable `gh` runner,
  reads only outside Actions, and adds its issue to the board in a second job with the board App's token, in the
  main-only `board` environment.
- **The Apps** (`oob/app-installations.json`): the board App has only Projects write. The infrastructure App has Issues
  write but not Pull requests, holds org administration, and its key is in the owner-approved `apply` environment. The
  release App has contents write. None fits an unattended run that edits pull requests.
- **Milestones**: every managed repository has the same titles (spec milestones), but GitHub's numbers differ between
  repositories and don't follow the version (website's `0.2.0` is number 16). `tofu/milestones.json`'s order isn't by
  version either.

GitHub behaviour this relies on, from GitHub's docs:

- Events caused by a workflow's `GITHUB_TOKEN` start no new workflow run, apart from `workflow_dispatch` and
  `repository_dispatch`. An App token's events do start them.
- A workflow started by Dependabot's `pull_request` or `push` events gets a read-only `GITHUB_TOKEN` and only
  Dependabot's secrets. A `pull_request_target` run for a Dependabot pull request is restricted the same way.

## Goals / Non-Goals

**Goals:**
- No state outside GitHub: each run works out what to do from the pull requests and the App's issues, so a run that
  dies part-way is finished by the next one.
- Nothing that writes ever holds a pull request's files.

**Non-Goals:**
- **Deciding what may merge.** The update type in the issue informs the person who picks it up. #174's exemption reads
  Dependabot's own metadata to decide.
- **Security alerts without a pull request.** An alert with no fix opens no pull request, so it gets no issue here.
- **`.github`.** It has no dependencies and no Dependabot configuration.
- **Watching this workflow's schedule.** The schedule watch exists for repositories that go quiet. infrastructure gets
  a commit after every apply, so GitHub won't turn this schedule off.

## Decisions

### D1. One scheduled workflow in infrastructure covers all three repositories

`.github/workflows/dependabot-issues.yml` runs on `schedule` (`*/10 * * * *`) and `workflow_dispatch`, in
infrastructure only, and reads troupe, website and infrastructure.

- **Why a schedule:** a schedule runs from `main`'s workflow file and gets the repository's own secrets. Nothing a
  pull request carries is in its context.
- **Why here, not a workflow delivered to each repository** (as #170 section 2 first sketched):
  - One environment and one key, in the repository whose `main` only the owner's approved changes reach. A delivered
    workflow would need the key in three environments.
  - No new delivered file, so no delivery plan, and no new path for Dependabot to leave out (#170, 5b).
  - The schedule watch already reads other repositories from here.
- *Rejected: `pull_request_target` or `workflow_run`.* A `pull_request_target` run for a Dependabot pull request gets
  no secrets, so it can't mint the App's token. Whether a `workflow_run` started by a Dependabot run gets the
  repository's secrets isn't clearly documented. Either one would also put the pull request's event in the context of
  a job that writes, which the anti-goal forbids.
- *Rejected: `GITHUB_TOKEN` in each repository.* Its edits start no workflow, so adding the closing line wouldn't
  re-run `guard`, and the pull request would stay red.
- **Latency:** GitHub often starts a scheduled run late. With a 10-minute schedule, an issue usually appears within
  about 20 minutes. Dependabot's weekly runs make updates arrive in a batch, so that's soon enough.
- `concurrency: dependabot-issues`, with `cancel-in-progress: false`, so two runs never open the same issue twice.

### D2. A script works out what to do, and acts with the App's token

`scripts/dependabot_issues.py` (standard library, with `gh` run through an injectable runner, as
`watch_schedules.py`). For each repository it reads:

- the open pull requests whose author is `dependabot[bot]`;
- the issues labelled `dependencies` that the App opened, open ones and ones closed in the last 30 days;
- each linked pull request it didn't already read, by number.

Then, per open Dependabot pull request:

1. **Its issue** is the App's issue whose marker names it. Failing that, it's the App's open issue for the same
   dependency key (D3), which is relinked. Failing that, a new issue.
2. **A closed issue for an open pull request is reopened** (spec: a reopened pull request).
3. **The closing line:** if no line of the description is exactly `Closes #<n>` for its issue, the script appends
   `\n\nCloses #<n>` and writes the description back. Everything Dependabot wrote stays.

Then, per open App issue whose linked pull request is closed: merged → close as completed, with a comment; closed
unmerged over an hour ago, with no open pull request for its key → close as not planned, with a comment.

Every write goes through `gh api`, with the request's fields passed as arguments or on stdin, never through a shell.
A failure reading one repository stops the work in that repository only. The run exits 1 at the end, naming it.

### D3. The issue carries a marker, and the key is repository, ecosystem, directory and dependency

The issue body ends with a marker the script reads back:

```
<!-- dependabot-issue: {"ecosystem": "npm_and_yarn", "directory": "/", "dependency": "zod", "pull": 44} -->
```

- **`ecosystem`** is the branch's second segment. Dependabot names its branches this way. The branch isn't trusted for
  anything else, and the author is checked first (D6).
- **`dependency`** is the title's text between `Bump` or `Update` and ` from `, with a trailing ` requirement` taken
  off. It works for a scoped name (`@axe-core/playwright`), which the branch can't split.
- **`directory`** is the title's ` in <dir>` suffix, `/` when there is none.
- **`pull`** is the number of the pull request the issue is linked to now. Relinking changes it.
- A title that doesn't parse gets no key. Its issue is never reused, and isn't closed by a successor (spec: versions
  that can't be read).
- *Alternative: find the issue from the pull request's closing line alone.* Dependabot's description isn't the
  App's to keep, and a superseding pull request starts without the line. The marker is in a body only the App writes.

### D4. The issue's title, body and update type

- **Title:** `Update <dependency> from <old> to <new>`, plus ` in <dir>` when the directory isn't `/`. When the
  versions can't be read, the pull request's title after its Conventional prefix.
- **Body:** which pull request, the ecosystem and directory, that the release notes are in the pull request's
  description, and the update type. For major or unknown, it says the update needs an OpenSpec change, linking
  `docs/development-workflow.md`'s "Dependabot pull requests" section. Then the marker.
- **Update type:** both versions are dotted runs of digits, compared by their first differing part: the first is
  major, the second minor, any later one patch. This is how Dependabot's `update-type` counts, so `0.30.0 → 0.30.2` is
  a patch and `3 → 7` (an action's major tag) is major. Anything else, such as a requirement range, is unknown.
- **Release notes are linked, not copied.** Copying them would put upstream text into an issue the App writes.

### D5. The milestone is found by title in each repository

The script reads `tofu/milestones.json` from its checkout of `main`. It takes the open milestones whose titles are
versions, and picks the lowest by version. It then looks up the milestone with that title among each repository's
open milestones, and creates the issue with that milestone's number.

- A declaration with no open milestone stops the whole run before any write. A repository without the title stops
  that repository only (spec).
- An interim title during a renumbering (spec milestones) shows as "not found" for that window, and the run fails
  until the second apply. That's loud, and safe.

### D6. Trust: the author, the App's issues, and text as data

- **Pull requests:** only those whose `user.login` is `dependabot[bot]` and whose `user.type` is `Bot`. A person can't
  take a `[bot]` login, so a branch named `dependabot/...` proves nothing and is never checked on its own.
- **Issues:** only those whose author is the App's bot user, `troupe-run-dependabot[bot]`. The marker in anyone
  else's issue is ignored, so writing a fake one doesn't capture a pull request or close one.
- **Text:** titles and descriptions travel only as data, in Python strings and in `gh api` fields. No `${{ }}`
  expression in the workflow holds anything from a pull request: the jobs pass only issue URLs, which the board job
  checks against a pattern before use, as the schedule watch does.
- **Checkout:** one `actions/checkout` with no `ref` and no `repository`, so the schedule gets `main` of
  infrastructure. A test of the workflow pins this.

### D7. A new App for issues and pull requests, and the board App for the card

- **`troupe-run-dependabot`**: Issues read/write, Pull requests read/write, Metadata read. No organisation
  permission. Installed on troupe, website and infrastructure. Created by the owner. Its client ID goes in
  `tofu/dependabot_issues.tf` and its installation in `oob/app-installations.json`.
  - Pull requests write can edit a description and comment, but it can't merge or push, which need contents write.
  - *Alternative: widen an existing App.* The board App is pinned to one permission (spec board-credentials). The
    infrastructure App's key needs the owner's approval to use. The release App can write contents. Each would grow a
    credential beyond its job.
  - *Alternative: give the new App Projects write too, and skip the board job.* That would be one token fewer, but it
    would make two Apps able to write the org's projects.
- **Environment `dependabot-issues`** in infrastructure: main only, no admin bypass, no reviewers, since the run is
  unattended and each write is reversible. It holds `DEPENDABOT_APP_PRIVATE_KEY`. `DEPENDABOT_APP_CLIENT_ID` is a
  repository variable. `test_main_only_environments.py` gains the environment.
- **The board job** runs after the issue job whenever any App issue is open in the three repositories. It reads the
  board's items and adds each open App issue that's missing. Re-checking every run means a failed add is retried by
  the next run, not lost.

### D8. Outside Actions it only reads

When `GITHUB_ACTIONS` isn't `true`, the script makes every read and prints each write it would make, as the schedule
watch does. Its tests set `GITHUB_ACTIONS` both ways, since CI's check runs them with it set.

## Risks / Trade-offs

- **[Risk] A burst of issues on the first run:** 18 issues on 2026-10-27, one per open pull request, and more each
  Monday.
  → That's the owner's rule: every update has its issue (#170). Batching is deferred (#170, Non-goals).
- **[Risk] Dependabot rewrites the description and drops the line.** Whether it does on a rebase isn't documented.
  → Each run restores it (spec). Between the rewrite and the next run, `guard` is red for up to about 20 minutes. The
  probe records which events rewrite it.
- **[Risk] The successor appears more than an hour later**, and the issue was already closed as not planned.
  → The successor gets a new issue. Nothing is lost, but there are two issues for one dependency. The hour can be
  changed in one place.
- **[Risk] The update type here and #174's could disagree.**
  → Both follow Dependabot's counting (D4). The type here is advice in an issue. #174 decides what merges, and its
  tests can share these fixtures.
- **[Risk] Setting the issue type with only Issues write.** The REST API takes `type` on creation, but whether the
  App needs more for an org's issue types is unconfirmed.
  → Probed first. If it needs more, the permission is added to the spec and the declaration.
- **[Trade-off] Runs every 10 minutes, mostly with nothing to do.** Actions minutes are free on public repositories,
  and a run with nothing to do makes only reads.

## Migration Plan

1. **The owner creates `troupe-run-dependabot`** (D7), installs it on troupe, website, infrastructure and a throwaway
   `troupe-run/infra-probe-dependabot-issues`, and records its IDs on #172.
2. **Probe** on the throwaway repository, with a dependency old enough for Dependabot to open a pull request: create
   an issue with `type: Task` using the App's token; edit the pull request's description with it and check that the
   workflow on `pull_request: edited` runs; then comment `@dependabot rebase` and check whether the line survives.
   Record the results in tasks.md. Remove the repository from the installation and delete it afterwards.
3. Build and test. Open the pull request. Its plan shows the environment, its deployment policy and the variable.
4. After the merge and the apply, the owner sets `DEPENDABOT_APP_PRIVATE_KEY` (oob/README.md). Scheduled runs fail
   on the missing key until then, so this follows the apply straight away.
5. Start the workflow by hand. Check website #44, #45 and #46 each get an issue with type, label, milestone, board card
   and closing line, and `guard` re-runs on each without `pr-closes-issue` failing. Check the 15 other open pull
   requests too.

Rollback: disable the workflow (`gh workflow disable dependabot-issues.yml`). Issues it opened stay, and can be closed
by hand. Removing the declarations deletes the environment and variable.
