# Tasks

## 1. The rule (D1 to D4)

- [x] 1.1 In `scripts/tests/test_guard_commit_rules.py`, test first: each refused case from the spec, plus `Vec<u8>`,
  `a <b`, `</details>`, `<!-- x -->`, `&#60;b`, `&amp;lt;` and a fixup naming such a subject, is refused under
  `commit-message`. The reason quotes the text, and the fix names `{NAME}` and backticks. Each allowed case is
  accepted: `a < b`, `<=`, `1<2`, `<3`, `->`, `R&D`, `<https://…>`, `<NAME>` in the body, and trailers with
  addresses after a breaking note. Add a property test: a one-line Conventional Commit is refused exactly when
  the pattern matches it. Verify: the new tests fail on main (`uv run pytest scripts/tests/test_guard_commit_rules.py`).
- [x] 1.2 Implement in `scripts/guard.py`: the pattern, the text D3 judges, and the decision inside
  `commit_message`. Verify: the tests from 1.1 pass, and the existing commit-message tests are unchanged and pass.
- [x] 1.3 `pr_title` passes the markup decision through. Test first: a title with `<NAME>` is refused with the
  markup reason and the edit-the-title fix, not "isn't a Conventional Commit". Verify: fails before, passes after.
- [x] 1.4 The `pre-push` range check and the `guard` check name such a commit. Test first, in the existing
  range-check tests. Verify: fails before 1.2, passes after.

## 2. Docs and size

- [x] 2.1 `docs/development-workflow.md`: the `commit-message` row lists the markup refusal and its fix. Verify: the
  docs tests (`test_guard_docs.py`) pass.
- [ ] 2.2 `uv run scripts/check.py` passes in full, including the size gate on `scripts/guard.py`. Verify: its
  output kept in a scratch file, with the margin left under the ceiling noted in the PR.

## Workflow follow-up

- After the merge, the guard's delivery to troupe and website carries the rule (owner-approved plan).
- Comment on #364 with the PR and the archived change; troupe-run/troupe#484 tracks the troupe side.
