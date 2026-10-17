# troupe.run's DNS records, served by Cloudflare (spec: dns; #55). The domain is registered at Gandi,
# whose nameservers point at Cloudflare; that, the zone and the token are set up by hand
# (oob/README.md).
#
# Declared in dns.json, which scripts/tests/test_dns.py checks offline. Each record's key names its
# address and never changes: changing a key replaces the record. Nothing is proxied, here and
# nowhere else, so the answers are GitHub's own addresses and Pages can issue the certificate
# (manage-dns-as-code design D2, D3).

locals {
  dns = jsondecode(file("${path.module}/dns.json"))
}

# Read, not managed: creating or destroying a zone needs an account-wide token, and destroying this
# one would take troupe.run off the internet (design D2).
data "cloudflare_zone" "troupe_run" {
  filter = {
    name = local.dns.zone
  }
}

resource "cloudflare_dns_record" "troupe_run" {
  for_each = local.dns.records

  zone_id  = data.cloudflare_zone.troupe_run.id
  name     = each.value.name
  type     = each.value.type
  ttl      = try(each.value.ttl, local.dns.ttl)
  proxied  = false
  content  = each.value.type == "CAA" ? null : each.value.content
  priority = try(each.value.priority, null)
  data = each.value.type == "CAA" ? {
    flags = each.value.flags
    tag   = each.value.tag
    value = each.value.value
  } : null
}

# Universal SSL is off, so the declared CAA records are the whole policy: while it's on, Cloudflare
# adds `issue` and `issuewild` records for its own CAs beside them, which aren't in the API, so the
# undeclared check below can't see them (spec dns; turn-off-universal-ssl). It stays declared so a
# change in the dashboard shows in the plan. The provider's delete does nothing, so removing this
# block stops managing the setting without changing it, and there's no prevent_destroy to add
# (declare-universal-ssl design D2).
resource "cloudflare_universal_ssl_setting" "troupe_run" {
  zone_id = data.cloudflare_zone.troupe_run.id
  enabled = local.dns.universal_ssl
}

# What an apply can't see is reported, not fixed: a failed check is a warning, so a stray record
# can't block an unrelated plan, and scripts/plan_checks.py puts it on the run (design D5).
#
# The zone is read one record type at a time. One cloudflare_dns_records list holding CAA records
# and others panics OpenTofu (5.28.0 with 1.13.1), at plan and while an apply saves state; one list
# per type doesn't (design D5, the probe of 2026-10-17). It's the provider's open bug
# https://github.com/cloudflare/terraform-provider-cloudflare/issues/7004: once that's fixed, retest
# with the probe's probe_dns_read_all before going back to one read. Every type the API has is read,
# not only the declared ones, so a stray record of any type is reported. Going back to one read is #73.
locals {
  dns_record_types = toset([
    "A", "AAAA", "CAA", "CERT", "CNAME", "DNSKEY", "DS", "HTTPS", "LOC", "MX", "NAPTR", "NS",
    "OPENPGPKEY", "PTR", "SMIMEA", "SRV", "SSHFP", "SVCB", "TLSA", "TXT", "URI",
  ])

  dns_undeclared = [
    for record in flatten([for read in data.cloudflare_dns_records.troupe_run : read.result]) :
    "${record.name} ${record.type} ${record.content}"
    if !contains([for declared in cloudflare_dns_record.troupe_run : declared.id], record.id)
  ]
}

data "cloudflare_dns_records" "troupe_run" {
  for_each = local.dns_record_types

  zone_id   = data.cloudflare_zone.troupe_run.id
  type      = each.key
  max_items = 1000
}

check "undeclared_records" {
  assert {
    condition     = length(local.dns_undeclared) == 0
    error_message = "Records in the troupe.run zone that tofu/dns.json doesn't declare: ${join(", ", local.dns_undeclared)}. Declare each one in tofu/dns.json, or delete it in Cloudflare."
  }
}

check "zone_active" {
  assert {
    condition     = data.cloudflare_zone.troupe_run.status == "active"
    error_message = "Cloudflare reports the troupe.run zone as ${data.cloudflare_zone.troupe_run.status}, not active. troupe.run's nameservers at Gandi should be ${join(" and ", data.cloudflare_zone.troupe_run.name_servers)} (oob/README.md)."
  }
}
