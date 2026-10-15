# What troupe's release workflow needs from the org (spec: release-credentials; troupe-run/troupe#23).
# It opens release pull requests with the troupe-run-release App's token, because one opened with
# GITHUB_TOKEN starts no workflows. The App itself is created by hand and declared in
# oob/app-installations.json: the provider can't read an installation as an App (design D1).

locals {
  # Not a secret: it names the App, and minting a token also needs the key (design D3). The App's
  # IDs are recorded on #34.
  release_app_client_id = "Iv23liPmD0ygDtxCbwVX"
  release_app_id        = 5300488
}

# Holds RELEASE_APP_PRIVATE_KEY, which the owner sets from 1Password (oob/README.md). Only a run on
# main may use it, and no admin may bypass that. No reviewers: it runs on every push to main, and
# the release pull request is reviewed before it merges (design D2).
resource "github_repository_environment" "release" {
  repository          = module.repo_troupe.name
  environment         = "release"
  can_admins_bypass   = false
  prevent_self_review = false

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "release_main_only" {
  repository     = module.repo_troupe.name
  environment    = github_repository_environment.release.environment
  branch_pattern = "main"
}

# The infrastructure App writes it with "Variables: write" (owner, 2026-10-13, design D3).
resource "github_actions_variable" "release_app_client_id" {
  repository    = module.repo_troupe.name
  variable_name = "RELEASE_APP_CLIENT_ID"
  value         = local.release_app_client_id
}

# Only the release App creates or updates a release-please branch, so on troupe the branch's name is
# proof of who wrote it, and the guard exempts it by that name (drop-forgery-resistance design D1,
# D2). No non_fast_forward rule, because release-please force-pushes its branch, and no owner
# bypass; the break-glass is editing the ruleset on GitHub. No deletion rule, so GitHub's
# delete-on-merge removes the branch once its pull request merges; only the App can create it again
# (probed: drop-forgery-resistance design D3).
resource "github_repository_ruleset" "release_branches" {
  name        = "release branches"
  repository  = module.repo_troupe.name
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["refs/heads/release-please--*"]
      exclude = []
    }
  }

  rules {
    creation                      = true
    update                        = true
    update_allows_fetch_and_merge = false
  }

  bypass_actors {
    actor_type  = "Integration"
    actor_id    = local.release_app_id
    bypass_mode = "always"
  }
}
