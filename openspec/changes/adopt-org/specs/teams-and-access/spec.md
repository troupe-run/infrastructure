# Spec Delta

## Purpose

Declares who and what has access to the org's repositories. It starts with which repositories each GitHub App is
installed on, and teams join it when the org has some.

## ADDED Requirements

### Requirement: Each App's repositories are declared
For each GitHub App installed in the org (today DCO and `troupe-run-infrastructure`), the repositories it is
installed on SHALL be declared here. A difference from GitHub SHALL be reported by the plan or, where OpenTofu
can't read it, by a documented drift check.

#### Scenario: An App added to a repository by hand is reported
- **WHEN** an owner adds a repository to an App's installation on GitHub without changing the declaration
- **THEN** the next plan or drift check reports that repository

#### Scenario: The declared installations match
- **WHEN** each App's installed repositories match the declaration
- **THEN** neither the plan nor the drift check reports a difference
