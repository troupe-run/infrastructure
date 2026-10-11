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

  security_and_analysis {
    secret_scanning {
      status = "disabled"
    }
    secret_scanning_push_protection {
      status = "disabled"
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

# main is changed only through pull requests merged by rebase; its history can't be rewritten or
# deleted (spec: rulesets; openspec/changes/protect-main/design.md, D2 and D3).
resource "github_repository_ruleset" "main" {
  count = var.protect_main ? 1 : 0

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

  # The infrastructure App delivers the guard's files straight to main (spec: guard-delivery,
  # design D5). It already holds org administration, so this adds no trust it didn't have.
  dynamic "bypass_actors" {
    for_each = var.delivery_app_id == null ? [] : [var.delivery_app_id]
    content {
      actor_type  = "Integration"
      actor_id    = bypass_actors.value
      bypass_mode = "always"
    }
  }
}
