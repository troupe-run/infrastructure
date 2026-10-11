# Design

## Context

See proposal.md for why. The state on 2026-10-11:
- **No repository has a ruleset.**
- **Every merge on every repo has been linear.** `main` has 0 merge commits on `troupe`, `infrastructure` and
  `troupe-run.github.io`.
- **No workflow pushes to `main`.** The website deploys Pages from an Actions artifact, not from a push.
- **The org has one member, the owner, who is an org admin.** Agent sessions push with the owner's credentials.

Provider `integrations/github` 6.13.0, `github_repository_ruleset`:
- `target`, `enforcement`, `conditions.ref_name`;
- `rules`: `deletion`, `non_fast_forward`, `required_linear_history`, and `pull_request`, which takes
  `required_approving_review_count` and `allowed_merge_methods`;
- `bypass_actors`: `actor_type`, `actor_id`, `bypass_mode`.

GitHub's REST docs on bypass actors:
- `OrganizationAdmin` ignores `actor_id`.
- `bypass_mode = "pull_request"` "means that an actor can only bypass rules on pull requests".
- `exempt` skips the rules and the audit entry.

## Goals / Non-Goals

**Goals:**
- One declaration of the rules, which every managed repo inherits, with an explicit off switch.
- Every behaviour in the `rulesets` spec demonstrated on a throwaway repo before the live apply.

**Non-Goals:**
- Required status checks, and `.github`'s ruleset (`required-checks`).
- Org-level rulesets. Only repository rulesets have been tested on Free, and they are enough for three repos.
- Signed commits (`required_signatures`). Commits here are signed off (DCO), not cryptographically signed. Requiring
  signatures would refuse the owner's own pushes to branches, and is a separate decision.

## Decisions

### D1. The ruleset lives in the shared repository module

`modules/repository` gains a `github_repository_ruleset.main`, created when `var.protect_main` is true (the default).
`repo_github` sets it to false until `.github`'s own ruleset arrives. A new repo is therefore protected unless
someone writes that it isn't.

- **Why the module and not a separate file:** the rule set is meant to be identical everywhere. The probe (D5) then
  exercises the same code that protects the live repos.
- **The branch condition is `~DEFAULT_BRANCH`,** rather than `refs/heads/main`. Every managed repo's default branch is
  `main`, and if one is ever renamed, the protection follows it. The spec says `main`, because that's what the
  default branch is.

### D2. The rules

| Rule | Setting | Why |
|---|---|---|
| `pull_request` | `required_approving_review_count = 0`, `allowed_merge_methods = ["rebase"]` | Changes arrive through PRs. There's one maintainer, so requiring a review would block everything. Rebase-only is the workflow's merge. Unlike a squash, it keeps each commit and its message on `main`. |
| `required_linear_history` | on | Refuses merge commits however they arrive |
| `non_fast_forward` | on | No force-push |
| `deletion` | on | `main` can't be deleted |

`dismiss_stale_reviews_on_push`, `require_code_owner_review`, `require_last_push_approval` and
`required_review_thread_resolution` are left off. With no required reviews, they have nothing to act on.

### D3. Owner bypass: `OrganizationAdmin` in `pull_request` mode

| Option | Direct push to `main` by the owner, or an agent using the owner's credentials | PR merge blocked by a rule | Chosen |
|---|---|---|---|
| No bypass actor | refused | refused, so the owner must edit the ruleset | no |
| `OrganizationAdmin`, `always` | **allowed**: an agent session could push to `main` | allowed | no |
| `OrganizationAdmin`, `pull_request` | refused | allowed, with GitHub's explicit bypass | **yes** |

`always` would undo the point of the change for the most likely source of a stray push: an agent running as the owner.
`pull_request` keeps a deliberate, visible route for the owner, merging a PR past a stuck rule, without opening
direct pushes.

- **Break-glass** is editing or disabling the ruleset on GitHub. Org owners can always do that, so the owner can't be
  locked out. The edit shows as drift in the next plan, and an apply restores the ruleset.
- **`OrganizationAdmin` rather than `User`:** it follows the owner role rather than one login. Today that role is
  the owner alone.

### D4. Rollout: one plan, three rulesets, no other change

The plan must show exactly three `github_repository_ruleset.main` creations, for `troupe`, `infrastructure` and the
website, and nothing else. The owner approves that saved plan, and the saved plan is what gets applied. Afterwards:
- the plan is clean;
- `gh api repos/troupe-run/<repo>/rulesets/<id>` for each repo matches what the probe used;
- no live `main` is pushed to as a test, because the behaviour was proven on the probe.

### D5. Proving the rules on a throwaway repo

The owner is the org's only member, and the bypassing actor. Tests run as the owner would therefore show what the
owner can do, not what the rules refuse. So `tofu/probe` gains a `probe_bypass` variable, and the probe runs in two phases against
`troupe-run/infra-probe-<date>`, which must be added to the App's installation by the owner.

**Phase 1: no bypass actor (the rules as they apply to everyone else).**
1. A direct `git push` to `main` is refused.
2. A force-push to `main` is refused.
3. Deleting `main` (`git push origin :main`) is refused.
4. A PR merged with `gh pr merge --merge` is refused, and with `--squash` too.
5. The same PR merged with `--rebase` succeeds, with no review.

**Phase 2: owner bypass in `pull_request` mode.**

6. A direct `git push` to `main` by the owner is still refused.
7. Record what `gh pr merge --merge` does now. It is expected to succeed only with `--admin`. The result is written
   into this design, so the owner knows what the bypass permits.

**Break-glass:**

8. Disable the ruleset with the owner's `gh`. The plan shows `enforcement` returning to `active`, and applying it
   restores the ruleset.

Each step's output goes into the PR. Then the probe repo is deleted.

## Risks / Trade-offs

- [An agent, or the owner, can no longer push a quick fix to `main`] → That is the intent. Everything already goes
  through PRs.
- [A future bot (#23's release PRs) merges with a different method] → release-please opens PRs that the owner merges
  by rebase, so nothing changes. A bot that needs to push gets its own bypass entry, in its own change.
- [The bypass lets the owner merge past a rule without noticing] → GitHub makes the bypass explicit (the `--admin`
  flag, or a checkbox in the UI), and records it in the ruleset's insights.
- [Rulesets refuse the infrastructure repo's own state commit after an apply] → State is committed on the change's
  branch, before the PR merges, as it was for `adopt-org`. `main` only ever receives it through the PR.

## Migration Plan

Apply the three rulesets. To roll back, set `protect_main = false` on a repo, or disable a ruleset on GitHub as a
break-glass, then follow with a PR.
