# Design

## Context

See proposal.md, Why. `guard.yml` installs the OpenSpec CLI at `OPENSPEC_VERSION` for `openspec-strict`, which runs
`openspec validate --all --strict --json --no-interactive` and reads its JSON report (guard-strict-openspec design
D1, D2; this repository's pin was last moved by the archived change `openspec-1-14-3`). `guard.py`'s `OPENSPEC_PIN`
names where the pin lives, and its "OpenSpec isn't installed" fix points there; nothing compares the installed
version with the pin. The pin reaches troupe and website, the only other governed repositories
(`tofu/guard_delivery.tf`), by delivery.

OpenSpec 2.0 keeps one copy of each skill in `.agents/skills/`, links tool folders to it, and removes the `/opsx:*`
commands ([release notes](https://github.com/Fission-AI/OpenSpec/releases/tag/v2.0.0),
[upgrade guide](https://openspec.dev/docs/upgrade-to-2)). The guide maps `/opsx:propose` → `openspec-propose`,
`/opsx:apply` → `openspec-apply-change`, `/opsx:archive` → `openspec-archive-change`, and so on; in Claude Code a skill
is typed as `/<name>`. troupe#423 and website#116 regenerate those repositories' files and rename the commands in
their own docs.

## Goals / Non-Goals

**Goals:**
- CI's `openspec-strict` runs 2.0.0 in every governed repository, once each is on 2.0's layout.
- Nothing the guard says, and no live doc here, tells a person or agent to type a `/opsx:*` command.
- This repository's generated files are exactly what `openspec update` 2.0.0 writes.

**Non-Goals:**
- Checking the installed CLI's version against the pin. Not asked for, and the pin is the only install route in CI.
- Changing how `openspec-strict` parses the report: 2.0.0's report has the same shape (D2).
- Rewriting archived changes or the recorded plan fixture `plan-pr96.txt` (it records a past plan's text).

## Decisions

**D1. Merge only after troupe#423 and website#116.** The delivery lands on their `main` with no pull request. If the
new names or pin arrived first, the guard would name skills those repositories' docs don't, and CI would validate a
repository still holding 1.14.3's files with 2.0.0. Both are only a mismatch of names, not a failure, but the order
removes it. Before asking for the plan's approval, 2.0.0's `openspec validate --all --strict` runs over each governed
repository's `main` (docs/development-workflow.md, "Moving the OpenSpec version"); troupe#423 and website#116 have
already run it over their branches with both versions.

**D2. Re-capture the fixtures rather than only relabel them.** `openspec-strict`'s tests read reports captured from
1.14.3. Running 2.0.0 over the same two trees gave the same exit status (0 and 1), the same error output and the same
report bar `durationMs`. Re-capturing puts 2.0.0's own output in the fixtures, so they keep recording what CI runs, and
the tests' `version="1.14.3"` and messages move with them. If a later version changes the report, the same
re-capture shows it.

**D3. The messages name the skills as slash commands.** `/openspec-propose <change-name>`, `/openspec-apply-change`:
what the person types in Claude Code, and what troupe's and website's CLAUDE.md now say. The session-start summary
keeps its shape; only the two names change.

**D4. `skip_specs: true`.** No requirement names a slash command or the OpenSpec version.

## Risks / Trade-offs

- [2.0.0 is stricter than 1.14.3 on some spec in a governed repository] → D1's run over each `main` names it before
  the plan's approval. troupe and website already pass with both versions on their upgrade branches.
- [Sessions still on `/opsx:*` read the guard's new names] → the skills they name exist under 1.14.3's layout too,
  and the orchestrator has told running sessions the names.
- [The guard's change puts every spec and active change here in `openspec-strict`'s scope (`OPENSPEC_ALL_PATHS`)] →
  intended; it's the validation of this repository with the new version that the procedure asks for.
