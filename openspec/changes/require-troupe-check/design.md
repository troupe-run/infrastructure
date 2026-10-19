# Design: Require troupe's one check result

## Context

See proposal.md for why. What exists today:

- `tofu/required-checks.json` lists troupe's 12 legs `check (<os>, Python <version>)` (3 OSes × Python 3.12 to 3.15),
  `guard (workflow rules)` and `DCO`. `tofu/repositories.tf` maps each `app` to its id (`github-actions` = 15368) and
  passes the list to troupe's "protect main" ruleset.
- `scripts/tests/test_required_checks.py` checks infrastructure's list against its own workflows. It can't read
  troupe's, so it tests troupe only for the `guard` check.
- troupe's #117 (branch `ci-check-scope`) renames the matrix job's id to `check-legs`, keeps its reported names, and
  adds a job with id and name `check` that needs `changes` and `check-legs`, runs `if: always()`, and passes when
  every leg passed or all were skipped because `changes` answered `none`. Its `changes` job reads the previous head's
  `check` from app 15368 only. On #117's current head, GitHub reports all 12 legs, `check`, `guard (workflow rules)`
  and `DCO` as success.
- troupe's `ci-check-scope` tasks 4.1 to 4.3b proved on a throwaway repository, with a ruleset requiring `check` from
  GitHub Actions, that an archive push after a green code push skips the legs and merges, and that the same push
  after a failing one runs the full check and stays red. This repository's `run-checks-by-path` task 1.1 proved the
  unexpanded-name behaviour. Neither needs proving again here.

## Goals / Non-Goals

**Goals:**
- troupe's ruleset requires `check` (GitHub Actions), `guard (workflow rules)` and `DCO`, and nothing else.
- No window in which #117 can't merge.

**Non-Goals:**
- Any change to troupe's workflow. It's #117's.
- Reading troupe's workflow from this repository's tests. They stay offline, and troupe's file isn't here.
- The website's or infrastructure's required checks.

## Decisions

### D1. troupe requires `check` from GitHub Actions, in place of the 12 legs

One entry `{"context": "check", "app": "github-actions"}` replaces the 12, placed first, where the legs were. It's
pinned to GitHub Actions like every other Actions check, so a `check` status posted by anything else doesn't count,
and it's the same app #117's `changes` job reads the previous `check` from.

Alternative: keep the legs and add `check`. Rejected: a push that skips the legs would still wait for 12 contexts that
never report, which is the problem this change exists to fix.

### D2. This change goes first, then #117

The issue proposed troupe first. It's the other way round (owner, via the `ci-check-scope` session, 2026-10-19):

1. This change's pull request merges, and the owner approves main's apply.
2. #117 merges. Its runs report `check`, so it meets the new ruleset.

troupe-first can't work cleanly: #117's archive push changes only `openspec/`, after a head whose `check` passed, so
it skips the legs, and the old ruleset would wait for 12 contexts that never report. #117 would need the owner's
bypass to merge.

Cost of this order: between 1 and 2, a troupe pull request on the old `ci.yml` reports no `check` and can't merge.
The only other open one is release-please's #89, and release-please rebuilds it from `main` after #117 merges, so it
picks up the new `ci.yml`. The window should be minutes, so merge #117 straight after the apply.

Rollback is the reverse: restore the 12 legs here and apply first, then revert troupe. Reverting troupe first would
leave a `ci.yml` with no `check` job under a ruleset requiring `check`, which blocks every pull request, the revert's
own included. In between, a troupe push that skips the legs waits for them, which the owner's bypass can merge past.

### D3. A test pins troupe's list

`test_required_checks.py` gets a test that troupe's GitHub Actions checks include `check` and no name starting
`check (`. troupe's workflow can't be read here, so this can't prove the name matches what troupe's CI reports. That
was read from #117's checks. What it does catch is the regression this change fixes: someone restoring the legs, or
adding one back, by copying a name from a troupe run. The module docstring says what the test can and can't know.

Alternative: no test, relying on the plan. Rejected: the plan shows a change once, and nothing would notice the legs
coming back later.

### D4. Docs and comments say `check`

`tofu/repositories.tf`'s comment says troupe's checks were read from merged pull requests on 2026-10-12. It's updated
to say troupe's `check` was read from #117 on 2026-10-19. The README's rulesets section uses
`check (macos-latest, Python 3.13)` in troupe as its example of a check named as GitHub reports it. That's no longer
required, so the example becomes another reported name, and the paragraph says troupe's legs report through `check`,
as it already says for infrastructure's `guard tests`.

## Risks / Trade-offs

- [#117 doesn't merge soon after the apply, or is reworked so it no longer reports `check`] → troupe's pull requests
  can't merge in the meantime. Apply only when #117 is ready to merge (green, archived), and if #117 stalls, roll back
  as in D2.
- [#117 renames `check` before merging] → the plan here would name a check nobody reports. Before the apply, read
  #117's latest head's check runs again and check `check` is there, from GitHub Actions.
- [The test in D3 only pins this repository's list] → it can't see troupe's workflow change. The README says to change
  the list here whenever troupe renames a job, as it does today.

## Migration Plan

1. Merge this change's pull request (opened with #117 green and archived). The plan in its CI shows troupe's ruleset
   dropping 12 required checks and adding `check`, and no other change.
2. The owner approves main's apply.
3. Merge #117.
4. Verify on troupe: the ruleset requires the 3 checks, and a pull request whose latest push skipped the legs shows as
   mergeable (#117's archive push, or the next one).

Rollback is in D2.
