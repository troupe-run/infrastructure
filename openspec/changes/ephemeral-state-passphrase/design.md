# Design

## Context

See proposal.md for why. The current state:

- Both roots declare `state_passphrase` as `sensitive` only, and read it in the `encryption` block's
  `key_provider "pbkdf2" "passphrase"`. `github_app_pem` and `cloudflare_api_token` are already `ephemeral` in both
  roots (ci-apply D3, manage-dns-as-code D4), which is why a saved plan holds neither.
- `scripts/tofu.py` supplies all four `TF_VAR_*` secrets: from the environment in CI, otherwise through `op run`.
- Each plan job (`pr-plan`, and `main`'s plan) writes `plan.txt` (`tofu show -no-color`, posted on the pull request
  or shown for approval) and `plan.json` (`tofu show -json`, read by `hook_modes.py` and `plan_checks.py`), both under
  `$RUNNER_TEMP`.

**Evidence already gathered** (scratch root in the session's scratchpad, OpenTofu 1.13.1, built-in `terraform_data`
only, the same `encryption` block as `tofu/versions.tf`, `state_passphrase` marked `ephemeral = true`):

| Step | Result |
|---|---|
| `tofu init`, `tofu plan -out` | accepted: no error about an ephemeral value in the encryption block |
| `tofu show -json` of the plan | `variables` holds only the non-ephemeral `note`; the passphrase's value appears 0 times in the JSON or the plan file |
| `tofu apply` of the saved plan, passphrase supplied | `Apply complete!`; the state is encrypted (`meta` holds the pbkdf2 key's salt), passphrase not in it |
| second plan against that state, then apply without `TF_VAR_state_passphrase` | refused: `Unable to compute static value` / `Failed to request input from user for variable var.state_passphrase` |
| same apply with a wrong passphrase | refused: `Failed to load "p3.tfplan" as a plan file` |
| same apply with the right passphrase | `Apply complete! Resources: 0 added, 1 changed, 0 destroyed.` |

## Goals / Non-Goals

**Goals:**

- No rendering of a saved plan (the file, `tofu show`, `tofu show -json`) contains the state passphrase.
- Any of the three keys turning up in a plan CI makes fails that plan job. That covers a key's variable losing
  `ephemeral`, and a key reaching a resource attribute some other way.

**Non-Goals:**

- Changing the passphrase, the key provider, the method, or anything already encrypted. Nothing is re-encrypted.
- Deciding whether `plan.json` may leave the runner. It still holds the billing email and every resource attribute
  (proposal, out of scope).
- Detecting a key that's been transformed (base64, hashed, split) before it reaches a plan. The check catches the
  value as written and as JSON escapes it.

## Decisions

### D1. `state_passphrase` is ephemeral in both roots

Add `ephemeral = true` to `variable "state_passphrase"` in `tofu/versions.tf` and `tofu/probe/main.tf`, keeping
`sensitive = true`, with a comment saying why: a saved plan records no ephemeral variable, so neither the file nor its
JSON holds the key to the state.

Prove it on the probe root first, as #80 asks. Make a saved plan with `declared=false`, `probe_repo=none` and no
probe flags, so nothing is created and no throwaway repository is needed. Then check that `tofu show -json` of it
doesn't contain the passphrase and that applying the saved plan succeeds. Only then change the live root. Its proof is
a local plan with `No changes.` (the state still decrypts with the same passphrase), and the same `show -json` check.
CI's pull-request plan runs it again with D2's step.

- *Alternative: strip `variables` from the JSON before any step reads it* (#80's fallback). Rejected. It's only
  needed if ephemeral isn't allowed, and it is. Filtering would also leave the value in the plan file, so every future
  reader of the plan would have to remember to filter.
- *Alternative: a different key provider* (for example, a KMS). Rejected as a much larger change, for a problem
  ephemeral already solves.

### D2. CI checks every plan it makes for the three keys: `scripts/plan_secrets.py`

A new script, `plan_secrets.py FILE...`, reads each file as text. For each key it reads the value from the
environment, and fails if the value appears in the file, either as written or JSON-escaped (`json.dumps(value)[1:-1]`,
since the App key's newlines appear as `\n` in JSON). It exits non-zero, naming the file and the variable, never the
value. A key whose variable is unset or empty is also an error: an unchecked key mustn't pass as a clean plan
(learned rule: malformed input is an error). The keys are `TF_VAR_github_app_pem`, `TF_VAR_state_passphrase` and
`TF_VAR_cloudflare_api_token`. They're named once, as `KEYS` in `scripts/tofu.py` next to `SECRETS`, and a test
checks that `KEYS` is a subset of `SECRETS`. The billing email isn't a key and can't be ephemeral, so it isn't
checked.

In both plan jobs, a new step "The plan holds no key" runs straight after the plan step. It runs `show -json` into
`$RUNNER_TEMP/plan.json` (moved out of "Modes to set after the apply"), then
`plan_secrets.py "$RUNNER_TEMP/plan.txt" "$RUNNER_TEMP/plan.json"`. It has the same `if:` as the steps around it, so
it runs exactly when a plan was made. Checking `plan.txt` as well covers the rendering CI publishes on the pull
request.

- *Alternative: check only `variables` in the JSON.* Rejected. A substring search over the whole file also catches a
  key that reaches a resource attribute, and it's no more code.
- *Alternative: fold it into `plan_checks.py`.* Rejected. That script turns check-block results into warnings that
  never fail the job. This check always fails it, so keeping it separate keeps each script to one job.

### D3. An offline test that the keys are ephemeral in both roots

`scripts/tests/test_plan_secrets.py` also reads `tofu/*.tf` and `tofu/probe/main.tf`. For each `variable` block named
for a key in `KEYS` (with the `TF_VAR_` prefix removed), it asserts that the block sets `ephemeral = true` and
`sensitive = true`, and that each key is declared in both roots. `check.py` runs it, so a dropped `ephemeral` fails
before any plan is made, with no secrets needed. It's written first, so it fails on today's
`state_passphrase`.

### D4. Docs

README.md's `scripts/` row gains `plan_secrets.py`. The comment on `state_passphrase` in `tofu/versions.tf` explains
the ephemeral setting. The `state-and-apply` spec's requirement is extended (specs/).

## Risks / Trade-offs

- [The live root behaves differently from the scratch root, for example the GitHub provider or `-lock=false`
  interacting with an ephemeral encryption variable] → D1 proves it on the probe root, which uses the same providers,
  and then with a local live plan before anything merges. CI's pull-request plan is the third run.
- [The check prints a key while reporting it] → it prints only file and variable names. GitHub also masks secret
  values in logs. The tests assert the value is absent from the script's output.
- [A false positive: a short or common value matches by chance] → the three keys are long random strings. A match
  is worth failing on anyway.
- [The apply job applies a plan made before this change] → each apply uses a plan its own run made, so there's no
  such plan. Old plan files on disk can't be applied after an apply has changed the state's serial anyway.

## Migration Plan

1. The probe proof (D1), then the live root, the script, the step and the tests on the branch. Local plan:
   `No changes.`.
2. PR: CI's plan runs D2's step and stays green. Its posted plan reads `No changes.` for this change.
3. After merge, main's plan runs the step too. There's nothing to apply from this change.

Rollback: revert the commit. The encryption is unchanged, so the state reads the same before and after.
