## Why

The guard's Claude Code hook can only refuse. For a `gh` command on its allow-list it says nothing, which hands the
call to Claude Code's own permission check: a rule, a prompt, or auto mode's classifier. So a command the guard allows
can still be stopped. In troupe-run/troupe#74, auto mode refused `gh pr ready 74`, and the owner had to run it by hand.
Shipping permission rules in the delivered `.claude/settings.json` was set aside in #30. Troupe can't add to that
file, and the rules would be a second copy of the allow-list. The owner agreed (#31, 2026-10-13) that the guard's
hook should answer "allow" for the `gh` commands it allows.

## What Changes

- **The guard's hook answers "allow"** for a Bash command that is exactly one `gh` command the guard grants, with no
  refusal and no override used. Every other command is handled as today: refused, or left to Claude Code.
- **What it grants is a subset of what it allows:** the `gh` reads, and the everyday issue, pull request, comment and
  project-item writes. It doesn't grant:
  - `gh api`, whose reach is much wider than the named subcommands;
  - `gh pr merge` and `gh pr checkout`;
  - workflow and run writes;
  - writes to throwaway repositories;
  - anything allowed only through an override.

  Those keep their prompt, or auto mode's check.
- **It grants only commands it fully understands:**
  - a single simple command, run through the Bash tool, not PowerShell;
  - no command substitution, variables, redirection, globbing, chaining or environment prefix;
  - every file the command reads (`--body-file`, `-F`) is inside the repository or the system temp directory.

  A hook's "allow" skips auto mode's classifier, so the guard has to do the classifier's job for what it grants.
- **Only the reviewed guard grants.** The hook answers "allow" only when the `scripts/guard.py` running is
  byte-identical to the one on `origin/main`. A guard edited on a branch can still refuse, but never grant. So an agent
  changing the guard can't approve its own next command.
- **A person's own `deny` and `ask` rules still win** over the hook's "allow". So does any `deny` the guard gives.
- **`docs/development-workflow.md`** says what is granted, and adds the new limits to its known gaps.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: two new requirements. "The guard grants the gh commands it allows" says what is granted,
  and that only the guard on `origin/main` grants. "A grant is only for a plain gh command" says what a granted
  command may contain.

## Impact

- `scripts/guard.py`: a grant decision beside the refusals in the `PreToolUse` hook, a table of what is granted, and
  the check that the running guard matches `origin/main`. It is a delivered file, so troupe gets it after the owner
  approves the apply.
- `scripts/tests/`: tests for the grant decision and the hook's output.
- `docs/development-workflow.md`.
- No change to `.claude/settings.json`: the hook is already wired for `Bash|PowerShell`.
- Out of scope: permission rules in `.claude/settings.json`, granting anything that isn't a `gh` command, owner-only
  acts, and `gh api`.
