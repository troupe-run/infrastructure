## MODIFIED Requirements

### Requirement: The rules are re-checked on GitHub
For every push to any branch and for every pull request, a GitHub check SHALL re-apply the git-level rules to the
commits involved: every commit message is a Conventional Commit, the branch matches an OpenSpec change (for any
branch other than `main`, except a release branch in a repository that reserves its name for the release App), and no
archived change has an unticked task. It applies the same rules as the git hooks, so a commit that skipped the local
hooks is still caught.

#### Scenario: A push that skipped the local hooks
- **WHEN** a branch is pushed carrying a commit with a non-conventional message that was made with `--no-verify`
- **THEN** the GitHub check for that push fails and names the commit

#### Scenario: A pull request from a branch with no matching change
- **WHEN** a pull request's branch has no matching OpenSpec change
- **THEN** the GitHub check fails and names the rule

#### Scenario: A Dependabot pull request in a governed repository
- **WHEN** a pull request in `troupe-run/troupe`, `troupe-run/infrastructure` or `troupe-run/website` comes from a
  branch named `dependabot/<ecosystem>/<package>-<version>`, which has no matching OpenSpec change
- **THEN** the GitHub check fails on the branch-change rule: no exemption covers a Dependabot branch
