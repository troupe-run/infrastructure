# Tasks

## 1. Probe (design D2, D2a, D3, D4)

- [x] 1.1 Create public `troupe-run/infra-probe-review-reply` with `gh repo create` on its own, and push a probe
  workflow with this design's `pull_request` and `pull_request_review_comment` (`created`) triggers and its three jobs:
  `gate` with D2's `if:` and D2a's step as the review workflow has it, then `review` and `resolve` with D3's job-level
  concurrency. A job outside the `if:` prints the event, the comment's `author_association` and `in_reply_to_id`, the
  run's SHA, and whether a repository secret `PROBE_SECRET` is set (never its value); `review` prints its checkout's
  SHA, then sleeps 120 seconds. Verify the workflow is on the probe's `main` and `gh secret list -R
  troupe-run/infra-probe-review-reply` names `PROBE_SECRET`
- [x] 1.2 Ask the owner to add the probe to the review App's installation, as #194's probe did, and to set
  `REVIEW_APP_PRIVATE_KEY` on the probe from 1Password; open a pull request from a branch of the probe and, with a
  review App token, post two inline findings, one labelled must-fix and one nit; verify the pull request's run reaches
  `review`, and each finding's run is skipped at `gate`, as a bot's comment
- [x] 1.3 Reply to the must-fix as the owner; record the reply's `author_association`, that `gate` says yes and
  `review` runs, and that the checked-out SHA is the merge ref's; verify from the run's log
- [x] 1.4 While that `review` sleeps, reply to the nit as the owner, and post a comment and a reply with the review
  App's token; record that the nit reply's `gate` says no, the App's runs skip `gate`, the sleeping run finishes and its
  `resolve` runs; verify with `gh run list` and each run's conclusion. If the sleeping run is cancelled, switch to
  D3's alternative in the probe workflow and record that this step passes with it
- [x] 1.5 Post two replies to the must-fix as the owner ten seconds apart while a `review` sleeps; record that each
  cancels the run before it and the last runs to its end; verify with each run's conclusion
- [x] 1.6 Fork the probe into the owner's account, open a pull request from the fork, and reply in a conversation on
  it; record that `gate` is skipped and that the job outside the `if:` reports `PROBE_SECRET` unset; verify from the
  run's log
- [x] 1.7 Reply to the must-fix as an account without write access to the probe (the owner names one); record that
  `gate` says no from the permission API, the run doesn't fail, and the reply's `author_association`; verify from the
  run's log and conclusion
- [x] 1.8 Write what 1.2 to 1.7 showed into design.md as "Probe results", with what each one changes (D2's
  write-access check, D3 or its alternative); verify by deleting the fork and the probe repository (`gh repo view`
  reports both gone) and the owner removing the probe from the review App's installation (`uv run scripts/oob.py`
  reports no difference)

## 2. The workflow and its tests (design D1 to D3, D2a)

- [x] 2.1 Write tests first in `scripts/tests/test_claude_review_workflow.py`: `problems()` accepts `on` holding
  exactly `pull_request` with today's types and `pull_request_review_comment` with `[created]`; pins the first job's
  `if:` (the gate's, D2a) to D2's condition; pins the concurrency group on both jobs and none at the workflow level; and names each of:
  `issue_comment` or `pull_request_review` added, `edited` added to the comment types, the reply, bot or
  pull request skip dropped, an association check added, and the group moved back to the workflow. Verify the new
  parametrised cases fail against the workflow on `main`
- [x] 2.2 Change `.github/workflows/claude-review.yml` as D1 to D3 say (as the probe confirmed), with the header
  comment saying a reply starts a review and why the group is on the jobs; verify the 2.1 tests and
  `uv run scripts/check.py` pass
- [x] 2.4 Write tests first for the gate (design D2a): `problems()` pins a `gate` job with D2's `if:`, no concurrency
  group, `contents: read`, a read-only review App token (contents read, pull requests read) and its one step pinned by
  hash, and `review` needing it and running only on its yes; it names each of the gate dropped, given a group, its
  token widened, and `review` not needing it. With the stub `gh`, the gate's step says yes for a `pull_request` event
  without calling `gh`, and for a reply to an open must-fix the review opened by someone the permission API says can
  push (admin, write), asking that before reading any conversation; no, reading nothing more, for read, none and any
  other value, such as a literal triage or maintain, which the API reports as read and write; no for a reply to a nit, a decision, a
  must-fix re-tiered nit, a must-fix whose only `**must-fix**` is in a person's reply, a person's conversation, a
  resolved must-fix and a comment on no conversation read; and fails, saying so, when either read fails or isn't an
  answer, or the reply's ID or author isn't one. Its `LABEL` and `BOT` equal the resolver's. Verify the new tests fail before the gate exists
- [x] 2.5 Add the gate to `.github/workflows/claude-review.yml` as D2a says, moving D2's `if:` to it; verify the 2.4
  and 2.1 tests and `uv run scripts/check.py` pass
- [x] 2.3 With the changed workflow in place, run website's `npx vitest run tests/unit/workflow-node-version.test.ts`
  and troupe's `uv run scripts/check.py` (each on a scratch copy of its `main`, with this file copied in); verify both
  pass

## 3. Docs (design D5)

- [x] 3.1 In `docs/development-workflow.md`, say the review runs on each push and on each person's reply to one of
  its open must-fixes, and that a reply to a nit or a decision starts none, and keep the re-run for a run that failed or was skipped; in `org-profile/CONTRIBUTING.md` step 4,
  `CLAUDE.md` step 5 and `openspec/config.yaml`'s context, drop the instruction to re-run after a reply; verify
  `grep -rn "gh run rerun" CLAUDE.md openspec/config.yaml org-profile/CONTRIBUTING.md` finds nothing that tells anyone
  to re-run after a reply, and `uv run scripts/check.py` passes

## 4. Shown end to end (design D4)

- [x] 4.1 On this change's pull request, after the review's run, reply to one of its must-fixes, and to a nit if it
  posted one (if it found no must-fix, record that and rely on 1.3); verify the must-fix reply's run reaches `review`
  and its summary says what became of the finding, and the nit reply's run stops at `gate`; record both runs' URLs
  here. Done 2026-10-28: the review of #215's first push (run 40685129918:
  gate, claude review and resolve all succeeded, so the gate let a `pull_request` event through on the live workflow)
  posted no findings and opened no conversation, so there was no must-fix or nit to reply to; the reply path rests on
  probe step 1.3, which ran this gate unchanged

## Workflow follow-up

- Act on Claude's review of the last push, archive on the branch, and after the merge comment on #208 with the pull
  request and the archived change.
- After the merge, the owner approves the plan that delivers the workflow to troupe and website and writes
  CONTRIBUTING.md to troupe-run/.github; check the delivered copies match the source.
