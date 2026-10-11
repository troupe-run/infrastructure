# Adoption (design D5): each existing object is imported, not created. Kept after the import as
# a record of what was adopted; once imported, an import block is a no-op.

import {
  to = github_organization_settings.org
  id = "334442748"
}

import {
  to = module.repo_troupe.github_repository.this
  id = "troupe"
}

import {
  to = module.repo_troupe.github_issue_labels.this
  id = "troupe"
}

import {
  to = module.repo_github.github_repository.this
  id = ".github"
}

import {
  to = module.repo_github.github_issue_labels.this
  id = ".github"
}

import {
  to = module.repo_infrastructure.github_repository.this
  id = "infrastructure"
}

import {
  to = module.repo_infrastructure.github_issue_labels.this
  id = "infrastructure"
}

import {
  for_each = local.org_profile_files
  to       = github_repository_file.org_profile[each.key]
  id       = ".github:${each.key}:"
}

import {
  to = module.repo_website.github_repository.this
  id = "troupe-run.github.io"
}

import {
  to = module.repo_website.github_issue_labels.this
  id = "troupe-run.github.io"
}

import {
  for_each = local.guard_deliveries
  to       = github_repository_file.guard[each.key]
  id       = "${each.value.repository}:${each.value.file}:"
}
