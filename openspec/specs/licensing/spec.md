# licensing Specification

## Purpose

Says which licence this repository is published under, declares it in the repository's own files the way troupe does,
and keeps the org's contributing guide naming the same licence.

## Requirements

### Requirement: This repository is licensed Apache-2.0, as troupe is
This repository SHALL be published under Apache-2.0, the licence troupe uses. Its root `LICENSE` SHALL hold the
Apache-2.0 text, its `pyproject.toml` SHALL declare `Apache-2.0` with that file, and its README SHALL name the licence,
saying the troupe name, logo, mark and characters are trademarks of HPS.GD PTY LTD and aren't covered by it.

#### Scenario: GitHub detects the licence
- **WHEN** GitHub's licence API is asked for infrastructure's licence
- **THEN** it reports `Apache-2.0`, read from `LICENSE`

#### Scenario: The README names the licence
- **WHEN** someone reads the README
- **THEN** a Licence section links `LICENSE`, names Apache-2.0 and carries the trademark note

### Requirement: The guide names the licence this repository declares
The org's contributing guide SHALL give infrastructure the licence its `pyproject.toml` declares. A difference SHALL
fail the repository's check, naming both licences.

#### Scenario: The licence changes without the guide
- **WHEN** `pyproject.toml`'s `license` changes and the guide's infrastructure row doesn't
- **THEN** the check fails, naming the licence declared and the licence the guide gives
