# Design: manage troupe.run's DNS as code

## Context

See proposal.md for why. What shapes the approach:

- **Gandi's zone (owner's export, 2026-10-17):** SOA, four A and four AAAA records at the apex, `www` CNAME
  `troupe-run.github.io.`, and `_gh-troupe-run-o` TXT `"ab7788e488"`, all with TTL 3600. Nothing else: no MX, no
  other TXT, no CAA. There's no DS record, so no DNSSEC.
- **The switch, done by the owner on 2026-10-17:** `.run`'s registry (`v0n0.nic.run`) delegates troupe.run to
  `audrey.ns.cloudflare.com` and `sterling.ns.cloudflare.com`. `audrey` answers authoritatively with every record in
  the export, with the same content and TTL 300 (Cloudflare's "auto"), and the A records are GitHub's addresses, so
  nothing is proxied. Resolvers that still hold Gandi's delegation get the same answers until its TTL (21600) runs
  out. https://troupe.run returns 200 from GitHub.
- **The certificate:** Let's Encrypt `YR1`, issued 2026-10-07, expiring 2027-01-05. GitHub renews it about a month
  before expiry. So a CAA mistake wouldn't show until about December unless a new issue is forced.
- **Pages verification:** troupe.run is verified for the org (`organization.domains`: `isVerified: true`, through
  `_gh-troupe-run-o`). It isn't a Pages verified domain (owner, 2026-10-17). They're separate GitHub features, each
  with its own TXT record.
- **Provider:** `cloudflare/cloudflare` 5.28.0 (2026-10-13). `cloudflare_dns_record` takes `zone_id`, `name`, `type`,
  `ttl` (1 means automatic), `content`, `priority` (MX), `proxied`, and a `data` block for CAA (`flags`, `tag`,
  `value`). `data "cloudflare_zone"` reads a zone by name, including its `status` (`initializing`, `pending`,
  `active` or `moved`) and its assigned `name_servers`. `data "cloudflare_dns_records"` lists a zone's records. Each
  needs only DNS Read/Write and Zone Read. The provider takes `api_token`.
- **Precedents here:** declarations are JSON read with `jsondecode`, with stable keys (`tofu/milestones.json`,
  `tofu/labels/`). Their validation is a pytest module run by `scripts/check.py` (`scripts/tests/test_milestones.py`).
  Adoption is by `import` blocks in `tofu/imports.tf`, proved by a plan that imports and changes nothing (adopt-org,
  website-pages). Secrets are TF_VAR_ variables: 1Password references in `tofu/secrets.env`, listed in `SECRETS` in
  `scripts/tofu.py`, and set by the owner in the `plan-pr`, `plan-main` and `apply` environments. The App key is an
  ephemeral variable, so no saved plan holds it. What OpenTofu can't manage is recorded in `oob/README.md`.

## Goals / Non-Goals

**Goals:**
- The records Cloudflare serves are adopted with no change, then the new ones are added. Nothing else in troupe.run's
  answers changes.
- One token, which can do nothing but edit troupe.run's DNS records, and no saved plan holds it.
- Switching back to Gandi stays possible until Gandi's records are cleared on purpose.

**Non-Goals:**
- Managing the Cloudflare zone or its settings in OpenTofu (D2).
- Monitoring the site's reachability. The plan reports drift in what's declared, not whether the site is up.

## Decisions

### D1. Cloudflare hosts the DNS; Gandi keeps the registration

See proposal.md (owner, 2026-10-17). The nameservers at Gandi were changed once, by hand, before this change was
built (see Context for the evidence). Gandi's provider would be the only way to manage them in code, and it's the
dormant dependency this change avoids. A one-off change by hand, recorded in `oob/README.md` with its rollback, is
the smaller risk. The plan reports when it's changed back (D5).

Both logins can change troupe.run outside this repository: Cloudflare's can edit any record, and Gandi's can change
the nameservers. A changed record shows in the next plan (daily at the latest), but serves whatever it points at until
then. So two-factor login on both accounts is part of this change (task 1.2), and `oob/README.md` records it.

### D2. The zone was created by hand; OpenTofu reads it and adopts its records

`dns.tf` finds the zone with `data "cloudflare_zone"` by name, so its ID isn't copied anywhere. The ten records
Cloudflare's scan copied from Gandi, and the Pages challenge record the owner added (D9), are what troupe.run
serves now, so they're **imported, not recreated**: one
`import` block each in `tofu/imports.tf`, ID `<zone_id>/<record_id>`. The zone and record IDs are read with the token
(task 1.3). They identify objects, and aren't secret. The first plan must show the eleven imported with no change before
anything else is approved.

Alternatives:
- **`cloudflare_zone` as a resource.** Creating or importing a zone needs an account-level token (Zone Write on the
  account), and destroying it would take troupe.run off the internet. Keeping the zone out of OpenTofu keeps the token
  to one zone's records, and puts nothing in state that an apply could destroy that badly.
- **Deleting the scanned records and creating them from the declaration.** That was the plan while the zone wasn't
  serving. Now it would take the site down between the delete and the create. It's ruled out.

### D3. One declaration, `tofu/dns.json`, with a stable key for each record

```json
{
  "zone": "troupe.run",
  "ttl": 1,
  "records": {
    "apex-a-108":   { "name": "troupe.run", "type": "A", "content": "185.199.108.153" },
    "www":          { "name": "www.troupe.run", "type": "CNAME", "content": "troupe-run.github.io" },
    "org-verify":   { "name": "_gh-troupe-run-o.troupe.run", "type": "TXT", "content": "\"ab7788e488\"" },
    "mx-null":      { "name": "troupe.run", "type": "MX", "content": ".", "priority": 0 },
    "spf":          { "name": "troupe.run", "type": "TXT", "content": "\"v=spf1 -all\"" },
    "dmarc":        { "name": "_dmarc.troupe.run", "type": "TXT", "content": "\"v=DMARC1; p=reject; sp=reject; adkim=s; aspf=s\"" },
    "caa-issue":    { "name": "troupe.run", "type": "CAA", "flags": 0, "tag": "issue", "value": "letsencrypt.org" },
    "caa-wildcard": { "name": "troupe.run", "type": "CAA", "flags": 0, "tag": "issuewild", "value": ";" },
    "pages-verify": { "name": "_github-pages-challenge-troupe-run.troupe.run", "type": "TXT", "content": "\"f20f50ae5c14b2efb4e971b5c99318\"" }
  }
}
```

(Abbreviated: the other three A and four AAAA records follow the same shape.) `dns.tf` has one
`cloudflare_dns_record` per key, with `proxied = false` written there and nowhere else (spec: "No record is proxied").

**TTL is automatic (`1`, served as 300s)** (owner, 2026-10-17). It's what the scan set, so the import is clean, and a
change takes effect within minutes. A record can override it. Names are fully qualified, which is how the API returns
them, so a plan doesn't show `@` changing to `troupe.run`. The key is what state is keyed by, so changing a record's
content updates it in place, while changing its key replaces it.

`scripts/tests/test_dns.py` validates the file offline. It checks that the types are among A, AAAA, CNAME, MX, TXT
and CAA, and that each type has exactly its fields (`content`, plus `priority` for MX; `flags`, `tag` and `value`
for CAA). Keys are unique, every name is in the zone, and a TXT content is quoted. An unknown field is an error, not
ignored. `json.load` would silently keep the last of two duplicate keys, so the test reads with `object_pairs_hook`
to catch them.

Alternative: HCL locals. They're readable, but the duplicate-key check and the per-type field check would be
`validation` blocks, harder to name failures in than a test. The JSON follows milestones.

### D4. The token: DNS edit on one zone, ephemeral, from 1Password

The owner creates a custom API token with **Zone → DNS → Edit** and **Zone → Zone → Read**, for the troupe.run zone
only, saved in 1Password as item `troupe-run cloudflare dns`, field `credential`, in vault `troupe.run`. It reaches
OpenTofu as `TF_VAR_cloudflare_api_token`, which joins `SECRETS` in `scripts/tofu.py` and `tofu/secrets.env`. Each
job's `env` in `tofu.yml` gets it, and the README's loop sets it in all three environments. The variable is
`sensitive` and `ephemeral`, like `github_app_pem`, and feeds only the provider's `api_token`. So a saved plan holds
only its name, and the apply job gets it again from the environment.

The token isn't IP-restricted, since GitHub's runners have no fixed addresses. Its reach is limited instead: one
zone's records, and Zone Read.

### D5. Reporting what an apply can't see: `check` blocks, surfaced as warnings in CI

Two `check` blocks in `dns.tf`:

- **Undeclared records:** `data "cloudflare_dns_records"` for the zone, compared by name, type and content with the
  declaration. Each one that's left over is named in the assertion's message.
- **Zone active:** `data "cloudflare_zone"`'s `status == "active"`, naming the status and the nameservers Cloudflare
  expects.

A failing `check` block is a warning: it never stops a plan, so a stray record can't block an unrelated pull request
or the apply that fixes it. A warning in a run that plans nothing would go unread, though: a clean daily plan ends
without asking for anything. So each plan step in `tofu.yml` turns every `Check block assertion failed` in the plan's
output into a `::warning::` annotation, which shows on the run's summary and the pull request.

Alternatives:
- **A `postcondition` that fails the plan.** It's louder, but one record added by hand would block every pull request
  and the daily apply until someone dealt with it.
- **`scripts/oob.py`.** It reads only with the owner's `gh`, and would need the Cloudflare token on the owner's
  machine for a check the plan can already make.

### D6. The switch is recorded, and its rollback kept

The comparison the switch needed was made after it: every record in Gandi's export is served by Cloudflare with the
same content (Context). Task 1.1 repeats it, record by record, against Gandi's nameservers, which still serve the old
zone, and records the output. `oob/README.md` records Gandi's nameserver setting, Cloudflare's two nameservers, and
the rollback: set Gandi's three nameservers again. Gandi's LiveDNS records are left as they are for that reason. After
the rollback, Gandi serves the original records, without the new ones.

### D7. A probe under `infra-probe.troupe.run`, before the pull request

The zone is serving now, so the probe can't use the whole of it. It uses only names under `infra-probe.troupe.run`,
which nothing reads (owner, 2026-10-17). The probe (`tofu/probe/`, its own root and git-ignored state, run locally as
the earlier probes were) applies one record of each new shape, then destroys them. It settles what the docs leave
open:

1. whether a plan straight after the apply is clean for each type: quoted TXT, CAA `flags`, the null MX's `.`
   content with `priority = 0`, fully qualified names, and `ttl = 1`;
2. whether importing a record the scan made (`<zone_id>/<record_id>`) plans clean, using one probe record created in
   the dashboard;
3. whether Cloudflare adds its own CAA entries once a CAA record exists while Universal SSL is on, which would break
   "only Let's Encrypt". The probe's CAA records are on a name the site doesn't use, so they can't affect issuance for
   troupe.run;
4. that the undeclared-records check fires on a record added by hand and is quiet once it's gone. The zone-active
   check is expected to pass, since the zone is serving.

The probe's records are on names nothing reads, and they're destroyed afterwards. The zone is then checked to hold
only the eleven adopted records.

### D8. The CAA test forces a new certificate

Once the CAA record is served, the owner removes troupe.run as the website's custom domain and adds it again, which
makes GitHub issue a new certificate. It's done by hand, not by the plan, because it's a one-off check. The plan's
declaration doesn't change, so the next plan shows no drift once it's back. The site has no traffic, so a few minutes
without HTTPS cost nothing. If no certificate is issued within an hour, the CAA record is removed by a pull request,
and the cause is recorded on #55.

### D9. Pages domain verification: started and served by hand, then declared

The owner started it on 2026-10-17 in the org's Settings → Pages → Add a domain, which gave
`_github-pages-challenge-troupe-run` with the value `f20f50ae5c14b2efb4e971b5c99318`. The value isn't secret: it's
published in DNS. The owner added the record in Cloudflare's dashboard the same day, so it's imported like the scanned
records (task 1.1), and pressing Verify doesn't wait for this change. GitHub asks for the record to stay, so it stays
declared.

## Risks / Trade-offs

- [The scan set attributes the declaration doesn't have, such as a comment, tags or `settings`] → The probe (D7,
  point 2) and the pull request's plan show them. Each is declared, or reset with the owner's agreement, before
  merging. The eleven imports must read "0 to change".
- [Cloudflare adds CAA records for its own CAs] → The probe checks for them (D7). If they appear, the owner turns off
  Universal SSL for the zone, which a DNS-only zone doesn't use, and records that in `oob/README.md`.
- [A record is changed in the dashboard before this change merges] → The import's plan shows the difference, and the
  owner decides which is right before approving.
- [Cloudflare's v5 provider still has perpetual diffs on some types] → The probe's clean replan (D7, point 1) is the
  test. A type that won't settle is shaped differently in `dns.tf`, or its diff is recorded as a known issue on #55
  before merging.
- [A warning nobody reads] → CI's annotation (D5) puts it on the run summary. It's still a warning: a record added by
  hand is reported, not removed. That's deliberate, the same as an undeclared milestone.
- [One more secret in every plan run] → It's scoped to one zone's records, and every pull request's plan already
  needs the owner's approval before it gets any secret (spec: ci-apply).

## Migration Plan

1. Done by the owner on 2026-10-17: the zone created, Gandi's records copied by the scan, and the nameservers switched.
2. The owner creates the token and starts Pages domain verification.
3. The probe runs under `infra-probe.troupe.run`, then destroys what it created.
4. The pull request's plan shows the eleven records imported with no change, and creates for the new records only. The
   owner merges and approves the apply.
5. The owner verifies the Pages domain. The CAA test (D8) runs, and the new records are checked from public resolvers.

**Rollback:** an apply that goes wrong is reverted by a pull request. To leave Cloudflare entirely, set Gandi's
nameservers back. Gandi still serves the original records, without the new ones.

## Open Questions

- **An expiry on the token.** None is planned, matching the App key. Setting one later only adds a rotation to the
  README.
