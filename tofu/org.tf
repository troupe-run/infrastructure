# The organisation's settings (spec: org-settings). Some are findings to fix in later changes,
# such as members being able to create repos. The provider has no attribute for requiring 2FA,
# so that one is checked in oob/org-settings.json instead.

variable "billing_email" {
  description = "Required by the provider. Personal data in a public repo, so supplied at run time."
  type        = string
  sensitive   = true
}

resource "github_organization_settings" "org" {
  name          = "troupe.run"
  billing_email = var.billing_email
  location      = "Australia"
  blog          = ""
  company       = ""
  description   = local.one_line
  email         = ""

  default_repository_permission            = "read"
  members_can_create_repositories          = true
  members_can_create_public_repositories   = true
  members_can_create_private_repositories  = true
  members_can_create_internal_repositories = false
  members_can_fork_private_repositories    = false
  # Members can't create Pages sites: the website's is the org's only one, and its own declaration
  # manages it (spec: org-settings; repository-features design D8, owner 2026-10-28).
  members_can_create_pages         = false
  members_can_create_public_pages  = false
  members_can_create_private_pages = false
  has_organization_projects        = true
  has_repository_projects          = true
  web_commit_signoff_required      = false

  # These don't decide what new repositories get. The "troupe-run baseline" code security
  # configuration does: it's the default for new public repositories, and turns on the dependency
  # graph, Dependabot and secret scanning (oob/code-security.json; spec: org-settings;
  # security-scanning design D4). The provider can't manage configurations, so oob.py checks it.
  # GitHub has marked these parameters as closing down, and still reads them all as false with the
  # configuration as the default (2026-10-16), so they're kept at that to keep the plan clean.
  advanced_security_enabled_for_new_repositories               = false
  dependabot_alerts_enabled_for_new_repositories               = false
  dependabot_security_updates_enabled_for_new_repositories     = false
  dependency_graph_enabled_for_new_repositories                = false
  secret_scanning_enabled_for_new_repositories                 = false
  secret_scanning_push_protection_enabled_for_new_repositories = false
}
