# Tasks

## 1. Probe what GitHub accepts

- [x] 1.1 On two throwaway repositories (`troupe-run/infra-probe-<date>-a` and `-b`), with milestone `0.1.0` on `-a`,
      verify that `gh issue create -R …-a --type Task --milestone 0.1.0`, `gh issue edit <b-epic> -R …-b
      --add-sub-issue <a-issue-url>` and `gh issue edit <b-issue> -R …-b --add-blocked-by <a-issue-url>` all succeed,
      and that `gh api repos/…-a/issues/<n>` then shows the parent and `issues/<b>/dependencies/blocked_by` lists the
      blocker. Record the commands and output in design D2, revise the change before writing the runbook if any is
      refused, then delete both repositories and verify with `gh repo view` that they're gone

## 2. The label checks

- [x] 2.1 In `scripts/tests/test_labels.py`, write the byte-order, name-form and colour checks as functions that
      return problems, each with tests that fail first on a bad list: `cap:cli` before `cap:claude-code-runner`
      (both named), `cap:Workspaces`, `cap:a--b`, `cap:-a` and `cap:` (each named with the form), a `cap:*` label
      coloured `5319E7` (named with the colour), and `cap:infrastructure` coloured `5319E7` (passes). Then add the
      test that `troupe.json` has no problems. Verify the new tests pass, the existing ones are unchanged, and
      `uv run scripts/check.py` passes

## 3. The board check

- [x] 3.1 In `scripts/oob.py`, add the "board capabilities" check (design D4), with tests in
      `scripts/tests/test_oob.py` that fake the GraphQL answer: a declared label with no option and an option with no
      label each give a difference naming it and saying the owner changes the options; matching lists give none; a
      missing field or a non-single-select field is a difference naming the field; a failed read is unreadable, not a
      difference. Verify the tests pass, `uv run scripts/check.py` passes, and `uv run scripts/oob.py` on today's
      `main` lists `runs`, `user-docs` and the 12 spec-level labels as having no option, and nothing else for the
      board
- [x] 3.2 Add the board check's row to `oob/README.md`'s table: what it declares (derived from `troupe.json`), why
      OpenTofu can't manage it, how to read it, and that the owner changes options in the board's field settings.
      Verify `uv run scripts/check.py` passes

## 4. The runbook

- [ ] 4.1 Write `docs/standard-changes.md`: what a standard change is, then the "Capability label" section with
      design D2's steps as commands whose only blanks are `<name>`, `<description>` and `<issue>`, and the checklist
      for the sub-issue's body. Point to it from `oob/README.md`'s "A new capability's label" paragraph and from
      `docs/development-workflow.md`, without writing anything about Purpose records. Verify `uv run scripts/check.py`
      passes, and that each command in the runbook is one the guard allows, by running each step-1 read for
      `cap:stages` (it reports the label as declared) and checking every write against the allow-list in
      `scripts/guard.py`

## 5. After #151, before the merge

- [ ] 5.1 Once #151 has merged and its apply has run, rebase onto `origin/main` and run `uv run scripts/oob.py`.
      Verify it reports only board options, and list them on the pull request for the owner to fix in the board's
      field settings. After the owner has, verify `oob.py` reports nothing for the board's capabilities, and that the
      21 cards that set the field keep their values (`gh project item-list 1 --owner troupe-run`)
- [ ] 5.2 Run `openspec validate capability-label-standard-change --strict` and `uv run scripts/check.py` on the
      rebased branch, and verify both pass

## Workflow follow-up

- Open the pull request with `Closes #152` once groups 1 to 4 are done, saying it merges after #151. No OpenTofu file
  changes, so the plan is empty.
- Archive on the branch after 5.2, before merging; the owner merges by rebase.
- After the merge: check that the next `drift (out of band)` run reports no board difference, that #152 is closed
  with its card Done, and comment on it with the pull request and the archived change. Update #153 to point to
  `docs/standard-changes.md`. Leave #150 open until #151 and #153 are done.
