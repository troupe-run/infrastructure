# Proposal: declare the release milestones in every managed repository

## Why

troupe's release automation (#34, troupe-run/troupe#23) makes its next release 0.1.0, and the owner wants the roadmap
board to follow the releases: 0.1.0, 0.2.0 and 1.0.0 as now, next and later, with issues moved between them as work
comes up (owner, 2026-10-17, #68). A GitHub milestone belongs to one repository, though. Today only troupe has one
(`alpha-0`), so an infrastructure or website issue can't be filed under a release at all. Copies made by hand aren't
linked, and the board shows two groups as soon as one title differs. Declaring the set once here keeps the copies
identical.

## What Changes

- `tofu/milestones.json` declares the release milestones once: a stable key for each, its title, its description
  and whether it's open. It also lists the repositories that get them: all four managed repositories (troupe,
  infrastructure, website and `.github`).
- `tofu/milestones.tf` creates every declared milestone in every listed repository, so the titles and descriptions
  are the same everywhere. No milestone can be destroyed by an apply. A finished release's milestone is closed, not
  removed, so its issues keep it.
- troupe's `alpha-0` (milestone 1, with 3 closed issues) is imported as troupe's 0.1.0 and renamed in place, so its
  issues stay with the release they shipped in (owner, 2026-10-17). Its description is kept, because it already
  describes 0.1.0: the walking skeleton.
- `scripts/check.py` fails when the milestone repository list and the managed repositories in `repositories.tf`
  differ, or the declaration is malformed (a duplicate key or title, or an unknown state).
- `scripts/oob.py` reports a milestone on a listed repository that isn't declared, because an apply only manages the
  milestones it declares. A milestone made by hand would otherwise go unnoticed.
- No due dates for now.

Out of scope:

- **Which issue goes in which milestone.** That's triage on each issue. The first sweep runs once the milestones
  exist, and is recorded on #68.
- **Board views**, such as a roadmap view grouped by milestone. GitHub's API can't create or change a Projects v2
  view, so the owner sets them up by hand.
- **Closing a milestone when its release ships.** That stays a pull request here for now. Automating it from troupe's
  release workflow would be its own issue.

## Capabilities

### New Capabilities

- `milestones`: the release milestones every managed repository has, declared once with the same titles and
  descriptions, never destroyed by an apply, and reported by the drift check when one is made by hand.

### Modified Capabilities

None.

## Impact

- New: `tofu/milestones.json` and `tofu/milestones.tf`. An import block for troupe's milestone 1 in
  `tofu/imports.tf`.
- `scripts/check.py`'s tests and `scripts/oob.py` (with its tests) gain the checks above.
- An apply, after the owner approves its plan, creates 11 milestones (0.1.0, 0.2.0 and 1.0.0 in infrastructure,
  website and `.github`, plus 0.2.0 and 1.0.0 in troupe), and renames troupe's `alpha-0` to 0.1.0. No issue changes
  milestone.
- The infrastructure App already has `issues: write` on every managed repository, which covers milestones, so it
  needs no new permission or installation.
