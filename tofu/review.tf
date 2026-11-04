# The model Claude's review runs on, the one place it's declared (spec: pr-review;
# review-covers-the-diff design D6). claude-review.yml reads it as vars.CLAUDE_REVIEW_MODEL, checks
# it's a model name, and fails naming the variable when it's unset: the workflow holds no default,
# so changing the model is this line and an apply. Sonnet for now (owner, 2026-11-04).

locals {
  review_model = "claude-sonnet-5-5"

  # Every repository the review runs in: this one, and the two it's delivered to.
  review_repositories = toset([
    module.repo_troupe.name,
    module.repo_infrastructure.name,
    module.repo_website.name,
  ])
}

# The infrastructure App writes it with "Variables: write", which it already has on all three
# (board.tf, dependabot_dispatch.tf).
resource "github_actions_variable" "review_model" {
  for_each = local.review_repositories

  repository    = each.value
  variable_name = "CLAUDE_REVIEW_MODEL"
  value         = local.review_model
}

# The owner set infrastructure's by hand before this change's pull request, whose review runs its
# own copy of the workflow before any apply (design D6, Migration Plan); the apply adopts it.
import {
  to = github_actions_variable.review_model["infrastructure"]
  id = "infrastructure:CLAUDE_REVIEW_MODEL"
}
