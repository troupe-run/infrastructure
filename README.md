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
| `tofu/labels/` | Label sets as data |
| `tofu/probe/` | Points the same module at a throwaway repo, to show drift behaviour without touching a live one |
| `tofu/guard_delivery.tf` | The guard's files in each repository that receives it, and the generated list of them |
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
  `TF_VAR_billing_email`), as they will be in CI, it uses them.
- **Otherwise** it runs `tofu` under `op run`, which takes the secrets from the 1Password references in
  `tofu/secrets.env` for that one run. Expect a 1Password prompt.
- **Without either,** it stops before contacting GitHub and names what's missing.

No secret is ever written to the repo. The state is encrypted, and is unreadable without the passphrase.

## Changing the org

1. Change the configuration on a branch, and run a plan.
2. Put the plan output (and `scripts/oob.py`'s) in the pull request.
3. **Nothing is applied until the owner has approved that plan.** Apply the saved plan you showed:
   `uv run scripts/tofu.py plan -out=change.tfplan`, then after approval
   `uv run scripts/tofu.py apply change.tfplan`.
4. Commit the updated `tofu/terraform.tfstate`.

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

**Adding a repository:** add it to both Apps' installations first (`troupe-run-infrastructure`, which applies,
and `troupe-run-infrastructure-plan`, which plans), and update the lists in `oob/README.md`. Without the App, OpenTofu sees only the repository's public view. A new repository gets the "protect
main" ruleset unless its `module` block sets `protect_main = false`.

## How main is protected

Every managed repository except `.github` has a ruleset named "protect main" on its default branch:
- **Changes reach `main` only through a pull request,** merged with a rebase. No approval is required. A direct push,
  a force-push, a merge commit and a squash are all refused, for the owner too. GitHub refuses to delete a default
  branch anyway.
- **The owner's bypass works only on pull requests.** An org admin can merge a PR past a rule that blocks it with
  `gh pr merge --rebase --admin` (or the checkbox in the UI), and the ruleset's insights record it as a bypass. The
  bypass doesn't allow a merge commit or a squash, and doesn't allow a direct push.
- **Break-glass:** an org owner can always edit or disable a ruleset on GitHub. The next plan shows the edit as
  drift, and an apply restores the declared ruleset. Follow it with a PR.

The encrypted state is committed on the change's branch, so it reaches `main` with the PR.

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
2. **Wait until CI is green on all three OSes for that commit.** troupe's own CI doesn't see the files before they
   land, so this is their only check.
3. Plan, show the saved plan to the owner, and apply it after approval. Each changed file becomes one commit on
   troupe's `main`, by the App, named `chore(guard): deliver <path> <content hash> from troupe-run/infrastructure`.
4. Check troupe's `guard` and CI runs on those commits.

The probe showed how this behaves (design D3 and D8 of the `development-workflow` change):
- troupe's ruleset lets only the App push to `main`; the owner's own push is still refused;
- a hand edit to a delivered file in troupe fails troupe's `guard` check (`delivered-file`), and shows in the next
  plan, whose apply restores the file;
- an unchanged file is never recommitted.

**If a delivery breaks troupe,** fix the source here and deliver again: no troupe hook can block a delivery. A person
can also grant themselves a local override in a troupe clone.

**To stop delivering,** in this order:
1. Drop `.github/guard-delivery.json` from the delivery, and apply. The App deletes it from troupe, which turns
   `delivered-file` off there. It has to go first, while the App can still push.
2. Replace the remaining delivery resources with `removed` blocks (see "Changing the org"). That leaves the files in
   troupe, which then change through troupe's own workflow.
3. Remove `app_bypass_id` from `repo_troupe`.
