# Proposal

## Why

troupe's Dependabot `uv` job has failed on every scheduled run (2026-10-26, 2026-10-27, 2026-11-02). Dependabot
treats each workspace member as a dependency and looks it up on PyPI, where the name `troupe` belongs to an unrelated
project (0.5.2). It then runs `uv lock --upgrade-package troupe==0.5.2`, which can never resolve against the
workspace member `troupe`, and reports `dependency_file_not_resolvable` (diagnosis on troupe-run/troupe#254). The fix
is for troupe's `uv` entry to ignore troupe's own members, but `tofu/dependabot.json` has no way to declare an ignore
(#259).

## What Changes

- `tofu/dependabot.json` gets an `ignore` key: per repository, per ecosystem, a list of dependency names (Dependabot's
  `*` wildcard allowed). It declares troupe's `uv` ignoring `troupe` and `troupe-*`, troupe's workspace members, which
  move only with the workspace and, in the bundle, through the pinning pull request.
- `scripts/dependabot_config.py` renders each declared list in that repository's entry for that ecosystem as
  `ignore: - dependency-name: …`, and nothing in any other entry. `scripts/check.py` fails, naming the problem, when
  `ignore` names a repository or ecosystem that isn't declared for Dependabot, or holds an empty list or a repeated
  name.
- `tofu/dependabot/troupe.yml` is regenerated, so the next apply delivers troupe's `.github/dependabot.yml` with the
  ignore. No other generated file changes.
- `docs/development-workflow.md` and `README.md` say the policy also holds each repository's ignored dependencies.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dependency-updates`: a new requirement that an entry can ignore dependencies declared per repository and ecosystem,
  with troupe's `uv` entry ignoring its workspace members.

## Impact

- `tofu/dependabot.json`, `scripts/dependabot_config.py`, `scripts/tests/test_dependabot_config.py`,
  `tofu/dependabot/troupe.yml`.
- `docs/development-workflow.md`, `README.md`.
- The apply after the merge commits troupe's `.github/dependabot.yml` through the App (`github_repository_file.
  dependabot["troupe"]`, one in-place update). No new App permission.
- troupe: its own check that every workspace member is ignored is the OpenSpec change `dependabot-uv-resolve` on
  troupe-run/troupe#254. It reads the delivered file, so it can pass on troupe's `main` only after this change is
  applied.
