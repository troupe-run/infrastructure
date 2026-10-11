# troupe-run/infrastructure

This repository says how the troupe-run organisation builds software. It holds the org as code (OpenTofu, in
`tofu/`) and the development workflow every governed repository follows: its spec, and the guard that enforces it.
See [README.md](README.md) for the layout and [openspec/config.yaml](openspec/config.yaml) for the constraints every
change respects.

## How work happens here

Every change, however small, follows one path. The full guide is the org's
[CONTRIBUTING.md](https://github.com/troupe-run/.github/blob/main/CONTRIBUTING.md).

1. **An issue** says what and why.
2. **An OpenSpec change** says how: `/opsx:propose <name>`, on a branch named exactly `<name>`.
3. **`/opsx:apply`** builds it. A task is ticked only when its verification has run and passed.
4. **A pull request** closes the issue (`Closes #n`), with the plan as evidence when it changes the org.
5. **`/opsx:archive`** runs on the branch before merging. The owner merges by rebase.
6. **After the merge**, comment on the issue with the PR and the archived change.

Commits are Conventional Commits, signed off, and `uv run scripts/check.py` passes before each one.

**Nothing is applied to the org without the owner's approval of the saved plan.** Test GitHub behaviour on a
throwaway repository, never a live one. Secrets come from 1Password at run time and are never printed or pasted.

## Guardrails

Git hooks and Claude Code hooks enforce the path above. [docs/development-workflow.md](docs/development-workflow.md)
lists every rule. When one refuses an action:

- **Follow its fix.** Don't look for another route to the same action. The hooks aren't a security boundary, so
  getting round one is possible, and it's exactly the shortcut they exist to stop.
- **If the rule seems wrong for the situation, stop and ask the owner.** Only a person, in their own terminal, can
  grant an override, and every use is logged.

The guard's files here are the source of the copies in other repositories. A change to them reaches those
repositories only by a delivery: a plan the owner approves, made from a commit whose CI is green on all three OSes.
