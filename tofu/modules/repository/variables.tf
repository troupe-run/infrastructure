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
# several are findings to fix in later changes (openspec/changes/adopt-org/design.md, Findings).
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
