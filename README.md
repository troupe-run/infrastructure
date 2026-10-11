# troupe-run/infrastructure

How the troupe-run GitHub organisation builds software. This repo is not the product: troupe itself lives in
[troupe-run/troupe](https://github.com/troupe-run/troupe). It owns two things (Decision troupe-run/troupe#25):

- **The org as code.** OpenTofu declares the org's settings, its repositories and their labels, and the files of
  [troupe-run/.github](https://github.com/troupe-run/.github), which is a target only. What OpenTofu can't manage is
  checked for drift from [`oob/`](oob/README.md).
- **The development process.** The `development-workflow` spec and its guard. Coming in a later change.

Work follows OpenSpec: an issue, then a change under `openspec/changes/`, on a branch named after it, then a pull request
that closes the issue. Specs live in `openspec/specs/`.

## Layout

| Path | What it holds |
|---|---|
| `tofu/` | The OpenTofu root module and its encrypted, committed state |
| `tofu/modules/repository/` | One managed repository: settings, labels, and protection against deletion |
| `tofu/labels/` | Label sets as data |
| `tofu/probe/` | Points the same module at a throwaway repo, to show drift behaviour without touching a live one |
| `org-profile/` | The source of `troupe-run/.github`'s files, byte for byte |
| `oob/` | What OpenTofu can't manage, and `scripts/oob.py`'s declarations |
| `scripts/` | `tofu.py` (the only way to run `tofu`), `oob.py` (drift checks), `check.py` (the repo's check) |

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

**Adding a repository:** add it to the infrastructure App's installation first, and update the list in
`oob/README.md`. Without the App, OpenTofu sees only the repository's public view.

## The state passphrase

The passphrase is in 1Password, as the item named in `tofu/secrets.env`. If it is lost, the state can be rebuilt:
- delete `tofu/terraform.tfstate`;
- set a new passphrase;
- run a plan and an apply. The import blocks in `tofu/imports.tf` re-adopt everything.

You lose time, not data.
