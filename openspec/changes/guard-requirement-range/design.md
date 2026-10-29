# Design

## Context

See proposal.md for why. Current state, read on 2026-10-29 at infrastructure `7799009`:

- **The exemption's kind reading** is `dependabot_ineligibility` in `scripts/guard.py`. For each commit it reads the
  subject with `DEPENDABOT_SUBJECT` (a copy of `TITLE` in `scripts/dependabot_issues.py`), counts `old` to `new` with
  `dependabot_update_kind` (a copy of `update_type`), and checks every `update-type:` line. A subject it can't read
  is "unknown", and refused. Paths are judged separately by `non_dependency_paths` (dependabot-exemption D4).
- **troupe #181, as Dependabot wrote it** (head `a9fe317`, branch `dependabot/uv/uv-build-gte-0.13.3-and-lt-0.14`):

  | Where | What it says |
  |---|---|
  | Commit subject | `chore(deps-dev): Update uv-build requirement` |
  | Message metadata | `dependency-name: uv-build`, `dependency-version: 0.13.3`, no `update-type`, no previous version |
  | Diff | 9 × `pyproject.toml`, each `-requires = ["uv_build>=0.13.0,<0.14"]` / `+requires = ["uv_build>=0.13.5,<0.14"]` (+1 −1) |
  | Pull request title | `chore(deps-dev): Update uv-build requirement from <0.14,>=0.13.0 to >=0.13.5,<0.14` |

  The metadata's `0.13.3` disagrees with the diff's `0.13.5`: Dependabot updated the pull request in place and kept
  the old metadata. The title lists the old range's bounds in a different order from the file (`<0.14,>=0.13.0`).
- **`dependabot/fetch-metadata` v3.1.0** (`src/dependabot/update_metadata.ts`): with no "from … to" in the commit, it
  matches `[Uu]pdate .* requirement from \S*? ?(v?\d\S*) to …` against the pull request's **title**, giving
  `0.14,>=0.13.0` and `0.13.5,<0.14`, and `calculateUpdateType` splits those on `.` and compares the first two parts.
  Here it happens to say minor; it reads an editable title and doesn't parse a range.
- **`dependabot_issues.read_update`** reads the pull request's title with `TITLE`, which already captures a range
  title's `old` and `new`; `update_type` calls them unknown, and the issue (troupe #179) says the update needs an
  OpenSpec change. Its body is written only when the issue is opened or relinked.
- **troupe's ranges** today: `uv_build>=0.13.0,<0.14` (build-system, nine packages, no lock entry),
  `eventsourcing>=9.5.6,<9.6`, `jsonschema>=4.26,<5`, `pydantic>=2.14,<3`, `ruamel.yaml>=0.19.1,<0.20` (locked in
  `uv.lock`). website's `package.json` pins exact versions.

## Goals / Non-Goals

**Goals:**
- troupe #181 passes `guard` after `@dependabot rebase`, with nothing else done to it but its closing line.
- A range update that isn't plainly a minor or patch move is still refused, saying why.
- The issue and the check give a range update the same kind.

**Non-Goals:**
- Reading lock files' contents. The path rule already allows `uv.lock` and `package-lock.json`; the kind comes from
  the manifest, as for a version bump it comes from the subject.
- npm range syntax beyond what D3 reads (`||`, `x` wildcards, hyphen ranges). They're unreadable and refused.
- Grouped updates (several dependencies in one commit). Not configured; unreadable if they appear.
- Rewriting the bodies of issues already open.

## Decisions

### D1. Read the versions from the manifest diff

Four sources were weighed:

- **The commit message**: the subject has no versions, and the metadata is stale (Context). Rejected.
- **The pull request's title**: has both ranges, but anyone with write access can edit it, so it isn't read for a
  check (dependabot-exemption D3).
- **`fetch-metadata`'s `update-type`**: derived from the same editable title, by splitting a range on dots, and would
  need a workflow step and the network, where the guard is standard-library and offline. Rejected.
- **The manifest lines the commit changes**: on a reserved branch only Dependabot writes them, as it writes the
  message; they're present on a push as well as a pull request; and they're what actually changes. Chosen.

### D2. Which commits are requirement updates

A copied pattern, `DEPENDABOT_REQUIREMENT`, matches Dependabot's requirement subject:
`<prefix>[Uu]pdate <dependency> requirement`, optionally followed by `from <range> to <range>` and `in <directory>`.
A commit whose subject matches it is read by D3. Every other commit keeps today's reading, so no version bump's
result changes. `dependabot_subject_kind` stays as it is for bump subjects.

### D3. Reading a requirement commit

For each requirement commit, from `git diff-tree -p -U0` of that commit:

1. **Manifest lines.** Only `package.json` and `pyproject.toml` are read. The commit's other paths may only be
   `package-lock.json` or `uv.lock`; anything else makes it unreadable here (the path rule names it as well).
2. **Pairs.** In each hunk, the removed lines and added lines must be equal in number; the k-th removed line pairs
   with the k-th added line. No manifest line changed is unreadable.
3. **Only versions move.** With every run of dotted digits (`\d+(?:\.\d+)*`) replaced by a placeholder, the two lines
   of a pair must be identical. So operators, names, quotes and order are unchanged, and the k-th number of one line
   pairs with the k-th of the other.
4. **The dependency.** The removed line must name the subject's dependency, compared after PEP 503 normalisation
   (lower case, each run of `-`, `_`, `.` as `-`) and bounded by characters that can't be part of a name, so
   `uv-build` matches `uv_build>=` but not `uv-build-extra`.
5. **Counting.** Each number pair that differs is counted with `dependabot_update_kind`, and must go up (compared as
   integer tuples padded with zeros). One that goes down is unreadable. The commit's kind is the largest of its
   pairs (patch < minor < major); no differing pair is unreadable.
6. **Two readings agree.** If the subject carries `from <range> to <range>`, its kind (D4) must equal the diff's;
   if they differ, the commit is refused, as an `update-type` that disagrees is today (dependabot-exemption D5).
   `update-type:` lines are checked as today.

So `<0.14` to `<1` is major, and `<0.14` to `<0.15` is minor, as `0.13.5` to `0.14.0` already is for a bump.

### D4. One counting for ranges, copied into both readers

`dependabot_issues.py` gains `range_kind(old, new)`: split each range into specifiers on commas and spaces, each an
operator (`>=`, `<=`, `==`, `!=`, `~=`, `>`, `<`, `^`, `~`, `=`, or none) and a version matching `VERSION`; both
ranges must have the same operators, each once; pair by operator, then count as D3 step 5 does. `read_update` uses
it when the title is a requirement title. The guard carries a copy (it can't import infrastructure's scripts), used
by D3 step 6, and both share the pair counting with D3 step 5.

Tests hold them together: the patterns are compared as today; the real title of #181 gives patch in both; and a
property test generates ranges, renders each as a `pyproject.toml` line pair (fixed order) and as a title (old
range's specifiers shuffled, as Dependabot writes them), and asserts the guard's diff reading and the issue's title
reading give the same kind.

### D5. Refusals name what failed

The reasons join `dependabot_ineligibility`'s list, so the refusal stays under `commit-branch-change` with the
existing fix:

- `<sha> ('<subject>') is a major update` (as for a bump);
- `<sha>'s requirement versions can't be read as a minor or patch update: <path> '<removed line>' to '<added line>'
  <why>`, where `<why>` is one of "changes more than version numbers", "doesn't name <dependency>", "lowers a
  version", "doesn't pair line for line", or "changes no manifest line";
- `<sha>'s subject and diff disagree: the subject's ranges are <kind>, its diff <kind>`.

Lines are trimmed to 120 characters in the message.

### D6. Delivery and #181

One pull request carries the guard, `dependabot_issues.py`, the tests and the docs. Its plan changes the delivered
`scripts/guard.py` in troupe and website. After the apply, troupe #181 is rebased with `@dependabot rebase` and must
pass `guard`. Its issue, troupe #179, keeps its old body (D4 changes only new and relinked issues), so it gets a
comment saying the update now reads as a patch and takes the light path.

## Risks / Trade-offs

- **[Trade-off] A 0.x minor step is exempt.** `<0.14` to `<0.15` counts as minor, though 0.x releases may break. This
  matches how a bump from `0.13.5` to `0.14.0` is already counted, and the owner's merge is still the gate. Changing
  it would be a policy change for bumps too, out of scope here.
- **[Trade-off] A deliberate cap can move without an OpenSpec change.** troupe caps `ruamel.yaml` at `<0.20` on
  purpose (config-model D8: a release that renders differently changes files' hashes), and `<0.20` to `<0.21` counts
  as minor. Refusing cap moves was weighed (raised by a side agent, 2026-10-29) and not adopted (owner, 2026-10-29):
  the guard decides how much process an update needs, not whether it's safe. A cap move that breaks something has to
  be caught by the product's tests failing the build. A refusal would only add an OpenSpec change around the same diff,
  and nobody would catch the break just by looking at it. So a cap's protection rests on troupe's tests covering the
  behaviour it guards. The same holds for a bump commit that rewrites manifest lines, which the exemption doesn't
  read.
- **[Risk] A line that coincidentally pairs.** Two unrelated lines in one hunk could pair. → Step 3 requires them
  identical but for numbers, and step 4 requires the dependency's name, so a mismatched pair is refused, not passed.
- **[Risk] Dependabot rewrites a line's layout** (reorders bounds, changes quoting). → Step 3 refuses it: red, not
  wrongly green, and the refusal shows the lines.
- **[Trade-off] Lock files aren't read.** A requirement commit could in principle move a locked version further than
  its range. The range bounds what can be locked, and the bump path already trusts lock files this way.
- **[Risk] The copies drift.** → The property test of D4, and the existing pattern comparison.
