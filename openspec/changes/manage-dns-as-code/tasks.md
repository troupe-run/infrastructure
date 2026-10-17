# Tasks

## 1. Record the switch and get the token (D1, D2, D4, D6, D9)

- [x] 1.1 Query every record in Gandi's export (A, AAAA, `www` CNAME, `_gh-troupe-run-o` TXT) at
      `audrey.ns.cloudflare.com` and at `ns-25-c.gandi.net`, and the delegation at `.run`'s registry. Also query MX,
      apex TXT, CAA, `_dmarc` TXT and DS at Cloudflare, and read the certificate's issuer and dates. Verify the
      content matches name by name, the delegation names Cloudflare's two nameservers, and nothing else is published.
      Record the output here as the switch's evidence (spec dns: "The new nameservers answer as the old ones did")
      Done 2026-10-17T10:17Z. Same content at both, name by name: A 185.199.108–111.153; AAAA
      2606:50c0:8000–8003::153; `www` CNAME `troupe-run.github.io.`; `_gh-troupe-run-o` TXT `"ab7788e488"`.
      `v0n0.nic.run` delegates to `audrey` and `sterling.ns.cloudflare.com`, with no DS. Cloudflare serves no MX,
      apex TXT, CAA or `_dmarc` TXT. It does serve `_github-pages-challenge-troupe-run` TXT
      `"f20f50ae5c14b2efb4e971b5c99318"`, which the owner added in the dashboard after starting Pages verification,
      so it's adopted like the others (11 records, not 10). Certificate: Let's Encrypt `YR1`, notBefore 2026-10-07,
      notAfter 2027-01-05
- [ ] 1.2 Ask the owner to create the D4 token (Zone → DNS → Edit, Zone → Zone → Read, troupe.run only, no IP
      filter) and save it in 1Password as `troupe-run cloudflare dns`, field `credential`, vault `troupe.run`. Using
      it through `op run`, without printing it, verify the zone's status is `active` and it has exactly eleven records:
      the ones in 1.1, each with `proxied: false`. Ask the owner to confirm two-factor login is on for the
      Cloudflare account and for the Gandi account: either login can repoint troupe.run without a plan (design D1).
      Record the account (not its credentials) and both confirmations here
      Progress 2026-10-17: the owner created the token and saved it in 1Password. Read through `op run`: an
      account-owned token, `active`, no expiry. It sees one zone, `troupe.run`, in account `troupe.run`
      (`32b1f418aad2938f5d7dc5a8ad51226c`), status `active`, nameservers `audrey` and `sterling.ns.cloudflare.com`.
      Eleven records, all `proxied: false`. Scope: SSL settings, Universal SSL and account members are refused
      (403); DNSSEC status reads (200, Zone Read). The account is troupe-run's; hps.gd's zones will go in a
      separate account (owner, 2026-10-17). Waiting on: the item's title has a leading space
      (`" troupe-run cloudflare dns"`), which the owner is asked to remove; two-factor confirmations
- [x] 1.3 With the token, list the zone's ID and each record's ID, content, TTL, comment, tags and `settings`. Record
      them here: IDs, not secrets. Note any attribute the scan set that D3's declaration doesn't have
      Done 2026-10-17. Zone `f716f063a26f15bcfcecd62791cdd202`. Every record: TTL 1, `proxied: false`, no comment,
      no tags. The CNAME has `settings.flatten_cname: false` (Cloudflare's default); the others have empty
      `settings`. The probe (2.2) shows whether the declaration needs it. Record IDs:
      A 108 `be277d7b076adb4e5ce20835d1c51898`, 109 `358fa37e927b4887ad5c893d6652a872`,
      110 `dea0be14dc4d244cd40f5e877f3bb8cd`, 111 `660e903470158fa5dbf5a77c6f04b6db`;
      AAAA 8000 `d445ef5e762426d8f78b4a0eed0f2c23`, 8001 `5a337b22a47d23fc5f4cc1d4f94fcb93`,
      8002 `bff4ac11cb1977de99fc16069bbe20b2`, 8003 `4a0260edaa4b749fa6b3329d14c4be3b`;
      CNAME www `1c76375044e1296ce02454c0c922b560`; TXT `_gh-troupe-run-o` `05b01811966bd3ed028215c1382805f4`;
      TXT `_github-pages-challenge-troupe-run` `25be6a5ec9d1532102f26ba9aea140eb`
- [ ] 1.4 The owner started Pages domain verification on 2026-10-17 and added its record in the dashboard:
      `_github-pages-challenge-troupe-run`, `f20f50ae5c14b2efb4e971b5c99318` (D9). Ask the owner whether troupe.run
      shows as verified or pending in the org's Pages settings, and record it here

## 2. Probe the provider under infra-probe.troupe.run (D7)

- [ ] 2.1 In `tofu/probe/`, add a Cloudflare section behind a `probe_dns` variable. It holds one record of each new
      shape (quoted TXT, null MX, CAA `issue` and `issuewild`) under `infra-probe.troupe.run`, an `import` block for
      one A record the owner creates by hand in the dashboard under that name, and the two D5 `check` blocks. Its
      header comment says how to run and clean it up, as the earlier probes do. Verify `tofu fmt -check` and
      `tofu validate` pass in `tofu/probe/`
- [ ] 2.2 Apply the probe locally, then plan again. Verify, and record here: (a) the second plan is clean for every
      type (TXT quoting, CAA `flags`, null MX `.` with `priority = 0`, fully qualified names, `ttl = 1`); (b) the
      hand-made record imports with no change; (c) whether CAA for `infra-probe.troupe.run` or `troupe.run` shows
      entries that weren't declared; (d) the undeclared-records check warns on a second record added by hand and is
      quiet once it's deleted; (e) the zone-active check passes. If (a) or (b) fails for a type, change D3's shape for
      it and record why. If (c) shows Cloudflare's CAs, ask the owner to turn off Universal SSL for the zone, and
      check again
- [ ] 2.3 Destroy the probe's records, delete its local state, and unset `probe_dns`. Verify with the token that the
      zone holds exactly the eleven records from 1.2, and that `git status` shows no probe state or tfvars

## 3. Supply the token (D4; specs: state-and-apply, ci-apply)

- [x] 3.1 Add `TF_VAR_cloudflare_api_token` to `SECRETS` in `scripts/tofu.py` and its 1Password reference to
      `tofu/secrets.env`, and update `scripts/tofu.py`'s tests for the new secret. Verify the test that a missing
      secret is named before anything runs passes for the token, and `uv run scripts/check.py` passes
      Done 2026-10-17: two new tests failed first (the token wasn't required; secrets.env didn't name it), then
      `test_tofu_wrapper.py` 8 passed, including one that `secrets.env` names exactly the wrapper's secrets
- [x] 3.2 Add `TF_VAR_cloudflare_api_token` to the `env` of every job in `.github/workflows/tofu.yml` that sets the
      other secrets. Update the README's environments paragraph and its `gh secret set` loop. Verify
      `uv run scripts/check.py` passes and a `grep` finds the variable in each job that has `TF_VAR_state_passphrase`
      Done 2026-10-17: 3 jobs have `TF_VAR_state_passphrase:` and 3 have `TF_VAR_cloudflare_api_token:`;
      `check.py`: all gates passed
- [ ] 3.3 Ask the owner to run the README's updated loop, so all three environments get the token. Verify with
      `gh secret list --env <env> -R troupe-run/infrastructure` for each (names only)

## 4. Declare and adopt the records (D2, D3, D5, D9; spec: dns)

- [x] 4.1 Add `scripts/tests/test_dns.py`, failing first against a missing or empty declaration. It covers: the
      supported types; each type's exact fields; unknown fields; duplicate keys (read with `object_pairs_hook`);
      names inside the zone; quoted TXT content; and that the kept records are exactly the ones in spec dns. Each
      failure names the record's key and the problem. Verify the tests fail for the right reason before 4.2
      Done 2026-10-17: before `tofu/dns.json` existed, the 5 declaration tests failed with `FileNotFoundError` and
      the 9 refusal tests passed. Also covers the mail lockdown, CAA set and Pages record being declared, an
      unknown top-level field, and `proxied` being refused as a field no type takes
- [ ] 4.2 Add `tofu/dns.json` with every record from D3: the eleven kept records as 1.3 found them (the Pages
      verification record among them), the mail and CAA records, and any shape changes from 2.2. Verify
      `scripts/tests/test_dns.py` passes, and that one deliberately broken copy per refusal fails naming the key
- [ ] 4.3 Add the `cloudflare/cloudflare` provider to `tofu/versions.tf` (`~> 5.28`). Add its configuration and the
      `sensitive`, `ephemeral` `cloudflare_api_token` variable to `tofu/providers.tf`. Add `tofu/dns.tf`:
      `data "cloudflare_zone"` by name, one `cloudflare_dns_record` per key with `proxied = false`, and the two D5
      `check` blocks, with a header citing spec: dns and #55. Lock the provider for every platform the existing lock
      file covers. Verify `uv run scripts/check.py` passes (`tofu fmt`, `tofu validate`) and the lock file lists the
      new provider's hashes for each platform
- [x] 4.4 Add eleven `import` blocks to `tofu/imports.tf`, one per kept record, with the IDs from 1.3. Verify a local plan
      (fast-forward onto `origin/main` first) imports exactly those eleven with no change, and its other actions are
      creates for the new records only, with no change to any GitHub resource
      Done 2026-10-17 on the branch at `origin/main`'s head: `Plan: 11 to import, 5 to add, 0 to change, 0 to
      destroy.` The eleven imports plan no change (the CNAME's `flatten_cname: false` included); the five creates are
      `mx-null`, `spf`, `dmarc`, `caa-issue` and `caa-issuewild`. Nothing else in the plan
- [x] 4.5 In each plan step of `.github/workflows/tofu.yml`, turn every `Check block assertion failed` in the plan's
      output into a `::warning::` annotation naming the check. Verify with a local run of the step's script against
      a saved plan output holding one failed check: exactly one annotation, naming it
      Done 2026-10-17 as `scripts/plan_checks.py`, reading `tofu show -json`'s `checks`, not the text. A real plan
      showed `tofu show` drops the warning and the text output wraps it at 80 columns. Run against that real saved
      plan (one failing, one passing check): exactly one line,
      `::warning title=check.undeclared_records::Records in the zone ...`, exit 0. Both plan jobs run it after
      the JSON plan exists, and add its summary to the posted plan and the step summary.
      `test_plan_checks.py`: 8 passed; an unknown status is an error naming the known ones
- [ ] 4.6 Verify the 4.4 plan shows no check warning, and that the saved plan holds no token: `tofu show -json` on it
      contains neither the token nor the App key. Record the plan's summary line here
- [ ] 4.7 Add the Layout row for `tofu/dns.json` / `dns.tf` to README.md (a key never changes; nothing is proxied; TTL
      automatic). Add a "troupe.run's DNS (set up by hand)" section to `oob/README.md`: the account, the zone and its
      scan-imported records, the token's scope and 1Password item, Universal SSL if 2.2(c) needed it, the Pages
      domain verification, Gandi's nameserver setting and the rollback (D6). Verify `uv run scripts/check.py` passes
- [ ] 4.8 Commit each of groups 2, 3 and 4 as its own Conventional Commit, signed off. Verify the guard accepts each

## 5. Pull request

- [ ] 5.1 Open the pull request with `Closes #55`, the plan summary from 4.6, and a note that the import changes
      nothing served and the apply adds only the new records. Verify CI is green on every job, and that its plan (once
      the owner approves that run) matches 4.6's summary with no check warning

## Workflow follow-up

- Archive the change on the branch before merging (`/opsx:archive`). The owner merges by rebase.
- After the owner approves the apply, verify the MX, SPF, DMARC, CAA and Pages verification answers match spec dns at
  Cloudflare's nameservers and from two public resolvers. Verify https://troupe.run and https://www.troupe.run still
  serve the site.
- The owner presses Verify for troupe.run in the org's Pages settings (D9). Verify it's listed as verified, and the
  org's domain verification still reads `isVerified: true`.
- The CAA test (D8): the owner removes troupe.run as the website's custom domain and adds it again. Verify a new
  Let's Encrypt certificate is served (its `notBefore` is after the apply), and the next plan shows no Pages drift.
- Comment on #55 with the PR, the archived change and the results above. Then check that #55 is closed and its card
  says Done.
- Remove this change's worktree and branch once it's verified. Ask the owner about the empty `dns-as-code` worktree
  and branch (`../infrastructure-dns-as-code`), which holds no commits of its own.
