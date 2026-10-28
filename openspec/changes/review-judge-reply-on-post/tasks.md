# Tasks

## 1. Probe (design D2, D3, D4)

- [ ] 1.1 Create public `troupe-run/infra-probe-review-reply` with `gh repo create` on its own, and push a probe
  workflow with this design's `pull_request` and `pull_request_review_comment` (`created`) triggers, D2's `if:` and
  D3's job-level concurrency on two jobs (`review`, then `resolve` needing it). `review` prints the event, the comment's
  `author_association` and `in_reply_to_id`, the checked-out SHA against `refs/pull/<n>/merge`, whether a repository
  secret `PROBE_SECRET` is set (never its value), then sleeps 120 seconds; verify the workflow is on the probe's `main`
  and `gh secret list -R troupe-run/infra-probe-review-reply` names `PROBE_SECRET`
- [ ] 1.2 Ask the owner to add the probe to the review App's installation, as #194's probe did; open a pull request
  from a branch of the probe and post an inline comment on it; verify a run starts for the pull request, and the
  inline comment's run is skipped because it isn't a reply
- [ ] 1.3 Reply to that comment as the owner; record the reply's `author_association`, whether `review` ran, and that
  the checked-out SHA is the merge ref's; verify from the run's log
- [ ] 1.4 While a reply's `review` is sleeping, post an inline comment and a reply with a review App token minted as
  the workflow mints it (contents read, pull requests write); record that both runs are skipped and the sleeping run
  finishes, then that its `resolve` runs; verify with `gh run list` and each run's conclusion. If the sleeping run is
  cancelled, switch to D3's alternative in the probe workflow and record that this probe step passes with it
- [ ] 1.5 Post two replies as the owner ten seconds apart while a `review` sleeps; record that each cancels the run
  before it and the last runs to its end; verify with each run's conclusion
- [ ] 1.6 Fork the probe into the owner's account, open a pull request from the fork, and reply in a conversation on
  it; record that `review` is skipped and that a step outside the `if:` reports `PROBE_SECRET` unset; verify from the
  run's log
- [ ] 1.7 Reply as an account without write access to the probe (the owner names one); record that `review` is
  skipped, not failed, and the reply's `author_association`; verify from the run's conclusion
- [ ] 1.8 Write what 1.2 to 1.7 showed into design.md as "Probe results", with what each one changes (D2's
  association list, D3 or its alternative); verify by deleting the fork and the probe repository (`gh repo view`
  reports both gone) and the owner removing the probe from the review App's installation (`uv run scripts/oob.py`
  reports no difference)

## 2. The workflow and its tests (design D1 to D3)

- [x] 2.1 Write tests first in `scripts/tests/test_claude_review_workflow.py`: `problems()` accepts `on` holding
  exactly `pull_request` with today's types and `pull_request_review_comment` with `[created]`; pins the review job's
  `if:` to D2's condition; pins the concurrency group on both jobs and none at the workflow level; and names each of:
  `issue_comment` or `pull_request_review` added, `edited` added to the comment types, the reply, bot, association or
  pull request skip dropped, an association added, and the group moved back to the workflow. Verify the new
  parametrised cases fail against the workflow on `main`
- [ ] 2.2 Change `.github/workflows/claude-review.yml` as D1 to D3 say (as the probe confirmed), with the header
  comment saying a reply starts a review and why the group is on the jobs; verify the 2.1 tests and
  `uv run scripts/check.py` pass
- [ ] 2.3 With the changed workflow in place, run website's `npx vitest run tests/unit/workflow-node-version.test.ts`
  and troupe's `uv run scripts/check.py` (each on a scratch copy of its `main`, with this file copied in); verify both
  pass

## 3. Docs (design D5)

- [x] 3.1 In `docs/development-workflow.md`, say the review runs on each push and on each person's reply in a review
  conversation, and keep the re-run for a run that failed or was skipped; in `org-profile/CONTRIBUTING.md` step 4,
  `CLAUDE.md` step 5 and `openspec/config.yaml`'s context, drop the instruction to re-run after a reply; verify
  `grep -rn "gh run rerun" CLAUDE.md openspec/config.yaml org-profile/CONTRIBUTING.md` finds nothing that tells anyone
  to re-run after a reply, and `uv run scripts/check.py` passes

## 4. Shown end to end (design D4)

- [ ] 4.1 On this change's pull request, after the review's run, reply to one of its findings (or, if it found none,
  to a review comment the owner posts and the review App answers); verify a `claude review` run starts from the
  reply, its summary says what became of the finding, and record the run's URL here

## Workflow follow-up

- Act on Claude's review of the last push, archive on the branch, and after the merge comment on #208 with the pull
  request and the archived change.
- After the merge, the owner approves the plan that delivers the workflow to troupe and website and writes
  CONTRIBUTING.md to troupe-run/.github; check the delivered copies match the source.
