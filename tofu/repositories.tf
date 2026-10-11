# The org's repositories that aren't archived (spec: repositories). Archived bake-off and spike
# repos are deliberately left out (owner, 2026-10-11).

locals {
  github_default_labels = jsondecode(file("${path.module}/labels/github-defaults.json"))
}

module "repo_troupe" {
  source       = "./modules/repository"
  name         = "troupe"
  description  = "troupe: run your development process with agents and people in named roles"
  homepage_url = "https://troupe.run"
  # The cap:* labels are copied as they were on 2026-10-11; capability-labels replaces the copy
  # with troupe's capability list.
  labels = concat(local.github_default_labels, jsondecode(file("${path.module}/labels/troupe.json")))
  # troupe receives the guard from this repository (guard_delivery.tf).
  delivery_app_id = local.infrastructure_app_id
}

module "repo_github" {
  source = "./modules/repository"
  name   = ".github"
  # .github gets its own ruleset, letting only the App push, in required-checks.
  protect_main = false
  description  = "Org-wide defaults for troupe-run repositories: DCO config, contributing, security policy, org profile"
  labels       = local.github_default_labels
}

module "repo_infrastructure" {
  source       = "./modules/repository"
  name         = "infrastructure"
  homepage_url = "https://troupe.run"
  description  = "How the troupe-run org builds software: the org as code (OpenTofu), the development workflow and its guardrails"
  topics       = ["infrastructure-as-code", "openspec", "opentofu"]
  labels       = local.github_default_labels
}

# GitHub Pages (deployed from Actions) isn't declared yet: the provider treats `pages` as
# computed, so leaving it out shows no drift. See the Findings in design.md.
module "repo_website" {
  source      = "./modules/repository"
  name        = "troupe-run.github.io"
  description = "troupe.run \u2014 website and landing page"
  labels      = local.github_default_labels
}
