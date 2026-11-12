# Tasks

## 1. Reproduce the false report (#298)

- [ ] 1.1 In `scripts/tests/test_guard_pytest.py`, add a project builder for design D3: the helper's declaration plus
  scopes `alpha` (`alpha/**`, tests `alpha/tests/**`) and `beta` (`beta/**`, tests `beta/tests/**`), with
  `alpha/data.txt`, `beta/data.txt`, `alpha/tests/test_alpha.py` (a test reading `alpha/data.txt`, and one reading
  `docs/a.md`), and `beta/tests/conftest.py` with a fixture reading `beta/data.txt` that `beta/tests/test_beta.py`
  uses. Start from troupe's draft (`selection_test.py` from the #365 session), changed to the file's `project()` and
  `run_pytest` style
- [ ] 1.2 Add `test_tests_from_two_scopes_selected_by_node_id_pass` over `PARALLEL`: select the clean `alpha` and
  `beta` tests by node id, and assert the run passes with no `guard:` line. Verify it **fails** on the unchanged
  guard, charging a test with the other module's source or `.pyc`, and commit it marked
  `xfail(strict=True, reason="#298")` with the failure quoted in the commit message
- [ ] 1.3 Add `test_a_module_level_read_in_a_selection_by_node_id_counts_for_its_module_only` over `PARALLEL`: a
  module under `alpha/tests/` reads `docs/a.md` at import; select one of its tests and the `beta` test by node id, and
  assert that test fails naming `docs/a.md` and `docs`, and the `beta` test passes. Verify it **fails** on the
  unchanged guard (the `beta` test is charged too), and commit it with 1.2, marked the same way
- [ ] 1.4 Add `test_an_untagged_read_in_a_selection_by_node_id_fails_only_that_test` over `PARALLEL`: the selection of
  1.2 plus the `alpha` test reading `docs/a.md`. Assert exactly one `guard:` line, naming that test, `docs/a.md` and
  the `docs` tag, and that the other two tests pass. Verify it passes on the unchanged guard serially, or record what
  it reports if the false report also fails the others, and mark it like 1.2 if so

## 2. Charge a collection read to the innermost collector (design D1, D2)

- [ ] 2.1 In `scripts/guard_pytest.py`, add the `_COLLECTING` stack, make `pytest_make_collect_report` push and pop
  its window there (by identity), and make `_record` add to every `_RECORDING` window and to `_COLLECTING[-1]` only,
  returning early when both are empty. Update the docstrings of `_RECORDING`, `_COLLECTING` and the module to say
  what a collection read counts for. Verify by removing the xfail marks from section 1: every test in
  `scripts/tests/test_guard_pytest.py` passes, including the existing module-level and parametrize tests
- [ ] 2.2 In `docs/development-workflow.md`, "Every test run checks the tags", add that a file opened while a module
  is collected (its imports, a module-level read, parameters built from a file) counts for that module's tests only,
  however the run selects them. Verify the paragraph matches the delta spec's requirement
- [ ] 2.3 Verify `uv run mypy --strict scripts` and `uv run ruff check scripts` are clean, and that `guard_pytest`
  still imports nothing outside the standard library (`grep -n "^import\|^from" scripts/guard_pytest.py`)
- [ ] 2.4 Time `uv run pytest scripts/tests/test_guard_pytest.py` three times before and after 2.1, and record both
  here

## 3. Integration

- [ ] 3.1 Copy the new `scripts/guard_pytest.py` into a scratch clone of troupe's `main`. Run troupe#365's command
  (tests from several packages by node id) serially and with `-n 2`, and verify no `guard:` line. Then run troupe's
  full suite with `-n 10`, and verify it reports no guard failure the unchanged guard doesn't. Record both
- [ ] 3.2 Run `uv run scripts/check.py` and `openspec validate guard-pytest-selection --strict`, and verify both pass
- [ ] 3.3 Run `uv run scripts/tofu.py plan` after rebasing onto `origin/main`, and verify it shows only
  `scripts/guard_pytest.py` updated in place in troupe and website. Keep it for the pull request

## Workflow follow-up

- Open the draft pull request with a Conventional title and `Closes #298`, the evidence from 1.2-1.4, 2.4 and 3.1, and
  the plan from 3.3. CI must be green on all three OSes before the delivery is planned.
- Act on Claude's review of the last push, mark it ready, and archive the change on the branch before merging. The
  owner merges by rebase and approves the `apply` job, which delivers `scripts/guard_pytest.py` to troupe and website.
- After the apply, confirm troupe's delivered file matches `main` here, and tell the troupe session for #362/#365 so
  troupe PR #385 can add its test and close troupe-run/troupe#365.
- Comment on #298 with the pull request and the archived change, check it's closed, and check its roadmap card says
  Done.
