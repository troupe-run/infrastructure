# Proposal

Issue: #34. It serves troupe-run/troupe#23 (OpenSpec change `release-automation` in troupe, design D5, D6 and D9).

## Why

troupe's release workflow (troupe-run/troupe#23) opens release pull requests with release-please. A pull request
opened with the workflow's `GITHUB_TOKEN` starts no workflows, so troupe's required checks would never run on it and
it could never merge. The workflow uses a dedicated, narrow GitHub App's token instead. That App and everything
around it are part of the org, so they're declared here like the rest of it, and drift in any of them shows up.

## What Changes

- **The release App, `troupe-run-release`, is declared and checked.** The owner creates it by hand, because GitHub
  has no API for creating an App. It has repository permissions contents, pull requests and issues read/write, and
  metadata read, with nothing at org level. It's installed on `troupe-run/troupe` only. Its permissions and repository
  selection are declared in `oob/app-installations.json`, and its repository list in `oob/README.md`, confirmed by
  hand. OpenTofu can't hold the installation: the provider's resource reads it through an endpoint that refuses App
  tokens (design D1).
- **A `release` environment on troupe**, declared in OpenTofu, whose deployment branches are limited to `main` and
  which admins can't bypass. A workflow on any other branch can't read the key (design D2).
- **The repository variable `RELEASE_APP_CLIENT_ID` on troupe**, declared in OpenTofu, holding the App's client ID.
  A client ID isn't a secret. Writing it needs the infrastructure App to gain the repository permission "Variables:
  write", which the owner has agreed to grant (design D3).
- **The private key** is set by the owner as the `release` environment's secret `RELEASE_APP_PRIVATE_KEY`, from
  1Password, by a command in `oob/README.md`. OpenTofu never holds the value. Its presence is checked by name, never
  its value (design D4).
- **Labels `autorelease: pending` and `autorelease: tagged` on troupe.** Labels are declared in full, so any label
  release-please made by itself would be deleted by the next apply, and release-please finds its release PR by these
  labels. They're declared in a new label set, `tofu/labels/release.json` (design D5).
- **A ruleset on troupe, `release branches`**: only the release App can create, update or delete a
  `release-please--*` branch, and no owner bypasses it. #33's guard exempts such a branch when the release App's bot
  authored every commit, but a commit's author is self-declared, so GitHub has to enforce who writes those branches
  (#33 design D5; owner, 2026-10-13). The `creation` rule isn't used anywhere yet, so it's probed on a throwaway
  repository first (design D7, D8).
- **Docs:** `oob/README.md` records the steps done by hand: creating the App, installing it, and setting the key. It
  also says what to do when the key is rotated.

Out of scope:
- The guard's exemption for the release branch, and the PR-title check (troupe-run/infrastructure#33).
- The release workflow, release-please's config and its `signoff` (troupe-run/troupe#23).
- A bypass of `protect main` for the release App. It never writes to `main` directly, only through a reviewed pull
  request, so it gets none.
- A tag ruleset on troupe.
- Filling #33's `RELEASE_AUTHOR_EMAIL`, which opens its exemption: a follow-up there, once this ruleset is applied.

## Capabilities

### New Capabilities

- `release-credentials`: the credential troupe's release workflow uses to open pull requests, and where it may be
  read: the release App's installation, the `release` environment that holds its key, the variable naming the App,
  and who may write the release branches.

### Modified Capabilities

- `teams-and-access`: the release App joins the declared installations, so the drift check expects three Apps, not
  two, and the infrastructure App's declared permissions gain "Variables: write".
- `labels`: troupe's label set includes release-please's two labels, declared once in their own set.

## Impact

- `tofu/release.tf` (new): the `release` environment, its branch policy, the variable and the `release branches`
  ruleset.
- `tofu/probe/main.tf`: a variable that adds the same ruleset to the probe repository.
- `tofu/labels/release.json` (new) and `tofu/repositories.tf`: troupe's labels.
- `oob/app-installations.json` and `oob/README.md`: the release App's declaration and the steps done by hand.
- `README.md`: the layout table names the new files.
- `openspec/specs/` on archive: the new `release-credentials` spec, plus `teams-and-access` and `labels`.
- GitHub, done by the owner: the App is created and installed on troupe, the key is stored in 1Password and set as
  the environment's secret, and the infrastructure App gets "Variables: write".
- GitHub, for the probe: a throwaway `troupe-run/infra-probe-*` repository, added by the owner to the infrastructure
  App's installation while the probe runs, then deleted.
- GitHub, after the owner approves the plan: on troupe-run/troupe, the `release branches` ruleset, the `release`
  environment and its branch policy,
  the variable and the two labels are created. Nothing is changed or destroyed.
- Unblocks troupe-run/troupe#23. The App's bot user ID, which #33 and troupe's `signoff` need, comes from the owner
  creating the App (task 1).
