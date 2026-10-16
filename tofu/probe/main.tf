# The drift probe (design D7): the same repository module and file resource as the live root,
# pointed at a throwaway repo, so the drift behaviours in the specs can be shown without
# touching a live one. Its state is git-ignored and deleted with the repo; it is encrypted the
# same way regardless.
#
# To run it again (task 6 in openspec/changes/archive/2026-10-11-adopt-org/tasks.md):
#   1. gh repo create troupe-run/<name> --public --add-readme, then add it to the App's installation;
#   2. save its README as README.probe.md here, and set probe_repo = "<name>" in terraform.tfvars;
#   3. from tofu/probe, with OP_ACCOUNT set: op run --env-file=../secrets.env -- tofu <init|plan|apply>;
#   4. delete the repo, then this directory's state, README.probe.md and terraform.tfvars.
#
# The guard-delivery probe (development-workflow, design D8) needs no README.probe.md: set
# probe_delivery = true to deliver the guard's script, workflow and list, plus probe-note.txt,
# whose content is var.probe_note, with the live delivery's commit messages.
#
# The ci-apply probe (design D8) switched identity between plan and apply: it planned with
# TF_VAR_github_app_id and TF_VAR_github_app_installation_id set to the read-only plan App's, and
# applied that plan with the write App's key and neither ID set. The plan App was deleted in
# required-checks (design D7); the variables stay for any App the same test needs.
#
# The required-checks probe (design D8) sets probe_main_ruleset and probe_required_checks.
# probe_description makes the change; probe_environments adds the D2 environments.
#
# The release-app probe (design D8) sets probe_release_ruleset, which adds the "release branches"
# ruleset of ../release.tf with this App standing in for the release App as its only bypass. Then
# probe_release_branch makes the App create release-please--probe, and probe_release_commit makes it
# commit to that branch; unsetting them makes it delete the file and the branch.
# drop-forgery-resistance (design D3) reruns it without the deletion rule, merging a pull request
# from the branch to show that delete-on-merge removes it.
#
# The website-pages probe (design D6) sets probe_pages, which imports the probe's Pages site,
# turned on beforehand with `gh api -X POST repos/troupe-run/<name>/pages -f build_type=workflow`,
# into a github_repository_pages deployed from Actions. Switching the site to a branch with
# `gh api -X PUT repos/troupe-run/<name>/pages -f build_type=legacy -f "source[branch]=main"` then
# shows as drift. It has no domain, so the module's `pages`, which needs one, isn't used: what's
# tested is the provider's drift detection.

terraform {
  required_version = ">= 1.8"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.13"
    }
  }

  encryption {
    key_provider "pbkdf2" "passphrase" {
      passphrase = var.state_passphrase
    }
    method "aes_gcm" "main" {
      keys = key_provider.pbkdf2.passphrase
    }
    state {
      method   = method.aes_gcm.main
      enforced = true
    }
    plan {
      method   = method.aes_gcm.main
      enforced = true
    }
  }
}

variable "state_passphrase" {
  type      = string
  sensitive = true
}

# Ephemeral, so a saved plan stores neither the key nor the identity it was made with, and the
# apply runs as whichever App it is given (ci-apply design D3). Null IDs mean the write App.
variable "github_app_pem" {
  type      = string
  sensitive = true
  ephemeral = true
}

variable "github_app_id" {
  type      = string
  default   = null
  ephemeral = true
}

variable "github_app_installation_id" {
  type      = string
  default   = null
  ephemeral = true
}

variable "probe_description" {
  description = "The probe repo's description, changed to make a plan with one change (ci-apply D8)."
  type        = string
  default     = "Throwaway: drift probe for troupe-run/infrastructure#2. Deleted after use."
}

variable "probe_main_ruleset" {
  description = "Passed to the module's main_ruleset: none lets a probe workflow be pushed to main."
  type        = string
  default     = "pull-request"
}

variable "probe_required_checks" {
  description = "Passed to the module's required_checks (required-checks design D8)."
  type = list(object({
    context        = string
    integration_id = number
  }))
  default = []
}

variable "probe_environments" {
  description = "Add the plan and apply environments of ci-apply design D2 to the probe."
  type        = bool
  default     = false
}

variable "probe_pages" {
  description = "Import and declare the probe's Pages site, deployed from Actions (website-pages design D6)."
  type        = bool
  default     = false
}

variable "probe_repo" {
  description = "The throwaway repo, e.g. infra-probe-20261011."
  type        = string
}

variable "probe_bypass" {
  description = "Passed to the module's owner_bypass: false shows the rules as they apply to everyone (D5 phase 1)."
  type        = bool
  default     = true
}

variable "probe_delivery" {
  description = "Deliver the guard's script, workflow and list to the probe (development-workflow D8)."
  type        = bool
  default     = false
}

variable "probe_delivery_bypass" {
  description = "Give the infrastructure App the delivery bypass on the probe's ruleset (design D5)."
  type        = bool
  default     = false
}

variable "probe_note" {
  description = "The content of probe-note.txt, changed between applies to test the commit message."
  type        = string
  default     = "first\n"
}

variable "probe_release_ruleset" {
  description = "Add the release branches ruleset of ../release.tf, with this App as its bypass (release-app D8)."
  type        = bool
  default     = false
}

variable "probe_release_branch" {
  description = "The App creates release-please--probe from main; false deletes it (release-app D8)."
  type        = bool
  default     = false
}

variable "probe_release_commit" {
  description = "The App commits probe-release.txt to release-please--probe (release-app D8)."
  type        = bool
  default     = false
}

variable "declared" {
  description = "Set to false to remove the repo's declaration (the prevent_destroy step)."
  type        = bool
  default     = true
}

provider "github" {
  owner = "troupe-run"

  app_auth {
    id              = coalesce(var.github_app_id, "5272634")
    installation_id = coalesce(var.github_app_installation_id, "170224209")
    pem_file        = var.github_app_pem
  }
}

module "probe" {
  source = "../modules/repository"
  count  = var.declared ? 1 : 0

  name            = var.probe_repo
  description     = var.probe_description
  labels          = jsondecode(file("${path.module}/../labels/github-defaults.json"))
  owner_bypass    = var.probe_bypass
  main_ruleset    = var.probe_main_ruleset
  required_checks = var.probe_required_checks

  app_bypass_id = var.probe_delivery_bypass ? 5272634 : null
}

resource "github_repository_file" "probe" {
  count = var.declared && fileexists("${path.module}/README.probe.md") ? 1 : 0

  repository          = var.probe_repo
  branch              = "main"
  file                = "README.md"
  content             = try(file("${path.module}/README.probe.md"), "")
  commit_message      = "chore: probe file"
  overwrite_on_create = false

  lifecycle {
    ignore_changes = [commit_message]
  }
}

locals {
  adopt        = var.declared ? toset(["probe"]) : toset([])
  adopt_readme = var.declared && fileexists("${path.module}/README.probe.md") ? toset(["probe"]) : toset([])

  # The same shape as the live delivery (../guard_delivery.tf): sources from this repository, the
  # list generated, and a message that changes exactly when the content does (design D3).
  probe_sources = var.probe_delivery ? {
    "scripts/guard.py"            = file("${path.module}/../../scripts/guard.py")
    ".github/workflows/guard.yml" = file("${path.module}/../../.github/workflows/guard.yml")
    "probe-note.txt"              = var.probe_note
  } : {}
  probe_list = var.probe_delivery ? {
    ".github/guard-delivery.json" = jsonencode({
      source = "troupe-run/infrastructure"
      files  = sort(concat(keys(local.probe_sources), [".github/guard-delivery.json"]))
    })
  } : {}
  probe_deliveries = merge(local.probe_sources, local.probe_list)
}

resource "github_repository_file" "delivery" {
  for_each = local.probe_deliveries

  repository          = var.probe_repo
  branch              = "main"
  file                = each.key
  content             = each.value
  commit_message      = "chore(guard): deliver ${each.key} ${substr(sha256(each.value), 0, 12)} from troupe-run/infrastructure"
  overwrite_on_create = false
}

import {
  for_each = local.adopt
  to       = module.probe[0].github_repository.this
  id       = var.probe_repo
}

import {
  for_each = local.adopt
  to       = module.probe[0].github_issue_labels.this
  id       = var.probe_repo
}

import {
  for_each = local.adopt_readme
  to       = github_repository_file.probe[0]
  id       = "${var.probe_repo}:README.md:"
}

# The environments of ci-apply design D2, on the probe.
resource "github_repository_environment" "plan" {
  count = var.probe_environments ? 1 : 0

  repository  = var.probe_repo
  environment = "plan"
}

resource "github_repository_environment" "apply" {
  count = var.probe_environments ? 1 : 0

  repository          = var.probe_repo
  environment         = "apply"
  can_admins_bypass   = false
  prevent_self_review = false

  reviewers {
    users = [160232611]
  }

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "apply_main" {
  count = var.probe_environments ? 1 : 0

  repository     = var.probe_repo
  environment    = github_repository_environment.apply[0].environment
  branch_pattern = "main"
}

# The "release branches" ruleset of ../release.tf (release-app design D7), with the infrastructure
# App as the only bypass in place of the release App, which isn't installed here (design D8). No
# deletion rule, so delete-on-merge removes the branch (drop-forgery-resistance design D2, D3).
resource "github_repository_ruleset" "release_branches" {
  count = var.probe_release_ruleset ? 1 : 0

  name        = "release branches"
  repository  = var.probe_repo
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
    actor_id    = 5272634
    bypass_mode = "always"
  }
}

resource "github_branch" "release" {
  count = var.probe_release_branch ? 1 : 0

  repository    = var.probe_repo
  branch        = "release-please--probe"
  source_branch = "main"
}

resource "github_repository_file" "release" {
  count = var.probe_release_branch && var.probe_release_commit ? 1 : 0

  repository          = var.probe_repo
  branch              = github_branch.release[0].branch
  file                = "probe-release.txt"
  content             = "written by the App\n"
  commit_message      = "chore: probe a commit by the App to a release branch"
  overwrite_on_create = false
}

# The website-pages probe (design D6): a Pages site deployed from Actions, with no domain.
resource "github_repository_pages" "probe" {
  count = var.probe_pages ? 1 : 0

  repository = var.probe_repo
  build_type = "workflow"
}

import {
  for_each = var.probe_pages ? toset([var.probe_repo]) : toset([])
  to       = github_repository_pages.probe[0]
  id       = each.key
}
