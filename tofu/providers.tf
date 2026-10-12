# The provider acts as the troupe-run-infrastructure App (design D3). The App and installation
# IDs aren't secret; the private key arrives at run time through var.github_app_pem, supplied by
# scripts/tofu.py from 1Password (or by CI from a secret), so this block is the same everywhere.
locals {
  # The troupe-run-infrastructure App: the provider acts as it, troupe's ruleset lets it deliver
  # the guard (guard_delivery.tf), and this repository's lets CI commit the state (tofu.yml).
  infrastructure_app_id = 5272634
}

provider "github" {
  owner = "troupe-run"

  app_auth {
    id              = tostring(local.infrastructure_app_id)
    installation_id = "170224209"
    pem_file        = var.github_app_pem
  }
}

# Ephemeral: a saved plan keeps only the name, and the key is supplied again at apply, so no plan
# file (including CI's plan artifact) ever holds it (ci-apply design D3).
variable "github_app_pem" {
  description = "The App's private key (PEM contents, not a path). Never committed, never saved in a plan."
  type        = string
  sensitive   = true
  ephemeral   = true
}
