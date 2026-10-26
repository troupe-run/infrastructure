# Tasks

## 1. One parser for the Capability: line (design D6)

- [x] 1.1 Move `purpose_lines`, `capability_line`, `capability_labels`, `MalformedCapabilityLineError`,
  `CAPABILITY_LINE` and `CAPABILITY_SHAPE` from `scripts/oob.py` into `scripts/guard.py`, unchanged, and import them
  in `oob.py` from `guard`. Verify `uv run pytest scripts/tests/test_oob.py` passes with the test file unchanged, and
  `uv run scripts/oob.py` on `main` reports the same differences as before the move (record both outputs here).
  Result: `test_oob.py` unchanged, 81 passed. `oob.py` imports the parser from `guard` and re-exports
  `capability_labels`, which the test reads as `oob.capability_labels`. `uv run scripts/oob.py` before and after the
  move both print `oob: no differences (.github files, org settings, App installations, issue types, projects, troupe
  specs, troupe label descriptions, code security, milestones, board capabilities)` and exit 0. Python sources have
  no scope in `scripts/check-paths.toml`, so a change to `guard.py` still runs the full check, `test_oob.py`
  included
- [x] 1.2 Add tests in the guard's test suite for the moved parser, called from `guard`: a well-formed line with one
  and with two labels, no Purpose, a first line that isn't the line, `Capabilities:` and `capability:` as malformed,
  a repeated label, and a trailing `(and git)`. Tag them as `scripts/check-paths.toml` requires. Verify they pass, and
  that `guard_pytest` reports no untagged read. Result: `scripts/tests/test_guard_capability_labels.py`, 10 passed;
  the tests read no file, so none needs a tag, and `guard_pytest` reported nothing

## 2. The capability-label rule (design D1, D2, D5)

- [x] 2.1 Add `CAPABILITY_RULE = "capability-label"` to `RULES` (not `OVERRIDABLE_RULES`), and
  `CAPABILITY_REPOSITORIES` naming `troupe-run/troupe`, each with a docstring citing this design. Verify the existing
  rule-list tests (`test_guard_docs.py` among them) fail until 2.5 adds the rule's row, then pass. Result: with
  the rules doc from HEAD, `test_the_docs_list_exactly_the_guard_s_rules` fails (`'command-unparseable' !=
  'capability-label'`); with 2.5's row, 3 passed
- [x] 2.2 Write the scope (D2): from `openspec_scope()` and the head's tree, the main specs to judge and the
  `(change, spec)` deltas whose main spec doesn't exist. Verify with tests for each of the spec's "judges what the
  range touches" scenarios: no spec touched, a delta for an existing spec skipped, everything on a push to `main` and
  on a change to `scripts/guard.py`, and an archive commit judging the new main spec. Result: the scope tests in
  `test_guard_capability_labels.py` pass; replacing the "main spec doesn't exist" filter with `True` fails
  `test_a_delta_for_a_spec_that_exists_isn_t_judged`
- [x] 2.3 Write the rule: it takes the scope, the repository and a labels reader, and returns `ALLOW` outside
  `CAPABILITY_REPOSITORIES` or for an empty scope without calling the reader, else one refusal listing every finding
  as D5 words it, sorted by spec, with the fix for each kind found. Verify with a test per scenario of "A troupe
  spec's capability labels are checked on GitHub", each asserting the names, label and fix text, including the
  standard change's URL with its `#a-capability-label` anchor. Check by hand that the anchor resolves on
  `docs/standard-changes.md` (GitHub's heading slug), and record it here. Result: the rule tests pass; dropping the
  undeclared check fails 5 of them. The heading is `## A capability label`, whose GitHub slug is
  `a-capability-label`. Findings are joined by `; `, as `openspec-strict` lists its items (design D5 updated)
- [x] 2.4 Call it from `run_ci_entry` after `openspec-strict`, with the repository from `GITHUB_REPOSITORY` (the run's,
  not the head's; D1) and the same `notes` line style (`guard: capability-label: judged N spec(s) ...` or why it
  wasn't run). Verify with a `run_ci_entry` test that a fork pull request into troupe is judged, and one that both
  refusals print when both rules fail. Result: 3 CI-entry tests pass (fork judged, both refusals, the passing
  run's log line); passing the head repository instead of `GITHUB_REPOSITORY` fails all 3
- [x] 2.5 In `docs/development-workflow.md`, add `capability-label` to the `guard` check's row of the layer table, and
  the rule's row to the rules table: what it refuses, its scope, that it reads infrastructure's `main` over the
  network, that it's GitHub-only and not overridable, and the fix. Verify `uv run pytest
  scripts/tests/test_guard_docs.py` passes. Result: 3 passed

## 3. Reading the declared labels (design D3)

- [x] 3.1 Write the reader: the contents API URL at `ref=main` with the raw media type, `CAPABILITY_LABELS_TIMEOUT_SECONDS
  = 30.0`, the bearer token from `GITHUB_TOKEN` when set, and a check that the body is a JSON list of objects with a
  string `name`. Any failure raises an error the rule turns into its unreadable refusal. Verify with tests, the
  request injected: a good body, an HTTP error, a timeout, invalid JSON, a list with an entry missing `name`, and that
  the header is sent only when the token is set. Result: 9 reader tests pass (good body and URL and headers,
  token, six unreadable cases, and the rule's refusal for an unreadable read)
- [x] 3.2 Verify the reader against GitHub itself, once, outside the test suite: run it from the branch and confirm it
  returns exactly the label names in `origin/main`'s `tofu/labels/troupe.json` (36 on 2026-10-26). Result: with
  no `GITHUB_TOKEN`, `uv run --no-project python -c 'import sys; sys.path.insert(0, "scripts"); import guard;
  print(len(guard.declared_labels()))'` prints 36, and the set equals the names in `git show
  origin/main:tofu/labels/troupe.json` Record the command and the count here
- [x] 3.3 In `.github/workflows/guard.yml`, add `GITHUB_TOKEN: ${{ github.token }}` to the "Check the workflow rules"
  step's `env`, and mention the labels read in the file's header comment. Verify `uv run scripts/check.py` passes
  (workflow lint included), and `scripts/tests/test_guard_workflow.py` still passes. Result: `scripts/check.py`
  passed on 0fd9bda (1909 passed, 14 skipped for no pwsh). It has no separate workflow-lint gate; the workflow tests
  in it (`test_guard_workflow.py`, `test_guard_delivery.py` among them) pass
- [x] 3.4 Keep the run's token from the OpenSpec CLI: `run_openspec` runs it without `GITHUB_TOKEN` (design D3,
  from Claude's review of #168). Verify the stub test in `test_guard_openspec.py` records no token when one is set.
  Result: `test_the_cli_runs_strict_json_validation_at_the_root_with_telemetry_off_and_no_token` passes, and fails
  when the filter is removed

## 4. Integration checks

- [x] 4.1 Run the rule over a troupe checkout, as CI would, with `GITHUB_REPOSITORY=troupe-run/troupe`: on troupe's
  `main` (a push to `main`, so all 25 specs), and on a scratch branch of it with a new spec's delta naming
  `cap:workspaces`. Verify the first passes and the second fails naming the change, the spec and the label, and
  record both outputs here. Result: in a scratch clone of troupe at `main` e998824, with this branch's
  `guard.py ci --branch main` and `GITHUB_REPOSITORY=troupe-run/troupe`: `capability-label: judged 25 spec(s),
  every spec, against 36 declared label(s)` and `every rule passes for main`, exit 0. On a scratch branch adding
  the change `probe-workspaces`, whose new spec `workspaces` starts its Purpose with ``Capability:
  `cap:workspaces` ``: exit 1, `capability-label: 1 problem(s) with the capability labels specs name: change
  `probe-workspaces`: spec `workspaces` names `cap:workspaces`, which troupe-run/infrastructure doesn't declare
  on main.`, with the standard change's link in the fix. Nothing was pushed
- [x] 4.2 Just before asking for the plan's approval, re-run 4.1's `main` case against troupe's latest `main`, so the
  delivery can't turn it red. Record the commit and the result here. Result: troupe `main` e998824, with this
  branch's guard at 820d288: `capability-label: judged 25 spec(s), every spec, against 36 declared label(s)`,
  `openspec-strict` validated 25 of 25, every rule passes, exit 0
- [x] 4.3 Push the branch and open the pull request (`Closes #153`). Verify this repository's `guard` runs pass and log
  that `capability-label` wasn't run here (not troupe), and that the PR's plan comment changes only the delivered
  `scripts/guard.py` and `.github/workflows/guard.yml`, in troupe and in website. Result: PR #168. Both `guard`
  runs on fcfd4f5 pass and log `capability-label: troupe-run/infrastructure names no capability labels, so it
  wasn't checked.`; all 20 checks pass. The plan for fcfd4f5 is 0 to add, 4 to change, 0 to destroy:
  `github_repository_file.guard` for `scripts/guard.py` and `.github/workflows/guard.yml`, in troupe and website,
  content and commit message in place, with no modes to set. 3.4 changes `scripts/guard.py` again, so the plan is
  re-made on the next push, for the same four files

## Workflow follow-up

- Archive the change on the branch before asking for the plan's approval, and rebase onto `main`'s state commit, so
  the approval is asked once.
- After the owner merges and approves the delivery's apply, verify on troupe's `main`: its `guard` run passes and its
  log says `capability-label` judged every spec. Verify website's `guard` run passes and skips the rule.
- Comment on #153 with the PR and the archived change, check it's closed and its card says Done, and check whether
  #150 can close (all four parts done).
