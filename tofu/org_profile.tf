# The files of troupe-run/.github, whose source is ../org-profile (spec: org-profile).

locals {
  org_profile_files = toset([
    "CONTRIBUTING.md",
    "SECURITY.md",
    "profile/README.md",
    ".github/dco.yml",
  ])
}

resource "github_repository_file" "org_profile" {
  for_each = local.org_profile_files

  repository          = module.repo_github.name
  branch              = "main"
  file                = each.key
  content             = file("${path.module}/../org-profile/${each.key}")
  commit_message      = "chore: sync ${each.key} from troupe-run/infrastructure"
  overwrite_on_create = false

  # The provider reads back the message of the file's last commit, which isn't a property of
  # the file. Ignoring it keeps the plan about content; a content change still commits with
  # the message above.
  lifecycle {
    ignore_changes = [commit_message]
  }
}
