# Tasks

## 1. Pin what must stay the same

- [ ] 1.1 Before changing `scripts/oob.py`, list in this task the troupe behaviours that stay: a declared label no
  spec names isn't reported; a Purpose that's only re-wrapped isn't reported; a recorded Purpose with no spec is
  reported; a failed read of the spec list is unreadable and the descriptions check is "not checked"; a spec with no
  Purpose section is reported. Check that a test in `scripts/tests/test_oob.py` covers each one, and add any that's
  missing (a failed read of one `spec.md` being unreadable, naming the spec, is the likely gap). Verify the added tests
  pass on the unchanged `oob.py` with `uv run pytest scripts/tests/test_oob.py`

## 2. Read the Capability: line (design D1, D2)

- [ ] 2.1 Add the parser for the line to `scripts/oob.py` (D2): no Purpose, or a first non-blank line that doesn't
  begin with `Capability`, names no label. A line that begins with `Capability` must fully match the shape with
  distinct labels, or it's malformed. Add unit tests named for what they check: one label; two labels; a blank line
  before it; no Purpose; a first line about something else; and each malformed form (no backticks, text after the
  last label, `;` as separator, a label twice, `Capabilities:`, `Capability:` with nothing after it). Verify they
  pass, and that the "text after the last label" test fails if the match is loosened to a search (check by hand,
  then restore)
- [ ] 2.2 Replace `unlabelled_specs` with the D1 check: read the folder list and each `spec.md` once, keep the
  contents, and report each spec that names no label, has a malformed line, or names an undeclared label, using D2's
  messages. Rewrite the `troupe specs` tests in `test_oob.py` to the delta's scenarios (a spec without a label, an
  undeclared label, two labels, a label ahead of its spec, a folder without a label of its own name, every spec has
  a label, and each malformed scenario). Each fake spec carries a `Capability:` line copied from troupe's `main`, not
  a made-up shape. Verify the 1.1 tests and the new ones pass
- [ ] 2.3 Remove `test_an_unlabelled_spec_is_reported_once_and_its_spec_not_read`, whose "not read" no longer holds
  (every spec is read), and add a test that each `spec.md` is fetched exactly once across both checks. Verify it
  passes, and fails if the descriptions check fetches again (check by hand, then restore)

## 3. Key the Purpose record by spec (design D3)

- [ ] 3.1 Change `stale_descriptions` to compare each spec's Purpose without its `Capability:` line against
  `oob/troupe-spec-purposes.json` keyed by folder, with D3's three messages, which name the spec's labels. Rewrite
  the Purpose tests for the new keys and messages, and add "troupe changes only the labels a spec names" (a changed
  `Capability:` line with the same Purpose reports nothing). Verify they pass with `uv run pytest
  scripts/tests/test_oob.py`
- [ ] 3.2 Re-key `oob/troupe-spec-purposes.json` from `cap:<name>` to `<name>`, values unchanged, sorted in byte
  order. Verify with `git diff --word-diff` that only the keys changed, and that 25 entries remain
- [ ] 3.3 Update `oob/README.md`: the `tofu/labels/troupe.json` (derived) row (labels named in each spec's
  `Capability:` line, the shape, one way), the `troupe-spec-purposes.json` row (keyed by spec, without the line), and
  the "A new capability's label" paragraph (a description covers every spec that names the label, and a new spec's
  Purpose is recorded by spec). Update the comments above both checks in `oob.py` the same way. Verify `git grep -n
  "cap:<folder>"` outside `openspec/changes/archive` finds nothing, and `uv run scripts/check.py` passes

## 4. Declare cap:development and describe cap:flows (design D4)

- [ ] 4.1 In `tofu/labels/troupe.json`, add `cap:development` (colour `1D76DB`, D4's description) between `cap:cues`
  and `cap:docs-publishing`, and set `cap:flows`' description to D4's. Verify `uv run pytest
  scripts/tests/test_labels.py` passes (length and "repeats the name" checks), the file stays sorted in byte order,
  and it has 49 labels

## 5. Integration checks

- [ ] 5.1 Run `uv run scripts/oob.py` against GitHub with the branch's code. Verify the only difference left is
  `App installations: 'troupe-run-review'` (#154), with no `troupe specs` or `troupe labels` line, and record the
  output here
- [ ] 5.2 Using the branch's parser, print the labels each of troupe's 25 specs names on `main`. Verify they match
  troupe#169's mapping table row for row, and record any difference here (one would mean the parser or troupe's lines
  are wrong, not the table)
- [ ] 5.3 Fast-forward onto `origin/main` if only a state commit is ahead, then run `uv run scripts/tofu.py plan`.
  Verify it shows `github_issue_labels` for troupe changing in place, creating `cap:development` and changing
  `cap:flows`' description, with no label removed and nothing else changing. Record the summary line here
- [ ] 5.4 Push the branch and open the pull request (`Closes #158`, `Part of #151`), saying the `troupe-run-review`
  drift is #154's. Verify CI passes and the PR's plan comment matches 5.3

## Workflow follow-up

- Archive the change on the branch before asking for the plan's approval, and rebase onto `main`'s state commit, so
  the approval is asked once.
- After the owner merges and approves the apply, verify on GitHub that `cap:development` exists on troupe-run/troupe
  with the declared colour and description, `cap:flows` has its new description, and the `tofu` workflow's oob job
  shows only the #154 difference.
- Comment on #158 with the PR and the archived change, check it's closed and its card says Done. Comment on #151
  that `cap:development` exists, so its second change (the relabelling, then removing the 12 folded labels and
  `cap:lifecycle`) can start.
