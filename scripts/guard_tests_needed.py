"""Decide whether a pull request needs the guard's tests on every OS and Python, from its paths.

Usage (in .github/workflows/ci.yml's `changes` job; the changed paths on stdin, one per line):
    git diff --name-only --no-renames "$BASE...$HEAD" | python3 scripts/guard_tests_needed.py

Prints `guard=true` or `guard=false`, for $GITHUB_OUTPUT. Spec: ci-apply; run-checks-by-path
design D5.

And in the `guard tests` job, which stands in for the legs as the required check (design D6):
    python3 scripts/guard_tests_needed.py --result "$LEGS" "$CHANGES" "$GUARD"

where LEGS and CHANGES are the jobs' results and GUARD the `changes` job's answer. It exits 0 when
the legs passed, or were skipped because `changes` said they weren't needed, and 1 otherwise.

The list below names what the guard's tests depend on, the opposite of plan_needed.py's list. A
path missing here costs only the other OSes on one pull request: whenever any of these changes, the
`check` job runs the full check, every guard test among it, on Linux, and main runs every leg
after the merge. A test fails if a file the guard delivers isn't covered. An empty list needs them.

Standard library only: the job runs it with the runner's python3, before anything is installed.
"""

import sys
from collections.abc import Iterable, Sequence

# Directories (ending in /), file-name prefixes (ending in _) and files the guard's tests depend on.
DEPENDS_ON = (
    # The guard's files, delivered to every governed repository (tofu/guard_delivery.tf).
    "scripts/guard.py",
    "scripts/guard_pytest.py",
    ".githooks/",
    ".claude/settings.json",
    ".github/workflows/guard.yml",
    # Delivered with the guard, so a change to it runs every leg before it's delivered (spec:
    # pr-review), though the guard's tests don't read it.
    ".github/workflows/claude-review.yml",
    # The same, for the dispatcher that starts dependabot-issues (spec: dependency-updates).
    ".github/workflows/dependabot-dispatch.yml",
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


def result_problem(legs: str, changes: str, guard: str) -> str | None:
    """Why the legs' result fails the `guard tests` check, or None when it passes. Any result not
    named here fails, so a skip nobody asked for can't pass as one that was."""
    if legs == "success":
        return None
    if legs == "skipped" and changes == "success" and guard == "false":
        return None
    if legs == "skipped":
        return (
            f"the legs were skipped, but `changes` was {changes or 'not run'} and answered "
            f"guard={guard or '(nothing)'}, so nothing said they weren't needed"
        )
    return f"the legs' result is {legs or '(none)'}; each leg's own check names what went wrong"


def main(argv: Sequence[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if args[:1] == ["--result"]:
        if len(args) != 4:
            print("usage: guard_tests_needed.py --result LEGS CHANGES GUARD", file=sys.stderr)
            return 2
        problem = result_problem(*args[1:])
        if problem is not None:
            print(f"guard tests: {problem}.", file=sys.stderr)
            return 1
        print("guard tests: passed", flush=True)
        return 0
    print(f"guard={'true' if guard_tests_needed(sys.stdin) else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
