# Tasks

## 1. The ruleset in the shared module

- [x] 1.1 Add `github_repository_ruleset.main` to `tofu/modules/repository`. It is created when `var.protect_main`
  (default true), has an `owner_bypass` variable (default true: `OrganizationAdmin`, `pull_request`), and uses the
  rules in D2 on `~DEFAULT_BRANCH`. Set `protect_main = false` on `repo_github`. Verify: `scripts/check.py` passes,
  and `scripts/tofu.py plan` shows exactly three `github_repository_ruleset.main` creations (troupe,
  infrastructure, website) and nothing else. It is not applied yet.

## 2. Prove the rules on a throwaway repo (D5)

- [x] 2.1 Create `troupe-run/infra-probe-<date>` with a README. The owner adds it to the App's installation. Add
  `probe_bypass` to `tofu/probe` (passed to the module's `owner_bypass`), and import and apply with
  `probe_bypass = false`. Verify: the ruleset exists on the probe, and the plan is clean.
- [x] 2.2 Phase 1, as the owner with no bypass actor: a direct push, a force-push and deleting `main` are each
  refused; a PR merged with `--merge` and with `--squash` is refused; the same PR merged with `--rebase` succeeds
  with no review. Verify: each command's output, quoted in the PR.
- [x] 2.3 Phase 2, applied with `probe_bypass = true`: the owner's direct push is still refused. Record what
  `gh pr merge --merge` does without and with `--admin`, and write the result into D5. Verify: outputs quoted, and
  D5 updated.
- [x] 2.4 Break-glass: disable the probe's ruleset with `gh api`. Verify: the plan shows `enforcement` returning to
  `active`, applying it restores the ruleset, and the plan is clean afterwards.
- [x] 2.5 Delete the probe repo, and its local state and files. Verify: `gh repo view` reports not found.

## 3. Protect the live repos

- [ ] 3.1 Save the plan and show it to the owner. Verify: it contains exactly the three ruleset creations, and the
  owner approves it.
- [ ] 3.2 Apply the saved plan, and commit the encrypted state. Verify: the plan afterwards says "No changes", each
  repo's ruleset read with `gh api` matches the probe's, and `scripts/oob.py` reports no differences.

## 4. Docs and evidence

- [ ] 4.1 Update `README.md`: changes reach `main` only by a PR merged with a rebase, the owner's bypass, and
  break-glass. Verify: the README describes what the probe showed. The archived adopt-org findings stay as they
  are, and #5's closing comment says the "no rulesets" finding is fixed.
- [ ] 4.2 Open the PR closing #5, with the plan, the probe outputs and the apply evidence. Verify: CI and DCO are
  green, and the PR merges by rebase under the new ruleset, which also checks the ruleset from the inside.

## Workflow follow-up

- Archive the change on the branch, then the owner merges with a rebase.
- Comment on #5, and tick `protect-main` on #1.
