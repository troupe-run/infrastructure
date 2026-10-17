# Spec Delta

## MODIFIED Requirements

### Requirement: Secrets are supplied at run time
Running the tool SHALL take the App key, the state passphrase and the DNS host's API token from the environment when
they are set, and otherwise fetch them from the owner's 1Password at that moment. A run that can get none of them
SHALL stop before contacting GitHub or the DNS host, saying which secret is missing and how to supply it.

#### Scenario: Secrets come from 1Password
- **WHEN** the owner runs a plan with the secrets not set in the environment and 1Password available
- **THEN** the secrets are fetched from 1Password for that run only, and the plan proceeds

#### Scenario: Secrets already in the environment are used as they are
- **WHEN** a plan runs with every secret set in the environment
- **THEN** 1Password is not consulted

#### Scenario: A missing secret stops the run
- **WHEN** a plan runs with a secret neither in the environment nor obtainable from 1Password
- **THEN** it stops before contacting GitHub or the DNS host, naming the missing secret and how to supply it

### Requirement: A saved plan holds no key
A saved plan SHALL NOT contain the App's private key or the DNS host's API token. Both SHALL be supplied again when
the plan is applied, so a plan file passed between CI jobs or kept on disk can't be used to act as the App or to
change troupe.run's DNS.

#### Scenario: A saved plan holds no key
- **WHEN** a saved plan is inspected with the passphrase
- **THEN** it contains no private key, and applying it without the key supplied fails

#### Scenario: A saved plan holds no DNS token
- **WHEN** a saved plan is inspected with the passphrase
- **THEN** it contains no DNS host API token, and applying it without the token supplied fails
