"""Drift checks for what OpenTofu can't manage (design D6; see oob/README.md).

Usage: uv run scripts/oob.py

Compares each declaration in oob/ with GitHub, read with the owner's `gh`, prints every
difference and exits 1 if there are any. It only reads: no call writes to GitHub.
"""

import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OOB = ROOT / "oob"
ORG = "troupe-run"

Record = dict[str, Any]
Fetch = Callable[[list[str]], Any]


@dataclass(frozen=True)
class Check:
    """One thing outside OpenTofu: its declaration file, how to read it, and its key field.

    A declaration is either a JSON file in oob/ or, where this repo already holds the source,
    derived from it (so there is no second list to keep in step).
    """

    name: str
    declaration: str
    key: str
    gh_args: list[str]
    derived: Callable[[Path], list[Record]] | None = None


def org_profile_files(root: Path) -> list[Record]:
    """Every file under org-profile/, the source of troupe-run/.github (spec: org-profile)."""
    source = root / "org-profile"
    return [{"path": p.relative_to(source).as_posix()} for p in source.rglob("*") if p.is_file()]


CHECKS = [
    Check(
        name=".github files",
        declaration="org-profile/ (derived)",
        key="path",
        gh_args=[
            "api",
            f"repos/{ORG}/.github/git/trees/main?recursive=1",
            "--jq",
            '[.tree[] | select(.type == "blob") | {path}]',
        ],
        derived=org_profile_files,
    ),
    Check(
        name="org settings",
        declaration="org-settings.json",
        key="name",
        gh_args=[
            "api",
            f"orgs/{ORG}",
            "--jq",
            '[{name: "two_factor_requirement_enabled", value: .two_factor_requirement_enabled}]',
        ],
    ),
    Check(
        name="App installations",
        declaration="app-installations.json",
        key="app_slug",
        gh_args=[
            "api",
            f"orgs/{ORG}/installations",
            "--jq",
            "[.installations[] | {app_slug, repository_selection, permissions}]",
        ],
    ),
    Check(
        name="issue types",
        declaration="issue-types.json",
        key="name",
        gh_args=[
            "api",
            f"orgs/{ORG}/issue-types",
            "--jq",
            "[.[] | {name, description, color, is_enabled}]",
        ],
    ),
    Check(
        name="projects",
        declaration="projects.json",
        key="number",
        gh_args=[
            "api",
            "graphql",
            "-f",
            f'query={{organization(login:"{ORG}"){{projectsV2(first:100)'
            "{nodes{number title public closed shortDescription}}}}",
            "--jq",
            ".data.organization.projectsV2.nodes",
        ],
    ),
]


def differences(name: str, key: str, declared: list[Record], actual: list[Record]) -> list[str]:
    """Every item missing, extra or changed, in a stable order."""
    want = {item[key]: item for item in declared}
    have = {item[key]: item for item in actual}
    found: list[str] = []
    for k in sorted(want.keys() - have.keys(), key=str):
        found.append(f"{name}: {k!r} is declared but missing on GitHub")
    for k in sorted(have.keys() - want.keys(), key=str):
        found.append(f"{name}: {k!r} is on GitHub but not declared")
    for k in sorted(want.keys() & have.keys(), key=str):
        for field in sorted(want[k].keys() | have[k].keys()):
            if want[k].get(field) != have[k].get(field):
                found.append(
                    f"{name}: {k!r} {field} is {have[k].get(field)!r} on GitHub, "
                    f"declared {want[k].get(field)!r}"
                )
    return found


def gh(args: list[str]) -> Any:  # noqa: ANN401 (JSON)
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def run(fetch: Fetch, oob_dir: Path, root: Path = ROOT) -> list[str]:
    found: list[str] = []
    for check in CHECKS:
        if check.derived is not None:
            declared = check.derived(root)
        else:
            declared = json.loads((oob_dir / check.declaration).read_text())
        found += differences(check.name, check.key, declared, fetch(check.gh_args))
    return found


def main() -> int:
    found = run(gh, OOB, ROOT)
    for line in found:
        print(line)
    if found:
        print(f"oob: {len(found)} difference(s). Fix GitHub, or update the declaration in oob/.")
        return 1
    print(f"oob: no differences ({', '.join(c.name for c in CHECKS)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
