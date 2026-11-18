# Spec Delta

## ADDED Requirements

### Requirement: Only the vulnerable package's own patched release is a fix
For the audit gate and the weekly report, an advisory has a fix only when a patched release of the vulnerable package
itself exists. A change to another package, such as a downgrade of one that depends on it, SHALL NOT count as a fix,
whatever a tool proposes (#330). The patched release SHALL come from the advisory's record; only when that record
can't be had SHALL a tool's own fix count, and only when it names the vulnerable package itself.

#### Scenario: npm offers a downgrade of a dependent as the fix
- **WHEN** a pull request changes `package-lock.json`, a pinned package has a high-severity advisory with no patched
  version, and `npm audit` marks it fixable by downgrading a package that depends on it
- **THEN** the audit gate passes, and the advisory appears in the weekly report, once

#### Scenario: OSV has no record, and npm's fix names the vulnerable package
- **WHEN** a pull request changes `package-lock.json`, OSV has no record of a high-severity advisory (or npm's link
  for it isn't a GitHub advisory id), and `npm audit` fixes it with a newer release of the vulnerable package itself
- **THEN** the audit leg fails, naming that release as the fix (owner, 2026-11-18)

#### Scenario: OSV has no record, and npm's fix names a dependent
- **WHEN** OSV has no record of a high-severity advisory, and `npm audit`'s only fix moves a package that depends on
  the vulnerable one
- **THEN** the audit gate passes, and the advisory appears in the weekly report
