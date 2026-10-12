# The environments that gate CI's plans and applies on this repository (spec: ci-apply, design D2).
# Each holds the App's key, the state passphrase and the billing email, set by the owner from
# 1Password (README); OpenTofu never manages the values.
#
#   plan-pr    any branch   the owner approves each run   a pull request's plan
#   plan-main  main only    no approval                   the plan after a merge, and manual runs
#   apply      main only    the owner approves            the apply

locals {
  # The owner, the only required reviewer.
  owner_user_id = 160232611

  ci_environments = {
    "plan-pr"   = { approval = true, main_only = false }
    "plan-main" = { approval = false, main_only = true }
    "apply"     = { approval = true, main_only = true }
  }
}

resource "github_repository_environment" "ci" {
  for_each = local.ci_environments

  repository  = module.repo_infrastructure.name
  environment = each.key
  # No admin may skip the approval; the owner both merges and approves, so self-review is allowed.
  can_admins_bypass   = false
  prevent_self_review = false

  dynamic "reviewers" {
    for_each = each.value.approval ? [1] : []
    content {
      users = [local.owner_user_id]
    }
  }

  dynamic "deployment_branch_policy" {
    for_each = each.value.main_only ? [1] : []
    content {
      protected_branches     = false
      custom_branch_policies = true
    }
  }
}

resource "github_repository_environment_deployment_policy" "main_only" {
  for_each = { for name, env in local.ci_environments : name => env if env.main_only }

  repository     = module.repo_infrastructure.name
  environment    = github_repository_environment.ci[each.key].environment
  branch_pattern = "main"
}
