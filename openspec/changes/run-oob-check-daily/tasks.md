# Tasks

## 1. Unreadable is an error, for every check (design D3)

- [x] 1.1 In `scripts/tests/test_oob.py`, add failing tests first: a 403 from the issue types read, a projects read
  that `gh` fails because the GraphQL answer carried `errors`, and an org-settings answer with `value: null` each make
  `run` report the check as unreadable (naming the field, for `null`), with no difference reported for any of them.
  Run `uv run pytest scripts/tests/test_oob.py` and see them fail.
- [x] 1.2 Route every read in `run` through one wrapper that turns a fetch failure into `UnreadableError` naming the
  check, and mark org settings `null_is_unreadable` (D3). Verify that 1.1's tests pass and every existing test in
  `test_oob.py` still passes.
- [x] 1.3 Add tests that `null` stays an ordinary value everywhere else. A project whose `shortDescription` is
  declared `null` and reads `null` matches, and one declared with text that reads `null` is a difference, not
  unreadable. Verify both pass, and that the second fails if `null_is_unreadable` is set on projects.
- [x] 1.4 Make `run` go on after a check fails to read, and `main` report every unreadable check and every
  difference. Test that two refused reads and one difference produce two named errors and the difference, and exit 1.

## 2. Checks run only by hand, and `--ci` (design D4, D5)

- [x] 2.1 Test first, then add `BY_HAND` (check name to reason, design D4), holding only App installations, and
  `--ci`. With `--ci`, a `BY_HAND` check makes no read (the test's fetch records calls), and the report names it with
  its reason. Without `--ci`, it's read as today. Any other argument exits 2 with the usage before any read. A test
  pins App installations in `BY_HAND`. Verify with `uv run pytest scripts/tests/test_oob.py`. (Removed again by 3.5.)
- [x] 2.2 Test first, then write the report for CI. `--ci` prints an `::error::` line for each difference and each
  unreadable check, and, when `GITHUB_STEP_SUMMARY` is set, appends a Markdown summary to it: the differences, the
  unreadable checks, the checks that ran, and the by-hand checks with their reasons. Verify with tests of the
  rendered annotations and summary.
- [x] 2.3 Run `uv run scripts/oob.py` with the owner's login, which should show "no differences" with every check run,
  and `uv run scripts/oob.py --ci`, which should name App installations as by hand. Quote both outputs in the PR.
- [x] 2.4 Run `uv run scripts/check.py`, which must pass (mypy --strict, ruff, tests).

## 3. The App's grants and the job (design D1, D2, D5, D6)

- [x] 3.1 The owner grants the infrastructure App org "Issue types: read" and "Projects: read" in its settings, and
  accepts them on the installation. Then declare both in `oob/app-installations.json`, and verify the hand run of
  `uv run scripts/oob.py` shows no App-installations difference.
- [x] 3.2 Probe the token the job will use, before the job depends on it. With the owner present for the 1Password
  prompt, mint an installation token locally from the App's key, with exactly D2's repositories and read permissions.
  Check the action's `permission-*` input names for issue types and projects against its documentation. Never print
  the key or the token. Run `GH_TOKEN=<that token> uv run scripts/oob.py --ci`. Record each read's result in
  design.md's table, replacing "documented, not yet probed". Any check that's still unreadable goes in `BY_HAND`
  (D4), recorded in design.md. Done when `--ci` with that token reports no unreadable check and no
  difference.
- [ ] 3.3 Show a difference failing with that token. After 3.5, run `--ci` with the job's token on a scratchpad copy
  of what `oob.py` reads, with one issue type's description changed, so the worktree isn't touched. Check that it
  exits 1 with an `::error::` line naming the difference, and a summary listing every check. (The plan was a
  test-only path; then #59's `troupe-run-board`, until #59's change declared it on `main`.) Then ask the owner to
  confirm their GitHub notification setting for Actions sends email for failed workflows (D5), and record the answer
  in design.md.
- [ ] 3.4 Add the `oob` job to `.github/workflows/tofu.yml`. It gets the `plan` job's `if`, the `plan-main` environment
  (`deployment: false`), `permissions: contents: read`, and the read-only token from `actions/create-github-app-token`
  (D2) as `GH_TOKEN`. It runs `uv run --no-project scripts/oob.py --ci`, with no `needs:` on `plan` and not needed by
  it. Update the comment at the top of the file. Add a workflow test next to `scripts/tests/test_ci_workflow.py`
  that fails if the job's `if` differs from `plan`'s, its environment isn't `plan-main`, it gains a write permission
  or a write `permission-*` input, it needs or is needed by `plan`, or it doesn't run `oob.py --ci`. Verify each
  failure by mutating a copy of the loaded workflow in the test, and run `uv run scripts/check.py`.

- [x] 3.5 Run App installations in CI too (owner, 2026-10-18; design D4): the probe read all four installations in
  full with the job's token. Remove `BY_HAND`, the skip and its output, and the tests of them. Add a test that
  `--ci` reads the org's installations and that the summary lists App installations among the checks run. Update
  `oob/README.md`, README.md and the job's comment in `tofu.yml`. Verify with `uv run scripts/check.py`, and with
  `grep -rn "BY_HAND\|\.by_hand\|not run in CI" scripts .github oob README.md` finding nothing.

## 4. Documentation

- [x] 4.1 Update `oob/README.md` ("It isn't run by CI…"): where and when the job runs, that App installations is left
  to the hand run (pointing at `BY_HAND` in `oob.py`), that the manual run still goes in a PR that changes
  `oob/`, and D5's notification note (who GitHub emails, and that changing the `cron` line moves it). Update README.md's
  `oob.py` lines to match. Verify with `uv run scripts/check.py`, and check that no "isn't run by CI" wording is left:
  `grep -rn "run by CI" README.md oob/README.md`.

## Workflow follow-up

- Open the PR with `Closes #62`, and quote `scripts/oob.py`'s output (task 2.3) and the probe's results (task 3.2).
- Archive on the branch before the owner merges by rebase.
- After the merge, once CI passes on `main`, check the `oob` job's first run: it passes, its summary lists the checks
  run, App installations among them, and it made no write. Comment on #62 with the PR, the archived change and
  that run's URL, check #62 is closed, and set its card to Done.
