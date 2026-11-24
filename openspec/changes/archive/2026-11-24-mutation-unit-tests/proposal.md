# Proposal

## Why

Owner decision (2026-11-23): mutation testing runs only troupe's fast unit tests, never its integration tests (the full
stack: subprocesses, git theatres, stand-in servers). That's the owner's standing practice (#394).

The incremental run's seeding (#378) slowed to about 500 mutants per 4-hour run, about a minute of tests per mutant.
troupe#510 (troupe#507) has since split every troupe test into `packages/*/tests/unit/` and `tests/integration/`, with
the helpers both kinds import kept beside them in `tests/`. By #507's CI numbers, the unit tests are 11-22% of the summed
test time.

## What Changes

- Each mutmut unit in `scripts/mutation.json` gains a required `select`: the directory under its `tests` that mutation
  runs use. All eight troupe units select `unit`. mutmut's test selection becomes `<tests>/<select>`. `tests` keeps
  its meaning: it's what's linked or copied beside the source and never mutated, so the shared helpers in `tests/`
  stay importable and unmutated.
- The scheduled run (`mutation.yml`) and a pull request's report (`mutation-pr.yml`) both build mutmut's config in
  `scripts/mutation_run.py`, so both run only the unit tests.
- A missing or malformed `select` is refused, naming the unit: absent, absolute, leaving `tests` with `..`, or empty.
  So is a `deselect` outside the selection, which could never match.
- troupe's three deselects go. All three are integration tests (#395), so the selection no longer runs them. #395's
  test that held both their ids goes with them.
- The kept state records each unit's `select`. A changed selection discards that unit's state once, named in the
  summary as moved settings, and the run fails visibly, as moved sources or tests already do.
- The development workflow describes the unit-only selection and its effects. The seeding runbook covers the reseed
  after this change and re-enabling the schedule.

## Expected effects

- **Code covered only by integration tests shows as surviving, or as reached by no test.** That's the honest signal:
  no unit test checks that code. A module's score may fall below its baseline in troupe's `quality-gates.toml`. Where
  that's intended, its baseline is lowered by an ordinary troupe pull request. Otherwise the module's issue asks for
  unit tests.
- **The first run after the apply starts every troupe unit afresh.** It fails visibly once (exit 3, moved settings).
  The fill then needs far fewer runs than #378's.
- **Pull request reports get faster**, since a mutant runs only the unit tests that reach its function.

## Re-enabling the schedule and reseeding

The nightly schedule has been disabled since 2026-11-23 (`disabled_manually`). After the apply:

1. Seeding, by dry-run dispatches, one after another, each reporting what it carried and tested, until every module
   is finished:
   `gh workflow run mutation.yml -R troupe-run/infrastructure --ref main -f repository=troupe -f dry-run=true`.
   The first fails visibly (exit 3) for the reset, as expected.
2. The owner re-enables the schedule: `gh workflow enable mutation.yml -R troupe-run/infrastructure`.
3. The next nightly run (03:23 UTC) is the first not dry. It judges every finished module and raises at most 5 new
   issues.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: a mutation run uses only each unit's selected tests (ADDED requirement).

## Impact

- `scripts/mutation_settings.py`, `scripts/mutation_run.py`, `scripts/mutation_state.py` and `scripts/mutation.json`,
  all delivered to troupe, with their tests.
- `docs/development-workflow.md`.
- The plan updates troupe's delivered copies of the four scripts.
