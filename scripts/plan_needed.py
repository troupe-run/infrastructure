"""Decide whether a pull request needs an OpenTofu plan, from the paths it changes.

Usage (in .github/workflows/tofu.yml's `changes` job; the changed paths on stdin, one per line):
    git diff --name-only "$BASE...$HEAD" | python3 scripts/plan_needed.py

Prints `plan=true` or `plan=false`, for $GITHUB_OUTPUT. Spec: ci-apply; design D2 of
required-checks.

The list below names what OpenTofu is known never to read, not what it reads: OpenTofu reads
tofu/, org-profile/ and every file the guard delivers, and a list of those would have to grow with
each new delivery. So a path nobody thought about plans, and a mistake costs one approval rather
than a pull request merged without its plan. An empty list plans too.

The Python tooling's `pyproject.toml` and `uv.lock` are on the list because the tofu workflow runs
every script with `uv run --no-project`, which reads neither, so they can't change what a plan or
an apply runs (skip-plan-python-tooling, design D1 and D3). The provider lockfile,
tofu/.terraform.lock.hcl, is read by OpenTofu and plans.

Standard library only: the job runs it with the runner's python3, before anything is installed.
"""

import sys
from collections.abc import Iterable

# Directories (ending in /) and files that OpenTofu never reads.
NEVER_READ = (
    "openspec/",
    "docs/",
    "oob/",
    "scripts/tests/",
    "README.md",
    "CLAUDE.md",
    # The Python tooling's dependencies, at the root only: no step of the tofu workflow runs in
    # the project's environment (a test in test_plan_needed.py checks it).
    "pyproject.toml",
    "uv.lock",
)


def never_read(path: str) -> bool:
    return any(
        path.startswith(entry) if entry.endswith("/") else path == entry for entry in NEVER_READ
    )


def plan_needed(paths: Iterable[str]) -> bool:
    changed = [path.strip() for path in paths if path.strip()]
    return not changed or not all(never_read(path) for path in changed)


def main() -> int:
    print(f"plan={'true' if plan_needed(sys.stdin) else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
