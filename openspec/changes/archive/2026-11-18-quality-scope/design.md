# Design

## Context

See proposal.md for why. What's there now (2026-11-18, after #322/#328 and #325/#327 merged):

- `scripts/mutation.json` names three repositories, each with its tool and what it mutates. `mutation.yml`'s matrix is
  fixed at troupe, infrastructure and website. `tofu/guard_delivery.tf` delivers `mutation-pr.yml` and its six
  scripts to every guard target (troupe and website), with the guard's files.
- `scripts/quality_gates.py` (#322's, delivered) requires `[coverage]` in `quality-gates.toml`. Infrastructure's
  `check.py` runs coverage and the dependency audit on CI's leg (`QUALITY_GATES_LEG=true`).
- The dry run (44221282773): troupe's job stopped in mutmut's stats pass, and website's Stryker initial test run
  failed. A local reproduction of troupe's package `troupe` found:
  - its tests count directories up from their own file to find the repository's root; inside mutmut's copy
    (`packages/troupe/mutants/tests`) that lands one level too high, on `packages/`;
  - clearing pytest's `addopts`, which infrastructure needed, drops troupe's own plugins (`protocol_guard`,
    `hypothesis_profiles`, `gitrepo`), so 15 tests failed for want of them;
  - with both fixed, 3 tests still fail under mutmut's hooks.

## Goals / Non-Goals

**Goals:** one place says which repositories get coverage and mutation testing; nothing else decides it; troupe's
weekly run and pull request report work.

**Non-Goals:** website's coverage (website#134, #322's worker); troupe's coverage leg (troupe#444, unaffected); the
dependency audit, which stays everywhere.

## Decisions

### D1. The list is `scripts/mutation.json`'s `repositories`

It already names each repository with what to mutate, and every mutation job and the delivery read it. Cut to troupe,
it is the list. Coverage follows it too: a repository named there may declare `[coverage]`, and the rest don't. A
separate list for coverage would be two lists for one decision. For a repository other than infrastructure, the
coverage table is that repository's own, so the list can't enforce it from here. Infrastructure's own table is held to
the list by a test (it's not listed, so it has none). website drops its table with website#134.

*Alternative:* a new `scripts/test-quality.json` naming repositories only. Rejected for now: it would split one
repository's mutation settings from the decision to mutate it. If coverage ever needs repositories that mutation
doesn't, that's the time to split.

### D2. The weekly run's jobs come from the list

A first job, `targets`, reads the list and hands its names to the `mutate` matrix as JSON. The dispatch input
`repository` becomes a string: `all`, or one listed name; anything else fails `targets`, naming what's listed. The
issues job reads the same list, as it already does.

### D3. Only listed repositories receive the pull request report

`tofu/guard_delivery.tf` reads `scripts/mutation.json` and delivers the report's seven files (`mutation-pr.yml`,
`mutation.json` and the five scripts) only to guard targets the list names. Each target's `guard-delivery.json` lists
what it receives, and `scripts/dependabot_config.py` leaves out the delivered workflows each repository has, so both
become per-repository. Removing website from the list deletes its copies through the App, as any delivered file is
removed. `quality_gates.py` is delivered everywhere still: complexity and the audit run everywhere.

infrastructure holds `mutation-pr.yml` as its source, so it runs here too. A first job, `listed`, reads
`scripts/mutation.json` at the merge and lets `mutate` run only when the list names the repository; otherwise it says
so, and the report mutates nothing and doesn't fail (from the review of #334).

### D4. `[coverage]` is optional (agreed with #322's worker)

`parse_config` reads `[coverage]` only when it's there; `Config.coverage` is `CoverageConfig | None`. The `coverage`
subcommand with none prints `coverage: not measured in this repository (no [coverage] in quality-gates.toml)` and
exits 0. Infrastructure's `check.py` adds pytest's `--cov` options only when the config has `[coverage]`, and its leg
still runs the audit. #322's worker owns the rest of `quality_gates.py`; this change touches `parse_config`,
`Config.coverage`, the `coverage` subcommand and their tests only.

### D5. troupe's mutation runs: links, its own pytest options, three deselections

In `mutation_run.py`, for a unit whose source is a package's `src` (mutmut runs in the package's directory):

- **Links.** Before mutmut runs, each top-level entry of the checkout that the package's parent directory lacks is
  linked into it (`packages/plugins → ../plugins`, and so on), with `packages/packages → .`, and all are removed
  afterwards. A test that counts one directory too many from inside the copy then still finds what it reads. Python's
  directory walks don't follow links, so `packages/packages` can't loop one. Verified locally: the
  `runner-anthropic/fixtures` and `packages/troupe/...` reads both resolve.
- **pytest's options.** Instead of clearing `addopts`, the run passes the repository's own `addopts` (read from its
  `pyproject.toml`) without `--strict-markers` and `-p guard_pytest`. The guard's tag plugin looks for
  `scripts/check-paths.toml` from the copy and can't find it, so it registers no scope markers, and strict markers then
  refuse every tagged test. Verified locally: troupe's package suite under mutmut's stats setting went from 15 failures
  to 3.
- **Deselected, with reasons**, in troupe's `troupe` unit:
  - `tests/test_cli_startup.py::test_importing_the_command_line_loads_none_of_the_heavy_modules`: mutmut's hooks
    import `email` and `importlib.metadata` into the test process;
  - `tests/test_config_schemas.py::test_the_models_are_what_the_schemas_generate`: it compares the generated models
    with the source, which in mutmut's copy is the mutated one;
  - `tests/test_package.py::test_the_built_wheel_carries_the_recorded_protocol_version_and_every_schema`: `uv build`
    can't build the package from mutmut's copy.
- troupe's other packages are mutated as before. If their runs show more such tests, they're deselected the same way.

### D7. The pull request report tests the merge, not the branch

`mutation-pr.yml`'s mutate job checked out `pull_request.head.sha`. On troupe#444, branched before the report's
delivery, `scripts/mutation.json` wasn't there, so the run failed before mutating anything. It now checks out
`github.sha`, the merge with the base, which is what the pull request would merge, and diffs it against the merge's
first parent, so only the pull request's changes are mutated, at their lines in the merge. `pull_request.base.sha` isn't
used for the range: if GitHub recomputed the merge on a newer base, the range from an older base would take in main's
own changes.

### D6. website's Stryker failure isn't fixed here

website is off the list, so its weekly job and report go. The Stryker code stays, tested against its fixture, for a
TypeScript repository the list names later.

## Risks / Trade-offs

- **troupe's other packages hit their own incompatibilities** → a unit whose tests fail under mutmut stops that
  repository's run, naming the unit (`mutation_run.py` fails rather than report empty modules). The troupe dry run after
  the merge runs every unit, and each failure found is fixed by a deselection with its reason before the first real
  run.
- **The links in `packages/` could surprise a test that lists `packages/`** → they exist only during the throwaway
  checkout's mutation run, and are removed afterwards; the local run of troupe's package suite with them in place
  passed apart from the three deselected.

## Migration Plan

1. Merge; the apply deletes website's report copies and updates troupe's.
2. Dispatch `mutation.yml` as a dry run for troupe alone; report each module's score and the runtime against the 4-hour
   budget; the owner confirms or moves the threshold.
