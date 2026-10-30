## MODIFIED Requirements

### Requirement: Claude reviews each pull request when it's opened and updated
A pull request in troupe, infrastructure or website SHALL get a review from Claude when it's opened, reopened, or
pushed to. Drafts SHALL be reviewed too. Marking a draft ready for review SHALL NOT start a review: its head was
reviewed when it was pushed. The review SHALL be posted as comments on the pull request: inline on the lines it
concerns, and one top-level summary.

#### Scenario: A pull request is opened
- **WHEN** a member opens a pull request from a branch of troupe, infrastructure or website
- **THEN** a review run starts, and Claude's comments appear on the pull request once it finishes

#### Scenario: A pull request is updated
- **WHEN** a member pushes a new commit to a pull request's branch
- **THEN** a new review run starts for the new head, and a run still going for the earlier head is cancelled

#### Scenario: A draft
- **WHEN** a member opens a draft pull request
- **THEN** it's reviewed as any other pull request is

#### Scenario: A draft is marked ready
- **WHEN** a member marks a draft pull request ready for review, with no new push
- **THEN** no review run starts, and the review of its last push stands

#### Scenario: A push after it's marked ready
- **WHEN** a member pushes to a pull request after marking it ready
- **THEN** a review run starts for the new head, as for any push
