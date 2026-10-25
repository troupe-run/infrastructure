# Tasks

## 1. Confirm the labels on a probe repository

- [ ] 1.1 Run `uv run scripts/tofu.py plan` on the branch, fast-forwarded onto `origin/main`, and verify its only
      label changes are website's `dependencies` and `javascript` being deleted. If there's more, stop and report it
      on #138
- [ ] 1.2 Create `troupe-run/infra-probe-dependabot-labels` (public) holding the files in design D2: `pyproject.toml`
      and `uv.lock` with one dependency that has a known advisory and one that's only out of date, a
      `workflow_dispatch`-only workflow on an old major version of an action, and a `.github/dependabot.yml` for `uv`
      and `github-actions` version updates. Turn on Dependabot security updates. Verify with
      `gh api repos/troupe-run/infra-probe-dependabot-labels/automated-security-fixes` that they're enabled
- [ ] 1.3 Wait for Dependabot's pull requests: a uv security update, a uv version update and a GitHub Actions
      version update. Record each one's labels (`gh pr list --json number,title,labels`) and the repository's labels
      (`gh label list --json name,color,description`) in the PR description draft, and compare them with the
      source's values in design Context. If a pull request doesn't come within a day, record that and use the
      source's values for that ecosystem (design D2)
- [ ] 1.4 If the probe differs from design D1 or the spec delta's scenarios (a different name, colour or
      description, a separate name for security updates, or a `security` label), update design D1/D2 and the spec
      delta to the observed values before going on, and verify `openspec validate declare-dependabot-labels --strict`
      passes
- [ ] 1.5 Delete the probe repository and verify `gh repo view troupe-run/infra-probe-dependabot-labels` fails with
      not found

## 2. Declare the labels

- [ ] 2.1 In `scripts/tests/test_labels.py`, write the tests in design D4: every declared Dependabot label's
      description is within the limit, an over-limit one is named with its length, an undeclared ecosystem is named
      with its repository, and the file's repositories are exactly the `module "repo_*"` names in
      `tofu/repositories.tf`. Run them and verify they fail because `tofu/labels/dependabot.json` doesn't exist yet
- [ ] 2.2 Create `tofu/labels/dependabot.json` as in design D1, with the values from section 1, website's two
      matching `gh label list -R troupe-run/website` exactly. Verify 2.1's tests pass
- [ ] 2.3 In `tofu/repositories.tf`, build each repository's Dependabot labels from the file and add them to all
      four modules' `labels`, after the kinds of work, with a comment saying what the set is for and citing the spec
      and this change's design (D1, D3). Verify `tofu fmt` and `tofu validate` are clean and
      `uv run scripts/check.py` passes
- [ ] 2.4 Add `dependabot.json` to `README.md`'s row for `tofu/labels/`, saying it holds the labels Dependabot
      applies and each repository's ecosystems. Verify the row renders as one table row and `uv run scripts/check.py`
      passes

## 3. Verify

- [ ] 3.1 Run `uv run scripts/tofu.py plan` on the branch, fast-forwarded onto `origin/main`, and verify it shows no
      change to website's `dependencies` or `javascript`, `github_actions` created on website, `dependencies`,
      `python:uv` and `github_actions` created on troupe and infrastructure (or the names section 1 settled on), and
      nothing else created, changed or deleted. Keep its output for the pull request
- [ ] 3.2 Run `openspec validate declare-dependabot-labels --strict` and verify it passes

## Workflow follow-up

- Open the pull request with `Closes #138`, the plan from 3.1 and the probe's findings from 1.3. The owner approves
  the `plan-pr` run. Batch the archive with the last tick before asking for approval, since each push re-asks it.
- Archive the change on the branch before merging; the owner merges by rebase.
- After the merge, the owner reads the `plan (main)` plan in the `tofu` workflow and approves the `apply` job. Verify
  with `gh label list -R troupe-run/<repo>` for troupe, infrastructure and website, and check that website#44, #45
  and #46 still carry `dependencies` and `javascript`.
- Check #138 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #138 with the pull request, the archived change and the probe's findings.
- Delete the change's worktree and branch once it's merged and verified.
