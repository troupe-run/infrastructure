"""Run every quality gate, in order, stopping at the first failure.

Usage: uv run scripts/check.py

The same script runs locally and in CI, so the two can't diverge (design D8). It needs no
secret: `tofu validate` reads neither state nor variable values. Every repo the org builds in
has a scripts/check.py; the development-workflow guard runs it before every commit.
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = Path(sys.executable).parent


def tool(name: str, path: str | None = str(BIN)) -> str:
    """Find a tool: console scripts in this interpreter's environment, or tofu on the PATH."""
    found = shutil.which(name, path=path)
    if found is None:
        where = BIN if path else "the PATH"
        fix = "run `uv sync`" if path else "install OpenTofu (brew install opentofu)"
        sys.exit(f"check: {name} is not installed in {where}. Fix: {fix}.")
    return found


def gates() -> list[tuple[str, list[str]]]:
    tofu = tool("tofu", path=None)
    return [
        ("ruff lint", [tool("ruff"), "check", "."]),
        ("ruff format", [tool("ruff"), "format", "--check", "."]),
        ("mypy --strict", [tool("mypy")]),
        ("tests", [tool("pytest")]),
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
    sys.path.insert(0, str(root / "scripts"))
    import guard

    return guard.activate_hooks(root)


def run_gates(steps: list[tuple[str, list[str]]], cwd: Path) -> int:
    for label, command in steps:
        print(f"==> {label}", flush=True)
        started = time.monotonic()
        result = subprocess.run(command, cwd=cwd, check=False)
        elapsed = time.monotonic() - started
        if result.returncode != 0:
            code = result.returncode
            print(f"check: {label} failed (exit {code}) after {elapsed:.1f}s", flush=True)
            return code
        print(f"    {label} passed in {elapsed:.1f}s", flush=True)
    print("check: all gates passed", flush=True)
    return 0


def main() -> int:
    activated = activate_git_hooks(ROOT)
    if activated is not None:
        print(f"check: {activated}", flush=True)
    return run_gates(gates(), ROOT)


if __name__ == "__main__":
    sys.exit(main())
