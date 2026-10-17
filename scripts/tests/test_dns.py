"""troupe.run's DNS declaration is well formed and holds the records spec dns requires (spec: dns;
manage-dns-as-code design D3).

Cloudflare refuses a bad record only when the plan is applied, after the merge, and a record
dropped from the declaration would be destroyed. So both are checked here, offline, on every
pull request.
"""

import json
from typing import Any

from conftest import REPO

DNS = REPO / "tofu" / "dns.json"

# Each supported type and exactly the fields it takes besides name, type and an optional ttl.
# There's deliberately no `proxied`: nothing is proxied (spec dns: "No record is proxied").
TYPES: dict[str, frozenset[str]] = {
    "A": frozenset({"content"}),
    "AAAA": frozenset({"content"}),
    "CNAME": frozenset({"content"}),
    "TXT": frozenset({"content"}),
    "MX": frozenset({"content", "priority"}),
    "CAA": frozenset({"flags", "tag", "value"}),
}
COMMON = frozenset({"name", "type"})
OPTIONAL = frozenset({"ttl"})
# universal_ssl decides which CAs the CAA records admit, so it's declared beside them (spec dns:
# "troupe.run's Universal SSL setting is declared once"; declare-universal-ssl design D1), and it
# must be off (spec dns: "Only Let's Encrypt may issue certificates"; turn-off-universal-ssl D2).
TOP_LEVEL = frozenset({"zone", "ttl", "universal_ssl", "records"})

# (name, type, content) of the records troupe.run had at Gandi (spec dns: "The records from
# before the move are kept").
KEPT = {
    *(("troupe.run", "A", f"185.199.{n}.153") for n in (108, 109, 110, 111)),
    *(("troupe.run", "AAAA", f"2606:50c0:800{n}::153") for n in range(4)),
    ("www.troupe.run", "CNAME", "troupe-run.github.io"),
    ("_gh-troupe-run-o.troupe.run", "TXT", '"ab7788e488"'),
}


def parse(text: str) -> tuple[dict[str, Any], list[str]]:
    """The declaration, and each key declared twice anywhere in it (json.loads keeps the last)."""
    duplicates: list[str] = []

    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: dict[str, Any] = {}
        for key, value in pairs:
            if key in seen:
                duplicates.append(f"{key}: declared twice in tofu/dns.json")
            seen[key] = value
        return seen

    return json.loads(text, object_pairs_hook=no_duplicates), duplicates


def record_problems(key: str, record: dict[str, Any], zone: str) -> list[str]:
    """What's wrong with one record, each naming its key."""
    kind = record.get("type")
    if kind not in TYPES:
        return [f"{key}: type is {kind!r}; supported types are {', '.join(TYPES)}"]
    fields = set(record)
    allowed = COMMON | OPTIONAL | TYPES[kind]
    found = [f"{key}: {kind} records don't take {field!r}" for field in sorted(fields - allowed)]
    found += [
        f"{key}: {kind} records need {field!r}" for field in sorted((COMMON | TYPES[kind]) - fields)
    ]
    name = record.get("name", "")
    if name != zone and not name.endswith(f".{zone}"):
        found.append(f"{key}: name {name!r} isn't in the {zone} zone; write it fully qualified")
    content = record.get("content")
    if (
        kind == "TXT"
        and isinstance(content, str)
        and not (len(content) >= 2 and content.startswith('"') and content.endswith('"'))
    ):
        found.append(f"{key}: TXT content must be quoted, as Cloudflare stores it: {content!r}")
    return found


def declaration_problems(text: str) -> list[str]:
    """Every problem in the declaration's text, or [] when it's well formed."""
    declared, found = parse(text)
    found += [
        f"{field}: unknown top-level field in tofu/dns.json"
        for field in sorted(set(declared) - TOP_LEVEL)
    ]
    found += [f"{field}: tofu/dns.json needs it" for field in sorted(TOP_LEVEL - set(declared))]
    universal_ssl = declared.get("universal_ssl", False)
    if not isinstance(universal_ssl, bool):
        found.append(f"universal_ssl: is {universal_ssl!r}; it takes true or false")
    elif universal_ssl:
        found.append(
            "universal_ssl: is true; it must be false, because while it's on Cloudflare adds CAA"
            " records for its own CAs beside the declared ones (spec dns: Only Let's Encrypt may"
            " issue certificates)"
        )
    for key, record in declared.get("records", {}).items():
        found += record_problems(key, record, declared.get("zone", ""))
    return found


def declared_records() -> list[dict[str, Any]]:
    declared, _ = parse(DNS.read_text(encoding="utf-8"))
    records: dict[str, dict[str, Any]] = declared["records"]
    return list(records.values())


def text(records: dict[str, Any], **top: object) -> str:
    return json.dumps(
        {"zone": "troupe.run", "ttl": 1, "universal_ssl": False, "records": records, **top}
    )


def a_record(**fields: object) -> dict[str, Any]:
    return {"name": "troupe.run", "type": "A", "content": "192.0.2.1", **fields}


def test_the_declaration_is_well_formed() -> None:
    assert declaration_problems(DNS.read_text(encoding="utf-8")) == []


def test_every_record_from_before_the_move_is_declared() -> None:
    declared = {(r["name"], r["type"], r["content"]) for r in declared_records() if "content" in r}
    assert sorted(KEPT - declared) == []


def test_the_mail_lockdown_is_declared() -> None:
    records = declared_records()
    pairs = {(r["name"], r["type"], r.get("content"), r.get("priority")) for r in records}
    assert ("troupe.run", "MX", ".", 0) in pairs
    assert ("troupe.run", "TXT", '"v=spf1 -all"', None) in pairs
    dmarc = [r["content"] for r in records if r["name"] == "_dmarc.troupe.run"]
    assert len(dmarc) == 1
    assert {"p=reject", "sp=reject"} <= {part.strip() for part in dmarc[0].strip('"').split(";")}


def test_the_declared_caa_records_name_only_lets_encrypt() -> None:
    caa = {(r["tag"], r["value"], r["flags"]) for r in declared_records() if r["type"] == "CAA"}
    assert caa == {("issue", "letsencrypt.org", 0), ("issuewild", ";", 0)}


def test_the_pages_verification_record_is_declared() -> None:
    names = {r["name"] for r in declared_records() if r["type"] == "TXT"}
    assert "_github-pages-challenge-troupe-run.troupe.run" in names


def test_an_unknown_type_names_the_key_and_the_supported_types() -> None:
    assert declaration_problems(text({"x": a_record(type="SRV")})) == [
        "x: type is 'SRV'; supported types are A, AAAA, CNAME, TXT, MX, CAA"
    ]


def test_a_duplicate_key_is_named() -> None:
    record = json.dumps(a_record())
    raw = (
        f'{{"zone": "troupe.run", "ttl": 1, "universal_ssl": false, '
        f'"records": {{"x": {record}, "x": {record}}}}}'
    )
    assert declaration_problems(raw) == ["x: declared twice in tofu/dns.json"]


def test_a_field_the_type_does_not_take_is_named() -> None:
    assert declaration_problems(text({"x": a_record(priority=0)})) == [
        "x: A records don't take 'priority'"
    ]


def test_a_record_cannot_be_proxied() -> None:
    assert declaration_problems(text({"x": a_record(proxied=True)})) == [
        "x: A records don't take 'proxied'"
    ]


def test_a_missing_field_is_named() -> None:
    record = {"name": "troupe.run", "type": "MX", "content": "."}
    assert declaration_problems(text({"mx": record})) == ["mx: MX records need 'priority'"]


def test_a_name_outside_the_zone_is_named() -> None:
    assert declaration_problems(text({"x": a_record(name="www")})) == [
        "x: name 'www' isn't in the troupe.run zone; write it fully qualified"
    ]


def test_unquoted_txt_content_is_named() -> None:
    record = {"name": "troupe.run", "type": "TXT", "content": "v=spf1 -all"}
    assert declaration_problems(text({"spf": record})) == [
        "spf: TXT content must be quoted, as Cloudflare stores it: 'v=spf1 -all'"
    ]


def test_an_unknown_top_level_field_is_named() -> None:
    assert declaration_problems(text({"x": a_record()}, proxied=False)) == [
        "proxied: unknown top-level field in tofu/dns.json"
    ]


def test_a_well_formed_caa_record_is_valid() -> None:
    record = {"name": "troupe.run", "type": "CAA", "flags": 0, "tag": "issue", "value": "x"}
    assert declaration_problems(text({"caa": record})) == []


def test_a_missing_universal_ssl_is_named() -> None:
    declared = json.loads(text({"x": a_record()}))
    del declared["universal_ssl"]
    assert declaration_problems(json.dumps(declared)) == ["universal_ssl: tofu/dns.json needs it"]


def test_a_universal_ssl_that_is_not_a_boolean_is_named() -> None:
    assert declaration_problems(text({"x": a_record()}, universal_ssl="false")) == [
        "universal_ssl: is 'false'; it takes true or false"
    ]


def test_universal_ssl_off_is_accepted() -> None:
    assert declaration_problems(text({"x": a_record()}, universal_ssl=False)) == []


def test_universal_ssl_on_is_refused_with_why() -> None:
    assert declaration_problems(text({"x": a_record()}, universal_ssl=True)) == [
        "universal_ssl: is true; it must be false, because while it's on Cloudflare adds CAA"
        " records for its own CAs beside the declared ones (spec dns: Only Let's Encrypt may"
        " issue certificates)"
    ]
