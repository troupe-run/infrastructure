# Design

## Context

troupe-run/troupe#120 (closed, owner, 2026-10-19) decided that everything under troupe.run's `/docs` is built from
troupe. "The website rebuilds on every push to troupe's `main` and on every new tag. troupe's workflow notifies the
website." The token that lets troupe trigger the website's build was left for the designs, and #109 tracks it here.

What exists today:

- **website's deploy** (`.github/workflows/deploy.yml` in troupe-run/website) runs on `workflow_run` after website's
  own CI succeeds on a push to `main`. Its `deploy` job uses the `github-pages` environment, whose deployment branches
  are limited to `main` (declared in `tofu/environments.tf`, and held there by the main-only test).
- **troupe's release workflow** (`.github/workflows/release.yml`) runs on every push to `main`. Its `release-please`
  job holds the `release` environment, mints the release App's token, and either opens or updates the release pull
  request, or tags and releases what a merged one released. The `troupe-v*` tags are created there, in a run on
  `main`.
- **Two narrow Apps** already carry a credential between repositories: `troupe-run-release` (release-credentials) and
  `troupe-run-board` (board-credentials). Each has its own App, a main-only environment holding its key, and a
  variable naming it. Both are created by hand and declared in `oob/app-installations.json`, because GitHub has no API
  for creating an App.
- A workflow's `GITHUB_TOKEN` covers only its own repository, so troupe can't start a website run with it.

Since #109 was written, troupe-run/website#23 was opened. It says it "owns both ends of the trigger: the website's
side, and the sending step in troupe-run/troupe's workflows (a small PR there), using troupe-run/infrastructure#109's
credential." #109's outcome still lists "The website's deploy workflow accepts the trigger". This design follows
website#23, the later and more specific of the two, and leaves that to it (D4).

## Goals / Non-Goals

**Goals:**
- A credential troupe's workflows can use to start a website workflow run, and nothing more on the website.
- Its key readable only by runs on troupe's `main`, and never by OpenTofu.
- Every part of it declared here, and checked: the environment by the main-only test, the App by the drift check.
- Proof, on a throwaway repository, that the chosen permission starts a run and can't write contents.

**Non-Goals:**
- The website's workflow accepting the trigger, and what it builds (website#23).
- The step in troupe's workflows that sends it (website#23's pull request in troupe).
- Versioned builds, caching earlier versions, or the version menu (website#23).
- A render check of a troupe PR's docs (troupe#123).

## Decisions

### D1. A new, narrow App, `troupe-run-docs` (owner, 2026-10-19)

The owner chose option A on 2026-10-19. The options as they were put:

**Option A, chosen: a new App, `troupe-run-docs`.**
- Permissions: repository "Actions: read and write", and "Metadata: read", which GitHub always grants with a
  repository permission. No organisation permission.
- Installed on troupe-run/website only, with selected repositories. It doesn't need to be installed on troupe: the
  run mints a token for the website installation (`owner: troupe-run`, `repositories: website`).
- Blast radius if its key leaks: on website only, someone can start, re-run or cancel workflow runs, delete run logs,
  artifacts and caches, and enable or disable workflows. They can't change website's code, settings, rulesets, issues
  or pull requests, and they can't deploy anything that isn't on website's `main` (D2).
- Cost: about ten minutes of the owner's setup, by the same steps as the board App (`oob/README.md`), then a key to
  rotate and one more row in the drift check.

**Option B: widen `troupe-run-release`.** Its key already sits in troupe's `release` environment, on `main`. Its
installation would gain website and "Actions: write". A leak would then reach both repositories: troupe's contents,
issues, pull requests and its reserved `release-please--*` branches, plus website's Actions. It also mixes two jobs
in one App, so the drift check could no longer say which job a permission is for.

**Option C: use `troupe-run-infrastructure`.** It already has "Workflows: write" but not "Actions: write", so its
installation changes anyway. Its key would get a home in troupe, where every push to `main` runs third-party code in
CI. A leak there could undo every control this repository declares.

**Why A.** It's the release-and-board precedent: one narrow App per job, holding no more than that job needs. The
saving from B or C is one App's setup. Their cost is a wider credential in a repository that runs third-party
dependencies on `main`. The constraints say to take the choice that can't lock the owner out, and C's could.

### D2. The trigger is `workflow_dispatch`, which needs "Actions: write"

GitHub has two ways for one repository's run to start another's (permissions from GitHub's "Permissions required for
GitHub Apps", read 2026-10-19):

| Event | Endpoint | App permission |
|---|---|---|
| `workflow_dispatch` | `POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches` | Actions: write |
| `repository_dispatch` | `POST /repos/{owner}/{repo}/dispatches` | Contents: write |

"Contents: write" on website would let the token push any branch that no ruleset protects, and create tags and
releases. "Actions: write" can't write contents at all. So the trigger is `workflow_dispatch`.

What "Actions: write" still allows is listed under D1, option A. Two of those are worth naming:

- **A dispatch can name any ref.** A dispatch on a website branch other than `main` runs that branch's copy of the
  workflow. The `github-pages` environment only deploys from `main`, so such a run can't publish anything.
- **It can disable a workflow.** The schedule watch (spec: schedule-watch) already reports a disabled scheduled
  workflow on website, such as the weekly link check. A disabled deploy has no schedule to miss, so the next docs
  change simply doesn't appear. That's visible and reversible.

`workflow_dispatch` inputs are limited to 25 properties, and `repository_dispatch` payloads to 10, so neither limits
what troupe can say (a ref and an event kind).

### D3. The `docs` environment on troupe is limited to `main`, which covers tags too

The key lives in a `docs` environment on troupe, limited to `main`, with no admin bypass and no reviewer. It's like
`release`, because it runs on every push to `main` and is unattended. It's separate from `release`, so the release
job can't read the docs key and the docs job can't read the release key.

Tags need no tag rule. release-please creates every `troupe-v*` tag inside the `release` workflow, in a run on
`main`, so the step that notifies the website about a new tag runs there, after release-please, using its
`releases_created` output. A run started by a tag push, with `github.ref` set to the tag, isn't needed. That matters
because anyone with write access can push a tag. An environment that admitted `troupe-v*` tags would give the key to
any workflow file at a tag someone pushed by hand.

The same holds for the push to `main` itself: a job in troupe's CI or release workflow on `main`.

### D4. website#23 uses the credential, under these constraints

This change ships the credential and nothing that uses it. website#23 owns both ends. For the owner's review of that
work, these are the constraints this design relies on:

- **troupe side:** the job that sends the trigger holds `environment: docs` and runs only on `main` (D3). It mints
  the token with `actions/create-github-app-token`, `owner: troupe-run`, `repositories: website`,
  `permission-actions: write`, and does nothing else with it. For a new tag, it runs in the release workflow after
  release-please reports a release.
- **website side:** the build workflow gains `on: workflow_dispatch`. It treats any inputs as data, such as a ref to
  build, not as code or a path to run. It keeps deploying only through `github-pages`, so only `main`'s copy of the
  workflow can publish.

The main-only test and the drift check enforce the credential's side. The workflow sides are reviewed in their own
pull requests.

### D5. Probe the permission before anything is applied

The table in D2 comes from GitHub's documentation. Before the plan, prove it on a throwaway repository,
`troupe-run/infra-probe-docs-trigger`, with a workflow that has `on: workflow_dispatch`:

1. A docs App token with only "Actions: write" creates a `workflow_dispatch` event, and a run starts.
2. The same token is refused (403) when it creates a branch, a tag or a file in the probe repository.
3. The token doesn't need the App installed on the repository that sends it: it's minted locally from the key, as a
   troupe run would mint it.

The App is installed on the probe repository for the probe, then removed from it, and the repository is deleted.

**Findings (2026-10-19).** A token minted locally from the 1Password key, for the probe repository only, came back
with exactly `actions: write` and `metadata: read`.

1. Yes. `POST actions/workflows/probe.yml/dispatches` on `main` returned 204, and run 39254721925 started on `main`
   and succeeded. No other permission was needed.
2. Yes. Creating a branch (`POST git/refs`, `refs/heads/probe-branch`), a tag (`refs/tags/troupe-v0.0.0-probe`) and a
   file (`PUT contents/probe.txt`) each returned 403. Afterwards the repository had only `refs/heads/main`, and no
   new file.
3. Yes. The token was minted outside any workflow, from the key and the installation alone, as a troupe run would
   mint it. The App isn't installed on troupe.

### D6. The declarations sit in `tofu/docs.tf` and `oob/`

- `tofu/docs.tf`: the `docs` environment on `module.repo_troupe`, its `main`-only deployment policy, and
  `DOCS_APP_CLIENT_ID`, with the client ID in a `locals` block, as `release.tf` and `board.tf` do. Not a secret: it
  names the App, and minting a token also needs the key.
- `scripts/tests/test_main_only_environments.py`: `("repo_troupe", "docs"): False` joins `MAIN_ONLY`, and
  `tofu/docs.tf` joins `TF_FILES`. The test is written first and fails before `docs.tf` exists.
- `oob/app-installations.json`: the App's row, with the permissions the probe confirmed.
- `oob/README.md`: the App's repository row (`website`) in the hand-confirmed table, and a "The docs App (set up by
  hand)" section: create, install, store the key, set the secret, check it by name, rotate.
- `README.md`: `tofu/docs.tf` in the layout table.

The infrastructure App needs no new permission: it already writes environments and variables on troupe.

## Risks / Trade-offs

- **One more App and key to look after.** → Same steps as the board App, documented in `oob/README.md`. The drift
  check catches a permission it gains.
- **troupe's `main` runs third-party code** (dependencies in CI). If one is compromised in a job that holds `docs`,
  it gets "Actions: write" on website. → The blast radius is website's Actions only (D1, D2). Only the job that sends
  the trigger holds the environment.
- **The trigger is sent, but the website ignores it** until website#23 adds `on: workflow_dispatch`. → Expected. The
  credential is ready first, and nothing depends on it until then.
- **#109's outcome lists the website's side, which this change doesn't do.** → website#23 claims it (Context). The
  pull request and the after-merge comment say so, so #109 closes on the credential alone.

## Migration Plan

1. The owner decided D1: a new App (2026-10-19).
2. The owner creates and installs the App, and stores its key. The probe (D5) runs.
3. The declarations land, and CI's plan shows only the `docs` environment, its policy and `DOCS_APP_CLIENT_ID` being
   created.
4. After the merge and apply, the owner sets `DOCS_APP_PRIVATE_KEY` and checks it by name.

Rollback: remove `docs.tf` and the test's entry in one pull request, then uninstall or delete the App. Nothing else
reads them until website#23 lands.

## Open Questions

None. D1 was decided by the owner on 2026-10-19.
