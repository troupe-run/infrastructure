"""Run every quality gate, in order, stopping at the first failure.

Usage: uv run scripts/check.py [--scope NAME ...]

With --scope, every gate still runs, but the tests narrow to those marked with any of the scopes
declared in scripts/check-paths.toml. The guard passes scopes when a commit stages only paths
they cover (spec: development-workflow; commit-check-paths design D8).

The same script runs locally and in CI, so the two can't diverge (design D8). It needs no
secret: `tofu validate` reads neither state nor variable values. Every repo the org builds in
has a scripts/check.py; the development-workflow guard runs it before every commit.
"""

import argparse
import shutil
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = Path(sys.executable).parent
sys.path.insert(0, str(ROOT / "scripts"))
import guard  # noqa: E402  (scripts/guard.py reads the declaration and activates the hooks)


def tool(name: str, path: str | None = str(BIN)) -> str:
    """Find a tool: console scripts in this interpreter's environment, or tofu on the PATH."""
    found = shutil.which(name, path=path)
    if found is None:
        where = BIN if path else "the PATH"
        fix = "run `uv sync`" if path else "install OpenTofu (brew install opentofu)"
        sys.exit(f"check: {name} is not installed in {where}. Fix: {fix}.")
    return found


def requested_scopes(names: Sequence[str], declaration: guard.CheckPaths | None) -> tuple[str, ...]:
    """The scopes to run, sorted and once each; exits naming any the declaration doesn't list."""
    declared = {name for name, _ in declaration.scopes} if declaration is not None else set()
    unknown = sorted(set(names) - declared)
    if unknown:
        listed = ", ".join(f"`{name}`" for name in unknown)
        sys.exit(
            f"check: scope {listed} isn't declared in scripts/check-paths.toml. Fix: declare it "
            "there, or run the check without --scope."
        )
    return tuple(sorted(set(names)))


def gates(scopes: tuple[str, ...] = ()) -> list[tuple[str, list[str]]]:
    tofu = tool("tofu", path=None)
    pytest = [tool("pytest")]
    if scopes:
        pytest += ["-m", guard.marker_expression(scopes)]
    return [
        ("ruff lint", [tool("ruff"), "check", "."]),
        ("ruff format", [tool("ruff"), "format", "--check", "."]),
        ("mypy --strict", [tool("mypy")]),
        ("tests", pytest),
        ("tofu fmt", [tofu, "fmt", "-check", "-recursive", "tofu"]),
        ("tofu init", [tofu, "-chdir=tofu", "init", "-backend=false", "-input=false"]),
        ("tofu validate", [tofu, "-chdir=tofu", "validate"]),
    ]


def activate_git_hooks(root: Path) -> str | None:
    """Turn the repository's git hooks on by default (spec: development-workflow).

    Git never runs hooks from a fresh clone, so the project's own tooling turns them on. The
    logic lives in guard.py, next to the hooks it activates.
    """
    if not (root / ".git").exists():
        return None  # not a git checkout (for example, an unpacked source archive)
    return guard.activate_hooks(root)


NO_TESTS_RAN = 5
"""pytest's exit code when it selected no tests, as `-m` does for a scope no test is tagged with."""


def run_gates(steps: list[tuple[str, list[str]]], cwd: Path, scopes: tuple[str, ...] = ()) -> int:
    for label, command in steps:
        print(f"==> {label}", flush=True)
        started = time.monotonic()
        result = subprocess.run(command, cwd=cwd, check=False)
        elapsed = time.monotonic() - started
        if scopes and label == "tests" and result.returncode == NO_TESTS_RAN:
            # Safe: guard_pytest fails any test that reads a scope's paths untagged, so no tagged
            # tests means no test reads them (commit-check-paths design D8).
            tags = " or ".join(f"`{name}`" for name in scopes)
            print(f"    no test is tagged {tags}, so there was nothing to test", flush=True)
            continue
        if result.returncode != 0:
            code = result.returncode
            print(f"check: {label} failed (exit {code}) after {elapsed:.1f}s", flush=True)
            return code
        print(f"    {label} passed in {elapsed:.1f}s", flush=True)
    print("check: all gates passed", flush=True)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--scope", action="append", default=[], help="a declared scope")
    names = parser.parse_args(argv).scope
    scopes: tuple[str, ...] = ()
    if names:
        text = guard.read_working_tree(ROOT)(guard.CHECK_PATHS)
        try:
            declaration = None if text is None else guard.check_paths(text)
        except guard.CheckPathsError as error:
            sys.exit(f"check: {error.decision().text()}")
        scopes = requested_scopes(names, declaration)
    activated = activate_git_hooks(ROOT)
    if activated is not None:
        print(f"check: {activated}", flush=True)
    return run_gates(gates(scopes), ROOT, scopes)


if __name__ == "__main__":
    sys.exit(main())
