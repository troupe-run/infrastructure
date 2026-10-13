# Design

## Context

See proposal.md for why. What shapes the approach:

- **Installations are already declared outside OpenTofu.** `oob/app-installations.json` declares each App's
  permissions and repository selection, and `scripts/oob.py` compares it with `gh api orgs/troupe-run/installations`,
  keyed by `app_slug`. Which repositories an installation covers is listed in `oob/README.md` and confirmed by hand,
  because no token this repo holds can read it (adopt-org design D9).
- **Environments are already declared in OpenTofu**, for this repository's CI (`tofu/environments.tf`): a
  `github_repository_environment` with `can_admins_bypass = false`, and a `github_repository_environment_deployment_policy`
  for `main`. The ci-apply probe showed that such an environment refuses a run from another branch.
- **Labels are authoritative.** `github_issue_labels` in `tofu/modules/repository/main.tf` holds each repository's
  complete set, so a label it doesn't declare is deleted on the next apply.
- **The infrastructure App is installed on troupe** with administration, contents, issues, members, workflows and
  organisation administration write, and metadata read. It has no "Variables" or "Environments" permission.

Evidence read on 2026-10-13:

| Question | Finding | Source |
|---|---|---|
| Can OpenTofu hold an App's installation on a repo? | No. `github_app_installation_repository` adds a repository with `PUT /user/installations/{id}/repositories/{repo}`, which accepts an App token. But it reads with `ListUserRepos`, which is `GET /user/installations/{id}/repositories`, and that accepts only a user's token. Every plan would fail with the 403 that design D9 recorded. | provider v6.13.0 `resource_github_app_installation_repository.go` L59, L84; GitHub's "Permissions required for GitHub Apps" |
| Which permission does each declaration need? | The environment and its branch policies need "Administration: write", which the App has. A repository variable needs "Variables: write". An environment variable would need "Environments: write" instead, which also writes environment secrets. Labels need "Issues: write", which the App has. | "Permissions required for GitHub Apps" |
| What exists today? | No `troupe-run-release` App (`gh api apps/troupe-run-release` gives 404), no environment on troupe, no `autorelease:` label on troupe. The org has two installations, and they match the declaration. | `gh api`, 2026-10-13 |

## Goals / Non-Goals

**Goals:**
- Every part of the release credential except the key's value is declared here, and drift in any of it is reported.
- The key can be read only by a run on troupe's `main`.

**Non-Goals:**
- Proving release-please works end to end. troupe-run/troupe#23 does that with its first release.
- Managing the key's value, or rotating it automatically.

## Decisions

### D1. The installation is declared in `oob/`, not in OpenTofu

The release App is added to `oob/app-installations.json`, with its permissions (`contents`, `issues` and
`pull_requests` write, `metadata` read) and `repository_selection: selected`. It's also added to `oob/README.md`'s
table of repositories, as `troupe`, confirmed by the owner. That's how the other two Apps are declared, and the drift
check reports any difference in permissions or selection.

Alternative: `github_app_installation_repository`. Its read uses an endpoint that refuses App tokens (Context), so it
would fail every plan. Running OpenTofu with a user token instead would undo the provider's authentication as the
App, which is a fixed constraint.

### D2. The `release` environment is declared like CI's, in `tofu/release.tf`

A new file holds everything troupe's release needs from the org. It has a `github_repository_environment` named
`release` on `module.repo_troupe.name`, with `can_admins_bypass = false`, `prevent_self_review = false`, no reviewers,
and a `deployment_branch_policy` with `custom_branch_policies = true`. A `github_repository_environment_deployment_policy`
adds `branch_pattern = "main"`.

- **No reviewers.** The release workflow runs on every push to `main`. An approval on each run would make the owner
  approve a release PR update after every merge, and the PR itself still waits for review before it merges.
- **`can_admins_bypass = false`**, so a session holding the owner's credentials can't send a run from another branch
  past the branch policy. It matches `tofu/environments.tf`.
- **A file of its own** rather than adding to `environments.tf`, whose comments and locals are about this repository's
  CI. The two share no locals.

### D3. The client ID is a repository variable, and the infrastructure App gains "Variables: write" (owner, 2026-10-13)

`github_actions_variable` declares `RELEASE_APP_CLIENT_ID` on troupe, with the client ID as a literal in
`tofu/release.tf`. A client ID isn't a secret: it identifies the App, and minting a token also needs the key. Writing
the variable needs "Variables: write" on the infrastructure App, which it doesn't have.

| Option | What it costs |
|---|---|
| **A. Grant "Variables: write" (chosen)** | The owner adds the permission in the App's settings and accepts it on the org's installation. The App can then write Actions variables on the four repositories it's installed on. It already has workflows and contents write there, so it can change what any workflow does, and this adds no reach it doesn't have. `oob/app-installations.json` declares `actions_variables: write`. |
| B. An environment variable in `release` | Needs "Environments: write", which also lets the App write environment secrets, including CI's own. That's wider than A, and it breaks the rule that the App never holds secret values. |
| C. The owner sets it by hand, and `oob/` checks it | No new permission. A third kind of out-of-band declaration, for a value that OpenTofu could manage. troupe's design D5 and #34 both ask for it to be managed as code. |

The owner chose A (2026-10-13).

### D4. The key is set by the owner, from 1Password

The owner generates the key in the App's settings and stores it in 1Password as an item named `troupe-run-release`,
in vault `troupe.run`, with the PEM in the field `private key`. The downloaded file is then deleted. This matches the
infrastructure App's item. The owner sets the secret with:

```sh
export OP_ACCOUNT=l-a-u.1password.com
op read -n "op://troupe.run/troupe-run-release/private key" \
  | gh secret set RELEASE_APP_PRIVATE_KEY --env release -R troupe-run/troupe
```

That's the same pattern as CI's secrets in README.md, and nothing is printed. The guard already refuses an agent
running `gh secret set`, so this is the owner's step by construction. It runs after the apply, because the
environment must exist first. It's checked by name with `gh api repos/troupe-run/troupe/environments/release/secrets
--jq '.secrets[].name'`.

To rotate the key, the owner generates a new one, updates the 1Password item, runs the command again, and then
deletes the old key in the App's settings. These steps go in `oob/README.md`.

### D5. release-please's labels are a label set of their own

`tofu/labels/release.json` holds the two labels. `repo_troupe` concatenates them like the other sets. They get colour
`ededed`, which GitHub gives a label created by applying it to an issue, so the colour matches what release-please
would have produced alone. Their descriptions say what each one marks:

- `autorelease: pending`: "release-please's release PR, not yet released". release-please applies it when it opens
  the pull request.
- `autorelease: tagged`: "release-please's release PR, merged and released". release-please swaps it in once it has
  tagged the merged pull request and created the GitHub release.

The labels exist before release-please first runs, so it applies the declared ones. A separate file keeps them apart
from the workflow's labels, which every repository gets, and from troupe's `cap:` labels, which the description test
reads. Another repository that starts releasing adds the same set.

### D6. Verification without touching a live repository's behaviour

- **The plan** is the evidence for D2, D3 and D5: it creates an environment, a branch policy, a variable and two
  labels on troupe, and changes or destroys nothing.
- **The branch policy** isn't re-probed. The ci-apply probe showed that an environment declared this way refuses a run
  from another branch. After the apply, `gh api repos/troupe-run/troupe/environments/release` shows
  `can_admins_bypass: false` and `custom_branch_policies: true`, and its `deployment-branch-policies` list exactly
  `main`. Testing on troupe itself would need a workflow on a branch of a live repository.
- **The installation**: `uv run scripts/oob.py` is clean, and the owner confirms the repository list in the App's
  settings.

## Risks / Trade-offs

- [The drift check fails between the owner creating the App and this change merging] → Expected. The pull request
  quotes that output. The declaration merges in the same pull request that the App's creation unblocks.
- [The client ID is unknown until the owner creates the App] → Task 1 is the owner's, and it records the App ID,
  client ID and bot user ID on #34. #33 and troupe's `signoff` need the bot user ID too.
- [The infrastructure App gains a permission on every repository it's installed on] → It's declared and
  drift-checked like the rest, and adds no reach beyond what workflows write already gives.
- [release-please may use a label this repo doesn't declare, such as `autorelease: snapshot`, which is Java only] →
  The next plan would show it being removed, and the owner would see that before approving. Declare it then.
- [The App is created with more permissions than declared] → The drift check reports it (spec: release-credentials).

## Migration Plan

1. **Owner:** create the App, install it on troupe only, store the key in 1Password, and record the client ID and bot
   user ID on #34. Also grant the infrastructure App "Variables: write" and accept it.
2. **This branch:** the declarations, the docs, `scripts/check.py`, `uv run scripts/oob.py` clean, and a PR plan
   showing only the creations.
3. **Merge, then approve the apply.**
4. **Owner:** set the key's secret (D4). Then verify the environment, its secret and its variable by API.

Rollback: take the declarations out with `removed` blocks, or delete them and apply. Uninstall or delete the App in
its settings, and remove its `oob/` entry. troupe's release workflow then can't mint a token, so it fails without
writing anything.
