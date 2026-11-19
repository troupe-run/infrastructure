# Spec Delta

## ADDED Requirements

### Requirement: A pull request can't merge while an issue it closes is blocked
The GitHub check SHALL fail under `blocked-by` when an issue a pull request closes is blocked by an issue that's still
open, in any repository. The closed issues SHALL be read as `pr-closes-issue` reads them. Every open blocker SHALL
count, whatever its type. The refusal SHALL name the closed issue, the blocker and the fix.

#### Scenario: Blocked by an open issue in another repository
- **WHEN** a troupe pull request's description says `Closes #278`, and troupe-run/troupe#278 is blocked by
  troupe-run/infrastructure#272, which is open
- **THEN** the GitHub check fails under `blocked-by`, saying troupe-run/troupe#278 is blocked by
  troupe-run/infrastructure#272, which is still open, to merge that first and then re-run the check

#### Scenario: The blocker is closed
- **WHEN** the same pull request's check is re-run after troupe-run/infrastructure#272 closes
- **THEN** the GitHub check doesn't fail under `blocked-by`

#### Scenario: Blocked in the same repository
- **WHEN** an infrastructure pull request closes #300, which is blocked by #299, which is open
- **THEN** the GitHub check fails under `blocked-by`, naming troupe-run/infrastructure#299

#### Scenario: The blocker is an Epic or a reopened Decision
- **WHEN** the blocker is an open issue of type Epic, or a Decision that was reopened
- **THEN** the GitHub check fails under `blocked-by`, as for any open blocker

#### Scenario: No blockers
- **WHEN** no issue the pull request closes is blocked by anything
- **THEN** the GitHub check doesn't fail under `blocked-by`

#### Scenario: A release pull request
- **WHEN** troupe's release pull request is checked, and its body, release-please's changelog, says "Fixes #5"
  about an issue blocked by an open one
- **THEN** the GitHub check doesn't fail under `blocked-by`: a release branch that passes the branch rule is exempt,
  as from `pr-closes-issue`, and its body isn't read

### Requirement: The merge queue re-checks blocked issues
In a merge group, the GitHub check SHALL read the pull request the group was built for, and judge its closed issues'
blockers as on the pull request, so a blocker opened or reopened after the pull request's own check fails the group.

#### Scenario: A blocker reopened after the pull request passed
- **WHEN** a pull request passed `blocked-by`, its closed issue's blocker is then reopened, and the pull request is
  queued
- **THEN** the merge group's check fails under `blocked-by`, and the pull request leaves the queue unmerged

#### Scenario: The merge group's pull request can't be found
- **WHEN** a merge group's branch name doesn't give a pull request number
- **THEN** the GitHub check fails under `blocked-by`, saying it couldn't tell which pull request the group is for

### Requirement: An unreadable dependency fails the blocked-by check
When an issue the pull request closes, its blocked-by list, or a blocker's state can't be read, the GitHub check SHALL
fail under `blocked-by`. The message SHALL name what couldn't be read, and SHALL say to re-run the check. It SHALL
never treat the issue as not blocked.

#### Scenario: The API refuses
- **WHEN** reading troupe-run/troupe#278's blocked-by list returns 403
- **THEN** the GitHub check fails under `blocked-by`, naming troupe-run/troupe#278 and the status, and says to re-run
  the check and tell the owner if it fails again

#### Scenario: A closed issue that doesn't exist
- **WHEN** a pull request's description says `Closes #99999`, and no such issue exists
- **THEN** the GitHub check fails under `blocked-by`, saying troupe-run/<repository>#99999 couldn't be read

### Requirement: Removing the hold label is the owner's
In a Claude Code session, removing the `hold` label from a pull request or an issue SHALL be refused under
`owner-only`, in any repository. Adding `hold`, and removing any other label, SHALL be allowed as before.

#### Scenario: An agent lifts a hold
- **WHEN** an agent runs `gh pr edit 41 --remove-label hold`, or `gh pr edit 41 --remove-label bug,hold`
- **THEN** the command is refused, and the message says only the owner lifts a hold

#### Scenario: Through issue edit
- **WHEN** an agent runs `gh issue edit 41 --remove-label hold`
- **THEN** the command is refused the same way

#### Scenario: Through the API
- **WHEN** an agent runs `gh api -X DELETE repos/troupe-run/troupe/issues/41/labels/hold`, or
  `gh api -X PATCH repos/troupe-run/troupe/issues/41 -f 'labels[]=bug'`, which replaces the labels
- **THEN** the command is refused the same way

#### Scenario: An agent adds a hold
- **WHEN** an agent runs `gh pr edit 41 --add-label hold`
- **THEN** the command is allowed

#### Scenario: Another label
- **WHEN** an agent runs `gh pr edit 41 --remove-label needs:owner`
- **THEN** the command is allowed
