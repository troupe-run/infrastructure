# Tasks

## 1. Declare Universal SSL off (D1, D2; spec: dns)

- [x] 1.1 In `scripts/tests/test_dns.py`, make `declaration_problems` refuse `universal_ssl: true`, naming it and why it
      must be off. Change the `text` helper and the duplicate-key test's raw JSON to `false`, and split
      `test_universal_ssl_takes_true_and_false` into "false is accepted" and "true is refused with that message". Verify
      the new refusal test fails before the check is written, and `test_the_declaration_is_well_formed` fails against
      `"universal_ssl": true`, then set `tofu/dns.json` to `false` and verify every test in the module passes
- [x] 1.2 Update `tofu/dns.tf`'s comment on `cloudflare_universal_ssl_setting` (off, and why it stays declared),
      README.md's row, and `oob/README.md`'s zone and token paragraphs (D4). Verify `uv run scripts/check.py` passes
- [x] 1.3 Fast-forward onto `origin/main`, then run a local plan. Verify it reads
      `0 to add, 1 to change, 0 to destroy`, the one change is `cloudflare_universal_ssl_setting.troupe_run`
      `enabled = true -> false`, and no check warns. Record the summary here
      2026-10-17: the local plan couldn't run; the owner was on remote control without 1Password (the prompt timed
      out). CI's pull-request plan, which runs the same plan with the same token once the owner approves it, stands in
      for it (owner, 2026-10-17); its result is recorded under 2.1
- [x] 1.4 Commit as Conventional Commits, signed off, saying why. Verify the guard accepts each commit
      Done 2026-10-17: `db8396b` (the change's artifacts) and `f04c7a4` (the declaration, check and docs; the guard
      ran `check.py`, which passed). Both signed off

## 2. Pull request

- [x] 2.1 Open the pull request with `Closes #81` and 1.3's plan summary. Verify CI is green on every job, and that its
      plan (once the owner approves that run) matches 1.3
      Done 2026-10-17: #82. Every check passed except main's plan and apply, which were skipped. The owner approved
      the plan run (39033838782): `Plan: 0 to add, 1 to change, 0 to destroy.`, the one change being
      `cloudflare_universal_ssl_setting.troupe_run` `~ enabled = true -> false`. No check warning (the job's one
      annotation is GitHub's notice about `ubuntu-latest`). It's the first plan since #79's apply, so that apply left
      no drift. This is 1.3's evidence too

## Workflow follow-up

- Archive the change on the branch before merging (`/opsx:archive`). The owner merges by rebase.
- After the owner approves the apply (D3): query CAA at `audrey` and `sterling.ns.cloudflare.com` until the answer is
  only `issue letsencrypt.org` and `issuewild ;`, for up to about an hour. If Cloudflare's records stay, reopen #81 and
  bring the owner the findings (D3). Verify https://troupe.run and https://www.troupe.run still serve the site with the Let's
  Encrypt certificate, and the next plan is clean.
- Comment on #81 with the PR, the archived change and the `dig` result. Check #81 is closed and its card says Done.
- Remove the `declare-universal-ssl` and `turn-off-universal-ssl` worktrees and branches once verified.
