# What the org's workflows need to start the website's build (spec: docs-build-credentials): troupe's
# release workflow, on every push to its main (#109, troupe-run/troupe#120), and infrastructure's
# milestones notice, when tofu/milestones.json changes on main (#124, spec: milestones). A run's
# GITHUB_TOKEN covers only its own repository, so the job that notifies the website mints the
# troupe-run-docs App's token, which can start a workflow_dispatch run on website and write nothing
# there (docs-build-trigger design D2). The App itself is created by hand and declared in
# oob/app-installations.json. The website's side, and troupe's sending step, are
# troupe-run/website#23's (design D4). Both repositories get the same environment and variable
# (rebuild-site-on-milestones design D1).

locals {
  # Not a secret: it names the App, and minting a token also needs the key. The App's IDs are
  # recorded on #109.
  docs_app_client_id = "Iv23lir5BQmFPhN7GdAP"
}

# Holds DOCS_APP_PRIVATE_KEY, which the owner sets from 1Password (oob/README.md). Only a run on
# main may use it, and no admin may bypass that. A new troupe-v* tag is announced from the release
# workflow's run on main, so no tag needs the key (design D3). No reviewers: it runs on every push to
# main, unattended. Separate from release, so neither job can read the other's key. Removing or
# weakening it fails scripts/tests/test_main_only_environments.py.
resource "github_repository_environment" "docs" {
  repository          = module.repo_troupe.name
  environment         = "docs"
  can_admins_bypass   = false
  prevent_self_review = false

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "docs_main_only" {
  repository     = module.repo_troupe.name
  environment    = github_repository_environment.docs.environment
  branch_pattern = "main"
}

# The infrastructure App writes it with "Variables: write", which it already has on troupe.
resource "github_actions_variable" "docs_app_client_id" {
  repository    = module.repo_troupe.name
  variable_name = "DOCS_APP_CLIENT_ID"
  value         = local.docs_app_client_id
}

# The same, on infrastructure, for the milestones notice (.github/workflows/milestones-notice.yml;
# rebuild-site-on-milestones design D1, D3). The owner sets DOCS_APP_PRIVATE_KEY here from the same
# 1Password item (oob/README.md).
resource "github_repository_environment" "docs_infrastructure" {
  repository          = module.repo_infrastructure.name
  environment         = "docs"
  can_admins_bypass   = false
  prevent_self_review = false

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "docs_infrastructure_main_only" {
  repository     = module.repo_infrastructure.name
  environment    = github_repository_environment.docs_infrastructure.environment
  branch_pattern = "main"
}

resource "github_actions_variable" "docs_app_client_id_infrastructure" {
  repository    = module.repo_infrastructure.name
  variable_name = "DOCS_APP_CLIENT_ID"
  value         = local.docs_app_client_id
}
