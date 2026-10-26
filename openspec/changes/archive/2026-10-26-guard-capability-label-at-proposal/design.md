# Design

## Context

See proposal.md for why. Current state, read on 2026-10-26 at infrastructure `802e6f3` and troupe `main` `2d24fcf`:

- **The line.** troupe#170 design D2 fixed its shape: the first non-blank line of `## Purpose`, `Capability: ` then
  one or more backticked labels joined by `, `. A new spec's delta carries it at the top of its `## Purpose`, which
  OpenSpec copies into the main spec on archive. For a spec that already exists, OpenSpec ignores a delta's Purpose,
  so its labels change only by editing `openspec/specs/<name>/spec.md` directly (troupe#170 D1, D3; troupe's
  `openspec/config.yaml`, Working). All 25 of troupe's specs have the line, and every label they name is declared.
- **The parser** is in `scripts/oob.py` (`purpose_lines`, `capability_line`, `capability_labels`,
  `MalformedCapabilityLineError`, `CAPABILITY_LINE`, `CAPABILITY_SHAPE`; spec-capability-label-check design D2).
  `oob.py` isn't delivered. `scripts/guard.py` is, and is standard library only, one file.
- **The CI rules.** `run_ci_entry` runs the git-level rules (`run_ci`), then `openspec-strict` with a scope from
  `openspec_scope()`: the main specs and active changes the range changes; everything on a push to `main` or when the
  range changes `OPENSPEC_ALL_PATHS`. `openspec-strict` is GitHub-only and not overridable, and fails rather than
  passes when it can't run.
- **The repository.** `github_ci_inputs` returns the head repository for a pull request (a fork's name for a fork),
  which decides the release-branch exemption. `GITHUB_REPOSITORY` is the repository the run is in: troupe for a fork's
  pull request into troupe.
- **The workflow.** `.github/workflows/guard.yml` has `permissions: contents: read` and passes no token to the guard
  step. troupe-run/infrastructure is public, so the run's token can read its contents.
- **The standard change** is `docs/standard-changes.md`, section "A capability label" (anchor `#a-capability-label`):
  its first step opens a sub-issue under the needing issue's Epic, which then blocks the troupe issue that needs it
  (#153's owner comment, 2026-10-26). There's no command or skill to name.

## Goals / Non-Goals

**Goals:**
- A troupe push that proposes a spec, or edits a spec's line, fails on that push when a named label isn't declared on
  infrastructure's `main`, and says how to add it.
- One reading of the line, used by both the guard and the drift check.

**Non-Goals:**
- Reading a delta's Purpose for a spec that exists. OpenSpec ignores it, so judging it would refuse a line that
  changes nothing, and passing it would suggest the labels changed. Saying "OpenSpec ignores this" is a separate
  improvement, not needed for #153.
- Checking the label is *applied* on GitHub. #153 asks for declared on `main`: the standard change's pull request
  merges, then its apply follows, and a troupe change proposed in between is right to pass.
- A local hook. See D4.

## Decisions

### D1. A new rule, `capability-label`, GitHub-only and not overridable

It's a rule of its own, not part of `openspec-strict`, because it fails for a different reason with a different fix,
and the refusal names the rule. It joins `RULES` beside `OPENSPEC_RULE`, not `OVERRIDABLE_RULES`: no override is
consumed on GitHub. It runs in `run_ci_entry` after `openspec-strict`, and both refusals are reported in the same run.

It applies only where the run's repository (`GITHUB_REPOSITORY`) is in `CAPABILITY_REPOSITORIES`, a constant naming
`troupe-run/troupe`, the way `RELEASE_REPOSITORIES` names where the release exemption applies. The run's repository,
not the head repository: a fork's pull request into troupe is judged against troupe's labels.

Rejected: applying it in any repository with `Capability:` lines. infrastructure's and the website's specs have none,
so every spec would fail "no label" there. Rejected: keying it on the labels file existing, since the file lives in
infrastructure, not in the repository being checked.

### D2. The scope

Reuse `openspec_scope()` for which main specs and active changes the range touches, and the same "everything" cases.
Then:

- each main spec in scope is judged from `openspec/specs/<name>/spec.md` at the head;
- for each active change in scope, each `openspec/changes/<c>/specs/<name>/spec.md` whose `openspec/specs/<name>/`
  doesn't exist at the head is judged, as the spec `<name>` proposed by change `<c>`.

Archiving creates the main spec and moves the change under `archive/`, so the archive commit judges the main spec,
and the delta is no longer active. Specs are flat in troupe, as `oob.py` already assumes.

Rejected: a scope of its own. The two rules would then disagree about what a range touches, and `openspec_scope()`
already encodes the guard-changes-everything case that a delivery needs.

### D3. The labels are read from GitHub when the check runs

`GET https://api.github.com/repos/troupe-run/infrastructure/contents/tofu/labels/troupe.json?ref=main` with
`Accept: application/vnd.github.raw+json`, `urllib.request` as `scripts/commit_state.py` uses it, a named timeout
(`CAPABILITY_LABELS_TIMEOUT_SECONDS`, 30), and `Authorization: Bearer $GITHUB_TOKEN` when the token is set. The read
is a function passed in, so tests inject it. It's read once per run, and only when the scope isn't empty. What comes
back must be a JSON list of objects each with a string `name`; anything else is unreadable, never "no labels".

Why GitHub rather than a delivered copy (#153's first question):
- **It's `main` the moment the label merges.** A delivered copy changes only when the owner approves a plan, and a
  troupe branch sees it only after rebasing onto it. The standard change merges the label first so the troupe change
  can follow straight away.
- **No second list in troupe.** troupe keeps no capability list of its own (owner, 2026-10-12, #22). A delivered copy
  would be one, even if generated, and each label would also become a delivery commit on troupe's `main`.
- The cost is a network read on GitHub, where the check already installs Node and OpenSpec from the network.

The token is the run's own `GITHUB_TOKEN`, passed to the step in `guard.yml`. It needs no new permission: the file is
in a public repository. Without the token the request is unauthenticated, which works but shares the runner's
address's 60-an-hour limit, so the workflow always passes it. An absent token falls through to an unauthenticated read;
that's an absent input, not a wrong one. The guard removes the token from the environment it runs the OpenSpec CLI in, so
only the labels request has it (from Claude's review of #168).

Rejected: `raw.githubusercontent.com`, which caches for about five minutes, so a label merged a minute ago could read
as missing. Rejected: `gh api`, which adds a program the guard otherwise doesn't need on CI.

### D4. GitHub only, not the local hooks

#153's second question. The guard's local hooks work offline, and this rule needs another repository's file, so a
local version would either need the network for every push, or pass when offline, which is a check that passes
without its input. The `guard` check runs on every push to every branch, so "fails on that push" holds, minutes after
it. It's a required check, so the change can't merge past it.

Rejected: the `pre-push` hook with a network read. It would refuse a push on a train, and a skipped read is the
fall-through the guard avoids. Rejected: a Claude Code hook on writing a spec. It would be earlier still, but needs the
network inside an edit, and an agent proposing a spec already reads troupe's config, which says a missing label goes
through #152 first.

### D5. The refusal

One `Decision` for the rule, listing every finding sorted by spec, joined by `; ` as `openspec-strict`'s refusal
lists its items:

- undeclared: ``change `x`: spec `run-workspaces` names `cap:workspaces`, which troupe-run/infrastructure doesn't
  declare on main`` (for a main spec, ``spec `stages` names ...``);
- no line: ``change `x`: spec `run-workspaces` names no capability label: its Purpose doesn't start with a
  Capability: line``;
- malformed: ``spec `stages`: its Capability: line is malformed: 'Capability: cap:stages'``.

The fix covers each kind found: for an undeclared label, "add it as a standard change: open the label's sub-issue
from https://github.com/troupe-run/infrastructure/blob/main/docs/standard-changes.md#a-capability-label under the
needing issue's Epic, so it blocks that issue; or name a declared label"; for no line or a malformed one, the shape
(`CAPABILITY_SHAPE`) and, for a proposed spec, "at the top of the delta's `## Purpose`". An unreadable labels file
is a refusal of its own: the file, the reason, and "re-run the check; if it fails again, tell the owner with the run's
URL".

Rejected: naming a command or skill. There isn't one (#153's owner comment); the runbook is the one place.

### D6. One parser, in `guard.py`

`purpose_lines`, `capability_line`, `capability_labels`, `MalformedCapabilityLineError`, `CAPABILITY_LINE` and
`CAPABILITY_SHAPE` move to `scripts/guard.py`, unchanged. `scripts/oob.py` imports them from `guard` (both run from
`scripts/`, so `import guard` resolves as it does for the tests). `oob.py`'s messages stay its own, since they point
at troupe's `main` rather than a push.

Rejected: a copy in each. The line's shape would then live in two places that can drift, against "keep each decision
in one named place". Rejected: `guard.py` importing from `oob.py`. `oob.py` isn't delivered, so troupe's copy of the
guard couldn't.

## Risks / Trade-offs

- [GitHub's API is down or slow] → the rule fails, and the check is red until a re-run. That's the price of not
  passing unchecked, the same trade as `openspec-strict`. The timeout keeps it well inside the job's 5 minutes.
- [A label PR is merged but troupe's run started before it] → the run fails; a re-run passes. The refusal says to
  re-run once the label's pull request is merged.
- [Delivery to troupe's `main` judges every spec] → all 25 name declared labels today (design Context). Task 4.2
  re-checks just before the plan, so the delivery doesn't turn troupe's `main` red.
- [`oob.py` now depends on `guard.py`] → a guard change can break the drift check. Both are tested by the same
  `scripts/check.py`, and `test_oob.py` covers the parser through `oob.py`.
- [A fork's pull request has a read-only token] → that's enough: the read is of a public file.

## Migration Plan

1. Merge. The rule applies only in troupe, so nothing changes in infrastructure's own runs, apart from the moved
   parser.
2. The owner approves the plan that delivers `scripts/guard.py` and `.github/workflows/guard.yml` to troupe and the
   website. troupe's next `guard` run on `main` judges all its specs; the website's skips the rule.
3. Rollback: revert, and deliver again. Nothing outside the guard's files changes.
