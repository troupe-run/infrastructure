# Design

## Context

- **How plans and applies run today:**
  - Every plan and apply runs on the owner's Mac through `scripts/tofu.py`, which wraps `op run`.
  - The encrypted state (`tofu/terraform.tfstate`) is committed on the change's branch and reaches `main` with the
    pull request.
  - `main` is protected by "protect main": pull requests only, rebase only, and no direct push for anyone.
  - On troupe only, the infrastructure App (5272634) has an `always` bypass, for guard deliveries.
- **`scripts/tofu.py`** already runs `tofu` as is when `TF_VAR_github_app_pem`, `TF_VAR_state_passphrase` and
  `TF_VAR_billing_email` are set, and only falls back to `op` when they aren't. So it can stay the entry point in CI
  (issue #6, question 3).
- **The provider** authenticates with `app_auth`:
  - the App ID comes from `local.infrastructure_app_id`, which troupe's bypass also uses;
  - the installation ID is a literal;
  - the key comes from `var.github_app_pem` (sensitive, not ephemeral).

  A saved plan stores the values of non-ephemeral variables, so today a plan can only be applied with the identity
  it was made with.
- **The owner's decisions (2026-10-12), on #6's two open questions:**
  - **State:** an external backend was the owner's first preference, but not a new service. Research found no
    GitHub-native state backend. The options were:
    - a community fork of `tofu` with an OCI/GHCR backend;
    - self-hosted HTTP servers that write to git.

    Neither was acceptable, so the state stays on `main`, committed by the App.
  - **PR plans:** a second, read-only App.
- **Constraints** (`openspec/config.yaml`):
  - CI applies only from `main`, through an environment that needs the owner's approval;
  - secret values are never managed by OpenTofu;
  - GitHub Free with public repositories, where environments, required reviewers and deployment branch policies are
    available.

## Goals / Non-Goals

**Goals:**
- A merge to `main` is applied without the owner at the Mac, after a plan they approve in GitHub.
- Every pull request shows its plan, made in CI, unattended.
- No pull request's run can reach a credential that can change the org.
- The state stays committed, encrypted, on `main`, and the history says which commit each state came from.
- Local runs keep working, as the fallback and the break-glass.

**Non-Goals:**
- **A real state backend with locking.** It was declined: CI runs are serialised (D6), and local applies are the
  break-glass.
- **A scheduled drift plan.** Running the workflow by hand covers drift for now.
- **Making the `tofu` plan a required check.** That's `required-checks`.
- **Managing secret values.** The owner sets them from 1Password (D9).

## Decisions

### D1. One workflow, `tofu.yml`, with two paths

```
pull_request ---------------------> [pr-plan]  env: plan  (read-only App)
                                        |
                                        +--> plan posted as a PR comment (replaced on each push)

workflow_run: CI completed on main -+
workflow_dispatch on main ----------+-> [plan] env: plan (read-only App)
                                        |   waits for guard on the same commit
                                        |   plan -out, summary in the run
                                        |   no changes --> run ends
                                        v
                                    [apply] env: apply (owner approves; write App)
                                        |   apply the saved plan
                                        v
                                    [state] commit tofu/terraform.tfstate to main as the App
```

- **The main path starts on `workflow_run`,** after CI completes on `main`, and only if CI succeeded:
  - The `guard` workflow is separate and delivered to troupe as it is, so the plan job waits for `guard`'s run on
    the same commit to succeed. A short `gh run list --commit` poll does that, and the job fails if `guard` failed.
  - That way an apply always follows green CI on all three OSes. It's the precondition the guard's delivery already
    states (CLAUDE.md, README "Delivering the guard"); until now the owner checked it by hand.
  - A `workflow_run` workflow always runs from the default branch's file, so a branch can't change what runs on
    `main`.
- **`workflow_dispatch`** (D10) runs the same jobs on `main` without waiting for CI, because the owner started it.
- **The PR path** checks out GitHub's merge ref, so it plans against `main`'s latest state, and posts the plan as one
  comment. The comment is edited on each push (`gh pr comment --edit-last --create-if-none`, as `github-actions`,
  with `pull-requests: write` on that job only).
- **Why one file, not `ci.yml`:** CI cancels superseded runs (`cancel-in-progress: true`). A cancelled apply is
  unsafe, so tofu needs its own concurrency (D6).

### D2. The plan is made as a read-only App; only the apply holds the write key

- **The read-only App:** a second App, `troupe-run-infrastructure-plan`, has the write App's permission set at read
  level:
  - administration, contents, issues, members and organization administration: read;
  - metadata: read.

  The probe (D8) settles the exact set: any 403 in a read-only plan names a missing read permission.
- **Its installation** covers the same repositories as the write App's. The README's "Adding a repository" gains
  "install both Apps".
- **The `plan` environment** holds the read-only App's key, the state passphrase and the billing email. It has no
  reviewer and no branch restriction, because a pull request's run has to reach it.
  - The worst a hostile workflow change in a pull request can do with them is read the org and decrypt the state.
  - The state holds settings and the billing email, nothing that grants access.
  - Fork pull requests get no secrets, and their job says so and stops.
- **The `apply` environment** holds the write App's key, the passphrase and the billing email:
  - its required reviewer is the owner (user 160232611);
  - its deployment branch policy is custom, `main` only;
  - `can_admins_bypass = false`, so the approval can't be skipped;
  - `prevent_self_review = false`, because the owner both merges and approves.
- **The main plan also runs in `plan`,** as the read-only App. So the write key is reachable only after the
  approval.

### D3. The App's identity is ephemeral input

For D2 to work, a plan saved as the read-only App has to apply as the write App. OpenTofu doesn't store ephemeral
variables' values in a plan, only their names, and they're allowed in provider configuration. So:

```hcl
variable "github_app_pem"             { type = string, sensitive = true, ephemeral = true }
variable "github_app_id"              { type = string, default = null,   ephemeral = true }
variable "github_app_installation_id" { type = string, default = null,   ephemeral = true }

provider "github" {
  app_auth {
    id              = coalesce(var.github_app_id, tostring(local.infrastructure_app_id))
    installation_id = coalesce(var.github_app_installation_id, local.infrastructure_installation_id)
    pem_file        = var.github_app_pem
  }
}
```

- **Defaults** are the write App's, from the locals that stay the single place for its ID. So local runs and the
  apply job set nothing new.
- **The plan jobs** set `TF_VAR_github_app_id` and `TF_VAR_github_app_installation_id` to the read-only App's IDs.
  These aren't secrets, so they're literals in the workflow.
- **A bonus:** the key stops being written into saved plans at all.
- **This is the one assumption to prove before anything depends on it** (D8). The fallback, if a saved plan can't
  switch identity:
  - the main plan uses the write App instead;
  - its key also lives in a third environment, `plan-main`, limited to `main` and with no reviewer.

  That's still sound, because only owner-merged code reaches `main`. It's just one more place the key lives.

### D4. State is committed to `main` by the App

- **The bypass:** `infrastructure`'s ruleset gets the same `always` bypass for the write App that troupe's has.
  - The module's `delivery_app_id` becomes `app_bypass_id`, since it's no longer only for deliveries.
  - The README's "To stop delivering" is updated to match.
  - As on troupe, it grants nothing new: the App already holds organization administration and could edit the
    ruleset itself.
- **The commit:** after the apply, the `state` step:
  - mints an installation token for the write App with `actions/create-github-app-token`;
  - `PUT`s `tofu/terraform.tfstate` through the contents API to `main`, with `sha` set to the blob it last saw.

  So a concurrent change to the file fails with a 409 rather than overwriting it.
- **The result:** a commit authored by `troupe-run-infrastructure[bot]`, which GitHub signs and verifies, with the
  message `chore(tofu): commit the state after applying <sha7>`. The guard's `ci` rules pass it unchanged: the
  message is Conventional, and on `main` no branch rule applies.
- **The state commit doesn't start another plan:**
  - The App's push does trigger CI and `guard`, which is correct.
  - The `workflow_run` job skips a head commit whose author is the App's bot and that changes only
    `tofu/terraform.tfstate`.
- **On failure:**
  - The state is uploaded as a run artifact first, and always (`if: always()` after an apply was attempted).
  - The apply writes state even when it fails part way, and that state is committed too.
  - If the commit fails, the run fails. The owner downloads the artifact and commits it through a pull request
    (README, break-glass).
  - The artifact is encrypted, so the public repo's artifact access exposes nothing.

### D5. Branches no longer commit state

- **On a change's branch,** a pull request no longer carries state. A local plan stays read-only.
- **Since the pull request's plan runs on the merge ref,** it always sees `main`'s current state, even when the
  branch is behind.
- **The one exception** is a local break-glass apply: its state goes on a branch and through a pull request, as
  today.

### D6. Serialising runs

- The `workflow_run` and `workflow_dispatch` jobs share `concurrency: { group: tofu-main, cancel-in-progress: false }`.
  A run waiting for approval holds the group, so a later merge plans only after it finishes, against the state it
  left.
- GitHub keeps at most one pending run per group. A third merge replaces the second's pending run, which is
  harmless, because the latest plan contains every earlier change.
- OpenTofu itself refuses a saved plan whose state changed since it was made: a stale plan errors rather than
  applies.
- The PR path has its own group per pull request, with `cancel-in-progress: true`. It only plans.

### D7. What the owner sees

- **The plan job** writes the plan's text to the run summary. GitHub shows the "Review deployments" approval on the
  same run page, so the owner reads the plan, then approves.
- **Sensitive values** (the billing email and keys) print as `(sensitive value)`.
- **Everything is public:** the run, its summary and the PR comment are visible to everyone, as pasted plans already
  were.

### D8. Prove it on a probe first

Before the live root changes, two throwaway repositories show the behaviour. Both use the existing probe root
(`tofu/probe`), extended, and both are deleted afterwards.

1. **Identity switch:**
   - plan as the read-only App, save the plan, then apply that saved plan as the write App;
   - confirm it applies, and that `tofu show -json` of the plan holds neither App's key;
   - confirm the read-only App's token gets 403 on a write.
2. **Environments:** on a probe repository with an `apply`-like environment (reviewer, `main` only) and a `plan`-like
   one, plus a small workflow, confirm that:
   - a branch's run requesting `apply` is refused;
   - a `main` run waits for approval;
   - a pull request's run reaches `plan`.

   It also settles whether `environment: { deployment: false }` avoids "deployed to plan" noise on every pull
   request. If it doesn't, accept the noise.

The probe's findings go in the memory of adopt-org findings and, where they change the design, back here.

### D9. Secrets are set by the owner, from 1Password

There are six environment secrets: `TF_VAR_github_app_pem`, `TF_VAR_state_passphrase` and `TF_VAR_billing_email` in
each of `plan` and `apply`. The plan App's key goes in `plan`. The owner runs, for example:

```
op read "op://troupe.run/troupe-run-infrastructure/private key" \
  | gh secret set TF_VAR_github_app_pem --env apply -R troupe-run/infrastructure
```

so no value is printed or passes through a session. The README lists all six commands.

### D10. Local runs stay

- `scripts/tofu.py plan` keeps working, as the write App by default.
- The README's "Changing the org" becomes:
  - open a pull request, and CI posts the plan;
  - merge it;
  - approve the run's plan.
- "Applying from your machine" moves to a break-glass section: when CI can't run, plan and apply locally as before,
  and commit the state on a branch.
- **Running the workflow by hand** (`gh workflow run tofu.yml`) on `main` covers drift and re-runs after a rejected
  approval.

### D11. Bootstrap order

The environments and their secrets must exist before the workflow can run. The App's push bypass should be applied
by CI itself, so that the first live CI apply is a real one and exercises the state commit.

1. **The owner** creates and installs the plan App, and stores its key in 1Password.
2. **Probe** (D8).
3. **On the branch, locally:**
   - commit the ephemeral identity and the environments;
   - plan, and the owner approves;
   - apply, and commit the state.

   This is the last state committed on a branch.
4. **The owner** sets the six secrets (D9).
5. **Commit the workflow and the bypass.** The pull request's own CI plan is the first PR plan: it should show only
   the bypass.
6. **Archive, then the owner merges.** The `main` run plans the bypass; the owner approves; it applies, then commits
   the state through the bypass it just applied.

## Risks / Trade-offs

- **[Ephemeral identity doesn't behave as documented]** → probed first (D8). The fallback (D3) keeps the design
  without it.
- **[No lock between CI and a local break-glass apply]** → the README says to apply locally only when no `tofu` run is
  in progress. The state `PUT` with `sha` refuses to overwrite a file that changed underneath it.
- **[The state commit fails after a successful apply]** → the state is kept as an artifact and the run fails loudly.
  Even if the state were lost, the import blocks re-adopt everything (README, "The state passphrase").
- **[A pull request can read the plan secrets]** → by a workflow change in a pull request from this repository, which
  only the owner and their sessions can open. The exposure is read access and the state's contents.
- **[An approval is asked for a plan the owner hasn't read]** → the plan is in the same run's summary. Approving is
  the owner's act, as approving a pasted plan was.
- **[CI on `main` is noisier]** → each state commit runs CI and `guard` once more. That's cheap, and keeps every
  commit on `main` checked.
- **[The DCO App]** → the state commit has no sign-off. DCO checks pull requests, not pushes. `required-checks` will
  revisit this if it matters.
- **[Two Apps to keep in step]** → `oob/app-installations.json` declares both installations' permissions, and
  `scripts/oob.py` reports drift.
