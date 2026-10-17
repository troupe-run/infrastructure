# Proposal: publish troupe.run's new Pages verification record

## Why

troupe.run was removed from the org's Pages verified domains by mistake during #55's follow-up, and added back the
same day (2026-10-17). GitHub issued a new challenge value. The zone still serves the old one from `tofu/dns.json`, so
troupe.run can't be verified for Pages, and nothing stops another account's Pages site from claiming it (#76).

## What Changes

- `tofu/dns.json`'s `pages-verify` record changes from `"f20f50ae5c14b2efb4e971b5c99318"` to
  `"5f257f97c64f4931616bb34e817511"`. The record keeps its key, so the plan updates it in place.
- After the apply, the owner presses Verify in the org's Pages settings.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The `dns` spec already says the record holds the value GitHub gives ("troupe.run is a verified Pages domain for
the org"). Only that value changes, so `skip_specs` is set.

## Impact

- `tofu/dns.json`: one value.
- The live zone: one TXT record's content changes in place. Nothing else in troupe.run's answers changes.
