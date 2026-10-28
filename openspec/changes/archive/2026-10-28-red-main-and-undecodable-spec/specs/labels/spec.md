## ADDED Requirements

### Requirement: A troupe spec that can't be read is reported by name
When the drift check can't read a troupe spec's `spec.md`, because fetching it failed or its content couldn't be
decoded as base64 or as UTF-8, it SHALL report troupe's specs as unreadable, naming that spec and why. It SHALL NOT
read the spec as naming no label, and SHALL NOT check label descriptions against specs it couldn't read.

#### Scenario: A spec that can't be fetched
- **WHEN** GitHub answers an error for troupe's `cli` spec's `spec.md`
- **THEN** the drift check reports troupe's specs as unreadable, naming `cli` and GitHub's error, and reports no
  difference for them

#### Scenario: A spec whose content isn't base64
- **WHEN** GitHub's content for troupe's `cli` spec's `spec.md` isn't valid base64
- **THEN** the drift check reports troupe's specs as unreadable, naming `cli` and why

#### Scenario: A spec that isn't UTF-8
- **WHEN** troupe's `cli` spec's `spec.md` decodes from base64 to bytes that aren't UTF-8
- **THEN** the drift check reports troupe's specs as unreadable, naming `cli` and why
