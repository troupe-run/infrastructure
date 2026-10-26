# Proposal

Issue: #173, section 5 of #170.

## Why

The owner wants every pull request checked, consistently, for closing an issue (2026-10-26, #170 section 5, option
(b)). Today only the local `pr-closes-issue` rule checks it, and only for an agent's `gh pr create`. A pull request
opened in GitHub's UI, by a bot, or by a session whose hooks didn't run, isn't checked at all. The `guard` GitHub check
already re-runs on every pull request, and on `edited`, so it can hold every pull request to the same rule.

## What Changes

- **The `guard` GitHub check refuses a pull request whose description closes no issue**, in every governed repository
  (troupe, infrastructure, website). It reads the description from the event payload, as it reads the title today,
  and uses the same `CLOSING` pattern as the local rule: `Closes`, `Fixes` or `Resolves` (and their other forms),
  followed by `#n`, `owner/repo#n` or an issue URL, so closing an issue in another repository passes. The refusal is
  under `pr-closes-issue`, names the pull request, and says how to edit its description (design D1, D2).
- **An empty description fails the same way.** GitHub sends `null` for one. A payload whose `body` is missing, or isn't
  a string or `null`, is malformed: the check fails saying it couldn't read the description, as it does for an
  unreadable title (design D3).
- **release-please's pull request is exempt**, on the same terms as its branch exemption: a `release-please--` branch
  in a repository whose ruleset reserves the name (troupe). Elsewhere, or from a fork, it isn't (design D4).
- **Editing the description re-runs the check.** `guard.yml` already runs on `edited`; its header comment and the docs
  say the description is checked too.
- **Pushes aren't pull requests**, so a push (to `main` or any branch) checks no description, as it checks no title.
- **Before delivery, the open pull requests are listed** in each governed repository, and any without a closing line
  is fixed, so none goes red unexpectedly. On 2026-10-26 those are troupe #89 (release-please, exempt) and website
  #44, #45 and #46 (Dependabot, already red on `commit-branch-change`; #170 section 7 decides their fate) (design D5).
- `docs/development-workflow.md`: the `guard` check's row and `pr-closes-issue`'s row say the rule also runs on
  GitHub, for every pull request, and the "Dependabot pull requests" section says their pull requests close no issue
  either.

Out of scope: Dependabot's exemption and the workflow that gives its pull requests an issue (#170 sections 2-4);
whether a closing line actually closes anything, which GitHub decides (it does only for a pull request into the default
branch, design Non-Goals).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: a new requirement that the GitHub check refuses a pull request whose description closes no
  issue, with release-please's exempt and an unreadable description failing.

## Impact

- `scripts/guard.py`: `github_ci_inputs` reads the body, `run_ci`/`run_ci_entry` check it, a new unreadable-body
  error. Delivered, so troupe and website receive it after the owner approves the delivery plan.
- `.github/workflows/guard.yml`: header comment only. Also delivered.
- `scripts/tests/`: the CI-entry tests' pull request payloads gain a `body`; new tests for each scenario.
- `docs/development-workflow.md`: two table rows and the Dependabot section.
- Every open pull request in troupe, infrastructure and website without a closing line goes red once delivered.
