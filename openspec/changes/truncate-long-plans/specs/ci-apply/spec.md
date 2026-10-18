## ADDED Requirements

### Requirement: A plan too long to show is cut on purpose, never silently
Wherever CI shows a plan with a size limit, the pull request's plan comment and the run summary of `main`'s plan, the
plan SHALL be shown whole when it fits. When it doesn't, it SHALL be cut at a line boundary, below the limit, with a
note that it is truncated, how much is shown, and a link to the full plan. Every resource change line and the `Plan:`
line SHALL be listed in full above the cut. A plan SHALL never be cut without that note.

#### Scenario: A plan that fits is shown whole
- **WHEN** a pull request's plan fits within the comment's limit
- **THEN** the comment holds the whole plan and no truncation note

#### Scenario: A plan over the limit is cut at a line, with the summary kept
- **WHEN** a pull request's plan is longer than the comment's limit
- **THEN** the comment stays under GitHub's limit, lists every resource change and the `Plan:` line above the plan,
  shows the plan up to the end of a whole line, says it is truncated and how many of its lines and bytes are shown,
  and links to the full plan

#### Scenario: The full plan is reachable from the comment
- **WHEN** a reader follows the link in a truncated plan comment
- **THEN** they reach the whole plan made by that run

#### Scenario: The plan for approval is cut the same way
- **WHEN** the plan of `main` is longer than the run summary's limit
- **THEN** the run summary lists every resource change and the `Plan:` line, shows the plan cut at a line with the
  truncation note, and links to the full plan

#### Scenario: A summary that can't fit fails the step
- **WHEN** the resource change lines and the `Plan:` line alone don't fit within the limit
- **THEN** the step fails, naming the limit, and posts nothing with any of them left out
