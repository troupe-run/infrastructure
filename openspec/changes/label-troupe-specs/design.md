# Design

## Context

See proposal.md for why. What shapes the approach:

- troupe-run/troupe's labels come from `tofu/labels/troupe.json` through an authoritative `github_issue_labels`
  resource, so a new name is a label created on the next apply, and nothing else on the repository changes.
- `oob/troupe-spec-purposes.json` maps each `cap:<name>` with a troupe spec to that spec's Purpose as
  `scripts/oob.py`'s `purpose()` reads it: the `## Purpose` section, whitespace collapsed. It's sorted by label name
  (cap-label-descriptions D1), as is `tofu/labels/troupe.json`.
- `scripts/tests/test_labels.py` (run by `scripts/check.py`) refuses a description over 100 characters, or one that
  only repeats the name.
- Every managed repository's label set is a `concat` in `tofu/repositories.tf` of shared sets
  (`github-defaults.json`, GitHub's own, adopted unchanged; `workflow.json`, the labels the workflow uses) and, for
  troupe, its own (`troupe.json`, `release.json`).
- The existing descriptions are noun phrases or a short colon list ("The one seam for OS-specific behaviour: files,
  locks, …"), written to say what the capability covers rather than to paraphrase the whole Purpose.

Evidence read on 2026-10-18:

| | |
|---|---|
| `uv run scripts/oob.py` on this branch (= `main` f8328f8) | exactly #63's four differences, and nothing else |
| troupe's spec folders on `main` (c0634ec) | 19: the 15 recorded, plus `flake-hunt`, `python-support`, `quality-check` and `releases` |
| `tofu/labels/troupe.json` | 40 labels, `cap:releases` among them |
| troupe's open work | no OpenSpec change in flight, no branch but `main` and release-please's; every open issue's capability already has a label |
| troupe's labels on GitHub | none that isn't declared here |
| Issues carrying `cap:performance` | #36 (`troupe perform`), and #54, #75, #108, #109, which are about speed |
| Speed work with no label | troupe#83, #84; infrastructure#78 |

The four Purposes on troupe's `main`, whitespace collapsed:

- **flake-hunt:** "Finding flaky tests on demand, on every platform: repeating tests in overlapping rounds, under optional
  load and with fresh randomised inputs, and reporting each failure with the evidence an issue needs."
- **python-support:** "Which Python versions troupe supports, how that support is declared and enforced, and how the
  declaration stays exactly in step with the versions CI tests."
- **quality-check:** "What troupe's `scripts/check.py` runs, the scoped form that narrows its tests, and troupe's
  declaration of which paths need which part of the check. The commit guard and CI read that declaration, and every
  test run keeps it true."
- **releases:** "How troupe's packages get their versions, changelogs and releases: all derived from the Conventional
  Commits on `main` through a release pull request, never edited by hand."

## Goals / Non-Goals

**Goals:**
- `oob.py` reports no difference for troupe's labels once this merges.
- Each of troupe's specs has a label whose description was checked against its Purpose.
- Each label on an issue means what its description says: speed work has its own label, and troupe's issues carry the
  capability labels that now exist for them.

**Non-Goals:**
- Re-reading the 15 recorded Purposes. `oob.py` reports none of them as changed.
- Other kind labels. Only speed has turned up as a kind of work that a capability label was standing in for.

## Decisions

### D1. The three descriptions

| Label | Description | Length |
|---|---|---|
| `cap:flake-hunt` | `Finding flaky tests on demand, on every platform: repeated rounds, load, fresh inputs, evidence` | 95 |
| `cap:python-support` | `Which Python versions troupe supports, how that is declared and enforced, in step with CI` | 89 |
| `cap:quality-check` | `What scripts/check.py runs, its scoped form, and which paths need which part of the check` | 89 |

Each keeps its Purpose's opening and order, and drops what doesn't fit in 100 characters:

- **flake-hunt** keeps the Purpose's first clause word for word, then lists the method as the spec does (rounds, load,
  inputs, evidence). "Overlapping" and "optional" go: they qualify, they don't name.
- **python-support** keeps all three parts of the Purpose (which versions, declared and enforced, in step with CI).
- **quality-check** keeps the three things the Purpose names. The second sentence, that the guard and CI read the
  declaration, says who uses it, not what the capability covers, so it's left to the spec.

`scripts/check.py` is written without backticks, as `cap:protocol`'s `protocol/` is: GitHub shows a label description
as plain text.

Alternative: one fixed form for all three, such as "X: a, b and c". Rejected: the existing descriptions don't follow
one form, and forcing one would cost words the 100 characters need.

### D2. The record is the spec's text, verbatim

As in refresh-cap-label-purposes D3: each recorded Purpose is the spec's `## Purpose` section as `purpose()` reads it,
copied from `gh api repos/troupe-run/troupe/contents/openspec/specs/<name>/spec.md` on troupe's `main`, not from #63
or from this design. `oob.py` compares against exactly that, so it's the only text that makes the check pass. Each
entry goes in label-name order: `cap:flake-hunt` after `cap:event-store`, `cap:python-support` after `cap:protocol`,
`cap:quality-check` after `cap:python-support`, `cap:releases` after `cap:quality-check`. The labels go in the same
places in `tofu/labels/troupe.json` (`cap:flake-hunt` between `cap:event-store` and `cap:flows`).

### D3. `cap:releases` keeps its description

Its description, "Versions, changelogs and releases, derived from Conventional Commits through a release PR" (89
characters), was written from troupe#23's body before the spec existed. Checked against the Purpose, it names the
same three things, the same source and the same route. The Purpose adds "never edited by hand", which "derived from"
already implies. So only the Purpose is recorded, and the description stays.

Alternative: append ", never by hand" (104 characters, over the limit), or reword to fit it. Rejected: it changes a
label that issues carry for no gain in meaning, and the plan would show an in-place change that isn't needed.

### D4. `speed`, a kind label in its own shared set

`{"name": "speed", "color": "FBCA04", "description": "Making something faster: the product, its tests, or its checks"}`
(62 characters), in a new file `tofu/labels/kinds.json`, which `tofu/repositories.tf` adds to all four repositories'
label sets after `workflow_labels`.

- **The name.** `performance` is what GitHub projects often call this, but in troupe a performance is a run of a
  process, which is exactly the clash that put `cap:performance` on speed issues. `speed` can't be read as anything
  else. The owner said yes to a speed label without naming it; `speed` is this design's choice and is a one-word change
  before the apply.
- **Every repository.** Speed work exists in troupe and in infrastructure (#78), and the guard and checks this
  repository delivers run in every governed repository.
- **Its own set.** It isn't one of GitHub's defaults, which are kept as adopted, and the workflow doesn't use it, so it
  belongs in neither existing set. A set named for kinds of work gives the next one (if any) a place, and the
  requirement in the delta spec says what goes there.
- **The check.** `scripts/tests/test_labels.py`'s length check runs over `kinds.json` too, since GitHub refuses a
  description over 100 characters only at apply time. The "repeats its name" check stays for `cap:` labels only.

Alternative: put `speed` in `workflow.json`. Rejected: that set is "the labels the workflow uses", and its test reads
the org's issue forms against it. A label nobody's workflow applies would blur that.

Alternative: describe `cap:performance` as covering speed too. Rejected: a capability label names a part of troupe,
and speed cuts across many parts (#54 and #75 are event-store work, #108 and #109 are the check).

### D5. Relabelling after the apply

The labels exist only once the owner approves the apply, so the relabelling is done then, with
`gh issue edit <n> -R troupe-run/<repo> --add-label … --remove-label …`, and checked with `gh issue view`. Removing a
label from an issue doesn't change the declaration, so "A capability label in use is never removed or renamed" isn't
touched. Read on 2026-10-18:

| Issue | Add | Remove | Why |
|---|---|---|---|
| troupe#54, #75 | `speed` | `cap:performance` | event-store work to cut latency (no polling) and cost (no git per event) |
| troupe#108, #109 | `cap:quality-check`, `speed` | `cap:performance`, `cap:infrastructure` | troupe's scoped check, written to make commits faster |
| troupe#101 | `cap:quality-check` | `cap:infrastructure` | which checks CI runs for OpenSpec-only commits |
| troupe#83 | `cap:quality-check`, `speed` | | running the suite in parallel to cut the check's time |
| troupe#84 | `speed` | | shortening the slowest tests' waits |
| troupe#104, #105, #107 | `cap:python-support` | `cap:infrastructure` | the supported Python versions; `cap:releases` stays, since the build declares them |
| troupe#100, #112 | `cap:flake-hunt` | | the flake hunt and a flake it found; `cap:platform` stays, since the fixes are platform's |
| troupe#113 | `cap:infrastructure` | | regenerating the workflow's OpenSpec files, which this repository's workflow owns |
| infrastructure#78 | `speed` | | running only the checks a change's paths need |

troupe#36 (`troupe perform`) keeps `cap:performance`, its real meaning.

`cap:infrastructure` stays on troupe's other issues (#22–#30, #48), which are about the org's setup and the guard.

## Risks / Trade-offs

- [troupe changes or adds a spec before this merges] → `oob.py` is run on the branch before the pull request opens and
  on `main` after the apply. A new difference is reported on #63, not folded in silently.
- [The plan shows more than three labels created, for example drift made by hand] → The plan is read before the pull
  request opens. Anything beyond the three creations is reported to the owner.
- [A description misreads its capability] → Each is checked against its recorded Purpose in review, and the Purpose
  sits beside it in the same pull request.
- [New issues get the wrong label again] → The descriptions say what each covers, and `speed` now exists for speed.
  Nothing checks how issues are labelled; that stays a review habit.
- [An issue's labels change between this design and the relabelling] → Each issue's labels are read before it's
  edited, and only the adds and removes in D5 are made. Anything unexpected is reported on #63.

## Migration Plan

The owner approves the pull request's plan. After the merge, the owner approves the `apply` job, which creates the
three capability labels on troupe and `speed` on all four repositories. Then the issues are relabelled (D5). Rolling
back is reverting the commit, but the next apply then deletes the four labels and takes them off every issue D5
labelled. So undo D5's edits first, putting back the labels it removed, then revert.
