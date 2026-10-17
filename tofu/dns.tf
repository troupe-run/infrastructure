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

# What an apply can't see is reported, not fixed: a failed check is a warning, so a stray record
# can't block an unrelated plan, and scripts/plan_checks.py puts it on the run (design D5).
check "undeclared_records" {
  data "cloudflare_dns_records" "all" {
    zone_id   = data.cloudflare_zone.troupe_run.id
    max_items = 1000
  }

  assert {
    condition = length([
      for record in data.cloudflare_dns_records.all.result : record
      if !contains([for declared in cloudflare_dns_record.troupe_run : declared.id], record.id)
    ]) == 0
    error_message = "Records in the troupe.run zone that tofu/dns.json doesn't declare: ${join(", ", [
      for record in data.cloudflare_dns_records.all.result : "${record.name} ${record.type} ${record.content}"
      if !contains([for declared in cloudflare_dns_record.troupe_run : declared.id], record.id)
    ])}. Declare each one in tofu/dns.json, or delete it in Cloudflare."
  }
}

check "zone_active" {
  assert {
    condition     = data.cloudflare_zone.troupe_run.status == "active"
    error_message = "Cloudflare reports the troupe.run zone as ${data.cloudflare_zone.troupe_run.status}, not active. troupe.run's nameservers at Gandi should be ${join(" and ", data.cloudflare_zone.troupe_run.name_servers)} (oob/README.md)."
  }
}
