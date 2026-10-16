# Development workflow guardrails

Every repository the org builds in enforces this workflow on its own development (spec:
`openspec/specs/development-workflow` in this repository). Today that's `troupe-run/troupe` and
`troupe-run/infrastructure`. The path every change takes is in the org's
[contributing guide](https://github.com/troupe-run/.github/blob/main/CONTRIBUTING.md). This page lists what the
guardrails refuse, how an override works, and how the guard reaches each repository.

Four layers enforce the rules. All of them call the same rule functions in `scripts/guard.py`, so they can't
drift apart:

| Layer | Runs | Covers | Can be skipped? |
|---|---|---|---|
| Git hooks: `pre-commit`, `commit-msg` | on every commit, for everyone | the git rules below | yes, `--no-verify` (it's your machine) |
| Git hook: `pre-push` | on every push, any branch | every commit being pushed is a Conventional Commit | yes, `--no-verify` |
| Claude Code hooks (`.claude/settings.json`) | before an agent's tool call | the Claude rules below, including refusing `--no-verify` | no, for an agent following `CLAUDE.md` |
| The `guard` GitHub check (`.github/workflows/guard.yml`) | on every push to every branch, and every pull request, re-run when its title is edited | commit messages, a pull request's title, the branch-change match, archived tasks | no: it's a required check, so a pull request can't merge while it's red (`tofu/required-checks.json`) |

**The git hooks are on by default.** Git never runs hooks from a fresh clone, so the repository's own tooling turns
them on: running `uv run scripts/check.py` does it, and so does starting a Claude Code session. Each says so when it
does. You can also run `git config core.hooksPath .githooks` yourself.

**GitHub can't reject a non-conforming push on our plan, or on GitHub Team.** We tested this on 2026-10-11. A
commit-message ruleset is accepted, but not enforced, on Free (`troupe-run`) and on Team (`hpsgd`, public and
private repositories), although Team did enforce a branch-deletion rule in the same repository. Metadata rules need
GitHub Enterprise, so moving the project or upgrading to Team wouldn't help. So a bad message can still
reach a branch. The `guard` check goes red within a minute of the push, and a pull request can't merge while it's
red. Fix it before anyone builds on the branch.

Every refusal names its rule and its fix:

```
guard: commit-on-main: commits aren't made on main; work reaches main through a pull request.
  fix: Create a branch named after the OpenSpec change: git switch -c <change-name>
```

## Rules

| Rule | Layer | Refuses | Fix |
|---|---|---|---|
| `commit-on-main` | git | a commit with `main` checked out | create a branch named after the change |
| `commit-branch-change` | git | a commit on a branch with no matching OpenSpec change (active, or archived on that branch), or on a detached HEAD. On GitHub, a `release-please--` branch is exempt by its name when it lives in a repository whose ruleset lets only the release App create or update those branches (`RELEASE_REPOSITORIES` in `scripts/guard.py`: troupe only). Who authored its commits isn't asked. For a pull request that's its head repository, so a fork's branch is never exempt; a run that names no repository exempts nothing | propose the change, or switch to its branch |
| `commit-message` | git | a first line that isn't a Conventional Commit (`type(scope)!: subject`); `fixup!`, `squash!` and `amend!` are accepted when they name a Conventional Commit subject. The `guard` check applies the same rule to a pull request's title, which becomes the commit message if squash merging is ever turned on | use one of `feat fix docs build ci test refactor perf style chore revert` |
| `commit-checks` | git | a commit while tracked files have unstaged changes, while `scripts/check.py` fails, or while `scripts/check-paths.toml` is malformed. The check runs only what the staged paths need (see below) | stage or stash the changes; fix what the check reports, or the declaration |
| `archive-incomplete` | git | a commit that adds an archived change with an unticked task | finish and tick every task first |
| `edit-branch-change` | Claude | an Edit, Write, MultiEdit or NotebookEdit to a repository file when the branch has no matching change | switch to, or create, the change's branch |
| `pr-closes-issue` | Claude | `gh pr create` into this repository whose `--body` or `--body-file` doesn't close an issue, or that uses `--fill` or stdin. The target is named by `--repo`/`-R`, else `GH_REPO`, else it's this repository; a PR into another repository isn't checked, and a target that can't be read, or a clone with no remote, counts as this one | add `Closes #<issue>`, or name the other repository with `--repo` |
| `skip-hooks` | Claude | `--no-verify`, `git commit -n`, and setting, unsetting or overriding `core.hooksPath` | fix what the hook reports |
| `command-unparseable` | Claude | a `git` or `gh` command that can't be parsed (for example, unbalanced quotes) | simplify the command |
| `delivered-file` | git | in a repository that receives the guard, a commit that changes a file listed in `.github/guard-delivery.json` (the Claude Code hook refuses the edit too, and the `guard` check fails such a commit unless its author is the infrastructure App; one that gets past them shows in the daily plan) | change the file in `troupe-run/infrastructure`, and deliver it from there |
| `owner-only` | Claude | a `gh` command doing what only the owner does, in any repository: merging past a pull request's rules (`gh pr merge --admin`, or any merge through the API), approving or rejecting a deployment, changing a ruleset, branch protection or environment, org and repository administration (secrets, variables, labels, repository settings, Pages, issue types, project definitions, transfers), and the login's credentials (`gh auth token`, `auth status --show-token`, login and logout). The throwaway repositories `troupe-run/infra-probe-*`, `spike-*` and `bakeoff-*` are exempt, except deleting, archiving, unarchiving or renaming a `spike-*` or `bakeoff-*` record. The list is `GH_OWNER_ONLY`, `GH_API_OWNER_ONLY` and `GH_MUTATIONS_OWNER_ONLY` in `scripts/guard.py` | ask the owner, or change it in `troupe-run/infrastructure` through a pull request |
| `gh-allow-list` | Claude | any other `gh` command not on the allow-list (reads, and the everyday pull request, issue, comment, sub-issue, project-item and workflow-run writes): an unknown subcommand, an extension, an alias, an unlisted `gh api` write, any GraphQL mutation (each everyday write has one way to do it, its `gh` command: guard-issue-mutations, design D1), and a GraphQL query that can't be read before it runs (stdin, or a file not yet written). The list is the `GH_*` tables in `scripts/guard.py`, built from the commands agents ran in earlier sessions (refuse-admin-merge, design D4) | for a GraphQL mutation, the refusal names it and, when there is one, the `gh` command that does the same (`updateIssueIssueType` → `gh issue edit <n> --type <name>`); otherwise ask the owner, or add it to the list in `troupe-run/infrastructure`; a read with fields needs `-X GET` |
| `guard-tamper` | Claude | running the override command, naming a path in the override directory, or editing under `.git/`. **No override unlocks this rule.** | ask the owner |

## What a commit runs

Before a commit, the guard runs `scripts/check.py`, the same check CI runs. Here the full check takes about 65
seconds on macOS (measured 2026-10-15), plus a one-time dependency download on a fresh clone. Whatever runs is
announced before it starts, its output streams as it runs, and it's stopped and the commit refused after 10 minutes
(`CHECK_TIMEOUT_SECONDS` in `scripts/guard.py`).

A repository can say that some paths need less than the full check, in `scripts/check-paths.toml`. The file is the
repository's own and isn't delivered, because what its tests read is its own knowledge:

```toml
version = 1

[skip]          # no test reads these
paths = ["openspec/**"]

[scopes.docs]   # only the tests tagged `docs` read these
paths = ["docs/**", "plugins/runner-scripted/README.md"]
```

- **Entries** are an exact path (`plugins/runner-scripted/README.md`) or a directory and everything under it
  (`docs/**`). No other wildcard is accepted.
- **Scopes may overlap.** A path in two scopes runs both. A path can't be both skipped and in a scope.
- **Scope names** match `[a-z][a-z0-9_]*`, so each is a valid tag in any test runner. `none` and `full` are reserved.
- **Anything else is malformed**, and refuses the commit, naming the file, the problem and the fix. That includes
  other keys or tables, another `version`, and the bad entries above. A malformed file is never treated as missing.

The guard lists the staged paths with rename detection off, so a file moved from `src/` into `openspec/` counts by
both names. Then:

| Staged paths | What runs |
|---|---|
| all skipped | nothing; the guard says `only openspec/** is staged; the check is skipped (scripts/check-paths.toml).` |
| all skipped or in scopes | `scripts/check.py --scope <a> --scope <b>`, for every scope a path is in, sorted |
| any path in no group, none at all, or `scripts/check-paths.toml` itself | the full check |

With no `scripts/check-paths.toml`, every commit runs the full check. A commit that changes the declaration always
runs the full check, so it can't widen itself and benefit in the same commit. This repository skips `openspec/**`.

**CI gets the same answer from the same code.** A workflow pipes the changed paths into `check-scope`:

```bash
git diff --name-only --no-renames "$BASE...$HEAD" | uv run --no-project scripts/guard.py check-scope >> "$GITHUB_OUTPUT"
```

It prints two lines:

| Decision | Output |
|---|---|
| nothing | `scope=none` and `check-args=` |
| scopes | `scope=api,docs` and `check-args=--scope api --scope docs` |
| full | `scope=full` and `check-args=` |

A job reports success when `scope` is `none`, and otherwise runs `uv run scripts/check.py <check-args>`. That keeps
a required check reporting even when nothing needs to run, which `paths-ignore` wouldn't. A malformed declaration
fails the step, prints the same message as the commit hook, and prints no answer. CI still decides two things for
itself: the base to compare against, and what to do when it can't work one out (a new branch, a force push, a shallow
history). Then it passes no paths, and the answer is `full`.

### A scope is a test tag

The guard passes scope names and doesn't know what they run. A repository that declares a scope makes its `check.py`
keep this contract, whatever language it's in:

- **Every gate still runs.** Linters, type checkers and `tofu validate` take seconds, so a scope can't skip a lint
  error. Only the tests, the slow part, are narrowed.
- **The tests narrow to those tagged with any of the scopes.**
- **A scope the declaration doesn't list is refused**, before any gate runs, naming the scope and the file.
- **A scope no test is tagged with passes**, after every other gate, and says there was nothing to test. The tag
  check below makes that safe: a test that read the scope's paths without the tag would fail the next full run. (pytest
  exits 5 when `-m` selects nothing, and this repository's `check.py` reads that as a pass, only in a scoped run.)

With pytest, the tag is a marker named for the scope: `@pytest.mark.docs` on a test, or `pytestmark = pytest.mark.docs`
on a module. `check.py` runs `pytest -m "api or docs"`, built by `guard.marker_expression`. This repository's
`check.py` takes `--scope` too. It declares no scope, so it refuses every name.

**Every test run checks the tags.** A test fails if it reads a file under a scope's paths without that scope's tag,
or reads a skipped path at all. The message names the test, the file and the tag to add. So a new test that reads
`docs/` can't be left out of the `docs` scope unnoticed: the next full run fails it. For pytest, the check is the
delivered plugin `scripts/guard_pytest.py`, loaded from the pytest configuration in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = ["scripts"]                  # wherever the repository keeps it on the path
addopts = ["-p", "guard_pytest"]
```

It registers each declared scope as a marker, so `--strict-markers` accepts them and the declaration is the one
list. It records each test's file reads through Python's `open` audit event, counting only files inside the
repository. Reads made by a subprocess the test starts aren't seen. A scope whose tests read that way keeps its tags
by hand, and its comment in `scripts/check-paths.toml` should say so.

The rule itself is `guard.tag_violations`, which takes plain data: a test's id, its tags and the files it read.
Another runner, such as vitest, follows the same contract with its own adapter that collects that data.

## What the guard grants

The Claude Code hook can also answer "allow", so a command runs without a prompt or auto mode's check
(guard-grants-gh). It grants only when all of these hold:

- **A granted `gh` command:** `GH_GRANTED` in `scripts/guard.py`. That's the allow-list's reads and everyday issue,
  pull request, comment and project-item writes, such as `gh pr ready 74` or `gh issue edit 29 --type Feature`. It
  doesn't include `gh pr merge`, `gh pr checkout`, `gh workflow run`, `gh run rerun`/`cancel`/`download`,
  `gh repo clone`, `gh api`, or anything allowed only in a throwaway repository. Those get Claude Code's own check.
- **A plain command, through the Bash tool:** exactly one `gh` command. Outside quotes it has no chaining,
  substitution, variable, redirection, glob, comment or escape, and inside double quotes no `$` or backtick. No
  environment prefix and no path to `gh`.
- **Local files only from here:** every `--body-file`/`-F` is inside the repository or the system temp directory.
- **No refusal:** no rule refuses it, including one an override would excuse.
- **The reviewed guard:** the running `scripts/guard.py` is identical to the one on `origin/main`. A guard edited on a
  branch refuses as usual but grants nothing.

A person's own `deny` and `ask` permission rules still apply to a granted command, whichever settings file holds them.

## Overrides

Only a person can grant an override, from their own terminal, never through an agent's tool calls:

```console
uv run scripts/guard.py override commit-on-main --reason "hotfix while CI is down"
```

- **One action:** the override applies to the next refusal of that rule, and is then used up.
- **Recorded:** it's stored under `.git/troupe-guard/`, which is local and never committed, with the reason, your
  git `user.email` and the time.
- **Logged:** each use appends a line to `.git/troupe-guard/overrides.jsonl`: the rule, the reason, who granted
  it, when it was granted and used, and what it let through.
- **Not for `guard-tamper`:** that rule can't be overridden.

## Where the guard comes from

The guard is maintained in `troupe-run/infrastructure` (spec: `guard-delivery`). Each other governed repository holds
copies that the infrastructure App delivers straight to its `main`, after the owner approves the plan:

- `scripts/guard.py`, `scripts/guard_pytest.py`, `.githooks/`, `.claude/settings.json` and
  `.github/workflows/guard.yml`;
- `.github/guard-delivery.json`, which lists the delivered files. Its presence is what marks a repository as one that
  receives the guard.

A hand edit to a delivered file shows as drift in the next plan, and an apply restores it. `main` is planned every
day, so that is within a day of the edit landing. The `delivered-file` rule refuses such an edit before it gets that
far: change the file in `troupe-run/infrastructure` instead. The scripts'
own checks (`scripts/check.py`), and any other files, stay each repository's own.

## Where the templates come from

The pull request template and the Bug, Feature and Decision issue forms are the org's defaults. Their source is
`org-profile/.github/` in `troupe-run/infrastructure`, and the App publishes them to `troupe-run/.github` with the
other org-wide files (specs: `development-workflow`, `org-profile`).

- **GitHub applies them only where a repository has none of its own.** A repository with any
  `.github/ISSUE_TEMPLATE/` folder, even one holding only a `config.yml`, uses none of the org's forms. A repository
  with its own `PULL_REQUEST_TEMPLATE.md` uses that one.
- **A form's issue type and labels must exist.** GitHub silently drops a type or label it doesn't know, so
  `scripts/tests/test_org_profile.py` checks each form's `type:` against `oob/issue-types.json`, and its labels
  against `tofu/labels/workflow.json`, which every managed repository gets.

## Dependabot pull requests

Every managed repository has Dependabot alerts and security updates on (spec: `repositories`). When an alert has a
fix, Dependabot opens a pull request for it.

- **In a governed repository** (troupe, infrastructure, website), Dependabot's pull request is an alert that comes
  with a fix.
  It can't merge as it is: its `dependabot/...` branch matches no OpenSpec change, so the `guard` check fails. (Its
  commit is a Conventional Commit, and it's signed off as `dependabot[bot] <support@github.com>`, so the branch is
  what stops it.) Take the fix into an issue and an OpenSpec change like any other change:
  make the same bump on a branch named after the change, with a pull request that closes the issue. Then close
  Dependabot's pull request with a comment linking that change. There's no exemption for Dependabot's branches, and a
  test fails if one appears (security-scanning, design D5).
- The website has no DCO, so there the branch is the only thing that stops it. It's handled the same way
  (govern-website).

## Known gaps

GitHub enforces rules that apply to everyone, or that protect a secret, such as an App's key. It doesn't try to tell
an agent from the owner: agents work with the owner's `gh` login, so GitHub sees one identity. Agents are governed
locally, by the guard's hooks and `gh` allow-list. The owner's review at merge is the gate, and required checks are
evidence for that review. A GitHub check that a pusher can satisfy by writing an author, naming a branch or editing a
workflow catches mistakes, not forgery. A rule that GitHub enforces for everyone but an App, like `protect main` or
troupe's release ruleset, is different: getting past it takes the App's key (#47).

- **These hooks aren't a security boundary.** They stop honest shortcuts. A Bash command that writes a file isn't
  seen by the edit hook, though the git hooks catch it at commit time. A determined bypass is still possible.
  GitHub's rulesets and required checks back them up, and the owner's review at merge is the gate.
- **A grant skips Claude Code's own checks.** When the guard answers "allow", auto mode's classifier isn't consulted,
  even for its `hard_deny` rules (measured on 2026-10-13; the docs don't state it). So for a granted command, the
  conditions under "What the guard grants" are the only check, apart from a person's own `deny` and `ask` rules. A
  file in the temp directory can be posted with `--body-file` without a check.
- **"The reviewed guard" is judged from local refs.** `origin/main` is a ref in the local clone, which an agent could
  move with plumbing commands. The check stops an edited guard granting by accident, not on purpose.
- **The `gh` rules see only `gh`.** An agent holds the owner's login, so any other HTTP client with its token
  (`curl`, a script, a `gh` extension the guard refuses to run but a script could) bypasses them, and so does an MCP
  tool, which the hook doesn't see. Refusing `gh auth token` makes the token harder to reach, not unreachable: it's
  also in the keychain and gh's config.
- **A command assembled at run time** (`eval`, `sh -c "$X"`) isn't known before it runs, so its `gh` words can't
  be checked.
- **A throwaway repository is a naming convention.** An agent can create `troupe-run/spike-x` and do anything there;
  that's confined to a repository nothing depends on.
- **Pull requests opened through `gh api`** aren't checked for a closing reference. They're refused anyway, as
  an unlisted write (`gh-allow-list`), unless the owner grants an override.
- **A bad commit message can reach a branch** if the local hooks were skipped, because GitHub doesn't reject it at
  push time on our plan. The `guard` check flags it at once, and blocks the merge.
- **The local hooks run the working tree's `guard.py`.** A commit that edits it can disable its own check. The
  `guard` check on GitHub runs the committed rules, and in a repository that receives the guard, the plan shows the
  edit as drift.
- **The `delivered-file` check catches mistakes, not forgery.** The `guard` check accepts a change to a delivered
  file whose author is the infrastructure App's bot, and anyone can write that into a commit. It also runs the pushed
  copy of itself, so a push could change the check too. GitHub can't refuse the push either: it allows no push rules
  on a public repository (enforce-delivered-files, design D1). A change that gets past it, by any route, is drift: it
  shows in the daily plan within a day of landing, and stays until the owner approves the apply that restores it.
- **The release-branch exemption is by name, on troupe only.** A `release-please--` branch skips the branch-change
  rule on GitHub when it lives in troupe, whoever authored its commits. troupe's "release branches" ruleset
  (`tofu/release.tf`) lets only the release App create or update those branches, so there the name is proof. The
  exemption applies nowhere else: not in this repository, which has no such ruleset, and not to a fork's branch,
  which troupe's ruleset doesn't cover. A test fails if an exempt repository loses its declared ruleset, or the
  ruleset stops reserving creation or update.
- **A security fix waits for a person.** In a governed repository, Dependabot's pull request can't merge, so a fix for
  a vulnerable dependency lands only once someone takes it into a change. The alert is emailed to the owner and stays
  open until the vulnerable version is gone from `main`.
- **Overrides are local.** The `guard` check on GitHub ignores them, so nothing granted on one machine excuses a
  commit on `main`.
- **Bash parsing is heuristic.** When a `git` or `gh` command can't be parsed, it's refused rather than guessed at.
- **Permission modes:** a Claude Code hook's deny holds in `bypassPermissions` mode (`--dangerously-skip-permissions`).
  Verified on 2026-10-11 on Windows: `git commit --dry-run --no-verify` was refused with `skip-hooks`. `dontAsk` mode
  is untested. The git hooks apply in every mode.
