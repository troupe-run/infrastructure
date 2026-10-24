# Proposal

## Why

Nothing runs `openspec validate --strict`, so a spec can break strict validation and nobody notices. troupe-run/troupe#155
found two requirements on troupe's main over OpenSpec's 500-character limit. Both had been failing strict validation
for a while. Then a strict run over every spec made any change look broken (#123).

The owner chose the guard over `scripts/check.py` for this (troupe-run/troupe#155, design of `split-long-requirements`):
troupe's `quality-check` spec says no gate in the check reads OpenSpec artifacts, and `scripts/check-paths.toml` skips
the check for commits that stage only `openspec/**`, which are the commits that can break validation. The `guard`
check already runs on every push and pull request, reads OpenSpec changes, and is required.

## What Changes

- **A new guard rule, `openspec-strict`, checked by the `guard` check on GitHub.** In a repository with an `openspec/`
  root, `guard.py ci` runs OpenSpec's strict validation over every main spec and every active change. It fails for
  each spec or change that doesn't pass, naming it, each requirement at fault (by its name, not just its position)
  with OpenSpec's message, and the fix: the command to run locally and the OpenSpec version CI used. Archived changes
  aren't validated: they're a dated record, and `archive-incomplete` already checks their tasks.
- **A pull request is judged on what it touches.** For a pull request or a push to a branch other than `main`, the
  rule validates the main specs and active changes its commits change. It validates everything when they change the
  guard itself (`scripts/guard.py` or `.github/workflows/guard.yml`, which pins the OpenSpec version). So a spec
  that's broken on main never fails an unrelated pull request (owner, 2026-10-24).
- **A push to `main` is validated in full**, whatever it changed, deliveries included. A spec that fails on main, or
  that a new OpenSpec version fails, shows on main's own `guard` run straight away, not months later, and blocks no
  pull request.
- **Missing or unreadable is a failure, not a pass.** When anything is in scope, a run where the `openspec` CLI is
  missing, or prints output the guard can't read, fails saying so. A repository with no `openspec/`, or a run with
  nothing in scope, passes without running OpenSpec.
- **A pin bump is checked against every governed repository first.** The version goes out to troupe and website in
  the same delivery, so `docs/development-workflow.md` says to run the new version over all three repositories'
  main before the delivery plan is approved.
- **The `guard` workflow installs a pinned OpenSpec CLI.** It sets up Node and installs `@fission-ai/openspec` at one
  exact version, named once in `.github/workflows/guard.yml`, with OpenSpec's telemetry off. The job keeps its
  5-minute timeout.
- **`docs/development-workflow.md` lists the rule**, and the `development-workflow` spec gains a requirement for it.
- **Delivered to troupe and website** in the usual way (`guard.py` and `guard.yml`), once CI is green on all three
  OSes and the owner approves the plan. Today every spec and active change passes strict validation in all three
  repositories (infrastructure 17 of 17, troupe 25 of 25, website 9 of 9, with OpenSpec 1.14.3 on 2026-10-24), so the
  delivery doesn't start failing their pull requests. The plan task checks this again against their main.

Not changing: `scripts/check.py` and `scripts/check-paths.toml` in any repository, which still don't read OpenSpec
artifacts, and the local git hooks. The issue asked whether a local hook should run the validation too. The owner chose
CI only (2026-10-24): the required check already stops a broken spec before it merges, and a local hook would need
Node and OpenSpec on every contributor's machine, at the version CI pins (design D7).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: adds requirements that the `guard` check on GitHub fails for a spec or active change in its
  scope that doesn't pass OpenSpec's strict validation, naming it, the requirement and the fix; that a pull request's
  scope is what it touches (everything when it changes the guard); that a push to main is validated in full; and that
  a validation that can't run fails.

## Impact

- `scripts/guard.py` (delivered): the `openspec-strict` rule, run by `guard.py ci`, and its tests in a new
  `scripts/tests/test_guard_openspec.py`, which run with a stub `openspec` on `PATH` (no Node needed by the tests).
- `.github/workflows/guard.yml` (delivered): Node and the pinned OpenSpec CLI before the guard runs.
- `docs/development-workflow.md`: the rule's row, where the OpenSpec version is pinned, and the step for moving it.
- `openspec/specs/development-workflow/spec.md`: the new requirement, at archive.
- Delivery: the next plan shows `scripts/guard.py` and `.github/workflows/guard.yml` changing in troupe-run/troupe and
  troupe-run/website, four file changes in all.
- The `guard (workflow rules)` required check (`tofu/required-checks.json`) keeps its name, so no ruleset changes.
