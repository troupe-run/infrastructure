# The org's repositories that aren't archived (spec: repositories). Archived bake-off and spike
# repos are deliberately left out (owner, 2026-10-11).

locals {
  github_default_labels = jsondecode(file("${path.module}/labels/github-defaults.json"))

  # The labels the workflow itself uses, such as needs:owner, which the Decision form applies. Every
  # repository gets them, so the org's issue forms work in each (spec: labels; pr-templates D3).
  workflow_labels = jsondecode(file("${path.module}/labels/workflow.json"))

  # Kinds of work GitHub's default labels don't cover, such as speed, so a capability label never
  # stands in for one. Every repository gets them (spec: labels; label-troupe-specs D4).
  kind_labels = jsondecode(file("${path.module}/labels/kinds.json"))

  # The labels Dependabot applies: dependencies, and one for each ecosystem a repository's
  # dependency graph lists. Dependabot finds a label by name, so it uses these rather than creating
  # its own, which the next apply would delete. A repository with no ecosystem gets none of them,
  # not even dependencies (spec: labels; declare-dependabot-labels D1, D3).
  dependabot = jsondecode(file("${path.module}/labels/dependabot.json"))
  dependabot_labels = {
    for repo, ecosystems in local.dependabot.repositories : repo => concat(
      length(ecosystems) > 0 ? [local.dependabot.dependencies] : [],
      [for ecosystem in ecosystems : local.dependabot.ecosystems[ecosystem]],
    )
  }

  # How troupe is described: the org's description and troupe's repository description are the
  # tagline then the sentence. The org profile is held to the same file by a test, and website's
  # brand guide is the reference across repositories, which troupe's README and the website follow
  # (spec: descriptions; align-troupe-descriptions design D1 to D3).
  descriptions = jsondecode(file("${path.module}/descriptions.json"))
  one_line     = "${local.descriptions.tagline} ${local.descriptions.sentence}"

  # The checks each repository's pull requests need before they merge (spec: rulesets), named
  # as GitHub reports them. infrastructure's are tested against its workflows
  # (scripts/tests/test_required_checks.py); website's were read from its latest merged pull
  # request on 2026-10-12 (required-checks design D1), and troupe's `check`, which reports for
  # its OS and Python legs, from troupe#117 on 2026-10-19 (require-troupe-check). Each repository
  # receiving the guard requires its `guard` check, which is tested too. website requires no DCO:
  # it takes no sign-off (owner, 2026-10-16; govern-website D3).
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
  description  = local.one_line
  homepage_url = "https://troupe.run"
  topics       = ["ai-agents", "developer-tools", "human-in-the-loop", "python", "workflow"]
  # troupe.json is troupe's capability labels, declared here and changed by pull request: troupe
  # keeps no separate list (spec: labels; owner, 2026-10-12, #22). release.json is release-please's
  # two labels, which it finds its release pull request by (release-app design D5).
  labels = concat(
    local.github_default_labels,
    local.workflow_labels,
    local.kind_labels,
    local.dependabot_labels["troupe"],
    jsondecode(file("${path.module}/labels/troupe.json")),
    jsondecode(file("${path.module}/labels/release.json")),
  )
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
  labels = concat(
    local.github_default_labels,
    local.workflow_labels,
    local.kind_labels,
    local.dependabot_labels[".github"],
  )
}

module "repo_infrastructure" {
  source       = "./modules/repository"
  name         = "infrastructure"
  homepage_url = "https://troupe.run"
  description  = "How the troupe-run org builds software: the org as code (OpenTofu), the development workflow and its guardrails"
  topics       = ["infrastructure-as-code", "openspec", "opentofu"]
  labels = concat(
    local.github_default_labels,
    local.workflow_labels,
    local.kind_labels,
    local.dependabot_labels["infrastructure"],
  )
  # CI commits the state here after an apply (spec: ci-apply, design D4).
  app_bypass_id   = local.infrastructure_app_id
  required_checks = local.checks_for["infrastructure"]
  # Every check it requires runs on merge groups (scripts/tests/test_required_checks.py);
  # website and troupe follow once theirs do (#197; spec: rulesets, merge-queue design D7).
  merge_queue = true
}

module "repo_website" {
  source      = "./modules/repository"
  name        = "website"
  description = "The troupe.run website and landing page"
  topics      = ["astro", "website"]
  # Set by the owner on GitHub after rename-website, and declared here (required-checks).
  homepage_url = "https://troupe.run/"
  labels = concat(
    local.github_default_labels,
    local.workflow_labels,
    local.kind_labels,
    local.dependabot_labels["website"],
  )
  # The org's roadmap (project 1) is linked here too, and turning projects off would hide it from
  # the repository (govern-website D4).
  has_projects = true
  # website receives the guard from this repository (guard_delivery.tf; govern-website).
  app_bypass_id   = local.infrastructure_app_id
  required_checks = local.checks_for["website"]
  # https://troupe.run, deployed from Actions (spec: repositories; website-pages). If the domain is
  # removed by hand, GitHub drops HTTPS and the certificate with it: the first apply restores the
  # domain and fails on HTTPS ("The certificate does not exist yet"), and a second, once GitHub has
  # approved the new certificate, enforces it.
  pages = { cname = "troupe.run" }
}
