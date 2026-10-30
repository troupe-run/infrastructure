## MODIFIED Requirements

### Requirement: Every Dependabot pull request has its issue
Every open pull request by `dependabot[bot]` in troupe, website or infrastructure SHALL have an issue, opened in the
same repository by the Dependabot issues App. The issue SHALL be of type Task, carry the `dependencies` label, and be
on the troupe roadmap board. It SHALL have the release in progress as its milestone when its pull request is a security
update, and no milestone otherwise. One issue SHALL serve one pull request at a time.

#### Scenario: A new Dependabot pull request
- **WHEN** Dependabot opens a version update in website and the next run of `dependabot-issues` ends
- **THEN** website has an open issue for it, of type Task, labelled `dependencies`, with no milestone, and on the
  troupe roadmap board

#### Scenario: A new security update
- **WHEN** Dependabot opens a security update in website and the next run of `dependabot-issues` ends
- **THEN** website has an open issue for it, of type Task, labelled `dependencies`, in the release in progress, and on
  the troupe roadmap board

#### Scenario: A run finds nothing new
- **WHEN** every open Dependabot pull request already has its issue and its closing line
- **THEN** the run opens, edits and comments on nothing

#### Scenario: Pull requests open before the workflow
- **WHEN** the first run happens while website #44, #45 and #46 are open
- **THEN** each of the three gets its own issue in website

### Requirement: The release in progress is the lowest open milestone
The release in progress SHALL be the open milestone in `tofu/milestones.json` on infrastructure's `main` whose title
is the lowest version. It SHALL be found in each repository by that title. Where it isn't found, the run SHALL open
no issue in that repository, and SHALL fail, naming the repository and the title.

#### Scenario: Today's milestones
- **WHEN** a run opens the issue for a security update while `0.1.0` is the lowest open milestone declared
- **THEN** the issue's milestone is `0.1.0`

#### Scenario: The milestone is missing in a repository
- **WHEN** the declared title isn't a milestone in troupe
- **THEN** the run opens no issue in troupe, still handles website and infrastructure, and fails naming troupe and
  the title

## ADDED Requirements

### Requirement: A security update is told by the repository's open alerts
A Dependabot pull request SHALL count as a security update when its repository has an open Dependabot alert for the
same ecosystem and package whose first patched version is at or below the version the pull request moves to, or when
that alert has a patched version and the pull request's version can't be read. Any other pull request SHALL count as a
version update, whatever its branch, labels or title say.

#### Scenario: A pull request that fixes an open alert
- **WHEN** website has an open alert for npm's `zod` first patched in `4.6.6`, and Dependabot opens `Bump zod from
  4.6.5 to 4.6.7`
- **THEN** the run counts the pull request as a security update

#### Scenario: A version update for a package with no alert
- **WHEN** Dependabot opens `Bump typescript from 6.0.3 to 7.0.2` in website, and website has no open alert for
  `typescript`
- **THEN** the run counts the pull request as a version update

#### Scenario: An alert that's already fixed
- **WHEN** website's only alerts for npm's `undici` are fixed or dismissed, and Dependabot opens a pull request for
  `undici`
- **THEN** the run counts the pull request as a version update

#### Scenario: A pull request that stops short of the fix
- **WHEN** website has an open alert for `fast-uri` first patched in `3.1.9`, and Dependabot opens `Bump fast-uri from
  3.1.7 to 3.1.8`
- **THEN** the run counts the pull request as a version update

#### Scenario: The same name in another ecosystem
- **WHEN** a repository has an open npm alert for a package, and Dependabot opens a `github-actions` pull request with
  the same name
- **THEN** the run counts the pull request as a version update

#### Scenario: A version that can't be read
- **WHEN** a repository has an open alert with a patched version for a package, and Dependabot's pull request for it
  gives no version the run can read
- **THEN** the run counts the pull request as a security update

#### Scenario: A title that names no package
- **WHEN** Dependabot's pull request title can't be read for a package, such as `Bump the npm group with 3 updates`
- **THEN** the run counts it as a security update while the repository has any open alert with a patched version, and
  as a version update otherwise

### Requirement: A run that can't read a repository's alerts opens no issue there
A run SHALL read each repository's open Dependabot alerts before opening or relinking any issue in it. When the alerts
can't be read, or a pull request's ecosystem has no known alert ecosystem, the run SHALL open and relink no issue that
depended on it, still handle the other repositories, and fail, naming the repository and what it couldn't read.

#### Scenario: The alerts can't be read
- **WHEN** reading website's Dependabot alerts fails, as it would if the App lost its alerts permission
- **THEN** the run opens and relinks no issue in website, still handles troupe and infrastructure, and fails naming
  website and its alerts

#### Scenario: An ecosystem with no known alert ecosystem
- **WHEN** a Dependabot pull request's branch names an ecosystem the run can't map to an alert ecosystem
- **THEN** the run opens no issue for that pull request and fails, naming the ecosystem and where to add it

### Requirement: A run never takes a milestone off an issue
A run SHALL set a milestone only when it opens an issue, or when it relinks an issue that has no milestone to a
security update. It SHALL NOT remove or change a milestone an issue already has, whoever set it.

#### Scenario: A security update supersedes a version update
- **WHEN** an open issue with no milestone is relinked to a new pull request that is a security update
- **THEN** the issue's milestone becomes the release in progress

#### Scenario: A version update supersedes a security update
- **WHEN** an open issue in `0.1.0` is relinked to a new pull request that is a version update
- **THEN** the issue stays in `0.1.0`

#### Scenario: A milestone set by hand
- **WHEN** someone puts a version update's issue in `0.2.0`, and a later run handles its pull request
- **THEN** the issue stays in `0.2.0`
