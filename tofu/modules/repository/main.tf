# One managed repository: its settings and its labels (specs: repositories, labels).

terraform {
  required_providers {
    github = {
      source = "integrations/github"
    }
  }
}

resource "github_repository" "this" {
  name         = var.name
  description  = var.description
  homepage_url = var.homepage_url
  topics       = var.topics
  visibility   = "public"

  has_issues      = true
  has_discussions = false
  has_wiki        = var.has_wiki
  has_projects    = var.has_projects
  allow_forking   = true
  is_template     = false

  allow_merge_commit          = var.allow_merge_commit
  allow_squash_merge          = var.allow_squash_merge
  allow_rebase_merge          = var.allow_rebase_merge
  allow_auto_merge            = false
  allow_update_branch         = false
  delete_branch_on_merge      = var.delete_branch_on_merge
  merge_commit_title          = "MERGE_MESSAGE"
  merge_commit_message        = "PR_TITLE"
  squash_merge_commit_title   = "COMMIT_OR_PR_TITLE"
  squash_merge_commit_message = "COMMIT_MESSAGES"
  web_commit_signoff_required = false

  # Every managed repository is public, so these are free, and none may turn them off
  # (spec: repositories; security-scanning design D2).
  security_and_analysis {
    secret_scanning {
      status = "enabled"
    }
    secret_scanning_push_protection {
      status = "enabled"
    }
  }

  # An apply never deletes a repository (spec: repositories). prevent_destroy fails the plan;
  # archive_on_destroy is the backstop if someone lifts it. To stop managing a repo, use a
  # `removed` block with `destroy = false` (see README.md).
  archive_on_destroy = true

  lifecycle {
    prevent_destroy = true
  }
}

# The Pages site, when var.pages is set (spec: repositories; website-pages design D1 to D3). Built
# from Actions, so it has no source: the provider refuses one with "workflow", and ignores the
# branch the API still reports. Destroying it disables Pages and takes the site down, so, like the
# repository, it can't be destroyed: to stop managing it, use a `removed` block (README.md).
resource "github_repository_pages" "this" {
  count = var.pages == null ? 0 : 1

  repository     = github_repository.this.name
  build_type     = "workflow"
  cname          = var.pages.cname
  https_enforced = var.pages.https_enforced

  lifecycle {
    prevent_destroy = true
  }
}

# Dependabot alerts, and the security updates that answer them (spec: repositories;
# security-scanning design D1). Separate resources, because github_repository's
# vulnerability_alerts is deprecated. Destroying either one turns its feature off, so they can't be
# destroyed. Deleting a resource block gets past prevent_destroy, so don't: removing a whole
# repository with a `removed` block forgets them safely.
resource "github_repository_vulnerability_alerts" "this" {
  repository = github_repository.this.name
  enabled    = true

  lifecycle {
    prevent_destroy = true
  }
}

# GitHub turns security updates on only once alerts are on.
resource "github_repository_dependabot_security_updates" "this" {
  repository = github_repository.this.name
  enabled    = true

  depends_on = [github_repository_vulnerability_alerts.this]

  lifecycle {
    prevent_destroy = true
  }
}

resource "github_issue_labels" "this" {
  repository = github_repository.this.name

  dynamic "label" {
    for_each = { for l in var.labels : l.name => l }
    content {
      name        = label.value.name
      color       = label.value.color
      description = label.value.description
    }
  }
}

# main is changed only through pull requests merged by rebase, once their required checks pass; its
# history can't be rewritten or deleted (spec: rulesets; protect-main design D2 and D3,
# required-checks design D1 and D4).
resource "github_repository_ruleset" "main" {
  count = var.main_ruleset == "pull-request" ? 1 : 0

  name        = "protect main"
  repository  = github_repository.this.name
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }
  }

  rules {
    deletion                = true
    non_fast_forward        = true
    required_linear_history = true

    pull_request {
      required_approving_review_count = 0
      allowed_merge_methods           = ["rebase"]
    }

    # Each check is pinned to the App that posts it, so a status of the same name from anywhere
    # else doesn't count. Not strict: the App's state commit after every apply would otherwise put
    # every open pull request out of date (required-checks design D3).
    dynamic "required_status_checks" {
      for_each = length(var.required_checks) > 0 ? [1] : []
      content {
        strict_required_status_checks_policy = false

        dynamic "required_check" {
          for_each = var.required_checks
          content {
            context        = required_check.value.context
            integration_id = required_check.value.integration_id
          }
        }
      }
    }
  }

  # Org owners bypass on pull requests only: never a direct push, so an agent using the owner's
  # credentials can't push to main either. Break-glass is editing the ruleset on GitHub.
  dynamic "bypass_actors" {
    for_each = var.owner_bypass ? [1] : []
    content {
      actor_type  = "OrganizationAdmin"
      bypass_mode = "pull_request"
    }
  }

  # The infrastructure App pushes straight to main: guard deliveries to the repositories that
  # receive the guard (spec: guard-delivery), and the state after a CI apply here (spec: ci-apply).
  # It already holds org administration, so this adds no trust it didn't have.
  dynamic "bypass_actors" {
    for_each = var.app_bypass_id == null ? [] : [var.app_bypass_id]
    content {
      actor_type  = "Integration"
      actor_id    = bypass_actors.value
      bypass_mode = "always"
    }
  }
}

# Only the App changes main: no push, no pull request merge, no force-push or deletion, by anyone
# else, org owners included. The owner's break-glass is editing the ruleset on GitHub
# (required-checks design D4).
resource "github_repository_ruleset" "app_only" {
  count = var.main_ruleset == "app-only" ? 1 : 0

  name        = "app only"
  repository  = github_repository.this.name
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }
  }

  rules {
    update                        = true
    update_allows_fetch_and_merge = false
    deletion                      = true
    non_fast_forward              = true
  }

  bypass_actors {
    actor_type  = "Integration"
    actor_id    = var.app_bypass_id
    bypass_mode = "always"
  }

  lifecycle {
    precondition {
      condition     = var.app_bypass_id != null
      error_message = "An app-only ruleset needs app_bypass_id: without it, nothing could change main."
    }
  }
}
