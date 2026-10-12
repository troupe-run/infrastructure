# Design

## Context

See proposal.md for why. What shapes the approach:

- troupe-run/troupe's labels come from `concat(github-defaults.json, workflow.json, troupe.json)` in
  `tofu/repositories.tf`, through one `github_issue_labels` resource per repository. That resource is authoritative:
  a label missing from the declaration is deleted from GitHub, and GitHub deletes it from every issue with it.
- `scripts/oob.py` is the one script here that reads GitHub with the owner's `gh`. The owner runs it alongside every
  plan and quotes its output in the pull request. `scripts/check.py` must work offline, and CI holds no credentials
  for `oob.py`.
- The guard already refuses `gh label create` and other label administration from Claude (`owner-only`), so a label
  can't be added by hand from a session.

Evidence gathered on 2026-10-12, troupe at `31809fb` (`origin/main`):

| | Labels |
|---|---|
| troupe's specs (10) | `actor-runners`, `artifact-store`, `cli`, `event-store`, `identity`, `lineage`, `platform`, `runner-protocol`, `scripted-runner`, `vcs` |
| Spec with no label (3) | `artifact-store`, `runner-protocol`, `scripted-runner` |
| Label on a troupe issue (25) | `actor-runners`, `cli`, `collaboration`, `config`, `core-api`, `effects`, `event-store`, `gates`, `house`, `identity`, `infrastructure`, `lineage`, `performance`, `platform`, `plugins`, `policy`, `projections`, `protocol`, `roles`, `settings`, `stages`, `storage`, `telemetry`, `vcs`, `work-tracking` |
| Label on no issue or PR (9) | `actors`, `cues`, `escalation`, `flows`, `guests`, `lifecycle`, `notes`, `notifications`, `theatre` |

No troupe pull request carries a `cap:*` label. Read with `gh issue list -R troupe-run/troupe --state all` and
`gh pr list … --state all`; the task that changes the file reads it again.

## Goals / Non-Goals

**Goals:**
- One declared list of troupe's capability labels, changed by pull request, that no future change has to replace.
- No label taken off an issue, now or by a later change.
- A missing label for a new troupe spec shows up where the owner already looks for drift.

**Non-Goals:**
- Deciding which planned capabilities troupe keeps. That is troupe's product question.
- Giving each label a better description than `Capability: <name>`.

## Decisions

### D1. The label file is the list, and the constraint says so

`openspec/config.yaml`'s constraint "Product concepts stay in troupe. The capability list is read from there, never
copied by hand." becomes:

> Product concepts stay in troupe. troupe's `cap:*` labels are the exception: they're declared here in
> `tofu/labels/troupe.json` and changed by pull request when a capability is needed. troupe keeps no separate
> capability list to read them from (owner, 2026-10-12, #22).

The why is recorded three times, each where its reader looks: the constraint carries the decision and its issue,
this design carries the reasoning, and the comment on #22 after the merge links both. The reasoning: generating the
labels needs a list in troupe that is machine-readable and kept current, and troupe has decided not to keep one.
Deriving labels from troupe's `openspec/specs/` folders was considered and rejected: most labels (25 of 34) lead
their spec, and some capabilities (`infrastructure`, `performance`) will never have one, so the spec folders are
not the capability list either.

### D2. Add a label per spec, matching its folder name exactly; never rename

The three specs with no label get `cap:artifact-store`, `cap:runner-protocol` and `cap:scripted-runner`, colour
`1D76DB` and description `Capability: <name>`, like their neighbours. Labels stay sorted by name in the file.

- **Exact names** make D4's check a set difference with no mapping table to keep in step.
- **Alternative rejected: let an existing label cover the spec** (`cap:storage` for `artifact-store`,
  `cap:protocol` for `runner-protocol`, `cap:actor-runners` for `scripted-runner`). It saves three labels but needs
  a spec-to-label map, which is a second list to keep. `cap:protocol` already covers more than the runner
  contract (troupe-run/troupe#7 config schema, #37 plugin transports), so it isn't the same capability.
- **Alternative rejected: rename `cap:protocol` to `cap:runner-protocol`.** The resource would delete
  `cap:protocol` and create the new one, taking the label off four issues.

### D3. Keep all 34 existing labels

The nine unused labels are not leftovers. They are the kickoff vocabulary that troupe-run/troupe#15 records as
troupe's planned concepts ("cue, provisionally", the "guest", "notes", "theatre" terms; notifications and escalation
as cue sources). Removing them loses no issue data, but it would make this repo decide that a planned capability
is gone, which the "product concepts stay in troupe" constraint leaves to troupe. Keeping them is the reversible
choice: a later pull request can remove any of them once troupe drops the concept.

`lifecycle` is the weakest: it's on no issue and in none of troupe's documents read here. It is kept on the same
rule, and called out in the pull request so the owner can drop it in review if they know it is dead.

### D4. The spec check lives in `oob.py`, one way

troupe's specs can't be read offline from here, so the check can't be in `scripts/check.py` or the guard. Three
places were considered:

| Where | Runs when | Verdict |
|---|---|---|
| `scripts/oob.py` here | the owner runs it with every plan | **Chosen.** It already reads GitHub, already reports drift between a declaration here and GitHub, and its output is quoted in each pull request. |
| A job in this repo's CI | every pull request here | Rejected: troupe adding a spec would fail unrelated pull requests here, and CI holds no credentials for `oob.py` yet. |
| troupe's CI, reading `troupe.json` from this public repo | a troupe pull request that adds a spec | Deferred: the most timely of the three, but it's a change to troupe's files, which arrives through troupe's own pull request. It can follow if the `oob.py` report proves too late. |

`oob.py`'s existing checks compare a declaration with GitHub both ways. This one is one way: a spec with no label
is a difference, a label with no spec is not (spec: labels). So it is a separate kind of check alongside `CHECKS`,
not one more entry in it: it reads the folder names with
`gh api repos/troupe-run/troupe/contents/openspec/specs --jq '[.[] | select(.type == "dir") | .name]'`, which skips
`.gitkeep`, and reads the declared names from `tofu/labels/troupe.json`. Its message names the folder and the file
to add the label to. The tests drive it through `run`'s injected `fetch`, as the existing checks' tests do, so they
stay offline.

A troupe spec folder whose name isn't a valid label (over 50 characters) is reported as missing like any other:
the fix, a pull request here, is where the naming question gets settled.

### D5. Where the "add a label by pull request" path is written down

- **The org's Feature and Decision forms**, the place a contributor meets `cap:` labels. Their line becomes: "If
  the repository has `cap:<capability>` labels, add one for each capability this touches. If none fits, say so here;
  a new label is added by a pull request to troupe-run/infrastructure." The forms are shared by every repository,
  so the line stays conditional.
- **README.md**'s layout row for `tofu/labels/`: names `troupe.json` as troupe's capability labels, changed by pull
  request.
- **`oob/README.md`**'s check table: a row for troupe's specs.
- **The `labels` spec** (this change's delta).

`docs/development-workflow.md` is about the guard's rules and doesn't change.

## Risks / Trade-offs

- [A new troupe spec goes unlabelled until the owner next runs `oob.py`] → It's reported on the next plan of any
  change here; issues can be filed without a `cap:` label meanwhile, and the forms say how to ask for one.
- [Someone later removes a label still in use] → The spec requires the usage list in the pull request, and the plan
  shows the deletion before the owner approves it.
- [The GitHub contents API lists at most 1,000 entries per folder] → troupe has ten specs; not a concern.

## Migration Plan

The plan for this change creates three labels on troupe-run/troupe and updates two files in troupe-run/.github. No
deletion. Rollback is a revert pull request, whose plan deletes the three labels; none will be on an issue unless
someone used them in the meantime, which the plan's reviewer checks.
