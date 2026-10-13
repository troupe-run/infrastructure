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

- **The plan** is the evidence for D2, D3, D5 and D7: it creates the ruleset, an environment, a branch policy, a
  variable and two labels on troupe, and changes or destroys nothing else.
- **The ruleset's behaviour** is shown by D8's probe, on a throwaway repository, before anything live changes.
- **The branch policy** isn't re-probed. The ci-apply probe showed that an environment declared this way refuses a run
  from another branch. After the apply, `gh api repos/troupe-run/troupe/environments/release` shows
  `can_admins_bypass: false` and `custom_branch_policies: true`, and its `deployment-branch-policies` list exactly
  `main`. Testing on troupe itself would need a workflow on a branch of a live repository.
- **The installation**: `uv run scripts/oob.py` is clean, and the owner confirms the repository list in the App's
  settings.

### D7. A ruleset reserves the release branches for the release App (owner, 2026-10-13)

#33 exempts a `release-please--` branch from the guard's branch-change rule when every commit it adds to `main` is
authored by `troupe-run-release[bot]` (#33 design D5). A commit's author is self-declared (`git commit --author`), so
the author check alone would let anyone with write access skip the rule. GitHub has to enforce who writes those
branches.

`github_repository_ruleset.release_branches` in `tofu/release.tf`, named `release branches`:

- target `branch`, `ref_name` including `refs/heads/release-please--*`;
- rules `creation`, `update` (with `update_allows_fetch_and_merge = false`) and `deletion`. There's no
  `non_fast_forward`, because release-please force-pushes its branch as `main` moves;
- one bypass actor: the release App (`Integration`, ID 5300488, `always`). There's no `OrganizationAdmin` bypass, so
  a session with the owner's credentials can't write these branches either.

It sits in `tofu/release.tf`, not the repository module, because the module protects `main` and this is specific to
troupe's release. The precedent is `.github`'s `app only` ruleset, which restricts `update` and `deletion` with one
App as the only bypass and holds on GitHub Free.

Alternative: rely on #33's author check alone. That was rejected, because the author is self-declared.

### D8. Probe first, on a throwaway repository

The `creation` rule isn't used anywhere in the org yet, so the ruleset is shown on `troupe-run/infra-probe-20261013`
before troupe gets it. `tofu/probe` gains a `probe_release_ruleset` variable that adds the same ruleset. The owner
adds the probe repository to the infrastructure App's installation, and the infrastructure App stands in for the
release App as the bypass actor. A bypass works the same way for any `Integration` actor, and installing the release
App on the probe repository would widen the installation this change declares. The steps:

1. The owner's `git push` creating `release-please--probe` is refused (`creation`).
2. The App creates `release-please--probe` through `tofu/probe` (`github_branch`), and it succeeds.
3. The owner's push and force-push to it are refused (`update`).
4. The App commits a file to it through `tofu/probe` (`github_repository_file` on that branch), and it succeeds.
5. The owner's `git push --delete` is refused (`deletion`).
6. A pull request from it into `main`, merged by the owner, with delete-on-merge on (troupe's setting): does GitHub
   delete the branch, or is the delete refused and the branch kept? Either is acceptable, because release-please
   reuses its branch. The finding is recorded so neither outcome is a surprise on troupe.
7. The App deletes the branch (destroying the `github_branch`), and it succeeds.
8. The owner pushes a branch with another name, and it isn't refused.

**Not probed: the App's force-push.** OpenTofu can't make one. A bypass applies per actor, not per rule, so step 4
already shows the App bypassing the `update` rule that a force-push would meet. The real check is troupe#23's first
rebase of the release branch.

The findings go here. Then the probe repository and the probe's local state are deleted.

**Findings (2026-10-13, `troupe-run/infra-probe-20261013`, since deleted).** The ruleset, as GitHub stored it, has
rules `creation`, `update` and `deletion` on `refs/heads/release-please--*`. Its one bypass is the App
(`Integration`, `always`), and it reports `current_user_can_bypass: never` for the owner.

1. **Owner creates:** refused. `git push origin release-please--probe` gave `GH013 … Cannot create ref due to
   creations being restricted.`
2. **App creates:** succeeded. `github_branch` created `release-please--probe` from `main`.
3. **Owner updates:** refused, both ways, with `GH013 … Cannot update this protected ref.` A fast-forward push was
   refused, and so was a force-push of an orphan commit, whose history doesn't descend from the branch. The branch
   stayed at `2b35105`.
4. **App updates:** succeeded. `github_repository_file` committed `884f92c` to the branch, authored by
   `troupe-run-infrastructure[bot]` and verified.
5. **Owner deletes:** refused. `git push origin --delete release-please--probe` gave `GH013 … Cannot delete this
   branch`.
6. **Delete-on-merge:** the branch is **kept**. With `delete_branch_on_merge = true`, the owner's
   `gh pr merge 1 --rebase` merged probe#1. Its events are `merged` and `closed`, with no `head_ref_deleted`, and the
   branch was still there afterwards. GitHub's automatic delete is refused like the owner's own. That's acceptable on
   troupe: release-please force-pushes its existing branch for the next release, which the App may do. The branch
   simply persists between releases.
7. **App deletes:** succeeded. Destroying the resources committed the file's deletion to the branch, then deleted the
   branch.
8. **Other branches:** the owner's push of `some-change` succeeded, and so did its deletion.

## Risks / Trade-offs

- [The drift check fails between the owner creating the App and this change merging] → Expected. The pull request
  quotes that output. The declaration merges in the same pull request that the App's creation unblocks.
- [The client ID is unknown until the owner creates the App] → Task 1 is the owner's, and it records the App ID,
  client ID and bot user ID on #34. #33 and troupe's `signoff` need the bot user ID too.
- [The infrastructure App gains a permission on every repository it's installed on] → It's declared and
  drift-checked like the rest, and adds no reach beyond what workflows write already gives.
- [release-please may use a label this repo doesn't declare, such as `autorelease: snapshot`, which is Java only] →
  The next plan would show it being removed, and the owner would see that before approving. Declare it then.
- [The owner can't write a release branch by hand, even to fix one] → That's the intent. The break-glass is
  editing the ruleset on GitHub, as for every ruleset (spec: rulesets); the next plan restores it.
- [GitHub's delete-on-merge is refused on a release branch, so it persists between releases (D8 step 6)] →
  Harmless: release-please force-pushes the same branch for the next release. Nobody but the App can remove it.
- [#33's exemption stays closed until this applies] → It's the ordering #33 chose: its follow-up fills
  `RELEASE_AUTHOR_EMAIL` only after this ruleset is on troupe.
- [The App is created with more permissions than declared] → The drift check reports it (spec: release-credentials).

## Migration Plan

1. **Owner:** create the App, install it on troupe only, store the key in 1Password, and record the client ID and bot
   user ID on #34. Also grant the infrastructure App "Variables: write" and accept it.
2. **This branch:** the probe (D8) and its findings, then the declarations, the docs, `scripts/check.py`, `uv run scripts/oob.py` clean, and a PR plan
   showing only the creations.
3. **Merge, then approve the apply.**
4. **Owner:** set the key's secret (D4). Then verify the ruleset, the environment, its secret and its variable by API.
5. **Tell #33** that the ruleset is on troupe, so its follow-up can fill `RELEASE_AUTHOR_EMAIL`.

Rollback: take the declarations out (the ruleset with them) with `removed` blocks, or delete them and apply. Uninstall or delete the App in
its settings, and remove its `oob/` entry. troupe's release workflow then can't mint a token, so it fails without
writing anything.
