# Tasks

## 1. The script: plan and apply

- [x] 1.1 Add `scripts/board_options.py` with `plan` and `apply` (design D1-D4, D7). Standard library only, calling
      GitHub through `gh api graphql` with an injectable fetch, as `oob.py` does. `--project` defaults to 1 and
      `--labels` to `tofu/labels/troupe.json`. Verify with tests in `scripts/tests/test_board_options.py`, each named
      for what it checks:
      - an option whose description differs from its label's is listed, with from and to;
      - a matching option, and an option with no label, aren't;
      - the list `apply` sends is every option read, in order, each with its id, name and colour unchanged, and only
        the planned descriptions changed (D2);
      - an option with no id, or an empty one, refuses naming it, and the send was never called (D2; spec: "never
        sent without their identity");
      - a field that differs from the plan's `before` (an option added, removed, renamed, recoloured, reordered, or a
        description edited) refuses naming the difference, and nothing is sent (D3);
      - a read-back after the send that differs from what was sent fails (D1);
      - `apply` on project 1 refuses unless `GITHUB_ACTIONS` is `true` (D7);
      - a missing field, or one that isn't a single select, refuses naming it;
      - a plan with no changes writes an empty `changes` and a summary saying so.

      Then `uv run scripts/check.py` passes, with ruff and `mypy --strict` clean
      Done 2026-10-26: `test_board_options.py` covers each case, plus the summary's table (a pipe escaped), only `cap:`
      labels read, a non-plan file refused, and `main` exiting 1 on a refusal. The GraphQL request goes to `gh api
      graphql --input -` as a JSON body, so the option list is passed as a variable. 24 passed;
      `uv run scripts/check.py`: all gates passed (ruff, `mypy --strict`, tests, tofu)
- [x] 1.2 Run `uv run scripts/board_options.py plan --out <scratchpad>/board-plan.json --summary <scratchpad>/board.md`
      against the live board with a read-only login. Verify and record here: 36 changes, every option's name matches a
      label (`infrastructure`'s current description differs from its label's), and the summary reads correctly
      Done 2026-10-26 with the owner's login, reading only: field `PVTSSF_lADOE-8w_M4Bmhi5zhlKO1A`, 36 options in
      `before`, 36 changes, so every option has a label. `infrastructure` goes from "The troupe-run org's own setup
      (troupe-run/infrastructure), not a troupe capability" to its label's "The troupe-run org's own setup, not a
      troupe capability"; the other 35 from *(none)*. The summary's table renders each as option, now, after

## 2. The probe (the owner, on a throwaway project)

- [ ] 2.1 Ask the owner to run design D6's probe in their own terminal, giving them the exact commands and a probe
      labels file in the scratchpad. Read back with `gh api graphql` and record here: each option kept its id and got
      its description (the longest label description, so GitHub's length limit is tested), both draft items kept
      their values, and the second run refused naming `effects`. The owner deletes the project afterwards. If an item
      lost its value, stop and take it to the owner before any further task

## 3. The drift check compares descriptions

- [x] 3.1 In `scripts/oob.py`, read `options{name description}` and report each option whose description differs from
      its label's, using the same comparison as `board_options.py` (design D4, D8). Verify with tests in
      `scripts/tests/test_oob.py`: a stale description is reported naming the option and the board; matching
      descriptions report nothing; an option with no label gets only the existing "no label" difference. Then
      `uv run scripts/check.py` passes
      Done 2026-10-26: `oob.py` imports `description_changes` from `board_options.py`, so the two compare alike. The
      test fixture's options now carry their labels' descriptions. Four tests added (stale reported naming the option
      and board, matching reports nothing, no-label option gets only its existing difference, the query reads
      `description`); `test_oob.py` 85 passed, ruff and `mypy --strict` clean
- [x] 3.2 Run `uv run scripts/oob.py` locally. Verify it reports the 36 differing descriptions as differences and nothing
      else new about the board, and record the count here
      Done 2026-10-26 with the owner's login: 36 differences, all "board capabilities: … option '<name>' has the
      description …", one per option (35 blank, `infrastructure`'s longer text), and nothing else
- [x] 3.3 Update `oob/README.md`'s board row: descriptions are compared too, and set by the `tofu` workflow's `board`
      job after an approved apply; options are still added and removed by the owner. Verify the row names the script
      and the spec
      Done 2026-10-26: the row names `scripts/board_options.py`, the plan and the `board` job, and `spec: labels`

## 4. The workflow

- [x] 4.1 In `.github/workflows/tofu.yml` (design D1): the `plan` job mints a read-only infrastructure App token
      (`permission-organization-projects: read`) and runs `board_options.py plan` into `tofu/board-plan.json`, adds
      its summary under the OpenTofu plan, counts its changes in the `changes` output and the approval line, and
      carries the file in `main-tfplan`. A new `board` job, `needs: [plan, apply]`, runs only when the apply succeeded
      and the board plan has changes, in the `board` environment, with the board App's token
      (`permission-organization-projects: write`), and runs `board_options.py apply`. Update the header diagram.
      Verify with workflow tests beside the existing ones for `tofu.yml` (the `board` job's environment, condition,
      token permission and `needs`; the plan token is read only), then `uv run scripts/check.py` passes
      Done 2026-10-26: the plan job's `board-token` (infrastructure App, projects: read) and `board` steps, the
      summary, `changes`/`board_changes` outputs and the artifact; the `board` job as designed. `test_board_job.py`
      checks both parts and names each of 14 ways of breaking them; 16 passed, the existing `tofu.yml` tests pass,
      and `actionlint` is clean. The header diagram has the `board` row
- [x] 4.2 Update `docs/standard-changes.md`'s capability-label steps (design D5): step 6 has the owner add the option
      with its label's description, and step 7 checks the next apply's `board` job left nothing for the drift check.
      Verify the checklist at the end of the section says the same
      Done 2026-10-26: step 6 adds the option with the label's description and says the `board` job sets it
      otherwise; step 7 checks the drift check reports nothing about the board; checklist items 6 and 7 say the same
- [x] 4.3 Make a board that can't be read in the plan job of `main` a reported error, not a failed plan (design D9):
      `board_options.py plan --ci` writes no board plan, an error annotation and an "unread" summary, and exits 0;
      the plan's board token continues on error; the step counts changes only when the board plan was written.
      Verify with tests: in CI an unreadable board is reported and leaves no plan (a stale one removed), outside CI it
      exits 1 naming why, a broken labels file is still an error, and `test_board_job.py` names `plan` run without
      `--ci` and the token step without `continue-on-error`. Then `uv run scripts/check.py` passes
      Done 2026-10-26: 4 tests in `test_board_options.py` and 2 more breakings in `test_board_job.py`; 46 passed
      across both, `actionlint` clean. The spec gained the scenario "A board that can't be read doesn't hold up the
      apply"

## Workflow follow-up

- Archive the change on the branch, then open the pull request with `Closes #166` through `--body-file` (one
  `plan-pr` approval). Its plan comment should show no OpenTofu change from this change. The owner merges by rebase.
- Before the owner approves the first plan of `main` after the merge: save every card's `Capability` value
  (`gh project item-list 1 --owner troupe-run --format json --limit 500`) in the scratchpad, and check the plan's
  summary lists the 36 descriptions. After the `board` job: the next `oob` run reports no board difference, and the
  cards' values compare equal to the saved ones (spec: "keeps every card's value"; #166's "Done when").
- Then: check #166 is closed and its card Done, and comment on it with the PR and the archived
  change.
- `board-credentials`' Purpose names only adding issues; a comment on #143 asks to add "and setting the `Capability`
  options' descriptions".
