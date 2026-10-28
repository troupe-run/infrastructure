# Proposal

Issues: #204, #205 and #206, all part of #194's look back.

## Why

#194's look back at the Dependabot exemption (#193) and the capability-label check (#168) found three gaps in
`scripts/guard.py`, each one where the guard passes, or sends, something it shouldn't. Two let a Dependabot branch be
exempt while changing more than dependency files. The third lets the run's token go wherever a redirect points. The
rulesets and the token's narrow scope lower the risk, but don't remove it. All three are small fixes to the same file,
so they go as one change with one delivery.

## What Changes

In the order the tasks fix them, each with a test that fails before its fix:

1. **#204: a workflow line that begins with `--` counts.** The exemption's "only `uses:` lines" test skipped every diff
   line starting `---` or `+++`, meaning to skip the file headers. A removed content line that begins with `--` (a
   YAML `---`, or a `--force` at column 0), or an added one that begins with `++`, was skipped too. Only the
   `--- a/…` and `+++ b/…` header lines are skipped now, so such a line makes the workflow a non-dependency file
   (design D1).
2. **#205: a merge commit isn't exempt.** A merge commit's paths were listed with plain `diff-tree`, which prints
   nothing for a merge, so a merge with a Dependabot-shaped subject passed as "dependency files only", whatever it
   brought in. Any merge commit now makes the branch ineligible, with a reason naming the commit and saying Dependabot
   doesn't make merge commits (design D2).
3. **#206: the capability-label read's token isn't re-sent on a redirect.** The `Authorization` header is added as one
   urllib doesn't carry to a redirect's request, so the token goes only to `api.github.com` (design D3).

`docs/development-workflow.md`: the `commit-branch-change` row and the "Dependabot pull requests" section say a merge
commit isn't exempt and that every changed workflow line counts; the `capability-label` row says the token isn't sent
on a redirect.

Out of scope: the rest of #194's look back, and any change to the rulesets that reserve `dependabot/` branches.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: a scenario added to "An exempt Dependabot branch changes only dependency files" for a
  workflow line that begins with `--`; a new requirement that a branch with a merge commit isn't exempt; a new
  requirement that the capability-label read sends its token to GitHub's API only.

## Impact

- `scripts/guard.py`: `_only_uses_lines`, `dependabot_ineligibility` and `declared_labels`. Delivered, so troupe and
  website receive it after the owner approves the delivery plan (`guard_targets` in `tofu/guard_delivery.tf`). The
  plan changes only `scripts/guard.py` in each of the two.
- `scripts/tests/test_guard_dependabot.py` and `scripts/tests/test_guard_capability_labels.py`: a new test per fix.
- `docs/development-workflow.md`: two table rows and the Dependabot section.
- An open Dependabot pull request that passed only through one of these gaps goes red once delivered. None is expected:
  Dependabot makes no merge commits, and its action bumps change only `uses:` lines.
