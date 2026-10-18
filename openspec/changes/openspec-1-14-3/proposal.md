# Proposal: regenerate the OpenSpec skills with 1.14.3, and ignore .claude/settings.local.json

## Why

infrastructure's generated OpenSpec files say `generatedBy: "1.14.1"`. These skills and commands drive every change's
workflow, so they should come from the current OpenSpec release (#58). The issue asked for 1.14.2, to match
troupe-run/website (website#6). 1.14.3 came out on 2026-10-17, and the owner chose it (2026-10-18: "get it to the
current up to date version"). Separately, `.claude/settings.local.json` is ignored here only by the owner's personal
git config, so anyone else could commit theirs. website's `.gitignore` already ignores it (owner, 2026-10-16: fold it
into this change).

## What Changes

- `openspec update`, run with OpenSpec 1.14.3, regenerates the nine files it owns that differ from main's. They're
  regenerated, not hand-edited:
  - From 1.14.2: `.claude/skills/openspec-explore/SKILL.md` and `.claude/commands/opsx/explore.md` say that, with a
    schema other than the default, insights go into whichever artifact the schema defines, and their example offers
    no longer name `design.md`. `.claude/skills/openspec-update-change/SKILL.md` and `.claude/commands/opsx/update.md`
    say an edit may also go to a confirmed concrete path under a partly filled glob artifact.
  - From 1.14.3: `.claude/skills/openspec-propose/SKILL.md` and `.claude/commands/opsx/propose.md` choose an artifact's
    output path before creating anything. A path chosen under a glob must stay inside the change's directory after
    symlinks are resolved, and a delegated skill is used only if it can write to that path.
  - The other skills (`openspec-apply-change`, `openspec-archive-change`, `openspec-sync-specs`): only `generatedBy`
    changes, to `"1.14.3"`.
- `.gitignore` gains `.claude/settings.local.json`.
- Nothing else changes. `openspec/config.yaml` and `.claude/settings.json` stay as they are. `.claude/settings.json`
  is outside `openspec update`'s scope, and it's the source of the copy the guard delivers to troupe and website.

Homebrew, which installs OpenSpec locally, still offers only 1.14.2, so the update runs as
`npx -y @fission-ai/openspec@1.14.3 update`. That doesn't install anything globally, so it can't shadow Homebrew's copy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No spec names the OpenSpec version, the generated skill files or `.gitignore`'s entries, and no behaviour the
specs describe changes, so `skip_specs` is set.

## Impact

- Nine generated files under `.claude/skills/` and `.claude/commands/opsx/`, and one line in `.gitignore`.
- OpenTofu: none of these files is delivered (`tofu/guard_delivery.tf` delivers `.claude/settings.json` only), so the
  pull request's plan is expected to show no changes. It still runs, because `scripts/plan_needed.py` plans for any
  path it doesn't list as never read.
- CI: these paths are in no group in `scripts/check-paths.toml`, so the full check runs.
- infrastructure will be one release ahead of website (1.14.2) and troupe (1.14.1, troupe#113 asks for 1.14.2). Each
  repository moves in its own pull request.
