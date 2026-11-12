# Design

## Context

See proposal.md, Why. In `scripts/guard_pytest.py`, `_RECORDING` is one stack of open read windows. Collectors
(`pytest_make_collect_report`), fixtures (`pytest_fixture_setup`) and tests (`pytest_runtest_protocol`) each push a
window, and `_record`, the `open` audit hook, adds every in-repository path to **every** window on the stack. A
collector's window is saved in `_COLLECTED` under its node id, and `_reads(item)` unions the windows of every node in
`item.listchain()`, the test's own window, and its fixtures' windows.

Joining every open window is right for fixtures and tests: a fixture set up during a test is part of that test. For
collectors it's right only when collect reports aren't nested, and in a full run or a run given paths they aren't.
`Session.collect` makes only the path-level collectors' reports, and modules are collected afterwards in `genitems`.
Given a node id (`file.py::test`), the `matchparts` loop in `Session.collect` (pytest 9.2.0, `_pytest/main.py`) has to
collect each directory and module on the way to the named test, and it does so through `_collect_one_node` while the
Session's own report is still being made. Each of those reports is then nested in the Session's window, and since
every test's chain includes the Session, every test gets every selected module's imports, `.pyc` reads and writes, and
conftests.

xdist doesn't change this: each worker collects the same selection the same way, so the nesting is the same in every
worker, and in one process.

The troupe session for troupe-run/troupe#365 wrote a patch of this shape (design D6 of troupe's
`theatre-template-and-guard-xdist` change) and a draft pytester test. The patch passes that draft test and troupe's
`test_guard_pytest_workers.py`. This change brings both here, where `guard_pytest.py` is written.

## Goals / Non-Goals

**Goals:**
- A read during collection is charged to the collector being collected, and so to the tests under it, whichever way
  the tests were selected and with or without xdist.
- Every read a test is charged with today in a full run or a run given paths is still charged to it.
- The guard stays standard-library only, and its hook stays cheap.

**Non-Goals:**
- Changing what a fixture's or a test's window records, or the tag rule itself.
- Detecting that a read during collection "belongs" to some module by its path (a `.py` beside a `.pyc`, say). The
  guard records who was being collected when the file was opened, not what the file is.
- Reads in subprocesses, which stay unseen.

## Decisions

### D1: A collection read joins only the innermost open collector window

Collector windows move off `_RECORDING` onto their own stack, `_COLLECTING`. `pytest_make_collect_report` pushes a
set there and pops it by identity, as `_window` does now, and stores it in `_COLLECTED` as before. `_record` returns
early only when both stacks are empty. Otherwise it adds the path to every window on `_RECORDING` (fixtures and tests,
unchanged) and to `_COLLECTING[-1]` only.

In a full run, or one given paths, a collector's report is never made inside another's, so `_COLLECTING` holds at
most one window and the result is the same as now. In a node-id run, the Session's window keeps only what the Session
itself opened (the root `conftest.py`, say), and each directory and module keeps its own reads, which reach exactly
the tests under it through `listchain()`.

*Alternatives:*
- **Keep one stack and subtract.** After a nested report closes, remove its reads from the windows around it. That
  gives the same result with more bookkeeping, and a file the outer collector also opened itself would be removed
  from it wrongly.
- **Special-case the Session.** Don't record into the Session's window while another collector is open, or ignore the
  Session in `_reads`. Today only the Session nests other reports, but that's a fact about pytest's current
  `Session.collect`, not a rule. "Innermost only" states the rule the guard means, and holds for any collector that
  ever nests another (a plugin's custom collector, or a future pytest).
- **Attribute by path.** Charge a `.py` or `.pyc` read to the module it belongs to. That needs knowledge of import
  machinery, misses data files read at import, and is the guessing the guard avoids.

### D2: `_reads` and `_COLLECTED` don't change

What a test is charged with is still the union over its chain. Only what each collector's window holds changes. This
keeps the change to `_record` and one hook, which keeps the delivered diff small and the existing tests' meaning
intact.

### D3: Tests in this repository, built from troupe's draft

The tests go in `scripts/tests/test_guard_pytest.py`, using its `project()` helper and `run_pytest`, as every other
guard test does (a throwaway project holding this repository's `guard.py` and `guard_pytest.py`, run in a
subprocess). The project gets scopes `alpha` and `beta`, each with `paths` and `tests`, a `conftest.py` with a fixture
reading `beta/data.txt` under `beta/tests/`, and the `docs` scope the helper already declares. They cover the three
scenarios in the delta spec, each run serially and with `-n 2` through the existing `PARALLEL` parameters.

The clean-selection and module-level tests fail on the unchanged guard (the false report). They're committed first,
marked `xfail(strict=True, reason="#298")`, with the failure quoted, then the fix removes the marks. The untagged-read
test passes on the unchanged guard too, since the read is real; it pins that the fix doesn't hide real reads. The
existing module-level and parametrize tests (`test_a_read_at_import_counts_for_every_test_in_the_module`,
`test_a_read_while_collecting_parameters_counts_for_each_generated_test`) pin the full-run behaviour that mustn't
change.

## Risks / Trade-offs

- [A read the outer collector really caused, made while an inner report is open] → It's charged to the inner
  collector only. In pytest's own collection the outer collector is only walking towards the inner one, so the read
  is the inner one's. A plugin collector that opens a file for itself while nesting another's report would lose that
  read from its other children. None of the governed repositories has one.
- [pytest changes how it collects node ids] → The rule doesn't depend on which collectors nest, so it holds. If
  pytest stopped nesting, "innermost only" and "every open one" would agree again.
- [An in-process pytest run inside a test, such as `pytester.inline_run`] → Its collection reads join the inner
  run's collector and the outer test's window, as now. No change.

## Migration Plan

The delivery is the usual one: after the merge, the owner approves the `apply` job, which writes
`scripts/guard_pytest.py` to troupe and website. troupe PR #385 then adds troupe's own test and closes
troupe-run/troupe#365. To roll back, revert the commit here and deliver again.
