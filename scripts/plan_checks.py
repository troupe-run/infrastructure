"""Turn each failed `check` block in a saved plan into a warning on the run.

Usage (in .github/workflows/tofu.yml):
    tofu show -json main.tfplan > plan.json
    uv run --no-project scripts/plan_checks.py --plan-json plan.json --summary checks.md

Spec: dns ("A record added outside OpenTofu is reported", "An inactive zone is reported");
design: manage-dns-as-code D5. A failing check block is only a warning, so it never stops a plan,
and `tofu show` of a saved plan leaves it out. This prints a `::warning::` annotation for each one,
which GitHub shows on the run, and writes a Markdown section for the posted plan and the step
summary. A status this doesn't know is an error rather than ignored.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

WARN = {"fail", "error"}
QUIET = {"pass"}
UNEVALUATED = "unknown"
KNOWN = WARN | QUIET | {UNEVALUATED}


def warnings(plan: dict[str, Any]) -> list[tuple[str, str]]:
    """(check, message) for each check instance that didn't pass."""
    found: list[tuple[str, str]] = []
    for check in plan.get("checks", []):
        if check["address"].get("kind") != "check":
            continue
        for instance in check.get("instances", []):
            name = instance["address"]["to_display"]
            status = instance["status"]
            if status not in KNOWN:
                raise ValueError(
                    f"{name}: unknown status {status!r}; known: {', '.join(sorted(KNOWN))}"
                )
            if status == UNEVALUATED:
                found.append((name, "couldn't be evaluated at plan time"))
            elif status in WARN:
                found += [(name, problem["message"]) for problem in instance.get("problems", [])]
    return found


def annotation(name: str, message: str) -> str:
    """A workflow command; %, CR and LF in its message would otherwise be read as syntax."""
    escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return f"::warning title={name}::{escaped}"


def summary(found: list[tuple[str, str]]) -> str:
    if not found:
        return ""
    lines = ["**Check warnings** (a plan doesn't fix these; see spec dns):", ""]
    lines += [f"- `{name}`: {message}" for name, message in found]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan-json", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        found = warnings(json.loads(args.plan_json.read_text(encoding="utf-8")))
    except ValueError as error:
        print(f"plan_checks.py: {error}", file=sys.stderr)
        return 2
    for name, message in found:
        print(annotation(name, message))
    args.summary.write_text(summary(found), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
