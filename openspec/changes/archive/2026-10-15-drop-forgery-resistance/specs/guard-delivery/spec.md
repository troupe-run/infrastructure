## MODIFIED Requirements

### Requirement: Delivered files are changed only at their source
In a governed repository that receives delivered files, a commit or an agent's edit that changes a delivered file
SHALL be refused, and the guard's GitHub check SHALL fail on such a commit unless its author is the App. That check
catches mistakes, not forgery. A change that gets past these, by any route, is drift: a plan of `main` SHALL show it
within a day, and an apply SHALL restore the file. The fix SHALL be to change the file in this repository.

#### Scenario: Committing a change to a delivered file
- **WHEN** a contributor in `troupe` commits a change to `.githooks/pre-commit`
- **THEN** the commit is refused, naming the rule and saying to change the file in `troupe-run/infrastructure`

#### Scenario: An agent edits a delivered file
- **WHEN** an agent in a Claude Code session in `troupe` edits `scripts/guard.py`
- **THEN** the edit is refused, naming the rule and the source repository

#### Scenario: A pushed change to a delivered file
- **WHEN** a branch is pushed to `troupe` carrying a commit, not made by the App, that changes a delivered file
- **THEN** the guard's GitHub check for that push fails and names the commit and the file

#### Scenario: A forged delivery author shows within a day
- **WHEN** a commit that changes a delivered file, with the App's bot email written in as its author, reaches
  `troupe`'s `main`
- **THEN** a plan of `main` within a day shows the file returning to its source content, and applying it restores
  that content

#### Scenario: A delivery passes the check
- **WHEN** the App's delivery commit is pushed to `troupe`'s `main`
- **THEN** the guard's GitHub check passes

#### Scenario: The source repository edits its own files
- **WHEN** a contributor in this repository commits a change to `scripts/guard.py` on a change's branch
- **THEN** this rule does not apply
