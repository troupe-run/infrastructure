# Spec Delta

## ADDED Requirements

### Requirement: No App is installed that nothing uses
Each App installed in the org SHALL be used by something this repository declares or documents. An App that nothing
uses SHALL be deleted, and its declaration and its keys removed with it.

#### Scenario: The declared installations are only the ones in use
- **WHEN** the drift check reads the org's App installations
- **THEN** it finds exactly DCO and `troupe-run-infrastructure`, and reports no difference
