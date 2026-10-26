# Design

## Context

See proposal.md for why. Current state:

- `scripts/oob.py` runs two troupe checks in turn. `troupe specs` (`unlabelled_specs`) reads the folder list from
  `repos/troupe-run/troupe/contents/openspec/specs` and wants `cap:<folder>` in `tofu/labels/troupe.json`.
  `troupe label descriptions` (`stale_descriptions`) reads `spec.md` for each labelled folder only, and compares
  `purpose()`, the whole `## Purpose` section with its whitespace collapsed, with `oob/troupe-spec-purposes.json`,
  which is keyed by `cap:<name>`. The second check runs only when the first could read the list.
- The `Capability:` line's shape is troupe#170's design D2 (restated in the owner's comment on #151). It's the first
  non-blank line of `## Purpose`: `Capability: ` followed by one or more labels, each in backticks, separated by
  `, `, with nothing after the last. It's the first non-blank line rather than the line right after the heading,
  because OpenSpec drops the blank line under the heading when it archives a new spec.

Evidence read on 2026-10-26, on infrastructure `main` at 801fbee and troupe `main` after f159b5b:

| | |
|---|---|
| `uv run scripts/oob.py` | 25 `troupe labels: '<label>' spec's Purpose has changed` differences, one per spec, and `App installations: 'troupe-run-review'` (#154) |
| troupe's `openspec/specs/` | 25 folders. Each Purpose's first non-blank line is a well-formed `Capability:` line |
| Labels those lines name | 15 distinct labels, all declared except `cap:development` (named by `flake-hunt`, `python-support`, `quality-check`, `releases`, `docs-publishing`) |
| Each Purpose without its `Capability:` line, against the record | all 25 match the recorded text for `cap:<folder>` |
| `tofu/labels/troupe.json` | 48 labels, sorted in byte order. `cap:flows` is `TBD` |
| troupe issues per folded label (#151's second change) | 59 issues and no pull requests. `cap:lifecycle` is on nothing |

## Goals / Non-Goals

**Goals:**
- The drift job reports nothing for troupe's specs and Purposes once this merges, before the apply, because the check
  reads declarations rather than GitHub.
- The check stays green between this change's apply and #151's second change. The folded labels are then declared
  but named by no spec, and that's not reported.

**Non-Goals:**
- Checking that an issue carries the labels its spec names. That's the relabelling's job, in #151's second change.
- Checking the label list in a spec against troupe#169's mapping table. troupe owns the line, and the table was the
  starting point, not a second list.

## Decisions

### D1. Every spec is read once, and both checks use what was read

Every spec's labels are now in its `spec.md`, so each one has to be read, not only the labelled ones. `troupe specs`
reads the folder list and then each `spec.md`, keeps the contents, and reports labels. `troupe label descriptions`
uses the same contents and makes no further calls. If any one read fails, `troupe specs` is unreadable and names the
spec, never "no label". The descriptions check is then reported as not checked, as it already is when the list can't
be read.

Rejected: keeping the folder list as the label source and reading `spec.md` only in the descriptions check. Labels
would then depend on the Purpose read, the two checks would fail together anyway, and each spec would be fetched
twice.

### D2. How the line is read

`capability_labels(spec_md)` returns the labels named, or a finding:

- The `## Purpose` section is found as `purpose()` finds it today. Its first non-blank line is the candidate.
- **No Purpose section, or a first line that doesn't begin with `capabilit` in any case:** the spec names no
  label.
  `troupe specs: 'cli' names no capability label; add a Capability: line as the first line of its Purpose in
  troupe-run/troupe`.
- **A first line that begins with `capabilit` in any case** (so `Capabilities:` and `capability:` too) is the
  line. Once trailing whitespace is stripped, it must fully
  match `Capability: ` + `` `label` `` (`, ` + `` `label` ``)\*, where a label has no backtick or whitespace, and no
  label may appear twice. Anything else is malformed: `troupe specs: 'stages' Capability: line is malformed:
  'Capability: cap:stages'; write it as Capability: `cap:<name>`, `cap:<name>` ` (spec: "A malformed Capability
  line is reported"). A malformed line isn't partly read. This is the rule that a present but wrong input is an
  error, never a fall-through. `Capabilities:` or `Capability:` with nothing after it are malformed, not "no label".
- **Each named label not in `tofu/labels/troupe.json`:** `troupe specs: 'flake-hunt' names 'cap:development', which
  isn't declared; add it to tofu/labels/troupe.json by pull request, or correct the spec in troupe-run/troupe`. A
  name without the `cap:` prefix is reported the same way, since only `cap:` labels are declared there.

Rejected: reading only the line right after the heading (it breaks on archived specs, per troupe#170 D2), and a
looser parse that pulls out anything in backticks (it would read ``Capability: `cap:vcs` (and git)`` as naming
`cap:vcs`).

### D3. The Purpose record is keyed by spec

`oob/troupe-spec-purposes.json` becomes `{"<folder>": "<Purpose without the Capability: line>"}`, sorted by key. The
25 values stay as they are: only the keys lose `cap:`. The Purpose compared is `purpose()` with the `Capability:`
line removed, using D2's test for which line that is. Removing it keeps a change to a spec's labels from showing as
a changed Purpose. Messages, all under the existing `troupe labels:` prefix:

- changed: `troupe labels: 'runner-protocol' spec's Purpose has changed; review the descriptions of
  'cap:actor-runners', 'cap:protocol' in tofu/labels/troupe.json and update oob/troupe-spec-purposes.json`
- not recorded: `troupe labels: 'cli' spec's Purpose isn't recorded; check the descriptions of 'cap:cli' against it
  and record it in oob/troupe-spec-purposes.json`
- record with no spec: `troupe labels: 'cues' has a recorded Purpose but troupe has no cues spec; remove it from
  oob/troupe-spec-purposes.json`

A spec whose line is missing or malformed still has its Purpose compared, and its message names no labels: `review
the descriptions of the labels it names`. Its `troupe specs` difference covers the line.

Rejected (owner, 2026-10-26, on #158's question): dropping the record and `stale_descriptions`. A rewritten Purpose
would then never prompt a review of the labels written from it. Also rejected: keeping it keyed by label. A label
such as `cap:development` is written from five Purposes, so there's no single text to record against it.

### D4. The two descriptions

| Label | Description | Length |
|---|---|---|
| `cap:development` | `How troupe itself is built, tested and released: the check, flaky tests, Python versions, releases` | 98 |
| `cap:flows` | `How actors are arranged: in sequence, in parallel with fork and join, in loops, and as swarms` | 93 |

- **`cap:development`** is troupe#169's "how troupe is built, tested and released". "Itself" sets it apart from
  `cap:infrastructure` (the org's own setup). The list after the colon is four of the five specs that name it. The
  fifth, `docs-publishing`, also names `cap:user-docs`, which covers the docs, so it's left out to stay within 100
  characters. Colour `1D76DB`, like every `cap:` label. It goes between `cap:cues` and `cap:docs-publishing` in byte
  order.
- **`cap:flows`** is from the milestones that build it: 0.5.0 sequence, 0.8.0 fork and join, 0.12.0 loops, 0.13.0
  swarms (`tofu/milestones.json`). No spec names it yet, so it has no recorded Purpose, and none is needed (D3 keys
  by spec).

## Risks / Trade-offs

- [The check now reads every spec, not only the labelled ones] → today all 25 are labelled, so it's still 25 calls,
  growing by one per spec. That's well inside the read-only token's rate limit for a job that runs daily and on
  `main`.
- [troupe changes the line's shape] → every spec is then reported as malformed, which is loud and names the shape.
  The shape is troupe#170's D2, and changing it is a troupe decision that would come with a change here.
- [The folded labels are named by no spec until #151's second change removes them] → that's the "label ahead of its
  spec" case, which isn't reported. The relabelling isn't blocked by a red job.
- [The `troupe-run-review` difference keeps the job red after this merges] → it's #154's. This change's PR says so,
  so the owner doesn't read it as this change failing.

## Migration Plan

1. Merge. The drift job's 25 `troupe labels` differences clear on the next run on `main`, before the apply.
2. The owner approves the plan: `cap:development` is created and `cap:flows`' description changes on
   troupe-run/troupe. No label is deleted, so no issue loses one.
3. Rollback is a revert PR. Reverting removes `cap:development` from the declaration, so it can't be done once any
   issue carries the label. It would then fall under "A capability label in use is never removed or renamed".
4. #151's second change then relabels and removes the folded labels and `cap:lifecycle`.
