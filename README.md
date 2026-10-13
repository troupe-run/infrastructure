# troupe-run/infrastructure

How the troupe-run GitHub organisation builds software. This repo is not the product: troupe itself lives in
[troupe-run/troupe](https://github.com/troupe-run/troupe). It owns two things (Decision troupe-run/troupe#25):

- **The org as code.** OpenTofu declares the org's settings, its repositories and their labels, and the files of
  [troupe-run/.github](https://github.com/troupe-run/.github), which is a target only. What OpenTofu can't manage is
  checked for drift from [`oob/`](oob/README.md).
- **The development process.** The `development-workflow` spec and its guard, which governs this repo and is
  delivered to troupe. The rules are in [docs/development-workflow.md](docs/development-workflow.md).

Work follows OpenSpec: an issue, then a change under `openspec/changes/`, on a branch named after it, then a pull request
that closes the issue. Specs live in `openspec/specs/`.

## Layout

| Path | What it holds |
|---|---|
| `tofu/` | The OpenTofu root module and its encrypted, committed state |
| `tofu/modules/repository/` | One managed repository: settings, labels, and protection against deletion |
| `tofu/labels/` | Label sets as data. `troupe.json` is troupe's `cap:*` capability labels: a new capability gets its label by a pull request here. `release.json` is release-please's two labels on troupe |
| `tofu/probe/` | Points the same module at a throwaway repo, to show drift behaviour without touching a live one |
| `tofu/guard_delivery.tf` | The guard's files in each repository that receives it, and the generated list of them |
| `tofu/release.tf` | What troupe's release workflow needs: the `release` environment, limited to `main`, the release App's client ID, and the ruleset that reserves `release-please--*` branches for the App. The App and its key are set up by hand ([oob/README.md](oob/README.md#troupes-release-app-set-up-by-hand)) |
| `org-profile/` | The source of `troupe-run/.github`'s files, byte for byte |
| `scripts/guard.py`, `.githooks/`, `.claude/settings.json`, `.github/workflows/guard.yml` | The guard: this repo's own, and the source of every delivered copy |
| `docs/development-workflow.md` | Every rule the guard enforces, and how an override works |
| `oob/` | What OpenTofu can't manage, and `scripts/oob.py`'s declarations |
| `scripts/` | `tofu.py` (the only way to run `tofu`), `oob.py` (drift checks), `check.py` (the repo's check), `guard.py` |

## Setup

You need:
- [uv](https://docs.astral.sh/uv/);
- OpenTofu 1.8 or later (`brew install opentofu`);
- the 1Password CLI (`op`), signed in to the account named in `scripts/tofu.py`;
- `gh`, logged in with read access to the org.

```
uv sync
uv run scripts/check.py          # ruff, mypy --strict, pytest, tofu fmt and validate; needs no secret
```

The first run of the check turns the git hooks on (`core.hooksPath = .githooks`), and says so. From then on, each
commit runs the check first and needs a Conventional Commit message on a branch named after an OpenSpec change. A
Claude Code session turns the hooks on too, and its hooks refuse the same shortcuts.

## Running a plan

```
uv run scripts/tofu.py init
uv run scripts/tofu.py plan
uv run scripts/oob.py            # drift in what OpenTofu can't manage
```

`scripts/tofu.py` runs `tofu` in `tofu/` as the `troupe-run-infrastructure` GitHub App:
- **When the secrets are already in the environment** (`TF_VAR_github_app_pem`, `TF_VAR_state_passphrase` and
  `TF_VAR_billing_email`), as they are in CI, it uses them.
- **Otherwise** it runs `tofu` under `op run`, which takes the secrets from the 1Password references in
  `tofu/secrets.env` for that one run. Expect a 1Password prompt.
- **Without either,** it stops before contacting GitHub and names what's missing.

No secret is ever written to the repo. The state is encrypted, and is unreadable without the passphrase. The App's
key is ephemeral input, so a saved plan doesn't hold it either: applying a saved plan asks for the key again.

A local plan is read-only and always safe to run. Changes reach the org through CI (below).

CI also plans `main` every day at 06:00 UTC, so drift (a change made on GitHub rather than declared here) shows within
a day. A plan with changes waits for your approval like any plan of `main`; one with none asks nothing. GitHub pauses
a public repository's scheduled workflows after 60 days without activity in it. `gh workflow enable tofu.yml` turns
the daily plan back on.

## Changing the org

Changes are planned and applied by the `tofu` workflow (`.github/workflows/tofu.yml`, spec `ci-apply`). Your part
is two approvals:

1. **Open a pull request.** Its `plan (pull request)` job waits for your approval, because a pull request runs its
   own copy of the workflow, and an approved run holds the App's key. Look at whether the pull request changes
   `.github/workflows/`, then approve: on the run, **Review deployments**, tick `plan-pr`, **Approve and deploy**.
   GitHub notifies you of each waiting run. The plan appears as one comment on the pull request, updated on each
   push. Put `scripts/oob.py`'s output in the pull request yourself.

   The plan is a required check: the pull request can't merge until you've approved the run and the plan has
   succeeded. A pull request that changes only files OpenTofu never reads (`openspec/`, `docs/`, `oob/`,
   `scripts/tests/`, `README.md`, `CLAUDE.md`; the list is in `scripts/plan_needed.py`) skips the plan, which counts
   as passed and asks you for nothing. Anything else is planned, including a file the list doesn't know about.
2. **Merge.** Once CI and `guard` pass on `main`, the `plan (main)` job plans unattended and shows the plan in the
   run's summary. A plan with no changes ends there.
3. **Read that plan, then approve the `apply` job** (`apply` environment). It applies exactly the saved plan you
   read, then commits the new encrypted state to `main` as the App:
   `chore(tofu): commit the state after applying <sha>`. That commit starts no further plan.

Rejecting the approval applies nothing. To plan `main` again later, for example after drift or a rejection, run
`gh workflow run tofu.yml --ref main`.

| Environment | Who may use it | Approval | Used by |
|---|---|---|---|
| `plan-pr` | any branch | the owner, each run | a pull request's plan |
| `plan-main` | `main` only | none | the plan after a merge, and manual runs |
| `apply` | `main` only | the owner | the apply |

Each holds the same three secrets. OpenTofu declares the environments (`tofu/environments.tf`) but never their
values: the owner sets them from 1Password, so no value is printed or passes through a session:

```sh
export OP_ACCOUNT=l-a-u.1password.com
for env in plan-pr plan-main apply; do
  op read -n "op://troupe.run/troupe-run-infrastructure/private key" \
    | gh secret set TF_VAR_github_app_pem --env "$env" -R troupe-run/infrastructure
  op read -n "op://troupe.run/troupe-run-infrastructure tofu state/password" \
    | gh secret set TF_VAR_state_passphrase --env "$env" -R troupe-run/infrastructure
  op read -n "op://troupe.run/troupe-run-infrastructure tofu state/billing email" \
    | gh secret set TF_VAR_billing_email --env "$env" -R troupe-run/infrastructure
done
```

Run it again after rotating any of them.

### Break-glass: applying from your machine

When CI can't apply (GitHub Actions down, or the workflow itself broken), apply locally. Do it only while no `tofu`
run is in progress: nothing locks the state between CI and your machine.

1. On a branch named after the change, `uv run scripts/tofu.py plan -out=change.tfplan`, and show the plan to the
   owner.
2. **After the owner approves it,** `uv run scripts/tofu.py apply change.tfplan`.
3. Commit the updated `tofu/terraform.tfstate` on that branch, and merge it through a pull request.

**If CI applied but couldn't commit the state,** the run fails and keeps the state as its `state-after-apply`
artifact. Download it (`gh run download <run> -n state-after-apply`), copy it over `tofu/terraform.tfstate` on a
branch, and merge that through a pull request.

**An apply can't delete a repository.** Removing a repository's declaration makes the plan fail on `prevent_destroy`.
To stop managing a repository but keep it, replace its `module` block with:

```hcl
removed {
  from = module.repo_<name>
  lifecycle {
    destroy = false
  }
}
```

The plan then shows it as "forget", with nothing destroyed.

**Adding a repository:** add it to the `troupe-run-infrastructure` App's installation first, and update the list in
`oob/README.md`. Without the App, OpenTofu sees only the repository's public view. A new repository gets the "protect
main" ruleset unless its `module` block sets `main_ruleset` to `app-only` or `none`.

## How main is protected

`.github` has a ruleset named "app only": nobody but the infrastructure App can change its `main`, not by a push and
not by merging a pull request, and the owner has no bypass. Its files are written from `org-profile/` here, so change
them there. The break-glass is the same as below: edit or disable the ruleset on GitHub, and the next plan restores it.

Every other managed repository has a ruleset named "protect main" on its default branch:
- **Changes reach `main` only through a pull request,** merged with a rebase. No approval is required. A direct push,
  a force-push, a merge commit and a squash are all refused, for the owner too. GitHub refuses to delete a default
  branch anyway.
- **A pull request merges only when its required checks pass.** Each repository's checks are listed in
  `tofu/required-checks.json`, as GitHub names them (`guard tests (macos-latest, Python 3.13)`, not the workflow's job
  id), each pinned to the App that posts it, so a status of the same name posted by anything else doesn't count. A
  skipped job counts as passed. A test checks this repository's list against its workflows; when you rename a job or
  change a matrix in troupe or the website, change the list here too, or their pull requests wait for a check that
  never reports.
- **The owner's bypass works only on pull requests.** An org admin can merge a PR past a rule that blocks it with
  `gh pr merge --rebase --admin` (or the checkbox in the UI), past failing or missing required checks too, and the
  ruleset's insights record it as a bypass. The bypass doesn't allow a merge commit or a squash, and doesn't allow a
  direct push.
- **Break-glass:** an org owner can always edit or disable a ruleset on GitHub. The next plan shows the edit as
  drift, and an apply restores the declared ruleset. Follow it with a PR.

troupe also has a ruleset named "release branches" (`tofu/release.tf`): only the `troupe-run-release` App can create,
update or delete a `release-please--*` branch, and the owner has no bypass. The guard exempts those branches from its
branch rule only when the App authored every commit, and an author can be set by anyone, so GitHub enforces who writes
them. GitHub's delete-on-merge is refused there too, so the release branch stays after its pull request merges, and
release-please reuses it. The break-glass is the same: edit or disable the ruleset on GitHub, and the next plan
restores it.

After a CI apply, the App commits the encrypted state straight to this repository's `main`. Its ruleset lets the App
through for that, and only the App.

## The state passphrase

The passphrase is in 1Password, as the item named in `tofu/secrets.env`. If it is lost, the state can be rebuilt:
- delete `tofu/terraform.tfstate`;
- set a new passphrase;
- run a plan and an apply. The import blocks in `tofu/imports.tf` re-adopt everything.

You lose time, not data.

## Delivering the guard

troupe holds copies of the guard's files, delivered from this repo by the App straight to its `main` (spec:
`guard-delivery`). A change to the guard reaches troupe like any other change to the org, with one extra condition:

1. Change the guard's source here, on the change's branch, with its tests.
2. **Merge it.** The `tofu` workflow plans the delivery only after CI is green on all three OSes, and `guard` has
   passed, for that commit. troupe's own CI doesn't see the files before they land, so this is their only check.
3. Read the plan, and approve the apply. Each changed file becomes one commit on troupe's `main`, by the App, named
   `chore(guard): deliver <path> <content hash> from troupe-run/infrastructure`.
4. Check troupe's `guard` and CI runs on those commits.

The probe showed how this behaves (design D3 and D8 of the `development-workflow` change):
- troupe's ruleset lets only the App push to `main`; the owner's own push is still refused;
- a hand edit to a delivered file in troupe fails troupe's `guard` check (`delivered-file`), and shows in the next
  plan, at the latest the next daily one, whose apply restores the file. A commit forging the App as its author
  passes the check, and the daily plan is what catches it (enforce-delivered-files);
- an unchanged file is never recommitted.

**If a delivery breaks troupe,** fix the source here and deliver again: no troupe hook can block a delivery. A person
can also grant themselves a local override in a troupe clone.

**To stop delivering,** in this order:
1. Drop `.github/guard-delivery.json` from the delivery, and apply. The App deletes it from troupe, which turns
   `delivered-file` off there. It has to go first, while the App can still push.
2. Replace the remaining delivery resources with `removed` blocks (see "Changing the org"). That leaves the files in
   troupe, which then change through troupe's own workflow.
3. Remove `app_bypass_id` from `repo_troupe`.
