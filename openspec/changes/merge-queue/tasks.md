# Tasks

## 1. Probe (design D1)

- [ ] 1.1 Add `probe_merge_queue` to `tofu/probe/main.tf` (the module's ruleset with the `merge_queue` block of D2 and
  the probe's required checks: a workflow job that runs on `merge_group`, one skipped there by `if:`, and `DCO`), with
  its run instructions in the file's header comment; verify `tofu fmt -check` and `tofu validate` pass in `tofu/probe`
- [ ] 1.2 Create public `troupe-run/infra-probe-merge-queue`, ask the owner to add it to the infrastructure App's and
  the DCO App's installations, then apply the probe after the owner approves its plan; verify the ruleset shows the
  merge queue rule (`gh api repos/troupe-run/infra-probe-merge-queue/rulesets/<id>`), or record that the Free plan
  refuses it and stop here for the owner
- [ ] 1.3 Queue a signed-off pull request and record: it lands by rebase under linear history, `main`'s head equals
  the queue's tested commit, DCO reports from the `dco` App on the merge group, and the `if:`-skipped job reports
  skipped and doesn't block; verify each with the merge group's check runs (`gh api .../commits/<sha>/check-runs`)
- [ ] 1.4 Record what DCO does with a sign-off name that differs from the author's GitHub profile name, whether the
  queue's `gh-readonly-queue/main/...` push starts a `push` workflow, and whether a person can push a branch with that
  prefix; verify each with the run list and the push's response
- [ ] 1.5 Record that the App's `always` bypass still pushes to `main` directly, and that the owner can still merge
  past a failing check without the queue; verify with the push and merge results
- [ ] 1.6 Write the answers into design.md as "Probe results", with what each one changes. If the queue isn't
  offered, or DCO doesn't report, stop and take it back to the owner on #169. Verify by deleting the probe
  repository and the probe's local state, and by `gh repo view` reporting it gone

## 2. The guard judges a merge group (design D3)

- [ ] 2.1 Write tests first in `scripts/tests/` for `github_ci_inputs` on a `merge_group` event (range
  `base_sha..head_sha`, branch `main`, no title, description or repository), for an event missing either commit
  (refused under `commit-branch-change` with the re-run fix), and for a pull request from a branch named
  `gh-readonly-queue/main/pr-1-abc` (still judged by the branch rule); verify they fail on main's `guard.py`
- [ ] 2.2 Teach `github_ci_inputs` and `run_ci_entry` the `merge_group` event; verify the 2.1 tests and the guard's
  full suite pass, with `GITHUB_ACTIONS` both set and unset (memory: CI runs pytest with it set), and mypy --strict
  and ruff are clean
- [ ] 2.3 Add `merge_group: types: [checks_requested]` to `.github/workflows/guard.yml`, narrow its `push` to
  `["**", "!gh-readonly-queue/**"]`, and update its header comment; verify with a test that reads the workflow's
  triggers, and with `uv run scripts/check.py`
- [ ] 2.4 Run the branch's `guard.py ci` over a fresh scratch clone of troupe with `GITHUB_REPOSITORY=troupe-run/troupe`
  and a synthetic `merge_group` payload whose range is troupe's last few commits on main (memory: probe the guard on a
  troupe clone); verify it passes, and fails when one commit's message is made non-conventional
- [ ] 2.5 Document the merge group's handling and the queue branch's exclusion in `docs/development-workflow.md`;
  verify the doc names both new requirements and that `uv run scripts/check.py` passes

## 3. CI and the plan on the queue (design D4, D5)

- [ ] 3.1 Add `merge_group:` to `.github/workflows/ci.yml`, keeping `changes` pull-request-only so a merge group runs
  in full, and update its header comment; verify with a test in `scripts/tests/` that a `merge_group` run's `check`
  and guard legs have no condition that skips them
- [ ] 3.2 Add `merge_group:` to `.github/workflows/tofu.yml` with a concurrency group of `tofu-mq-<head_sha>` for it,
  leaving every job but `pr-plan` unreachable on that event and `pr-plan` skipped by its `if:`; verify with a test
  that only `pr-plan` can report on `merge_group`, that it can't run there, and that the concurrency group never
  resolves to `tofu-main` for it
- [ ] 3.3 Extend `scripts/tests/test_required_checks.py`: when infrastructure's queue switch is on, every workflow
  defining one of its required GitHub Actions checks runs on `merge_group`; verify it fails with the trigger removed
  from `ci.yml`, naming the check and the workflow
- [ ] 3.4 Update the header comments that describe each run (ci.yml's run list, tofu.yml's table) to include the merge
  queue; verify by reading them against D4 and D5, and with `uv run scripts/check.py`

## 4. The ruleset's switch (design D2)

- [ ] 4.1 Add `merge_queue` (bool, default `false`) to `tofu/modules/repository/variables.tf`, the dynamic
  `merge_queue` block to the `protect main` ruleset with D2's values, and a precondition refusing it unless
  `main_ruleset` is `pull-request`; verify `tofu fmt -check` and `tofu validate`, and a local plan (fast-forwarded onto
  origin/main first) showing no change while every repository's switch is off
- [ ] 4.2 Update the ruleset's comment and `strict_required_status_checks_policy`'s comment to say the queue, not
  strict, guards combinations; verify by reading against D2

## 5. Docs for the new merge step

- [ ] 5.1 Change the merge step in CLAUDE.md, `org-profile/CONTRIBUTING.md` and `docs/standard-changes.md` to
  "add to the merge queue", where a repository's queue is on; verify with `grep` that no doc still says the owner
  merges by rebase without the queue, and that `uv run scripts/check.py` passes

## 6. troupe and website (design D6)

- [ ] 6.1 Open an issue in troupe-run/troupe and one in troupe-run/website, each with `--project "troupe roadmap"`,
  asking for `merge_group:` on the workflow behind `check` (troupe) and `test` (website), run in full on that event;
  and one in troupe-run/infrastructure to turn on their queues once those merge; verify each is on the board
  (`gh issue view <n> --json projectItems`) and all three are linked from #169

## 7. Turn on infrastructure's queue (design D7)

- [ ] 7.1 Set `merge_queue = true` for infrastructure only in `tofu/repositories.tf`; verify a local plan, fast-forwarded
  onto origin/main first, shows only the `merge_queue` block added to infrastructure's `protect main` ruleset, besides
  the guard's delivered files to troupe and website
- [ ] 7.2 Open the pull request (`Closes #169`); verify its posted plan matches 7.1's and every required check passes

## Workflow follow-up

- Archive the change on the branch, rebase onto main's state commit, and ask for the plan approval once (memory:
  archive before plan approval). The owner merges by rebase, which is the last merge without the queue.
- After the owner approves the apply of `main`: check that infrastructure's ruleset on GitHub has the merge queue rule
  with `merge_method: REBASE`, that the delivered `guard.yml` and `guard.py` reached troupe's and website's `main`,
  and that their `guard` runs there passed.
- Check that the next infrastructure pull request lands through the queue: its merge group's `check`, `guard tests`,
  `guard (workflow rules)` and `DCO` pass, `plan (pull request)` reports skipped, and `main`'s head equals the tested
  commit. If it stalls, turn the switch off in a pull request and reopen #169.
- Comment on #169 with the PR and the archived change, check it's closed and its card says Done.
- Website's and troupe's queues are turned on under the infrastructure issue from 6.1.
