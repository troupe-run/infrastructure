# Proposal

Issue: #21, a follow-up from `pr-templates` (#19, #20).

## Why

After #20 applied, the org's issue chooser shows two security entries side by side (seen on a throwaway repository,
2026-10-12):
- **"Report a security vulnerability"**, GitHub's own, shown because the org has a security policy (`SECURITY.md` in
  `troupe-run/.github`, published from `org-profile/SECURITY.md` here);
- **"Report a vulnerability"**, the `contact_links` entry `pr-templates` added to `config.yml`, because #15 asked for it.

Both lead to the same policy, so ours only duplicates GitHub's. #15 asked for the link before anyone had seen what
GitHub already shows.

## What Changes

- **`org-profile/.github/ISSUE_TEMPLATE/config.yml` loses `contact_links`.** It keeps the source note and
  `blank_issues_enabled: true`.
- **The `development-workflow` scenario "Vulnerability reports go to the security policy" changes.** The chooser
  offers one security entry, GitHub's own, which appears because the org publishes a security policy.
- **A test keeps the duplicate from coming back:** `config.yml` has no contact link to the security policy.
- **The apply makes one sync commit** to `troupe-run/.github`, for `config.yml`.

Decision: **rely on GitHub's entry rather than ours.** GitHub's entry ("Please review our security policy for more
details") points to the same policy ours does; where it leads is checked after the apply (tasks). GitHub's entry
depends on the security policy existing. That policy is published from this repository and checked for
drift, so it can't vanish unnoticed. The alternative, keeping our link and losing GitHub's, isn't possible: GitHub
shows its entry whenever a policy exists.

Out of scope:
- `SECURITY.md` itself, and private vulnerability reporting settings.
- Any other part of the forms or the PR template.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- **`development-workflow`:** "The workflow's templates are org defaults" changes its last scenario: one security
  entry, GitHub's, instead of our link.

## Impact

- **Changed:** `org-profile/.github/ISSUE_TEMPLATE/config.yml`, `scripts/tests/test_org_profile.py`.
- **Applied, after the owner approves the plan:** one file updated in `troupe-run/.github`. Nothing else.
- **Every repository using the org's forms** (`infrastructure`, `.github`, `website`, and troupe once troupe-run/troupe#48
  lands) shows one security entry instead of two.
