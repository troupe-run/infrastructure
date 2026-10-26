# Tasks

## 1. Pin what must stay the same

- [x] 1.1 Before changing `scripts/oob.py`, list in this task the troupe behaviours that stay: a declared label no
  spec names isn't reported; a Purpose that's only re-wrapped isn't reported; a recorded Purpose with no spec is
  reported; a failed read of the spec list is unreadable and the descriptions check is "not checked"; a spec with no
  Purpose section is reported. Check that a test in `scripts/tests/test_oob.py` covers each one, and add any that's
  missing (a failed read of one `spec.md` being unreadable, naming the spec, is the likely gap). Verify the added tests
  pass on the unchanged `oob.py` with `uv run pytest scripts/tests/test_oob.py`. Result: covered already: a label no spec names (`test_a_cap_label_ahead_of_its_spec_is_not_reported`), a re-wrapped Purpose, a record with no spec, a spec with no Purpose. Added `test_a_failed_spec_list_read_is_unreadable_and_purposes_not_checked`, which passed on the unchanged `oob.py` (56 passed). Its "not checked" message later changed on purpose from "spec list" to "specs", since a failed `spec.md` read now leads to it too

## 2. Read the Capability: line (design D1, D2)

- [x] 2.1 Add the parser for the line to `scripts/oob.py` (D2): no Purpose, or a first non-blank line that doesn't
  begin with `Capability`, names no label. A line that begins with `Capability` must fully match the shape with
  distinct labels, or it's malformed. Add unit tests named for what they check: one label; two labels; a blank line
  before it; no Purpose; a first line about something else; and each malformed form (no backticks, text after the
  last label, `;` as separator, a label twice, `Capabilities:`, `Capability:` with nothing after it). Verify they
  pass, and that the "text after the last label" test fails if the match is loosened to a search (check by hand,
  then restore). Result: `capability_labels` with the cases in `test_capability_labels_reads_the_first_non_blank_purpose_line` and `test_a_malformed_capability_line_is_reported_quoting_it`. A first line beginning with `capabilit` in any case is the line, so `Capabilities:` and `capability:` are malformed, not "no label" (D2 and the spec delta corrected to say so). With `fullmatch` changed to `search`, 3 tests failed, including the text-after-the-last-label case. Restored
- [x] 2.2 Replace `unlabelled_specs` with the D1 check: read the folder list and each `spec.md` once, keep the
  contents, and report each spec that names no label, has a malformed line, or names an undeclared label, using D2's
  messages. Rewrite the `troupe specs` tests in `test_oob.py` to the delta's scenarios (a spec without a label, an
  undeclared label, two labels, a label ahead of its spec, a folder without a label of its own name, every spec has
  a label, and each malformed scenario). Each fake spec carries a `Capability:` line copied from troupe's `main`, not
  a made-up shape. Verify the 1.1 tests and the new ones pass. Result: `spec_documents` and `spec_labels`. The tests' `CLI_SPEC` carries `Capability: \`cap:cli\`` as troupe's `cli` spec does on `main`. Added `test_a_failed_spec_read_is_unreadable_naming_the_spec`. 75 passed
- [x] 2.3 Remove `test_an_unlabelled_spec_is_reported_once_and_its_spec_not_read`, whose "not read" no longer holds
  (every spec is read), and add a test that each `spec.md` is fetched exactly once across both checks. Verify it
  passes, and fails if the descriptions check fetches again (check by hand, then restore). Result: removed, and `test_each_spec_md_is_read_once_for_both_checks` added. Having the descriptions check call `spec_documents` again failed it. Restored

## 3. Key the Purpose record by spec (design D3)

- [x] 3.1 Change `stale_descriptions` to compare each spec's Purpose without its `Capability:` line against
  `oob/troupe-spec-purposes.json` keyed by folder, with D3's three messages, which name the spec's labels. Rewrite
  the Purpose tests for the new keys and messages, and add "troupe changes only the labels a spec names" (a changed
  `Capability:` line with the same Purpose reports nothing). Verify they pass with `uv run pytest
  scripts/tests/test_oob.py`. Result: `stale_descriptions(documents, oob_dir)`, with `test_a_change_to_the_capability_line_alone_is_not_a_changed_purpose`. 75 passed
- [x] 3.2 Re-key `oob/troupe-spec-purposes.json` from `cap:<name>` to `<name>`, values unchanged, sorted in byte
  order. Verify with `git diff --word-diff` that only the keys changed, and that 25 entries remain. Result: the old and new files hold the same 25 values in the same order, and only the keys lost `cap:`
- [x] 3.3 Update `oob/README.md`: the `tofu/labels/troupe.json` (derived) row (labels named in each spec's
  `Capability:` line, the shape, one way), the `troupe-spec-purposes.json` row (keyed by spec, without the line), and
  the "A new capability's label" paragraph (a description covers every spec that names the label, and a new spec's
  Purpose is recorded by spec). Update the comments above both checks in `oob.py` the same way. Verify `git grep -n
  "cap:<folder>"` outside `openspec/changes/archive` finds nothing, and `uv run scripts/check.py` passes. Result: the only hit
  left is `openspec/specs/labels/spec.md`, which this change's delta replaces at archive. `check.py`: all gates
  passed

## 4. Declare cap:development and describe cap:flows (design D4)

- [x] 4.1 In `tofu/labels/troupe.json`, add `cap:development` (colour `1D76DB`, D4's description) between `cap:cues`
  and `cap:docs-publishing`, and set `cap:flows`' description to D4's. Verify `uv run pytest
  scripts/tests/test_labels.py` passes (length and "repeats the name" checks), the file stays sorted in byte order,
  and it has 49 labels. Result: 13 passed, 49 labels, sorted in byte order

## 5. Integration checks

- [x] 5.1 Run `uv run scripts/oob.py` against GitHub with the branch's code. Verify the only difference left is
  `App installations: 'troupe-run-review'` (#154), with no `troupe specs` or `troupe labels` line, and record the
  output here. Result (59e4ed2): `App installations: 'troupe-run-review' is on GitHub but not declared`, then
  `oob: 1 difference(s)`, and nothing else
- [x] 5.2 Using the branch's parser, print the labels each of troupe's 25 specs names on `main`. Verify they match
  troupe#169's mapping table row for row, and record any difference here (one would mean the parser or troupe's lines
  are wrong, not the table). Result: all 25 match, with no mismatches
- [x] 5.3 Fast-forward onto `origin/main` if only a state commit is ahead, then run `uv run scripts/tofu.py plan`.
  Verify it shows `github_issue_labels` for troupe changing in place, creating `cap:development` and changing
  `cap:flows`' description, with no label removed and nothing else changing. Record the summary line here. Result: the local plan
  couldn't run, because 1Password's approval timed out (`authorization timeout`) with the owner remote. The PR's CI plan
  for 59e4ed2 stands in for it: `Plan: 0 to add, 1 to change, 0 to destroy.`, `module.repo_troupe.github_issue_labels.this`
  updated in place, `cap:development` added and `cap:flows`' description changed, nothing else. The provider shows a
  set element replaced, but it updates a changed description in place without taking the label off issues
  (cap-label-descriptions design), so the 4 troupe issues with `cap:flows` keep it
- [x] 5.4 Push the branch and open the pull request (`Closes #158`, `Part of #151`), saying the `troupe-run-review`
  drift is #154's. Verify CI passes and the PR's plan comment matches 5.3. Result: PR #160. Every check passes (check, guard tests,
  guard, plan, DCO), and the plan comment matches 5.3

## Workflow follow-up

- Archive the change on the branch before asking for the plan's approval, and rebase onto `main`'s state commit, so
  the approval is asked once.
- After the owner merges and approves the apply, verify on GitHub that `cap:development` exists on troupe-run/troupe
  with the declared colour and description, `cap:flows` has its new description, and the `tofu` workflow's oob job
  shows only the #154 difference.
- Comment on #158 with the PR and the archived change, check it's closed and its card says Done. Comment on #151
  that `cap:development` exists, so its second change (the relabelling, then removing the 12 folded labels and
  `cap:lifecycle`) can start.
