"""Values read from the OpenTofu configuration's text, for the scripts and tests that need them
without running tofu (which would need the encrypted state).

Each reader fails, naming what it expected, when the text no longer has the shape it reads, so a
refactor of the .tf file breaks loudly rather than reading nothing.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GUARD_DELIVERY_TF = REPO / "tofu" / "guard_delivery.tf"
REPOSITORIES_TF = REPO / "tofu" / "repositories.tf"


class ShapeError(Exception):
    """The configuration's text isn't the shape a reader expects."""


def guard_files(text: str) -> list[str]:
    """The `guard_files` list in guard_delivery.tf's text, in its order."""
    found = re.search(r"guard_files = toset\(\[(.*?)\]\)", text, re.S)
    if found is None:
        raise ShapeError("guard_files isn't toset([...]) in tofu/guard_delivery.tf")
    files = re.findall(r'"([^"]+)"', found.group(1))
    if not files:
        raise ShapeError("guard_files lists no file in tofu/guard_delivery.tf")
    return files


def module_names(repositories_tf: str) -> dict[str, str]:
    """Each module "repo_*" block's key mapped to its repository's name."""
    return dict(
        re.findall(r'module "(repo_\w+)" \{.*?\n  name\s+= "([^"]+)"', repositories_tf, re.S)
    )


def guard_targets(guard_delivery_tf: str, repositories_tf: str) -> list[str]:
    """The repositories in `guard_targets`, by name, sorted."""
    found = re.search(r"guard_targets = toset\(\[(.*?)\]\)", guard_delivery_tf, re.S)
    if found is None:
        raise ShapeError("guard_targets isn't toset([...]) in tofu/guard_delivery.tf")
    names = module_names(repositories_tf)
    keys = re.findall(r"module\.(repo_\w+)\.name", found.group(1))
    if not keys:
        raise ShapeError("guard_targets names no module.repo_*.name in tofu/guard_delivery.tf")
    unknown = [key for key in keys if key not in names]
    if unknown:
        raise ShapeError(f"guard_targets names {unknown}, not in tofu/repositories.tf")
    return sorted(names[key] for key in keys)
