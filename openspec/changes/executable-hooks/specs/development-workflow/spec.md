# Spec Delta

## ADDED Requirements

### Requirement: A hook git would skip is reported
Wherever the git hooks are made active, starting a Claude Code session or running the repository's check, each hook
that git would skip because it isn't executable SHALL be named, saying that git skips it and where it is fixed. It
SHALL NOT refuse anything, and it SHALL NOT change the file's mode. Where git runs a hook whatever its mode, nothing
SHALL be reported.

#### Scenario: A session starts where a hook isn't executable
- **WHEN** a Claude Code session starts in a clone of `website` whose `.githooks/pre-push` isn't executable
- **THEN** the session is told that git skips `.githooks/pre-push` because it isn't executable, and that the fix is
  made in `troupe-run/infrastructure`, not in the clone

#### Scenario: The check runs where a hook isn't executable
- **WHEN** a contributor runs the repository's check in that clone
- **THEN** the check names each hook git skips, still runs its gates, and its result is decided by those gates alone

#### Scenario: Every hook is executable
- **WHEN** a session starts, or the check runs, in a clone whose hooks are all executable
- **THEN** nothing about hook modes is reported

#### Scenario: A platform where git ignores the mode
- **WHEN** the check runs on Windows
- **THEN** nothing about hook modes is reported
