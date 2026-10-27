# Tasks

## 1. Probe (design D4, D8; Risks)

- [x] 1.1 Add `probe_review_threads` to `tofu/probe/main.tf`, passed to a new module switch
  `review_thread_resolution` (default `false` until 5.1), which sets the `protect main` ruleset's
  `required_review_thread_resolution`, with a merge queue, with run instructions in the file's header comment;
  verify `tofu fmt -check` and `tofu validate` pass in `tofu/probe`
- [x] 1.2 Create public `troupe-run/infra-probe-review-threads`, ask the owner to add it to the infrastructure App's
  and the review App's installations, then apply the probe after the owner approves its plan; verify
  `gh api repos/troupe-run/infra-probe-review-threads/rules/branches/main` lists the pull request rule with
  conversation resolution required
- [x] 1.3 Open a pull request there, and, with a review App token (`contents: read`, `pull_requests: write`), post an
  inline comment on it; record whether the open conversation blocks `gh pr merge` (into the queue) and a rebase merge,
  and whether the owner's bypass merges past it; verify with each command's response and the pull request's
  `mergeStateStatus`
- [x] 1.4 With the same token, resolve that conversation with `resolveReviewThread`, and try `minimizeComment` and a
  contents write; record that the resolve succeeds and the others are refused; verify by reading the conversation's
  `isResolved` and each refusal
- [x] 1.5 Record whether `anthropics/claude-code-action` at the workflow's pinned SHA accepts `--json-schema` in
  `claude_args` and exposes `structured_output` (its `action.yml` and docs at that SHA); choose D4's primary path or
  its fallback; verify by quoting the input or output definition
- [x] 1.6 Write the answers into design.md as "Probe results", with what each one changes; if an open conversation
  doesn't block the queue, or the App can't resolve, stop and take it back to the owner on #194. Verify by deleting the
  probe repository and the probe's local state, and by `gh repo view` reporting it gone

## 2. Tier labels and their parser (design D1)

- [x] 2.1 Write tests first in `scripts/tests/` for a tier parser over a table of first lines: each of must-fix, nit
  and decision, a missing label, an unknown tier (including `critical` and `minor`), two tiers on one line, extra
  spaces or a different separator, and a label that isn't on the first line; and a conversation's tier as the review App's latest label, across a
  must-fix re-labelled decision, a must-fix re-labelled nit, a nit re-labelled must-fix, and a must-fix whose only
  `**nit**` is in the author's reply; verify they fail before the parser exists
- [x] 2.2 Add the parser and the label format to `scripts/guard.py`, as one named table of tiers; verify the 2.1
  tests, the guard's full suite (with `GITHUB_ACTIONS` set and unset), `mypy --strict` and ruff pass

## 3. The guard allows resolving a nit (design D5)

- [x] 3.1 Write tests first: `resolveReviewThread` on a review-App nit, or a must-fix the review re-labelled nit, is
  allowed; a must-fix, a decision, a nit the review re-labelled must-fix or decision, one whose last 100 comments
  hold no review label, an unlabelled finding and a person's conversation are each refused with D5's fix; a failed
  or timed-out lookup, a query that names two conversations, a `threadId` from `-F field=@file` or stdin, and
  `unresolveReviewThread` are each refused saying why. Stub the lookup's `gh` call on PATH (memory: real-shell stub
  tests); verify they fail on main's `guard.py`
- [ ] 3.2 Implement the condition and lookup under `gh-allow-list`, and give `GH_MUTATIONS_ALLOWED`'s comment the
  reason this one is allowed; verify the 3.1 tests, the full suite on all three OSes in CI, `mypy --strict` and ruff
- [x] 3.3 Run the branch's `guard.py` hook over a fresh scratch clone of troupe with a stubbed lookup (memory: probe
  the guard on a troupe clone); verify a nit's resolve is allowed and a must-fix's is refused there too
- [x] 3.4 Document the rule in `docs/development-workflow.md`'s `gh-allow-list` row and in the section on Claude's
  review, with the one way to reply in a conversation (D5: `gh api -X POST …/pulls/<n>/comments -F in_reply_to=<id>`);
  add a test that this reply is allowed and that `…/comments/<id>/replies` and `addPullRequestReviewThreadReply` are
  refused; verify the doc names the new requirement and that `uv run scripts/check.py` passes

## 4. The review labels, reads and resolves (design D1 to D4)

- [x] 4.1 Extend `scripts/tests/test_claude_review_workflow.py` first: the snapshot step runs before the action, with
  the App token, and writes `.review-threads.json`; the resolving step runs after it, with the App token only, and
  its script matches a pinned hash; Claude's tool list doesn't gain `gh api`; the prompt's example first lines parse
  with the guard's parser (2.2); verify the new tests fail on the current workflow
- [x] 4.2 Add the snapshot step (paginated `reviewThreads`, failing the run when the query fails); verify with a test
  that runs its script against a stubbed `gh` and a two-page response, and one where `gh` fails
- [x] 4.3 Rewrite the prompt: the three tiers, their rule and label format, and "unsure means must-fix" (D1), every finding inline and where a finding
  about the whole pull request goes (D2), read `.review-threads.json` and don't repeat an open finding, post a fresh
  must-fix when a resolved nit looks wrong, re-tier an open conversation by replying with a new label and its reason
  when the author's reply shows it's a decision or only a nit, report each earlier finding in the summary, and return the
  IDs it considers addressed (D4, or its fallback after 1.5); verify by reading it against D1 to D4 and with 4.1's
  tests
- [x] 4.4 Add the resolving step with D4's checks against the snapshot; verify with tests that run its script on a
  snapshot holding two review-App must-fixes (one first posted as a nit and re-labelled), a must-fix re-labelled
  nit, a nit, a decision, an unlabelled one, a person's conversation and an ID
  not on the pull request, and that only the two must-fixes are resolved (stubbed `gh`), each other one named in a
  warning, and that a failed mutation warns and continues
- [x] 4.5 Update the workflow's header comment and the pr-review section of `docs/development-workflow.md`; then run
  website's `npx vitest run tests/unit/workflow-node-version.test.ts` and troupe's `uv run scripts/check.py` with the
  workflow in place (the workflow's header asks for both); verify each passes and `uv run scripts/check.py` passes here

## 5. The ruleset (design D2, D8)

- [x] 5.1 Turn the module's `review_thread_resolution` switch (1.1) on by default in
  `tofu/modules/repository/variables.tf`, so every `protect main` ruleset sets `required_review_thread_resolution`; add a test in
  `scripts/tests/` that fails when the setting is false or missing; verify `tofu fmt -check`, `tofu validate`, the
  test, and a local plan (fast-forwarded onto origin/main first) showing the one in-place change on each of the three
  `protect main` rulesets
- [ ] 5.2 List every open pull request's unresolved conversations in troupe, infrastructure and website
  (`reviewThreads` with `isResolved: false`), and post the list on the pull request for the owner before approving
  the plan; verify the comment is there

## 6. The workflow step (design D6)

- [x] 6.1 Add the step to `org-profile/CONTRIBUTING.md`'s step 4, to CLAUDE.md's "How work happens here", and one line
  to this repository's `openspec/config.yaml` context under "Working"; verify with `grep` that each names the
  three tiers and who resolves each, and that `uv run scripts/check.py` passes
- [x] 6.2 Open an issue in troupe-run/troupe and one in troupe-run/website, each with `--project "troupe roadmap"`,
  asking for the same line in their `openspec/config.yaml` context, linked from #194; verify each is on the board
  (`gh issue view <n> --json projectItems`)

## 7. Look back at merged pull requests (#194, question 5)

- [x] 7.1 Read the review's summary and inline comments on infrastructure #160 to #198 (14 pull requests), troupe#183
  and website#70; classify each finding by D1's tiers, and for each must-fix or decision, say whether a
  later commit or pull request addressed it; post the table as a comment on #194, and open an issue (on the board) for
  each must-fix or decision that's still open; verify the comment and each issue exist

## 8. Resolving with contents write (design D4a; owner, 2026-10-28)

- [ ] 8.1 Ask the owner to give `troupe-run-review` contents read and write on GitHub, and to accept it on the org's
  installation; update its declared permissions in `oob/app-installations.json` and `oob/README.md`; verify with the
  drift check's App comparison (`uv run scripts/oob.py`, or its test) that the declared and live permissions match
- [x] 8.2 Write tests first in `scripts/tests/test_claude_review_workflow.py` for a `resolve` job that needs `review`,
  runs only on its success, checks out nothing, runs no Claude action, mints the App token with contents write and pull
  requests write, and runs the snapshot and resolving steps in that order on `needs.review.outputs.structured_output`;
  and for the review job keeping its contents-read token and having no resolving step; verify they fail on the branch's
  current workflow
- [x] 8.3 Move the resolving step into the `resolve` job, with the review job's `outputs`; verify 8.2's tests, the
  scripts' behaviour tests, and website's and troupe's checks with the workflow in place, as in 4.5
- [ ] 8.4 On the probe, with a review App token minted as the `resolve` job mints it, resolve a review-App
  conversation; verify `isResolved` is true; then delete the probe repository and the probe's local state, and verify
  `gh repo view` reports it gone

## 9. Merging is the owner's (design D5a)

- [x] 9.1 Write tests first: `gh pr merge 32 --rebase`, `gh pr merge 32 --auto`, `gh pr merge` with no number, and
  GraphQL `enablePullRequestAutoMerge` and `enqueuePullRequest` are refused as owner-only with the merge fix; `gh pr
  merge` on `troupe-run/infra-probe-*` is still allowed; and the spec examples moved off `gh pr merge` still hold
  (`gh pr ready` allowed, `gh pr checkout` allowed but not granted); verify they fail on main's `guard.py`
- [x] 9.2 Make `gh pr merge` owner-only in `scripts/guard.py` and add the two mutations; update the merge message, the
  `owner-only` row in `docs/development-workflow.md`, and the guide's merge step (merge once every conversation is
  resolved); verify 9.1's tests and the full suite both ways

## Workflow follow-up

- Act on the review's findings on this change's own pull request by their tier, before archiving.
- After the apply: check that troupe's and website's `.github/workflows/claude-review.yml` match the source, and that
  each repository's `protect main` ruleset requires conversation resolution
  (`gh api repos/troupe-run/<repo>/rules/branches/main`).
- After the merge: comment on #194 with the pull request and the archived change. Keep #194 open until troupe's and
  website's `config.yaml` pull requests (6.2) merge, then close it and set its card to Done.
