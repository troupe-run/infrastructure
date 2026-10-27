# Proposal

Issue: #174, sections 3, 4 and 6 of #170.

## Why

Every Dependabot pull request in troupe, website and infrastructure is red today: its `dependabot/...` branch matches
no OpenSpec change, so the `guard` check refuses it under `commit-branch-change`. The owner decided that a minor or
patch update shouldn't need an OpenSpec change (#170, 2026-10-26). Its issue and closing line now arrive from
`dependabot-issues` (#172), and `pr-closes-issue` is checked on GitHub (#173), so the branch rule is the only thing
left in the way. Thirteen Dependabot pull requests are open today, website #44, #45 and #46 among them, kept open to
test this on.

The exemption mustn't be one anyone can claim. A `dependabot/` name proves nothing unless GitHub stops everyone else
from writing such a branch, as troupe's ruleset does for `release-please--` (#47). So the change starts by proving
that a ruleset can reserve the name for Dependabot alone. **If it can't, the change stops there** (owner,
2026-10-26): nothing below is built, and Dependabot's pull requests keep the manual path.

## What Changes

- **First, a probe** on a throwaway `troupe-run/infra-probe-*` repository. It checks that a ruleset can let only
  Dependabot (App 29110) create and update `dependabot/**` branches, that Dependabot still opens, rebases and
  recreates its pull requests under it, and that the owner can't push to one. If any of that fails, the change stops
  and reports to the owner (design D1).
- **A "dependabot branches" ruleset** in each repository that gets a `.github/dependabot.yml` (troupe, website,
  infrastructure). It refuses creating and updating `dependabot/**` branches to everyone but Dependabot, with no
  owner bypass. Force-pushes and deletion stay allowed, for Dependabot's rebases and delete-on-merge (design D2).
- **The guard's `commit-branch-change` rule exempts a Dependabot branch on GitHub** only when all of these hold
  (design D3-D5):
  1. its name starts with `dependabot/` and it lives in a repository whose ruleset reserves that name;
  2. every commit on it changes only dependency files: `package.json`, `package-lock.json`, `pyproject.toml`,
     `uv.lock`, and workflow files where every changed line is a `uses:` line;
  3. every commit's message is Dependabot's for a single minor or patch update, read from its versions and, where
     present, its `update-type`.

  Who authored the commits isn't checked. The ruleset makes "only Dependabot's commits" true, and the guard doesn't
  guess identity from what a pusher wrote (#47; design D3).
- **A failed condition is refused as today**, under `commit-branch-change`, and the refusal says which condition
  failed and that the update takes the full path (design D6). A major update, an unreadable one (such as a
  requirement-range update), one touching other files, or a `dependabot/` branch in a repository without the ruleset
  takes an OpenSpec change.
- **Everything else still applies** to an exempt branch: Conventional Commit messages and title, `pr-closes-issue`,
  delivered files, schema commit types, archived tasks, and the other required checks.
- **security-scanning D5's pinning test and its scenario change deliberately**: they now say which Dependabot pull
  requests are exempt and which aren't, with a test for each condition failing. The guard's minor-or-patch counting
  is tested against `dependabot_issues.py`'s, so the issue and the check agree on what a patch is (design D4).
- **`docs/development-workflow.md`** is rewritten for both paths: minor and patch merge as they are; majors and the
  rest take an OpenSpec change. It says to use `@dependabot rebase`, not GitHub's "Update branch", which the ruleset
  refuses.
- **After delivery**, the open Dependabot pull requests pick the rule up when Dependabot rebases them. website #44,
  #45 and #46 (or their successors) are the test: they pass `guard`, and website #55 (typescript, major) stays red.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: the GitHub check exempts a minor or patch, dependency-only Dependabot branch from the
  branch rule where a ruleset reserves its name; the scenario that says no exemption covers a Dependabot branch is
  replaced.
- `dependency-updates`: a ruleset in each repository with a Dependabot configuration lets only Dependabot create or
  update its branches.

## Impact

- `scripts/guard.py`: the exemption, its constants and its refusal text. Delivered, so troupe and website receive it
  after the owner approves the delivery plan.
- `tofu/dependabot.tf`: the ruleset in three repositories. The plan adds three rulesets; the owner approves it.
- `scripts/tests/`: the D5 pinning test replaced by tests for each condition; a tofu-text test that every repository
  the guard exempts has the ruleset declared; a differential test of the update counting.
- `docs/development-workflow.md`: the `commit-branch-change` row and the Dependabot section.
- Open Dependabot pull requests turn green once rebased onto the delivered guard, where they qualify.
