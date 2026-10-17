# Keep the state passphrase out of decrypted plan JSON

## Why

`var.state_passphrase` derives the key that encrypts the committed state and every saved plan, but it's an ordinary
variable marked only `sensitive`. So `tofu show -json` on a saved plan writes it in plain text under
`variables.state_passphrase.value`, and both plan jobs in `.github/workflows/tofu.yml` write that JSON to
`$RUNNER_TEMP/plan.json` for `hook_modes.py` and `plan_checks.py`. Nothing uploads or prints the file today, but one
future step that did would publish the key to the state in a public repository (#80, found during #55's task 4.6).

## What Changes

- **`state_passphrase` becomes ephemeral** in the live root (`tofu/versions.tf`) and the probe root
  (`tofu/probe/main.tf`), like `github_app_pem` and `cloudflare_api_token`, which is the owner's preferred shape
  (#80). OpenTofu then records it in no plan. A scratch run on OpenTofu 1.13.1 has already shown this works:
  - the `encryption` block's `pbkdf2` key provider accepts an ephemeral variable;
  - the plan's JSON has no `state_passphrase` in `variables` and doesn't contain the value anywhere;
  - an apply of the saved plan with the passphrase supplied again decrypts it and succeeds;
  - without the passphrase the apply fails, and with a wrong one it can't load the plan.
  The change proves the same on `tofu/probe/` before the live root.
- **CI refuses a plan that holds a key.** A new step in both plan jobs, run straight after `tofu show -json` and
  before anything else reads the file, fails the job if the plan's JSON contains the value of the App key, the DNS
  token or the state passphrase anywhere. It names the variable, never the value. This turns #55's task 4.6, run by
  hand once, into a check on every plan.
- **An offline test** (`scripts/tests/`) fails if any of those three variables isn't declared `ephemeral` in either
  root, so the regression shows up in `check.py` before a plan is ever made.
- The encryption itself doesn't change: same passphrase, same key derivation, same method. The committed state and
  1Password item stay as they are, and the live plan stays clean.

Out of scope:

- **The billing email in plan JSON.** `var.billing_email` is personal data and is in the decrypted plan JSON too, along
  with every resource attribute. It can't be ephemeral, because the org resource stores it. That's a separate
  question, about whether `plan.json` may ever leave the runner. This change doesn't settle it.
- **A guard rule refusing to upload or print `plan.json`.** That was #80's fallback for the case where ephemeral
  wasn't allowed, and it is.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `state-and-apply`: "A saved plan holds no key" covers the state passphrase as well as the App key and the DNS
  token. It holds in every rendering of the plan, including its decrypted JSON, and CI checks it on every plan it
  makes.

## Impact

- `tofu/versions.tf`, `tofu/probe/main.tf`: `ephemeral = true` on `state_passphrase`, and a comment on why.
- `.github/workflows/tofu.yml`: one new step in each of the two plan jobs.
- New `scripts/plan_secrets.py` and its tests, plus the ephemeral-declaration test. README.md's `scripts/` row.
- No change to the org, the state's encryption, the secrets or 1Password. The PR's plan should read
  `No changes.`
