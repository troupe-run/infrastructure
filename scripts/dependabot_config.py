"""Generate each repository's .github/dependabot.yml into tofu/dependabot/, from the policy and
the declared ecosystems and labels. OpenTofu delivers the files (tofu/dependabot.tf).

Usage, after changing tofu/dependabot.json, tofu/labels/dependabot.json or the guard's delivered
workflows:
    uv run scripts/dependabot_config.py

Spec: dependency-updates; deliver-dependabot design D1 to D3. A test fails while a generated file
differs from what this writes, so the files can't drift from their sources.
"""

import json
import sys
from pathlib import Path
from typing import Any

import yaml

import tofu_text

REPO = tofu_text.REPO
POLICY = REPO / "tofu" / "dependabot.json"
LABELS = REPO / "tofu" / "labels" / "dependabot.json"
OUT = REPO / "tofu" / "dependabot"
COMMAND = "uv run scripts/dependabot_config.py"

HEADER = (
    "# Generated in troupe-run/infrastructure from tofu/dependabot.json and\n"
    "# tofu/labels/dependabot.json, and delivered by its App. Change it there: an edit here is\n"
    "# drift, and the next apply reverts it.\n"
)

WORKFLOWS = ".github/workflows/"


def undirected_ecosystems(policy: dict[str, Any], labels: dict[str, Any]) -> list[str]:
    """Each repository's ecosystem that the policy gives no directory."""
    return [
        f"{repo}: ecosystem {ecosystem!r} has no directory in tofu/dependabot.json"
        for repo, ecosystems in labels["repositories"].items()
        for ecosystem in ecosystems
        if ecosystem not in policy["directories"]
    ]


def unknown_releases(policy: dict[str, Any], labels: dict[str, Any]) -> list[str]:
    """Each repository or ecosystem in the policy's releases that isn't declared for Dependabot.
    The releases say whose runtime dependencies ship, so a security update to one releases a fix
    (security-updates-release design D4); they change no generated file."""
    problems = []
    for repo, ecosystems in policy.get("releases", {}).items():
        if repo not in labels["repositories"]:
            problems.append(
                f"{repo}: in tofu/dependabot.json's releases, but not a repository in "
                "tofu/labels/dependabot.json"
            )
            continue
        problems += [
            f"{repo}: ecosystem {ecosystem!r} in tofu/dependabot.json's releases isn't one of its "
            "Dependabot ecosystems in tofu/labels/dependabot.json"
            for ecosystem in ecosystems
            if ecosystem not in labels["repositories"][repo]
        ]
    return problems


def delivered_workflows(guard_files: list[str]) -> list[str]:
    """The workflows the guard delivers, sorted."""
    return sorted(path for path in guard_files if path.startswith(WORKFLOWS))


def entry(
    policy: dict[str, Any],
    labels: dict[str, Any],
    ecosystem: str,
    excluded: list[str],
) -> dict[str, Any]:
    cooldown = dict(policy["cooldown"])
    if ecosystem not in policy["semver_cooldown"]:
        cooldown = {"default-days": cooldown["default-days"]}
    update: dict[str, Any] = {
        "package-ecosystem": ecosystem,
        "directory": policy["directories"][ecosystem],
        "schedule": dict(policy["schedule"]),
        "cooldown": cooldown,
        "commit-message": dict(policy["commit-message"]),
        "labels": [labels["dependencies"]["name"], labels["ecosystems"][ecosystem]["name"]],
    }
    if ecosystem == "github-actions" and excluded:
        update["exclude-paths"] = excluded
    return update


def configs(
    policy: dict[str, Any],
    labels: dict[str, Any],
    guard_files: list[str],
    guard_targets: list[str],
) -> dict[str, dict[str, Any]]:
    """Each repository with ecosystems mapped to its configuration."""
    workflows = delivered_workflows(guard_files)
    return {
        repo: {
            "version": 2,
            "updates": [
                entry(policy, labels, ecosystem, workflows if repo in guard_targets else [])
                for ecosystem in ecosystems
            ],
        }
        for repo, ecosystems in labels["repositories"].items()
        if ecosystems
    }


class Dumper(yaml.SafeDumper):
    """Quotes every string holding a colon, so a YAML 1.1 reader can't take `00:00` for a
    base-60 number, as GitHub's examples quote `time`."""


def represent_str(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
    style = '"' if ":" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


Dumper.add_representer(str, represent_str)


def render(config: dict[str, Any]) -> str:
    body = yaml.dump(config, Dumper=Dumper, sort_keys=False, default_flow_style=False, width=100)
    return HEADER + body


def generated() -> dict[str, str]:
    """Each generated file's name in tofu/dependabot/ mapped to its content."""
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    problems = undirected_ecosystems(policy, labels) + unknown_releases(policy, labels)
    if problems:
        raise SystemExit("\n".join(problems))
    guard_delivery_tf = tofu_text.GUARD_DELIVERY_TF.read_text(encoding="utf-8")
    targets = tofu_text.guard_targets(
        guard_delivery_tf, tofu_text.REPOSITORIES_TF.read_text(encoding="utf-8")
    )
    files = tofu_text.guard_files(guard_delivery_tf)
    return {
        f"{repo}.yml": render(config)
        for repo, config in configs(policy, labels, files, targets).items()
    }


def stale(out: Path, files: dict[str, str]) -> list[str]:
    """Each generated file in `out` that's missing, differs, or is no longer generated."""
    present = {path.name for path in out.glob("*.yml")} if out.is_dir() else set()
    problems = [
        f"tofu/dependabot/{name} is out of date: run `{COMMAND}`"
        for name, content in sorted(files.items())
        if name not in present or (out / name).read_text(encoding="utf-8") != content
    ]
    problems += [
        f"tofu/dependabot/{name} is no longer generated: run `{COMMAND}`"
        for name in sorted(present - files.keys())
    ]
    return problems


def write(out: Path, files: dict[str, str]) -> None:
    out.mkdir(exist_ok=True)
    for path in out.glob("*.yml"):
        if path.name not in files:
            path.unlink()
    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")


def main() -> int:
    write(OUT, generated())
    return 0


if __name__ == "__main__":
    sys.exit(main())
