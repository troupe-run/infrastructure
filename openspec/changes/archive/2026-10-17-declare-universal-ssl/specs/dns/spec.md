## RENAMED Requirements

- FROM: `### Requirement: Only Let's Encrypt may issue certificates`
- TO: `### Requirement: CAA limits who may issue certificates`

## MODIFIED Requirements

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

## ADDED Requirements

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
