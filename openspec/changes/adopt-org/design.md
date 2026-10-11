# Design

## Context

See proposal.md for why. The org as observed on 2026-10-11, read through the API:

| Thing | State |
|---|---|
| Plan | GitHub Free. One member (the owner), no teams. |
| Org settings | 2FA not required, web sign-off not required, members can create repos, default permission `read` |
| Issue types | Task, Bug, Feature, Epic, Decision |
| Repos not archived | `troupe`, `.github`, `infrastructure`, `troupe-run.github.io`. Every bake-off and spike repo is archived, `bakeoff-specs` included. |
| All four repos | merge, squash and rebase all allowed; branches not deleted on merge; wiki and projects on; discussions off; no rulesets |
| Labels | `troupe` 46 (GitHub's 10 defaults, 34 `cap:*`, `needs:owner`, `parked`); the other three 10 each (the defaults) |
| Environments | `github-pages` on `troupe-run.github.io` only |
| `.github` files | `CONTRIBUTING.md`, `SECURITY.md`, `profile/README.md`, `.github/dco.yml` |
| Apps | DCO (installation 170159387), `troupe-run-infrastructure` (170224209). Both are selected-repo installations, and both now include `infrastructure` (owner, 2026-10-11). |

Provider `integrations/github` v6.13.0 has resources for org settings, repositories, rulesets, labels
(`github_issue_labels`), App installation repositories, repository files and environments. Its documentation has
**no resource for org issue types**, and only **classic** Projects (`github_organization_project`), not Projects v2.

**Confirmed by task 1.1** (`tofu providers schema -json`, OpenTofu 1.13.1, provider 6.13.0, 88 resources):

| Thing | Resource | Data source |
|---|---|---|
| Org issue types | none | none |
| Projects | `github_organization_project`, `github_repository_project`, `github_project_card`, `github_project_column`, all classic; `github_organization_project` is marked `deprecated` | none |
| App installation repos | `github_app_installation_repositories` (`installation_id`, `selected_repositories`), `github_app_installation_repository` | `github_organization_app_installations` |
| Rulesets | `github_repository_ruleset`, `github_organization_ruleset` | none |
| Org settings, labels, files | `github_organization_settings`, `github_issue_labels`, `github_repository_file` | labels and files |

So issue types and the Projects v2 project go to `oob/` (D6).

## Goals / Non-Goals

**Goals:**
- A module laid out so the next changes (`protect-main`, `required-checks`, `capability-labels`) add files rather
  than restructure.
- Every adoption proven with a plan that shows no changes, and every drift behaviour in the specs shown once against a
  throwaway repo rather than a live one.
- The owner can run a plan with one command and no secrets on screen.

**Non-Goals:**
- Applying from CI, the approval environment, and a CI plan on pull requests. Those need the App key as an Actions
  secret and come with a later change. Until then the owner runs plans locally, and the plan output goes into the PR.
- Remote state or locking. One owner applies, from one machine, so a committed local state is enough for now.
- Any write to the org.

## Decisions

### D1. Layout: one root module, one shared repository module

```
tofu/
  versions.tf      required_version, provider pin (~> 6.13), the encryption block
  providers.tf     provider "github" { owner = "troupe-run", app_auth {} }
  org.tf           github_organization_settings
  repositories.tf  one module "repo_<name>" per managed repo
  apps.tf          App installation repositories
  org_profile.tf   github_repository_file x4, content = file("../org-profile/...")
  imports.tf       the import blocks (kept: they're no-ops once imported, and they document the adoption)
  terraform.tfstate          encrypted, committed
  modules/repository/        settings + labels for one repo; prevent_destroy on the repository
  probe/                     a root module that uses modules/repository against a throwaway repo (D7)
org-profile/       the source of .github's files, byte for byte (CONTRIBUTING.md, SECURITY.md, profile/README.md,
                   .github/dco.yml)
oob/               drift checks for what OpenTofu can't manage (D6), with declarations as data files
scripts/tofu.py    the wrapper (D4)
scripts/check.py   the repo's check (D8)
```

**Why one shared repository module:** the four repos have the same shape, the later rulesets attach per repo, and the
probe (D7) has to exercise the same code that manages the live repos. If it didn't, the probe would prove nothing.
**Why one state:** with four repos and one owner, splitting state per repo adds ceremony and no isolation that
matters yet.

### D2. Encryption: PBKDF2 passphrase, enforced, plans too

The `encryption` block in `versions.tf` uses the `pbkdf2` key provider with the AES-GCM method, applied to `state`
and `plan`, with `enforced = true`. With `enforced`, OpenTofu refuses to write plain text instead of falling back to
it. The passphrase comes from a variable, `var.state_passphrase`, which OpenTofu evaluates early (since 1.8). The
variable has no default, so a missing passphrase stops the run before any state is written.

- **Alternatives:** AWS KMS, GCP KMS or OpenBao key providers. Each needs an account or service we don't have.
  1Password, with a passphrase, is what the owner already uses.
- **Rotation:** OpenTofu supports a `fallback` key for reading, so the passphrase can be changed later without a
  migration. This is noted, not built.

### D3. Auth: `app_auth` with the IDs committed and the key from a variable

`providers.tf` holds the App ID and installation ID, which aren't secret. The private key comes from
`var.github_app_pem` (the PEM contents, not a path), which is supplied at run time. The block is the same locally and in
CI.

*Revised during task 4:* the first version used an empty `app_auth {}`, which reads `GITHUB_APP_ID`,
`GITHUB_APP_INSTALLATION_ID` and `GITHUB_APP_PEM_FILE` from the environment. Once resources existed, `tofu validate`
checked the provider block and failed without those variables, so the repo's check would have needed fake values.
Committing the IDs in the provider block keeps them in one named place, and lets `validate` pass with no environment
at all.

### D4. Secrets: the wrapper, with `op run`

`scripts/tofu.py` (standard library only, run with `uv run`) is the only way the docs tell anyone to run `tofu`:

1. It sets `OP_ACCOUNT` to the owner's 1Password account unless one is already set.
2. **If `TF_VAR_github_app_pem`, `TF_VAR_state_passphrase` and `TF_VAR_billing_email` are all set,** it runs `tofu -chdir=tofu <args>` as is.
   This is how CI will run it.
3. **Otherwise, if `op` is on the PATH,** it runs `op run --env-file=tofu/secrets.env -- tofu -chdir=tofu <args>`.
   `tofu/secrets.env` is committed and holds only `op://` references (vault, item and field names), never values.
   `op run` resolves them into the child process's environment for that run only, and masks them in its output.
4. **Otherwise** it stops before running `tofu`, names the missing variable, and says how to supply it: sign in to
   1Password, or export the variable.

- **Why `op run` and not `op read` into the wrapper's own environment:** the secret never passes through Python
  or a shell variable, and the masking comes free.
- **Why a wrapper at all,** rather than documenting the `op run` line: it gives the "missing secret" refusal the spec
  requires, and the same entry point CI will use.
- **The organisation's billing email** is required by `github_organization_settings`. It isn't secret, but it is
  personal data in a public repo, so it is supplied the same way: an `op://` reference, read into
  `TF_VAR_billing_email`.

### D5. Adoption: import blocks plus generated configuration, then tidied by hand

For each resource, an `import` block goes in `imports.tf`, and `tofu plan -generate-config-out=generated.tf` drafts
the matching configuration. The draft is moved into the files from D1 by hand: the repos into the shared module, the
labels into data. Then `generated.tf` is deleted. Adoption is done when `tofu plan` reports
`No changes. Your infrastructure matches the configuration.`

- **Labels** use `github_issue_labels`, one per repo. It is authoritative: an undeclared label shows as a removal,
  which is what the `labels` spec asks for. troupe's labels are written as a data file in the module's input. The
  `cap:*` labels are copied as they are, today, and `capability-labels` will replace that copy with troupe's list.
- **Repositories** get `lifecycle { prevent_destroy = true }` and `archive_on_destroy = true`. The first makes
  removing a declaration fail the plan. The second is a backstop if someone lifts the first. Taking a repo out of
  management is a `removed` block with `destroy = false`, which is documented in the module's README.
- **`.github`'s files** use `github_repository_file`. Their sources in `org-profile/` are fetched through the API
  and compared byte for byte (`git hash-object` against the blob SHA) before import. No `commit_author` is set (see
  the Decided section of the brief), though nothing commits in this change.
- **Fields the provider can't read back** would show as a permanent diff. Each one found gets
  `lifecycle { ignore_changes = [...] }` with a comment naming the field and why, and is listed under Findings. The
  plan can't be called clean by hiding real drift, so each ignored field is shown to the owner in the PR.

### D6. What OpenTofu can't manage: read-only drift checks

`oob/` holds a declaration per thing (`issue-types.json`, `projects.json`, and `app-installations.json` if D9 needs
it) and `scripts/oob.py`, which reads GitHub with `gh api` and compares. It prints the differences and exits non-zero
if there are any. It never writes to GitHub in this change. A later change can add `--apply`, behind the same
plan-then-approve rule. Each check names, in its output and in `oob/README.md`, the OpenTofu gap that it fills.

- **Why `gh` and not a provider data source:** there is no data source for issue types or Projects v2 either.
- **Auth:** reading issue types and Projects v2 needs org read access. The owner's `gh` token reads them today. Using
  the App token instead would need extra App permissions (Projects). Reads with the owner's token don't break the
  "the tool acts as the App" spec, because that requirement covers OpenTofu's reads and writes. This is stated in
  `oob/README.md`, and revisited when `--apply` arrives.

### D7. Drift behaviours are proven on a throwaway repo

The `repositories`, `labels` and `org-profile` specs promise behaviours (a hand edit shows as drift; removing a
declaration doesn't delete) that can only be shown by changing something on GitHub. We never do that to a live repo.
`tofu/probe/` is a root module with its own throwaway state (encrypted the same way, git-ignored) that points
`modules/repository` at a scratch repo, `troupe-run/infra-probe-<date>`:

1. Create the scratch repo with the owner's `gh`, then add it to the App's installation by hand, since the App can't
   add itself to repos (D9).
2. Import it, and check the plan is clean.
3. Change a merge setting and add a label by hand, and check the plan shows both reverting.
4. Remove the declaration, and check the plan refuses (`prevent_destroy`).
5. Add a file by hand, and check the plan shows it as drift.
6. Delete the scratch repo, and confirm it's gone.

Each step's output goes in the PR as the evidence. Step 1 needs the owner, because adding a repo to the installation
is done in the App's settings.

**Results (2026-10-11, `troupe-run/infra-probe-20261011`, since deleted):**
- **Import then apply:** `3 imported, 0 added, 1 changed`. The "change" is the provider-local `archive_on_destroy` and
  `ignore_vulnerability_alerts_during_read`. The provider applies it with a `PATCH` of the whole repo. Diffing the repo's
  full API JSON, its labels and its head commit before and after showed **one difference: `homepage` went from `null`
  to `""`**. The provider always sends the field. The live `.github` and `troupe-run.github.io` have `homepage: null`,
  so their adoption apply makes the same cosmetic write. After the apply, the plan was clean.
- **Hand edits:** merge commits turned off, a label added and the managed file edited. The plan showed all three
  reverting, and applying them reverted all three.
- **The App's file commit:** author `troupe-run-infrastructure[bot]`, committer `GitHub`, **verified (`valid`)**. This
  settles the brief's inference: commits the App makes through the API are signed by GitHub.
- **But its message was the previous commit's ("Initial commit"),** not the configured one. With `commit_message` in
  `ignore_changes`, the provider updates using the message held in state, which was read back from the last commit.
  This is harmless here, because adoption commits nothing. It's a finding for the first change that syncs `.github`.
- **Declaration removed:** the plan failed with `Resource instance module.probe[0].github_repository.this has
  prevent_destroy`, and the repo was untouched. A `removed` block with `destroy = false` planned
  `0 to destroy, 3 to forget`.
- **A file added to `.github` by hand:** OpenTofu can't see files that aren't declared, so the `oob` check covers it.
  It derives `.github`'s expected files from `org-profile/` (D6).


### D8. The repo's check

`scripts/check.py` runs, in order, failing on the first failure:
- `ruff check`;
- `ruff format --check`;
- `mypy --strict scripts`;
- `pytest`;
- `tofu fmt -check -recursive tofu`;
- `tofu -chdir=tofu init -backend=false` and `tofu validate`.

`tofu validate` reads neither state nor variables' values: it passes with no passphrase set (checked in task 3.1),
so the check needs no secret. Python is uv-managed (`pyproject.toml`, Python ≥ 3.12, dev
dependencies `ruff`, `mypy`, `pytest`), matching troupe. A `ci` workflow runs `check.py` on `ubuntu-latest` on every
push and pull request. It needs no secrets.

**This is the contract the guard will rely on** when `development-workflow` moves here: every repo has
`scripts/check.py`. Naming it the same as troupe's is deliberate.

### D9. App installations: try OpenTofu first, fall back to a drift check

`github_app_installation_repositories` manages which repos an installation covers. GitHub's endpoints for changing
that (`PUT /user/installations/{id}/repositories/{repo}`) take a **user** token, not an installation token. Listing
another App's installation (DCO) isn't possible with an installation token either. So with App auth, the resource
can probably neither be read nor written.

Task 1 tests this: import the resource for the infrastructure App's own installation, and plan.
- **If it works,** it stays in OpenTofu.
- **If it doesn't,** both installations go to `oob/app-installations.json`, checked with the owner's token, and the
  gap is documented.

The spec allows either route. This is the one place where the design depends on a probe result.

**Result (task 1.2, 2026-10-11):** neither can be read as the App. An import plan of both, authenticated as the App,
failed:

```
Error: GET https://api.github.com/user/installations/170224209/repositories?per_page=100: 403 Resource not accessible by integration []
Error: GET https://api.github.com/user/installations/170159387/repositories?per_page=100: 403 Resource not accessible by integration []
```

So App installations leave OpenTofu for `oob/app-installations.json`. The owner's `gh` login can't read them either:
it is an OAuth token, and `/user/installations/{id}/repositories` takes only a token authorized to a GitHub App, a
personal access token, or basic auth. How each installation gets read is settled in task 4.4.

**Settled (task 4.4, owner, 2026-10-11): a partial check, with the gap stated.** A classic personal access token was
refused in the same way, with no scopes and again with `repo`. So `oob/app-installations.json` declares what *can* be
read: each App's permissions and repository selection, from `gh api orgs/troupe-run/installations`. The repositories
each App covers are listed in `oob/README.md` and confirmed by hand, and the `teams-and-access` spec says so. The
alternative was a user access token for the App (device flow). It was turned down, because it would probably cover the
App's own installation and not DCO's.

### Findings, recorded and not fixed

Each finding is fixed by a later change, through a PR with its plan:

| Finding | Fixed by |
|---|---|
| Merge commits allowed on every repo, while history is meant to be linear | `required-checks` (repo settings), with `protect-main`'s linear-history rule as the backstop |
| Branches not deleted on merge | `required-checks` |
| Wiki and classic projects on, unused | `required-checks` |
| No rulesets; `main` unprotected everywhere | `protect-main` |
| 2FA not required; members can create repos | a later org-settings change. Turning on 2FA can remove members who don't have it; today the only member is the owner, who must have it. |
| A sync commit into `.github` would reuse the previous commit's message (`ignore_changes = [commit_message]`; see the D7 results) | the change that first syncs `.github`. It must give each commit a message naming the source commit without the plan showing a permanent diff. |
| GitHub Pages on `troupe-run.github.io` isn't declared. `pages` is computed, so it shows no drift either. | a later change, if Pages settings are to be managed |
| `homepage` is `null` on `.github` and the website. Adoption's no-op PATCH sets it to `""`, which means the same. | accepted with the adoption apply |
| `.github`'s files carry no "edit this in infrastructure" line | the change that adds the `.github` ruleset. It is also the first App commit, which tests signing. |

## Risks / Trade-offs

- [The App can't read something the plan needs, e.g. org settings or another App's installation] → Task 1 probes
  every resource type with a read-only plan before any configuration is tidied. Anything unreadable moves to `oob/`
  (D6, D9).
- [`github_organization_settings` writes every field it knows on apply, not just the ones that changed] → Not a risk
  while nothing is applied. Before the first apply that touches it, the plan is checked field by field.
- [Committed state with no lock: two applies at once could clash] → There's one owner and one machine. CI apply,
  with an environment that serialises applies, comes before anyone else can apply.
- [`github_issue_labels` is authoritative, so a label someone adds by hand is removed on the next apply] → That's
  what the spec intends. The plan shows the removal before it happens, and the owner approves every apply.
- [`.github` files fetched for adoption could change between the fetch and the import] → The byte-for-byte compare
  runs again just before the final plan.
- [Losing the state passphrase] → The state can be rebuilt by re-importing, because the import blocks are kept in
  the repo. No data is lost, only time. The passphrase lives in 1Password.

## Migration Plan

Nothing on GitHub changes, so there is nothing to roll back. If the change is abandoned, deleting the branch leaves
the org exactly as it was.

## Open Questions

- **The 1Password item and field names** for the App key, the state passphrase and the billing email. They only fill
  in `tofu/secrets.env`. The owner names them in task 2.2, or the task creates the passphrase item.
