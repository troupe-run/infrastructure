# The environments this repo declares (spec: ci-apply, design D2; spec: repositories, #52).
#
# CI's, on this repository, gate its plans and applies. Each holds the App's key, the state
# passphrase and the billing email, set by the owner from 1Password (README); OpenTofu never
# manages the values.
#
#   plan-pr    any branch   the owner approves each run   a pull request's plan
#   plan-main  main only    no approval                   the plan after a merge, and manual runs
#   apply      main only    the owner approves            the apply
#
# The website's, which its deploy job publishes troupe.run through:
#
#   github-pages  main only  no approval  the website's deploy (deploy.yml)
#
# scripts/tests/test_main_only_environments.py fails if a main-only one stops being declared so.

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

# GitHub created it when Pages was set up; adopted by import (website-environment design D2).
# Only main may deploy troupe.run. No reviewers: the website's pull requests are reviewed before
# they merge, and every push to main that passes CI deploys (design D4).
resource "github_repository_environment" "github_pages" {
  repository  = module.repo_website.name
  environment = "github-pages"
  # GitHub's default was true, which lets admins bypass the branch rule, and agents share
  # the owner's admin login (#47), so no admin may bypass it, as for apply and release (design D3).
  can_admins_bypass   = false
  prevent_self_review = false

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }

  # A destroy would let the next deploy recreate it with no branch rule (design D5).
  # prevent_destroy refuses one only while this block exists: deleting the block deletes the
  # guard too, which scripts/tests/test_main_only_environments.py catches (#61). To stop managing
  # it, use a `removed` block, which leaves it on GitHub.
  lifecycle {
    prevent_destroy = true
  }
}

resource "github_repository_environment_deployment_policy" "github_pages_main_only" {
  repository     = module.repo_website.name
  environment    = github_repository_environment.github_pages.environment
  branch_pattern = "main"
}
