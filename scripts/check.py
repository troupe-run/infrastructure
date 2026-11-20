"""Run every quality gate, in order, stopping at the first failure.

Usage: uv run scripts/check.py [--scope NAME ...] [--base REV]

The tests run in TEST_WORKERS parallel worker processes (pytest-xdist), or one per CPU where
there are fewer (check-time design D1).

With --scope, every gate still runs, but the tests narrow to those marked with any of the scopes
declared in scripts/check-paths.toml. The guard passes scopes when a commit stages only paths
they cover (spec: development-workflow; commit-check-paths design D8).

Every run measures the complexity of the functions the work adds or edits, and the size of the
files it adds or changes, since --base, or since where it left origin/main (spec: quality-gates).
Coverage and the dependency audit run only on CI's coverage leg, which sets QUALITY_GATES_LEG=true;
never locally (owner, 2026-11-18).

The same script runs locally and in CI, so the two can't diverge (design D8). It needs no
secret: `tofu validate` reads neither state nor variable values. Every repo the org builds in
has a scripts/check.py; the development-workflow guard runs it before every commit.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = Path(sys.executable).parent
sys.path.insert(0, str(ROOT / "scripts"))
import guard  # noqa: E402  (scripts/guard.py reads the declaration and activates the hooks)
import quality_gates  # noqa: E402  (whether this repository declares [coverage])
import tofu_text  # noqa: E402  (the files this repository delivers, from tofu/guard_delivery.tf)

TEST_WORKERS = 4
"""How many processes the tests run in, at most. Small, not `auto`: the machine is shared, and the
gain past 4 is small (check-time design D1). Only this gate uses it: a plain `pytest` runs in
one process."""


def worker_count() -> int:
    """TEST_WORKERS, or one per CPU where the machine has fewer."""
    return min(TEST_WORKERS, os.cpu_count() or 1)


def tool(name: str, path: str | None = str(BIN)) -> str:
    """Find a tool: console scripts in this interpreter's environment, or tofu on the PATH."""
    found = shutil.which(name, path=path)
    if found is None:
        where = BIN if path else "the PATH"
        fix = "run `uv sync`" if path else "install OpenTofu (brew install opentofu)"
        sys.exit(f"check: {name} is not installed in {where}. Fix: {fix}.")
    return found


TFLINT_RULES = ROOT / ".tflint.hcl"


def tflint_version() -> str:
    """The tflint version CI installs, from the `# tflint v<version>` line in .tflint.hcl."""
    found = re.search(r"^# tflint (v\d+\.\d+\.\d+)$", TFLINT_RULES.read_text(), re.MULTILINE)
    if found is None:
        sys.exit(f"check: {TFLINT_RULES.name} has no `# tflint v<version>` line. Fix: add it.")
    return found.group(1)


def tflint_gate(env: Mapping[str, str]) -> list[tuple[str, list[str]]]:
    """The tflint gate, or none on a machine without tflint outside GitHub Actions (design D2).

    CI installs tflint, so a missing one there is a broken workflow and fails. Locally the owner
    chose CI first (2026-11-17): absent is the one state that skips, and it says so. An installed
    tflint that fails fails the check like any gate.
    """
    found = shutil.which("tflint", path=env.get("PATH"))
    if found is None:
        if env.get("GITHUB_ACTIONS") == "true":
            sys.exit(
                "check: tflint is not on the PATH. Fix: install it in the workflow "
                "(terraform-linters/setup-tflint, the version in .tflint.hcl)."
            )
        install = f"go install github.com/terraform-linters/tflint@{tflint_version()}"
        print(
            f"check: tflint isn't installed, so the tflint gate is skipped here; CI runs it. "
            f"To run it locally: {install}",
            flush=True,
        )
        return []
    return [("tflint", [found, "--chdir=tofu", "--recursive", f"--config={TFLINT_RULES}"])]


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


LEG = "QUALITY_GATES_LEG"
"""Set to `true` by CI's coverage leg, under GitHub Actions only, to run coverage and the audit
(quality-gates design D5)."""

QUALITY_GATES = str(ROOT / "scripts" / "quality_gates.py")


def on_leg(env: Mapping[str, str]) -> bool:
    """Whether this run is CI's coverage leg. Set anywhere else, or to anything but `true`, the
    variable stops the check: it is not a way to measure coverage locally."""
    value = env.get(LEG, "")
    if value == "":
        return False
    if value != "true":
        sys.exit(
            f"check: {LEG}={value!r} isn't valid. Fix: unset it; CI's coverage leg sets it to true."
        )
    if env.get("GITHUB_ACTIONS") != "true":
        sys.exit(
            f"check: {LEG} is set, but this isn't GitHub Actions. Coverage and the dependency "
            f"audit run on CI's coverage leg only (quality-gates design D5). Fix: unset {LEG}."
        )
    return True


def coverage_report() -> Path:
    """Where the coverage leg's report goes: the runner's temporary directory."""
    return (
        Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir())) / "quality-gates-coverage.json"
    )


def delivered_python(guard_delivery_tf: str) -> list[str]:
    """The Python files this repository delivers to others (tofu/guard_delivery.tf), which the
    check type-checks as Windows sees them: troupe's and website's checks run on Windows, and this
    repository's Windows legs run only the guard's tests (#369, mutation-win32 design D2)."""
    try:
        listed = {
            *tofu_text.guard_files(guard_delivery_tf),
            *tofu_text.mutation_report_files(guard_delivery_tf),
        }
    except tofu_text.ShapeError as error:
        sys.exit(f"check: {error}")
    files = sorted(path for path in listed if path.endswith(".py"))
    if not files:
        sys.exit(
            f"check: {tofu_text.GUARD_DELIVERY_TF} names no delivered Python files to type-check"
        )
    return files


def gates(
    scopes: tuple[str, ...] = (),
    base: str | None = None,
    leg: bool = False,
    env: Mapping[str, str] = os.environ,
    coverage: bool | None = None,
) -> list[tuple[str, list[str]]]:
    """The check's steps. `coverage` says whether this repository measures coverage; left unset,
    its quality-gates.toml says, by declaring [coverage] or not (#332). Only CI's leg asks."""
    if coverage is None and leg:
        try:
            coverage = quality_gates.read_config(ROOT).coverage is not None
        except quality_gates.GateError as error:
            sys.exit(f"check: {error}")
    tofu = tool("tofu", path=None)
    pytest = [tool("pytest"), "-n", str(worker_count())]
    if scopes:
        pytest += ["-m", guard.marker_expression(scopes)]
    measure = leg and coverage and not scopes
    if measure:
        pytest += ["--cov", "--cov-report=", f"--cov-report=json:{coverage_report()}"]
    on_base = ["--base", base] if base else []
    steps = [
        ("ruff lint", [tool("ruff"), "check", "."]),
        ("ruff format", [tool("ruff"), "format", "--check", "."]),
        ("mypy --strict", [tool("mypy")]),
        (
            "mypy win32 (delivered)",
            [
                tool("mypy"),
                "--platform",
                "win32",
                *delivered_python(tofu_text.GUARD_DELIVERY_TF.read_text(encoding="utf-8")),
            ],
        ),
        ("complexity", [sys.executable, QUALITY_GATES, "complexity", *on_base]),
        ("size", [sys.executable, QUALITY_GATES, "size", *on_base]),
        ("tests", pytest),
    ]
    if measure:
        report = str(coverage_report())
        steps.append(
            ("coverage", [sys.executable, QUALITY_GATES, "coverage", "--coveragepy", report])
        )
    elif leg:
        why = ": the tests were scoped" if coverage else " in this repository (no [coverage])"
        note = f"print('coverage not measured{why}')"
        steps.append(("coverage", [sys.executable, "-c", note]))
    if leg:
        steps.append(("audit", [sys.executable, QUALITY_GATES, "audit", *on_base]))
    return [
        *steps,
        ("tofu fmt", [tofu, "fmt", "-check", "-recursive", "tofu"]),
        ("tofu init", [tofu, "-chdir=tofu", "init", "-backend=false", "-input=false"]),
        ("tofu validate", [tofu, "-chdir=tofu", "validate"]),
        *tflint_gate(env),
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
    parser.add_argument(
        "--base", help="the commit the complexity, size and audit gates compare with"
    )
    args = parser.parse_args(argv)
    names = args.scope
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
    return run_gates(gates(scopes, args.base, on_leg(os.environ)), ROOT, scopes)


if __name__ == "__main__":
    sys.exit(main())
