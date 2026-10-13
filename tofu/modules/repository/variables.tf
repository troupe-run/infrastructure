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

# Merge and feature settings (spec: repositories; required-checks design D5): rebase merges only,
# matching the ruleset, branches deleted on merge, and the unused wiki and classic projects off.
variable "allow_merge_commit" {
  type    = bool
  default = false
}

variable "allow_squash_merge" {
  type    = bool
  default = false
}

variable "allow_rebase_merge" {
  type    = bool
  default = true
}

variable "delete_branch_on_merge" {
  type    = bool
  default = true
}

variable "has_wiki" {
  type    = bool
  default = false
}

variable "has_projects" {
  type    = bool
  default = false
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

variable "delivered_paths" {
  description = "Files only the App in app_bypass_id may change, on any branch: the guard's delivered files. Empty: no such ruleset."
  type        = list(string)
  default     = []
}
