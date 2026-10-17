# dns Specification

## Purpose

Keeps troupe.run's DNS declared once and changed only through this repository's plan-and-approve path. Covers the
records the site needs, what the domain publishes so nobody can send mail as it or get a certificate for it from an
unexpected issuer, and how a record changed outside that path shows up.

## Requirements

### Requirement: troupe.run's records are declared once
Every DNS record troupe.run serves SHALL be declared in one place, each with a stable key, a name, a type, its
content and a TTL. The zone SHALL serve exactly the declared records. A difference between a declared record and the
zone SHALL appear in the plan.

#### Scenario: A record changed by hand shows as drift
- **WHEN** someone changes the content of a declared record in the zone outside OpenTofu
- **THEN** the next plan shows it changing back to the declared content

#### Scenario: A record deleted by hand shows as drift
- **WHEN** someone deletes a declared record from the zone outside OpenTofu
- **THEN** the next plan shows it being created again

#### Scenario: A declared record is added
- **WHEN** a pull request adds a record to the declaration and a plan runs
- **THEN** the plan shows that record being created, and no change to any other record

### Requirement: The records from before the move are kept
The zone SHALL serve the records troupe.run had at Gandi, with the same content: `troupe.run` A 185.199.108.153,
185.199.109.153, 185.199.110.153 and 185.199.111.153; AAAA 2606:50c0:8000::153, 2606:50c0:8001::153,
2606:50c0:8002::153 and 2606:50c0:8003::153; `www.troupe.run` CNAME `troupe-run.github.io.`; and
`_gh-troupe-run-o.troupe.run` TXT `"ab7788e488"`.

#### Scenario: The new nameservers answer as the old ones did
- **WHEN** each of these names and types is queried at the zone's nameservers and at Gandi's
- **THEN** both return the same content

#### Scenario: Adopting the records changes nothing
- **WHEN** the first plan with the declaration runs against the zone Cloudflare is serving
- **THEN** it imports each of these records and plans no change to any of them

#### Scenario: The site serves after the move
- **WHEN** the nameservers have switched and https://troupe.run and https://www.troupe.run are fetched
- **THEN** both reach the website over HTTPS with a valid certificate, `www` redirecting to `troupe.run`

### Requirement: No record is proxied
Every record SHALL be served as plain DNS, never through the DNS host's proxy, so the answers are GitHub's own
addresses and GitHub Pages can issue and serve the site's certificate. The declaration SHALL have no way to proxy a
record.

#### Scenario: The apex answers with GitHub's addresses
- **WHEN** `troupe.run` A is queried after the move
- **THEN** the answers are the four declared GitHub Pages addresses, not the DNS host's

### Requirement: The domain sends no mail
troupe.run SHALL publish that it sends and receives no mail: a null MX record (`0 .`), an SPF record `v=spf1 -all`
on `troupe.run`, and a DMARC record on `_dmarc.troupe.run` with policy `reject` for the domain and its subdomains.

#### Scenario: Mail records are published
- **WHEN** MX and TXT for `troupe.run`, and TXT for `_dmarc.troupe.run`, are queried after the move
- **THEN** MX is `0 .`, the apex TXT includes `v=spf1 -all`, and the DMARC TXT has `p=reject` and `sp=reject`

### Requirement: CAA limits who may issue certificates
troupe.run SHALL publish CAA records that let only Let's Encrypt issue certificates for it, and forbid wildcards. With
Universal SSL on, Cloudflare adds `issue` and `issuewild` records for its own CAs that the API doesn't list, so
issuance, wildcards included, SHALL be limited to Let's Encrypt and those CAs. With it off, issuance SHALL be limited
to Let's Encrypt, with no wildcards. GitHub Pages SHALL still issue the site's certificate. A CNAME, such as `www`,
takes its target's CAA policy.

#### Scenario: The CAA record is published
- **WHEN** CAA for `troupe.run` is queried at the zone's nameservers
- **THEN** the answers include `issue` `letsencrypt.org` and `issuewild` `;`, as declared

#### Scenario: The CAA records are published with Universal SSL on
- **WHEN** the declaration has `universal_ssl` on and CAA for `troupe.run` is queried at the zone's nameservers
- **THEN** `issue` names `letsencrypt.org` and otherwise only CAs that Cloudflare's CAA documentation lists for
  Universal SSL, and `issuewild` is `;` plus only those same names

#### Scenario: The CAA records are published with Universal SSL off
- **WHEN** the declaration has `universal_ssl` off, it has been applied, and CAA for `troupe.run` is queried at the
  zone's nameservers
- **THEN** `issue` names only `letsencrypt.org`, and `issuewild` is only `;`

#### Scenario: Cloudflare's added records aren't reported as undeclared
- **WHEN** a plan runs with Universal SSL on
- **THEN** the undeclared-records check doesn't report Cloudflare's added CAA records, because the API doesn't list
  them, so what's published is checked by querying the nameservers instead

#### Scenario: Pages still issues a certificate
- **WHEN** GitHub Pages is made to issue a new certificate for troupe.run with the CAA record published
- **THEN** a new certificate from Let's Encrypt is issued, and https://troupe.run serves it

### Requirement: troupe.run's Universal SSL setting is declared once
Whether Cloudflare's Universal SSL is on for troupe.run SHALL be declared once, next to the CAA records it changes,
and the zone SHALL have the declared setting. A difference between the declaration and the zone SHALL appear in the
plan. A declaration that doesn't say whether it's on SHALL be refused.

#### Scenario: Adopting the setting changes nothing
- **WHEN** the first plan with the declaration runs against the zone as Cloudflare serves it
- **THEN** it imports the setting as on and plans no change to it, or to any record

#### Scenario: A difference from the declaration shows in the plan
- **WHEN** the declared setting differs from the zone's and a plan runs
- **THEN** the plan shows the setting changing to the declared value

#### Scenario: The setting is left out
- **WHEN** the declaration has no `universal_ssl`, or its value isn't `true` or `false`
- **THEN** `scripts/check.py` fails, naming `universal_ssl` and what it takes

### Requirement: The org's domain verification is kept
The TXT record that verifies troupe.run for the troupe-run organisation (`_gh-troupe-run-o`) SHALL be declared with
the value it has, so the domain stays verified when GitHub re-checks it.

#### Scenario: The domain stays verified for the org
- **WHEN** the org's verified domains are read after the apply
- **THEN** troupe.run is verified (`isVerified: true`)

### Requirement: troupe.run is a verified Pages domain for the org
The TXT record GitHub gives for verifying troupe.run as a Pages domain for the troupe-run organisation
(`_github-pages-challenge-troupe-run`) SHALL be declared, and troupe.run SHALL be verified, so no Pages site outside
the org can claim it.

#### Scenario: The Pages domain is verified
- **WHEN** the challenge record is served and the owner asks GitHub to verify it
- **THEN** the org's Pages settings list troupe.run as verified

#### Scenario: The site keeps serving
- **WHEN** troupe.run is verified as a Pages domain
- **THEN** https://troupe.run still serves the website

### Requirement: A malformed declaration is refused
`scripts/check.py` SHALL fail on a malformed DNS declaration, naming the record and the problem: a duplicate key, an
unknown record type, a missing field, or a field that doesn't belong to the record's type.

#### Scenario: An unknown record type
- **WHEN** a declared record has a type the declaration doesn't support
- **THEN** `scripts/check.py` fails, naming the record's key, its type, and the supported types

#### Scenario: A duplicate key
- **WHEN** two declared records share a key
- **THEN** `scripts/check.py` fails, naming the key

#### Scenario: A field the type doesn't take
- **WHEN** a declared A record has a field only MX or CAA records take
- **THEN** `scripts/check.py` fails, naming the record's key and the field

### Requirement: A record added outside OpenTofu is reported
A plan SHALL report every record in the zone that isn't declared, naming it, because an apply only manages the
records it declares.

#### Scenario: A record added by hand
- **WHEN** someone adds a record to the zone outside OpenTofu and a plan runs
- **THEN** the plan reports that record, by name and type, as not declared

### Requirement: An inactive zone is reported
A plan SHALL report when the DNS host doesn't consider the troupe.run zone active, for example because troupe.run's
nameservers at the registrar no longer point at it. The nameservers are set by hand at the registrar, and are
recorded in `oob/README.md` with how to change them back.

#### Scenario: The nameservers are changed at the registrar
- **WHEN** troupe.run's nameservers at Gandi are changed away from the DNS host's, and the host marks the zone
  inactive
- **THEN** the next plan reports that the zone isn't active
