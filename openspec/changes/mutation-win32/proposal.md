# Proposal

## Why

#368 (#367) delivered a `scripts/mutation_children.py` that fails troupe's Windows CI (#369). `cap_address_space()`
imports the POSIX-only `resource` module with no platform guard. On win32, mypy's stubs for `resource` have no
`getrlimit`, `setrlimit`, `RLIMIT_AS` or `RLIM_INFINITY`, so all four of troupe's Windows check legs fail at
`mypy --strict` (troupe run 44675393265). It blocks troupe's 0.2.0 bundle pin (troupe#483) and every troupe pull
request.

Infrastructure didn't catch it. Its Windows CI legs run only the guard's tests, and its mypy runs only on Linux and
macOS, where `resource` is complete. Nothing type-checks the files it delivers as Windows sees them.

## What Changes

- **The plugin narrows before importing `resource`:** `if sys.platform == "win32":` returns first, since mutation
  runs are Linux-only and the cap can't apply there. mypy narrows on `sys.platform`; a pytest `skipif` doesn't.
- **The check type-checks delivered files for Windows.** A new gate runs `mypy --platform win32` over the Python
  files delivered to other repositories, read from `tofu/guard_delivery.tf` (its `guard_files` and
  `mutation_report_files`, through `scripts/tofu_text.py`). It runs on every OS the check runs on, so a POSIX-only
  use is refused here before a delivery can reach troupe or website.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `guard-delivery`: the delivered Python files type-check for Windows before they're delivered.

## Impact

- `scripts/mutation_children.py` (delivered to troupe), `scripts/check.py`, and their tests.
- `docs/development-workflow.md`, the check's gates.
- The plan updates troupe's delivered `scripts/mutation_children.py`, nothing else.
