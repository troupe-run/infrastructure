# Proposal: npm-audit-fixed-versions

## Why

The dependency-audit gate (#324) should block an advisory only when "a newer version fixes" it (spec: quality-gates).
For `package-lock.json`, `scripts/quality_gates.py` trusted `npm audit`'s `fixAvailable` instead, and npm sets that
whenever any change to the tree clears the advisory, a semver-major downgrade of a dependent included. On 2026-11-18
picomatch GHSA-fc5q-39xc-vjpf (high, `<= 4.0.7`, no patched version) reached website's lock, and npm offered
"downgrade astro 7.4.7 to 5.3.0" as its fix, so website's adoption pull request (troupe-run/website#134) would fail
the gate on an advisory nobody can fix (#330).

## What Changes

- For `package-lock.json`, the audit reads npm's root advisories (the GitHub advisories in each vulnerability's
  `via`), once each, and judges each by its patched versions in OSV, as the `uv.lock` path does with pip-audit's fixed
  versions. npm's `fixAvailable` is no longer read.
- Severity stays npm's (GitHub's advisory severity); an unknown one still blocks. OSV unreachable still fails the gate.
- The weekly report lists the same root advisories, each once, instead of every package that depends on one.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality-gates`: "A changed lock file can't bring in a fixable high-severity advisory" says what counts as a fix:
  a patched version of the vulnerable package, never a change to another one.

## Impact

- `scripts/quality_gates.py` and `scripts/tests/test_guard_quality_gates.py`, with npm audit and OSV output captured
  from website's lock on 2026-11-18 as fixtures. A delivered file, so the plan delivers it to troupe and website.
