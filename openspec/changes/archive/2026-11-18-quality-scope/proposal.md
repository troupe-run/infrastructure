# Proposal

## Why

The first weekly mutation run's dry run (run 44221282773, 2026-11-18) crashed on troupe and website. The owner then
decided (#332): coverage and mutation testing go together, and they apply only to the repositories infrastructure
names for them in one place, troupe for now. They add little for website (mostly content and Astro pages, which
Playwright tests) or infrastructure (mostly OpenTofu; its Python tests largely run in subprocesses mutmut can't see, and
it's the most expensive run, about 19,000 mutants). Naming them centrally keeps the choice in one place when
repositories are split or added.

## What Changes

- **One list.** `scripts/mutation.json`'s `repositories` names the repositories that get coverage and mutation testing,
  today `troupe` only. The weekly run's jobs, the pull request report's delivery and which repositories keep a
  `[coverage]` table all follow it.
- **The weekly run** mutates only the listed repositories: its jobs come from the list, not a fixed matrix, and a
  dispatch can name one of them.
- **The pull request report** (`mutation-pr.yml` and its scripts) is delivered only to the listed repositories that
  receive the guard's files. website's copies are removed, so the plan deletes them there.
- **Coverage is optional in `quality-gates.toml`.** `[coverage]` becomes an optional table in
  `scripts/quality_gates.py` (agreed with #322's worker, who owns the rest of that file). A repository without it
  measures nothing on its coverage leg and says so. Infrastructure drops its own `[coverage]` table: its CI leg keeps
  running the dependency audit, which it shares.
- **troupe's mutation runs work.** The dry run found that troupe's tests resolve the repository's root one directory too
  high inside mutmut's copy (`packages/troupe/mutants/tests/...`). The run links the checkout's top-level entries into
  `packages/`, keeps troupe's own pytest `addopts` (its `protocol_guard`, `hypothesis_profiles` and `gitrepo` plugins)
  minus `--strict-markers` and the guard's tag plugin, and deselects three tests that can't run under mutmut's hooks,
  each with its reason.
- **Docs and specs** say where the list lives and how to add a repository.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mutation-testing`: the weekly run and the pull request report cover only the listed repositories, and one place
  names them.
- `quality-gates`: `[coverage]` is optional; a repository without it measures no coverage.
- `ci-apply`: infrastructure's CI leg runs the dependency audit, not coverage.

## Impact

- `scripts/mutation.json`, `scripts/mutation_run.py`, `scripts/quality_gates.py`, `scripts/check.py`,
  `quality-gates.toml`, `.github/workflows/mutation.yml`, `tofu/guard_delivery.tf`, `scripts/dependabot_config.py`
  (the delivered workflows differ per repository), and their tests.
- The plan: website loses its delivered `mutation-pr.yml` and the mutation scripts (deleted by the App's commits), and
  its `guard-delivery.json` and `dependabot.yml` change; troupe's delivered files change with the new scripts.
- website#134 drops its coverage part (#322's worker); troupe#444 is unaffected.
- After the merge and apply: a dry run of troupe alone.
