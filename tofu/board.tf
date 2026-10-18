# What website's weekly link check needs from the org to put its "Broken external links" issue on
# the troupe roadmap board (spec: board-credentials; #59). It opens the issue with GITHUB_TOKEN, which
# can't write an org project, so a separate job adds it with the troupe-run-board App's token. The
# App itself is created by hand and declared in oob/app-installations.json (design D1, D4).

locals {
  # Not a secret: it names the App, and minting a token also needs the key. The App's IDs are
  # recorded on #59.
  board_app_client_id = "Iv23li9xJEOLGSyYlU5G"
}

# Holds BOARD_APP_PRIVATE_KEY, which the owner sets from 1Password (oob/README.md). Only a run on
# main may use it, and no admin may bypass that. No reviewers: the check is scheduled and
# unattended, and adding an item to the board is reversible (design D2). Removing or weakening it
# fails scripts/tests/test_main_only_environments.py (design D3).
resource "github_repository_environment" "board" {
  repository          = module.repo_website.name
  environment         = "board"
  can_admins_bypass   = false
  prevent_self_review = false

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "board_main_only" {
  repository     = module.repo_website.name
  environment    = github_repository_environment.board.environment
  branch_pattern = "main"
}

# The infrastructure App writes it with "Variables: write", which it already has on website.
resource "github_actions_variable" "board_app_client_id" {
  repository    = module.repo_website.name
  variable_name = "BOARD_APP_CLIENT_ID"
  value         = local.board_app_client_id
}
