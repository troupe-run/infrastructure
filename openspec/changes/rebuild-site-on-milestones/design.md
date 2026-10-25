# Design

## Context

See proposal.md for why. What exists today:

- **The website's build** reads `tofu/milestones.json` with a shallow bare clone of this repository's `main`, fetched
  on every run (`scripts/roadmap-lib.mjs` in troupe-run/website, its design D1). It reads the file's text, not
  GitHub's milestones, and marks each one released against troupe's tags.
- **The website's deploy** (`deploy.yml`) runs after website's CI on a push to `main`, and on `workflow_dispatch`. A
  dispatch takes no inputs, builds only on `refs/heads/main`, runs the link check, and publishes only through
  `github-pages`, which is limited to `main`. A newer build cancels a running one (`pages-build` concurrency).
- **troupe already sends this notice.** Its release workflow's `notify-website` job holds troupe's `docs`
  environment, has `permissions: {}`, checks out nothing, mints the `troupe-run-docs` App's token for website with
  `permission-actions: write`, and runs `gh workflow run deploy.yml -R troupe-run/website --ref main`.
- **The docs App** has "Actions: read and write" on website only (spec: docs-build-credentials). Its token was proved
  to start a dispatch and to be refused any contents write (docs-build-trigger design D5).
- **One App's key in two repositories has a precedent.** The board App's key sits in a `board` environment on
  website and on infrastructure, both declared in `tofu/board.tf`, both in the main-only test (watch-website-link-check
  design D5).
- infrastructure has the environments `apply`, `board`, `plan-main` and `plan-pr`, and the variable
  `BOARD_APP_CLIENT_ID` (read 2026-10-25). The infrastructure App already writes environments and variables here.

## Goals / Non-Goals

**Goals:**
- The notice sent from here is the same as troupe's: same token, same scope, same dispatch.
- The workflow's shape is pinned by a test, so weakening its trigger, permissions or token fails `scripts/check.py`.
- The path filter is proved on a throwaway repository before the merge.

**Non-Goals:**
- Rebuilding on the apply, or on milestones changed on GitHub by hand (D2).
- Any change to the website. Its deploy already accepts the dispatch.
- Recording the second sender in the website's `build-and-deploy` spec and `deploy.yml` header. That's a website
  change, through its own pull request (D7).

## Decisions

### D1. Reuse `troupe-run-docs`, with a second `docs` environment (owner, 2026-10-25)

The owner chose option A on 2026-10-25. The options as they were put:

**Option A, chosen: reuse the docs App.** Its installation, permissions and drift-check row don't change. Its
key also goes into a new `docs` environment on infrastructure, limited to `main`, no admin bypass, no reviewer, held
only by the notice job. The owner sets it from the same 1Password item.
- Blast radius of a leak from infrastructure: the same as from troupe, "Actions: write" on website (docs-build-trigger
  D1, D2). The key's exposure is one more job, which checks out nothing and runs only
  `actions/create-github-app-token` and `gh`.
- Cost: three declarations, a test entry, one more secret to set and rotate.

**Option B: a new App, `troupe-run-milestones-notice`,** with the same permission and installation. Each key would
live in one repository, and a website Deploy run's actor would say which repository sent it.
- Cost: an App to create by hand, a second key and drift-check row to keep, for the same capability. The sender is
  already visible without it: the sending run is in this repository's Actions.

**Why A.** The issue asks for "an App token that can only do that", and the docs App's token is exactly that. The
board App is the precedent for one narrow App per job, with its key in each repository that does the job. Splitting
by sender adds an App without narrowing anything.

### D2. Trigger on the file reaching `main`, not on the apply

`on: push: branches: [main], paths: [tofu/milestones.json]`. The website reads the file's text from `main`, so the
page is right as soon as the file is. Waiting for the apply would make the page wait for the owner's approval of a
plan, and couldn't add anything the page shows.

Considered: *a job in `tofu.yml` after `apply`.* It would tie the page to GitHub's milestones, but the page doesn't
read them, and it would rebuild after every apply, not only after a milestones change.

The state commit the App pushes after each apply changes `tofu/terraform.tfstate` only, so it sends nothing. GitHub
filters on the files the push changed, across all its commits, so a rebase merge of several commits counts.

### D3. The job is a copy of troupe's `notify-website`

`.github/workflows/milestones-notice.yml`, workflow `permissions: {}`, one job `notify` named "notify troupe.run",
`environment: docs`, `timeout-minutes: 5`. Two steps, as in troupe: mint the token (`client-id: vars.DOCS_APP_CLIENT_ID`,
`private-key: secrets.DOCS_APP_PRIVATE_KEY`, `owner: troupe-run`, `repositories: website`,
`permission-actions: write`), then `gh workflow run deploy.yml -R troupe-run/website --ref main` with the token as
`GH_TOKEN`. No checkout, no inputs, no `workflow_dispatch` on this workflow: the owner can dispatch the website's
deploy directly if one is ever needed. The action is pinned to the same commit as troupe's, as this repository's
workflows already pin theirs.

It runs only on pushes, so it posts no pull-request check, and `tofu/required-checks.json` doesn't change
(`test_required_checks.py` counts pull-request jobs only).

### D4. Tests are written first

- `scripts/tests/test_main_only_environments.py`: `("repo_infrastructure", "docs"): False` joins `MAIN_ONLY`. `docs`
  then appears in two repositories, so its findings are named with the repository, as `board`'s are. It fails before
  `tofu/docs.tf` declares the environment.
- `scripts/tests/test_milestones_notice_workflow.py`, shaped like `test_schedules_workflow.py`: a `problems()`
  function that reads the workflow and lists what's wrong. One test says the real file has none. One parametrised test
  applies each weakening to a copy and checks it's named: another event or branch, a missing or widened path filter,
  a workflow or job permission, a checkout step, no `docs` environment, a widened token (another repository or
  permission), and a dispatch on another ref, of another workflow, or with inputs (`-f`/`-F`). It fails before the
  workflow exists.

### D5. Prove the path filter on a throwaway repository

The token and the dispatch are already proved, in troupe's run on every push. What's new is the filter. On
`troupe-run/infra-probe-milestones-notice`, with a stub `deploy.yml` (`on: workflow_dispatch`), a `docs` environment
limited to `main` holding the key, the docs App installed for the probe, and this change's workflow with only the
target repository changed:

1. A push to `main` that changes `tofu/milestones.json` starts the notice, and a stub deploy run on `main` with
   event `workflow_dispatch`.
2. A push to `main` that changes another file starts no notice.
3. A push to another branch that changes `tofu/milestones.json` starts no notice.

Afterwards the App is removed from the probe, the repository is deleted, and the docs App's installation is checked to
list `website` only. Findings go here, under this decision, with the run IDs.

### D6. Where the declarations go

- `tofu/docs.tf`: `github_repository_environment.docs_infrastructure`, its policy
  `docs_infrastructure_main_only`, and `github_actions_variable.docs_app_client_id_infrastructure`, named as
  `board.tf` names its second set. The file's header names both users.
- `oob/README.md`, "The docs App": the second secret command and its check by name, and rotation runs both.
- `README.md`: the `tofu/docs.tf` row says both repositories; a row for the new workflow.
- `openspec/specs/docs-build-credentials/spec.md`: its Purpose says the key is held on troupe and infrastructure (a
  Purpose isn't carried by a delta).

### D7. The website documents the second sender; its code doesn't change (owner, 2026-10-25)

The website's `build-and-deploy` spec and `deploy.yml` header name troupe's release workflow as the deploy's only
dispatcher. The owner decided they should also name this repository's milestones notice, as documentation only: the
deploy already takes any dispatch on `main` with no inputs, so nothing in its code changes. A website issue tracks it,
because a product repository's files change only through its own pull requests.

## Risks / Trade-offs

- **[GitHub doesn't run a path-filtered workflow when the file is past the first 300 changed files of a push]** →
  Pushes to `main` are rebase merges of one change; none comes near 300 files. If one did, the owner dispatches the
  website's deploy by hand.
- **[The page and GitHub's milestones disagree until the apply]** → For as long as the plan waits for the owner. The
  page shows the declared list, which is what the apply will make true.
- **[One more place holds the docs key]** → It's limited to `main` of a repository whose `main` only the owner merges
  to, held by a job that runs no code from the repository. The main-only test holds the environment's policy.
- **[The secret isn't set when the first milestones change merges]** → The notice fails red in this repository's
  Actions and the page waits for the next deploy. The migration plan sets the secret straight after the apply.

## Migration Plan

1. The owner chose D1 option A, and decided D7 (2026-10-25).
2. The tests, the declarations and the workflow land on the branch; the probe (D5) runs.
3. CI's plan on the pull request shows only infrastructure's `docs` environment, its policy and `DOCS_APP_CLIENT_ID`
   being created.
4. After the merge and the apply, the owner sets `DOCS_APP_PRIVATE_KEY` on infrastructure (`oob/README.md`) and it's
   checked by name.
5. The merge's own push starts no notice run. The next push that changes `tofu/milestones.json` starts one, and a
   website Deploy run on `main`; the after-merge comment on #124 records them, or says the first is still to come.

Rollback: delete the workflow, then remove the three declarations and the test entry in one pull request. The
website is unaffected.

## Open Questions

None. D1 and D7 were decided by the owner on 2026-10-25.
