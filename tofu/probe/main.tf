# The drift probe (design D7): the same repository module and file resource as the live root,
# pointed at a throwaway repo, so the drift behaviours in the specs can be shown without
# touching a live one. Its state is git-ignored and deleted with the repo; it is encrypted the
# same way regardless.
#
# To run it again (task 6 in openspec/changes/adopt-org/tasks.md, archived with the change):
#   1. gh repo create troupe-run/<name> --public --add-readme, then add it to the App's installation;
#   2. save its README as README.probe.md here, and set probe_repo = "<name>" in terraform.tfvars;
#   3. from tofu/probe, with OP_ACCOUNT set: op run --env-file=../secrets.env -- tofu <init|plan|apply>;
#   4. delete the repo, then this directory's state, README.probe.md and terraform.tfvars.

terraform {
  required_version = ">= 1.8"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.13"
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

variable "state_passphrase" {
  type      = string
  sensitive = true
}

variable "github_app_pem" {
  type      = string
  sensitive = true
}

variable "probe_repo" {
  description = "The throwaway repo, e.g. infra-probe-20261011."
  type        = string
}

variable "declared" {
  description = "Set to false to remove the repo's declaration (the prevent_destroy step)."
  type        = bool
  default     = true
}

provider "github" {
  owner = "troupe-run"

  app_auth {
    id              = "5272634"
    installation_id = "170224209"
    pem_file        = var.github_app_pem
  }
}

module "probe" {
  source = "../modules/repository"
  count  = var.declared ? 1 : 0

  name        = var.probe_repo
  description = "Throwaway: drift probe for troupe-run/infrastructure#2. Deleted after use."
  labels      = jsondecode(file("${path.module}/../labels/github-defaults.json"))
}

resource "github_repository_file" "probe" {
  count = var.declared ? 1 : 0

  repository          = var.probe_repo
  branch              = "main"
  file                = "README.md"
  content             = file("${path.module}/README.probe.md")
  commit_message      = "chore: probe file"
  overwrite_on_create = false

  lifecycle {
    ignore_changes = [commit_message]
  }
}

locals {
  adopt = var.declared ? toset(["probe"]) : toset([])
}

import {
  for_each = local.adopt
  to       = module.probe[0].github_repository.this
  id       = var.probe_repo
}

import {
  for_each = local.adopt
  to       = module.probe[0].github_issue_labels.this
  id       = var.probe_repo
}

import {
  for_each = local.adopt
  to       = github_repository_file.probe[0]
  id       = "${var.probe_repo}:README.md:"
}
