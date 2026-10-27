# What troupe's and website's .github/workflows/dependabot-dispatch.yml need to start
# infrastructure's dependabot-issues when Dependabot acts there (spec: dependabot-dispatch-credentials;
# #195). A run's GITHUB_TOKEN covers only its own repository, so the dispatcher mints the
# troupe-run-dispatch App's token, which can start a workflow_dispatch run on infrastructure and
# write nothing there (dependabot-issues-on-events design D2). The App itself is created by hand and
# declared in oob/app-installations.json. infrastructure needs neither: Dependabot's runs there start
# dependabot-issues directly (design D1).

locals {
  # Not a secret: it names the App, and minting a token also needs the key. The App's IDs are
  # recorded on #195.
  dispatch_app_client_id = "Iv23liCtu5ApjTXIvaA4"
}

# Holds DISPATCH_APP_PRIVATE_KEY, which the owner sets from 1Password (oob/README.md). Only a run on
# main may use it, and no admin may bypass that. A workflow_run runs on main, and a Dependabot pull
# request's own workflows can't reach it. No reviewers: it runs after every Dependabot run,
# unattended. Removing or weakening it fails scripts/tests/test_main_only_environments.py.
resource "github_repository_environment" "dependabot_dispatch_troupe" {
  repository          = module.repo_troupe.name
  environment         = "dependabot-dispatch"
  can_admins_bypass   = false
  prevent_self_review = false

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "dependabot_dispatch_troupe_main_only" {
  repository     = module.repo_troupe.name
  environment    = github_repository_environment.dependabot_dispatch_troupe.environment
  branch_pattern = "main"
}

# The infrastructure App writes it with "Variables: write", which it already has on troupe.
resource "github_actions_variable" "dispatch_app_client_id_troupe" {
  repository    = module.repo_troupe.name
  variable_name = "DISPATCH_APP_CLIENT_ID"
  value         = local.dispatch_app_client_id
}

# The same, on website. The owner sets DISPATCH_APP_PRIVATE_KEY here from the same 1Password item.
resource "github_repository_environment" "dependabot_dispatch_website" {
  repository          = module.repo_website.name
  environment         = "dependabot-dispatch"
  can_admins_bypass   = false
  prevent_self_review = false

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "dependabot_dispatch_website_main_only" {
  repository     = module.repo_website.name
  environment    = github_repository_environment.dependabot_dispatch_website.environment
  branch_pattern = "main"
}

resource "github_actions_variable" "dispatch_app_client_id_website" {
  repository    = module.repo_website.name
  variable_name = "DISPATCH_APP_CLIENT_ID"
  value         = local.dispatch_app_client_id
}
