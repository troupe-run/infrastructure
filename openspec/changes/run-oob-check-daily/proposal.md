# Proposal

## Why

`scripts/oob.py` checks everything OpenTofu can't manage, but only when someone runs it with their own `gh` login.
`oob/README.md` says "It isn't run by CI: CI holds no credentials yet". The daily 06:00 UTC plan sees only what
OpenTofu manages, so a change made by hand to anything declared in `oob/` goes unnoticed until the next manual run.
Since security-scanning (#53) that gap matters more. Dependabot alerts depend on each repository's dependency graph,
and only the code security configuration in `oob/code-security.json` turns that graph on. If the graph were turned
off or the configuration detached, Dependabot would go quiet and no daily run would notice (#62).

## What Changes

- A new `drift (out of band)` job in `.github/workflows/tofu.yml` runs `oob.py` whenever the plan of `main` runs:
  daily at 06:00 UTC, after CI passes on a merge, and on a manual run. It has no `needs` on the plan, so a failure in
  one doesn't hide the other.
- The job reads GitHub with an installation token of the `troupe-run-infrastructure` App. The token is cut down to
  read-only permissions and minted in the `plan-main` environment, which is main-only and needs no approval. It writes
  nothing, and `GITHUB_TOKEN` stays `contents: read`.
- **The owner's choice (#62): a difference reaches the owner as a failed job.** The run fails, and every difference
  becomes an error annotation and a line in the run summary. GitHub then notifies the owner of the failed run. No
  issue is opened, so the job needs no write permission.
- **A check that can't be read is an error, never "no difference".** `oob.py` runs every check, even after one fails,
  collects both the differences and the read failures, names each failure's check, and exits 1 if there are any.
  This covers an HTTP failure, a GraphQL `errors` answer, and a declared field GitHub returns as `null` because the
  token can't see it. Today a 401 or 403 stops the run with a traceback, and a hidden 2FA setting reads as a
  difference instead of as unreadable (design D3).
- **The owner's choice (#62): the App gets two read grants.** The owner grants the infrastructure App organisation
  permissions "Issue types: read" and "Projects: read", so CI can run the issue-type and project checks.
  `oob/app-installations.json` records both grants.
- **CI runs every check, App installations included.** The plan left App installations to a hand run, reading adopt-org
  design D9's 403 as covering it. That 403 was for the repositories an installation covers, a different endpoint. The probe of the job's token read all four installations in
  full, so the owner chose to run it in CI too (2026-10-18). `oob.py --ci` changes only the output: annotations and the
  run summary.
- `oob/README.md`, the README and the comment at the top of `tofu.yml` say that CI now runs the check. The PR-evidence
  instruction to run `oob.py` by hand alongside a plan stays.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci-apply`: two new requirements. What OpenTofu can't manage is checked from CI whenever `main` is planned, with a
  read-only token; and a difference or a read failure fails the job, which runs every check and lists them.
- `org-settings`: "Issue types and the org project are checked for drift" now says the check runs daily in CI, not
  only by hand, and that a value it can't read is an error, never a difference or "no difference".
- `teams-and-access`: "Each App's installation is declared and checked" now says the check runs daily in CI, as well
  as by hand.

## Impact

- `.github/workflows/tofu.yml`: the new job, its App-token step and its permissions.
- `scripts/oob.py`: `--ci`, read failures collected per check, and annotations and run-summary output. `scripts/tests/test_oob.py` gets new tests. A workflow test pins the job's
  trigger, environment, permissions and token scope, alongside `scripts/tests/test_ci_workflow.py`.
- `oob/app-installations.json`: the infrastructure App's two new read permissions.
- The owner, by hand: grants those two permissions in the App's settings and accepts them on the installation.
- No OpenTofu resource changes. `plan-main` already holds `TF_VAR_github_app_pem`, so no new secret is needed.
