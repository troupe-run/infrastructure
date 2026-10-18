# The files of troupe-run/.github, whose source is ../org-profile (spec: org-profile).

locals {
  # Every file under org-profile/, so a new source can't be left unpublished (pr-templates D1).
  # fileset reads the disk, not git, so macOS's .DS_Store is left out of a local plan.
  org_profile_files = toset([
    for f in fileset("${path.module}/../org-profile", "**") : f if basename(f) != ".DS_Store"
  ])
}

resource "github_repository_file" "org_profile" {
  for_each = local.org_profile_files

  # content is sensitive, so a plan shows its hash in commit_message, not the file (spec:
  # ci-apply; truncate-long-plans D7). It's reviewed in the pull request's diff of its source.
  repository          = module.repo_github.name
  branch              = "main"
  file                = each.key
  content             = sensitive(file("${path.module}/../org-profile/${each.key}"))
  overwrite_on_create = false

  # Changes exactly when the content does, so a sync never reuses an earlier message (spec:
  # org-profile; development-workflow design D3).
  commit_message = "chore: sync ${each.key} ${substr(sha256(file("${path.module}/../org-profile/${each.key}")), 0, 12)} from troupe-run/infrastructure"
}
