# Spec Delta

## ADDED Requirements

### Requirement: The workflow's token asks for the App's declared permissions
The token `dependabot-issues` mints for the App SHALL ask for exactly the repository permissions the App is declared
with, metadata aside, which every token has. `scripts/check.py` SHALL compare the token's permissions with the App's
declaration and fail on any difference, naming the permission. So a run can read and write all the App was given for
it, and nothing else.

#### Scenario: The token leaves out a declared permission
- **WHEN** the App is declared with Dependabot alerts read, and the workflow's token asks only for issues write and
  pull requests write
- **THEN** `scripts/check.py` fails, naming Dependabot alerts as declared for the App but not asked for

#### Scenario: The token asks for more than the App is declared with
- **WHEN** the workflow's token asks for a permission the App isn't declared with, such as contents read
- **THEN** `scripts/check.py` fails, naming that permission

#### Scenario: The App gains a declared permission
- **WHEN** a change adds a permission to the App's declaration without the workflow's token asking for it
- **THEN** `scripts/check.py` fails on that change, naming the permission

#### Scenario: A run reads website's alerts
- **WHEN** website has an open Dependabot pull request and a `dependabot-issues` run on `main` reads its open
  Dependabot alerts with the App's token
- **THEN** the read succeeds, and the run handles website as it does troupe and infrastructure
