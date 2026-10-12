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
| The `guard` GitHub check (`.github/workflows/guard.yml`) | on every push to every branch, and every pull request | commit messages, the branch-change match, archived tasks | no: it's a required check, so a pull request can't merge while it's red (`tofu/required-checks.json`) |

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
| `commit-branch-change` | git | a commit on a branch with no matching OpenSpec change (active, or archived on that branch), or on a detached HEAD | propose the change, or switch to its branch |
| `commit-message` | git | a first line that isn't a Conventional Commit (`type(scope)!: subject`); `fixup!`, `squash!` and `amend!` are accepted when they name a Conventional Commit subject | use one of `feat fix docs build ci test refactor perf style chore revert` |
| `commit-checks` | git | a commit while tracked files have unstaged changes, or while `scripts/check.py` fails | stage or stash the changes; fix what the check reports |
| `archive-incomplete` | git | a commit that adds an archived change with an unticked task | finish and tick every task first |
| `edit-branch-change` | Claude | an Edit, Write, MultiEdit or NotebookEdit to a repository file when the branch has no matching change | switch to, or create, the change's branch |
| `pr-closes-issue` | Claude | `gh pr create` into this repository whose `--body` or `--body-file` doesn't close an issue, or that uses `--fill` or stdin. The target is named by `--repo`/`-R`, else `GH_REPO`, else it's this repository; a PR into another repository isn't checked, and a target that can't be read, or a clone with no remote, counts as this one | add `Closes #<issue>`, or name the other repository with `--repo` |
| `skip-hooks` | Claude | `--no-verify`, `git commit -n`, and setting, unsetting or overriding `core.hooksPath` | fix what the hook reports |
| `command-unparseable` | Claude | a `git` or `gh` command that can't be parsed (for example, unbalanced quotes) | simplify the command |
| `delivered-file` | git | in a repository that receives the guard, a commit that changes a file listed in `.github/guard-delivery.json` (the Claude Code hook refuses the edit too, and the `guard` check fails such a commit unless the infrastructure App made it) | change the file in `troupe-run/infrastructure`, and deliver it from there |
| `guard-tamper` | Claude | running the override command, naming a path in the override directory, or editing under `.git/`. **No override unlocks this rule.** | ask the owner |

The pre-commit check runs the full `scripts/check.py`. That takes 10–15 seconds on macOS and about a minute on
Windows, plus a one-time dependency download on a fresh clone. It's the same check CI runs, so a commit that passes
locally passes CI. The check is announced before it starts, its output streams as it runs, and it's stopped and the
commit refused after 10 minutes (`CHECK_TIMEOUT_SECONDS` in `scripts/guard.py`).

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

- `scripts/guard.py`, `.githooks/`, `.claude/settings.json` and `.github/workflows/guard.yml`;
- `.github/guard-delivery.json`, which lists the delivered files. Its presence is what marks a repository as one that
  receives the guard.

A hand edit to a delivered file shows as drift in the next plan, and an apply restores it. The `delivered-file` rule
refuses such an edit before it gets that far: change the file in `troupe-run/infrastructure` instead. The scripts'
own checks (`scripts/check.py`), and any other files, stay each repository's own.

## Known gaps

- **These hooks aren't a security boundary.** They stop honest shortcuts. A Bash command that writes a file isn't
  seen by the edit hook, though the git hooks catch it at commit time. A determined bypass is still possible.
  GitHub's rulesets and required checks are the hard backstop.
- **Pull requests opened through `gh api`** aren't checked for a closing reference by the Claude Code hook.
- **A bad commit message can reach a branch** if the local hooks were skipped, because GitHub doesn't reject it at
  push time on our plan. The `guard` check flags it at once, and blocks the merge.
- **The local hooks run the working tree's `guard.py`.** A commit that edits it can disable its own check. The
  `guard` check on GitHub runs the committed rules, and in a repository that receives the guard, the plan shows the
  edit as drift.
- **The `delivered-file` check trusts the commit's author.** It accepts a change to a delivered file whose author is
  the infrastructure App's bot. Commit metadata can be written by anyone, so this stops honest mistakes, not forgery.
- **Overrides are local.** The `guard` check on GitHub ignores them, so nothing granted on one machine excuses a
  commit on `main`.
- **Bash parsing is heuristic.** When a `git` or `gh` command can't be parsed, it's refused rather than guessed at.
- **Permission modes:** a Claude Code hook's deny holds in `bypassPermissions` mode (`--dangerously-skip-permissions`).
  Verified on 2026-10-11 on Windows: `git commit --dry-run --no-verify` was refused with `skip-hooks`. `dontAsk` mode
  is untested. The git hooks apply in every mode.
