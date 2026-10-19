## MODIFIED Requirements

### Requirement: Each repository requires its own checks
Each repository with a `main` ruleset SHALL require the checks that run on its pull requests:
- `infrastructure`: its CI check, its `guard tests` check, the `guard` check, DCO, and its pull request's plan;
- `troupe`: its CI `check`, not its legs, the `guard` check and DCO;
- `website`: its CI test and the `guard` check. It SHALL NOT require DCO: its contributions are accepted under its
  own licences, with no sign-off (owner, 2026-10-16).

The required names SHALL be declared in one place.

#### Scenario: The declared names match this repository's workflows
- **WHEN** this repository's tests run
- **THEN** they fail if `infrastructure`'s required checks name a job its workflows don't define, or leave out a job
  the list above says is required

#### Scenario: troupe's legs aren't required, their result is
- **WHEN** this repository's tests run
- **THEN** they fail if troupe's required checks leave out `check`, or name any `check (<os>, Python <version>)` leg:
  a skipped matrix job reports under its unexpanded name, so a required leg would never report on a push that skips
  them

#### Scenario: A renamed job can't be merged past
- **WHEN** a pull request renames a required job, so the old name never reports
- **THEN** the pull request can't be merged until the required checks are changed to match, or the owner bypasses
  the rules

#### Scenario: A website pull request needs the guard check
- **WHEN** a pull request into the website's `main` has passed its CI test but its `guard` check has failed or not
  reported
- **THEN** GitHub refuses to merge it, naming the `guard` check

#### Scenario: A website pull request needs no sign-off
- **WHEN** a pull request into the website's `main` has unsigned-off commits and its CI test and `guard` check have
  passed
- **THEN** the merge succeeds

#### Scenario: A skipped guard-tests matrix doesn't block a merge
- **WHEN** a pull request into `infrastructure` changes nothing the guard's tests depend on, so every guard-tests leg
  is skipped
- **THEN** its required checks can all pass, and it can be merged once they do

#### Scenario: A troupe pull request whose legs were skipped can merge
- **WHEN** the latest push to a troupe pull request skips every check leg, and its `check`, `guard` and DCO checks
  have passed
- **THEN** GitHub shows the pull request as mergeable

#### Scenario: A failed troupe leg blocks the merge
- **WHEN** any check leg on a troupe pull request's latest commit has failed
- **THEN** its `check` fails, and GitHub refuses to merge it, naming `check`
