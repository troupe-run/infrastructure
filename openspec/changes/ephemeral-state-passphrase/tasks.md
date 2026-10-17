# Tasks

## 1. The keys are declared ephemeral (D1, D3; spec: state-and-apply)

- [x] 1.1 Add `KEYS` (`TF_VAR_github_app_pem`, `TF_VAR_state_passphrase`, `TF_VAR_cloudflare_api_token`) to
      `scripts/tofu.py` beside `SECRETS`, with a comment saying a saved plan must hold none of them. In
      `scripts/tests/test_plan_secrets.py`, test that `KEYS` is a subset of `SECRETS`, and that every key's `variable`
      block in the live root (`tofu/*.tf`) and in `tofu/probe/main.tf` exists and sets both `ephemeral = true` and
      `sensitive = true`. Verify the declaration test fails on today's `state_passphrase` in both roots, naming the
      root and the variable
      Done 2026-10-17: `2 failed, 5 passed`. The two failures are `tofu: variable 'state_passphrase' isn't
      ephemeral, so a saved plan would record it` and the same for `tofu/probe`
- [ ] 1.2 Make `state_passphrase` ephemeral in `tofu/probe/main.tf` and prove it there (D1). Make a saved plan from
      `tofu/probe` with `-var declared=false -var probe_repo=none -out=probe.tfplan`, check that `tofu show -json` of
      it contains no `state_passphrase` variable and not the value (counted with the value from the environment, never
      printed), then apply the saved plan with the passphrase supplied. Record the counts and the apply's result here,
      then delete the probe's plan and state files
- [x] 1.3 Make `state_passphrase` ephemeral in `tofu/versions.tf`, with a comment on why (D1, D4). Verify
      `tofu fmt -check` and `tofu validate` pass, and 1.1's tests pass
      Done 2026-10-17: `tofu fmt -check -recursive tofu` is clean, and `tofu validate` reports `Success! The
      configuration is valid.` in both roots (initialised with `-backend=false`). `test_plan_secrets.py`: `7 passed`
- [ ] 1.4 Fast-forward onto `origin/main`, then run a local plan of the live root with `-out`. Verify it reads
      `No changes.` (the state still decrypts), and that `tofu show -json` of the saved plan contains none of the three
      keys' values. Record the summary line and the counts here

## 2. CI refuses a plan that holds a key (D2; spec: state-and-apply)

- [ ] 2.1 Write `scripts/plan_secrets.py FILE...` with its tests in `test_plan_secrets.py`, written first and seen to
      fail. The cases: a clean file passes; a file holding a key's value, as written or JSON-escaped (a multi-line PEM
      as `\n`), fails, naming the file and the variable; the value never appears in the output; an unset or empty key
      is an error naming it; a missing file is an error. Verify the tests pass, and that the script on 1.4's saved
      plan's `show` and `show -json` output exits 0
- [x] 2.2 In `.github/workflows/tofu.yml`, add the step "The plan holds no key" to both plan jobs, straight after the
      plan step and with its `if:`. It writes `$RUNNER_TEMP/plan.json` (moved out of "Modes to set after the apply")
      and runs `plan_secrets.py` on `plan.txt` and `plan.json`. Verify that every later step that reads `plan.json`
      comes after the new step in both jobs, and that `uv run scripts/check.py` passes
      Done 2026-10-17: in `pr-plan` the new step is after Plan and before "Modes to set after the apply" and "Check
      warnings", the only readers of `plan.json`. The same holds in `main`'s plan job. `check.py`: all gates passed
- [x] 2.3 Add `plan_secrets.py` to README.md's `scripts/` row (D4). Verify `uv run scripts/check.py` passes
      Done 2026-10-17: all gates passed
- [ ] 2.4 Commit groups 1 and 2 as Conventional Commits, signed off, saying why. Verify the guard accepts each commit

## 3. Pull request

- [ ] 3.1 Open the pull request with `Closes #80`, 1.2's probe result and 1.4's plan summary. Verify CI is green on
      every job, that the "The plan holds no key" step ran and passed in `pr-plan` once the owner approves that run,
      and that its posted plan reads `No changes.` (or only drift already on `main`, named in the PR)

## Workflow follow-up

- Archive the change on the branch before merging (`/opsx:archive`). The owner merges by rebase.
- After the merge, check that main's plan job ran "The plan holds no key" and passed.
- Comment on #80 with the PR and the archived change. Check #80 is closed and its card says Done.
- Remove this change's branch once it's merged and verified.
