# Design

## Context

`tofu/milestones.tf` makes one `github_repository_milestone.release` per repository and milestone, keyed
`<repository>/<key>`, with `title = milestone.title`. Keys never change, so a title change is a rename in place, and
`prevent_destroy` refuses anything else (release-milestones design D1, D2). The same file feeds three readers:

- the drift check, `scripts/oob.py` `undeclared_milestones`, which reports a title on GitHub that isn't declared;
- `scripts/tests/test_milestones.py`, which `scripts/check.py` runs, and which refuses a duplicate key or title;
- troupe.run's /status/, through website `scripts/roadmap-lib.mjs`. It reads `tofu/milestones.json` from this
  repository's `main` and reads only `title` and `description`. It refuses a title that isn't `MAJOR.MINOR.PATCH` or
  that's declared twice, ignores every other field, and orders by `byVersion(title)`, not by key or file order.

Live state, read 2026-10-24: every managed repository has all 21 milestones, under titles equal to their keys. In
troupe, key `0.14.0` (milestone 20) holds 2 open issues (#56 and #162), and key `0.2.0` (milestone 3) holds 3 open and
2 closed.

Why two applies, not one, is in proposal.md. The owner chose two changes, each a normal pull request and CI apply,
over a single change with a break-glass interim apply (2026-10-24).

## Goals / Non-Goals

**Goals:**

- One apply that takes the 13 milestones to titles that collide with nothing, in place, in every managed repository.
- A declaration that says the final order from the start, so /status/ never shows a temporary title.
- A way to move titles that's left in place for the next renumbering, not code written for this one and removed.

**Non-Goals:**

- Ordering renames inside one apply. OpenTofu doesn't order the instances of one `for_each`, and a cycle has no
  order that works anyway.
- Detecting at plan time that a rename would collide with a title on GitHub. `scripts/check.py` works offline from
  the declaration. The drift check keeps GitHub's titles equal to declared ones, so a collision with a declared title
  is what can happen, and that's what check.py refuses.

## Decisions

### D1. An optional `interim_title` field, applied instead of `title`

`tofu/milestones.tf` applies `interim_title` when it's declared, otherwise `title`. Each milestone is normalised to
the same attributes before `setproduct`, with an `applied_title` built by `try(milestone.interim_title,
milestone.title)`. `jsondecode` gives a tuple of objects, and once some have `interim_title` and others don't they
no longer unify into one list type, which `setproduct` needs. The normalised object has the four existing fields
plus `applied_title`, so the instance keys don't change.

Alternatives:

- **Write the interim titles into `title`.** That needs no code, but /status/ refuses a title that isn't a version.
  A website build between the two applies would fail, and the page would show temporary versions if they were made
  to look like versions.
- **A top-level `"renumbering": true` switch** that tells OpenTofu to give every changed milestone a title made from
  a pattern. OpenTofu can't tell which milestones changed without reading GitHub, so the switch would still need a
  list. Naming the interim title on each milestone says exactly what the apply will do.
- **A `terraform_data` with a local-exec that renames through the API before the update.** It's a second route to
  the same write (memory: one way per write), and the plan wouldn't show what it does.

### D2. The interim titles say where the milestone is going

Each is `<final title> (renumbering)`, as in `0.2.0 (renumbering)` on key `0.14.0`. On the board and in the issue
filter, between the two applies, an issue's milestone still says which release it's in. The suffix makes it collide
with no version title. check.py enforces the uniqueness itself (D3), so the format is a convention for whoever writes
the next one, written in README, not a rule.

### D3. check.py refuses a colliding or malformed interim title

`declaration_problems` gains two checks:

- an `interim_title` that's present and isn't a non-empty string is an error naming the milestone, not a fall-through
  to `title` (learned rule: malformed input is an error);
- titles and interim titles share one namespace, because that's what GitHub checks. An interim title equal to any
  declared title, or to another milestone's interim title, is an error naming the milestone and the title.

The existing duplicate-title check stays on `title` alone. A milestone's own title and interim title being equal is
refused by the second check, since its title is a declared title. The messages follow the existing form
(`<milestone>: ...`).

### D4. The drift check counts both titles as declared

`undeclared_milestones` builds its declared set from every `title` and every `interim_title`. Between this change's
merge and its apply, GitHub still has the 13 under their old titles, which are all declared `title`s. After the apply
it has the interim titles. Counting only the applied title would report 52 false differences in that window, and
whether a declared milestone has the right title is the plan's business anyway, not the drift check's (release-milestones
design D5).

### D5. The declaration takes #128's final order now

In `tofu/milestones.json`, key `0.14.0` gets `title` "0.2.0", `interim_title` "0.2.0 (renumbering)", and the
description "Other runners: an actor runs on a local model through its engine's own API, or on any OpenAI-style API,
without Claude Code". Keys `0.2.0` to `0.13.0` each get `title` one minor version up, and an interim title of that
version with the suffix. Their descriptions don't change. The file's order stays by key, since the website orders by
title anyway and the key order keeps the diff to the changed lines.

The plan should show 52 updates in place, 4 of them with a description change too, and no create, destroy or replace.
Anything else stops the apply.

### D6. A probe on a throwaway repository

`tofu/probe/main.tf` gains `probe_milestones`. It declares three milestones on `troupe-run/infra-probe-milestones`
with the live resource's title expression (D1), in three steps set by variables:

1. keys `a`, `b`, `c` titled `0.2.0`, `0.3.0`, `0.4.0`, with one issue filed in each by `gh issue create --milestone`;
2. the titles rotated (`a` → `0.3.0`, `b` → `0.4.0`, `c` → `0.2.0`) with no interim titles: the apply should fail on
   GitHub's duplicate-title refusal. Its error is recorded, and the next plan shows what was and wasn't renamed;
3. from a clean state, the same rotation with interim titles, then without them: both apply, and each issue's
   milestone number is unchanged at the end.

The probe copies the title expression instead of reusing `milestones.tf`, like the other probes copy theirs. That copy
is a second place for the same rule, which the probe's comment names. The repository is created and deleted by the
agent (memory: throwaway repo naming). Adding it to the App's installation is the owner's step.

## Risks / Trade-offs

- **[GitHub doesn't refuse duplicate titles on a rename]** → then the probe's step 2 applies. The interim titles
  still do no harm, but they're unneeded: the probe result goes on #128 and #129, and the owner decides whether
  #128 applies the final titles in one step instead.
- **[The apply partly fails]** → each interim title is unique and taken by nothing else, so a retry of the same plan's
  successor can only rename what's left. The next plan shows what remains.
- **[#128 merges before this change's apply]** → its plan would rename straight from the old titles to the final ones
  and hit the collision. #128's branch is rebased onto this change's state commit before its plan (memory: plan against
  current state), and its tasks start by checking GitHub has the interim titles.
- **[A website build between the two applies]** → /status/ reads `title`, which is final in both, so it shows the same
  order either way.
- **[The board's Milestone grouping shows the interim titles]** → for the time between the two applies. D2 keeps each
  readable.

## Migration Plan

1. Merge this change and approve its apply. The 13 milestones carry their interim titles in every managed repository.
2. #128's change removes the interim titles. Its apply gives the final titles.

Rollback before #128: revert `tofu/milestones.json`. The plan renames the 13 back from their interim titles to the old
ones, which nothing holds.
