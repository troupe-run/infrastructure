# state-and-apply Specification

## Purpose

Keeps the org's declared state safe and changeable only on purpose: state is committed but encrypted, the tool acts
as the infrastructure App, secrets never enter the repo, and every change is shown as a plan and approved by the owner.

## Requirements

### Requirement: No secret is stored in the repository
The repository SHALL contain no secret: no private key, token, passphrase or secret value, in any file or commit.
The App ID, the installation ID and references to where secrets are kept are not secrets and MAY be committed.

#### Scenario: A plan leaves no secret behind
- **WHEN** a plan has been run and the working tree is inspected
- **THEN** no file in the working tree, tracked or untracked, contains the App's private key or the state passphrase

### Requirement: State is committed encrypted
The state SHALL be committed to the repository, and SHALL be stored only in encrypted form. Saved plan files SHALL be
encrypted too. Reading or writing either without the passphrase SHALL fail rather than fall back to plain text.

#### Scenario: State is unreadable without the passphrase
- **WHEN** the committed state file is read without the passphrase
- **THEN** it reveals no resource attributes, and the tool refuses to use it

#### Scenario: A missing passphrase doesn't produce plain-text state
- **WHEN** a plan or apply runs without the passphrase
- **THEN** it fails before writing any state or plan file

### Requirement: The tool acts as the infrastructure App
Every read and write against GitHub SHALL be authenticated as the `troupe-run-infrastructure` GitHub App, both on
the owner's machine and in CI, and never with a personal token.

#### Scenario: A plan authenticates as the App
- **WHEN** a plan runs on the owner's machine
- **THEN** its GitHub requests are made with the App's installation token, not the owner's `gh` token

### Requirement: Secrets are supplied at run time
Running the tool SHALL take the App key and the state passphrase from the environment when they are set, and
otherwise fetch them from the owner's 1Password at that moment. A run that can get neither SHALL stop before
contacting GitHub, saying which secret is missing and how to supply it.

#### Scenario: Secrets come from 1Password
- **WHEN** the owner runs a plan with the secrets not set in the environment and 1Password available
- **THEN** the secrets are fetched from 1Password for that run only, and the plan proceeds

#### Scenario: Secrets already in the environment are used as they are
- **WHEN** a plan runs with both secrets set in the environment
- **THEN** 1Password is not consulted

#### Scenario: A missing secret stops the run
- **WHEN** a plan runs with a secret neither in the environment nor obtainable from 1Password
- **THEN** it stops before contacting GitHub, naming the missing secret and how to supply it

### Requirement: Every change is shown as a plan and approved before it is applied
No apply SHALL run unless the plan it applies was shown first and the owner approved it. Every pull request that
changes what is declared SHALL include its plan as evidence.

#### Scenario: An apply follows an approved plan
- **WHEN** a change to the org is to be applied
- **THEN** its plan has been shown, and the owner has approved that plan, before the apply runs

### Requirement: Adoption is proven by a plan with no changes
Bringing an existing GitHub object under management SHALL leave it unchanged. Its adoption is complete only when a
plan reports no changes for it.

#### Scenario: A clean plan after adoption
- **WHEN** the existing org, repositories, labels, App installations and `.github` files have been imported
- **THEN** `tofu plan` reports no changes to add, change or destroy
