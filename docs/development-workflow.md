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
| Git hook: `pre-push` | on every push, any branch | every commit being pushed is a Conventional Commit, and changes no protocol schema under a type that releases nothing | yes, `--no-verify` |
| Claude Code hooks (`.claude/settings.json`) | before an agent's tool call | the Claude rules below, including refusing `--no-verify` | no, for an agent following `CLAUDE.md` |
| The `guard` GitHub check (`.github/workflows/guard.yml`) | on every push to every branch but a merge queue's (`gh-readonly-queue/...`), every pull request, re-run when its title or description is edited, and every merge group, which it judges as a push to `main` (merge-queue design D3) | commit messages, schema changes' commit types, a pull request's title, that a pull request's description closes an issue (`pr-closes-issue`, release-please's exempt), the branch-change match, archived tasks, OpenSpec's strict validation (`openspec-strict`), and, in troupe, the capability labels its specs name (`capability-label`) | no: it's a required check, so a pull request can't merge while it's red (`tofu/required-checks.json`) |

**Claude's review isn't one of them.** `.github/workflows/claude-review.yml` posts Claude's findings on each member's
pull request. It isn't a required check, it can't approve or request changes, and its run can only read the code,
comment, and resolve its own must-fix conversations (spec: pr-review). A failed or skipped review never stops a merge.
Bots' and forks' pull requests aren't reviewed. What it found is enforced by GitHub, not by its run: see "Claude's
review" below. It doesn't load the repository's Claude Code settings, so the guard's hooks don't run
in it: they're written for an agent in your terminal, and would widen what the review can do (spec: pr-review). Its
session's output stays hidden. Only a tool call Claude was refused is named in the run's log, as a warning, so the
cause can be traced (spec: pr-review, #161).

**The git hooks are on by default.** Git never runs hooks from a fresh clone, so the repository's own tooling turns
them on: running `uv run scripts/check.py` does it, and so does starting a Claude Code session. Each says so when it
does. You can also run `git config core.hooksPath .githooks` yourself. Git only runs a hook that is executable, so
both also name any hook in `.githooks/` that isn't: git skips it. That's a notice, not a refusal. A delivered hook is
fixed in `troupe-run/infrastructure`, whose next plan sets its mode; don't change it in the clone. Git for Windows runs
a hook whatever its mode, so nothing is reported there.

**GitHub can't reject a non-conforming push on our plan, or on GitHub Team.** We tested this on 2026-10-11. A
commit-message ruleset is accepted, but not enforced, on Free (`troupe-run`) and on Team (`hpsgd`, public and
private repositories), although Team did enforce a branch-deletion rule in the same repository. Metadata rules need
GitHub Enterprise, so moving the project or upgrading to Team wouldn't help. So a bad message can still
reach a branch. The `guard` check goes red within a minute of the push, and a pull request can't merge while it's
red. Fix it before anyone builds on the branch. After a force push, the check's clone doesn't hold the tip the push
replaced, so it judges the branch from where it left `main`, as for a first push, and says so.

Every refusal names its rule and its fix:

```
guard: commit-on-main: commits aren't made on main; work reaches main through a pull request.
  fix: Create a branch named after the OpenSpec change: git switch -c <change-name>
```

## Claude's review

Every finding Claude's review posts is a conversation on the lines it's about, and its first line names its tier,
which says who resolves it (spec: pr-review; review-findings-by-severity design D1):

| Tier | What it is | Who resolves it |
| --- | --- | --- |
| `**must-fix** · …` | someone other than the author should check the fix before it merges: wrong behaviour, lost data, a weakened fence, a missing or overclaiming test, a ticked task with nothing behind it, or the issue's "Done when" not met. Unsure between must-fix and nit means must-fix | the review, on its next run, once the problem is gone or the author's reply convinces it; a dispute that's still open after that goes to the owner |
| `**nit** · …` | the worst outcome of leaving it is a reader briefly misled, or untidy code | the author, after replying with what it did: fixed it, raised a follow-up issue, or not worth it and why |
| `**decision** · …` | a choice the change's design doesn't settle, that's hard to reverse or reaches beyond the pull request | the owner |

A conversation's tier is the latest label the review gave in it: only the review re-tiers, by replying with a new label
and its reason. A label in anyone else's reply counts for nothing.

**Before the change is archived**, the session that owns it waits for the review of its last push and acts on each
finding by its tier (spec: development-workflow, "Review findings are acted on before a change is archived"). The `main`
ruleset refuses a merge, and the merge queue, while any conversation is unresolved (spec: rulesets).

**Replying in a conversation** has one way, since `gh` has no command for it: a review comment in reply to the
conversation's first comment, `gh api -X POST repos/<owner>/<repo>/pulls/<n>/comments -F in_reply_to=<comment id> -f
body=...`. A top-level `gh pr comment` isn't in the conversation. The `.../comments/<id>/replies` endpoint and GraphQL's
`addPullRequestReviewThreadReply` are refused.

**Resolving a nit** is the one GraphQL mutation an agent may send (spec: development-workflow, "An agent resolves only a
nit"; `GH_MUTATIONS_CONDITIONAL` in `scripts/guard.py`): `gh` and GitHub's REST API have no way to resolve a
conversation. The guard allows `resolveReviewThread` only for one conversation per command, named in the query
(`threadId: "PRRT_..."`) or by a `-f` field, after it has read the conversation from GitHub with your `gh` login: the
review (`troupe-run-review`, a Bot) opened it, and the review's latest label among its last 100 comments is nit. A
must-fix, a decision, an unlabelled finding and a person's conversation are refused, and so is a resolve when the read
fails or takes more than 20 seconds. `unresolveReviewThread` is refused: reopening a conversation is the owner's. This
is enforced only here, locally: GitHub can't tell an agent's resolve from the owner's, since they share one login (#47).

## Rules

| Rule | Layer | Refuses | Fix |
|---|---|---|---|
| `commit-on-main` | git | a commit with `main` checked out | create a branch named after the change |
| `commit-branch-change` | git | a commit on a branch with no matching OpenSpec change (active, or archived on that branch), or on a detached HEAD. On GitHub, a `release-please--` branch is exempt by its name when it lives in a repository whose ruleset lets only the release App create or update those branches (`RELEASE_REPOSITORIES` in `scripts/guard.py`: troupe only). Who authored its commits isn't asked. For a pull request that's its head repository, so a fork's branch is never exempt; a run that names no repository exempts nothing. A Dependabot branch (`dependabot/<ecosystem>/<name>`; another name under `dependabot/` isn't trusted) is exempt on GitHub, on the same terms, in a repository whose ruleset lets only Dependabot create or update those branches (`DEPENDABOT_REPOSITORIES`: troupe, website and this one), and only when every commit changes only dependency files (`package.json`, `package-lock.json`, `pyproject.toml`, `uv.lock`, or a workflow's `uses:` lines) and its subject is one minor or patch update, with any `update-type` in its message agreeing. Its commits' authors and the pull request's title aren't read. One that fails a condition is refused saying which. A merge group is judged as a push to the branch it lands on, so the queue's own `gh-readonly-queue/...` branch, which matches no change, isn't judged: each pull request in the group passed this rule. That comes from GitHub's `merge_group` event, never from a branch's name, so a branch named like a queue's is judged like any other, and a `merge_group` payload without its base, head and branch fails saying so | propose the change, or switch to its branch; for a Dependabot update that isn't exempt, take it through an OpenSpec change (see "Dependabot pull requests") |
| `commit-message` | git | a first line that isn't a Conventional Commit (`type(scope)!: subject`); `fixup!`, `squash!` and `amend!` are accepted when they name a Conventional Commit subject. The `guard` check applies the same rule to a pull request's title, which becomes the commit message if squash merging is ever turned on | use one of `feat fix docs build ci test refactor perf style chore revert` |
| `schema-commit-type` | git | a commit that changes, adds, moves or removes a file under `protocol/schemas/` under a type that releases nothing. release-please releases the protocol, and moves the version troupe records for its copy of the schemas, only for `feat`, `fix`, `perf` and `revert`, or a breaking change of any type (`!`, or a `BREAKING CHANGE:` or `BREAKING-CHANGE:` footer). Any other type would ship changed schemas under the old protocol version (#122). The paths are `SCHEMA_PATHS` and the types `RELEASING_TYPES`, both in `scripts/guard.py`. It judges the files the commit contains, including with `git commit -a` or `git commit <path>`, and a fixup by the type of the commit it names. A repository with no `protocol/schemas/` (today, everything but troupe) is never refused. An override excuses the local hook only: the `pre-push` hook and the `guard` check judge each commit again, so a schema change that merges has a releasing type | use `feat`, `fix`, `perf` or `revert` (e.g. `fix(protocol): <what changed>`), or mark it breaking; if the rest of the work shouldn't release, commit the schema change on its own |
| `commit-checks` | git | a commit while tracked files have changes it leaves out, while `scripts/check.py` fails, or while `scripts/check-paths.toml` is malformed. The check runs only what the staged paths need (see below). It judges what the commit contains, including with `git commit -a` or `git commit <path>`, so `-a` goes ahead, and a path commit is refused while another tracked file has an edit, staged or not, that it leaves out, because the check runs on the working tree | stage or stash the changes, or with `git commit <path>` name them too or commit without paths; fix what the check reports, or the declaration |
| `archive-incomplete` | git | a commit that adds an archived change with an unticked task, judged on what the commit contains, including with `git commit -a` or `git commit <path>` | finish and tick every task first |
| `edit-branch-change` | Claude | an Edit, Write, MultiEdit or NotebookEdit to a repository file when the branch has no matching change | switch to, or create, the change's branch |
| `pr-closes-issue` | Claude | `gh pr create` into this repository whose `--body` or `--body-file` doesn't close an issue, or that uses `--fill` or stdin. A `--body` built by the shell (`$VAR`, `$(...)` or backticks, such as `"$(cat <<'EOF' ... EOF)"`) whose own text closes no issue can't be checked before it's sent, and is refused saying so; because the guard sees words after quoting is removed, literal text in single quotes that looks like an expansion gets the same message. Flags are read as gh reads them (`-b'…'`, `-b=…`, `-Fpr.md`, grouped `-db …`, and a flag-like value such as `--title --fill`), and the last body flag wins. The target is named by `--repo`/`-R`, else `GH_REPO`, else it's this repository; a PR into another repository isn't checked, and a target that can't be read, or a clone with no remote, counts as this one. `gh pr create --help` and `-h` go ahead, as help requests (see `gh-allow-list`). The `guard` check applies the same reading to every pull request's description, however it was opened (GitHub's UI, a bot, a session without hooks), and re-runs when it's edited: an empty description fails, and a payload whose description can't be read fails saying so. A release-please pull request is exempt where its branch is exempt from `commit-branch-change`; a Dependabot one isn't | add `Closes #<issue>`, or name the other repository with `--repo`; for a body built by the shell, write it to a file in an earlier command and pass `--body-file` with a literal path. On GitHub, edit the description (`gh pr edit <n> --body-file <file>`, or on GitHub) to add `Closes #<issue>` or `Closes owner/repo#<issue>` |
| `skip-hooks` | Claude | `--no-verify`, `git commit -n`, and setting, unsetting or overriding `core.hooksPath` | fix what the hook reports |
| `command-unparseable` | Claude | a `git` or `gh` command that can't be parsed (for example, unbalanced quotes), or one the guard finds but can't read (see "Which commands the guard reads"): `gh` or `git` given to a program it doesn't know to treat them as data (`xargs`, `sudo`, `find -exec`, `docker`), a program named by an expansion (`$G auth token`, `& $c`), a shell reading its commands from a pipe or here-string, an alias, a `case` inside a substitution, a wrapper option it doesn't know (`env -S`), or commands nested more than 16 deep. A command that never mentions `git` or `gh` isn't refused for this (read-nested-commands, design D5) | run the `git` or `gh` command on its own, as a separate command, not through another program, a variable or a pipe into a shell; for unbalanced quotes, simplify the command |
| `delivered-file` | git | in a repository that receives the guard, a commit that changes a file listed in `.github/guard-delivery.json`, judged on what the commit contains, including with `git commit -a` or `git commit <path>` (the Claude Code hook refuses the edit too, and the `guard` check fails such a commit unless its author is the infrastructure App; one that gets past them shows in the daily plan) | change the file in `troupe-run/infrastructure`, and deliver it from there |
| `owner-only` | Claude | a `gh` command doing what only the owner does, in any repository: merging past a pull request's rules (`gh pr merge --admin`, or any merge through the API), approving or rejecting a deployment, changing a ruleset, branch protection or environment, org and repository administration (secrets, variables, labels, repository settings, Pages, issue types, project definitions, transfers), and the login's credentials (`gh auth token`, `auth status --show-token`, login and logout). The throwaway repositories `troupe-run/infra-probe-*`, `spike-*` and `bakeoff-*` are exempt, except deleting, archiving, unarchiving or renaming a `spike-*` or `bakeoff-*` record. The list is `GH_OWNER_ONLY`, `GH_API_OWNER_ONLY` and `GH_MUTATIONS_OWNER_ONLY` in `scripts/guard.py`. Its help (`gh repo edit --help`) isn't refused: see `gh-allow-list` | ask the owner, or change it in `troupe-run/infrastructure` through a pull request |
| `gh-allow-list` | Claude | any other `gh` command not on the allow-list (reads, and the everyday pull request, issue, comment, sub-issue, project-item and workflow-run writes): an unknown subcommand, an extension, an alias, an unlisted `gh api` write, any GraphQL mutation (each everyday write has one way to do it, its `gh` command: guard-issue-mutations, design D1) but `resolveReviewThread` on a nit (see "Claude's review" above), and a GraphQL query that can't be read before it runs (stdin, or a file not yet written). The list is the `GH_*` tables in `scripts/guard.py`, built from the commands agents ran in earlier sessions (refuse-admin-merge, design D4). A request for a built-in command's help goes ahead whatever the command would be refused for: `gh`, one of gh's own groups (`GH_BUILTIN_GROUPS`), words that aren't flags, and `--help` or `-h` as the last word (refuse-substituted-pr-body, design D4). `--help` after a flag, or followed by anything (a redirection included), is judged as the command it is; an extension, an alias and `gh extension exec` aren't help requests. A help request is granted only when the command it asks about is | for a GraphQL mutation, the refusal names it and, when there is one, the `gh` command that does the same (`updateIssueIssueType` → `gh issue edit <n> --type <name>`); otherwise ask the owner, or add it to the list in `troupe-run/infrastructure`; a read with fields needs `-X GET` |
| `openspec-strict` | GitHub | in a repository with an `openspec/` root, a main spec or active change in scope that fails `openspec validate --strict` (#123). For a pull request or a push to a branch other than `main`, the scope is the main specs and active changes its commits change, so a spec it doesn't touch never fails it; it's everything when the commits change `scripts/guard.py` or `.github/workflows/guard.yml` (`OPENSPEC_ALL_PATHS` in `scripts/guard.py`), and on every push to `main`, deliveries included, and every merge group. Archived changes aren't validated. It names each requirement at fault by its name, and fails, rather than passes, when the OpenSpec CLI is missing, runs over `OPENSPEC_TIMEOUT_SECONDS`, or prints a result the guard can't read. The CLI is the version `.github/workflows/guard.yml` pins (`OPENSPEC_VERSION`); see "Moving the OpenSpec version". Checked only on GitHub, so it isn't overridable | run the command the refusal gives, with the version it names, and fix what it reports; for a long requirement, move examples into scenarios, or split it |
| `capability-label` | GitHub | in troupe only (`CAPABILITY_REPOSITORIES` in `scripts/guard.py`, judged by the repository the run is in, so a fork's pull request into troupe is judged too), a spec in scope whose Purpose doesn't start with a `Capability:` line, has a malformed one, or names a label that `tofu/labels/troupe.json` on this repository's `main` doesn't declare (#153). The specs judged are the main specs the commits change, which is how an existing spec's labels change, and each delta in an active change the commits change whose spec doesn't exist yet, whose Purpose becomes the new spec's. A delta for a spec that exists isn't read: OpenSpec ignores its Purpose. The scope is everything in the same cases as `openspec-strict`. The labels are read over the network, from GitHub's contents API at `main`, with the run's token, so a label is found as soon as its pull request merges; the read is skipped when no spec is in scope, and a read that fails or returns something other than a list of labels fails the rule, rather than passing it. Checked only on GitHub, so it isn't overridable, and the local hooks, which work offline, don't run it | for an undeclared label, add it as [a standard change](standard-changes.md#a-capability-label): open the label's sub-issue under the needing issue's Epic, then re-run the check once its pull request merges; or name a declared label. For a missing or malformed line, start the Purpose with ``Capability: `cap:<name>`, `cap:<name>` ``: for a proposed spec, at the top of its delta's `## Purpose` |
| `guard-tamper` | Claude | running the override command, naming a path in the override directory, or editing under `.git/`. **No override unlocks this rule.** | ask the owner |

## Which commands the guard reads

Every Claude rule reaches every `git` and `gh` command a Bash or PowerShell command would run, wherever it sits, and
decides it as it would the same command run on its own: the same rule, message and fix (read-nested-commands). So
`out=$(gh repo delete troupe-run/x --yes)` is refused as `owner-only`, and `x=$(git commit --no-verify -m 'fix: x')`
as `skip-hooks`, while `git log $(git merge-base main HEAD)..HEAD` goes ahead. The reader is `read_shell` in
`scripts/guard.py`, and its tests check what it reads against what bash, zsh and PowerShell really run.

- **Bash and zsh (the Bash tool):** command substitution (`$(...)` and backticks, in or out of double quotes, nested
  to any depth), process substitution (`<(...)`, `>(...)`, zsh's `=(...)`), `${...}` and arithmetic, a heredoc whose
  body the shell expands, subshells and `{ ...; }` groups, loop, conditional and function bodies, `!`, leading
  assignments and redirections, the wrappers in `SHELL_WRAPPERS` (`time`, `command`, `builtin`, `exec`, `env`,
  `nice`, `nohup`, `timeout`, zsh's `noglob` and `nocorrect`), the `-c` string of `bash`, `sh`, `zsh`, `dash` and
  `ksh`, `eval`'s words, and a heredoc a shell runs as its script.
- **PowerShell (the PowerShell tool):** subexpressions (`$(...)`, `@(...)`, `(...)`), script blocks (`{ ... }`),
  expandable strings and here-strings (`"..."`, `@"..."@`; a backtick is an escape), the `&` and `.` call operators,
  assignments, the command strings of `Invoke-Expression` and `iex`, `pwsh` and `powershell` (`-Command`, and
  `-EncodedCommand` decoded), and `cmd /c`.
- **Words that only name `git` or `gh`** aren't refused: the programs in `DATA_PROGRAMS` (`echo`, `printf`, `which`,
  `type`, `grep`, `rg`, `man`, `for … in`, …), `command -v`, and in PowerShell those in `POWERSHELL_DATA_PROGRAMS`
  (`Write-Output`, `Get-Command`, `Select-String`, PowerShell's keywords). To add one, change the table by pull
  request: a program earns a place only if no option of it runs a word it's given.
- **What the guard can't read** is refused under `command-unparseable` when the command mentions `git` or `gh`; see
  its row.
- **Out of reach:** commands that programs and scripts run themselves (`bash script.sh`, `uv run scripts/check.py`,
  `make`, Python's `subprocess`, a git alias starting with `!`, `source`), and a program's name hidden on purpose,
  such as `$'\x67h'`. These are under "Known gaps".

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

[scopes.vcs_git]  # a package; its suite and the core suite reach it
paths = ["packages/troupe-vcs-git/src/**", "packages/troupe-vcs-git/tests/**"]
tests = ["packages/troupe-vcs-git/tests/**", "packages/troupe/tests/**"]
```

- **Entries** are an exact path (`plugins/runner-scripted/README.md`) or a directory and everything under it
  (`docs/**`). No other wildcard is accepted.
- **Scopes may overlap.** A path in two scopes runs both. A path can't be both skipped and in a scope.
- **A scope's `tests`**, if it has one, lists the test directories it runs, each written `dir/**`. Every test under
  one counts as tagged with the scope (below). The list can't be empty or name a file, and `[skip]` has none.
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
runs the full check, so it can't widen itself and benefit in the same commit. This repository skips `openspec/**`,
and scopes its declarations (`dns`, `milestones`, `labels`), its OpenTofu configuration (`tofu`) and its docs (`docs`).

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

This repository's `ci.yml` asks in a `changes` job on each pull request. `check` is skipped (which counts as passed)
on `none`, runs `check.py` with the scopes it's given, and runs the full check when `changes` failed. The same job asks
`scripts/guard_tests_needed.py` whether the guard's tests must run on every OS and Python: only when a pull request
changes what they depend on (the guard's files, its tests, the declaration, the Python project or `ci.yml`). One
`guard tests` job reports for those legs, run or skipped. `main` runs everything after every merge.

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
`check.py` takes `--scope` too, for the scopes above.

**Or the declaration tags whole directories.** Every test whose file is under one of a scope's `tests` directories
counts as tagged with it, for `-m` and for the tag check below, as if the marker were written on it. `guard_pytest`
adds the marker as the tests are collected, before `-m` selects, so a `--scope` run selects the same tests serially
and under pytest-xdist (`-n`), and no `check.py` changes. That's for selecting whole suites, such as a package's and
those that reach it, without a `pytestmark` in every module.

A `tests` entry that no collected test is under fails the run, so a renamed directory can't quietly stop a suite
running: a test named `scripts/check-paths.toml::scopes.<name>.tests[<i>]` fails, naming the scope, the entry and the
fix. It carries the scope's marker, so the scope's own run fails too, rather than passing with nothing to test. A
run given no paths (the full check, or any `--scope`) checks every entry. A run given paths checks only the entries
inside them, so running one file or one suite never fails for another. A run selecting a different scope doesn't
fail for it either; the full run does. The rule is `guard.directory_tags` and `guard.unmatched_tests`.

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
- **Local files only from here:** every `--body-file`/`-F`, `--input` and `--attach` is inside the repository or the
  system temp directory. For `--attach <file>#<alt text>`, gh reads the whole value or the part before a `#`,
  whichever exists when it runs, so every one of those paths must be (refuse-substituted-pr-body, design D6).
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

A delivered file also keeps its source's mode, so the hooks are executable wherever they're delivered. The plan lists
any file whose mode differs, as a change for the owner to approve, and after the apply the App sets the mode in one
commit per repository (README, "Delivering the guard").

### Moving the OpenSpec version

`openspec-strict` runs the OpenSpec CLI at the version `.github/workflows/guard.yml` pins (`OPENSPEC_VERSION`). The
pin moves by pull request here, whose `guard` check validates every spec and active change here with the new version.
The same delivery takes it to every other governed repository, where it lands on `main` with no pull request, so a
stricter version can turn their `main` red at once. Before asking for the delivery plan's approval, run the new version
over each governed repository's `main` (`openspec validate --all --strict`), and name any failure in the pull request.

### The guard check's Node version

The CLI runs on the Node of the repository's `.nvmrc`, where it has one. That keeps a repository's Node version in one
place. Where there's no `.nvmrc`, the workflow writes its own pin (`NODE_VERSION`) to one in the run's checkout, and
never commits it. No step names a Node version as an input, because website's test refuses any workflow that does
(troupe-run/website#4, #155). `scripts/tests/test_guard_workflow.py` holds `guard.yml` to that rule.

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

## Standard changes

Some routine changes, such as a new troupe capability label, have their steps written once in
[standard-changes.md](standard-changes.md), so they go the same way every time. They follow this workflow like any
other change; what they add is the exact commands, and checks that refuse a wrong value.

## Dependabot pull requests

Every managed repository has Dependabot alerts and security updates on (spec: `repositories`). When an alert has a
fix, Dependabot opens a pull request for it.

troupe, website and this repository also get weekly version updates, from a `.github/dependabot.yml` that this
repository generates and delivers (spec: `dependency-updates`). Its schedule, cooldown and commit prefix are changed
in `tofu/dependabot.json`, and a repository's ecosystems and labels in `tofu/labels/dependabot.json`. Then run
`uv run scripts/dependabot_config.py`. An edit to the delivered file itself is refused in troupe and website, and
reverted by the next apply everywhere. Version updates leave out the workflows the guard delivers. Those are bumped
here, and the next apply delivers them. Their pull requests are titled `chore(deps): …` and carry only declared
labels, and they take the same paths as security updates, below.

OpenTofu's providers here (`tofu/.terraform.lock.hcl`) get no version updates: Dependabot's `opentofu` updates
proposed nothing for a `registry.opentofu.org` lockfile when probed (deliver-dependabot design D6). Update them by
hand with `tofu init -upgrade` in a change of their own. Its plan and apply need the owner's approval as usual.

Each Dependabot pull request in troupe, website and this repository gets an issue, from the `dependabot-issues`
workflow here (spec: `dependency-updates`). The issue is opened in the pull request's
repository by the `troupe-run-dependabot` App: type Task, label `dependencies`, the release in progress (the lowest
open milestone in `tofu/milestones.json`) as its milestone, and on the troupe roadmap board. Its title names the
dependency and the versions, and its body links the pull request, whose description has the release notes, and gives
the update type: patch, minor, major, or unknown when the versions can't be read. The workflow then adds
`Closes #<n>` to the pull request's description, and puts it back if Dependabot rewrites the description. When
Dependabot supersedes an update, the open issue is relinked to the new pull request rather than a second one opened.
A pull request closed without merging closes its issue as not planned, once an hour has passed with no successor,
and reopening the pull request reopens it. So to drop an update, close Dependabot's pull request, or comment
`@dependabot ignore this dependency` on it, rather than closing the issue. Add notes to the issue as comments: the
last line of its description, hidden on the page, says which pull request it tracks. Without it the workflow leaves
that issue and its pull request alone and fails, naming it, until the line is put back from the edit history. The
workflow reads only pull requests by `dependabot[bot]` and issues its App opened, and never checks out a pull
request. `uv run scripts/dependabot_issues.py` run locally only reads, and prints what it would do.

The workflow starts when Dependabot acts, so a pull request has its issue and closing line within an hour of
Dependabot opening or rewriting it, with nobody starting anything (#195). Each finished "Dependabot Updates" run starts
it: here directly, and in troupe and website through their `dependabot-dispatch` workflow, which the guard delivers.
That workflow starts this one with the `troupe-run-dispatch` App's token, kept in a main-only environment
(oob/README.md). A daily run, the backstop, does the same work, which includes what only time makes due, such as
closing an issue as not planned an hour after its pull request closed. Closing a Dependabot pull request by hand starts
no Dependabot run, so its issue closes at the next backstop. Any run that finds a pull request still missing its issue
or closing line over an hour after it last changed has found a missed event. The run fixes it, lists it in the
"Dependabot events missed" issue here, and fails. Only the daily run closes the issue, when it finds none, so it stays
open while a cause such as a missing key is still there. The schedule watch
reports the backstop if its schedule stops. To run the workflow by hand: `gh workflow run dependabot-issues.yml -R
troupe-run/infrastructure`.

In a governed repository (troupe, infrastructure, website), a Dependabot pull request takes one of two paths. The
`guard` check decides which (spec: `development-workflow`; dependabot-exemption).

- **A minor or patch update of dependency files merges as it is.** Its `dependabot/` branch matches no OpenSpec
  change, but `commit-branch-change` exempts it, because a ruleset in each of the three repositories lets only
  Dependabot create or update `dependabot/` branches (spec: `dependency-updates`). Every commit must change only
  `package.json`, `package-lock.json`, `pyproject.toml`, `uv.lock`, or a workflow's `uses:` lines, and name one
  dependency moving to a minor or patch release (`Bump zod from 4.6.5 to 4.6.7`), counted as the issue counts it. Every
  other check still applies, and its description closes its issue through the line `dependabot-issues` adds. A green
  one waits for your merge like any pull request.
- **Anything else takes an OpenSpec change**: a major update, one whose versions can't be read (such as a requirement
  range, `Update uv-build requirement`), or one changing other files. Its `guard` run fails on `commit-branch-change`,
  saying which condition failed. Take the update into an OpenSpec change for its issue like any other change: make the
  same bump on a branch named after the change, with a pull request that closes the issue. Merge that first: it closes
  the issue, and Dependabot then closes its own pull request as up to date (or close it yourself, with a comment
  linking the change). Closing Dependabot's pull request while its issue is still open closes the issue as not planned
  an hour later.

Only Dependabot can write to its branches, you included. To bring one up to date with `main`, comment
`@dependabot rebase`; GitHub's "Update branch" is refused by the ruleset. An open pull request is judged by the guard
on its own branch, so it picks up a change to these rules only once Dependabot rebases it.

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
- **The guard reads the command line, not the programs it runs.** A script the agent writes and then runs, a
  program that runs `git` or `gh` itself (`make`, Python's `subprocess`, a git alias starting with `!`), and a name
  hidden on purpose (`$'\x67h'`) aren't seen. A command built at run time from a variable (`$X`, `sh -c "$X"`,
  `& $c`) is refused when its text mentions `git` or `gh`, and isn't seen when it doesn't. Giving agents a GitHub login
  of their own, which GitHub would then hold to its rules, was parked in #101: troupe will decide actors'
  credentials (troupe-run/troupe#11).
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
