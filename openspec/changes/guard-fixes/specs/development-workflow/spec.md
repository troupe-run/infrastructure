## MODIFIED Requirements

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

#### Scenario: A workflow line that begins with `--`
- **WHEN** a Dependabot patch-update branch changes a workflow's `uses:` line and also removes a line that begins with
  `--`, such as a YAML `---`, or adds one that begins with `++`
- **THEN** the GitHub check fails on the branch-change rule, naming the workflow

## ADDED Requirements

### Requirement: An exempt Dependabot branch has no merge commits
A Dependabot branch SHALL NOT be exempt when any of its commits is a merge commit, whatever its subject and whatever
files it changes. Dependabot doesn't make merge commits. The refusal SHALL name the merge commit and say that's why.

#### Scenario: A merge commit with a Dependabot subject
- **WHEN** a Dependabot branch `dependabot/npm_and_yarn/x` in `troupe-run/website` carries a patch update of
  `package-lock.json`, and then a merge commit whose subject is a Dependabot patch-update subject and which also
  changes `src/index.ts`
- **THEN** the GitHub check fails on the branch-change rule, naming the merge commit and saying it's a merge commit

### Requirement: The capability label read sends its token to GitHub's API only
When the capability label check reads the declared labels with the run's token, it SHALL send the token only in the
request to GitHub's contents API. If GitHub answers with a redirect, the request that follows it SHALL NOT carry the
token, wherever it points.

#### Scenario: A redirect to another host
- **WHEN** `GITHUB_TOKEN` is set and the labels' request is answered with a redirect to another host
- **THEN** the request to that host carries no `Authorization` header

#### Scenario: The first request
- **WHEN** `GITHUB_TOKEN` is set
- **THEN** the request to GitHub's contents API carries it as a bearer token
