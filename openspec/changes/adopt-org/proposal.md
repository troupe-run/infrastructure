# Proposal

Issue: #2 (part of #1)

## Why

The troupe-run org's setup exists only as clicks on GitHub: nothing records it, nothing shows when it drifts, and
every change to it is made by hand. Before this repo can change anything (rulesets come next, and `main` on
`troupe` is unprotected), it has to describe what exists today and prove the description matches. Adopting first,
with no changes, means the first apply that does change something shows only that change.

## What Changes

- **An OpenTofu root module** using the `integrations/github` provider, authenticated as the
  `troupe-run-infrastructure` App (ID 5272634, installation 170224209). The App ID and installation ID are
  committed; the private key is not.
- **Encrypted state, committed.** OpenTofu state encryption is enforced for state and saved plans, keyed by a
  passphrase that lives outside the repo.
- **Secrets at run time from 1Password.** A wrapper runs `tofu` with the App key and the passphrase taken from
  1Password through the `op` CLI, so nobody types or stores them. When the variables are already set (CI, later),
  the wrapper uses them as they are.
- **Imported as they are, with no changes:**
  - org settings;
  - the repos that aren't archived: `troupe`, `.github`, `infrastructure` and `troupe-run.github.io` (their settings
    and their labels, including troupe's 34 `cap:*` labels as they exist today);
  - which repos the DCO App and the infrastructure App are installed on;
  - the four files of `troupe-run/.github`.
- **Org issue types and the "troupe roadmap" project**, which the provider can't manage (to be confirmed with
  `tofu providers schema`), get a read-only `gh` check that reports drift from what this repo declares.
- **The repo's own check** (`scripts/check.py`): `tofu fmt`, `tofu validate`, and ruff, mypy `--strict` and pytest
  for the Python, plus a CI workflow that runs it on Linux.
- **Findings recorded, not fixed:** merge commits allowed, branches kept after merge, the wiki on, no rulesets, 2FA
  not required, members can create repos. Each is fixed by a later change, through a PR.
- **Proof:** `tofu plan` reports no changes.

Out of scope: any change to the org; the archived bake-off and spike repos (owner, 2026-10-11); rulesets
(`protect-main` and `required-checks` follow); the "edit this in infrastructure" header on `.github`'s files,
which changes them; applying from CI.

## Capabilities

### New Capabilities

- `state-and-apply`: how the org's declared state is kept, authenticated and changed: encrypted committed state, App
  auth, secrets from outside the repo, plans as evidence and owner-approved applies.
- `org-settings`: the org's own settings, plus its issue types and its project.
- `repositories`: which repos are managed and their settings, and that an apply can't delete one.
- `labels`: each managed repo's labels, declared in full.
- `teams-and-access`: which repos each GitHub App is installed on (teams join later; the org has none).
- `org-profile`: the files of `troupe-run/.github`, whose source is this repo.

### Modified Capabilities

None. This repo has no specs yet.

## Impact

- **New in this repo:** the OpenTofu module and its encrypted state, the 1Password wrapper, the `gh` drift checks,
  `pyproject.toml` with uv, `scripts/check.py`, and a `ci` workflow.
- **On GitHub: nothing changes.** Imports and plans only read. No apply happens unless a plan shows a change, and
  this change exists to show none.
- **The owner's machine:** OpenTofu (installed), the 1Password CLI (installed, 2.40.0), and 1Password items for the
  App key and the state passphrase.
