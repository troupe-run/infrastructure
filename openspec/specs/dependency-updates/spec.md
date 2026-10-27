# dependency-updates Specification

## Purpose
How Dependabot keeps each managed repository's dependencies up to date. One policy is declared in this repository,
and each repository's `.github/dependabot.yml` is generated from it and delivered by the App.

## Requirements

### Requirement: Each repository's Dependabot configuration is generated from one policy
Each managed repository with at least one declared Dependabot ecosystem SHALL get a `.github/dependabot.yml`. It SHALL
be generated from the shared policy and that repository's declared ecosystems, with one update entry per ecosystem.
A repository with no declared ecosystem SHALL get no file. The policy, the ecosystems and their labels SHALL each be
declared in one place.

#### Scenario: Each repository gets its ecosystems
- **WHEN** the generated configurations are read
- **THEN** troupe's has entries for `uv` and `github-actions`, website's for `npm` and `github-actions`, and
  infrastructure's for `uv` and `github-actions`, and each entry's directory is the policy's directory for that
  ecosystem

#### Scenario: A repository with no dependencies
- **WHEN** the generated configurations are read
- **THEN** there is none for `.github`

#### Scenario: An ecosystem with no declared directory
- **WHEN** a repository's declared ecosystems name one that the policy gives no directory
- **THEN** `scripts/check.py` fails, naming the repository and the ecosystem

### Requirement: Version updates run weekly, after a cooldown
Every update entry SHALL run version updates weekly, on the policy's day and time. Each SHALL wait the policy's
cooldown before proposing a release: the policy's patch, minor and major days where the ecosystem supports them, and
its default days otherwise. Each update SHALL be its own pull request, with no grouping, and the open pull request
limit SHALL be Dependabot's default. Security updates SHALL keep running, unaffected by the cooldown.

#### Scenario: The schedule is the same everywhere
- **WHEN** every generated configuration's entries are read
- **THEN** each has a weekly interval with the policy's day, time and timezone, and none has `groups` or
  `open-pull-requests-limit`

#### Scenario: Cooldown by kind of release
- **WHEN** the `npm` and `uv` entries are read
- **THEN** each has the policy's patch, minor and major cooldown days, the major one the longest

#### Scenario: Cooldown where an ecosystem has no release kinds
- **WHEN** a `github-actions` entry is read
- **THEN** it has the policy's default cooldown days and no patch, minor or major days

#### Scenario: A scheduled run opens version updates
- **WHEN** Dependabot's scheduled run finds a newer release of a dependency, older than the cooldown
- **THEN** it opens one pull request for that dependency's update

### Requirement: Dependabot's pull requests are Conventional and carry only declared labels
Each update entry SHALL set the commit prefix `chore` with the dependency scope, so a pull request's title and commit
read `chore(deps): …` or `chore(deps-dev): …`. Each entry SHALL set its labels to `dependencies` and its ecosystem's
declared label, both taken from the declared Dependabot labels. Dependabot's own default labels SHALL NOT be used.

#### Scenario: A version update's title
- **WHEN** Dependabot opens a version update pull request in a managed repository
- **THEN** its title starts with `chore(deps):` or `chore(deps-dev):`

#### Scenario: A version update's labels
- **WHEN** Dependabot opens a pull request from the `github-actions` entry in troupe
- **THEN** its labels are exactly `dependencies` and `github_actions`, both declared in this repository

#### Scenario: Labels follow the declaration
- **WHEN** the generated configurations are read
- **THEN** every label in every entry is the name of a label declared for that repository's Dependabot ecosystems

### Requirement: The App delivers each repository's configuration
The infrastructure App SHALL commit each generated `.github/dependabot.yml` to its repository's `main`, this
repository included, without a pull request, in a Conventional Commit naming the file and its content. A difference
from the generated content SHALL appear in the plan, and an apply SHALL restore it. A plan where nothing changed
SHALL deliver nothing.

#### Scenario: Every repository with ecosystems holds its file
- **WHEN** the managed state is read after an apply
- **THEN** troupe, website and infrastructure each hold `.github/dependabot.yml` with its generated content, and
  `.github` holds none

#### Scenario: A hand edit shows as drift
- **WHEN** someone changes `.github/dependabot.yml` on `main` in any of the three repositories
- **THEN** the next plan shows the file returning to its generated content, and applying it restores that content

#### Scenario: Nothing changed
- **WHEN** a plan runs and neither the policy, the ecosystems nor the labels have changed since the last delivery
- **THEN** the plan shows no change to any `.github/dependabot.yml`

#### Scenario: The file says where it comes from
- **WHEN** someone opens `.github/dependabot.yml` in any of the three repositories
- **THEN** its opening lines say it is generated in `troupe-run/infrastructure` and is changed there

### Requirement: The file is changed only at its source in a repository that receives the guard
In each repository that receives the guard, `.github/dependabot.yml` SHALL be named in the delivered list, so the
delivered-file rule applies to it as to the guard's files.

#### Scenario: Committing a change to it in troupe
- **WHEN** a contributor in troupe commits a change to `.github/dependabot.yml`
- **THEN** the commit is refused, naming the rule and saying to change it in `troupe-run/infrastructure`

#### Scenario: The delivered list names it
- **WHEN** troupe's or website's `.github/guard-delivery.json` is read
- **THEN** it lists `.github/dependabot.yml`

### Requirement: Delivered workflows are updated only at their source
In each repository that receives the guard, the `github-actions` entry SHALL leave out every workflow the guard
delivers there, so Dependabot proposes no change to a delivered file. In this repository, which is their source, the
entry SHALL cover them. The list left out SHALL be taken from the guard's delivered files.

#### Scenario: troupe leaves out the delivered workflows
- **WHEN** troupe's `github-actions` entry is read
- **THEN** it leaves out `.github/workflows/guard.yml` and `.github/workflows/claude-review.yml`

#### Scenario: infrastructure covers them
- **WHEN** infrastructure's `github-actions` entry is read
- **THEN** it leaves out nothing

#### Scenario: A newly delivered workflow is left out too
- **WHEN** a workflow is added to the guard's delivered files
- **THEN** troupe's and website's generated `github-actions` entries leave it out, with no other edit

#### Scenario: Dependabot proposes no change to a delivered workflow
- **WHEN** an action pinned in a delivered workflow has a newer release, older than the cooldown
- **THEN** no Dependabot pull request in troupe or website changes that delivered workflow

### Requirement: OpenTofu provider updates are covered or recorded as manual
infrastructure SHALL have an `opentofu` entry for its provider lockfile when Dependabot is shown to update a lockfile
whose providers come from `registry.opentofu.org`. Its label SHALL be declared like the other ecosystems' labels.
If Dependabot isn't shown to, there SHALL be no such entry, and the docs SHALL say provider updates are manual.

#### Scenario: Provider updates, when Dependabot supports them
- **WHEN** a throwaway repository shows that Dependabot's `opentofu` updates open a pull request that changes
  `.terraform.lock.hcl` for a `registry.opentofu.org` provider
- **THEN** infrastructure's generated configuration has an `opentofu` entry for `/tofu`, with a declared label

#### Scenario: Provider updates, when it doesn't
- **WHEN** the throwaway repository shows no such pull request
- **THEN** infrastructure's generated configuration has no `opentofu` entry, and `docs/development-workflow.md` says
  provider updates are made by hand

### Requirement: Every Dependabot pull request has its issue
Every open pull request by `dependabot[bot]` in troupe, website or infrastructure SHALL have an issue, opened in the
same repository by the Dependabot issues App. The issue SHALL be of type Task, carry the `dependencies` label, have
the release in progress as its milestone, and be on the troupe roadmap board. One issue SHALL serve one pull request
at a time.

#### Scenario: A new Dependabot pull request
- **WHEN** Dependabot opens a pull request in website and the next run of `dependabot-issues` ends
- **THEN** website has an open issue for it, of type Task, labelled `dependencies`, in the release in progress, and on
  the troupe roadmap board

#### Scenario: A run finds nothing new
- **WHEN** every open Dependabot pull request already has its issue and its closing line
- **THEN** the run opens, edits and comments on nothing

#### Scenario: Pull requests open before the workflow
- **WHEN** the first run happens while website #44, #45 and #46 are open
- **THEN** each of the three gets its own issue in website

### Requirement: A Dependabot pull request closes its issue
Each open Dependabot pull request's description SHALL contain the line `Closes #<n>`, where `#<n>` is its issue. A run
that finds the line missing, whether never added or removed when Dependabot rewrote the description, SHALL add it
and leave the rest of the description as it was.

#### Scenario: The line is added
- **WHEN** a run opens an issue for a Dependabot pull request
- **THEN** the pull request's description ends with `Closes #<n>` for that issue, and the `guard` check runs again on
  the edit

#### Scenario: Dependabot rewrites the description
- **WHEN** Dependabot rebases or updates its pull request and its new description has no closing line
- **THEN** the next run puts `Closes #<n>` back, naming the same issue

#### Scenario: Merging closes the issue
- **WHEN** a Dependabot pull request with its closing line is merged into `main`
- **THEN** GitHub closes its issue as completed

### Requirement: The issue says what the update is
The issue's title SHALL name the dependency and the versions it moves between. Its body SHALL link the pull request,
whose description carries Dependabot's release notes, and give the update type: patch, minor, major, or unknown when
the versions can't be read. For a major or unknown update, the body SHALL say the update needs an OpenSpec change.

#### Scenario: A patch update
- **WHEN** a run opens the issue for website's `chore(deps): Bump zod from 4.6.5 to 4.6.7`
- **THEN** its title names zod, 4.6.5 and 4.6.7, and its body links the pull request and says the update is a patch

#### Scenario: A major update
- **WHEN** a run opens the issue for `chore(deps-dev): Bump typescript from 6.0.3 to 7.0.2`
- **THEN** its body says the update is major and needs an OpenSpec change before it can merge

#### Scenario: Versions that can't be read
- **WHEN** a Dependabot pull request's title doesn't give a version it moves from and one it moves to
- **THEN** its issue is still opened, titled from the pull request's title, and its body says the update type is
  unknown and needs an OpenSpec change

### Requirement: The release in progress is the lowest open milestone
The release in progress SHALL be the open milestone in `tofu/milestones.json` on infrastructure's `main` whose title
is the lowest version. It SHALL be found in each repository by that title. Where it isn't found, the run SHALL open
no issue in that repository, and SHALL fail, naming the repository and the title.

#### Scenario: Today's milestones
- **WHEN** a run opens an issue while `0.1.0` is the lowest open milestone declared
- **THEN** the issue's milestone is `0.1.0`

#### Scenario: The milestone is missing in a repository
- **WHEN** the declared title isn't a milestone in troupe
- **THEN** the run opens no issue in troupe, still handles website and infrastructure, and fails naming troupe and
  the title

### Requirement: A superseded update reuses its issue
When Dependabot opens a pull request for a dependency, in the same repository, ecosystem and directory, whose issue is
still open, the run SHALL relink that issue instead of opening another. It SHALL point the issue at the new pull
request, retitle it with the new versions, and comment naming both pull requests.

#### Scenario: Dependabot supersedes an update
- **WHEN** Dependabot closes website #44 (zod 4.6.5 → 4.6.7) and opens a pull request for zod 4.6.5 → 4.6.8
- **THEN** the issue opened for #44 is retitled for 4.6.8, links the new pull request, has a comment naming both, and
  the new pull request's description closes it; no second zod issue is opened

#### Scenario: The same name in another ecosystem
- **WHEN** an open issue is for an `npm` dependency and Dependabot opens a `github-actions` pull request with the same
  name
- **THEN** the run opens a new issue for it

### Requirement: An update closed without merging closes its issue as not planned
When a Dependabot pull request linked to an open issue is closed without merging, and an hour later no open
Dependabot pull request for the same dependency exists, the run SHALL close the issue as not planned with a comment
naming the pull request. A reopened pull request SHALL reopen an issue closed as not planned; an issue closed as
completed SHALL stay closed.

#### Scenario: Dependabot gives up on an update
- **WHEN** a Dependabot pull request is closed without merging, and no successor opens within the hour
- **THEN** the next run after the hour closes its issue as not planned, with a comment naming the pull request

#### Scenario: Waiting for a successor
- **WHEN** a run happens less than an hour after a Dependabot pull request closed without merging
- **THEN** its issue stays open

#### Scenario: A pull request is reopened
- **WHEN** a Dependabot pull request whose issue was closed as not planned is reopened
- **THEN** the next run reopens the issue, and the pull request's description closes it

#### Scenario: A change took the update over
- **WHEN** a change's pull request that closes the issue merges, while Dependabot's pull request is still open
- **THEN** the issue stays closed as completed, and no new issue is opened for Dependabot's pull request

#### Scenario: Merged while the issue stays open
- **WHEN** a Dependabot pull request is merged and its issue is still open
- **THEN** the next run closes the issue as completed, with a comment naming the pull request

### Requirement: Only Dependabot's pull requests and the App's own issues are trusted
A run SHALL act only on pull requests whose author is `dependabot[bot]`, whatever their branch is named. It SHALL
treat as a pull request's issue only an issue the Dependabot issues App opened. An issue or line written by anyone else
SHALL neither be reused nor closed.

#### Scenario: A person's branch named like Dependabot's
- **WHEN** a person opens a pull request from a branch named `dependabot/npm_and_yarn/zod-4.6.8`
- **THEN** the run opens no issue for it and doesn't edit it

#### Scenario: An issue someone else wrote
- **WHEN** a person opens an issue labelled `dependencies` titled for the same dependency as a Dependabot pull request
  without one
- **THEN** the run opens the App's own issue for the pull request and leaves the person's issue as it is

#### Scenario: A closing line to someone else's issue
- **WHEN** a Dependabot pull request's description closes an issue the App didn't open
- **THEN** the run still opens the App's issue for it and adds its own closing line

### Requirement: The workflow never runs the pull requests' code
`dependabot-issues` SHALL run from infrastructure's `main` only, on a schedule every 10 minutes and by hand. It SHALL
check out only infrastructure's `main`, and read the pull requests through the API: their author, number, branch,
title, state and description. It SHALL NOT check out, fetch or run any file of a pull request.

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

### Requirement: A run that can't read what it needs fails without guessing
A run SHALL fail, naming what it couldn't read, when a pull request list, an issue, the milestone declaration or a
response is missing or malformed. It SHALL act on nothing that depended on what it couldn't read.

#### Scenario: A repository's pull requests can't be listed
- **WHEN** listing website's pull requests fails
- **THEN** the run changes nothing in website, still handles troupe and infrastructure, and fails naming website

#### Scenario: An issue whose marker was edited away
- **WHEN** someone edits one of the App's issues in website and removes the line that says which pull request it
  tracks
- **THEN** the run leaves that issue alone, and any Dependabot pull request whose description closes it, still
  handles every other pull request and issue in website, and fails naming the issue and how to restore the line

#### Scenario: A malformed milestone declaration
- **WHEN** `tofu/milestones.json` has no open milestone
- **THEN** the run opens no issue anywhere and fails, saying there is no release in progress

### Requirement: Outside GitHub Actions the run only reads
Run anywhere but GitHub Actions, the script SHALL read the same pull requests and issues and print what it would do,
and SHALL open, edit, comment on and close nothing.

#### Scenario: Run on a laptop
- **WHEN** the owner runs the script locally while a Dependabot pull request has no issue
- **THEN** it prints that it would open an issue for that pull request, and nothing changes on GitHub

### Requirement: Only Dependabot creates or updates its branches
Each repository that gets a `.github/dependabot.yml` SHALL have a ruleset that refuses creating and updating any
branch whose name starts with `dependabot/` to everyone but Dependabot, with no bypass for org owners. It SHALL NOT
refuse Dependabot's force-push, since Dependabot rewrites its branch when it rebases, and SHALL NOT refuse deletion,
so delete-on-merge removes the branch. A change to the ruleset on GitHub SHALL show in the next plan.

#### Scenario: Every repository with a configuration has the ruleset
- **WHEN** the declared rulesets are read
- **THEN** troupe, website and infrastructure each have one covering `refs/heads/dependabot/**/*`, refusing creation
  and update, whose only bypass actor is Dependabot, and `.github` has none

#### Scenario: An owner creates a Dependabot branch
- **WHEN** an org owner pushes a new branch named `dependabot/npm_and_yarn/anything` to website
- **THEN** GitHub refuses the push

#### Scenario: An owner writes to a Dependabot branch
- **WHEN** an org owner pushes a commit to an existing Dependabot branch, or uses "Update branch" on its pull
  request
- **THEN** GitHub refuses it, and the branch is unchanged

#### Scenario: Dependabot opens and rebases its pull requests
- **WHEN** Dependabot opens a pull request for an update, and later rebases it when asked with `@dependabot rebase`
- **THEN** GitHub allows both the new branch and the force-push

#### Scenario: A merged Dependabot pull request
- **WHEN** a Dependabot pull request is merged, with delete-on-merge on
- **THEN** GitHub deletes its branch

#### Scenario: The ruleset is changed on GitHub
- **WHEN** someone adds a bypass actor to a repository's Dependabot ruleset on GitHub
- **THEN** the next plan shows the ruleset returning to its declared bypass actors
