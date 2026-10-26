"""Drift checks for what OpenTofu can't manage (design D6; see oob/README.md).

Usage: uv run scripts/oob.py [--ci]

Compares each declaration in oob/ with GitHub, read with whatever login `gh` has (the owner's,
or CI's read-only App token), prints every difference and every check it couldn't read, and exits
1 if there are any. It only reads: no call writes to GitHub. --ci, used by tofu.yml's oob job,
runs the same checks and adds error annotations and the run summary.
"""

import base64
import dataclasses
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
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
    # GitHub answers null for a field this reader isn't allowed to see, so a declared value read
    # back as null is unreadable, not a difference. Only where GitHub hides fields that way: null is
    # a real value elsewhere, such as a project's empty shortDescription (run-oob-check-daily D3).
    null_is_unreadable: bool = False


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
        # Only an org owner sees whether 2FA is required.
        null_is_unreadable=True,
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


# troupe's specs, each of which names its capability labels in a Capability: line, the first
# non-blank line of its Purpose (spec: labels; spec-capability-label-check design D1, D2; troupe#170
# design D2). The check is one way, unlike CHECKS: a label no spec names isn't reported, since a
# label can come before its spec.
SPECS_GH_ARGS = [
    "api",
    f"repos/{ORG}/troupe/contents/openspec/specs",
    "--jq",
    '[.[] | select(.type == "dir") | .name]',
]
TROUPE_LABELS = "tofu/labels/troupe.json"
CAPABILITY_SHAPE = "Capability: `cap:<name>`, `cap:<name>`"
CAPABILITY_LINE = re.compile(r"Capability: (`[^`\s]+`(?:, `[^`\s]+`)*)")


def spec_md_gh_args(spec: str) -> list[str]:
    return [
        "api",
        f"repos/{ORG}/troupe/contents/openspec/specs/{spec}/spec.md",
        "--jq",
        "{content}",
    ]


def spec_documents(fetch: Fetch) -> dict[str, str]:
    """Each troupe spec's spec.md, read once for both troupe checks (design D1). A spec that
    can't be read makes the whole check unreadable, naming the spec: never "no label"."""
    documents: dict[str, str] = {}
    for spec in fetch(SPECS_GH_ARGS):
        try:
            content = fetch(spec_md_gh_args(spec))["content"]
        except Exception as error:
            raise UnreadableError(
                f"troupe specs: couldn't read {spec!r}'s spec.md ({reason(error)})"
            ) from error
        documents[spec] = base64.b64decode(content).decode()
    return documents


def purpose_lines(spec_md: str) -> list[str]:
    """The lines of a spec's `## Purpose` section; [] when there is none."""
    lines: list[str] = []
    inside = False
    for line in spec_md.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = line.strip() == "## Purpose"
        elif inside:
            lines.append(line)
    return lines


def capability_line(spec_md: str) -> str | None:
    """The Purpose's first non-blank line when it's meant as the Capability: line, else None.
    Any spelling of capability or capabilities, in any case, is meant as the line, so a misspelt
    one is malformed rather than "no label" (design D2)."""
    first = next((line.strip() for line in purpose_lines(spec_md) if line.strip()), "")
    return first if first.lower().startswith("capabilit") else None


class MalformedCapabilityLineError(Exception):
    """A Capability: line that isn't in the agreed shape: never read as naming no label, or as
    naming the labels it seems to (design D2)."""


def capability_labels(spec_md: str) -> list[str]:
    """The labels a spec names in its Capability: line; [] when it has none."""
    line = capability_line(spec_md)
    if line is None:
        return []
    match = CAPABILITY_LINE.fullmatch(line)
    labels = [label.strip("`") for label in match.group(1).split(", ")] if match else []
    if not labels or len(set(labels)) != len(labels):
        raise MalformedCapabilityLineError(line)
    return labels


def spec_labels(documents: dict[str, str], root: Path) -> list[str]:
    """Each troupe spec that names no label, has a malformed Capability: line, or names a label
    that isn't declared."""
    declared = {label["name"] for label in json.loads((root / TROUPE_LABELS).read_text())}
    found: list[str] = []
    for spec in sorted(documents):
        try:
            labels = capability_labels(documents[spec])
        except MalformedCapabilityLineError as error:
            found.append(
                f"troupe specs: {spec!r} Capability: line is malformed: {str(error)!r}; "
                f"write it as {CAPABILITY_SHAPE}"
            )
            continue
        if not labels:
            found.append(
                f"troupe specs: {spec!r} names no capability label; add a Capability: line as "
                "the first line of its Purpose in troupe-run/troupe"
            )
        found += [
            f"troupe specs: {spec!r} names {label!r}, which isn't declared; add it to "
            f"{TROUPE_LABELS} by pull request, or correct the spec in troupe-run/troupe"
            for label in labels
            if label not in declared
        ]
    return found


# The Purpose of each troupe spec, without its Capability: line, verbatim with its whitespace
# collapsed. The descriptions of the labels a spec names are written from it, so a Purpose troupe
# later rewrites shows up (spec: labels; spec-capability-label-check design D3).
PURPOSES = "troupe-spec-purposes.json"


def purpose(spec_md: str) -> str:
    """The text of a spec's `## Purpose` section without its Capability: line, whitespace
    collapsed; "" when there is none."""
    lines = purpose_lines(spec_md)
    if capability_line(spec_md) is not None:
        del lines[next(i for i, line in enumerate(lines) if line.strip())]
    return " ".join(" ".join(lines).split())


def stale_descriptions(documents: dict[str, str], oob_dir: Path) -> list[str]:
    """Each troupe spec whose Purpose isn't the one recorded for it, naming the labels it names,
    whose descriptions were written from it; and each record with no spec."""
    recorded: dict[str, str] = json.loads((oob_dir / PURPOSES).read_text())
    record = f"oob/{PURPOSES}"
    found: list[str] = []
    for spec in sorted(documents):
        try:
            labels = capability_labels(documents[spec])
        except MalformedCapabilityLineError:
            labels = []  # spec_labels reports the line
        named = ", ".join(repr(label) for label in labels) or "the labels it names"
        if spec not in recorded:
            found.append(
                f"troupe labels: {spec!r} spec's Purpose isn't recorded; check the descriptions "
                f"of {named} against it and record it in {record}"
            )
        elif purpose(documents[spec]) != " ".join(recorded[spec].split()):
            found.append(
                f"troupe labels: {spec!r} spec's Purpose has changed; review the descriptions of "
                f"{named} in {TROUPE_LABELS} and update {record}"
            )
    for spec in sorted(recorded.keys() - documents.keys()):
        found.append(
            f"troupe labels: {spec!r} has a recorded Purpose but troupe has no {spec} spec; "
            f"remove it from {record}"
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


# The release milestones, which OpenTofu manages only as declared: a milestone made by hand on a
# listed repository never shows in a plan (spec: milestones; release-milestones design D5). One way,
# like the spec labels: a declared milestone that's missing or different is the plan's business.
# A milestone's interim title counts as declared beside its title, so neither is reported while
# titles move between milestones over two applies (milestone-interim-titles design D4).
MILESTONES = "tofu/milestones.json"


def milestones_gh_args(repository: str) -> list[str]:
    return [
        "api",
        f"repos/{ORG}/{repository}/milestones?state=all&per_page=100",
        "--jq",
        "[.[] | .title]",
    ]


def undeclared_milestones(fetch: Fetch, root: Path) -> list[str]:
    """Each milestone, open or closed, on a listed repository whose title isn't declared, as a
    title or an interim title."""
    declared = json.loads((root / MILESTONES).read_text())
    titles = {milestone["title"] for milestone in declared["milestones"]}
    titles |= {m["interim_title"] for m in declared["milestones"] if "interim_title" in m}
    found: list[str] = []
    for repository in declared["repositories"]:
        try:
            actual: list[str] = fetch(milestones_gh_args(repository))
        except Exception as error:
            raise UnreadableError(
                f"milestones: couldn't read {repository!r}'s milestones ({error})"
            ) from error
        found += [
            f"milestones: {repository}: {title!r} is on GitHub but not declared; "
            f"declare it in {MILESTONES}"
            for title in sorted(set(actual) - titles)
        ]
    return found


# The troupe roadmap board's Capability field holds troupe's capabilities a second time, so its
# options are checked both ways against the declared cap: labels (spec: labels;
# capability-label-standard-change design D4). OpenTofu can't manage a Projects v2 field, and
# changing its options is the owner's, in the field's settings.
BOARD = "troupe roadmap"
BOARD_FIELD = "Capability"
BOARD_GH_ARGS = [
    "api",
    "graphql",
    "-f",
    f'query={{organization(login:"{ORG}"){{projectV2(number:1){{field(name:"{BOARD_FIELD}")'
    "{__typename ... on ProjectV2SingleSelectField{options{name}}}}}}",
    "--jq",
    ".data.organization.projectV2.field",
]
# What gh prints when the board has no field of that name: a GraphQL NOT_FOUND, so gh exits 1.
NO_SUCH_FIELD = "Could not resolve to a Unions::ProjectV2FieldConfiguration"


def board_capabilities(fetch: Fetch, root: Path) -> list[str]:
    """Each declared cap: label with no option on the board, and each option with no label."""
    try:
        field = fetch(BOARD_GH_ARGS)
    except subprocess.CalledProcessError as error:
        if NO_SUCH_FIELD not in str(error.stderr):
            raise
        return [
            f"board capabilities: the {BOARD} board has no {BOARD_FIELD!r} field; the owner adds "
            "it as a single select whose options are the cap: labels' names"
        ]
    if field.get("__typename") != "ProjectV2SingleSelectField":
        return [
            f"board capabilities: the {BOARD} board's {BOARD_FIELD!r} field is a "
            f"{field.get('__typename')}, not a single select"
        ]
    labels = json.loads((root / TROUPE_LABELS).read_text())
    declared = {label["name"].removeprefix("cap:") for label in labels}
    options = {option["name"] for option in field["options"]}
    found = [
        f"board capabilities: cap:{name} has no {name!r} option in the {BOARD} board's "
        f"{BOARD_FIELD} field; the owner adds it in the field's settings"
        for name in sorted(declared - options)
    ]
    found += [
        f"board capabilities: the {BOARD} board's {BOARD_FIELD} field has a {name!r} option, "
        f"but no cap:{name} is declared in {TROUPE_LABELS}; the owner removes it in the field's "
        "settings, or the label is declared"
        for name in sorted(options - declared)
    ]
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


def hidden_fields(check: Check, declared: list[Record], actual: list[Record]) -> None:
    """Raise UnreadableError for a declared value read back as null (Check.null_is_unreadable)."""
    want = {item[check.key]: item for item in declared}
    for item in actual:
        for field, value in sorted(item.items()):
            wanted = want.get(item.get(check.key), {}).get(field)
            if value is None and wanted is not None:
                raise UnreadableError(
                    f"{check.name}: {item.get(check.key)!r} {field} came back null, so this token "
                    "can't see it"
                )


def reason(error: BaseException) -> str:
    """What went wrong with a read, in gh's words where it gave some."""
    if isinstance(error, subprocess.CalledProcessError):
        lines = [line for line in str(error.stderr or "").splitlines() if line.strip()]
        return lines[-1].strip() if lines else f"gh exited {error.returncode}"
    return str(error) or type(error).__name__


@dataclass
class Report:
    """What a run found: differences, checks that couldn't be read, and what it ran."""

    differences: list[str] = dataclasses.field(default_factory=list)
    unreadable: list[str] = dataclasses.field(default_factory=list)
    ran: list[str] = dataclasses.field(default_factory=list)

    def attempt(self, name: str, body: Callable[[], list[str]]) -> bool:
        """Run one check. A failure to read is recorded against it, never a difference or "no
        difference", and the other checks still run (run-oob-check-daily D3)."""
        try:
            found = body()
        except UnreadableError as error:
            self.unreadable.append(str(error))
            return False
        except Exception as error:  # any failed read is unreadable, and named
            self.unreadable.append(f"{name}: couldn't read it ({reason(error)})")
            return False
        self.differences += found
        self.ran.append(name)
        return True


def check_declaration(check: Check, fetch: Fetch, oob_dir: Path, root: Path) -> list[str]:
    if check.derived is not None:
        declared = check.derived(root)
    else:
        declared = json.loads((oob_dir / check.declaration).read_text())
    actual = fetch(check.gh_args)
    if check.null_is_unreadable:
        hidden_fields(check, declared, actual)
    return differences(check.name, check.key, declared, actual)


def run(fetch: Fetch, oob_dir: Path, root: Path = ROOT) -> Report:
    report = Report()
    for check in CHECKS:
        report.attempt(check.name, partial(check_declaration, check, fetch, oob_dir, root))
    documents: dict[str, str] = {}

    def labels() -> list[str]:
        documents.update(spec_documents(fetch))
        return spec_labels(documents, root)

    if report.attempt("troupe specs", labels):
        report.attempt("troupe label descriptions", lambda: stale_descriptions(documents, oob_dir))
    else:
        report.unreadable.append(
            "troupe label descriptions: not checked, since troupe's specs couldn't be read"
        )
    report.attempt("code security", lambda: code_security(fetch, oob_dir))
    report.attempt("milestones", lambda: undeclared_milestones(fetch, root))
    report.attempt("board capabilities", lambda: board_capabilities(fetch, root))
    return report


def annotation(kind: str, message: str) -> str:
    """A GitHub Actions error annotation, escaped so the message can't end or split it."""
    escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return f"::error title=oob {kind}::{escaped}"


def plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def summary(report: Report) -> str:
    """The run summary in Markdown: what was found, and what was checked."""
    found = []
    if report.differences:
        found.append(plural(len(report.differences), "difference", "differences"))
    if report.unreadable:
        found.append(
            plural(len(report.unreadable), "check couldn't be read", "checks couldn't be read")
        )
    lines = ["### Out-of-band drift check", ""]
    lines.append(f"**{', '.join(found)}.**" if found else "**No differences.**")
    if report.differences:
        lines += ["", "Fix GitHub, or update the declaration in `oob/`:", ""]
        lines += [f"- {line}" for line in report.differences]
    if report.unreadable:
        lines += ["", "Couldn't be read, so nothing is known about them:", ""]
        lines += [f"- {line}" for line in report.unreadable]
    lines += ["", f"Checked: {', '.join(report.ran)}."]
    return "\n".join(lines) + "\n"


USAGE = "usage: uv run scripts/oob.py [--ci]"


def main(argv: list[str]) -> int:
    if argv not in ([], ["--ci"]):
        print(
            f"{USAGE}\n  --ci  for tofu.yml's oob job: the same checks, with error annotations and "
            f"the run summary. Got: {' '.join(argv)!r}",
            file=sys.stderr,
        )
        return 2
    ci = argv == ["--ci"]
    report = run(gh, OOB, ROOT)
    if ci:
        for line in report.differences:
            print(annotation("difference", line))
        for error in report.unreadable:
            print(annotation("unreadable", error))
        if path := os.environ.get("GITHUB_STEP_SUMMARY"):
            with Path(path).open("a", encoding="utf-8") as out:
                out.write(summary(report))
    for line in report.differences:
        print(line)
    for error in report.unreadable:
        print(f"oob: {error}. Nothing is known about it until it can be read; run again.")
    if report.differences:
        print(
            f"oob: {len(report.differences)} difference(s). Fix GitHub, or update the declaration "
            "in oob/."
        )
    if report.differences or report.unreadable:
        return 1
    print(f"oob: no differences ({', '.join(report.ran)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
