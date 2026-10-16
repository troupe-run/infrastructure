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
