# Proposal

## Why

During #136's probe the guard refused two commands on `infra-probe-20261028-prs`: a chained `gh repo create
troupe-run/$P ...` (#216) and a `POST repos/.../git/refs` (#217). The agent didn't know why, and took an undocumented
route round the second. Reproduced on the current guard, both refusals have one cause. The repository was named
through a shell variable (`$P`), so the guard couldn't tell it was a probe and judged it as a live repository. That
is the safe answer. But the refusal says only "only the owner changes … administration", and the docs don't say that
the exemption depends on the name as written. They also list the exemption only under `owner-only`, so nothing says
what an agent may do in a probe (#217).

Findings (guard on `main`, f1f86da, checked through `shell_decisions`):

- `gh repo edit --help`, piped or chained, is a help request either way. The row in #216 is right about help.
- `gh repo create troupe-run/$P` and `"troupe-run/$P"` are refused as `owner-only`. The same command with the name
  written out is allowed.
- `gh api -X POST repos/troupe-run/infra-probe-x/git/refs`, `gh api -X PATCH repos/troupe-run/infra-probe-x`,
  contents writes, `gh pr create`/`merge`, `gh secret set`, rulesets and `gh repo delete` on a probe named literally
  are all allowed. `repos/troupe-run/$P/git/refs` is refused as an unlisted write, which matches #136's refusal.
- GraphQL `updateRepository` is refused everywhere. A mutation names a node ID, not a repository, so the guard can't
  tell a probe from a live repository.
- A `git push` to a probe goes ahead. The Claude Code layer's git rules don't look at the target, and a scratch
  clone of a probe has no guard hooks.

## What Changes

- **Refusal says why (#216, owner 2026-10-29):** when the repository a refused `gh` command names contains a shell
  expansion (`$` or a backtick), its `owner-only` or `gh-allow-list` refusal adds that the name is built by the shell,
  so it can't be judged a throwaway repository, and that writing the name out lets a throwaway one go ahead. What's
  refused doesn't change.
- **The docs say what an agent may do in a probe (#217):** `docs/development-workflow.md` gets one place,
  next to the `owner-only` exemption, that says what the guard allows in `troupe-run/infra-probe-*`: create,
  configure (settings, rulesets, secrets), push branches, open and merge pull requests, and delete. It also says
  that `spike-*` and `bakeoff-*` are kept, that the name must be written out, and what isn't exempt: credentials,
  extensions and aliases, and GraphQL mutations.
- **GraphQL stays refused on probes (#217's decision, owner 2026-10-29):** each write keeps one route (#30).
  `gh repo edit`, or the REST call where `gh` has no flag, already does it on a probe. Allowing `updateRepository`
  would need a network lookup of its node ID, and would add a second route.
- **Tests pin what's documented:** a name built by the shell isn't exempt, a chained help request still goes
  ahead, a literal probe's `git/refs` and `PATCH` writes are allowed, and `updateRepository` naming a probe is
  refused.
- `#216`'s only item is fixed here, so this change closes it. A new collecting issue takes its place.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: a requirement added: a throwaway repository is judged by the name the command writes. A
  name built by the shell isn't exempt, and its refusal says so. A GraphQL mutation isn't exempt on a throwaway
  repository.

## Impact

- `scripts/guard.py`: the refusal for a shell-built repository name. This file is delivered, so the plan changes
  `scripts/guard.py` in **troupe and website** (`guard_targets`), after the owner approves it.
- `scripts/tests/test_guard_gh.py`: the tests above.
- `docs/development-workflow.md`: the `owner-only` row's exemption, and a "Throwaway repositories" section that the
  row and "Known gaps" point to.
- No OpenTofu resource changes besides the delivered file. No behaviour change for any command: only one message
  gets longer.
- Closes #216 and #217. The successor collecting issue goes on the roadmap board.
