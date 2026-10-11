# Spec Delta

## ADDED Requirements

### Requirement: Each sync commit names what it syncs
Each commit this repository makes to `troupe-run/.github` SHALL be a Conventional Commit naming the file and
identifying the content it writes. A commit SHALL NOT reuse the message of an earlier sync.

#### Scenario: Two syncs of the same file
- **WHEN** a file in `org-profile/` changes, is applied, then changes again and is applied
- **THEN** the two commits to `troupe-run/.github` have different messages, each identifying the content it wrote
