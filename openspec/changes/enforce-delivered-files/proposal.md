# Proposal

Issue: #35. Found while auditing the guard for the gap #34 closes for #33's release-branch exemption.

## Why

In a governed repository (`troupe`), the guard's GitHub check accepts a commit that changes a delivered file when the
commit's author email is the infrastructure App's bot. A commit's author is self-declared (`git commit --author`), so
anyone can forge it. The forged commit passes `guard`, merges once reviewed, and shows only as drift in the next
plan, and nothing plans on a schedule. Worse, the check runs the pushed copy of `scripts/guard.py` and
`.github/workflows/guard.yml`, which are themselves delivered files, so a push can also change the check that judges
it. Nothing in the guard can be the hard check. It has to be GitHub's. `docs/development-workflow.md` already lists
this under Known gaps.

## What Changes

- **Probe first,** on a throwaway `troupe-run/infra-probe-*` repository (public, like `troupe`). Find out whether a
  push ruleset with a `file_path_restriction` rule can be created on a public repository on GitHub Free, whether it
  refuses someone else's push and API edit to a restricted path, and whether the App's delivery still lands. Then
  delete the repository. GitHub's docs say push rulesets cover private and internal repositories only, so the probe
  may well say no. Its result picks the path below.
- **If push rulesets work:** a `delivered files` push ruleset on each repository that receives the guard. It
  restricts every delivered path (`guard_files` plus `.github/guard-delivery.json`), and the infrastructure App is
  its only bypass actor. No one else bypasses it, the owner included. The owner's break-glass is editing the ruleset,
  as for every ruleset. The paths come from `tofu/guard_delivery.tf`, so the ruleset can't disagree with what is
  delivered.
- **If they don't:** a plan of `main` every day (the issue's fallback; owner, 2026-10-13). A forged edit then shows
  in a plan within a day of landing, and approving that plan's apply restores the file. design.md (D5) holds the spec
  text for this path, so apply carries on after the probe without stopping for a revision.
- **The guard's author check stays,** recast in the spec as what it is: the check that catches an honest mistake
  early, not the enforcement.
- **`docs/development-workflow.md`'s Known gaps entry** is replaced. With the ruleset, it says what is left: the
  owner's break-glass. With the fallback, it says how long a forged edit can go unseen.

Out of scope:
- the release-branch exemption and its ruleset (#33, #34);
- making the guard's CI check run a trusted copy of itself and verify GitHub's signature on a delivery, which would
  refuse a forged edit before it merges. It becomes a follow-up issue (design D5);
- the `infrastructure` repository, which is the source and isn't restricted, and `.github`, which `app only` already
  restricts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- **`rulesets`:** a repository that receives the guard gets a ruleset under which only the infrastructure App
  changes a delivered file. The rule that limits which rulesets name the App gains this one.
- **`guard-delivery`:** "Delivered files are changed only at their source" is enforced by GitHub. The guard's check
  on the commit's author becomes the early, honest-mistake check behind it.
- **`ci-apply`** (fallback path only): `main` is planned every day, not only after a merge.

The spec files describe the ruleset path. If the probe rules it out, task 1.5 replaces them with design D5's text:
`rulesets` gets no delta, `guard-delivery` says the daily plan shows a forged edit, and `ci-apply` gains the daily
plan.

## Impact

- **Changed:**
  - `tofu/modules/repository` (a push ruleset over a list of paths);
  - `tofu/repositories.tf` and `tofu/guard_delivery.tf` (the delivered paths passed to `troupe`'s module);
  - `tofu/probe/main.tf` (the probe's variable);
  - fallback path only: `.github/workflows/tofu.yml` (the schedule) and the README's "Running a plan";
  - `docs/development-workflow.md` (Known gaps and the delivered-file rule);
  - `README.md` if it describes the rulesets.
- **GitHub:** one new ruleset on `troupe` (ruleset path), or a daily workflow run on this repository (fallback
  path). A follow-up issue for the pre-merge check.
- **Probe:** one throwaway repository, created, added to the App's installation by the owner, and deleted.
- **The owner, by hand:** adds the probe repository to the App's installation; approves the plans and the apply.
