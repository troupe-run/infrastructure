"""Decide whether a pull request needs the guard's tests on every OS and Python, from its paths.

Usage (in .github/workflows/ci.yml's `changes` job; the changed paths on stdin, one per line):
    git diff --name-only --no-renames "$BASE...$HEAD" | python3 scripts/guard_tests_needed.py

Prints `guard=true` or `guard=false`, for $GITHUB_OUTPUT. Spec: ci-apply; run-checks-by-path
design D5.

The list below names what the guard's tests depend on, the opposite of plan_needed.py's list. A
path missing here costs only the other OSes on one pull request: whenever any of these changes, the
`check` job runs the full check, every guard test among it, on Linux, and main runs every leg
after the merge. A test fails if a file the guard delivers isn't covered. An empty list needs them.

Standard library only: the job runs it with the runner's python3, before anything is installed.
"""

import sys
from collections.abc import Iterable

# Directories (ending in /), file-name prefixes (ending in _) and files the guard's tests depend on.
DEPENDS_ON = (
    # The guard's files, delivered to every governed repository (tofu/guard_delivery.tf).
    "scripts/guard.py",
    "scripts/guard_pytest.py",
    ".githooks/",
    ".claude/settings.json",
    ".github/workflows/guard.yml",
    # Its tests, what they share, and what they run with.
    "scripts/tests/test_guard_",
    "scripts/tests/conftest.py",
    "scripts/check-paths.toml",
    "pyproject.toml",
    "uv.lock",
    # The matrix itself.
    ".github/workflows/ci.yml",
)


def depends_on(path: str) -> bool:
    return any(
        path.startswith(entry) if entry.endswith(("/", "_")) else path == entry
        for entry in DEPENDS_ON
    )


def guard_tests_needed(paths: Iterable[str]) -> bool:
    changed = [path.strip() for path in paths if path.strip()]
    return not changed or any(depends_on(path) for path in changed)


def main() -> int:
    print(f"guard={'true' if guard_tests_needed(sys.stdin) else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
