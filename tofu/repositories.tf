# The org's repositories that aren't archived (spec: repositories). Archived bake-off and spike
# repos are deliberately left out (owner, 2026-10-11).

locals {
  github_default_labels = jsondecode(file("${path.module}/labels/github-defaults.json"))

  # The checks each repository's pull requests need before they merge (spec: rulesets), named
  # as GitHub reports them. infrastructure's are tested against its workflows
  # (scripts/tests/test_required_checks.py); troupe's and website's were read from their latest
  # merged pull requests on 2026-10-12 (required-checks design D1).
  required_checks = jsondecode(file("${path.module}/required-checks.json"))

  # The App that posts each check, so a status of the same name from anything else doesn't count.
  check_apps = {
    "github-actions" = 15368
    "dco"            = 1861
  }

  checks_for = {
    for repo, checks in local.required_checks : repo => [
      for check in checks : { context = check.context, integration_id = local.check_apps[check.app] }
    ]
  }
}

module "repo_troupe" {
  source       = "./modules/repository"
  name         = "troupe"
  description  = "troupe: run your development process with agents and people in named roles"
  homepage_url = "https://troupe.run"
  # The cap:* labels are copied as they were on 2026-10-11; capability-labels replaces the copy
  # with troupe's capability list.
  labels = concat(local.github_default_labels, jsondecode(file("${path.module}/labels/troupe.json")))
  # The org's roadmap (project 1) is linked here, and turning projects off would hide it from the
  # repository (required-checks design D8, finding 8).
  has_projects = true
  # troupe receives the guard from this repository (guard_delivery.tf).
  app_bypass_id   = local.infrastructure_app_id
  required_checks = local.checks_for["troupe"]
}

module "repo_github" {
  source = "./modules/repository"
  name   = ".github"
  # Only the App changes main: its files are written from org-profile/ here (spec: rulesets,
  # org-profile; required-checks design D4).
  main_ruleset  = "app-only"
  app_bypass_id = local.infrastructure_app_id
  description   = "Org-wide defaults for troupe-run repositories: DCO config, contributing, security policy, org profile"
  labels        = local.github_default_labels
}

module "repo_infrastructure" {
  source       = "./modules/repository"
  name         = "infrastructure"
  homepage_url = "https://troupe.run"
  description  = "How the troupe-run org builds software: the org as code (OpenTofu), the development workflow and its guardrails"
  topics       = ["infrastructure-as-code", "openspec", "opentofu"]
  labels       = local.github_default_labels
  # CI commits the state here after an apply (spec: ci-apply, design D4).
  app_bypass_id   = local.infrastructure_app_id
  required_checks = local.checks_for["infrastructure"]
}

# GitHub Pages (deployed from Actions) isn't declared yet: the provider treats `pages` as
# computed, so leaving it out shows no drift. See the Findings in design.md.
module "repo_website" {
  source      = "./modules/repository"
  name        = "website"
  description = "troupe.run \u2014 website and landing page"
  # Set by the owner on GitHub after rename-website, and declared here (required-checks).
  homepage_url    = "https://troupe.run/"
  labels          = local.github_default_labels
  required_checks = local.checks_for["website"]
}
