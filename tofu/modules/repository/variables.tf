variable "name" {
  description = "The repository's name in troupe-run."
  type        = string
}

variable "description" {
  type = string
}

variable "homepage_url" {
  type    = string
  default = ""
}

variable "topics" {
  type    = list(string)
  default = []
}

variable "labels" {
  description = "The repository's complete label set. Labels on GitHub that aren't listed show as removals."
  type = list(object({
    name        = string
    color       = string
    description = string
  }))
}

# Merge and feature settings. The defaults are what every repo had when adopted (2026-10-11);
# several are findings to fix in later changes (openspec/changes/archive/2026-10-11-adopt-org/design.md, Findings).
variable "allow_merge_commit" {
  type    = bool
  default = true
}

variable "allow_squash_merge" {
  type    = bool
  default = true
}

variable "allow_rebase_merge" {
  type    = bool
  default = true
}

variable "delete_branch_on_merge" {
  type    = bool
  default = false
}

variable "has_wiki" {
  type    = bool
  default = true
}

variable "has_projects" {
  type    = bool
  default = true
}

# Which ruleset covers main (spec: rulesets; required-checks design D4):
#   pull-request  changes arrive by pull request, merged by rebase once the required checks pass
#   app-only      only the App in app_bypass_id changes main (.github)
#   none          no ruleset (the probe, or a repository not protected yet)
variable "main_ruleset" {
  type    = string
  default = "pull-request"

  validation {
    condition     = contains(["pull-request", "app-only", "none"], var.main_ruleset)
    error_message = "main_ruleset must be pull-request, app-only or none."
  }
}

variable "required_checks" {
  description = "Checks a pull request needs before it merges, each pinned to the App that posts it (pull-request only)."
  type = list(object({
    context        = string
    integration_id = number
  }))
  default = []
}

variable "owner_bypass" {
  description = "Org owners may bypass the ruleset on pull requests only (design D3). Off only on the probe."
  type        = bool
  default     = true
}

variable "app_bypass_id" {
  description = "A GitHub App that may push straight to main: to deliver the guard, or to commit state after a CI apply. Null: none."
  type        = number
  default     = null
}
