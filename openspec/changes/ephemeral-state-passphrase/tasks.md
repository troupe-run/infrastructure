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
- [x] 1.2 Make `state_passphrase` ephemeral in `tofu/probe/main.tf` and prove it there (D1). Make a saved plan from
      `tofu/probe` with `-var declared=false -var probe_repo=none -out=probe.tfplan`, check that `tofu show -json` of
      it contains no `state_passphrase` variable and not the value (counted with the value from the environment, never
      printed), then apply the saved plan with the passphrase supplied. Record the counts and the apply's result here,
      then delete the probe's plan and state files
      2026-10-17: not run on the probe root. The owner was on remote control, and 1Password's prompt timed out
      (`authorization timeout`) before `tofu init`. The owner chose to let the scratch proof in design.md stand in
      for it, with CI's pull-request plan as the run against the real providers (3.1). Not proven before merge: an
      apply of a saved plan with the real providers and the passphrase supplied again. It first happens at `main`'s
      next apply that has changes. The probe's `tofu validate` passed (1.3), and nothing was left in `tofu/probe`
- [x] 1.3 Make `state_passphrase` ephemeral in `tofu/versions.tf`, with a comment on why (D1, D4). Verify
      `tofu fmt -check` and `tofu validate` pass, and 1.1's tests pass
      Done 2026-10-17: `tofu fmt -check -recursive tofu` is clean, and `tofu validate` reports `Success! The
      configuration is valid.` in both roots (initialised with `-backend=false`). `test_plan_secrets.py`: `7 passed`
- [x] 1.4 Fast-forward onto `origin/main`, then run a local plan of the live root with `-out`. Verify it reads
      `No changes.` (the state still decrypts), and that `tofu show -json` of the saved plan contains none of the three
      keys' values. Record the summary line and the counts here
      2026-10-17: no local plan: 1Password can't prompt over remote control. The owner chose CI's pull-request plan
      as the stand-in. It runs the same root with the real secrets, and its new step checks `plan.txt` and
      `plan.json` for all three keys. Recorded under 3.1 once the owner approves that run
      Done 2026-10-17 by that stand-in (run 39036267467, job `plan (pull request)`): `No changes. Your infrastructure matches the configuration.`, so
      the state decrypts with the passphrase now ephemeral. "The plan holds no key" passed with all three keys set,
      so neither rendering holds any of them

## 2. CI refuses a plan that holds a key (D2; spec: state-and-apply)

- [x] 2.1 Write `scripts/plan_secrets.py FILE...` with its tests in `test_plan_secrets.py`, written first and seen to
      fail. The cases: a clean file passes; a file holding a key's value, as written or JSON-escaped (a multi-line PEM
      as `\n`), fails, naming the file and the variable; the value never appears in the output; an unset or empty key
      is an error naming it; a missing file is an error. Verify the tests pass, and that the script on 1.4's saved
      plan's `show` and `show -json` output exits 0
      Done 2026-10-17: the 9 script tests failed before `plan_secrets.py` existed, and all 17 tests in the module
      pass. On the ephemeral scratch plan it exits 0. On the old JSON shape it exits 1, naming
      `TF_VAR_state_passphrase` without printing the value. The live plan's `plan.txt` and `plan.json` passed in CI
      (1.4's stand-in, run 39036267467, job `plan (pull request)`)
- [x] 2.2 In `.github/workflows/tofu.yml`, add the step "The plan holds no key" to both plan jobs, straight after the
      plan step and with its `if:`. It writes `$RUNNER_TEMP/plan.json` (moved out of "Modes to set after the apply")
      and runs `plan_secrets.py` on `plan.txt` and `plan.json`. Verify that every later step that reads `plan.json`
      comes after the new step in both jobs, and that `uv run scripts/check.py` passes
      Done 2026-10-17: in `pr-plan` the new step is after Plan and before "Modes to set after the apply" and "Check
      warnings", the only readers of `plan.json`. The same holds in `main`'s plan job. `check.py`: all gates passed
- [x] 2.3 Add `plan_secrets.py` to README.md's `scripts/` row (D4). Verify `uv run scripts/check.py` passes
      Done 2026-10-17: all gates passed
- [x] 2.4 Commit groups 1 and 2 as Conventional Commits, signed off, saying why. Verify the guard accepts each commit
      Done 2026-10-17, after rebasing onto `origin/main` (run-checks-by-path had landed): group 1 `42cf8af`, group 2
      `f808777`, and `c233a99`, which tags the declaration tests `tofu`, since `guard_pytest` refused them untagged
      once `tofu/*.tf` became that scope's. Each signed off; the guard ran `check.py` on each, and all gates passed

## 3. Pull request

- [x] 3.1 Open the pull request with `Closes #80`, 1.2's probe result and 1.4's plan summary. Verify CI is green on
      every job, that the "The plan holds no key" step ran and passed in `pr-plan` once the owner approves that run,
      and that its posted plan reads `No changes.` (or only drift already on `main`, named in the PR)
      Done 2026-10-17: #84. Every check passed. `plan (main)` and `apply (main)` were skipped, as on every pull
      request, and the guard's OS matrix was skipped because the paths didn't need it. In `pr-plan` (run 39036267467, job `plan (pull request)`), "The
      plan holds no key" ran after Plan and before the two steps that read `plan.json`, and passed. The posted
      plan reads `No changes. Your infrastructure matches the configuration.`

## Workflow follow-up

- Archive the change on the branch before merging (`/opsx:archive`). The owner merges by rebase.
- After the merge, check that main's plan job ran "The plan holds no key" and passed.
- Comment on #80 with the PR and the archived change. Check #80 is closed and its card says Done.
- Remove this change's branch once it's merged and verified.
