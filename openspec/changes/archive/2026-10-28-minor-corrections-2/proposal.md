# Proposal

## Why

infrastructure#143 has collected two corrections since 2026-10-26, both stale wording. The `board-credentials` spec
still describes the board key as website's alone, used only to put an issue on the board. Five file headers point at
a change's design under `openspec/changes/<name>/`, a path that moved into `openspec/changes/archive/` when the change
was archived. Neither changes behaviour, so they're batched here, as #143 says.

## What Changes

- **`openspec/specs/board-credentials/spec.md`, Purpose** (#143 comment 1): says the board App's key has two uses.
  An automated run puts an issue it opened on the board: website's weekly link check, infrastructure's watch of the
  org's scheduled workflows, and infrastructure's `dependabot-issues` workflow. And after an approved apply,
  `tofu.yml`'s board job sets the descriptions of the board's `Capability` options (spec: labels). It names both
  `board` environments, on website and on infrastructure. The Purpose is edited in the main spec, because OpenSpec
  ignores a delta's Purpose for a spec that exists.
- **The same description elsewhere**, found while checking comment 1: `README.md:28` (the `tofu/board.tf` row),
  `tofu/board.tf:1-6` (its header) and `oob/README.md:121-126` ("The board App") name only the link check and the
  schedule watch. Each gains `dependabot-issues` and the board's descriptions, in the same words as the Purpose.
- **The requirement "The board key is readable from website's main only"** is renamed "The board key is readable
  from main only". Its text has named both repositories since `watch-website-link-check`; only its name was left
  behind. Found while reading the spec for comment 1, and the same correction `rebuild-site-on-milestones` made to
  `docs-build-credentials`. Its text and scenarios don't change.
- **Change paths in file headers** (#143 comment 2): each cites its change by name and decision, as `tofu/` files
  already do, rather than by a path that moves when the change is archived:
  - `.github/workflows/dependabot-issues.yml:4` and `scripts/dependabot_issues.py:2` (`dependabot-issues`)
  - `.github/workflows/milestones-notice.yml:4` (`rebuild-site-on-milestones`)
  - `.github/workflows/schedules.yml:4` (`watch-website-link-check`)
  - `.github/workflows/tofu.yml:3` (`ci-apply`), not in the comment but the same stale path, found by searching for
    the others.

Out of scope: `pyproject.toml:2` and `oob/README.md:6` cite `openspec/changes/archive/2026-10-11-adopt-org/`, an
archived path that won't move again, so they stay. Wording that only describes `openspec/changes/<name>/` as where an
active change lives (README, the org profile, `scripts/guard.py`) is correct.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `board-credentials`: one requirement renamed, its text unchanged. The Purpose is corrected in the main spec.

## Impact

- `openspec/specs/board-credentials/spec.md`: the Purpose (direct edit) and, at archive, the renamed requirement.
- `.github/workflows/dependabot-issues.yml`, `milestones-notice.yml`, `schedules.yml`, `tofu.yml` and
  `scripts/dependabot_issues.py`: one header comment each. No workflow or script behaviour changes.
- `README.md`, `oob/README.md` and `tofu/board.tf`: prose and a comment. `tofu/board.tf` changes no resource.
- Not delivered: none of these files is in `guard_targets`. No OpenTofu resource changes. `.github/workflows/` and
  `scripts/` aren't on `scripts/plan_needed.py`'s never-read list, so `plan (pull request)` runs and asks for the
  owner's approval once; it should show no changes.
- Closes #143. Afterwards the next "Minor corrections to batch" issue is opened.
