# Proposal

## Why

`guard_pytest` fails a test that reads a scope's file without the scope's tag. It finds reads through Python's `open`
audit event, counting every open while a test runs. Hypothesis also opens files on its own. Before a draw, if
`sys.modules` has grown since the last draw, it reads the source of every newly imported first-party module to collect
constants (`hypothesis/internal/conjecture/providers.py` → `hypothesis/internal/constants_ast.py`,
`constants_from_module`). The guard then charges those reads to whichever Hypothesis test drew first after the import.
That test never read the file, and the guard's message tells you to tag it with a scope it has nothing to do with (#114).

On troupe's `cache-vcs-state` branch (troupe-run/troupe#75), about one full `pytest -n 10` run in two fails this way:

```
guard: packages/troupe-artifacts-local/tests/test_local_artifact_store.py::test_any_bytes_round_trip_under_their_own_sha256
reads packages/troupe-vcs-files/src/troupe_vcs_files/__init__.py, which scripts/check-paths.toml puts in scope
`vcs_files`, so a change to it wouldn't run this test.
```

A stack logged from the audit hook shows that exact path. troupe's `main` has the same problem but doesn't show it,
because it depends on which tests share an xdist worker. Every repository whose suite uses Hypothesis can hit it.

It reproduces every time with two tests: a tagged test imports a module under scope `pkg`, then an untagged `@given`
test draws, and the guard fails the `@given` test for reading `pkg/mod.py` and `pkg/__init__.py`.

## What Changes

- **The guard ignores files that Hypothesis's constant collection opens.** If `hypothesis/internal/constants_ast.py`
  is on the Python stack when the `open` audit event fires, the read isn't recorded for any test. It's Hypothesis's
  read, and it happens whatever the test does. A file the test itself opens, even from inside a `@given` test, still
  counts. The guard stays standard-library only: it checks the frames' file names, and never imports Hypothesis.
- **A test reproduces the false report** in a throwaway project, as the guard's other tests do. It also checks that
  a `@given` test reading the same file itself still fails.
- **Delivered to troupe and website** in the usual way, once CI is green on all three OSes and you approve the plan.

Not changing: what counts as a read for every other caller, the messages, and the fact that reads in subprocesses
aren't seen.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: "Test tags cover what each test reads" gains a scenario. A read made by the test framework's
  own machinery, specifically Hypothesis collecting constants, doesn't count against the test.

## Impact

- `scripts/guard_pytest.py` (`_record`) and `scripts/tests/test_guard_pytest.py`.
- The delivered copies in troupe-run/troupe and troupe-run/website (an apply after merge).
- Unblocks troupe-run/troupe#75, whose commits run the check.
