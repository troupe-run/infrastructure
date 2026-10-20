# Spec Delta

## Purpose

Makes every place on GitHub that introduces troupe (the org's description, troupe's repository description and the
org profile) say the same thing, from one source in this repository, so the wording can't drift between them.

## ADDED Requirements

### Requirement: troupe's description has one source here
troupe's tagline, sentence and status line SHALL be declared once in this repository. The org's description and
troupe's repository description SHALL each be the tagline followed by the sentence, taken from that declaration.

#### Scenario: Changing the sentence changes both descriptions
- **WHEN** the sentence in the declaration is changed and a plan runs
- **THEN** the plan shows the org's description and troupe's repository description both changing to the new text,
  and no other file in this repository needed editing

#### Scenario: A description edited on GitHub shows as drift
- **WHEN** an owner changes the org's description or troupe's repository description on GitHub
- **THEN** the next plan shows it changing back to the declared text

### Requirement: The org profile introduces troupe with the same text
The org profile SHALL carry the declared tagline, a paragraph that opens with the declared sentence, and the declared
status line. A check SHALL fail when the profile doesn't, naming the text that's missing.

#### Scenario: The profile still has the old sentence
- **WHEN** the declared sentence changes and the org profile isn't updated to match
- **THEN** the check fails and names the sentence the profile is missing

#### Scenario: The profile matches
- **WHEN** the profile carries the tagline, opens its paragraph with the sentence and carries the status line
- **THEN** the check passes

### Requirement: The one-line description fits GitHub's limit
The tagline and sentence together SHALL be no longer than 160 characters, the limit GitHub sets on an org's
description. A check SHALL fail when they're longer, giving the length and the limit.

#### Scenario: A sentence that's too long
- **WHEN** the declared sentence is lengthened so that the tagline and sentence together exceed 160 characters
- **THEN** the check fails, giving the length and the limit, before any plan is made

### Requirement: Repositories declare their topics
Each managed repository's topics SHALL be declared. A repository with none SHALL declare an empty list. A topic added
or removed on GitHub SHALL appear in the plan.

#### Scenario: A topic removed by hand
- **WHEN** an owner removes a declared topic from troupe on GitHub
- **THEN** the next plan shows the topic being added back
