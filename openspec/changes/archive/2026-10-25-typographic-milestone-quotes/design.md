# Design

## Context

See proposal.md for why and for the four descriptions.

- `tofu/milestones.json` is pure ASCII today. Nothing else under `tofu/` has a typographic quote yet, raw or escaped,
  so this is the first non-ASCII text in a declaration.
- `tofu/milestones.tf` reads the file with `jsondecode(file(...))`. `file()` reads UTF-8. Each milestone's
  `description` goes straight to `github_repository_milestone.release`, and a description change is an in-place update
  (milestones spec, "A declared description changes").
- The milestone check is `declaration_problems` in `scripts/tests/test_milestones.py`, which `scripts/check.py` runs.
  It already checks keys, titles, states and interim titles, and returns one message per problem.
- The website reads `title` and `description` from this repository's `main` and shows the description verbatim. Since
  #124 (`rebuild-site-on-milestones`, applied in bfa5435), a push to `main` that changes `tofu/milestones.json` runs
  `.github/workflows/milestones-notice.yml`, which dispatches the website's `deploy.yml`. The trigger is the merge,
  not the apply.
- The drift check (`scripts/oob.py`) compares milestone titles only, so a description change doesn't affect it.

## Goals / Non-Goals

**Goals:**

- One apply that changes four descriptions by one character each in every managed repository, and nothing else.
- A check that keeps a straight quote out of every description from now on.

**Non-Goals:**

- A general typography check (dashes, ellipses, spacing). Only quotes, as #127 asks.
- Checking label descriptions or any other file. #127 is about what /status/ shows from `tofu/milestones.json`.

## Decisions

### D1. Write ’ as the character itself, not `’`

The four apostrophes become the raw UTF-8 character `’` (U+2019), not the JSON escape `’`.

- **Why:** the file is read and edited by people, and the website shows it verbatim. The raw character reads the way
  the page does, and a diff shows the change as it'll appear. `file()` and Python's `json` both read UTF-8, and the
  check's tests read the file with `encoding="utf-8"`.
- **Alternative:** `’`. Same text once decoded, but unreadable in review, and it invites a mix of the two forms.
  Rejected.

All four are apostrophes inside a word, so each is ’. None is an opening quote.

### D2. Add the rule to the existing declaration check

`declaration_problems` gains one loop: for each milestone, if its description has `'` or `"`, it adds one message per
milestone and character, such as:

```
0.6.0: description has a straight apostrophe ('); use ’ for an apostrophe or closing quote and ‘ for an opening one
0.6.0: description has a straight double quote ("); use “ and ”
```

- **Why here:** it's where every other rule on the declaration lives, it already runs on every pull request through
  `scripts/check.py`, and its messages already name the milestone by title. #125's rules can sit beside it, and
  nothing in this rule needs undoing for them.
- **Why not auto-fix:** whether a `'` is an apostrophe or an opening quote depends on the sentence. The check names
  the choice and leaves it to the author.
- **Why only descriptions:** titles are version numbers and interim titles are short-lived labels the website never
  shows, so neither reaches /status/'s prose.
- **Alternative:** a separate test file or a lint in `scripts/check.py` itself. Rejected: two places describing one
  file's rules.

The test that the declared file is well formed (`test_the_declared_milestones_are_well_formed`) then passes only once
D1's edit is made, which checks that the edit is complete.

### D3. Let the merge rebuild /status/, and look at it

No manual deploy. When the pull request merges, the milestones notice dispatches the website's Deploy on `main`
(milestones spec, "A milestone is re-described"). This change verifies that a Deploy run started from that push and
succeeded, then checks troupe.run/status/ shows the four descriptions with ’ and no straight apostrophe anywhere in
the milestone list. It's also the notice's first live run on a description change.

- **If the notice doesn't fire or the deploy fails:** report it to the owner with the run's link rather than fixing it here. The
  owner can still dispatch `deploy.yml` by hand to get /status/ right.

## Risks / Trade-offs

- **[Risk] An editor or tool rewrites the file as ASCII with `’` escapes** → the check reads the decoded string,
  so either form passes it. The only effect is readability, and review catches it.
- **[Risk] A description really needs a straight quote** (a code sample, an inch mark) → none does today. If one ever
  does, the rule is changed by a pull request to this spec, not worked round.
- **[Trade-off] /status/ updates at the merge, before the apply** → the milestones on GitHub lag the page until the
  owner approves the apply. Both show the same text once it runs.

## Migration Plan

One pull request, one apply: 16 in-place description updates (four milestones × four repositories). Rollback is a
revert and another apply, also in place, and the revert's merge rebuilds the site again.
