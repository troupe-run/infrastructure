# Design

## Context

In mutmut's copy a package's test file is at `<package>/mutants/tests/<file>`, one directory deeper than
`<package>/tests/<file>`. So each `Path(__file__).parents[k]` inside the copy names the directory that
`parents[k - 1]` names outside it: `mutants/` stands for the package (mutmut and #337 copy its files there), the
package directory stands for `packages/`, and `packages/` stands for the checkout. #332's `link_checkout_entries`
covers the last of these only.

## Decisions

### D1. Link the level above, at each level

`link_checkout_entries` becomes: for each directory `A` from the package directory up to, not including, the
checkout, link every entry of `A`'s parent that `A` lacks into `A` (`A/<name> → ../<name>`), except `.git`. For
troupe's `packages/<pkg>/src` that's two levels:
- the package directory gets `packages/`'s entries: its sibling packages, and itself as `<pkg>/<pkg> → ../<pkg>`,
  as `packages/packages → .` already is;
- `packages/` gets the checkout's, as now.

Links go in `made` as they're made, so a failure partway still removes them all.

### D2. A package's copied files leave out links

#337 copies a package directory's other top-level entries into mutmut's copy (`also_copy`). The links D1 adds there
would be copied as whole sibling packages, so that listing skips symbolic links. A package's own entries are real
files and directories, so nothing it needs is lost.

## Risks / Trade-offs

- **A test that lists its package's directory** sees the sibling links while mutmut runs → none known in troupe; the
  links exist only in the throwaway checkout, during the run.

## Migration Plan

Merge and apply (troupe's `mutation_run.py`), then the troupe dry run held since #341.
