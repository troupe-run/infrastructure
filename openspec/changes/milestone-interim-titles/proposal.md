# Proposal

Issue: #129. It's the first of two changes for #128.

## Why

#128 renumbers the release milestones for troupe-run/troupe#139's amendment of 2026-10-24. A new 0.2.0, "other
runners", takes key `0.14.0`, and keys `0.2.0` to `0.13.0` each move up one title. Those 13 titles form a cycle. Key
`0.14.0` takes "0.2.0" from key `0.2.0`, which takes "0.3.0", and so on up to key `0.13.0`, which takes "0.14.0" from key
`0.14.0`. GitHub refuses two milestones with the same title in one repository, and no order of renames breaks a cycle.
So each of the 13 has to go to a title nobody holds first, and on to its new title in a second apply. Today a
milestone's declared title is the only title OpenTofu can give it, and the website refuses a title that isn't a
version, so the declaration can't say this.

## What Changes

- **A declared milestone may carry an `interim_title`.** While it's declared, OpenTofu gives the milestone that title
  on GitHub instead of its `title`. Its `title` is still the release's version, and it's what troupe.run's /status/
  and anything else that reads the declaration uses (design D1, D2).
- **`scripts/check.py` refuses an interim title that collides** with any declared title or another interim title,
  and refuses one that isn't a non-empty string (design D3).
- **The drift check counts both titles as declared**, so neither the old title before the apply nor the interim
  title after it is reported as made by hand (design D4).
- **`tofu/milestones.json` gets #128's order.** Keys `0.2.0` to `0.14.0` get their final titles and an interim title
  each, and key `0.14.0` gets 0.2.0's new description. The apply moves those 13 milestones to their interim titles in
  every managed repository, in place (design D5).
- **A probe shows the collision and the way round it** on a throwaway `infra-probe-milestones` repository: a rotation of
  titles in one apply fails, and the same rotation through interim titles applies, with each issue still in its
  milestone (design D6).
- **README** says that a milestone's key and title can differ and the title is the version, and what an interim title
  is for.

Out of scope:

- Removing the interim titles. #128 does that, in its own change and apply.
- Renaming keys to match titles. That's a separate, deliberate migration, and the owner's call (#128).
- Rebuilding troupe.run when this repository's milestones change. #128 checks /status/ and reports that gap on
  troupe-run/troupe#139.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `milestones`: a new requirement for interim titles. "The milestone declaration is well formed" gains the interim
  title collision. "A milestone made by hand is reported" counts an interim title as declared.

## Impact

- `tofu/milestones.tf`: the title it applies.
- `tofu/milestones.json`: 13 titles changed and 13 interim titles added; one description changed.
- `scripts/tests/test_milestones.py`, `scripts/oob.py`, `scripts/tests/test_oob.py`.
- `tofu/probe/main.tf`: a milestones probe.
- `README.md`: the milestones row.
- GitHub, after the owner approves the plan: 52 milestones renamed in place (13 in each of troupe, infrastructure,
  website and `.github`), and 4 of them re-described. Nothing is created or destroyed, and no issue changes milestone.
- troupe.run/status/ shows the new order at its next build. Its titles come from `title`, which already has the final
  versions.
