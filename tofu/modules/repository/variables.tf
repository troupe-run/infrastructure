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

# The ruleset on main (spec: rulesets). On for every managed repo unless its declaration says
# otherwise; .github turns it off until its own ruleset arrives.
variable "protect_main" {
  type    = bool
  default = true
}

variable "owner_bypass" {
  description = "Org owners may bypass the ruleset on pull requests only (design D3). Off only on the probe."
  type        = bool
  default     = true
}

variable "delivery_app_id" {
  description = "A GitHub App that may push straight to main, to deliver the guard (design D5). Null: none."
  type        = number
  default     = null
}
