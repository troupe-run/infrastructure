"""Drift checks for what OpenTofu can't manage (design D6; see oob/README.md).

Usage: uv run scripts/oob.py

Compares each declaration in oob/ with GitHub, read with the owner's `gh`, prints every
difference and exits 1 if there are any. It only reads: no call writes to GitHub.
"""

import base64
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
            "{nodes{number title public closed shortDescription"
            " repositories(first:100){nodes{name}}}}}}",
            "--jq",
            # The repositories each project is linked to, by name: OpenTofu can't link a project
            # (govern-website design D4).
            "[.data.organization.projectsV2.nodes[]"
            " | .repositories = ([.repositories.nodes[].name] | sort)]",
        ],
    ),
]


# troupe's spec folders, each of which needs a cap:<folder> label (spec: labels). The check is one
# way, unlike CHECKS: a label with no spec isn't reported, since a label can come before its spec.
SPECS_GH_ARGS = [
    "api",
    f"repos/{ORG}/troupe/contents/openspec/specs",
    "--jq",
    '[.[] | select(.type == "dir") | .name]',
]
TROUPE_LABELS = "tofu/labels/troupe.json"


def unlabelled_specs(specs: list[str], root: Path) -> list[str]:
    """Each troupe spec folder with no declared cap:<folder> label."""
    labels = {label["name"] for label in json.loads((root / TROUPE_LABELS).read_text())}
    return [
        f"troupe specs: {spec!r} has no cap:{spec} label; add it to {TROUPE_LABELS} by pull request"
        for spec in sorted(specs)
        if f"cap:{spec}" not in labels
    ]


# The Purpose each troupe-spec-based cap: label's description was written from, verbatim with its
# whitespace collapsed, so a Purpose troupe later rewrites shows up (spec: labels;
# cap-label-descriptions design D1, D2).
PURPOSES = "troupe-spec-purposes.json"


def purpose_gh_args(spec: str) -> list[str]:
    return [
        "api",
        f"repos/{ORG}/troupe/contents/openspec/specs/{spec}/spec.md",
        "--jq",
        "{content}",
    ]


def purpose(spec_md: str) -> str:
    """The text of a spec's `## Purpose` section, whitespace collapsed; "" when there is none."""
    lines: list[str] = []
    inside = False
    for line in spec_md.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = line.strip() == "## Purpose"
        elif inside:
            lines.append(line)
    return " ".join(" ".join(lines).split())


def stale_descriptions(fetch: Fetch, specs: list[str], oob_dir: Path, root: Path) -> list[str]:
    """Each labelled troupe spec whose Purpose isn't the one its label's description records."""
    labels = {label["name"] for label in json.loads((root / TROUPE_LABELS).read_text())}
    recorded: dict[str, str] = json.loads((oob_dir / PURPOSES).read_text())
    record = f"oob/{PURPOSES}"
    found: list[str] = []
    for spec in sorted(specs):
        label = f"cap:{spec}"
        if label not in labels:
            continue  # unlabelled_specs reports it
        if label not in recorded:
            found.append(
                f"troupe labels: {label!r} description hasn't been checked against its spec's "
                f"Purpose; record the Purpose in {record}"
            )
            continue
        content = base64.b64decode(fetch(purpose_gh_args(spec))["content"]).decode()
        if purpose(content) != " ".join(recorded[label].split()):
            found.append(
                f"troupe labels: {label!r} spec's Purpose has changed; review its description in "
                f"{TROUPE_LABELS} and update {record}"
            )
    for label in sorted(recorded.keys() - {f"cap:{spec}" for spec in specs}):
        found.append(
            f"troupe labels: {label!r} has a recorded Purpose but troupe has no "
            f"{label.removeprefix('cap:')} spec; remove it from {record}"
        )
    return found


# The code security configuration that turns on each managed repository's dependency graph,
# Dependabot and secret scanning, its default for new repositories, and where it's attached
# (spec: repositories, org-settings; security-scanning design D4, D7). The provider can't manage
# configurations. GitHub's own built-in configurations (target_type "global") aren't declared.
CODE_SECURITY = "code-security.json"
CONFIGURATION_FIELDS = [
    "name",
    "enforcement",
    "advanced_security",
    "dependency_graph",
    "dependency_graph_autosubmit_action",
    "dependabot_alerts",
    "dependabot_security_updates",
    "dependabot_delegated_alert_dismissal",
    "code_scanning_default_setup",
    "code_scanning_delegated_alert_dismissal",
    "secret_scanning",
    "secret_scanning_push_protection",
    "secret_scanning_delegated_bypass",
    "secret_scanning_validity_checks",
    "secret_scanning_non_provider_patterns",
    "secret_scanning_generic_secrets",
    "secret_scanning_delegated_alert_dismissal",
    "secret_scanning_extended_metadata",
    "private_vulnerability_reporting",
]
CONFIGURATIONS_GH_ARGS = [
    "api",
    f"orgs/{ORG}/code-security/configurations",
    "--jq",
    f'[.[] | select(.target_type == "organization") | {{{", ".join(CONFIGURATION_FIELDS)}}}]',
]
DEFAULTS_GH_ARGS = [
    "api",
    f"orgs/{ORG}/code-security/configurations/defaults",
    "--jq",
    "[.[] | {name: .configuration.name, default_for_new_repos}]",
]


def attachment_gh_args(repository: str) -> list[str]:
    """A repository's configuration. GitHub answers 204 with no body when none is attached."""
    return [
        "api",
        f"repos/{ORG}/{repository}/code-security-configuration",
        "--jq",
        "{status, configuration: .configuration.name}",
    ]


def sbom_gh_args(repository: str) -> list[str]:
    return [
        "api",
        f"repos/{ORG}/{repository}/dependency-graph/sbom",
        "--jq",
        ".sbom.packages | length",
    ]


class NotFoundError(Exception):
    """GitHub answered 404."""


class UnreadableError(Exception):
    """Something couldn't be read, so its state is unknown: an error, never "off" or "on"."""


def dependency_graph(fetch: Fetch, repository: str) -> str:
    """ "on" when the repository's dependency graph can be read, "off" when GitHub says it doesn't
    exist (404). Any other failure is an error naming the repository: never read as either."""
    try:
        fetch(sbom_gh_args(repository))
    except NotFoundError:
        return "off"
    except Exception as error:
        raise UnreadableError(
            f"code security repositories: couldn't read {repository!r}'s dependency graph ({error})"
        ) from error
    return "on"


def code_security(fetch: Fetch, oob_dir: Path) -> list[str]:
    """The configurations, the defaults, and each declared repository's attachment and graph."""
    declared = json.loads((oob_dir / CODE_SECURITY).read_text())
    found = differences(
        "code security configurations", "name", declared["configurations"],
        fetch(CONFIGURATIONS_GH_ARGS),
    )  # fmt: skip
    found += differences(
        "code security defaults", "name", declared["defaults"], fetch(DEFAULTS_GH_ARGS)
    )
    actual: list[Record] = []
    for repo in declared["repositories"]:
        name = repo["repository"]
        attached = fetch(attachment_gh_args(name)) or {}
        actual.append(
            {
                "repository": name,
                "configuration": attached.get("configuration"),
                "status": attached.get("status", "none"),
                "dependency_graph": dependency_graph(fetch, name),
            }
        )
    found += differences(
        "code security repositories", "repository", declared["repositories"], actual
    )
    return found


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
    """The JSON gh prints; None when GitHub sent no body (204). A 404 is NotFoundError, so a
    caller can tell "doesn't exist" from any other failure."""
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        if "(HTTP 404)" in result.stderr:
            raise NotFoundError(" ".join(args[:2]))
        raise subprocess.CalledProcessError(
            result.returncode, ["gh", *args], result.stdout, result.stderr
        )
    return json.loads(result.stdout) if result.stdout.strip() else None


def run(fetch: Fetch, oob_dir: Path, root: Path = ROOT) -> list[str]:
    found: list[str] = []
    for check in CHECKS:
        if check.derived is not None:
            declared = check.derived(root)
        else:
            declared = json.loads((oob_dir / check.declaration).read_text())
        found += differences(check.name, check.key, declared, fetch(check.gh_args))
    specs = fetch(SPECS_GH_ARGS)
    found += unlabelled_specs(specs, root)
    found += stale_descriptions(fetch, specs, oob_dir, root)
    found += code_security(fetch, oob_dir)
    return found


def main() -> int:
    try:
        found = run(gh, OOB, ROOT)
    except UnreadableError as error:
        print(f"oob: {error}. Nothing is known about it until it can be read; run again.")
        return 1
    for line in found:
        print(line)
    if found:
        print(f"oob: {len(found)} difference(s). Fix GitHub, or update the declaration in oob/.")
        return 1
    print(
        f"oob: no differences ({', '.join(c.name for c in CHECKS)}, "
        "troupe specs, troupe label descriptions, code security)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
