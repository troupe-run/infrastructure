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

# The four files .github had when it was adopted. Files added to org-profile/ since are created,
# not imported (pr-templates D1).
import {
  for_each = toset(["CONTRIBUTING.md", "SECURITY.md", "profile/README.md", ".github/dco.yml"])
  to       = github_repository_file.org_profile[each.key]
  id       = ".github:${each.key}:"
}

import {
  to = module.repo_website.github_repository.this
  id = "website"
}

import {
  to = module.repo_website.github_issue_labels.this
  id = "website"
}

# The files troupe already had when it was adopted; the generated list is created, not imported.
import {
  for_each = { for key, delivery in local.guard_deliveries : key => delivery if delivery.file != local.guard_list_path }
  to       = github_repository_file.guard[each.key]
  id       = "${each.value.repository}:${each.value.file}:"
}
