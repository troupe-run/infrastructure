# Proposal

Issue: #127.

## Why

troupe.run/status/ shows each milestone's description word for word (troupe-run/website#32). The rest of the site
uses typographic apostrophes (’), but four descriptions in `tofu/milestones.json` have straight ones, so the page
mixes the two. The owner asked for the fix to be made in the content here, not by rewriting quotes when the site
renders them (2026-10-23, #127).

#127 lists three, by their titles before the renumbering of 2026-10-24 (#128, #129). A fourth arrived with that
renumbering. Today they are:

| Key | Title | Straight quote in |
|---|---|---|
| `0.14.0` | 0.2.0 | "its engine's own API" (added by #129, after #127 was written) |
| `0.2.0` | 0.3.0 | "troupe's files" (#127's 0.2.0) |
| `0.5.0` | 0.6.0 | "can't decide" (#127's 0.5.0) |
| `0.13.0` | 0.14.0 | "each actor's declared effects" (#127's 0.13.0) |

## What Changes

- **The four descriptions use ’.** Each straight apostrophe in `tofu/milestones.json` becomes ’, and nothing else in
  the file changes. The apply updates those four descriptions in place in every managed repository (design D1).
- **`scripts/check.py` refuses a straight quote in a description.** A `'` or `"` in any declared milestone's
  description fails the existing milestone check, naming the milestone and the typographic characters to use, so the
  file stays this way. #127 makes this optional; it's included because the fourth description shows a new one can
  slip in, and it's a few lines in a check that already exists (design D2).
- **troupe.run/status/ is checked after the merge.** The merge itself rebuilds the site, through the milestones
  notice that #124 added, so this change only verifies the result (design D3).

Out of scope:

- The website's own rules for the file (title format, non-empty description). They're #125's, which this change
  doesn't add to or depend on.
- Other ASCII stand-ins, such as `--` or `...`. No description has one, and #127 asks only about quotes.
- Titles and interim titles. They're version numbers, and the website doesn't show interim titles.
- Rewriting quotes when the site renders them. The owner ruled that out (#127).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `milestones`: "The milestone declaration is well formed" also fails on a straight apostrophe or straight double quote
  in a description.

## Impact

- `tofu/milestones.json`: four descriptions, one character each.
- `scripts/tests/test_milestones.py`: the declaration check and its tests.
- GitHub, after the owner approves the plan: 16 milestones updated in place (four in each of troupe, infrastructure,
  website and `.github`), description only. Nothing is created, destroyed or replaced, and no issue changes milestone.
- troupe-run/website: one Deploy run, dispatched by the milestones notice when the pull request merges.
- troupe.run/status/: the four descriptions show ’ once that deploy finishes.
- #127 is closed by this change's pull request.
