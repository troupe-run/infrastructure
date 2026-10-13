# Spec Delta

## MODIFIED Requirements

### Requirement: Delivered files are changed only at their source
In a governed repository that receives delivered files, GitHub SHALL refuse a change to a delivered file unless the
infrastructure App makes it (spec: rulesets). Before that, a commit that changes a delivered file SHALL be refused,
an agent's edit to one SHALL be refused, and the guard's GitHub check SHALL fail on a commit that changes one unless
its author is the App. The guard's checks catch an honest mistake early, and they aren't the enforcement: a commit's
author is self-declared. The fix SHALL be to change the file in this repository.

#### Scenario: Committing a change to a delivered file
- **WHEN** a contributor in `troupe` commits a change to `.githooks/pre-commit`
- **THEN** the commit is refused, naming the rule and saying to change the file in `troupe-run/infrastructure`

#### Scenario: An agent edits a delivered file
- **WHEN** an agent in a Claude Code session in `troupe` edits `scripts/guard.py`
- **THEN** the edit is refused, naming the rule and the source repository

#### Scenario: A pushed change to a delivered file
- **WHEN** a branch is pushed to `troupe` carrying a commit, not made by the App, that changes a delivered file
- **THEN** GitHub refuses the push, naming the ruleset and the path

#### Scenario: A forged delivery author doesn't get through
- **WHEN** someone other than the App pushes a commit to `troupe` that changes a delivered file, with the App's bot
  email written in as the commit's author
- **THEN** GitHub refuses the push, although the guard's own check would have passed the commit

#### Scenario: A delivery passes the check
- **WHEN** the App's delivery commit is pushed to `troupe`'s `main`
- **THEN** GitHub accepts it, and the guard's GitHub check passes

#### Scenario: The source repository edits its own files
- **WHEN** a contributor in this repository commits a change to `scripts/guard.py` on a change's branch
- **THEN** this rule does not apply
