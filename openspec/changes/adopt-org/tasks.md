# Tasks

## 1. Coverage probe (read-only, decides D9)

- [x] 1.1 Pin the provider (`integrations/github ~> 6.13`) in a scratch root, run `tofu providers schema -json`, and
  record in design.md which of issue types, Projects v2 and App installation repositories have a resource. Verify:
  the recorded list matches the schema output, which is quoted in the PR.
- [x] 1.2 With App auth (key via `op run`, nothing committed), run a read-only import plan of
  `github_app_installation_repositories` for installation 170224209, and of DCO's 170159387. Record which can be read,
  and update D9 to the route taken (OpenTofu or `oob/`). Verify: the plan output, or its error, is quoted in design.md.

## 2. Tooling skeleton

- [x] 2.1 Add `pyproject.toml` (uv, Python ≥ 3.12, dev dependencies ruff, mypy, pytest), `.gitignore` (probe state,
  `.terraform/`, `generated.tf`, plan files) and `uv.lock`. Verify: `uv sync` succeeds and `uv run pytest` runs
  (with no tests yet).
- [x] 2.2 Create or name the 1Password items for the App key, the state passphrase and the billing email with the
  owner, and write `tofu/secrets.env` with their `op://` references only. Verify: `op run --env-file=tofu/secrets.env
  -- sh -c 'test -n "$TF_VAR_github_app_pem"'` exits 0, and `git grep -n "BEGIN RSA\|BEGIN PRIVATE"` finds nothing.
- [x] 2.3 Write `scripts/tofu.py` (D3, D4) and its tests: the env-already-set path runs `tofu` without `op`; the
  `op` path wraps the command in `op run --env-file`; a missing secret with no `op` exits non-zero before running
  `tofu`, naming the variable. Tests use a fake `tofu` and `op` on the PATH. Verify: `uv run pytest` passes, and each
  test fails when its branch is broken (checked by temporarily breaking it).
- [x] 2.4 Write `scripts/check.py` (D8) and a test that it fails when one step fails. Verify: `uv run
  scripts/check.py` passes on the branch.
- [x] 2.5 Add `.github/workflows/ci.yml`, running `scripts/check.py` on `ubuntu-latest` for every push and pull
  request, with no secrets and actions pinned to a SHA. Verify: the workflow is green on the pushed branch.

## 3. OpenTofu skeleton and encryption

- [x] 3.1 Write `tofu/versions.tf` (provider pin, `encryption` block per D2 with `enforced = true` for state and plan)
  and `tofu/providers.tf` (`app_auth {}`, owner `troupe-run`). Verify: `tofu fmt -check` and `tofu validate` pass
  through `check.py`.
- [x] 3.2 Show the encryption holds. Run `scripts/tofu.py plan` with an empty configuration and commit nothing yet.
  Check that the state file has no plain-text resource data, and that a plan with `TF_VAR_state_passphrase` unset
  fails before writing a file. Verify: both outputs are quoted in the PR.

## 4. Adopt the org

- [x] 4.1 Org settings: import `github_organization_settings`, generate, and tidy into `tofu/org.tf`, with the billing
  email from `var.billing_email`. Verify: `scripts/tofu.py plan` shows no change to it. Any `ignore_changes` field is
  listed under Findings with its reason.
- [x] 4.2 Write `tofu/modules/repository` (settings, `prevent_destroy`, `archive_on_destroy`, and
  `github_issue_labels` from an input map). Then import `troupe`, `.github`, `infrastructure` and
  `troupe-run.github.io` into one instance each, with their labels as data. Verify: the plan shows no change to any
  repo or label, and troupe declares 46 labels.
- [x] 4.3 `.github`'s files: fetch them into `org-profile/`, compare each with its blob SHA (`git hash-object`), and
  import the four `github_repository_file` resources. Verify: the hashes match, the plan shows no change, and
  `troupe-run/.github` has no new commit (its head SHA before and after is quoted in the PR).
- [x] 4.4 App installations, by the route task 1.2 chose (`oob/`, D9). Write `oob/app-installations.json`
  (permissions and repository selection) and the hand-confirmed repository lists in `oob/README.md`. Verify:
  `scripts/oob.py` reports no difference, and tests cover a new permission and a switch to all repositories.
- [x] 4.5 Delete `generated.tf`, keep `imports.tf`, and commit the encrypted state. Verify: `scripts/tofu.py plan`
  prints "No changes. Your infrastructure matches the configuration.", which is quoted in the PR, and
  `scripts/check.py` passes.

## 5. Drift checks for what OpenTofu can't manage

- [x] 5.1 Write `oob/issue-types.json` and `oob/projects.json` from GitHub's current state, plus `scripts/oob.py` with
  tests. The tests cover: no differences exit 0; an extra, missing or changed item is reported and exits non-zero; no
  call writes. Verify: `uv run pytest` passes, and `uv run scripts/oob.py` against the live org reports no
  differences.
- [x] 5.2 Write `oob/README.md` naming each gap (issue types, Projects v2, and App installations if 4.4 went that
  way), the provider version it was checked against, and the check that replaces it. Verify: every file in `oob/`
  is named in the README.

## 6. Prove the drift behaviours on a throwaway repo (D7)

- [x] 6.1 Create `troupe-run/infra-probe-<date>` with the owner's `gh`. The owner adds it to the infrastructure App's
  installation. Write `tofu/probe/` using `modules/repository` and a `github_repository_file`, with its own encrypted
  state, git-ignored. Verify: import, then a clean plan.
- [x] 6.2 Change a merge setting, add a label and edit the managed file on the probe repo by hand. Verify: the plan
  shows each reverting, and the output is quoted in the PR. (A file added by hand is invisible to OpenTofu, so it's
  covered by the `.github files` check in `scripts/oob.py`, with tests and a clean live run.)
- [x] 6.3 Remove the repo's declaration. Verify: the plan fails on `prevent_destroy`, and the repo still exists.
- [x] 6.4 Delete the probe repo, and remove it from the installation if GitHub hasn't already. Verify: `gh repo view
  troupe-run/infra-probe-<date>` reports not found.

## 7. Docs and evidence

- [x] 7.1 Write `README.md`: what this repo is, how to run a plan (`uv run scripts/tofu.py plan`), the 1Password
  setup, how to take a repo out of management (`removed` with `destroy = false`), and that nothing is applied without
  an approved plan. Verify: following the README from a fresh clone reaches a clean plan.
- [x] 7.2 Update design.md's Findings with anything found during adoption. Verify: every `ignore_changes` in `tofu/`
  appears there.
- [ ] 7.3 Open the PR closing #2, with the clean plan, the encryption checks, the probe outputs and the Findings.
  Verify: CI is green, and the PR body has each piece of evidence.

## Workflow follow-up

- Archive the change on the branch, then the owner merges with a rebase.
- Comment on #2 with the change and the PR, and tick the adopt step on #1.
