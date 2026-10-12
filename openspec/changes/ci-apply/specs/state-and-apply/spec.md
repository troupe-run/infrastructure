# Spec Delta

## MODIFIED Requirements

### Requirement: Every change is shown as a plan and approved before it is applied
No apply SHALL run unless the plan it applies was shown first and the owner approved it. Every pull request that
changes what is declared SHALL show its plan as evidence. CI posts that plan (spec: ci-apply), and a plan run on the
owner's machine is the fallback when CI can't plan. A saved plan SHALL NOT contain the App's private key; it is
supplied again when the plan is applied. An apply from the owner's machine is a break-glass: its plan is
shown and approved the same way, and its state reaches `main` through a pull request.

#### Scenario: An apply follows an approved plan
- **WHEN** a change to the org is to be applied
- **THEN** its plan has been shown, and the owner has approved that plan, before the apply runs

#### Scenario: A saved plan holds no key
- **WHEN** a saved plan is inspected with the passphrase
- **THEN** it contains no private key, and applying it without the key supplied fails

#### Scenario: A break-glass apply's state reaches main by pull request
- **WHEN** the owner applies from their machine
- **THEN** the resulting state is committed on a branch and reaches `main` through a pull request, not pushed directly
