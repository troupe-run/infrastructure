## ADDED Requirements

### Requirement: Auto-merge is on in the three governed repositories
OpenTofu SHALL set `AUTO_MERGE` to `on` in troupe, infrastructure and website, as the owner decided after the dry-run
week (#320, 2026-11-28). Changing any of them SHALL be a reviewed change to the declaration and a plan the owner
approves; setting one to `off` on GitHub stays the break-glass.

#### Scenario: The declared switches
- **WHEN** the declaration in `tofu/` is read
- **THEN** `AUTO_MERGE` is `on` in troupe, infrastructure and website, and declared for no other repository

#### Scenario: A qualifying pull request after the apply
- **WHEN** a pull request in any of the three repositories qualifies
- **THEN** it is queued and labelled `auto-merged`, and gets no "would have queued" comment
