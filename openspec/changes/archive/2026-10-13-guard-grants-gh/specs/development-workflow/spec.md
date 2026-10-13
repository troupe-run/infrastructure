## ADDED Requirements

### Requirement: The guard grants the gh commands it allows
In a Claude Code session, the guard SHALL grant a `gh` read or an everyday issue, pull request, comment or project-item
write that no rule refuses, so that it runs without a prompt or auto mode's check. Only a guard identical to the one on
`origin/main` SHALL grant. Anything else SHALL get no grant, and is refused or left to Claude Code as before. A
person's own `deny` and `ask` rules SHALL still apply to a granted command.

#### Scenario: A routine write is granted
- **WHEN** an agent runs `gh pr ready 74` or `gh issue edit 29 --type Feature`, with the guard matching `origin/main`
- **THEN** the command runs without a prompt, in auto mode as well

#### Scenario: A command the guard allows but doesn't grant
- **WHEN** an agent runs `gh pr merge 32 --rebase`, `gh workflow run tofu.yml`, `gh api repos/troupe-run/troupe`, or a
  write to `troupe-run/infra-probe-20261013`
- **THEN** the guard doesn't grant it, and Claude Code decides as it does today

#### Scenario: A guard edited on a branch
- **WHEN** the `scripts/guard.py` running differs from the one on `origin/main`, or `origin/main` can't be read
- **THEN** the guard grants nothing, and still refuses what its rules refuse

#### Scenario: The person's own rules
- **WHEN** a person's settings hold a `deny` or `ask` rule that matches a command the guard grants
- **THEN** that rule applies: the command is refused or prompts

### Requirement: A grant is only for a plain gh command
The guard SHALL grant only a Bash command that is exactly one `gh` command, with no substitution, variable,
redirection, glob, chaining or environment prefix, and whose every file read is inside the repository or the system
temp directory.

#### Scenario: A gh command combined with anything else
- **WHEN** an agent runs `gh pr ready 74 && rm -rf build`, `gh issue comment 1 --body "$(cat notes)"`, or
  `GH_TOKEN=x gh pr ready 74`
- **THEN** the guard doesn't grant it

#### Scenario: A body read from outside the repository
- **WHEN** an agent runs `gh issue comment 1 --body-file ~/.ssh/id_ed25519`
- **THEN** the guard doesn't grant it, so it can't skip auto mode's check for sending local data away

#### Scenario: Through PowerShell
- **WHEN** an agent runs `gh pr ready 74` through the PowerShell tool
- **THEN** the guard doesn't grant it
