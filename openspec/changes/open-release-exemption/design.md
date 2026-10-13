## Context

#33 (archived change `release-please-prs`) built the exemption in `release_branch_by_the_bot` in `scripts/guard.py`:
a `release-please--` branch whose commits not on `origin/main` are all authored by `RELEASE_AUTHOR_EMAIL`, with at
least one, skips the branch-change rule in `run_ci`. Its design D2 left the constant `None` until the App existed, and
D5 said the author is self-declared, so the hard check has to be a ruleset that lets only the App write those
branches. #34 (archived change `release-app`) applied that ruleset on troupe: `github_repository_ruleset.release_branches`
in `tofu/release.tf`, read back live on 2026-10-13 as `creation`, `update` and `deletion` over
`refs/heads/release-please--*`, with the one bypass `Integration` 5300488 (`always`).

The guard runs in two repositories: troupe, by delivery (`tofu/guard_delivery.tf`, `guard_targets`), and this one,
its source, through the same `guard.yml`. The ruleset is on troupe only, and the release App is installed on troupe
only (`oob/app-installations.json`).

The exemption's tests already exist (`scripts/tests/test_guard_push_and_ci.py`, "release-please-prs" section); they
monkeypatch a test address into the constant.

## Goals / Non-Goals

**Goals:**
- Release PRs on troupe pass the branch rule, and only where GitHub enforces who wrote the branch.
- The address in the guard is the one release-please's commits will carry, and a test shows the exemption with it.

**Non-Goals:**
- Making the author check stronger on its own (signatures, API calls): #33 design D5 rejected those, and it still
  holds.
- The `delivered-file` rule's same reliance on a self-declared author (#35).

## Decisions

### D1. The exemption applies only in repositories named in the guard as having the release ruleset

A new constant beside `RELEASE_AUTHOR_EMAIL`:

```python
RELEASE_REPOSITORIES = frozenset({"troupe-run/troupe"})
"""Where a ruleset lets only the release App write release-please--* branches (tofu/release.tf).
The exemption trusts a commit's author only here; anywhere else it would be the only check."""
```

`release_branch_by_the_bot` also takes the repository and returns `False` unless it's in the set. Without this,
filling the constant opens the exemption here too: a push to `troupe-run/infrastructure` of a `release-please--`
branch with `--author` set to the bot would skip the branch rule with only the author check behind it, which is what
#33 D5 and #42 both say isn't enough.

Alternatives:
- *Accept it, since the branch rule is all it skips* (#33's risk list: review and the required checks still apply).
  It's true, but it contradicts the stated reason the exemption is safe, and the cost of closing it is small.
- *Add the release ruleset here too.* That's a ruleset for an App not installed here, guarding branches release-please
  never writes here. More org state for no use.
- *Turn the exemption on by a file only troupe has* (as `.github/guard-delivery.json` turns on `delivered-file`).
  Nothing like that exists for releases, and adding one is a second place recording what the ruleset already records.

The set is a second record of "which repositories have the ruleset", beside `tofu/release.tf`. D4 ties the two with a
test so they can't drift silently.

### D2. The repository is where the branch lives, read from GitHub; an unnamed one exempts nothing (owner, 2026-10-14)

`github_ci_inputs` returns one more value, the repository the checked branch lives in, and `run_ci` passes it to
`release_branch_by_the_bot`:

- **push:** `GITHUB_REPOSITORY`, which GitHub sets on every Actions run.
- **pull_request:** `pull_request.head.repo.full_name` from the event payload. For a PR from a fork that's the fork, so
  a fork's `release-please--` branch, which troupe's ruleset doesn't cover, never matches the set. Using
  `GITHUB_REPOSITORY` here would name troupe and exempt it.

`guard.py ci` gains `--repository` for a local dry run, beside `--branch` and `--title`.

Absent and malformed are kept apart. `head.repo` is `null` when the fork has been deleted: that's absent, so the value
is `None` and nothing is exempt. A `head.repo` that's present but isn't an object with a string `full_name` is a
malformed payload: it's refused like an unreadable title (a new `UnreadableHeadRepositoryError`, reported by
`run_ci_entry` under `commit-branch-change`, saying to re-run and, if it fails again, to tell the owner with the run's
URL). An unset `GITHUB_REPOSITORY` on a push, or no `--repository` on a local run, is absent: `None`, nothing exempt.
A value that's present needs no format check, because it's only compared with the set.

Alternative: `GITHUB_REPOSITORY` plus a separate check that the head repository equals it. Two values for one
question; the head repository alone answers it.

### D3. The address is filled as observed, and `None` stays the rollback

`RELEASE_AUTHOR_EMAIL = "341990208+troupe-run-release[bot]@users.noreply.github.com"`. The ID is from
`gh api 'users/troupe-run-release%5Bbot%5D' --jq .id` (341990208, type `Bot`, 2026-10-13). The form is the one GitHub
gives an App's API-made commits, the same form `DELIVERY_AUTHOR_EMAIL` has and the delivery commits on troupe show. The
type stays `str | None`: `None` still exempts nothing, so if the App or ruleset ever goes, closing the exemption is one
line. The docstring drops "None until the App exists" and says: filled once the ruleset was applied (#41); the ruleset
is the hard check and the author check alone isn't; it applies only in `RELEASE_REPOSITORIES`.

### D4. A test keeps the guard's set and the ruleset declaration in step

A test reads `tofu/release.tf`, finds the `github_repository_ruleset` resource that includes
`refs/heads/release-please--*`, and checks that each repository in `RELEASE_REPOSITORIES` is the one it declares (today
`module.repo_troupe.name`, which `tofu/repositories.tf` names `troupe`). It's a text check, not an HCL parser: enough to
fail when the ruleset is removed or moved to another repository, which are the edits that would leave the exemption
open. The guard is standard-library only, and so is this test.

Alternative: check the live ruleset through the API in CI. That makes the guard's tests depend on the network and a
token; the daily plan already shows the live ruleset drifting from its declaration.

### D5. The existing tests switch to the real address and a repository

The release-please tests stop monkeypatching a test address and use `guard.RELEASE_AUTHOR_EMAIL` with a
`troupe-run-release[bot]` name, and pass `troupe-run/troupe`. Their commits take their author from the same constant,
so they check the exemption's logic, not the address: a wrong address would pass them. One more test compares the
constant with the ID and login written out from the API reading, which catches a typo or a stray edit. Only troupe#23's
first release PR shows that release-please's commits carry it. The `None` test keeps its monkeypatch. New tests: the bot's release branch in
`troupe-run/infrastructure` fails; with no repository it fails; `github_ci_inputs` returns `GITHUB_REPOSITORY` for a
push, the head repository for a pull request (a fork's name for a fork, `None` for a deleted one), and refuses a
malformed `head.repo` naming it.

## Risks / Trade-offs

- [release-please writes its commit with another identity (a configured author, or the user behind a token)] →
  troupe#23 design D9 sets only `signoff`, and an App token's API commits carry the bot's address. The first real
  release PR shows the author; if it differs, the release PR fails closed on the branch rule, and a follow-up names
  the observed identity.
- [The guard's own copy can be edited in the push being checked] → An existing known gap (docs: "The local hooks run
  the working tree's `guard.py`" and the forged-delivery entry); on troupe the plan shows the edit as drift.
- [`RELEASE_REPOSITORIES` and `tofu/release.tf` disagree] → D4's test fails.

## Migration Plan

1. On this branch: the code, the tests, the docs and the spec; `uv run scripts/check.py` passes. A local dry run with
   `guard.py ci --repository troupe-run/troupe` on a throwaway local repository shows the bot's branch exempt and
   another author's refused, and with `--repository troupe-run/infrastructure` or a fork's name refused.
2. PR closing #42; CI green on all three OSes; the plan shows only `scripts/guard.py` delivered to troupe.
3. Archive on the branch; the owner merges and approves the apply.
4. Check troupe's `scripts/guard.py` matches and troupe's `guard` run on the delivery commit passes.
5. When troupe#23 opens its first release PR, check its `guard (workflow rules)` run passes, and say so on #42.

Rollback: set `RELEASE_AUTHOR_EMAIL` back to `None` (or empty `RELEASE_REPOSITORIES`) and deliver. Release PRs then
fail on the branch rule again; nothing else changes.
