## MODIFIED Requirements

### Requirement: The rules are re-checked on GitHub
For every push to any branch and for every pull request, a GitHub check SHALL re-apply the git-level rules to the
commits involved: every commit message is a Conventional Commit, the branch matches an OpenSpec change (for any
branch other than `main`, except an exempt release or Dependabot branch in a repository that reserves its name for
its bot), and no archived change has an unticked task. It applies the same rules as the git hooks, so a commit that
skipped the local hooks is still caught.

#### Scenario: A push that skipped the local hooks
- **WHEN** a branch is pushed carrying a commit with a non-conventional message that was made with `--no-verify`
- **THEN** the GitHub check for that push fails and names the commit

#### Scenario: A schema change that skipped the local hooks
- **WHEN** a pull request carries a commit made with `--no-verify` that changes a file under `protocol/schemas/` with
  the message `test: cover the schema`
- **THEN** the GitHub check fails under `schema-commit-type`, naming the commit and its schema files

#### Scenario: A pull request from a branch with no matching change
- **WHEN** a pull request's branch has no matching OpenSpec change
- **THEN** the GitHub check fails and names the rule

#### Scenario: A Dependabot pull request in a governed repository
- **WHEN** a pull request in `troupe-run/troupe`, `troupe-run/infrastructure` or `troupe-run/website` comes from a
  branch named `dependabot/<ecosystem>/<package>-<version>`, which has no matching OpenSpec change
- **THEN** the GitHub check fails on the branch-change rule unless the branch is an exempt Dependabot branch

## ADDED Requirements

### Requirement: A minor or patch Dependabot branch passes the branch rule where GitHub reserves its name
The GitHub check SHALL exempt a branch from the branch-change rule when its name has Dependabot's shape,
`dependabot/<ecosystem>/<name>`, it lives in a repository (a pull request's head repository) whose ruleset lets only Dependabot create or update those branches,
it changes only dependency files, and it is a single minor or patch update. Who authored its commits SHALL NOT
matter. Elsewhere, or with no repository named, no Dependabot branch SHALL be exempt. Every other rule SHALL still
apply.

#### Scenario: A patch update in website
- **WHEN** a pull request in `troupe-run/website` from `dependabot/npm_and_yarn/zod-4.6.7`, closing its issue, carries
  one commit `chore(deps): Bump zod from 4.6.5 to 4.6.7` that changes only `package-lock.json`
- **THEN** the GitHub check passes

#### Scenario: A minor update with its manifest
- **WHEN** a pull request in `troupe-run/website` from `dependabot/npm_and_yarn/axe-core/playwright-4.14.0` carries
  one commit `chore(deps-dev): Bump @axe-core/playwright from 4.13.0 to 4.14.0`, with `update-type:
  version-update:semver-minor`, that changes `package.json` and `package-lock.json`
- **THEN** the GitHub check doesn't fail on the branch-change rule

#### Scenario: A push to a Dependabot branch
- **WHEN** Dependabot pushes `dependabot/uv/eventsourcing-9.5.6` to `troupe-run/troupe`, its commit a patch update
  changing only `pyproject.toml` files and `uv.lock`
- **THEN** the GitHub check for the push doesn't fail on the branch-change rule

#### Scenario: Whoever authored the commits
- **WHEN** a qualifying Dependabot branch in `troupe-run/website` carries a commit whose author isn't
  `dependabot[bot]`
- **THEN** the GitHub check doesn't fail on the branch-change rule

#### Scenario: A repository without the ruleset
- **WHEN** a push to `troupe-run/.github`, or any repository not reserving the name, is checked for a qualifying
  `dependabot/npm_and_yarn/zod-4.6.7` branch
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: A name under the prefix but not Dependabot's shape
- **WHEN** a push to `troupe-run/website` is checked for a branch named `dependabot/zod-4.6.7` whose commits would
  otherwise qualify
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: A Dependabot branch from a fork
- **WHEN** a pull request into `troupe-run/website` comes from a fork's qualifying `dependabot/npm_and_yarn/zod-4.6.7`
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: A check that can't name its repository
- **WHEN** the check is run without a repository, and a qualifying `dependabot/npm_and_yarn/zod-4.6.7` is checked
- **THEN** the check fails on the branch-change rule

#### Scenario: Other rules still apply
- **WHEN** a qualifying Dependabot pull request in `troupe-run/website` has a description that closes no issue
- **THEN** the GitHub check fails under `pr-closes-issue`, and not on the branch-change rule

#### Scenario: A local commit on a Dependabot branch
- **WHEN** a contributor commits on a local branch named `dependabot/npm_and_yarn/zod-4.6.7`
- **THEN** the commit is refused under `commit-branch-change`: the exemption applies only on GitHub

### Requirement: An exempt Dependabot branch changes only dependency files
A Dependabot branch SHALL be exempt only when every path its commits change is a dependency file: a `package.json`,
`package-lock.json`, `pyproject.toml` or `uv.lock` in any directory, or a workflow under `.github/workflows/` in which
every added and removed line is a `uses:` line. Any other path, a deleted or renamed dependency file, or a workflow
with any other changed line SHALL leave the branch to the branch rule.

#### Scenario: An action bump
- **WHEN** a Dependabot branch in `troupe-run/infrastructure` changes only the `uses: actions/download-artifact@…`
  lines of `.github/workflows/tofu.yml`, for a patch update
- **THEN** the GitHub check doesn't fail on the branch-change rule

#### Scenario: Manifests in several packages
- **WHEN** a Dependabot branch in `troupe-run/troupe` changes `pyproject.toml` in two packages and the root `uv.lock`,
  for a patch update
- **THEN** the GitHub check doesn't fail on the branch-change rule

#### Scenario: Another file
- **WHEN** a Dependabot patch-update branch also changes `src/index.ts`
- **THEN** the GitHub check fails on the branch-change rule, naming `src/index.ts`

#### Scenario: A workflow line that isn't `uses:`
- **WHEN** a Dependabot patch-update branch changes a workflow's `uses:` line and also a `run:` line
- **THEN** the GitHub check fails on the branch-change rule, naming the workflow

### Requirement: An exempt Dependabot branch is a single minor or patch update
A Dependabot branch SHALL be exempt only when every commit's subject is Dependabot's for one dependency moving from
one version to another, and both versions count as a minor or patch update: dotted runs of digits whose first
differing part is the second or a later one. Where a commit's message gives an `update-type`, each SHALL be
`version-update:semver-minor` or `version-update:semver-patch`. A major update, or one whose versions can't be read,
SHALL NOT be exempt.

#### Scenario: A security update with no update type
- **WHEN** a Dependabot branch in `troupe-run/website` carries `build(deps): Bump postcss-selector-parser from 6.1.4
  to 6.1.5`, whose message has no `update-type`, changing only `package-lock.json`
- **THEN** the GitHub check doesn't fail on the branch-change rule

#### Scenario: A major update
- **WHEN** a Dependabot branch carries `chore(deps-dev): Bump typescript from 6.0.3 to 7.0.2`
- **THEN** the GitHub check fails on the branch-change rule, saying the update is major

#### Scenario: A requirement range
- **WHEN** a Dependabot branch carries `chore(deps-dev): Update uv-build requirement`, with no versions in its subject
- **THEN** the GitHub check fails on the branch-change rule, saying the update's versions can't be read

#### Scenario: An update type that disagrees with the versions
- **WHEN** a Dependabot commit's subject moves `1.2.3` to `1.2.4` and its message says `update-type:
  version-update:semver-major`
- **THEN** the GitHub check fails on the branch-change rule

#### Scenario: The same counting as the issue
- **WHEN** any pair of versions is counted by the check and by `dependabot-issues`
- **THEN** both call it the same kind of update

### Requirement: A Dependabot branch that isn't exempt says why
When a `dependabot/` branch in a repository that reserves the name fails a condition of the exemption, the
branch-change refusal SHALL name the condition that failed (the files, or the update's kind) and SHALL say the update
takes an OpenSpec change, linking the Dependabot section of the development workflow.

#### Scenario: A major update is refused
- **WHEN** website's `dependabot/npm_and_yarn/typescript-7.0.2` is checked
- **THEN** the refusal is under `commit-branch-change`, says the typescript update is major, and says to take it
  through an OpenSpec change
