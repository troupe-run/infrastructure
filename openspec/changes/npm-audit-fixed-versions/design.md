# Design: npm-audit-fixed-versions

## Context

`npm audit --json` lists every vulnerable package, the advisories' own packages and every package that depends on one.
Each entry's `via` holds either names of other entries or the advisory objects themselves (`source`, `name`,
`severity`, `url` ending in the GitHub advisory id, `range`). Its `fixAvailable` is npm's plan to clear it: `true`,
or `{name, version, isSemVerMajor}` naming whatever package npm would move, in either direction. On website's lock of
2026-11-18 it named `astro@5.3.0`, a downgrade from 7.4.7, for an advisory with no patched version.

## Decisions

### D1. Root advisories, judged by OSV

The audit collects the advisory objects from every `via`, once each by `source`. For each, it reads the GitHub
advisory id from `url` and asks OSV for its record, as it already does for severity on the `uv.lock` path, and takes
the lowest `fixed` event among the record's npm ranges for that package as the fixed version. No `fixed` event means
no fix. A record OSV doesn't have (404) means no known fix, and the advisory still appears in the report.

*Rejected:* reading `fixAvailable` and ignoring semver-major or downgrade plans. npm doesn't say which direction a
plan moves, and a semver-minor move of a dependent can still be a downgrade. The advisory's own data is what the spec
means by "a newer version".

### D2. Severity and version

Severity stays the one npm reports for the advisory (GitHub's). An advisory's `version` is its vulnerable range, as
npm gives it, since the lock may pin several versions of one package.

### D3. The report

The weekly issue lists root advisories, so picomatch appears once instead of with each of the 20 packages that depend
on it.
