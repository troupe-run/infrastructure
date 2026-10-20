# Design

## Context

See proposal.md for why. The approach is label-troupe-specs's (2026-10-18), for two labels instead of three:

- troupe-run/troupe's labels come from `tofu/labels/troupe.json` through an authoritative `github_issue_labels`
  resource. A new name is a label created on the next apply, and nothing else on the repository changes.
- `oob/troupe-spec-purposes.json` maps each `cap:<name>` with a troupe spec to that spec's Purpose as
  `scripts/oob.py`'s `purpose()` reads it. Both files are sorted by label name.
- `scripts/tests/test_labels.py` refuses a description over 100 characters, or one that only repeats the name.

Evidence read on 2026-10-20:

| | |
|---|---|
| `uv run scripts/oob.py` on `main` (5b950cd) | exactly the two differences in #112, and nothing else |
| `tofu/labels/troupe.json` | 43 labels |
| `oob/troupe-spec-purposes.json` | 19 entries |
| troupe issues about these capabilities | #120 (closed, `cap:infrastructure`) and #123 (closed, `documentation`, `cap:releases`) |

The two Purposes on troupe's `main`, as `purpose()` reads them:

- **user-docs:** "troupe's user documentation, which troupe.run's `/docs` is built from: where it lives, the page
  contract the site builds from, which reference is generated and how it's kept true, how pages describe built and
  unbuilt behaviour, and the vocabulary rules they follow."
- **docs-publishing:** "How a change to troupe reaches troupe.run: which pushes notify the website to rebuild `/docs`,
  and what the job that sends the notice may do."

## Goals / Non-Goals

**Goals:**
- `oob.py` reports nothing for troupe's labels, and the drift job passes, once this is applied.
- Each of the two specs has a label whose description was checked against its Purpose.

**Non-Goals:**
- Re-reading the 19 recorded Purposes. `oob.py` reports none of them as changed.
- Making the drift job tolerate a new spec until its label lands. A red job is how a missing label gets noticed.

## Decisions

### D1. The two descriptions

| Label | Description | Length |
|---|---|---|
| `cap:user-docs` | `troupe's user docs, built into troupe.run's /docs: page contract, generated reference, vocabulary` | 97 |
| `cap:docs-publishing` | `How a change to troupe reaches troupe.run: which pushes rebuild /docs, what the notice job may do` | 97 |

- **user-docs** keeps the Purpose's opening (what the docs are and what's built from them), then three of the five
  things it lists. "Where it lives" and "built and unbuilt behaviour" go, because 100 characters can't hold them.
  The page contract, the generated reference and the vocabulary are what an issue for this capability is most
  likely to be about.
- **docs-publishing** keeps the Purpose's first clause word for word, then both parts it names, shortened.

`/docs` is written without backticks, as label-troupe-specs D1 wrote `scripts/check.py`: GitHub shows a label
description as plain text.

### D2. The record is the spec's text, verbatim

As in label-troupe-specs D2: each recorded Purpose is copied from `gh api
repos/troupe-run/troupe/contents/openspec/specs/<name>/spec.md` on troupe's `main` through `purpose()`, not from this
design. `cap:docs-publishing` goes after `cap:cues` in `tofu/labels/troupe.json` and after `cap:client-protocol` in
the record. `cap:user-docs` goes after `cap:theatre` in the labels and after `cap:stages` in the record.

### D3. Relabelling troupe's docs issues

After the apply, once the labels exist:

| Issue | Adds | Removes | Why |
|---|---|---|---|
| troupe#123 "troupe's user docs: written, generated and tested here, built into troupe.run's /docs" | `cap:user-docs` | `cap:releases` | it's the issue the user-docs spec came from. `cap:releases` stood in for the docs' versioning, which user-docs now covers |
| troupe#120 "Keeping troupe and its docs in step: one lifecycle, not two projects" | `cap:user-docs`, `cap:docs-publishing` | `cap:infrastructure` | it's about both. `cap:infrastructure` says "not a troupe capability" |

troupe#130 (the README's description, from #108) is left as it is: the README isn't part of `/docs`.

Alternative: leave both issues alone, since they're closed. Rejected: label-troupe-specs D5 relabelled closed issues
for the same reason, so that a label lists all the work on its capability.

## Risks / Trade-offs

- [troupe adds another spec before this merges] → 4.1 re-runs `oob.py` on the branch and stops if it reports
  anything more.
- [A Purpose changes on troupe's `main` before the apply] → `oob.py`'s next run reports it as a stale description,
  which a follow-up fixes the usual way.

## Migration Plan

The apply only creates two labels. Rolling back is a revert of the pull request, and nothing carries the labels
until D3's relabelling.
