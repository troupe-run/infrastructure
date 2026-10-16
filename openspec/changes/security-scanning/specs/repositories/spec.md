## ADDED Requirements

### Requirement: Repositories have their security features on
Every managed repository SHALL have Dependabot alerts, Dependabot security updates, secret scanning and secret
scanning push protection turned on, and each SHALL be declared, so that one turned off on GitHub appears in the plan.
Turning them on SHALL change no other setting of the repository.

#### Scenario: Every repository reads as protected
- **WHEN** each managed repository's security settings are read from GitHub after an apply
- **THEN** Dependabot alerts, Dependabot security updates, secret scanning and push protection are all on, and the
  plan shows no difference

#### Scenario: A feature turned off by hand shows as drift
- **WHEN** an owner turns off any of the four features on a managed repository on GitHub
- **THEN** the next plan shows it turning back on

#### Scenario: Turning them on leaves the other settings alone
- **WHEN** the features are turned on for a repository whose other settings already match the declaration
- **THEN** its other settings on GitHub are the same afterwards, the homepage and description included

### Requirement: Push protection lets the org's own commits through
Push protection SHALL NOT refuse the commits this repository's automation makes: the App's commits of the encrypted
state, and its deliveries of the guard's files. It SHALL still refuse a commit that contains a token GitHub
recognises.

#### Scenario: The state commit is accepted
- **WHEN** the encrypted state is committed to a repository that has push protection on
- **THEN** the commit is accepted

#### Scenario: A guard delivery is accepted
- **WHEN** the guard's delivered files are committed through the API to a repository that has push protection on
- **THEN** the commit is accepted

#### Scenario: A token is refused
- **WHEN** a commit containing a string in a token format GitHub scans for is pushed to a repository that has push
  protection on
- **THEN** the push is refused
