## Why

Two gaps in the merge gates, both in the delivered `scripts/quality_gates.py`:

- **Delivered files are left out by hand (#333).** Each receiving repository lists the files infrastructure delivers
  in its `[complexity] exclude` and its `[tool.coverage.run] omit`, and the lists go stale whenever a new file is
  delivered. On 2026-11-18 (troupe-run/troupe#444) troupe listed guard.py, guard_pytest.py and quality_gates.py; then
  the five `scripts/mutation_*.py` files arrived (626 statements, untested in troupe), troupe's `scripts` package
  measured 71.9% instead of 88.5%, and the gate failed until another pattern was written by hand. Infrastructure
  already says what it delivers, in each repository's `.github/guard-delivery.json`, and measures those files at
  their source.
- **Nothing keeps a file small enough to review (#271).** Claude's review reads every changed file whole, and a Read
  holds about 25,000 tokens (~22–41 KB); a file over 256 KB can't be read whole at all. Today 16 files in troupe, 16
  in infrastructure and 8 in website are over 40 KiB, and nothing stops one growing.

## What Changes

- The coverage and complexity gates read `.github/guard-delivery.json` and leave every delivered file out by
  themselves: coverage drops them from the report before mapping files to packages (so the "in no package" check
  never names one), and complexity doesn't measure them. A missing list means nothing is delivered (infrastructure
  itself); a malformed one fails the gate, never "nothing delivered".
- A new **size** gate, run by every check like complexity: a file the work adds or changes that is over
  `[size] block_above` bytes, and is new or larger than at the base, fails, naming the file, its size before and
  after, the limit and the fix. Over `[size] warn_above` it's noted, never failed. Delivered files, binary files and
  the config's `exclude` globs aren't measured. Files over the limit today are declared once, in `[size.allow]`, each
  with its own ceiling; an entry for a file now under the limit fails as stale, so the list only shrinks.
- `[size]` is optional for now, as `[coverage]` is: troupe's and website's current script refuses an unknown table,
  so they can declare it only after this script is delivered. A follow-up makes it required once both have it
  (design D7).
- `docs/development-workflow.md` lists the size gate and says delivered files are left out by the gates themselves.
- Infrastructure's own `quality-gates.toml` gains `[size]` with its exception list.
- `scripts/quality_gates.py` is split, so it isn't left at the limit it adds: the audit and weekly report move to a new
  delivered `scripts/quality_audit.py`, with the same command line (design D8).

The owner set the thresholds (warn above 32 KiB, block above 48 KiB) and the exception list's shape (each listed
file's ceiling at its size today plus 16 KiB) on 2026-11-19 (design D5–D6).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality-gates`: delivered files are left out of coverage and complexity by reading the delivered list; a new size
  gate with a declared exception list, declared in an optional `[size]` table.

## Impact

- `scripts/quality_gates.py` and the new `scripts/quality_audit.py` (both delivered to troupe and website), their
  tests `scripts/tests/test_guard_quality_gates.py` and `test_guard_quality_audit.py`, `tofu/guard_delivery.tf`,
  `scripts/check.py` (a `size` step), `quality-gates.toml`, `docs/development-workflow.md`.
- troupe and website: after delivery, each removes its hand-written delivered-file patterns, and needs `[size]` in its
  `quality-gates.toml` before the delivered script requires it (follow-up pull requests there, sequenced in design).
- The plan updates `scripts/quality_gates.py`, adds `scripts/quality_audit.py` and updates the delivered list in
  troupe and website.
