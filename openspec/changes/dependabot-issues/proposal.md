# Proposal

Issue: #172, section 2 of #170's design.

## Why

A dependency update should arrive the way all other work does: an issue on the board first, then a pull request that
closes it (#170, owner). Dependabot can't open an issue or write `Closes #n` into its pull request, and since #173 the
`guard` check refuses every pull request whose description closes no issue. So today no Dependabot pull request can
merge, even once #174's exemption lands. 18 are open across troupe, website and infrastructure on 2026-10-27.

## What Changes

- **A scheduled workflow in infrastructure, `dependabot-issues`, gives every Dependabot pull request its issue.** It
  runs every 10 minutes and by hand, on `main` only. It reads the open and recently closed pull requests by
  `dependabot[bot]` in troupe, website and infrastructure. For each open one without its issue, it opens one in the
  same repository: type Task, label `dependencies`, the release in progress as milestone, on the troupe roadmap board.
  Then it adds `Closes #<issue>` to the pull request's description. Editing the description re-runs `guard` (design
  D1, D2).
- **The issue says what the update is.** Its title names the dependency and the versions. Its body links the pull
  request, which carries Dependabot's release notes, and gives the update type. A major update, or one whose versions
  can't be read, says it needs an OpenSpec change (#170 section 6) (design D4).
- **The release in progress** is the open milestone in `tofu/milestones.json` with the lowest version. It's found in
  the repository by its title. If it isn't there, the run opens no issue in that repository and fails, naming it
  (design D5).
- **A superseded update reuses its issue.** When Dependabot opens a pull request for a dependency whose issue is
  still open, the issue is relinked to the new pull request, retitled with the new versions, and gets a comment (design
  D3).
- **The closing line comes back.** If the description of an open Dependabot pull request loses its `Closes` line,
  the next run puts it back.
- **A Dependabot pull request closed without merging closes its issue as not planned**, with a comment saying why.
  This happens only when no open Dependabot pull request for the same dependency exists an hour after it closed, so a
  successor has time to appear. A reopened pull request reopens its issue (design D3).
- **It never runs or reads the pull request's code.** It checks out only infrastructure's `main`. It reads the
  pull requests' metadata through the API, and their descriptions only to look for its own closing line. It trusts
  only issues its own App opened, so an issue someone else writes can't capture a pull request (design D6).
- **A new App, `troupe-run-dependabot`**, with Issues and Pull requests write, installed on troupe, website and
  infrastructure. Its key is held in a new main-only environment, `dependabot-issues`, in infrastructure. The board
  card is added with the existing board App, as the schedule watch does (design D7). The owner creates the App and
  sets its key by hand.
- **Outside GitHub Actions the script only reads** and prints what it would do.
- `docs/development-workflow.md`'s "Dependabot pull requests" section says each pull request gets its issue, and
  what's left until #174.

Out of scope: the guard's exemption and the reserved branch prefix (#174); the closing-issue check itself (#173,
done); applying website #44, #45 and #46 (website#53 is parked for them, and they're this change's test cases).

## Capabilities

### New Capabilities

- `dependabot-issue-credentials`: the `troupe-run-dependabot` App, its narrow permissions and installation, the
  main-only environment that holds its key, and the variable that names it. This follows board-credentials and
  docs-build-credentials.

### Modified Capabilities

- `dependency-updates`: new requirements for the issue each Dependabot pull request gets: when it's opened and what it
  carries, the closing line, superseded and closed pull requests, the trusted inputs, and the read-only run outside
  Actions.

## Impact

- New: `.github/workflows/dependabot-issues.yml`, `scripts/dependabot_issues.py` and its tests, and fixtures of real
  Dependabot pull request payloads.
- `tofu/`: a new `dependabot_issues.tf` with the environment, its deployment policy and the client ID variable.
  `oob/app-installations.json` declares the App. `scripts/tests/test_main_only_environments.py` covers the environment.
- `oob/README.md`: how the owner creates the App and sets its key.
- `docs/development-workflow.md`: the Dependabot section.
- The first run opens an issue for each Dependabot pull request open at the time (18 on 2026-10-27), each on the board.
- Each open Dependabot pull request still fails `guard` on `commit-branch-change` until #174.
