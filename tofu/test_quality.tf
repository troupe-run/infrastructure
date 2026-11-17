# What .github/workflows/mutation.yml needs to keep its test-quality issues in troupe, website and
# infrastructure (spec: mutation-issue-credentials; #325; lint-mutation design D4). GITHUB_TOKEN
# can't write the other repositories, so the issues job mints the troupe-run-test-quality App's
# token, which can write issues and nothing else. The App itself is created by hand and declared in
# oob/app-installations.json.

# Holds TEST_QUALITY_APP_PRIVATE_KEY, which the owner sets from 1Password (oob/README.md). Only a
# run on main may use it, and no admin may bypass that. No reviewers: the workflow runs weekly,
# unattended, and each write is an issue edit. Removing or weakening it fails
# scripts/tests/test_main_only_environments.py.
resource "github_repository_environment" "mutation_issues" {
  repository          = module.repo_infrastructure.name
  environment         = "mutation-issues"
  can_admins_bypass   = false
  prevent_self_review = false

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "mutation_issues_main_only" {
  repository     = module.repo_infrastructure.name
  environment    = github_repository_environment.mutation_issues.environment
  branch_pattern = "main"
}
