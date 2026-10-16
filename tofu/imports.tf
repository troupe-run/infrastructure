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

# The website's Pages site, set by hand before website-pages declared it (design D4).
import {
  to = module.repo_website.github_repository_pages.this[0]
  id = "website"
}

# The files troupe already had when it was adopted. The generated list, and any file delivered since
# (scripts/guard_pytest.py, commit-check-paths), is created, not imported: importing a file troupe
# doesn't have fails the plan with a 404. Only troupe's were adopted: a repository that joins the
# guard later has none of them, so each of its files is created (govern-website).
locals {
  guard_adopted_files = toset([
    "scripts/guard.py",
    ".githooks/pre-commit",
    ".githooks/commit-msg",
    ".githooks/pre-push",
    ".claude/settings.json",
    ".github/workflows/guard.yml",
  ])
}

import {
  for_each = { for key, delivery in local.guard_deliveries : key => delivery if delivery.repository == module.repo_troupe.name && contains(local.guard_adopted_files, delivery.file) }
  to       = github_repository_file.guard[each.key]
  id       = "${each.value.repository}:${each.value.file}:"
}

# The website's github-pages environment and its one deployment branch policy, main, which GitHub
# created with Pages (website-environment design D2).
import {
  to = github_repository_environment.github_pages
  id = "website:github-pages"
}

import {
  to = github_repository_environment_deployment_policy.github_pages_main_only
  id = "website:github-pages:62248502"
}

# Dependabot alerts were already on in all four repositories, so their import plans no change;
# security updates were off, so theirs plans one (security-scanning design D1).

import {
  to = module.repo_troupe.github_repository_vulnerability_alerts.this
  id = "troupe"
}

import {
  to = module.repo_troupe.github_repository_dependabot_security_updates.this
  id = "troupe"
}

import {
  to = module.repo_github.github_repository_vulnerability_alerts.this
  id = ".github"
}

import {
  to = module.repo_github.github_repository_dependabot_security_updates.this
  id = ".github"
}

import {
  to = module.repo_infrastructure.github_repository_vulnerability_alerts.this
  id = "infrastructure"
}

import {
  to = module.repo_infrastructure.github_repository_dependabot_security_updates.this
  id = "infrastructure"
}

import {
  to = module.repo_website.github_repository_vulnerability_alerts.this
  id = "website"
}

import {
  to = module.repo_website.github_repository_dependabot_security_updates.this
  id = "website"
}
