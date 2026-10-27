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
# The manage-dns-as-code probe (design D7) sets probe_dns, with declared = false and any
# probe_repo, so it needs no throwaway repository. It creates one record of each new shape under
# infra-probe.troupe.run, a name nothing reads, in the live troupe.run zone, plus the live root's two
# check blocks, the undeclared one narrowed to that name and read one type at a time. Apply with no
# types read, so the apply never reads the list:
#   op run --env-file=../secrets.env -- tofu apply -var probe_dns=true -var declared=false \
#     -var probe_repo=none
# then plan again, which must be clean, and plan with -var 'probe_dns_read=["CAA"]' and the other
# types. To test the undeclared check, add a record under infra-probe.troupe.run outside OpenTofu
# (the API, with the same token), plan, and delete it. Clean up with `tofu destroy` and the same
# variables, then delete this directory's state.
#
# The website-pages probe (design D6) sets probe_pages, which imports the probe's Pages site,
# turned on beforehand with `gh api -X POST repos/troupe-run/<name>/pages -f build_type=workflow`,
# into a github_repository_pages deployed from Actions. Switching the site to a branch with
# `gh api -X PUT repos/troupe-run/<name>/pages -f build_type=legacy -f "source[branch]=main"` then
# shows as drift. It has no domain, so the module's `pages`, which needs one, isn't used: what's
# tested is the provider's drift detection.
#
# The deleted-block probe (correct-prevent-destroy-claim, design D1) shows what declared = false
# can't: deleting a module call deletes its prevent_destroy too. After the import apply, delete
# `module "probe"` and the two `import` blocks that target it, in the working tree only, then plan
# and apply: the repository is archived and its labels, ruleset and Dependabot settings are
# destroyed. To recover, `gh repo unarchive`, `git checkout` this file and apply again.
#
# The merge-queue probe (merge-queue design D1) sets probe_merge_queue, with probe_delivery_bypass
# and probe_required_checks naming `probe check` and `probe skipped` (GitHub Actions, 15368) and
# `DCO` (1861). Before the apply, push two workflows to the probe's main (no ruleset yet): probe.yml,
# on pull_request and merge_group, with job `probe check` (fails when a file FAIL exists) and job
# `probe skipped` (`if: github.event_name == 'pull_request'`); and push.yml, on push to "**",
# echoing the ref. The owner adds the probe to the infrastructure App's and the DCO App's
# installations. Queue signed-off pull requests, and read each merge group's check runs; change
# README.probe.md and apply to push to main as the App.

terraform {
  required_version = ">= 1.8"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.13"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.28"
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

# Ephemeral, as in ../versions.tf: a saved plan records no ephemeral variable.
variable "state_passphrase" {
  type      = string
  sensitive = true
  ephemeral = true
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

variable "probe_merge_queue" {
  description = "Passed to the module's merge_queue (merge-queue design D1)."
  type        = bool
  default     = false
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
  merge_queue     = var.probe_merge_queue

  app_bypass_id = var.probe_delivery_bypass ? 5272634 : null
}

resource "github_repository_file" "probe" {
  count = var.declared && fileexists("${path.module}/README.probe.md") ? 1 : 0

  repository          = var.probe_repo
  branch              = "main"
  file                = "README.md"
  content             = sensitive(try(file("${path.module}/README.probe.md"), ""))
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
  content             = sensitive(each.value)
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
  content             = sensitive("written by the App\n")
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

# The manage-dns-as-code probe (design D7): the live dns.tf's record shapes and checks, under a name
# nothing reads.
variable "probe_dns" {
  description = "Create the DNS probe's records under infra-probe.troupe.run (manage-dns-as-code D7)."
  type        = bool
  default     = false
}

variable "cloudflare_api_token" {
  description = "The DNS token, as in ../providers.tf. Never committed, never saved in a plan."
  type        = string
  sensitive   = true
  ephemeral   = true
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

locals {
  probe_dns_name = "infra-probe.troupe.run"
  probe_dns_records = var.probe_dns ? {
    "txt"           = { name = local.probe_dns_name, type = "TXT", content = "\"v=spf1 -all\"" }
    "mx-null"       = { name = local.probe_dns_name, type = "MX", content = ".", priority = 0 }
    "caa-issue"     = { name = local.probe_dns_name, type = "CAA", flags = 0, tag = "issue", value = "letsencrypt.org" }
    "caa-issuewild" = { name = local.probe_dns_name, type = "CAA", flags = 0, tag = "issuewild", value = ";" }
    "cname"         = { name = "www.${local.probe_dns_name}", type = "CNAME", content = "troupe-run.github.io" }
  } : {}
}

data "cloudflare_zone" "probe" {
  count = var.probe_dns ? 1 : 0

  filter = {
    name = "troupe.run"
  }
}

resource "cloudflare_dns_record" "probe" {
  for_each = local.probe_dns_records

  zone_id  = data.cloudflare_zone.probe[0].id
  name     = each.value.name
  type     = each.value.type
  ttl      = 1
  proxied  = false
  content  = each.value.type == "CAA" ? null : each.value.content
  priority = try(each.value.priority, null)
  data = each.value.type == "CAA" ? {
    flags = each.value.flags
    tag   = each.value.tag
    value = each.value.value
  } : null
}

# One read per record type: a single cloudflare_dns_records list holding CAA and other types
# panics OpenTofu (the first probe run, 2026-10-17). probe_dns_read names the types to read, so an
# apply with none read can't reach the panic.
variable "probe_dns_read" {
  description = "Record types to read under infra-probe.troupe.run, one data source each."
  type        = list(string)
  default     = []
}

data "cloudflare_dns_records" "probe" {
  for_each = var.probe_dns ? toset(var.probe_dns_read) : toset([])

  zone_id   = data.cloudflare_zone.probe[0].id
  type      = each.key
  max_items = 1000
  name = {
    endswith = local.probe_dns_name
  }
}

check "probe_undeclared_records" {
  assert {
    condition = length([
      for record in flatten([for read in data.cloudflare_dns_records.probe : read.result]) : record
      if !contains([for declared in cloudflare_dns_record.probe : declared.id], record.id)
    ]) == 0
    error_message = "Records under ${local.probe_dns_name} that the probe doesn't declare: ${join(", ", [
      for record in flatten([for read in data.cloudflare_dns_records.probe : read.result]) : "${record.name} ${record.type} ${record.content}"
      if !contains([for declared in cloudflare_dns_record.probe : declared.id], record.id)
    ])}."
  }
}

check "probe_zone_active" {
  assert {
    condition     = !var.probe_dns || try(data.cloudflare_zone.probe[0].status, "") == "active"
    error_message = "The troupe.run zone is ${try(data.cloudflare_zone.probe[0].status, "unread")}, not active."
  }
}

# The first probe's shape: one read of the whole zone, every type in one list. Set to test whether
# it still panics with CAA records in the zone (cloudflare/terraform-provider-cloudflare#7004).
variable "probe_dns_read_all" {
  description = "Read every record under infra-probe.troupe.run in one data source."
  type        = bool
  default     = false
}

data "cloudflare_dns_records" "probe_all" {
  count = var.probe_dns && var.probe_dns_read_all ? 1 : 0

  zone_id   = data.cloudflare_zone.probe[0].id
  max_items = 1000
  name = {
    endswith = local.probe_dns_name
  }
}

output "probe_all_count" {
  value = length(try(data.cloudflare_dns_records.probe_all[0].result, []))
}

# The milestone-interim-titles probe (design D6): the live milestones.tf's resource and title
# expression, on the probe repository. The expression is a copy, kept in step by hand: change both
# together. The milestones are JSON, decoded as the live file is, so a milestone without
# interim_title takes the same path. Run with declared = false, so only milestones are managed:
#   -var declared=false -var probe_repo=infra-probe-milestones -var 'probe_milestones=[
#     {"key":"a","title":"0.2.0"},{"key":"b","title":"0.3.0"},{"key":"c","title":"0.4.0"}]'
# then rotate the titles, without and then with interim_title, and plan and apply each step.
variable "probe_milestones" {
  description = "The probe's milestones as JSON, as milestones.json declares them (milestone-interim-titles D6)."
  type        = string
  default     = "[]"
}

locals {
  probe_milestones = { for milestone in jsondecode(var.probe_milestones) : milestone.key => milestone }
}

resource "github_repository_milestone" "probe" {
  for_each = local.probe_milestones

  owner      = "troupe-run"
  repository = var.probe_repo
  title      = try(each.value.interim_title, each.value.title)
  state      = "open"
}
