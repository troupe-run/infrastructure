# Design

## Context

See proposal.md for why. Read on 2026-10-26:

- The board's `Capability` field (`PVTSSF_lADOE-8w_M4Bmhi5zhlKO1A`) has 36 options, all colour `GRAY`, one with a
  description (`infrastructure`'s, which isn't its label's). Each option has a short id (`0c6bcf57` for `platform`).
- GraphQL introspection of `ProjectV2SingleSelectFieldOptionInput`: `name`, `color` and `description` are required,
  and `id` is optional, "The ID of an existing single select option. Include this to preserve the option's identity
  during updates, preventing item field values from being cleared." `UpdateProjectV2FieldInput.singleSelectOptions`:
  "provided values overwrite existing options, and existing options should be fetched for partial updates."
- The guard makes `updateProjectV2Field` owner-only (`scripts/guard.py`, `"updateProjectV2Field": "admin"`), as it
  does `gh project field-*`. capability-label-standard-change D4 kept the options owner-made in the UI because
  whether a replaced list keeps cards' values was then unknown and untested.
- `tofu.yml` already has the shape this needs: `scripts/hook_modes.py` makes a mode plan in the `plan` job (read
  only), the plan job's `changes` output counts it, the saved plan artifact carries it, and the `apply` job applies it
  after the owner's approval, only when the OpenTofu apply succeeded (executable-hooks D1-D4).
- The infrastructure App has "Projects: read" (the `oob` job's token asks for it). The troupe-run-board App has
  "Projects: read and write", and its key is the secret of infrastructure's `board` environment, main only, no
  reviewers (`tofu/board.tf`, #60). A job has one environment, so the `apply` job can't use the board key.
- `scripts/oob.py`'s `board_capabilities` reads `options{name}` through `gh api graphql` and compares names with
  `tofu/labels/troupe.json`.

## Goals / Non-Goals

**Goals:**
- No description reaches the board without the owner approving a plan that shows it.
- No card loses its `Capability` value, by construction and by a probe before the first live run.
- One source for a description: the label's.

**Non-Goals:**
- Creating, removing, renaming, recolouring or reordering options.
- Any other board field, or the board's workflows.

## Decisions

### D1. A plan and an apply, like the delivered files' modes

`scripts/board_options.py` has two subcommands, as `hook_modes.py` does:

- `plan --out board-plan.json --summary board.md` reads the field (`id`, and each option's `id name color
  description`) and `troupe.json`, and writes the field as read (`before`) and each option whose description will
  change (`changes`: id, name, from, to). The summary lists the changes as a table under the OpenTofu plan, or says
  there are none. It only reads.
- `apply --board-plan board-plan.json` re-reads the field, refuses if it isn't exactly `before` (D3), builds the full
  option list from it with the planned descriptions (D2), and sends one `updateProjectV2Field`. Then it reads the
  field again and fails unless every id, name, colour and description is what it sent.

In `tofu.yml`: the `plan` job gets a read-only infrastructure App token (`permission-organization-projects: read`,
like the `oob` job's) for the `plan` step, and its `changes` output becomes true when the board plan has changes too.
`board-plan.json` goes into the `main-tfplan` artifact beside `mode-plan.json`. A new `board` job, `needs: [plan,
apply]`, runs only when the apply succeeded and the board plan has changes. In the `board` environment it mints the
board App's token with `permission-organization-projects: write` and runs `apply`.

Alternative: one `sync` step after the apply, computing and sending in one go. Rejected: what it sends would never
be shown for approval, so an out-of-band edit to a description would be overwritten unseen, against "every apply is
shown as a plan first". Alternative: give the infrastructure App "Projects: write" and do it in the `apply` job.
Rejected: it widens the App every `tofu` job holds, when a narrow App for exactly this already exists.

### D2. The list sent is the list read, with descriptions changed

`updateProjectV2Field` replaces the whole list. So `apply` sends every option the re-read returned, in its order,
each with its `id`, `name` and `color` as read, and `description` from the plan where it changes and as read
otherwise. The function that builds the list refuses, raising before anything is sent, when any option lacks an `id`
or has an empty one, naming the option. A test builds a list from a field with an option missing its id and checks
the refusal and that the send function was never called. Nothing else in the script builds an option list.

### D3. The apply refuses a field that moved since the plan

The owner may add an option for a new label, or edit one, between the plan and the apply. Sending a list built from
the plan's read would then remove the new option and clear its cards. Building it from the apply's read instead would
send something the owner didn't approve. So `apply` compares its read with `before`, every option's id, name, colour
and description in order, and refuses on any difference, naming it. The next plan of `main` (daily at the latest)
reads the field again. This is executable-hooks D4's "the planned blob still holds" for the board.

### D4. Descriptions come from the labels, matched by name

An option's label is `cap:<option name>`. An option with no such label keeps its description, and an option whose
description already equals its label's isn't listed. The drift check's comparison and the plan's use the same
function, so the check passes after an apply exactly when the plan would list nothing. GitHub's limit on an option's
description is unknown; the labels' descriptions are at most 100 characters (`test_labels.py`), and the probe (D6)
sends the longest one.

### D5. Options are still added and removed by the owner

#166 left open whether the sync should create a missing option. It doesn't. Creating one means sending an option
without an id, which D2 refuses without exception; a refusal with an exception is weaker. The drift check also keeps
reporting a missing option, which is how a forgotten step 6 of the standard change shows up. Removal stays the
owner's for the reason D4 of capability-label-standard-change gave: a removed option clears its cards.

The standard change's step 6 changes: the owner adds the option *with its label's description*, copied from the pull
request. Otherwise the drift job that runs right after the merge reports the blank description until the apply is
approved, the red run #132 warned of. If the owner leaves it blank, the plan made after the merge lists it, and the
apply sets it.

This can be reversed later by making option creation a separate, explicit step in the plan.

### D6. A probe before the live board

The id's documented behaviour is the whole safety argument, so it's proven before the first live run. The guard
makes project creation and field changes owner-only, so the owner runs it, in their own terminal, on a throwaway
project:

1. The owner creates an org project titled `infra-probe-board-options`, adds a single-select field `Capability` with
   options `runs` and `cues` (no descriptions), adds two draft items, and sets one to `runs` and one to `cues`.
2. The owner runs `uv run scripts/board_options.py plan --project <n> --labels <probe labels file> --out … --summary
   …`, then `apply` on that plan. The probe labels file holds `cap:runs` and `cap:cues` with the longest description
   in `troupe.json`.
3. Read back (any login): both options keep their ids and have the descriptions, and both items keep their values.
4. A second probe: the owner adds an option `effects` in the UI after `plan`, and `apply` refuses, naming it.
5. The owner deletes the project.

`--project` and `--labels` default to 1 and `tofu/labels/troupe.json`; the workflow passes neither.

### D7. `apply` on the live board runs only in CI

An agent shares the owner's `gh` login, and the guard sees `uv run scripts/board_options.py apply`, not the GraphQL
mutation inside it. So `apply` refuses project 1 unless `GITHUB_ACTIONS` is `true`, saying the board's descriptions
are set by the `tofu` workflow's `board` job. This is a seatbelt against a mistaken local run, not a security
boundary (the guard's own stance): the owner's review of the plan is the gate.

### D8. The drift check reads descriptions

`BOARD_GH_ARGS` asks for `options{name description}`. `board_capabilities` adds one difference per option whose
description differs from its label's (D4), naming the option, its description on the board and the label's, and
saying the next approved apply sets it. The read-only `oob` token can already read it.

## Risks / Trade-offs

- [The documented id behaviour doesn't hold, and a card loses its value] → The probe (D6) runs first. Before the first
  live apply, the owner's task records every card's `Capability` value (`gh project item-list 1 --owner troupe-run
  --format json`), and the same read after compares them; any change is restored by hand from that record.
- [The owner edits the field between plan and apply] → The apply refuses (D3), and the next plan lists it again. No
  write happens on a moved field.
- [A blank option after a new label's merge turns the drift job red until the apply] → D5's step 6 change; and the
  plan made at that merge lists it, so the red run is the length of one approval.
- [Two descriptions for one capability briefly] → Only between a label's merge and its apply, the same window as the
  label itself on GitHub.
- [`board_options.py apply` run by an agent locally on the live board] → D7.

## Migration Plan

1. Merge with the probe done (D6). The plan made at the merge lists 36 descriptions.
2. Before approving, the owner saves every card's `Capability` value (Risks).
3. The owner approves; the `board` job sets them. The `oob` job of the next run reports no board difference, and the
   cards' values compare equal to the saved ones.

Rollback: revert the merge. The descriptions stay on the board, harmless; or the owner clears them in the field's
settings.
