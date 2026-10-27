# What .github/workflows/dependabot-issues.yml needs to give every Dependabot pull request its issue
# and link the pull request to it (spec: dependabot-issue-credentials; #172). GITHUB_TOKEN can't
# write other repositories, and its edits start no workflow, so adding the closing line wouldn't
# re-run guard. So the issues job mints the troupe-run-dependabot App's token, which can write
# issues and pull requests' descriptions in troupe, website and infrastructure, and can't push or
# merge (dependabot-issues design D1, D7). The App itself is created by hand and declared in
# oob/app-installations.json.

locals {
  # Not a secret: it names the App, and minting a token also needs the key. The App's IDs are
  # recorded on #172.
  dependabot_app_client_id = "Iv23lip7KZ08OFBhsLuQ"
}

# Holds DEPENDABOT_APP_PRIVATE_KEY, which the owner sets from 1Password (oob/README.md). Only a run
# on main may use it, and no admin may bypass that. No reviewers: the workflow runs after each
# Dependabot run and daily, unattended, and each write is reversible (design D7). Removing or
# weakening it fails scripts/tests/test_main_only_environments.py.
resource "github_repository_environment" "dependabot_issues" {
  repository          = module.repo_infrastructure.name
  environment         = "dependabot-issues"
  can_admins_bypass   = false
  prevent_self_review = false

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "dependabot_issues_main_only" {
  repository     = module.repo_infrastructure.name
  environment    = github_repository_environment.dependabot_issues.environment
  branch_pattern = "main"
}

# The infrastructure App writes it with "Variables: write", which it already has on infrastructure.
resource "github_actions_variable" "dependabot_app_client_id" {
  repository    = module.repo_infrastructure.name
  variable_name = "DEPENDABOT_APP_CLIENT_ID"
  value         = local.dependabot_app_client_id
}
