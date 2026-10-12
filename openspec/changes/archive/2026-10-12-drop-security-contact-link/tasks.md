# Tasks

## 1. The config and its test

- [x] 1.1 Remove `contact_links` from `org-profile/.github/ISSUE_TEMPLATE/config.yml`, keeping the source note and
  `blank_issues_enabled: true`. Add a test to `scripts/tests/test_org_profile.py`, named for what it checks: the
  chooser config has no contact link whose URL is the security policy, and a fixture `config.yml` with one fails with
  a message saying GitHub already shows that entry. Verify:
  - the new test fails against the old `config.yml` (run it once before removing the link), then passes;
  - `scripts/check.py` passes (ruff, `mypy --strict`, tests, `tofu validate`);
  - `uv run scripts/oob.py` reports no `.github` file missing or extra (content isn't compared by it).

## 2. Land it

- [x] 2.1 Open the pull request (`Closes #21`). Its evidence:
  - the CI plan comment, after the owner approves the run. It must show only
    `github_repository_file.org_profile[".github/ISSUE_TEMPLATE/config.yml"]` updated, with a new sync commit message,
    and nothing else;
  - the test output.

  Verify: every required check is green on all three OSes, and the plan comment matches.

## Workflow follow-up

- Archive on the branch before the merge (`/opsx:archive`), syncing the `development-workflow` delta.
- **After the owner merges and approves the apply:**
  - the sync commit in `troupe-run/.github` is named `chore: sync .github/ISSUE_TEMPLATE/config.yml <hash> from
    troupe-run/infrastructure`;
  - the owner checks a repository's issue chooser (`infrastructure`'s, read only): three forms, a blank issue, and one
    security entry. Note where GitHub's entry leads.
- Comment on #21 with the PR and the archived change.
