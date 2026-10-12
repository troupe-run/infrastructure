# Spec Delta

## MODIFIED Requirements

### Requirement: The tool acts as the infrastructure App
Every read and write against GitHub SHALL be authenticated as a GitHub App of the org, both on the owner's machine
and in CI, and never with a personal token. Changes SHALL be made only as the `troupe-run-infrastructure` App. A plan
MAY be made as the read-only `troupe-run-infrastructure-plan` App instead, and a plan made that way SHALL be
applicable as the `troupe-run-infrastructure` App without being made again.

#### Scenario: A plan authenticates as the App
- **WHEN** a plan runs on the owner's machine
- **THEN** its GitHub requests are made with the App's installation token, not the owner's `gh` token

#### Scenario: A read-only plan is applied as the write App
- **WHEN** a plan saved as the read-only App is applied
- **THEN** the apply's GitHub requests are made as `troupe-run-infrastructure`, and the plan file contains neither
  App's private key

### Requirement: Every change is shown as a plan and approved before it is applied
No apply SHALL run unless the plan it applies was shown first and the owner approved it. Every pull request that
changes what is declared SHALL show its plan as evidence. CI posts that plan (spec: ci-apply), and a plan run on the
owner's machine is the fallback when CI can't plan. An apply from the owner's machine is a break-glass: its plan is
shown and approved the same way, and its state reaches `main` through a pull request.

#### Scenario: An apply follows an approved plan
- **WHEN** a change to the org is to be applied
- **THEN** its plan has been shown, and the owner has approved that plan, before the apply runs

#### Scenario: A break-glass apply's state reaches main by pull request
- **WHEN** the owner applies from their machine
- **THEN** the resulting state is committed on a branch and reaches `main` through a pull request, not pushed directly
