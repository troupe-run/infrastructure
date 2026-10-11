# Proposal

Issue: #5 (part of #1)

## Why

`main` is unprotected on every repo in the org (a finding from `adopt-org`). Anyone with write access, or an agent
using the owner's credentials, can push to it directly, force-push over its history, or delete it. The workflow
says every change arrives by pull request and is merged with a rebase, but today nothing on GitHub enforces that. The
rules in this change don't depend on any check's name, so they can land now, before the guard moves here.

## What Changes

- **A repository ruleset on `main`** for `troupe`, `infrastructure` and `troupe-run.github.io`, declared once in the
  shared repository module:
  - no direct pushes: every change arrives through a pull request, with no approval required (there is one
    maintainer);
  - pull requests merge by **rebase only**;
  - linear history;
  - no force-push and no deletion.
- **The owner's bypass applies to pull requests only.** An org owner can merge a pull request that a rule would
  block, but can't push to `main` directly. Break-glass is to change the ruleset itself. Org owners always can,
  and the next plan shows it as drift.
- **Each rule is proven on a throwaway repo first.** The ruleset behaviours tested on GitHub Free so far are
  required checks, no force-push and linear history. Pull-request-only and the bypass weren't.
- **A plan for the three live repos,** approved by the owner, then the apply.

Out of scope:
- required status checks, which come in `required-checks` once the guard's check name is final;
- `troupe-run/.github`, which gets its own ruleset (only the App may push) in `required-checks`;
- the repos' merge settings (merge commits still offered). `required-checks` tidies them, and this ruleset already
  refuses anything but a rebase on `main`.

## Capabilities

### New Capabilities

- `rulesets`: the rules GitHub enforces on the org's branches: which repos and branches they cover, what they refuse,
  who can bypass them, and how the owner keeps control.

### Modified Capabilities

None. `repositories` is unchanged: its requirements cover settings, and the ruleset is a separate capability.

## Impact

- **`tofu/modules/repository`:** a `github_repository_ruleset`, switched on per repo. `.github` has it off.
- **GitHub:** three new rulesets. After the apply:
  - `git push origin main` is refused for everyone, the owner included;
  - pull requests show only "Rebase and merge".
- **Agents:** a session that tries to push to `main` is refused by GitHub, not just by local habit.
- **No change to the workflow:** issues, branches and PRs merged by a rebase are already how work lands.
