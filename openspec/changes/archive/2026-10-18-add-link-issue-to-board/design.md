# Design

## Context

See proposal.md (Why). What exists today:

- **website's weekly check** (`.github/workflows/links-weekly.yml` in troupe-run/website) runs on a schedule and by
  hand. It has `permissions: contents: read, issues: write`, and it runs `npm ci`, `npm run build` and
  `npm run linkcheck:external` in one job, with `GH_TOKEN: ${{ github.token }}`. A scheduled run is always on the
  default branch, `main`.
- **The infrastructure App** (`troupe-run-infrastructure`, `tofu/providers.tf`) is installed on troupe, .github,
  infrastructure and website. Its permissions (`oob/app-installations.json`) are administration, organisation
  administration, members, contents, workflows, pages, issues and actions variables, all write. It has no projects
  permission. Its key is held only in infrastructure's CI environments and in 1Password.
- **The release App** (`troupe-run-release`, release-credentials spec, archived change `2026-10-13-release-app`) is
  the precedent for giving another repository's workflow an App token. That App was created by hand and declared in
  `oob/`. It has a main-only `release` environment holding its key, set by the owner from 1Password, and a
  `RELEASE_APP_CLIENT_ID` variable declared in `tofu/release.tf`.
- **What the infrastructure App can already do on website:** write environments, deployment policies and variables
  (it declares `github-pages` there, `tofu/environments.tf`). This change needs no new permission for it.
- **Projects v2 and Apps.** An App gets access to an org's Projects v2 through the organisation permission
  "Projects" (`organization_projects`). With read and write, an installation token can add items through the GraphQL
  API (`addProjectV2ItemById`), which is what `gh project item-add` calls. A classic token needs the `project` scope
  instead, and `GITHUB_TOKEN` can't be given any org projects permission at all. That's the cause of #59.
- **What OpenTofu can't do.** GitHub has no API for creating an App or changing its permissions. Those happen in the
  org's settings, and a permission change has to be accepted on the installation. The provider can't read an
  installation as an App either (release-app D1). So the App, its permissions and its installation are the owner's,
  checked for drift by `oob.py`. The environment, its deployment policy and the variable can all be declared in
  OpenTofu.

Evidence read on 2026-10-18:

| Question | Finding | Source |
|---|---|---|
| Does a board App exist? | No. `gh api apps/troupe-run-board` gives 404. The org has three installations (`dco`, `troupe-run-infrastructure`, `troupe-run-release`), and none has an organisation Projects permission. | `gh api orgs/troupe-run/installations` |
| What does website have now? | One environment, `github-pages`, main-only with no admin bypass. No repository variables. | `gh api repos/troupe-run/website/environments`, `gh variable list -R troupe-run/website` |
| Which board? | Project 1, "troupe roadmap", public, linked to troupe and website. | `oob/projects.json` |

## Goals / Non-Goals

**Goals:**
- A credential that can add an issue to project 1 and do as little else as GitHub allows.
- It's readable only by a run on website's `main`.
- Every part that can be declared is declared, and every part that can't is checked for drift.

**Non-Goals:**
- Website's workflow change, which is a follow-up in troupe-run/website (D5).
- Opening the issue with the App instead of `GITHUB_TOKEN`. The issue is opened today with `GITHUB_TOKEN`, which can
  write issues, so the App doesn't need to.
- An auto-add workflow on the board. The owner ruled that out on 2026-10-14: the plan allows one, and it watches one
  repository.
- Other automated runs that open issues. If one appears, it can reuse this App by adding its repository to the
  installation, in a change of its own.

## Decisions

### D1. A new, narrow App, `troupe-run-board` (owner, 2026-10-18)

This was #59's decision. The owner chose option A on 2026-10-18. The options as they were put:

**Option A, chosen: a new App, `troupe-run-board`.**
- Permissions: organisation "Projects: read and write". On website, "Metadata: read", which GitHub always grants,
  and "Issues: read" only if the probe (D6) shows the token needs it to resolve the issue's URL. Nothing else.
  The probe showed it doesn't, so the App has no repository permission.
- Installed on no repository, with selected repositories. The plan was website only, but the probe found the
  installation covers none and still works, because website is public, so the owner chose to keep it on none
  (2026-10-18). If website ever goes private, `item-add` fails
  visibly, and the App would need website and "Issues: read".
- Blast radius if its key leaks: someone can add, edit or remove items on the org's projects, and change fields on
  them. Today that means project 1 only (`oob/projects.json`). That's annoying but recoverable. They can't change any
  repository's code, settings, rulesets or members.
- Cost: about ten minutes of the owner's setup. They create the App, install it, generate a key, store it in
  1Password and set the secret, once, by the same steps as the release App (`oob/README.md`). After that there's a
  key to rotate, and one more row in the drift check.

**Option B: reuse `troupe-run-infrastructure`.**
- Its installation gains organisation "Projects: read and write". The owner still accepts that on GitHub, so
  there's still a manual step.
- Its key gets a second home: a `board` environment on website.
- Blast radius if its key leaks from website: everything OpenTofu can do to the org. That means administration of
  every governed repository, organisation administration, members, rulesets and their bypass (the App is a bypass
  actor on `protect main`), workflows and contents. That includes pushing the guard's files straight to `main`. A
  leak would let someone undo every control this repository declares.
- Website runs third-party code every week (`npm ci` installs the site's dependencies, and the build runs them).
  The main-only environment limits *which branch* can read the key, not *which code* runs on main. A compromised
  dependency in a scheduled run would be on `main`.
- Saving: no new App and no new key to rotate.

**Option C: reuse `troupe-run-release`.** Its installation would gain organisation "Projects: read and write" and
website. A leak from website would also let someone write troupe's contents, issues and pull requests, and its
`release-please--*` branches, which only that App may write (spec: release-credentials).

**Why A.** The saving from B is one App's setup. B's cost is putting the org's most powerful
credential within reach of a weekly job that runs third-party npm code. The constraints say to take the choice that
can't lock the owner out, and a leaked infrastructure key could. A also matches the release App precedent: one
narrow App per job, holding no more than that job needs.

The issue suggests "Issues write on website". This design asks for less, because the issue is opened with
`GITHUB_TOKEN` and the App only adds it to the board.

### D2. The `board` environment and variable are declared in `tofu/board.tf`

The structure follows `tofu/release.tf`. There's a `github_repository_environment` `board` on `module.repo_website`,
with `can_admins_bypass = false`, `prevent_self_review = false`, no reviewers and custom branch policies. Its
`github_repository_environment_deployment_policy` allows `main` only. There's also a `github_actions_variable`
`BOARD_APP_CLIENT_ID`. A separate file keeps the "what this credential needs" story in one place, as `release.tf`
does.

There are no reviewers. The run is scheduled and unattended, and adding an item to the board is low-risk, so an
approval each Monday would only make the check stall. This matches `release` and `github-pages`.

Alternative: put it in `tofu/environments.tf` next to `github-pages`. That file is infrastructure's CI environments
plus website's Pages, which is about deployment, not credentials. `board.tf` keeps this credential's parts together.

Alternative: hold the key in website's `github-pages` environment, which is already main-only. Then the deploy job,
which runs the whole build, could read it, so the key's reach would follow every change to the deploy. Rejected.

### D3. `board` joins the main-only test

`scripts/tests/test_main_only_environments.py` gains `"board": Expected("repo_website", owner_reviews=False)`, and
`tofu/board.tf` joins `TF_FILES`. Without this, deleting the environment's declaration would plan a destroy that
nothing refuses. The next run would then make GitHub recreate the environment with no branch rule (#61). Write this
test first and see it fail before `board.tf` exists.

### D4. The App is declared in `oob/`, and its key is set by the owner

This follows release-app D1 and D4. The App gets a row in `oob/app-installations.json` with its exact permissions and
`repository_selection: selected`, and a row in `oob/README.md`'s table (none, D1). A new section, "website's board
App (set up by hand)", gives the creation, key, secret and rotation steps.

The secret is set with
`op read -n "op://troupe.run/troupe-run-board/private key" | gh secret set BOARD_APP_PRIVATE_KEY --env board -R troupe-run/website`
and checked by name only. The guard treats `gh secret set` as owner-only (`GH_OWNER_ONLY`), so an agent can't run it
anyway.

### D5. Website's use of the token is a follow-up change there

troupe-run/website changes by pull request through its own checks. That follow-up change, outlined here so the
credential fits it:
- A **separate job** holds `environment: board`. It runs only when the link job has opened or updated the issue, and
  it receives the issue's URL as a job output. It mints the token with `actions/create-github-app-token` (`client-id:
  ${{ vars.BOARD_APP_CLIENT_ID }}`, `private-key: ${{ secrets.BOARD_APP_PRIVATE_KEY }}`, `owner: troupe-run`). Then it
  runs `gh project item-add 1 --owner troupe-run --url <issue>`. That command is idempotent, so a re-add of an issue
  already on the board does nothing.
- Keeping the key out of the job that runs `npm ci` and the build means the site's dependencies never run where the
  key is readable. That holds whichever App D1 picks.

An issue for it is opened in troupe-run/website, on the board, once this change is applied. It isn't opened before,
because it can't be done until the secret exists.

### D6. Probe the token before website depends on it

These are unknowns that GitHub's docs don't settle. Answer them with the real App on throwaways, before the
environment goes live:
1. Can an installation token with only organisation "Projects: read and write" add an issue from a **public**
   repository the App isn't installed on, by URL (`gh project item-add`)? If yes, the App needs no repository
   permission beyond metadata. If no, add "Issues: read" on website, and record the finding.
2. Does `gh project item-add` accept an installation token (`ghs_…`)? gh checks a classic token's scopes, so this
   makes sure it doesn't refuse an App token.
3. Is a token refused when it tries to write to a repository (for example, `gh issue comment` on website)? This shows
   the narrowness is real.

Use a throwaway org project the owner creates, because project definitions are owner-only in the guard. Use an issue
on a `troupe-run/infra-probe-*` repository, and delete both afterwards. Don't touch project 1. Mint the token locally
from the 1Password key with `op run`, and never print it. gh can't mint one, so it's a JWT signed with `openssl dgst
-sha256 -sign`, exchanged at `POST /app/installations/{id}/access_tokens`, all inside one `op run` shell that prints
nothing. The findings go in this section.

Question 3 was asked without a live write: the probe tried a write that can't succeed either way (creating a label
with no name on website), where 403 means refused for lack of permission and 422 means permitted but invalid. Posting
a comment on website, as first planned, would have written to a live repository had the App had the permission.

**Findings (2026-10-18, the owner's terminal, throwaway project 3 "infra-probe board" and
`troupe-run/infra-probe-20261018-board`, since deleted).** The token was minted from the 1Password key and revoked
afterwards (`DELETE /installation/token`: 204). Nothing secret was printed.

- **The token's permissions:** `{'organization_projects': 'write'}`, `repository_selection: selected`. No
  `metadata`, and no repository permission.
- **The installation's repositories:** `GET /installation/repositories` returned `[]`. The installation covers no
  repository at all.
- **Q1, yes:** `gh project item-add 3 --owner troupe-run --url <probe issue>` added the issue
  (`PVTI_lADOE-8w_M4BnlvlzhBml-g`), from a public repository the App isn't installed on, and
  `gh project item-list 3` showed it. The App needs no repository permission, so "Issues: read" isn't added.
- **Q2, yes:** gh accepted the installation token (`ghs_…`) for `project item-add`, with no scope warning.
- **Q3, refused:** the label write on website gave HTTP 403.

**Not probed: the branch policy.** The ci-apply probe showed that an environment declared like this refuses a run from
another branch, and `release` and `github-pages` are declared the same way. After the apply, `gh api` shows `board`'s
`can_admins_bypass: false`, and its custom branch policies list exactly `main`.

## Risks / Trade-offs

- [The App's key leaks from website] → It's in a main-only environment no admin can bypass, and only a job that runs
  no third-party code reads it (D5). The damage is limited to project items (D1, option A). Rotate it by the
  documented steps.
- [The App gains a permission by hand, or is installed on more repositories] → `oob.py` reports it against
  `app-installations.json`. That check is still manual until #62 runs it daily.
- [Organisation "Projects: write" also lets the App edit project fields and views] → That's GitHub's granularity:
  there's no "add items only" permission. It's accepted and recorded here.
- [The secret isn't set when website's follow-up merges] → `create-github-app-token` fails the job, and the issue
  stays off the board, which is today's behaviour. The order in Migration Plan prevents it.
- [The probe needs a throwaway project, which only the owner can create] → It's one owner step, listed in tasks.

## Migration Plan

1. The owner creates `troupe-run-board`, installs it on website, and stores its key in 1Password (tasks 2.x).
2. Probe (D6), then fix the App's permissions to match the findings.
3. Pull request: `board.tf`, the test, and the `oob/` rows. The owner approves the plan and CI applies it.
4. The owner sets `BOARD_APP_PRIVATE_KEY` on the new environment, and it's checked by name.
5. Open the website follow-up issue (D5).

Rollback: delete the `board` declarations and the test entry in one diff, which the owner reviews. Remove the secret,
and uninstall and delete the App. The website workflow then goes back to leaving the issue off the board.
