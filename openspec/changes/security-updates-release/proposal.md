# Proposal

## Why

troupe-run/troupe#214 decided (owner, 2026-10-31) that a Dependabot security update to a runtime dependency of a
package troupe ships releases a patch, at any severity, while version updates and development dependencies ride along
with the next release (#240). Today every Dependabot pull request is `chore(deps)` or `chore(deps-dev)`, and troupe
merges by rebase through the merge queue, so Dependabot's commit lands on `main` unchanged and release-please never
releases anything for it.

## What Changes

- **A probe first.** On a throwaway `troupe-run/infra-probe-*` repository laid out like troupe (linked-versions
  group, `bump-minor-pre-major`, rebase merges through a merge queue), check that release-please honours a
  `BEGIN_COMMIT_OVERRIDE` … `END_COMMIT_OVERRIDE` block in a rebase-merged pull request's description: the release
  pull request lists the overridden commit as a fix and bumps the patch, while a `chore(deps)` pull request in the
  same window bumps nothing. Also check that an override on a commit touching only the root (`uv.lock`) releases
  nothing. Nothing after the probe is built until it passes; if it fails, the change stops and the owner chooses
  another mechanism.
- **`dependabot-issues` adds the override.** For a Dependabot pull request that counts as a security update (the
  existing open-alerts rule), is titled `chore(deps):` (a runtime dependency, not `chore(deps-dev):`), and comes from
  a repository's ecosystem declared as shipping in a release, the run adds an override block to the description that
  reads the same title as `fix(deps): …`. It puts the block back when Dependabot rewrites the description, as it does
  the `Closes` line, and never takes one away.
- **Which ecosystems ship is declared once**, in `tofu/dependabot.json`: troupe's `uv` only. release-please's own
  package paths then limit a release to the `packages/*` and `plugins/*` a commit touches, so a lock-only or
  root-only change releases nothing.
- A pull request still missing a due override over an hour after it last changed counts as a missed event, like a
  missing closing line.
- `docs/development-workflow.md` says what the override is for, and how to recover when one was missed before a
  merge (add it to the merged pull request's description before the release pull request merges).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dependency-updates`: a new requirement that a shipped runtime dependency's security update carries release-please's
  `fix(deps)` override, declared per repository and ecosystem; and "A missed event is reported" counts a missing
  override too.

## Impact

- `scripts/dependabot_issues.py` and `scripts/tests/test_dependabot_issues.py`: a new `override` action next to the
  closing `line`, the declaration read and checked, misses widened.
- `tofu/dependabot.json`, and `scripts/check.py` / `scripts/dependabot_config.py` checking the new key names a
  declared repository and ecosystem. The generated `dependabot.yml` files don't change.
- `docs/development-workflow.md`.
- No new App permission: the App already edits Dependabot pull requests' descriptions and reads alerts (#238).
- troupe: no file changes here. `contributing/releasing.md` saying a security update releases belongs to
  troupe-run/troupe#215, which rewrites that page.
- A throwaway probe repository, deleted when the probe is done.
- `scripts/dependabot_issues.py` also changed in #238 (alerts read, PR #239). That merged before this branch was cut,
  so there's nothing to rebase over, but any other open change to the script should rebase onto whichever merges
  first.
