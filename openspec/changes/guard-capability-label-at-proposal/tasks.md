# Tasks

## 1. One parser for the Capability: line (design D6)

- [ ] 1.1 Move `purpose_lines`, `capability_line`, `capability_labels`, `MalformedCapabilityLineError`,
  `CAPABILITY_LINE` and `CAPABILITY_SHAPE` from `scripts/oob.py` into `scripts/guard.py`, unchanged, and import them
  in `oob.py` from `guard`. Verify `uv run pytest scripts/tests/test_oob.py` passes with the test file unchanged, and
  `uv run scripts/oob.py` on `main` reports the same differences as before the move (record both outputs here)
- [ ] 1.2 Add tests in the guard's test suite for the moved parser, called from `guard`: a well-formed line with one
  and with two labels, no Purpose, a first line that isn't the line, `Capabilities:` and `capability:` as malformed,
  a repeated label, and a trailing `(and git)`. Tag them as `scripts/check-paths.toml` requires. Verify they pass, and
  that `guard_pytest` reports no untagged read

## 2. The capability-label rule (design D1, D2, D5)

- [ ] 2.1 Add `CAPABILITY_RULE = "capability-label"` to `RULES` (not `OVERRIDABLE_RULES`), and
  `CAPABILITY_REPOSITORIES` naming `troupe-run/troupe`, each with a docstring citing this design. Verify the existing
  rule-list tests (`test_guard_docs.py` among them) fail until 2.5 adds the rule's row, then pass
- [ ] 2.2 Write the scope (D2): from `openspec_scope()` and the head's tree, the main specs to judge and the
  `(change, spec)` deltas whose main spec doesn't exist. Verify with tests for each of the spec's "judges what the
  range touches" scenarios: no spec touched, a delta for an existing spec skipped, everything on a push to `main` and
  on a change to `scripts/guard.py`, and an archive commit judging the new main spec
- [ ] 2.3 Write the rule: it takes the scope, the repository and a labels reader, and returns `ALLOW` outside
  `CAPABILITY_REPOSITORIES` or for an empty scope without calling the reader, else one refusal listing every finding
  as D5 words it, sorted by spec, with the fix for each kind found. Verify with a test per scenario of "A troupe
  spec's capability labels are checked on GitHub", each asserting the names, label and fix text, including the
  standard change's URL with its `#a-capability-label` anchor. Check by hand that the anchor resolves on
  `docs/standard-changes.md` (GitHub's heading slug), and record it here
- [ ] 2.4 Call it from `run_ci_entry` after `openspec-strict`, with the repository from `GITHUB_REPOSITORY` (the run's,
  not the head's; D1) and the same `notes` line style (`guard: capability-label: judged N spec(s) ...` or why it
  wasn't run). Verify with a `run_ci_entry` test that a fork pull request into troupe is judged, and one that both
  refusals print when both rules fail
- [ ] 2.5 In `docs/development-workflow.md`, add `capability-label` to the `guard` check's row of the layer table, and
  the rule's row to the rules table: what it refuses, its scope, that it reads infrastructure's `main` over the
  network, that it's GitHub-only and not overridable, and the fix. Verify `uv run pytest
  scripts/tests/test_guard_docs.py` passes

## 3. Reading the declared labels (design D3)

- [ ] 3.1 Write the reader: the contents API URL at `ref=main` with the raw media type, `CAPABILITY_LABELS_TIMEOUT_SECONDS
  = 30.0`, the bearer token from `GITHUB_TOKEN` when set, and a check that the body is a JSON list of objects with a
  string `name`. Any failure raises an error the rule turns into its unreadable refusal. Verify with tests, the
  request injected: a good body, an HTTP error, a timeout, invalid JSON, a list with an entry missing `name`, and that
  the header is sent only when the token is set
- [ ] 3.2 Verify the reader against GitHub itself, once, outside the test suite: run it from the branch and confirm it
  returns exactly the label names in `origin/main`'s `tofu/labels/troupe.json` (36 on 2026-10-26). Record the command and the count here
- [ ] 3.3 In `.github/workflows/guard.yml`, add `GITHUB_TOKEN: ${{ github.token }}` to the "Check the workflow rules"
  step's `env`, and mention the labels read in the file's header comment. Verify `uv run scripts/check.py` passes
  (workflow lint included), and `scripts/tests/test_guard_workflow.py` still passes

## 4. Integration checks

- [ ] 4.1 Run the rule over a troupe checkout, as CI would, with `GITHUB_REPOSITORY=troupe-run/troupe`: on troupe's
  `main` (a push to `main`, so all 25 specs), and on a scratch branch of it with a new spec's delta naming
  `cap:workspaces`. Verify the first passes and the second fails naming the change, the spec and the label, and
  record both outputs here
- [ ] 4.2 Just before asking for the plan's approval, re-run 4.1's `main` case against troupe's latest `main`, so the
  delivery can't turn it red. Record the commit and the result here
- [ ] 4.3 Push the branch and open the pull request (`Closes #153`). Verify this repository's `guard` runs pass and log
  that `capability-label` wasn't run here (not troupe), and that the PR's plan comment changes only the delivered
  `scripts/guard.py` and `.github/workflows/guard.yml`, in troupe and in website

## Workflow follow-up

- Archive the change on the branch before asking for the plan's approval, and rebase onto `main`'s state commit, so
  the approval is asked once.
- After the owner merges and approves the delivery's apply, verify on troupe's `main`: its `guard` run passes and its
  log says `capability-label` judged every spec. Verify website's `guard` run passes and skips the rule.
- Comment on #153 with the PR and the archived change, check it's closed and its card says Done, and check whether
  #150 can close (all four parts done).
