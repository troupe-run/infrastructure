# Tasks

## 1. Change the record

- [x] 1.1 Change `pages-verify`'s content in `tofu/dns.json` to `"5f257f97c64f4931616bb34e817511"`. Verify
      `scripts/tests/test_dns.py` passes and `uv run scripts/check.py` passes
      Done 2026-10-17: `test_dns.py` 14 passed; `check.py` passed on the commit (1.3)
- [x] 1.2 Run a local plan (fast-forward onto `origin/main` first). Verify it reads
      `Plan: 0 to add, 1 to change, 0 to destroy.`, the one change being `cloudflare_dns_record.troupe_run["pages-verify"]`'s
      `content`, in place, with both check blocks passing. Record the summary here
      Done 2026-10-17 at `origin/main`'s head (`4a29625`): `Plan: 0 to add, 1 to change, 0 to destroy.`, the one
      change `content = "\"f20f50ae5c14b2efb4e971b5c99318\"" -> "\"5f257f97c64f4931616bb34e817511\""`, in place;
      `plan_checks.py` printed nothing
- [x] 1.3 Commit (`fix(dns): publish troupe.run's new Pages verification record`), signed off

## 2. Pull request

- [ ] 2.1 Open the pull request with `Closes #76`. Verify CI is green and its plan (once the owner approves that run)
      matches 1.2

## Workflow follow-up

- Archive the change on the branch before merging (`/opsx:archive`). The owner merges by rebase.
- After the owner approves the apply, verify `_github-pages-challenge-troupe-run.troupe.run` serves the new value at
  Cloudflare's nameservers and from public resolvers. The owner then presses Verify, and troupe.run shows as verified
  in the org's Pages settings.
- Comment on #76 with the PR and the archived change, then check it's closed and its card says Done.
