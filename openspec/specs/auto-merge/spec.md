# auto-merge Specification

## Purpose
Queues the pull requests that pass the safe-PR rule decided in #319 into the merge queue without the owner, in troupe,
infrastructure and website, and records on each pull request what the rule saw, with switches the owner controls.

## Requirements

### Requirement: A pull request is queued only when every condition holds
The evaluator SHALL queue a pull request only when every condition of the safe-PR rule holds on its current head.
Any one condition failing SHALL leave it unqueued. The run's summary SHALL name, for each open pull request it
judged, the first condition that failed, or that it qualified.

#### Scenario: Everything holds
- **WHEN** a troupe pull request changes 300 code lines in 6 files, its highest function complexity is 9, and every
  other condition holds, with `AUTO_MERGE=on`
- **THEN** the evaluator queues it

#### Scenario: One condition fails
- **WHEN** the same pull request has one nit conversation unresolved
- **THEN** it isn't queued, and the run's summary names the open conversation

### Requirement: Only a ready pull request from the same repository qualifies
A pull request SHALL qualify only when it's open, isn't a draft, targets `main`, has its head branch in the same
repository, has no `hold` label, and GitHub reports no merge conflict.

#### Scenario: A draft
- **WHEN** a pull request is still a draft
- **THEN** it isn't queued

#### Scenario: A fork
- **WHEN** a pull request's head branch is in a fork
- **THEN** it isn't queued, whatever else holds

#### Scenario: A conflict
- **WHEN** GitHub reports the pull request as conflicting with `main`
- **THEN** it isn't queued

### Requirement: Every required check is green on the head
A pull request SHALL qualify only when every status check that `main`'s rules require has passed on its head commit,
as GitHub reports them now, a skipped check counting as passed.

#### Scenario: A required check failed
- **WHEN** `check` failed on the head
- **THEN** it isn't queued

#### Scenario: A required check is still running
- **WHEN** `guard (workflow rules)` hasn't finished on the head
- **THEN** it isn't queued yet, and a later run judges it again

#### Scenario: A skipped plan
- **WHEN** infrastructure's `plan (pull request)` is skipped because nothing OpenTofu reads changed
- **THEN** that check counts as passed

### Requirement: Claude's review read everything
A pull request SHALL qualify only when the review of its head completed with coverage `complete`. When every commit
after the last commit whose review completed with coverage `complete` changes only files under `openspec/`, that
review SHALL count for the head.

#### Scenario: Coverage at the floor only
- **WHEN** the head's review completed, read every source and test file, and left prose unread (`incomplete`)
- **THEN** it isn't queued

#### Scenario: An archive-only push
- **WHEN** the review of commit A was complete, and the only commit since moves `openspec/changes/auto-merge/` into
  `openspec/changes/archive/`
- **THEN** A's review counts, and the condition holds

#### Scenario: A code push after the complete review
- **WHEN** a commit after the complete review changes `scripts/auto_merge.py`
- **THEN** the earlier review doesn't count, and the head's own review decides

#### Scenario: No review result
- **WHEN** the head's review result can't be found or read
- **THEN** it isn't queued, and the run's summary says the result couldn't be read

### Requirement: No conversation is open and no change is requested
A pull request SHALL qualify only when none of its review conversations is unresolved, whatever its tier, and no
reviewer's latest review requests changes.

#### Scenario: An open decision
- **WHEN** a decision conversation is still open
- **THEN** it isn't queued

#### Scenario: A person's open conversation
- **WHEN** a conversation the owner opened is unresolved
- **THEN** it isn't queued

### Requirement: Every commit is signed off and the change is archived
A pull request SHALL qualify only when every commit it adds carries a `Signed-off-by:` trailer, in every repository,
and its head has no change left under `openspec/changes/` outside `archive/` with the head branch's name.

#### Scenario: A commit without sign-off in website
- **WHEN** one commit of a website pull request has no `Signed-off-by:` trailer, though website requires no DCO check
- **THEN** it isn't queued

#### Scenario: The change isn't archived
- **WHEN** `openspec/changes/<branch>/` still exists at the head
- **THEN** it isn't queued

### Requirement: Every commit is a person's and the head was pushed by the author
A pull request SHALL qualify only when no commit it adds is authored or committed by a bot account, and every
workflow run GitHub started for its head from a pull request event was started by the pull request's author. A
commit or a run whose author, committer or actor can't be read, or a head with no such run, SHALL fail the condition.

#### Scenario: A commit from the merge App
- **WHEN** a commit on the pull request's branch was committed by `troupe-run-merge[bot]`
- **THEN** it isn't queued, whatever else holds

#### Scenario: A commit authored by another bot
- **WHEN** a commit was authored by `dependabot[bot]` on a person's pull request
- **THEN** it isn't queued

#### Scenario: Someone else pushed the head
- **WHEN** the pull request's author is A, and its head's `pull_request` runs were started by B
- **THEN** it isn't queued

#### Scenario: The pusher can't be read
- **WHEN** listing the head's workflow runs fails, or finds none from a pull request event
- **THEN** it isn't queued, and the run's summary says the pusher couldn't be read

### Requirement: The issues it closes are neither decisions nor blocked
A pull request SHALL qualify only when every issue it closes, through its description's closing lines or GitHub's
closing references, in any repository, isn't of type Decision, has no `needs:owner` label, and is blocked by
no open issue. An issue or dependency that can't be read SHALL fail the condition.

#### Scenario: It closes a Decision
- **WHEN** the pull request closes an issue of type Decision
- **THEN** it isn't queued

#### Scenario: It closes an issue waiting on the owner
- **WHEN** an issue it closes has the `needs:owner` label
- **THEN** it isn't queued

#### Scenario: It closes a blocked issue
- **WHEN** it closes troupe-run/troupe#278, which is blocked by troupe-run/infrastructure#272, still open
- **THEN** it isn't queued

#### Scenario: A dependency can't be read
- **WHEN** reading a closed issue's blocked-by list fails
- **THEN** it isn't queued, and the run's summary names the issue

### Requirement: Nothing protected changes
A pull request SHALL qualify only when no changed path matches its repository's protected list and it deletes no
component. Deleting any `pyproject.toml`, any `package.json`, or any `openspec/specs/*/spec.md` SHALL count as
deleting a component. Every path in the repository's `.github/guard-delivery.json` SHALL be protected.

#### Scenario: A workflow
- **WHEN** a website pull request changes `.github/workflows/deploy.yml`
- **THEN** it isn't queued

#### Scenario: Masking code
- **WHEN** a troupe pull request changes `packages/troupe/src/troupe/core/masking.py`
- **THEN** it isn't queued

#### Scenario: A deleted plugin
- **WHEN** a troupe pull request deletes `plugins/runner-foo/pyproject.toml` with the rest of that plugin
- **THEN** it isn't queued

#### Scenario: The rule's own files
- **WHEN** an infrastructure pull request changes `auto-merge.toml`, `scripts/auto_merge.py` or `oob/`
- **THEN** it isn't queued

### Requirement: The change is within the size and complexity limits
A pull request SHALL qualify only when its changed lines, its changed files, the highest cyclomatic complexity of any
function it adds or makes more complex, and the sum of those rises (a new function's whole complexity) are each within
the limit its repository's config sets.

#### Scenario: Too many lines
- **WHEN** a pull request changes 1,200 code lines and the limit is 800
- **THEN** it isn't queued, and the summary says 1200 > 800

#### Scenario: One complex function
- **WHEN** a pull request adds one function of complexity 18, and the limit is 15
- **THEN** it isn't queued, though the blocking complexity gate at 25 passes

#### Scenario: An edit inside a complex function that adds no branching
- **WHEN** a pull request changes one line inside an existing function of complexity 25, and its complexity stays 25
- **THEN** that function counts for nothing toward the complexity limits

#### Scenario: A function made simpler
- **WHEN** a pull request lowers a function's complexity from 20 to 16
- **THEN** that function counts for nothing toward the complexity limits

#### Scenario: A similar line in many files
- **WHEN** a pull request adds one similar line to each of 40 files, with no new branching
- **THEN** it isn't queued for its 40 files (limit 30), and its complexity limits pass

### Requirement: Generated files and prose don't count toward the line limit
The line count SHALL leave out lock files, recorded fixtures, `openspec/`, `docs/` and Markdown files, as the config
lists them. The file count SHALL leave out only the generated files. Complexity SHALL be measured on non-test source
files in the config's languages.

#### Scenario: A lock file
- **WHEN** a pull request changes 3,000 lines of `uv.lock` and 100 lines of code
- **THEN** it counts 100 changed lines

#### Scenario: A long design
- **WHEN** a pull request adds a 600-line `design.md` and 200 lines of code
- **THEN** it counts 200 changed lines

### Requirement: The rule's settings live in one config file
The protected list, the line and file exclusions and the four limits SHALL be read from `auto-merge.toml` in
infrastructure, per repository, and from nowhere else. An unknown key, a wrong type, a missing repository or a
negative limit SHALL fail the run, naming the key.

#### Scenario: A misspelt limit
- **WHEN** the config has `max_line = 800` instead of `max_lines`
- **THEN** the run fails, naming `max_line` and the valid keys, and queues nothing

#### Scenario: Default limits
- **WHEN** the config is read as delivered by this change
- **THEN** each repository's limits are 800 lines, 30 files, complexity 15 and an increase of 40

### Requirement: A repository variable switches it per repository
In each repository, the variable `AUTO_MERGE` SHALL decide what the evaluator does there: `on` queues, `dry-run` only
comments, and `off` or unset does nothing. Any other value SHALL be an error, reported in the run, and SHALL queue and
comment nothing in that repository.

#### Scenario: Unset
- **WHEN** website has no `AUTO_MERGE` variable
- **THEN** nothing is queued or commented there

#### Scenario: A wrong value
- **WHEN** troupe's `AUTO_MERGE` is `yes`
- **THEN** the run reports the bad value, says `off`, `dry-run` and `on` are valid, and does nothing in troupe

#### Scenario: Dry-run
- **WHEN** `AUTO_MERGE=dry-run` and a pull request qualifies
- **THEN** it isn't queued, and it gets one "would have queued" comment for that head

### Requirement: A queued pull request records why
When it queues a pull request, the evaluator SHALL add the `auto-merged` label and post one comment. The comment SHALL
give the rule's version, the head SHA, and what each condition saw, with links to the check runs.

#### Scenario: The comment
- **WHEN** a pull request is queued
- **THEN** its comment lists the required checks with their runs, the review's coverage, the issues closed, the
  protected-path result, and the lines, files, highest complexity and increase against their limits

### Requirement: Dry-run comments once per head
In dry-run, the evaluator SHALL post one "would have queued" comment per head SHA that qualifies, with the same
content as a queued pull request's, and SHALL add no label.

#### Scenario: Several runs on one head
- **WHEN** the evaluator runs four times while a qualifying pull request's head stays the same
- **THEN** the pull request has one "would have queued" comment for that head

#### Scenario: A new push
- **WHEN** the pull request gets a new head that still qualifies
- **THEN** it gets a second comment, for the new head

### Requirement: The queueing names the head it judged
The evaluator SHALL queue a pull request with the head SHA it judged, so a push made after the judging makes the
queueing fail, and nothing it didn't judge is queued.

#### Scenario: A push during the run
- **WHEN** a commit is pushed between the evaluator's reading of the pull request and its queueing
- **THEN** GitHub refuses the queueing, and the next run judges the new head

### Requirement: The hold label stops it
A pull request with the `hold` label SHALL NOT be queued. When a pull request the App queued gets the label while
still in the queue, the evaluator SHALL take it out of the queue.

#### Scenario: Held before it qualifies
- **WHEN** a qualifying pull request has `hold`
- **THEN** it isn't queued

#### Scenario: Held while queued
- **WHEN** the owner adds `hold` to a pull request the App queued, which hasn't merged yet
- **THEN** the next run takes it out of the queue

### Requirement: A head is queued at most once
The evaluator SHALL queue a given head SHA of a pull request at most once. A head that left the queue without
merging SHALL stay out until a person queues it, or a new push gives a new head.

#### Scenario: The owner takes it out of the queue
- **WHEN** the owner removes a pull request the App queued from the queue
- **THEN** no later run queues it again on that head

#### Scenario: The queue drops it
- **WHEN** the merge queue drops the pull request because its group failed
- **THEN** it isn't queued again on that head, and re-queueing it is the owner's

### Requirement: The evaluator never runs a pull request's code
The evaluator SHALL run only `main`'s files in infrastructure. It SHALL read pull requests through GitHub's API and as
git data, and SHALL execute nothing from them.

#### Scenario: A pull request changes the evaluator
- **WHEN** an open pull request changes `scripts/auto_merge.py`
- **THEN** the evaluator judges it with `main`'s copy, and the pull request isn't queued because the file is protected

### Requirement: The evaluator runs on events and on a backstop
The evaluator SHALL run when CI, `guard` or the review completes, or a pull request's labels change, in any of the
three repositories, and every 15 minutes as a backstop. Each run SHALL judge every open pull request in the three
repositories.

#### Scenario: A conversation is resolved
- **WHEN** the last open conversation on a qualifying pull request is resolved, which starts no workflow
- **THEN** the next backstop run judges it and queues it

#### Scenario: CI completes in troupe
- **WHEN** CI completes on a troupe pull request
- **THEN** troupe's dispatcher starts the evaluator, which judges that pull request

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
