# Tasks

The probe (group 1) picks one path: group 2 if GitHub creates a push ruleset on a public repository, group 3 if
not (design D5; owner, 2026-10-13). Task 1.5 deletes the group not taken, so every task left is one that runs.

## 1. Probe on a throwaway repository (design D1)

- [ ] 1.1 Confirm the provider can declare the ruleset. In a scratch directory (not `tofu/`, whose `init` needs the
  passphrase), run `tofu providers schema -json` for `integrations/github` 6.13.0. Check that
  `github_repository_ruleset` accepts `target = "push"`, a `rules.file_path_restriction.restricted_file_paths` list,
  and no `conditions` block. Verify: the schema excerpt is recorded under design D1. If any of the three is missing,
  stop and raise it with the owner.
- [ ] 1.2 Give the module `delivered_paths` and the `delivered files` ruleset (D2): a list of strings, default `[]`.
  The ruleset exists only when the list isn't empty, with the App in `app_bypass_id` as its only bypass actor, and
  a precondition refuses a non-empty list without `app_bypass_id`. Add `probe_delivered_paths` to `tofu/probe`,
  passed to the module, and describe it in the probe's header comment. Leave `troupe`'s module unchanged for now.
  Verify:
  - `scripts/check.py` passes;
  - a local plan of the live root shows no changes;
  - `tofu validate` in `tofu/probe` passes.
- [ ] 1.3 Create `troupe-run/infra-probe-<yyyymmdd>` (public, with a README), and have the owner add it to the
  `troupe-run-infrastructure` App's installation. Set `probe_delivery = true`, `probe_delivery_bypass = true` and
  `probe_delivered_paths` to the probe's delivered files (`scripts/guard.py`, `.github/workflows/guard.yml`,
  `.github/guard-delivery.json`). Plan and apply. Verify, and record GitHub's response either way:
  - the plan shows the push ruleset with those paths and the App as its only bypass;
  - the apply either creates it (`gh api repos/troupe-run/<probe>/rulesets` lists it, `target: push`, active) or is
    refused. If it is refused, skip to 1.5.
- [ ] 1.4 Run D1 steps 2–5, recording each command and GitHub's response. Verify each against the rulesets spec
  delta:
  - the App's delivery to `main` is accepted;
  - a forged-author commit changing `scripts/guard.py` is refused, both pushed to a new branch and pushed to `main`;
  - a contents-API edit of `.github/guard-delivery.json` is refused;
  - a new branch from `main` is accepted, and so is a branch changing only `README.md`;
  - after a path is removed from `probe_delivered_paths` and the change applied, a push to that path is accepted.

  Any surprise stops the change and is raised with the owner.
- [ ] 1.5 Record the findings in design.md, under D1, and in the adopt-org findings memory. Delete the probe
  repository, and remove the probe's local state and `terraform.tfvars`. Then pick the path, and record which in D1:
  - **ruleset created and 1.4 as specified:** delete group 3 from this file;
  - **ruleset refused:** delete group 2. Revert 1.2's module and probe additions, which nothing would use. Delete
    `specs/rulesets/spec.md`, replace `specs/guard-delivery/spec.md` with D5's first block, and write
    `specs/ci-apply/spec.md` from D5's second block.

  Verify:
  - `gh repo view troupe-run/<probe>` reports not found;
  - `git status` shows no probe leftovers;
  - `openspec validate enforce-delivered-files --strict` passes;
  - on the fallback path, a local plan of the live root shows no changes.

## 2. Ruleset path: the ruleset on troupe (design D2, D3, D4)

- [ ] 2.1 Define `local.guard_delivered_paths = sort(keys(local.guard_contents))` in `tofu/guard_delivery.tf`, and
  pass it to `repo_troupe` as `delivered_paths`, with a comment pointing to the spec. Verify:
  - `scripts/check.py` passes;
  - a local plan shows exactly one resource added, `module.repo_troupe.github_repository_ruleset.delivered[0]`,
    restricting the seven delivered paths, with the App as its only bypass, and nothing else changed.
- [ ] 2.2 Show that the paths can't drift from the delivery. In a scratch copy of `tofu/`, add a file to
  `guard_files`. Verify: the plan's ruleset `restricted_file_paths` and its new `github_repository_file.guard` key
  name the same path. Discard the scratch copy.
- [ ] 2.3 Update `docs/development-workflow.md`:
  - the `delivered-file` row and the delivery section (lines 50 and 84): GitHub refuses the change through the
    `delivered files` ruleset; the guard's refusals catch it earlier;
  - Known gaps: replace "The `delivered-file` check trusts the commit's author" with what is left. The owner can
    disable the ruleset on GitHub as a break-glass, and the next plan shows it. Note that the `guard` check runs the
    pushed copy of itself, which is why the ruleset, not the check, is the enforcement.

  Verify:
  - `scripts/check.py` passes;
  - `grep -n "trusts the commit's author" docs README.md` finds nothing.
- [ ] 2.4 Update the README:
  - "How main is protected": the `delivered files` ruleset on troupe;
  - "Delivering the guard": a hand edit to a delivered file in troupe is refused by GitHub, citing this change's
    probe;
  - "To stop delivering": `delivered_paths` is emptied together with the delivery resources (step 2), and before
    `app_bypass_id` is removed (step 3), since the precondition needs the bypass and troupe can't change files the
    ruleset still restricts.

  Verify:
  - `scripts/check.py` passes;
  - a reread of the three sections against the spec deltas finds no claim that contradicts them.

## 3. Fallback path: a plan of main every day (design D4, D5)

- [ ] 3.1 In `.github/workflows/tofu.yml`, add `schedule: - cron: "0 6 * * *"`, let `plan (main)` run for
  `schedule` as for `workflow_dispatch`, and make "Skip the App's own state commit" skip only on `workflow_run`
  events. Update the workflow's header table with the scheduled row. Verify:
  - `scripts/check.py` passes, including `test_required_checks.py` (the plan job still isn't a pull request job);
  - `actionlint` passes, if it can be run with `uvx` or `brew`; otherwise say so;
  - a reread of the skip step shows a scheduled run on the state commit reaching the plan.
- [ ] 3.2 Update the docs:
  - `docs/development-workflow.md`: the `delivered-file` row and the delivery section (lines 50 and 84) say a change
    that gets past the guard shows in the daily plan. Known gaps: replace "The `delivered-file` check trusts the
    commit's author". A forged-author change passes `guard`, also because the check runs the pushed copy of itself.
    It shows in a plan within a day of landing, and stays live until the owner approves the apply that restores it;
  - README, "Running a plan": `main` is also planned daily at 06:00 UTC, drift waits for approval like any plan, and
    GitHub pauses the schedule after 60 days without activity in the repository. `gh workflow enable tofu.yml`
    re-enables it;
  - README, "Delivering the guard": a hand edit in troupe shows in the next daily plan.

  Verify:
  - `scripts/check.py` passes;
  - `grep -n "trusts the commit's author" docs README.md` finds nothing;
  - a reread against D5's spec text finds no contradiction.

## 4. Pull request, apply and live check (design, Migration Plan)

- [ ] 4.1 Open the pull request (`Closes #35`). Verify that every required check passes and that its CI plan, once
  the owner approves the run, shows:
  - **ruleset path:** only the ruleset added on `troupe`;
  - **fallback path:** no changes.
- [ ] 4.2 After the merge, and the owner's approval of the `main` plan if it has changes, verify:
  - **ruleset path:**
    - `gh api repos/troupe-run/troupe/rulesets` lists `delivered files` (`target: push`, active), and its detail
      shows the seven paths and only the App as a bypass actor;
    - the ruleset's paths equal troupe's `.github/guard-delivery.json` list;
    - the next `main` plan shows no changes.

    The refusal itself is shown by the probe (1.4), not on troupe: GitHub behaviour is tested on throwaway
    repositories only, and a forged commit in a troupe clone would have to get past troupe's own hooks.
  - **fallback path:** after the next 06:00 UTC, `gh run list --workflow tofu.yml --event schedule` shows a run, and
    its `plan (main)` job planned (not skipped) and reported no changes.
- [ ] 4.3 Open the follow-up issue for the pre-merge check (design D5, option 2; the owner agreed 2026-10-13):
  outcome, the signature probe it needs, and a link back to #35. Verify: `gh issue view <n>` shows it, and #35's
  closing comment links it.

## Workflow follow-up

- Run `/opsx:archive` on the branch before merging, as the workflow requires.
- After the merge, comment on #35 with the pull request, the archived change, the path taken and the follow-up issue.
