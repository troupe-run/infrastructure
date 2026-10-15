## Why

Agents work with the owner's `gh` login, so GitHub sees one identity. Every GitHub-side rule meant to stop a forgery
has to infer intent from something the pusher controls, such as a commit's author, a branch name or a check's name.
#39 showed where that leads, and even then a pull request could edit its own `ci.yml` to pass. A forged check result
is the same risk as dodgy code the owner approves, and it's caught in the same place: review. Owner, 2026-10-15:
"Github is the wrong place for that, we should be relying on local configuration to manage local behaviour" (#47).

## What Changes

- **Make the release exemption name-based, on troupe only** (`scripts/guard.py`). A `release-please--` branch that
  lives in troupe skips the branch-change rule because of its name. The author check, `RELEASE_AUTHOR_EMAIL`, and
  the rule that the branch must add a commit all go.
- **Keep troupe's `release branches` ruleset, without its `deletion` rule** (`tofu/release.tf`). The ruleset refuses
  everyone, the owner included, except the release App, which acts with its own key from the `main`-only `release`
  environment. That is a rule for everyone, not a guess about who pushed, so it stays. It's what makes the name proof
  on troupe. Owner, 2026-10-15: "only trust branches within troupe, as they're the ones that are enforced... if i
  fork to my own repo, remove checks, call branches weird things, that's external and we shouldn't be trusting it."
  - Dropping `deletion` lets GitHub's delete-on-merge remove the release branch after its pull request merges, which
    the owner wants. Only the App can create it again.
- **Keep `RELEASE_REPOSITORIES` and reading a pull request's head repository.** A branch elsewhere, in this repository
  or in a fork, isn't exempt, because nothing reserves its name there.
- **Keep the daily plan of `main`, reframed.** It's drift detection for everything OpenTofu manages, not a defence
  against forged deliveries. Its comments and docs say so.
- **Keep the delivered-file rule's GitHub check as it is.** It's described as a check for honest mistakes and outside
  contributors, not a security boundary.
- **Write the principle down.** Rewrite the Known gaps entries in `docs/development-workflow.md` on forged deliveries
  and the release exemption, and the README's sections on them. State the principle there, and add it to
  `openspec/config.yaml`'s context so later changes don't design against it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: the release exemption is by the branch's name in a repository that reserves that name for
  the release App, whoever authored its commits.
- `release-credentials`: the ruleset reserves the creation and update of release branches for the release App, and
  no longer refuses their deletion.
- `guard-delivery`: the delivered-file check is described as catching honest mistakes. A change that gets past it,
  forged or not, is ordinary drift that the daily plan shows.

## Out of scope

- Rules that apply to everyone, or that protect a secret rather than an identity. These stay:
  - `protect main`;
  - the required checks;
  - the PR-title check;
  - `plan-pr`'s approval, which keeps the App's key away from any pull request's code;
  - the `release` environment and the release ruleset;
  - the guard's local owner-only rules and `gh` allow-list.
- A separate GitHub identity for agents. It was discussed on #39 and not pursued.
- Putting a release ruleset on other repositories. Only troupe releases.

## Impact

- **Code:** `scripts/guard.py` and its tests in `scripts/tests/test_guard_push_and_ci.py`.
- **OpenTofu:** `tofu/release.tf`, and `tofu/probe/main.tf`'s copy of the ruleset. The plan updates troupe's "release
  branches" ruleset in place, dropping `deletion`, and delivers the changed `scripts/guard.py` to troupe. Nothing else
  changes.
- **Docs:** `docs/development-workflow.md`, `README.md`, `.github/workflows/tofu.yml`'s header comment,
  `openspec/config.yaml`.
- **A throwaway repository** for a probe of delete-on-merge without the `deletion` rule, deleted afterwards.
