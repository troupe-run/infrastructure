# org-profile Specification

## Purpose

Makes this repo the source of the files in `troupe-run/.github` (the contributing guide, security policy, org profile
and DCO configuration), so they change through pull requests here and edits made there show up as drift.

## Requirements

### Requirement: The source of `.github`'s files is this repository
Each file in `troupe-run/.github` SHALL have its source in this repository. A difference between a file on GitHub and
its source SHALL appear in the plan. A file in `.github` with no source here SHALL be reported.

#### Scenario: A file edited on GitHub shows as drift
- **WHEN** someone edits `CONTRIBUTING.md` directly in `troupe-run/.github`
- **THEN** the next plan shows the file returning to its source content

#### Scenario: An unexpected file is reported
- **WHEN** a file is added to `troupe-run/.github` that this repository has no source for
- **THEN** the drift check reports it

### Requirement: Adopted files match GitHub byte for byte
When `.github`'s files are adopted, each source SHALL be identical to the file on GitHub at that moment, so adoption
makes no commit to `.github`.

#### Scenario: Adoption makes no commit
- **WHEN** the four files are adopted and a plan runs
- **THEN** the plan shows no change to any of them, and `troupe-run/.github` gets no new commit

### Requirement: Each sync commit names what it syncs
Each commit this repository makes to `troupe-run/.github` SHALL be a Conventional Commit naming the file and
identifying the content it writes. A commit SHALL NOT reuse the message of an earlier sync.

#### Scenario: Two syncs of the same file
- **WHEN** a file in `org-profile/` changes, is applied, then changes again and is applied
- **THEN** the two commits to `troupe-run/.github` have different messages, each identifying the content it wrote

### Requirement: Each file in .github says where it is changed
Each file in `troupe-run/.github` SHALL carry a note naming `troupe-run/infrastructure` as its source and saying to
change it there. The note SHALL NOT appear in what GitHub renders from the file, such as the org's profile page.

#### Scenario: The contributing guide names its source
- **WHEN** someone opens `CONTRIBUTING.md` in `troupe-run/.github` as a raw file
- **THEN** its opening lines say it is written from `troupe-run/infrastructure` and changed there

#### Scenario: The note isn't rendered
- **WHEN** the org's profile page is viewed on GitHub
- **THEN** the note doesn't appear on it

#### Scenario: A new pull request's description doesn't show the note
- **WHEN** someone opens a pull request whose description starts from the org's template
- **THEN** the rendered description doesn't show the note

#### Scenario: An issue form doesn't show the note
- **WHEN** someone opens one of the org's issue forms
- **THEN** the form doesn't show the note
