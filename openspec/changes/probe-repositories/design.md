# Design

## Context

See proposal.md, "Why", for the findings. They're the guard on `main` (f1f86da), run through `shell_decisions`.
The parts that shape the approach:

- `gh_decision` exempts a command when `throwaway_kind(repository)` names a throwaway repository. The repository
  comes from `-R`/`--repo`, `GH_REPO=` before the command, the positional of `gh repo create|delete|archive|
  unarchive|edit`, or the `repos/<owner>/<name>` of a `gh api` endpoint. Any other way of naming one isn't seen.
- `read_shell` keeps an expansion in the word as written: `troupe-run/$P`, `troupe-run/${P}`,
  `troupe-run/$(echo x)`, `` troupe-run/`echo x` `` and `troupe-run/infra-probe-$N` all reach `gh_decision` with
  the `$` or backtick in them. `normalise_repository` then reads one as a repository that isn't a throwaway one, so
  the command falls through to `owner-only` or `gh-allow-list` with that rule's usual message.
- GitHub doesn't allow `$` or a backtick in a repository name, so a name holding either is always built by the shell.
- A GraphQL mutation reaches `_classify_api` with no repository (`repository = None`). `updateRepository` isn't in
  `GH_MUTATIONS_ALLOWED`, so it's refused as unlisted by name, for every repository.

## Goals / Non-Goals

**Goals:**

- A refusal caused by a shell-built repository name says so, and names the fix.
- One place in the docs says what an agent may do in a throwaway repository, and what isn't exempt.
- Tests that fail if the documented behaviour changes.

**Non-Goals:**

- Resolving a variable's value. The guard reads the command line, not the shell's state ("Known gaps"), and a
  value read from the session's environment could be different when the command runs.
- Allowing anything that's refused today. The set of allowed commands doesn't change.
- A new rule name. The refusal keeps the rule it has today (`owner-only` or `gh-allow-list`), so an owner's
  override of that rule still applies.

## Decisions

### D1. Add the reason to the refusal, keeping its rule

When `gh_decision` refuses a command whose named repository (as found above) contains `$` or a backtick, it returns
the same rule with a longer message. The problem adds: "The repository is named by the shell (`<word>`), so the
guard can't tell whether it's a throwaway repository and judges it as a live one." The fix adds: "For a throwaway
repository (`troupe-run/infra-probe-*`, `spike-*`, `bakeoff-*`), write its name out." The rule's own fix stays
first, because the command may target a live repository.

The check is one helper (`_named_by_shell(repository)`, true for `$` or a backtick), applied to each refusal
`gh_decision` makes with a repository named, on both the `gh api` path and the subcommand path. It's not applied to
a decision that allows, or to a refusal with no repository named (GraphQL, `gh auth`). A name whose owner is written
out and isn't `troupe-run` (`someone-else/$P`) gets no hint, since it can't be a throwaway one whatever the shell
fills in. One whose owner is built too (`$OWNER/$REPO`, or `$R` alone) does, since it could be. Found while
applying: an existing test of `gh api -X PUT repos/$OWNER/$REPO/pulls/$PR/merge` now gets the hint, which is right,
because a merge in a probe is allowed. So that test checks that the message starts with the merge message. For a
`gh api` endpoint, the name in the hint is taken from the command as written, case kept, because the guard
lowercases the endpoint it matches.

*Alternatives:* a new rule, `throwaway-name-unreadable`. That would change which override excuses the command, and
it adds a rule for what is really an explanation, so no. Refusing such a command as `command-unparseable`
would say "simplify the command" instead of saying what's wrong, and would refuse a `gh` read that's allowed today
(`gh repo view troupe-run/$P`), so no. Resolving `$P` from an assignment earlier in the same command
(`P=x; gh ... $P`) would cover #216's exact case but not `export`, a sourced file or `read`. It's a partial shell
interpreter, which the guard avoids ("Known gaps").

### D2. GraphQL mutations stay unexempt on throwaway repositories (#217)

The owner decided on 2026-10-29: keep one route per write (#30). On a probe, `gh repo edit`, or the REST call where
`gh` has no flag (`gh api -X PATCH repos/troupe-run/infra-probe-x -F has_pull_requests=false`), already does what
`updateRepository` does, and both are allowed. Exempting a mutation would mean looking up its `repositoryId`
through `gh` before deciding, as `resolveReviewThread` does. That adds a network call, a failure mode (refuse when
the lookup fails), and a second route for the same write.

The REST writes #217 names need no change: `POST repos/<probe>/git/refs` and `PATCH repos/<probe>` are allowed
when the name is written out. #136's refusal of `git/refs` matches the shell-built-name case: the same `$P` was in
use in that session. #136 didn't record the command, so this is the likely cause, not a proven one.

### D3. One "Throwaway repositories" section in the docs

`docs/development-workflow.md` gets a section after "Which commands the guard reads". It says:

- what a throwaway repository is (`troupe-run/infra-probe-*` to delete when done; `spike-*` and `bakeoff-*` are
  records that are kept);
- what an agent may do there, with the command for each. Create it (`gh repo create`), configure it (`gh repo edit`,
  `gh api` REST writes such as `PATCH repos/<probe>`, rulesets, secrets, variables, labels), push to it (a `git push`
  from a scratch clone, or `gh api` `git/refs` and contents writes), open, merge and close pull requests and issues
  in it, and delete it (`infra-probe-*` only). It also says a `gh pr create` into a probe isn't checked for a closing
  reference;
- what isn't exempt: the login's credentials, extensions and aliases, GraphQL mutations (D2), and a name built by
  the shell (D1);
- that installing the App on a probe, before its ruleset can name the App as a bypass actor, is still the owner's
  (throwaway-repo-naming).

The `owner-only` row's exemption sentence is cut down to one line pointing to this section, and so is the "Known
gaps" bullet. That keeps the list in one place. The `gh-allow-list` row gets the same pointer, because the
exemption covers its writes too, which the docs don't say today.

### D4. Tests pin the documented behaviour first

In `scripts/tests/test_guard_gh.py`:

- **Before the guard changes**, tests that pass on `main` today: a shell-built name (`$P`, `${P}`, `$(...)`,
  backticks, `infra-probe-$N`, through `-R`, `GH_REPO=` and a `gh api` endpoint) is refused with the same rule as a
  live repository; #216's chained command is refused only for its `gh repo create`; a literal probe's
  `POST git/refs`, `PATCH repos/<probe>` and `PUT contents` are allowed; `updateRepository` is refused as unlisted;
  `gh repo view troupe-run/$P` (a read) is allowed. They pin what must not change (D1's non-goal).
- **Then** D1's message: the shell-built cases' message names the word and the fix, and a live repository's
  refusal (`troupe-run/my-repo`) doesn't mention it.

## Risks / Trade-offs

- [The hint suggests writing out a name the agent meant to be a live repository] → It stays second to the rule's own
  fix, and writing the name out doesn't exempt a live repository: it's then refused with the plain message.
- [A repository named in a way `gh_decision` doesn't read (for example `gh pr view <url>`)] → Unchanged: no hint,
  same refusal as today. The docs section says the exemption needs `-R`, `GH_REPO` or the name as a positional.
- [The delivered `guard.py` changes in two repositories for a message] → It's delivered by the usual plan, which the
  owner approves. No behaviour changes in troupe or website.

## Migration Plan

1. Merge. CI's plan shows the delivered `scripts/guard.py` changing in **troupe and website** (`guard_targets` in
   `tofu/guard_delivery.tf`) and nothing else. The owner approves the apply.
2. Rollback is reverting the commit. The next plan delivers the old file.
3. #216 is closed by the pull request. A successor "Minor corrections to batch" issue is opened on the roadmap board,
   and the minor-corrections memory is updated to name it.
