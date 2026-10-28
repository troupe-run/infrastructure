# Tasks

## 1. An undecodable troupe spec is unreadable by name (#203; spec labels, "A troupe spec that can't be read is reported by name"; design D4)

- [ ] 1.1 In `scripts/tests/test_oob.py`, let `fake_github` serve a spec's raw `content` unencoded (a `raw_spec_content`
  map, name to content). Then write two tests named for what they check, next to
  `test_a_failed_spec_read_is_unreadable_naming_the_spec`: content that isn't valid base64 (`"abc"`, bad padding),
  and base64 of bytes that aren't UTF-8 (`base64.b64encode(b"\xff\xfe")`). Each asserts no difference, and
  `report.unreadable` is exactly `troupe specs: couldn't read 'cli''s spec.md (<the decode error's words>)` followed
  by the "label descriptions: not checked" line. Verify both fail on `main`'s code with the unnamed `troupe specs:
  couldn't read it (...)` message.
- [ ] 1.2 Move the decode in `scripts/oob.py`'s `spec_documents` inside the fetch's `try`. Verify
  `uv run pytest scripts/tests/test_oob.py` passes, the existing fetch-failure test unchanged, and commit.

## 2. The gate's superseded outcome (#202; spec ci-apply, "A scheduled or manual plan superseded by a newer merge plans nothing", "A red main fails ..."; design D1, D2)

- [ ] 2.1 In `scripts/tests/test_main_ci.py`, extend `FakeCI` to answer `api repos/.../compare/<sha>...main` from a
  given answer (or raise `ReadError`), recording that it was asked. Write tests first, each named for what its body
  checks: a cancel with `main` ahead by a merge is superseded (passed, `superseded`, summary names both short shas
  and the cancelled run's link, no "isn't green" heading); a cancel with `main` identical fails as red; a cancel with
  only the state file changed since fails as red; `behind`, `diverged` and an unknown status each fail, naming the
  status; a failed compare read fails with its error; a compare answer of the wrong shape fails; more commits than
  listed names "`main`'s head" with no sha; `failure`, `timed_out` and the other non-success conclusions fail
  **without** asking compare. Change `test_every_conclusion_but_success_fails` so its `cancelled` case has `main`
  unmoved, and say so in its name or a comment. Verify the new tests fail before 2.2.
- [ ] 2.2 Add the compare read and `Result.superseded` to `scripts/main_ci.py` per D1 and D2, `STATE_PATH` still from
  `plan_target`, and update its module docstring (the outcomes and the stdout line). Verify
  `uv run pytest scripts/tests/test_main_ci.py` passes.
- [ ] 2.3 Write tests of `main()` first: a pass prints exactly `superseded=false` on stdout and exits 0; a superseded
  run prints exactly `superseded=true`, appends its summary and exits 0 with no `::error::`; red prints nothing to
  stdout that isn't `name=value`, and exits 1 with the annotation as now. Update `main()`, moving "CI passed on" to
  stderr. Verify `uv run pytest scripts/tests/test_main_ci.py` passes and `uv run scripts/check.py` is clean
  (mypy --strict, ruff), then commit.
- [ ] 2.4 Run the gate read-only against this repository's real `main` after a fetch
  (`GH_TOKEN` from `gh auth token`, `python3 scripts/main_ci.py --main origin/main --repository
  troupe-run/infrastructure --summary <scratch file>`). Verify stdout is one `superseded=` line and the summary
  names the right commit (compare with `gh run list --workflow ci.yml --branch main --event push -L 3`). Also run the
  compare read for run 40510801628's commit `60b5253` against today's `main` and verify it would read as superseded.
  Record both in the pull request.

## 3. The workflow skips the plan on a superseded run (#202; design D2, D3)

- [ ] 3.1 In `scripts/tests/test_main_ci_workflow.py`, extend `problems()` first: the gate has `id: ci` and appends
  stdout to `$GITHUB_OUTPUT`; every plan step after the gate, except `Keep the saved plan for the apply job`, has
  `steps.ci.outputs.superseded != 'true'` in its `if:`. Add mutations, each caught: the gate's id dropped, its
  output not redirected, and the condition taken off `Plan` and off the guard wait. Update the module docstring.
  Verify the new checks fail on the current `tofu.yml`.
- [ ] 3.2 Update `.github/workflows/tofu.yml`: give the gate `id: ci` and `>> "$GITHUB_OUTPUT"`, add the condition to
  each later step's `if:`, and update the gate's comment and the header table's line about a red `main`. Verify
  `uv run pytest scripts/tests/test_main_ci_workflow.py scripts/tests/test_plan_target_workflow.py` passes, and
  `uv run scripts/check.py` is clean (it runs actionlint if the repository does), then commit.

## 4. Specs and docs (spec ci-apply; design D1)

- [ ] 4.1 README "Running a plan": after the paragraph on the CI wait, say that a run whose CI a newer merge
  cancelled plans nothing and fails nothing, that its summary names both commits, and that the newer merge's run
  plans `main` once CI passes on it. Verify the paragraph matches D1's cases (state-only and unmoved still fail),
  and `uv run scripts/check.py` is clean, then commit.
- [ ] 4.2 Run `openspec validate red-main-and-undecodable-spec --strict` and verify it passes.

## 5. Evidence

- [ ] 5.1 Run `uv run scripts/check.py` on the branch and record the result. Verify the pull request's plan shows no
  changes, since nothing in `tofu/` changes.

## Workflow follow-up

- Open one pull request with `Closes #202` and `Closes #203`. Act on Claude's review of the last push.
- Archive the change on the branch before merging; the owner merges by rebase through the merge queue.
- After the merge, check both issues are closed and their cards say Done, and comment on each with the pull request
  and the archived change.
