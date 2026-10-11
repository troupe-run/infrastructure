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
  overwrite_on_create = false

  # Changes exactly when the content does, so a sync never reuses an earlier message (spec:
  # org-profile; development-workflow design D3).
  commit_message = "chore: sync ${each.key} ${substr(sha256(file("${path.module}/../org-profile/${each.key}")), 0, 12)} from troupe-run/infrastructure"
}
