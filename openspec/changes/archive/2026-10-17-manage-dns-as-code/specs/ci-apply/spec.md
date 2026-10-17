# Spec Delta

## MODIFIED Requirements

### Requirement: A pull request's run holds no credential without the owner's approval
A workflow run for a pull request SHALL NOT get any credential (the App's key, the state passphrase or the DNS host's
API token) until the owner has approved that run. A run that isn't approved SHALL NOT plan. A pull request's run
SHALL NOT be able to reach the credential for planning `main`, which needs no approval.

#### Scenario: An unapproved pull request run gets nothing
- **WHEN** a pull request is pushed and the owner hasn't approved its plan run
- **THEN** the run waits, and no step in it has received a secret

#### Scenario: A pull request can't borrow main's plan credential
- **WHEN** a pull request's run asks for the environment that plans `main`
- **THEN** GitHub refuses the deployment
