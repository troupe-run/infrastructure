# What .github/workflows/auto-merge.yml needs to queue the pull requests that pass the safe-PR rule
# (spec: merge-credentials, auto-merge; #319, #320). The judge job mints the troupe-run-merge App's
# token, which can read the three governed repositories' pull requests, checks, issues, runs and
# variables, comment on and label pull requests, and add them to or take them out of the merge
# queue. Queueing needs contents write, which also lets it push a branch, but never main, a setting
# or a variable, and auto-merge never queues a push of its own (auto-merge design D10, D12). The App
# itself is created by hand and declared in oob/app-installations.json.

locals {
  # Not a secret: it names the App, and minting a token also needs the key. Created by the owner on
  # 2026-11-19 (App ID 5832075; design D10).
  merge_app_client_id = "Iv23liKUpo42H7OQcQ4g"

  # Each governed repository's switch (spec: auto-merge, "A repository variable switches it per
  # repository"): off, dry-run or on; unset reads as off. dry-run for a week first, then on in all
  # three at once by a later pull request (#319's rollout; design Migration Plan).
  auto_merge_switches = {
    troupe         = "dry-run"
    infrastructure = "dry-run"
    website        = "dry-run"
  }
}

# Holds MERGE_APP_PRIVATE_KEY, which the owner sets from 1Password (oob/README.md). Only a run on main
# may use it, and no admin may bypass that. No reviewers: the workflow runs every 15 minutes and on
# every pull request's checks, unattended. Removing or weakening it fails
# scripts/tests/test_main_only_environments.py.
resource "github_repository_environment" "auto_merge" {
  repository          = module.repo_infrastructure.name
  environment         = "auto-merge"
  can_admins_bypass   = false
  prevent_self_review = false

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "auto_merge_main_only" {
  repository     = module.repo_infrastructure.name
  environment    = github_repository_environment.auto_merge.environment
  branch_pattern = "main"
}

# The infrastructure App writes it with "Variables: write", which it already has on infrastructure.
resource "github_actions_variable" "merge_app_client_id" {
  repository    = module.repo_infrastructure.name
  variable_name = "MERGE_APP_CLIENT_ID"
  value         = local.merge_app_client_id
}

resource "github_actions_variable" "auto_merge" {
  for_each = local.auto_merge_switches

  repository    = each.key
  variable_name = "AUTO_MERGE"
  value         = each.value

  depends_on = [module.repo_troupe, module.repo_website, module.repo_infrastructure]
}
