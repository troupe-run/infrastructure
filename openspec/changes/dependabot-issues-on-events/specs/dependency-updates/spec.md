# Spec Delta

## ADDED Requirements

### Requirement: Dependabot's runs start the workflow
Each completed "Dependabot Updates" run in troupe, website or infrastructure SHALL start `dependabot-issues` on
infrastructure's `main`, whatever the run's conclusion. A Dependabot pull request that run opened or rewrote SHALL have
its issue and closing line within an hour of the run completing, with nobody starting the workflow by hand.

#### Scenario: Dependabot opens a pull request in website
- **WHEN** a "Dependabot Updates" run in website opens a pull request and completes
- **THEN** a `dependabot-issues` run starts on infrastructure's `main`, and within the hour the pull request has its
  issue and its closing line

#### Scenario: Dependabot rebases a pull request in troupe
- **WHEN** a "Dependabot Updates" run in troupe rebases a pull request and drops its closing line
- **THEN** a `dependabot-issues` run starts, and within the hour the line is back and `guard` passes
  `pr-closes-issue` again

#### Scenario: Dependabot acts in infrastructure
- **WHEN** a "Dependabot Updates" run in infrastructure completes
- **THEN** a `dependabot-issues` run starts in infrastructure, with no dispatch from another repository

#### Scenario: A burst of Dependabot runs
- **WHEN** several "Dependabot Updates" runs complete within a few minutes, as on Dependabot's weekly run
- **THEN** no two `dependabot-issues` runs are in progress at once, and a run starts after the last of them
  completes

### Requirement: The dispatch from troupe and website only starts the workflow
In troupe and website, the workflow that starts `dependabot-issues` SHALL run from that repository's `main` only. It
SHALL check out nothing, SHALL NOT pass anything from its triggering event to the run it starts, and SHALL do nothing
but start `dependabot-issues` on infrastructure's `main`. It SHALL be one of the guard's delivered files.

#### Scenario: What the dispatcher does
- **WHEN** the dispatcher's workflow file is read
- **THEN** it has no checkout step, no workflow expression that reads the event, and one step that starts
  `dependabot-issues.yml` in troupe-run/infrastructure on `main`

#### Scenario: The dispatcher in infrastructure
- **WHEN** a "Dependabot Updates" run completes in infrastructure, which holds the dispatcher as its source
- **THEN** the dispatcher's job is skipped there, and it uses no environment

#### Scenario: The dispatch credential is missing
- **WHEN** troupe's dispatcher runs before `DISPATCH_APP_PRIVATE_KEY` is set
- **THEN** its run fails, and the next daily backstop reports any pull request this left without its issue or closing
  line

### Requirement: A daily backstop does the work any run would do
`dependabot-issues` SHALL also run once a day on a schedule, and SHALL do in that run all that any other run does. That
includes what only a run more than an hour after a pull request closes can do, such as closing an issue as not planned.

#### Scenario: Dependabot gives up on an update between its runs
- **WHEN** Dependabot closes a pull request without merging, no successor opens, and no other Dependabot run follows
- **THEN** the next backstop run after the hour closes its issue as not planned

#### Scenario: A person closes a Dependabot pull request
- **WHEN** a person closes a Dependabot pull request without merging, which starts no Dependabot run
- **THEN** the next backstop run after the hour closes its issue as not planned

### Requirement: A missed event is reported
A backstop run SHALL count as missed each open Dependabot pull request that, when the run starts, lacks its issue or
closing line and was last updated over an hour ago. It SHALL fix each one, then report the misses in one tracking issue
in infrastructure, and fail. No other work it does SHALL count as a miss.

#### Scenario: A dispatch didn't happen
- **WHEN** a backstop run finds a website pull request rebased three hours ago with no closing line
- **THEN** it puts the line back, opens or comments on the tracking issue naming the pull request, and the run fails

#### Scenario: Work only the backstop can do
- **WHEN** a backstop run's only work is closing issues whose pull requests closed over an hour ago, or merged
- **THEN** it does that work, reports no miss, and the run succeeds

#### Scenario: A pull request updated within the hour
- **WHEN** a backstop run finds a pull request without its closing line that Dependabot rewrote 10 minutes ago
- **THEN** it puts the line back and doesn't count it as a miss

#### Scenario: A run that isn't the backstop
- **WHEN** a run started by Dependabot's run, by dispatch, or by hand without asking for the backstop finds a pull
  request missing its issue or line
- **THEN** it fixes it and reports no miss

#### Scenario: The backstop started by hand
- **WHEN** the owner starts `dependabot-issues` by hand asking for the backstop
- **THEN** the run counts and reports misses as the daily backstop does

### Requirement: The missed-event tracking issue follows the misses
The tracking issue SHALL be opened by the Dependabot issues App in infrastructure, titled "Dependabot events missed",
and put on the troupe roadmap board. A backstop SHALL open it when it finds misses and none is open, comment only when
the misses differ from those last reported, and close it with a comment when it finds none.

#### Scenario: First misses
- **WHEN** a backstop run finds misses and no tracking issue is open
- **THEN** it opens the tracking issue, naming each pull request and linking the run, and the board job adds it to
  the board

#### Scenario: The same misses the next day
- **WHEN** a backstop run finds the same misses the open issue last reported
- **THEN** it adds no comment

#### Scenario: Back to normal
- **WHEN** a backstop run finds no miss and the tracking issue is open
- **THEN** it closes the issue with a comment linking the run

#### Scenario: An issue someone else opened with the same title
- **WHEN** an open issue has the tracking title but wasn't opened by the App
- **THEN** the backstop neither comments on it nor closes it

## MODIFIED Requirements

### Requirement: The workflow never runs the pull requests' code
`dependabot-issues` SHALL run from infrastructure's `main` only: when a "Dependabot Updates" run completes, when
troupe or website dispatch it, once a day, and by hand. It SHALL check out only infrastructure's `main`, and read the
pull requests through the API: their author, number, branch, title, state and description. It SHALL NOT check out,
fetch or run any file of a pull request, or read anything from its triggering event.

#### Scenario: What the workflow checks out
- **WHEN** the workflow file is read
- **THEN** its only checkout is of the repository it runs in, at the default ref, and no step fetches a pull
  request's head

#### Scenario: Started by hand from a branch
- **WHEN** someone starts `dependabot-issues` by hand on a branch other than `main`
- **THEN** GitHub refuses its environment, and the run writes nothing

#### Scenario: Pull request text is data
- **WHEN** a Dependabot pull request's title or description contains shell or workflow-expression syntax
- **THEN** the run treats it as text, and no step evaluates it

#### Scenario: The triggering event is not read
- **WHEN** the workflow file is read
- **THEN** no workflow expression in it reads `github.event`, apart from the event's name

#### Scenario: No 10-minute schedule
- **WHEN** the workflow file is read
- **THEN** its only schedule is daily

### Requirement: Delivered workflows are updated only at their source
In each repository that receives the guard, the `github-actions` entry SHALL leave out every workflow the guard
delivers there, so Dependabot proposes no change to a delivered file. In this repository, which is their source, the
entry SHALL cover them. The list left out SHALL be taken from the guard's delivered files.

#### Scenario: troupe leaves out the delivered workflows
- **WHEN** troupe's `github-actions` entry is read
- **THEN** it leaves out `.github/workflows/guard.yml`, `.github/workflows/claude-review.yml` and
  `.github/workflows/dependabot-dispatch.yml`

#### Scenario: infrastructure covers them
- **WHEN** infrastructure's `github-actions` entry is read
- **THEN** it leaves out nothing

#### Scenario: A newly delivered workflow is left out too
- **WHEN** a workflow is added to the guard's delivered files
- **THEN** troupe's and website's generated `github-actions` entries leave it out, with no other edit

#### Scenario: Dependabot proposes no change to a delivered workflow
- **WHEN** an action pinned in a delivered workflow has a newer release, older than the cooldown
- **THEN** no Dependabot pull request in troupe or website changes that delivered workflow
