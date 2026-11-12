# Tasks

## 1. Pin what must not change, and reproduce #285

- [x] 1.1 Before touching `scripts/guard.py`, add `scripts/tests/fixtures/dependabot-285/`: `pyproject.toml` and
  `uv.lock` from `0b0f7d9`, and `b25fc2f.patch` from `git format-patch -1 b25fc2f`. Add a test in
  `scripts/tests/test_guard_dependabot.py` that commits the two files on main, applies the patch with `git am` on
  `dependabot/uv/types-pyyaml-6.0.12.20261030`, and asserts `run_ci` for `troupe-run/infrastructure` doesn't refuse
  it (spec scenario "A subject that leaves out its versions"). Run it on the unchanged guard and verify it fails with
  #301's reason (`b25fc2f's subject 'chore(deps-dev): Bump types-pyyaml' doesn't give one dependency's versions`)
- [x] 1.2 On the unchanged guard, run the existing Dependabot tests (`test_guard_dependabot.py`,
  `test_dependabot_issues.py`) and verify they pass, so they pin today's outcomes for every subject that gives its
  versions (design D6)

## 2. The short-subject reading (design D1 to D5)

- [ ] 2.1 Add `DEPENDABOT_SHORT_SUBJECT` and route a commit to it only when its subject matches neither
  `DEPENDABOT_REQUIREMENT` nor `DEPENDABOT_SUBJECT` (D1). Add a hypothesis test that for any subject either of those
  matches, the short reading isn't taken; verify it passes
- [ ] 2.2 Read the message's first body line as the `Bumps` reading (D2.1), each changed lock file's versions of X
  (D2.2, `uv.lock` with `tomllib`, `package-lock.json` with `json`, at the parent and at the commit), and each changed
  manifest's lines with the requirement line reader (D2.3). Unit-test each reader on #285's real files and on the
  failure shapes (no line, a line naming another dependency, a changelog line further down, X not moving in the lock,
  two versions moving, an unparseable lock, a nested `node_modules/` entry); verify they pass
- [ ] 2.3 Apply D3's agreement and D5's reasons in `dependabot_ineligibility`. Verify 1.1's test now passes and 1.2's
  tests still pass
- [ ] 2.4 Add a git-level test per scenario of "A Dependabot bump whose subject leaves out its versions is read from
  two agreeing sources": message and lock disagree, only one reading, metadata alone, a major update, a manifest line
  of another kind, an unreadable lock file, and a full subject read as before whatever its body and lock say. Verify
  each fails by mutation (break its check and see it fail), then passes
- [ ] 2.5 Add the four-part scenario to the counting tests (`6.0.12.20260906` to `6.0.12.20261030` patch,
  `6.0.12.x` to `6.1.0.x` minor, `6.0` to `6.0.0.1` patch) in both readers; verify they pass
- [ ] 2.6 Add a test that #285's real title, read by `dependabot_issues.read_update`, and its real commit, read by the
  guard, are both a patch; verify it passes

## 3. The old path against the new

- [ ] 3.1 One-off differential run (scratchpad script, not committed): load `origin/main`'s `scripts/guard.py` and the
  branch's, build generated commits (full bump, requirement, garbage and short subjects, with bodies and lock edits
  that agree and disagree), and compare `dependabot_ineligibility`. Verify every disagreement is a short subject, and
  record the counts here.

## 4. Docs and checks

- [ ] 4.1 In `docs/development-workflow.md`'s "Dependabot pull requests" section (and the `commit-branch-change` row),
  say a shortened `Bump X` subject is read from its message's `Bumps` line, its lock files and manifest lines, with
  two agreeing, and how four-part versions count; and that readings that disagree, or fewer than two, take an OpenSpec
  change. Verify the section reads correctly against the spec
- [ ] 4.2 Run `uv run scripts/check.py` (ruff, mypy --strict, pytest, OpenSpec strict validation) and verify it
  passes
- [ ] 4.3 Fast-forward onto `origin/main`, run a local plan, and verify it changes only the delivered
  `scripts/guard.py` in troupe and website

## Workflow follow-up

- Open the pull request closing #301; the owner approves the plan run; act on Claude's review of the last push.
- Archive on the branch before the merge; the owner merges by rebase.
- After the apply delivers the guard, comment `@dependabot rebase` on #285 and verify its `guard` run passes on the
  new head; report, so it can merge and close #288.
- Check #301 is closed and its card is Done.
