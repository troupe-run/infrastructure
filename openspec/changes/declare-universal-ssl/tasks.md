# Tasks

## 1. Widen the token (D3)

- [x] 1.1 Record the starting point: `dig CAA troupe.run` at `audrey.ns.cloudflare.com` and at
      `sterling.ns.cloudflare.com`, and, through `op run` without printing the token, the status of
      `GET /zones/f716f063a26f15bcfcecd62791cdd202/ssl/universal/settings` and the token's ID from the account token
      verify endpoint. Verify both nameservers give the eleven
      answers in design Context, and the settings read is refused (403). Record the output here
      Done 2026-10-17. Both nameservers give the same eleven answers: `issue` for `comodoca.com`,
      `digicert.com; cansignhttpexchanges=yes`, `letsencrypt.org`, `pki.goog; cansignhttpexchanges=yes` and
      `ssl.com`; `issuewild` for `;` and the same five. The settings read is refused: HTTP 403, error 9109. `/zones`
      lists only `troupe.run`. Token ID `4b9585f87a072028f69fc939db8ed53c`, `active`, no expiry
- [x] 1.2 Ask the owner to edit the existing token `troupe-run-cloudflare-dns` in Cloudflare, adding Zone → SSL and
      Certificates → Edit, still on troupe.run only, and not to roll its value. Verify through `op run`: the settings
      read now answers 200 with `enabled: true`, `/zones` still lists only `troupe.run`, and the 1Password item's
      credential is unchanged (the account token verify endpoint, `/accounts/32b1f418aad2938f5d7dc5a8ad51226c/tokens/verify`, gives the same
      token ID before and after). Record the results here
      Done 2026-10-17. The owner first added the permission at account level, which reached none of the zone's SSL
      endpoints and was wider than troupe.run; it was replaced by Zone → SSL and Certificates → Edit on troupe.run.
      Through `op run`: Universal SSL settings answer 200, `enabled: true`, `certificate_authority: lets_encrypt`;
      certificate packs and SSL verification read 200; `/zones` lists only `troupe.run`; token ID still
      `4b9585f87a072028f69fc939db8ed53c`, `active`, no expiry. The zone's SSL mode (`/settings/ssl`) is still refused
      (9109): it's Zone Settings, a different permission, so design D3 and `oob/README.md` say so
- [x] 1.3 Update `oob/README.md`'s DNS section: the token's permissions now include SSL and Certificates → Edit, what
      that lets it do (D3), and that it's needed to plan Universal SSL. Replace "turn that off for the zone" with: the
      added records are Cloudflare's for Universal SSL, which `tofu/dns.json` declares on; whether turning it off
      removes them is untested, so try it on the probe first. Verify `uv run scripts/check.py` passes

## 2. Declare and adopt the setting (D1, D2, D6; spec: dns)

- [x] 2.1 In `scripts/tests/test_dns.py`, add `universal_ssl` to the required top-level fields and refuse a value that
      isn't a JSON boolean, naming `universal_ssl` and that it takes `true` or `false`. Add tests, each failing first:
      a missing `universal_ssl` is named; `"false"` (a string) is refused; `true` and `false` are both accepted.
      Rename `test_only_lets_encrypt_may_issue` to `test_the_declared_caa_records_name_only_lets_encrypt` (D6).
      Verify the new tests fail against the current `dns.json` and helper, then pass with `"universal_ssl": true`
      added to `tofu/dns.json` beside `ttl`
- [x] 2.2 In `tofu/dns.tf`, add `cloudflare_universal_ssl_setting.troupe_run` with `zone_id` from the zone data source
      and `enabled = local.dns.universal_ssl`, with a comment: why it's declared with the records (D1), that
      Cloudflare's added CAA records aren't in the API so the undeclared check can't see them (D5), and that removing
      the block forgets the setting without changing it (D2). Verify `tofu fmt -check` and `tofu validate` are clean
- [x] 2.3 Add an `import` block to `tofu/imports.tf` for `cloudflare_universal_ssl_setting.troupe_run`, id
      `f716f063a26f15bcfcecd62791cdd202`, with a comment saying it's adopted as it is. Fast-forward onto
      `origin/main` first, then run a local plan. Verify it reads `1 to import, 0 to add, 0 to change, 0 to destroy`,
      the import shows `enabled = true`, and no check warns. Record the plan summary here
      Done 2026-10-17, `origin/main` at `4a29625`: `Plan: 1 to import, 0 to add, 0 to change, 0 to destroy.` The
      import reads `enabled = true`, `id` and `zone_id` `f716f063a26f15bcfcecd62791cdd202`. No check warning
- [x] 2.4 Show drift (D4): set `universal_ssl` to `false` in the working tree only and plan. Verify the plan shows
      `enabled` changing from `true` to `false`. Set it back, plan again, and verify 2.3's summary returns. Verify
      `git diff tofu/dns.json` then shows only the `true` line from 2.1. Record both summaries here
      Done 2026-10-17. With `false`: `~ enabled = true -> false`, `Plan: 1 to import, 0 to add, 1 to change, 0 to
      destroy.` Set back to `true`: `Plan: 1 to import, 0 to add, 0 to change, 0 to destroy.` `git diff tofu/dns.json`
      shows only the added `"universal_ssl": true,` line
- [x] 2.5 Update README.md's row for `tofu/dns.json`, `tofu/dns.tf`: it also declares the zone's Universal SSL setting,
      which decides which CAs the CAA policy admits. Verify `uv run scripts/check.py` passes
- [x] 2.6 Commit group 1's docs and group 2 as Conventional Commits, signed off, saying why. Verify the guard accepts
      each commit and `check.py` passes before each
      Done 2026-10-17: `c5f0a9a` (the change's artifacts; the check is skipped for openspec-only commits), `cce0dae`
      (the declaration, test, resource, import and README row) and `5acb606` (`oob/README.md`). Each signed off; the
      guard ran `check.py` on the last two, 892 tests passed

## 3. Pull request

- [x] 3.1 Open the pull request with `Closes #75`, the plan summary from 2.3, and a note that the import changes nothing
      served and the token was widened in place. Verify CI is green on every job, and that its plan (once the owner
      approves that run) matches 2.3's summary with no check warning
      Done 2026-10-17: #79. Every check passed except main's plan and apply, which were skipped. The owner approved
      the plan run (39031085144); it reads `Plan: 1 to import, 0 to add, 0 to change, 0 to destroy.`, importing
      `cloudflare_universal_ssl_setting.troupe_run` with `enabled = true`, as in 2.3, with no check warning

## Workflow follow-up

- Archive the change on the branch before merging (`/opsx:archive`). The owner merges by rebase.
- After the owner approves the apply, verify the next plan is clean, and `dig CAA troupe.run` at both of Cloudflare's
  nameservers gives the same answers as 1.1: `issue letsencrypt.org` and `issuewild ;`, plus only the CAs Cloudflare's
  CAA documentation lists for Universal SSL (spec dns, "with Universal SSL on"). Verify https://troupe.run still serves
  the site.
- Comment on #75 with the PR, the archived change and the results above. Then check that #75 is closed and its card
  says Done.
- Remove this change's worktree and branch once it's verified.
