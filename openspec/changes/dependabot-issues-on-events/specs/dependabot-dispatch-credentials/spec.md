# Spec Delta

## Purpose

Declares the credential troupe and website use to start infrastructure's `dependabot-issues` workflow when Dependabot
acts in them: the `troupe-run-dispatch` App's installation on infrastructure only, the main-only `dependabot-dispatch`
environments in troupe and website that hold its key, and the variable that names the App.

## ADDED Requirements

### Requirement: The dispatch App is narrow and installed on infrastructure only
The App `troupe-run-dispatch` SHALL have only these repository permissions: actions read/write, and metadata read. It
SHALL have no organisation permission. Its installation SHALL select repositories, and SHALL cover
`troupe-run/infrastructure` only. Its permissions and repository selection SHALL be checked by the drift check, and
its repository list by hand (spec: teams-and-access).

#### Scenario: The dispatch App gains a permission
- **WHEN** the App's installation gains a permission on GitHub, such as issues write, without the declaration changing
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: The dispatch App is switched to all repositories
- **WHEN** the App's installation is changed to all repositories
- **THEN** the drift check reports it and exits non-zero

#### Scenario: The dispatch App gains a repository
- **WHEN** a repository other than infrastructure, such as troupe, is added to the App's installation
- **THEN** the next hand check of its repository list, made by any change that depends on it, finds it, and it's
  removed or the declaration is changed in a pull request

#### Scenario: The declared dispatch App matches
- **WHEN** the App has exactly the declared permissions and repository selection
- **THEN** the drift check reports no difference for it

### Requirement: The dispatch App's token starts infrastructure workflows and writes nothing else
A token minted for the dispatch App SHALL be able to start a `workflow_dispatch` run of a workflow in
troupe-run/infrastructure. It SHALL NOT be able to write infrastructure's contents, issues or pull requests, or act in
any other repository.

#### Scenario: Starting dependabot-issues
- **WHEN** a troupe workflow mints the dispatch App's token and creates a `workflow_dispatch` event for
  infrastructure's `dependabot-issues.yml` on `main`
- **THEN** GitHub starts a run of that workflow

#### Scenario: Writing infrastructure's contents or issues
- **WHEN** the same token is used to create a branch or a file, or open an issue, in troupe-run/infrastructure
- **THEN** GitHub refuses it with 403, and nothing in the repository changes

#### Scenario: Acting in another repository
- **WHEN** the same token is used to start a workflow in troupe or website
- **THEN** GitHub refuses it

### Requirement: The dispatch key is readable from main only
troupe-run/troupe and troupe-run/website SHALL each have an environment named `dependabot-dispatch` whose deployment
branches are limited to `main`, and which no admin can bypass. The App's private key SHALL be held only as those
environments' secret `DISPATCH_APP_PRIVATE_KEY`, so a run on any other branch, or in another repository, can't read it.

#### Scenario: A run on another branch asks for the environment
- **WHEN** a workflow run in troupe or website on a branch other than `main` uses the `dependabot-dispatch` environment
- **THEN** GitHub refuses the deployment, and the run gets no secret from it

#### Scenario: A Dependabot pull request's workflows
- **WHEN** a workflow runs on a Dependabot pull request's `pull_request` or `push` event in troupe or website
- **THEN** it can't read `DISPATCH_APP_PRIVATE_KEY`

#### Scenario: The branch policy is changed by hand
- **WHEN** someone widens either `dependabot-dispatch` environment's deployment branches, or allows admins to bypass
  them, on GitHub
- **THEN** the next plan shows the change being reverted

#### Scenario: Removing or weakening the declaration fails the check
- **WHEN** a change deletes either `dependabot-dispatch` environment's declaration, lets it deploy from a branch other
  than `main`, or lets admins bypass it
- **THEN** `scripts/check.py` fails, naming the repository, the environment and what changed, before any plan is made

### Requirement: The dispatch key's value never passes through this repository
OpenTofu SHALL NOT hold or set the value of `DISPATCH_APP_PRIVATE_KEY` in any repository. The owner SHALL set it from
the password manager with a documented command that prints nothing. Checking that it's set SHALL read its name only.

#### Scenario: The key is set
- **WHEN** the owner has run the documented command for troupe and for website
- **THEN** listing each `dependabot-dispatch` environment's secrets shows `DISPATCH_APP_PRIVATE_KEY` by name, and no
  value appears in the repository, the state, a plan or a log

#### Scenario: A plan runs
- **WHEN** a plan runs with the dispatch declarations in place
- **THEN** it neither creates, changes nor deletes `DISPATCH_APP_PRIVATE_KEY`

### Requirement: The dispatch App's client ID is declared as a repository variable
troupe-run/troupe and troupe-run/website SHALL each have the repository variable `DISPATCH_APP_CLIENT_ID`, holding the
dispatch App's client ID, declared once in this repository. A different value on GitHub, or the variable's removal,
SHALL show in the next plan.

#### Scenario: The variable is changed by hand
- **WHEN** someone changes `DISPATCH_APP_CLIENT_ID` on troupe or website on GitHub
- **THEN** the next plan shows it changing back to the declared client ID

#### Scenario: The variable is deleted by hand
- **WHEN** someone deletes `DISPATCH_APP_CLIENT_ID` from troupe or website
- **THEN** the next plan shows it being created with the declared client ID

### Requirement: The dispatch App bypasses no ruleset
The dispatch App SHALL NOT be a bypass actor on any ruleset. It writes nothing to a repository's contents.

#### Scenario: Rulesets after the change
- **WHEN** a plan runs with the dispatch declarations in place
- **THEN** no ruleset's bypass actors change
