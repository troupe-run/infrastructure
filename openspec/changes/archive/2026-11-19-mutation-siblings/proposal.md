# Proposal

## Why

troupe#457's per-PR mutation report, its first run against `troupe-store-text`, failed in mutmut's stats run before
any mutant (#343). `packages/troupe-store-text/tests/test_processes.py` finds troupe's test helpers for a child process
at `Path(__file__).resolve().parents[2] / "troupe" / "tests"`. In mutmut's copy, `parents[2]` is the package directory,
not `packages/`, so the child imports nothing, prints nothing, and the test fails. #332 linked the checkout's
top-level entries into `packages/`, for tests that count up to the root. A test that counts up only to `packages/`
lands one level lower, in the package directory, which lacks its siblings. The weekly run's `troupe-store-text` unit
fails the same way, and a failed unit stops troupe's run, so this blocks the next troupe dry run and #339.

## What Changes

- **Links at every level.** During a package's run, each directory from the package's own up to (not including) the
  checkout gets links to the entries of the directory above it. Today that's only `packages/` (the checkout's
  entries). Now the package directory also gets its siblings (`troupe`, `troupe-plugin-sdk`, …). All are removed
  afterwards, failed runs too.
- **A package's copied files skip links.** The package's own entries copied into mutmut's copy (#337) leave out
  symbolic links, so the sibling links aren't copied as whole packages.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: a package's tests find their sibling packages inside the copy.

## Impact

- `scripts/mutation_run.py` (delivered) and its tests. The plan updates troupe's delivered `mutation_run.py`.
- After the apply: the troupe dry run held since #341.
