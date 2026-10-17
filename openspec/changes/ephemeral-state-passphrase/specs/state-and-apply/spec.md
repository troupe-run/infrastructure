## MODIFIED Requirements

### Requirement: A saved plan holds no key
A saved plan SHALL NOT contain the App's private key, the DNS host's API token or the state passphrase, in any
rendering of it, including the JSON of the decrypted plan. Each SHALL be supplied again when the plan is applied, so a
plan file passed between CI jobs or kept on disk, or its decrypted JSON, can't be used to act as the App, to change
troupe.run's DNS or to decrypt the committed state. Every plan CI makes SHALL be checked for all three, and a plan
holding any of them SHALL fail its job.

#### Scenario: A saved plan holds no key
- **WHEN** a saved plan is inspected with the passphrase
- **THEN** it contains no private key, and applying it without the key supplied fails

#### Scenario: A saved plan holds no DNS token
- **WHEN** a saved plan is inspected with the passphrase
- **THEN** it contains no DNS host API token, and applying it without the token supplied fails

#### Scenario: A saved plan holds no state passphrase
- **WHEN** a saved plan is rendered as JSON with the passphrase
- **THEN** the JSON contains no state passphrase, neither among its variables nor anywhere else, and applying the plan
  without the passphrase supplied fails

#### Scenario: CI refuses a plan that holds a key
- **WHEN** a plan made in CI contains the App's private key, the DNS host's API token or the state passphrase
- **THEN** the plan job fails before any other step reads the plan's JSON, naming which secret it found and not
  printing its value
