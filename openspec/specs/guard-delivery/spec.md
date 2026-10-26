# guard-delivery Specification

## Purpose
How the guard reaches the repositories it governs. This repository is the single source of the guard's files, the
infrastructure App delivers them, a difference in a governed repository shows as drift, and a delivered file is
changed only at its source.

## Requirements

### Requirement: This repository is the source of the guard's delivered files
Each repository that receives the guard SHALL hold copies of the guard's files whose source is this repository. A
difference between a delivered file and its source SHALL appear in the plan, and an apply SHALL restore the source
content.

#### Scenario: A delivered file edited in a governed repository shows as drift
- **WHEN** someone changes `scripts/guard.py` in `troupe` directly
- **THEN** the next plan shows the file returning to its source content, and applying it restores that content

#### Scenario: A governed repository receives every delivered file
- **WHEN** the managed state is read after an apply
- **THEN** each governed repository other than this one has each delivered file, with the content of its source

### Requirement: The App delivers the guard straight to main
A delivery SHALL be committed to the governed repository's `main` by the infrastructure App, without a pull request.
Each delivery commit SHALL be a Conventional Commit naming the file and the content it delivers. A plan in which no
source changed SHALL deliver nothing.

#### Scenario: A delivery commit names what it delivers
- **WHEN** a changed source is applied
- **THEN** the governed repository's `main` gains a commit by the App whose message is a Conventional Commit naming
  the file and identifying its new content

#### Scenario: Nothing to deliver
- **WHEN** a plan runs and no delivered file's source has changed since the last delivery
- **THEN** the plan shows no change to any delivered file, and no governed repository gets a commit

### Requirement: Delivered files say where they come from
Each delivered file that can hold a comment SHALL carry a note naming this repository as its source and saying to
change it there. Each governed repository SHALL hold a delivered list of the files that are delivered to it.

#### Scenario: A delivered script names its source
- **WHEN** someone opens `scripts/guard.py` in `troupe`
- **THEN** its opening lines say it is delivered from `troupe-run/infrastructure` and is changed there

#### Scenario: The delivered files are listed
- **WHEN** a governed repository's delivered list is read
- **THEN** it names every file delivered to that repository, including itself

### Requirement: Delivered files are changed only at their source
In a governed repository that receives delivered files, a commit or an agent's edit that changes a delivered file
SHALL be refused, and the guard's GitHub check SHALL fail on such a commit unless its author is the App. That check
catches mistakes, not forgery. A change that gets past these, by any route, is drift: a plan of `main` SHALL show it
within a day, and an apply SHALL restore the file. The fix SHALL be to change the file in this repository.

#### Scenario: Committing a change to a delivered file
- **WHEN** a contributor in `troupe` commits a change to `.githooks/pre-commit`
- **THEN** the commit is refused, naming the rule and saying to change the file in `troupe-run/infrastructure`

#### Scenario: An agent edits a delivered file
- **WHEN** an agent in a Claude Code session in `troupe` edits `scripts/guard.py`
- **THEN** the edit is refused, naming the rule and the source repository

#### Scenario: A pushed change to a delivered file
- **WHEN** a branch is pushed to `troupe` carrying a commit, not made by the App, that changes a delivered file
- **THEN** the guard's GitHub check for that push fails and names the commit and the file

#### Scenario: A forged delivery author shows within a day
- **WHEN** a commit that changes a delivered file, with the App's bot email written in as its author, reaches
  `troupe`'s `main`
- **THEN** a plan of `main` within a day shows the file returning to its source content, and applying it restores
  that content

#### Scenario: A delivery passes the check
- **WHEN** the App's delivery commit is pushed to `troupe`'s `main`
- **THEN** the guard's GitHub check passes

#### Scenario: The source repository edits its own files
- **WHEN** a contributor in this repository commits a change to `scripts/guard.py` on a change's branch
- **THEN** this rule does not apply

### Requirement: A delivered file has its source's mode
Each delivered file SHALL have its source's file mode in every governed repository, so a hook that is executable here
is executable there. A difference SHALL appear in the plan as a pending change, for the owner's approval like any
other. After the approved apply, the infrastructure App SHALL set the mode on `main` in a Conventional Commit naming
each file. A plan with no difference SHALL set nothing.

#### Scenario: A hook delivered without its mode shows in the plan
- **WHEN** `main` is planned while `website` holds `.githooks/pre-push` as non-executable and its source is executable
- **THEN** the plan names `website` and `.githooks/pre-push` as a mode to set, and the run waits for the owner's
  approval even when OpenTofu has no other change

#### Scenario: The approved apply sets the mode
- **WHEN** the owner approves that plan and the apply succeeds
- **THEN** `website`'s `main` gains one commit by the App, a Conventional Commit naming each file whose mode it set,
  and each of those files now has its source's mode with unchanged content

#### Scenario: A repository newly added to the targets gets executable hooks
- **WHEN** an apply delivers the guard to a repository for the first time
- **THEN** after that apply, its delivered hooks are executable, without a second plan

#### Scenario: Modes that already match set nothing
- **WHEN** a plan runs and every delivered file in every target has its source's mode
- **THEN** the plan shows no mode to set, and no governed repository gets a commit for modes

#### Scenario: A mode changed in a governed repository shows within a day
- **WHEN** a delivered hook in `troupe` stops being executable on `main` by any route
- **THEN** the daily plan shows the mode to set, and applying it restores the source's mode

#### Scenario: A file changed since the plan isn't touched
- **WHEN** a delivered file's content in a target differs at apply time from what the plan read
- **THEN** its mode isn't set, the apply's run fails naming the repository and the file, and the next plan reads it
  again

### Requirement: The guard is delivered to troupe and the website
The guard SHALL be delivered to `troupe` and `website`, and to no other repository. This repository is governed too,
as the guard's source. The list of repositories that receive it SHALL be declared in one place.

#### Scenario: Both governed repositories receive the guard
- **WHEN** the managed state is read after an apply
- **THEN** `troupe` and `website` each hold every delivered file with its source content, and no other repository
  holds any

#### Scenario: The website's delivered list names its files
- **WHEN** the website's `.github/guard-delivery.json` is read
- **THEN** it names this repository as the source and lists exactly the files delivered to it

### Requirement: A repository receives the guard only once it can run it
A repository SHALL be added to the guard's targets only after its `main` holds what the guard needs to run there: an
`openspec/` directory, a `scripts/check.py` that runs its checks, and contributor docs that say what to install. None
of the delivered files SHALL already exist in it.

#### Scenario: The website's first commit after delivery is checked
- **WHEN** the guard has been delivered to the website and a contributor commits on a branch named after an OpenSpec
  change in it
- **THEN** the commit hook runs the website's `scripts/check.py` and allows the commit only if it passes

#### Scenario: A delivery never overwrites a file the repository wrote
- **WHEN** a plan adds a repository to the guard's targets and that repository already has a file at a delivered
  path
- **THEN** the apply fails for that file rather than replacing it, and the owner resolves it in the repository first

### Requirement: The delivered guard check takes Node from the repository's .nvmrc
The `guard` workflow SHALL set up Node from the `.nvmrc` of the repository it runs in, when that repository has one,
and from the workflow's own pinned version only when it hasn't. No step of the workflow SHALL name a Node version as
an input, and the workflow SHALL NOT change or commit a repository's `.nvmrc`. The pin SHALL be declared in one place
in the workflow.

#### Scenario: A repository that keeps its Node version in .nvmrc
- **WHEN** the `guard` check runs in `website`, whose `.nvmrc` says `22`
- **THEN** it installs the OpenSpec CLI on Node 22, read from that `.nvmrc`

#### Scenario: A repository with no .nvmrc
- **WHEN** the `guard` check runs in `troupe` or this repository, neither of which has an `.nvmrc`
- **THEN** it installs the OpenSpec CLI on the workflow's pinned Node version, and the run's commits are unchanged

#### Scenario: The delivered workflow passes a rule against workflow-named Node versions
- **WHEN** a check reads every step of the delivered `.github/workflows/guard.yml`, ignoring each step's `if:`
- **THEN** every `actions/setup-node` step has `node-version-file: .nvmrc` and no `node-version` input, and no other
  step has a `node-version` input

#### Scenario: A change here that names a Node version again
- **WHEN** a commit in this repository gives a step of `.github/workflows/guard.yml` a `node-version` input
- **THEN** this repository's tests fail, naming the step, before the file can be delivered
