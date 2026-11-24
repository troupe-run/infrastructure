# Design

## Context

`scripts/mutation_run.py`'s `mutmut_config` writes each unit's `setup.cfg`. The unit's `tests` does three jobs there:

- it's mutmut's test selection (`pytest_add_cli_args_test_selection`);
- for the root package (`troupe`, whose working directory is the checkout), it's linked under `src` and listed in
  `do_not_mutate`;
- for a plugin package, it's left out of `also_copy`, since mutmut copies a package's `tests/` itself.

troupe#510 split each package's tests into `tests/unit/` and `tests/integration/`. The helpers both kinds import
(`*_shared.py`, the stand-ins, `gitrepo.py`) stay in `tests/`, on troupe's pytest `pythonpath`. Both mutation workflows
go through `mutmut_config`: the scheduled `mutation.yml`, and `mutation-pr.yml` through `mutation_run.py`.

## Goals / Non-Goals

**Goals:**

- Both runs use only the unit tests.
- The helpers stay importable and are never mutated.
- A missing or wrong selection is refused, not defaulted.
- The kept state resets once, visibly.

**Non-Goals:**

- Stryker's repositories. They already name only their unit tests' directory (`Repository.tests`).
- Lowering troupe's baselines. That's troupe's own pull request, if wanted, after the first judged run.

## Decisions

### D1: A separate `select` field, not a narrower `tests`

Setting `tests` to `packages/troupe/tests/unit` would narrow all three of its jobs. The root unit's helpers in `tests/`
would then fall outside `do_not_mutate` and be mutated. A plugin package's helpers might also go uncopied.

So `tests` keeps its meaning (what goes beside the source, unmutated), and a new `select` names the directory under it
that mutmut runs. Only the test selection changes: `<tests>/<select>`, written the same way `tests` is now, from
mutmut's working directory.

*Alternative:* a marker (`-m unit`). troupe's `kinds_pytest` gives each test its kind from its directory, so the
directory is the source of truth. A marker would also depend on a plugin loading in mutmut's copy.

### D2: `select` is required for every mutmut unit

The owner's practice is that mutation runs only unit tests. A default of "every test" would let a new unit quietly run
integration tests. So a mutmut unit without `select` is refused, naming the unit.

A malformed value is also refused (the "malformed input is an error" rule): one that is not text, is empty, is
absolute, or contains `..`. A `deselect` must sit under `<tests>/<select>`, since one outside it could never match.

### D3: The state's fit check includes `select`

`mutation_state.save` records `source` and `tests` in the manifest, and `restore` discards a unit's state when they
differ from the settings ("moved"). This change adds `select` to both. A manifest saved before this change has no
`select`, so it doesn't fit, and the first run discards every troupe unit's state once. That run says so and fails
visibly (exit 3).

That's the honest outcome. Results killed by an integration test would otherwise be carried as killed.

### D4: Reseed by dry runs, then re-enable the schedule

The schedule is disabled. Re-enabling it first would have the nightly run judge modules on a partial fill.

The order is therefore:

1. dry-run seeding dispatches, one after another, until every module is finished;
2. the owner runs `gh workflow enable`.

The runbook in `docs/development-workflow.md` says this.

## Risks / Trade-offs

- **[Scores fall where only integration tests cover code]** → expected and honest (#394). The module's issue names
  the survivors. A baseline is lowered by a troupe pull request where that's intended.
- **[A unit test needs a file that's only beside integration tests]** → `tests` still copies or links the whole
  directory (D1), so nothing a unit test reads goes missing.
- **[A package without a `tests/unit/`]** → every troupe package has one since #510. If one ever didn't, mutmut would
  find no tests and stop, and the run would name the unit.
