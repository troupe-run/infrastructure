# Design

## Context

- **Today's hook** (`scripts/guard.py`, `run_claude_pre_tool_use`):
  - For a Bash or PowerShell call, `shell_decisions` splits the command (`split_command`, heredoc bodies dropped) and
    runs `guard_tamper`, `skip_hooks`, `pr_closes_issue` and `gh_decision` on each simple command.
  - `first_refusal` returns the first refusal not excused by a one-use override.
  - A refusal prints `permissionDecision: "deny"`. Otherwise the hook prints nothing.
- **The splitter is heuristic.** It splits on `&&`, `||`, `;`, `|`, `&` and newlines, and `shlex` reads the words. It
  doesn't treat `$(...)`, backticks, `$VAR`, redirection, subshells or globs as special. That's enough for refusing,
  where a missed word means a missed refusal and Claude Code still decides. It isn't enough for granting.
- **The allow-list** is `GH_READS`, `GH_WORKFLOW_WRITES` and the throwaway-repository exemptions. `gh_decision`
  returns ALLOW for all of them.
- **Hook behaviour, measured locally** (2026-10-13, headless `claude -p` with a stub hook in a scratch repository;
  #31 has the table):
  - A hook's JSON `deny` beats a matching allow rule, in manual and auto mode.
  - A hook's `allow` replaces the prompt.
  - A person's own `deny` or `ask` rule beats a hook's `allow`.
  - **A hook's `allow` skips auto mode's classifier, even a `hard_deny` rule.** With
    `autoMode.hard_deny: ["Never run any command containing the text CANARY_BLOCK"]`, a `curl` to example.com carrying
    the canary was denied twice. With the hook answering `allow`, it ran twice (HTTP 200).

  The docs don't state this order. The hooks page says only that a hook's deny holds and its silence doesn't approve.
  Auto mode's docs list what the classifier stops by default, including sending local data away.
- **The hook runs the working tree's guard** (`${CLAUDE_PROJECT_DIR}/scripts/guard.py`). On a change branch in this
  repository, that's the agent's own edited copy. In troupe, agents can't edit it (`delivered-file`).

## Goals / Non-Goals

**Goals:**
- What the guard allows for everyday `gh` housekeeping runs without the owner, in every permission mode.
- A grant is never wider than the guard can check. When in doubt, no grant, and Claude Code decides as today.
- The allow-list stays the one source. No permission rules in the delivered settings.

**Non-Goals:**
- Granting anything that isn't a `gh` command, or `gh api`.
- Granting through PowerShell. Its quoting and expansion rules differ, and the guard's splitter is written for POSIX
  shells.
- Making the hooks a security boundary. They still aren't (docs, Known gaps). This change keeps a grant from being
  easier to abuse than auto mode's check, which it replaces.

## Decisions

### D1. Grant a subset of the allow-list, named in its own table

`GH_GRANTED` lists the `(group, subcommand)` pairs the hook grants: every pair in `GH_READS` and
`GH_WORKFLOW_WRITES` except these.

| Not granted | Why |
|---|---|
| `pr merge` | Merging is consequential. Rulesets stop most merges, but a prompt is cheap here. |
| `pr checkout` | It switches the local branch under the session. |
| `run download`, `repo clone` | Reads, but they write local files to any path the command names (`-D`, the clone's directory). Found during apply. |
| `workflow run`, `run rerun`, `run cancel` | These start or stop CI, including the `apply` workflow's runs. |
| `gh api` | Any endpoint, any method the allow-list allows, and `-F field=@file` reads local files. |
| throwaway-repository writes | Allowed by naming convention, which is fine for "don't refuse" but too broad to grant. |

A test checks that `GH_GRANTED` is a subset of `GH_READS ∪ GH_WORKFLOW_WRITES`, so a grant can never reach something
the guard refuses.

*Alternative:* grant everything the guard allows. Rejected, because the allow-list was built as "don't refuse" (#30's
discussion). Its broader entries are safe only because Claude Code still decides after it.

### D2. Grant only a command the guard fully understands

`grantable(command, root)` reads the raw command text, not `split_command`'s output, and grants only if every check
passes:
- Outside quotes, the text has none of `$`, `` ` ``, `\`, `<`, `>`, `|`, `&`, `;`, `(`, `)`, `{`, `}`, `*`, `?`,
  `[`, `]`, `~`, `!`, `#` or a newline. Inside double quotes, only `$` and `` ` `` rule a grant out, because they
  still expand there. Inside single quotes, nothing does. This excludes chaining,
  substitution, variables, redirection, heredocs, globs and comments in one rule, and still grants
  `--title "Fix #3"` or `--jq '.comments[]'`.
- `shlex.split` gives the words, and the first word is exactly `gh`: no path, no `VAR=value` prefix.
- `gh_decision` would allow the words, and `(group, subcommand)` is in `GH_GRANTED`.
- Every value of `--body-file`/`-F` (and `--input`, for completeness) resolves inside the repository root or
  `tempfile.gettempdir()`, after resolving symlinks. `-` (stdin) is no grant.

The PreToolUse payload says which tool is calling. Only `Bash` is granted.

*Alternative:* reuse `split_command` and check each simple command. Rejected, because its heuristics are tuned to not
miss refusals. A grant needs the opposite bias: anything unusual gets no grant.

### D3. Only the reviewed guard grants

Before granting, the hook compares the git blob hash of the running guard file (`Path(__file__)`) with
`git rev-parse origin/main:scripts/guard.py`. A grant needs them to be equal. Any error is no grant: no `origin/main`,
no `scripts/guard.py` there, or git failing.

- In troupe, `origin/main` holds the delivered guard, and the working copy can't be edited by agents. It grants once
  the delivery has been fetched.
- In this repository, a change branch that edits `guard.py` makes the hook stop granting until that edit is on
  `origin/main` (reviewed, merged) and fetched. The hook keeps refusing as before.

*Why `origin/main` and not `main`:* local `main` lags until someone pulls, and both are refs an agent could move with
plumbing commands. Neither makes a security boundary (Risks). `origin/main` is what a fetch keeps in step with GitHub.

### D4. The decision order in the hook

1. Run today's refusals. Any refusal not excused by an override is denied, as now.
2. If a refusal was excused by an override, give no grant. The override lets the command through to Claude Code, as
   now.
3. If the tool is `Bash`, D2 holds and D3 holds, print `permissionDecision: "allow"` with a reason naming the guard,
   such as `guard: gh pr ready is on the guard's allow-list (granted)`.
4. Otherwise print nothing.

A deny always comes before a grant, so a command that one rule refuses and another would grant is refused.

### D5. Docs

`docs/development-workflow.md`:
- A short section, "What the guard grants": the `GH_GRANTED` table, the D2 conditions and D3.
- **Known gaps** gains two entries. A grant skips Claude Code's own checks, auto mode's classifier and its `hard_deny`
  rules included, so the guard's conditions are the only check on a granted command. And D3's comparison uses local
  git refs, which an agent can move.

## Risks / Trade-offs

- **A grant skips auto mode's classifier entirely**, `hard_deny` included (Context). The guard takes on that job for
  what it grants. D1 keeps the set small, and D2 keeps each command plain. The body-file rule exists because sending
  local data away is exactly what the classifier would otherwise stop.
- **Files under the temp directory can be sent.** Agents write PR bodies there (the scratchpad), so it has to be
  allowed. A secret written there could then be posted to an issue without a check. That's narrower than today's gap,
  where an agent with `gh` can post anything once the person approves the prompt.
- **D3 compares against local refs.** An agent could rewrite `refs/remotes/origin/main` locally to match an edited
  guard. That needs a deliberate plumbing command, which the guard's other rules would flag only partly. The hooks
  aren't a security boundary, so this stops accidental self-grants, not a determined agent. Recorded under Known gaps.
- **The settings file can change the hook.** An agent on a branch here can edit `.claude/settings.json` to run another
  script. That was true before this change. It isn't widened, and remains a known gap.
- **Undocumented behaviour.** The grant depends on Claude Code applying a hook's "allow" before its classifier, which
  was measured, not documented. If a Claude Code release changes it, a grant becomes a no-op (back to today's
  behaviour), not a widening. A person's `deny` and `ask` rules still win, as documented.
- **Merge order:** #33 also edits `scripts/guard.py` and will probably merge first. This change rebases onto it and
  reruns its tests.
