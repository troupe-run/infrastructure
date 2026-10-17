# Provider pin and state encryption (design D2). State and saved plans are encrypted with a key
# derived from a passphrase that lives in 1Password; `enforced` makes OpenTofu refuse to write
# either in plain text rather than fall back.
terraform {
  required_version = ">= 1.8" # early-evaluated variables in the encryption block

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.13"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.28"
    }
  }

  encryption {
    key_provider "pbkdf2" "passphrase" {
      passphrase = var.state_passphrase
    }

    method "aes_gcm" "main" {
      keys = key_provider.pbkdf2.passphrase
    }

    state {
      method   = method.aes_gcm.main
      enforced = true
    }

    plan {
      method   = method.aes_gcm.main
      enforced = true
    }
  }
}

# Ephemeral, so a saved plan doesn't record it: `sensitive` alone hides it only from the readable
# plan, and `tofu show -json` would write it out in plain text (ephemeral-state-passphrase D1).
# The apply decrypts the plan with the passphrase supplied again.
variable "state_passphrase" {
  description = "Encrypts state and plans. Supplied at run time by scripts/tofu.py, never committed."
  type        = string
  sensitive   = true
  ephemeral   = true
}
