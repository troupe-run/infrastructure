# Tasks

## 1. Reproduce the false report (#114)

- [x] 1.1 In `scripts/tests/test_guard_pytest.py`, add a test that builds the throwaway project with a scope `pkg`
  covering `pkg/**` (with `pkg/__init__.py` and `pkg/mod.py`). A test tagged `pkg` imports `pkg.mod`, then an
  untagged `@given(st.integers())` test draws. The test asserts that the run passes. Verify it **fails** on the
  unchanged guard, naming `test_draws` and `pkg/mod.py`, and commit it marked `xfail(strict=True, reason="#114")`
  with the failure quoted in the message
- [x] 1.2 Add the guard's other side: an untagged `@given` test that opens `pkg/mod.py` in its own body fails, naming
  the file and the `pkg` tag. Verify it passes on the unchanged guard (it pins what must not change)

## 2. Skip Hypothesis's own reads (design D1)

- [x] 2.1 In `scripts/guard_pytest.py`, name the file (`hypothesis/internal/constants_ast.py`) as a module constant,
  and make `_record` skip an in-repository read when a frame on the stack comes from it, with `\` normalised to `/`.
  Update the module docstring's account of what counts as a read. Verify by removing 1.1's xfail: both tests pass
- [x] 2.2 Verify `uv run mypy --strict scripts` and `uv run ruff check scripts` are clean, and that `guard_pytest`
  still imports nothing outside the standard library (`grep -n "^import\|^from" scripts/guard_pytest.py`)
- [x] 2.3 Time `uv run pytest scripts/tests/test_guard_pytest.py` before and after 2.1, and record both. Before: 19.98, 19.46,
  19.80 s (30 passed, 1 xfailed). After: 17.25, 19.74, 19.81 s (31 passed). No measurable cost

## 3. Integration

- [ ] 3.1 Copy the new `scripts/guard_pytest.py` into a scratch checkout of troupe's `cache-vcs-state` branch and run
  its full suite with `-n 10` three times. Verify no run reports the false read (it failed one run in two before)
- [ ] 3.2 Run `uv run scripts/check.py` and `openspec validate guard-hypothesis-reads --strict`, and verify both pass
- [ ] 3.3 Run `uv run scripts/tofu.py plan` after rebasing onto `origin/main`, and verify it shows only
  `scripts/guard_pytest.py` updated in place in troupe and website. Keep it for the pull request

## Workflow follow-up

- Open the pull request with a Conventional title and `Closes #114`, the evidence from 1.1, 2.3 and 3.1, and the plan
  from 3.3. CI must be green on all three OSes before the delivery is planned.
- Archive the change on the branch before merging. The owner merges by rebase and approves the `apply` job, which
  delivers `scripts/guard_pytest.py` to troupe and website.
- After the apply, confirm troupe's delivered file matches `main` here, then carry on with troupe-run/troupe#75.
- Comment on #114 with the pull request and the archived change, check it's closed, and check its roadmap card says
  Done.
