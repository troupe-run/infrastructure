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
  description   = ""
  email         = ""

  default_repository_permission            = "read"
  members_can_create_repositories          = true
  members_can_create_public_repositories   = true
  members_can_create_private_repositories  = true
  members_can_create_internal_repositories = false
  members_can_fork_private_repositories    = false
  members_can_create_pages                 = true
  members_can_create_public_pages          = true
  members_can_create_private_pages         = true
  has_organization_projects                = true
  has_repository_projects                  = true
  web_commit_signoff_required              = false

  # New repositories start with the same security features as the managed ones (spec:
  # org-settings; security-scanning design D4). Dependabot alerts need the dependency graph, which
  # is always on for public repositories but not for private ones. Advanced Security stays off:
  # public repositories always have it, and private ones pay for it. GitHub marks these parameters
  # as closing down, in favour of code security configurations, which the provider can't manage.
  # So they're checked on a new repository after an apply, not trusted from what GitHub reads back.
  # If GitHub ignores them, the fallback is a code security configuration declared in oob/ (D4).
  advanced_security_enabled_for_new_repositories               = false
  dependabot_alerts_enabled_for_new_repositories               = true
  dependabot_security_updates_enabled_for_new_repositories     = true
  dependency_graph_enabled_for_new_repositories                = true
  secret_scanning_enabled_for_new_repositories                 = true
  secret_scanning_push_protection_enabled_for_new_repositories = true
}
