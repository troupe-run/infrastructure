"""A failed `check` block in a plan reaches the run as a warning (spec: dns; manage-dns-as-code
design D5).

`tofu show` of a saved plan leaves the warnings out, so the posted plan never shows them. The
fixture is `tofu show -json` of a real plan with one failing and one passing check block
(OpenTofu 1.13.1, 2026-10-17).
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from conftest import REPO

import plan_checks

SCRIPT = REPO / "scripts" / "plan_checks.py"

MESSAGE = (
    'Records in the zone that tofu/dns.json doesn\'t declare: probe.troupe.run TXT "x". '
    "Declare them, or delete them in Cloudflare."
)
REAL_CHECKS: list[dict[str, Any]] = [
    {
        "address": {
            "kind": "check",
            "name": "undeclared_records",
            "to_display": "check.undeclared_records",
        },
        "status": "fail",
        "instances": [
            {
                "address": {"to_display": "check.undeclared_records"},
                "status": "fail",
                "problems": [{"message": MESSAGE}],
            }
        ],
    },
    {
        "address": {"kind": "check", "name": "zone_active", "to_display": "check.zone_active"},
        "status": "pass",
        "instances": [{"address": {"to_display": "check.zone_active"}, "status": "pass"}],
    },
]


def check(name: str, status: str, message: str | None = None) -> dict[str, Any]:
    instance: dict[str, Any] = {"address": {"to_display": f"check.{name}"}, "status": status}
    if message is not None:
        instance["problems"] = [{"message": message}]
    return {
        "address": {"kind": "check", "name": name, "to_display": f"check.{name}"},
        "status": status,
        "instances": [instance],
    }


def test_a_failed_check_is_one_warning_naming_it() -> None:
    assert plan_checks.warnings({"checks": REAL_CHECKS}) == [("check.undeclared_records", MESSAGE)]


def test_a_plan_with_no_checks_has_no_warnings() -> None:
    assert plan_checks.warnings({"format_version": "1.2"}) == []


def test_an_errored_check_warns_too() -> None:
    plan = {"checks": [check("zone_active", "error", "status is unknown")]}
    assert plan_checks.warnings(plan) == [("check.zone_active", "status is unknown")]


def test_a_check_that_could_not_be_evaluated_warns_saying_so() -> None:
    plan = {"checks": [check("zone_active", "unknown")]}
    assert plan_checks.warnings(plan) == [
        ("check.zone_active", "couldn't be evaluated at plan time")
    ]


def test_a_status_it_does_not_know_is_an_error() -> None:
    with pytest.raises(ValueError, match=r"check\.x: unknown status 'skipped'; known: "):
        plan_checks.warnings({"checks": [check("x", "skipped")]})


def test_the_annotation_escapes_what_workflow_commands_would_read() -> None:
    assert plan_checks.annotation("check.x", "50% done\nnext") == (
        "::warning title=check.x::50%25 done%0Anext"
    )


def run(tmp_path: Path, plan: dict[str, Any]) -> tuple[subprocess.CompletedProcess[str], str]:
    plan_json = tmp_path / "plan.json"
    plan_json.write_text(json.dumps(plan))
    summary = tmp_path / "checks.md"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--plan-json", str(plan_json), "--summary", str(summary)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result, summary.read_text()


def test_the_script_prints_one_annotation_and_summarises_it(tmp_path: Path) -> None:
    result, summary = run(tmp_path, {"checks": REAL_CHECKS})
    assert result.returncode == 0
    assert result.stdout.splitlines() == [f"::warning title=check.undeclared_records::{MESSAGE}"]
    assert "check.undeclared_records" in summary
    assert MESSAGE in summary


def test_a_plan_whose_checks_pass_prints_and_summarises_nothing(tmp_path: Path) -> None:
    result, summary = run(tmp_path, {"checks": [REAL_CHECKS[1]]})
    assert result.returncode == 0
    assert result.stdout == ""
    assert summary == ""
