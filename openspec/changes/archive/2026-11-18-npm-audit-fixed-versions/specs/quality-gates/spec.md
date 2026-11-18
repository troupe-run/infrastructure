##### Scenario: OSV has no record, and npm's fix names the vulnerable package
- **WHEN** a pull request changes `package-lock.json`, OSV has no record of a high-severity advisory (or npm's link
  for it isn't a GitHub advisory id), and `npm audit` fixes it with a newer release of the vulnerable package itself
- **THEN** the audit leg fails, naming that release as the fix (owner, 2026-11-18)

#### Scenario: OSV has no record, and npm's fix names a dependent
- **WHEN** OSV has no record of a high-severity advisory, and `npm audit`'s only fix moves a package that depends on
  the vulnerable one
- **THEN** the audit gate passes, and the advisory appears in the weekly report

 Spec Delta

## MODIFIED Requirements

### Requirement: A changed lock file can't bring in a fixable high-severity advisory
On its audit leg, when the work changes a lock file the config names, a repository's check SHALL audit every dependency
that lock file pins, and SHALL fail on any advisory whose severity is one the config blocks on and that a newer version
fixes. An advisory whose severity can't be found SHALL count as blocking. When the advisory databases can't be reached,
the check SHALL fail saying so, never pass. When no named lock file changed, the audit SHALL NOT run.

#### Scenario: A lock file with a fixable high advisory
- **WHEN** a pull request changes `uv.lock` and a pinned package has a high-severity advisory with a fixed version
- **THEN** the audit leg fails, naming the package, its version, the advisory, its severity and the fixed version

#### Scenario: An advisory with no fix
- **WHEN** a pull request changes a lock file whose only advisory is high-severity with no fixed version
- **THEN** the audit gate passes, and the advisory appears in the weekly report

#### Scenario: No lock file changed
- **WHEN** a pull request changes no lock file the config names
- **THEN** the audit gate passes without auditing, and says so

#### Scenario: The database can't be reached
- **WHEN** the audit leg runs on a changed lock file and the advisory database doesn't answer
- **THEN** the audit leg fails, saying which service it couldn't reach

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
