# The guard's files in the repositories it governs, whose source is this repository (spec:
# guard-delivery, design D2). The App commits them straight to main.

locals {
  # Each governed repository other than this one, which is the source.
  guard_targets = toset([module.repo_troupe.name])

  guard_files = toset([
    "scripts/guard.py",
    ".githooks/pre-commit",
    ".githooks/commit-msg",
    ".githooks/pre-push",
    ".claude/settings.json",
    ".github/workflows/guard.yml",
  ])

  # The list a receiving repository holds (spec: guard-delivery). Generated from guard_files, so it
  # can't disagree with what is delivered; its presence is what turns on the delivered-file rule.
  guard_list_path = ".github/guard-delivery.json"
  guard_list = "${jsonencode({
    source = "troupe-run/infrastructure"
    files  = sort(concat(tolist(local.guard_files), [local.guard_list_path]))
  })}\n"

  guard_contents = merge(
    { for source in local.guard_files : source => file("${path.module}/../${source}") },
    { (local.guard_list_path) = local.guard_list },
  )

  guard_deliveries = {
    for pair in setproduct(local.guard_targets, keys(local.guard_contents)) :
    "${pair[0]}:${pair[1]}" => { repository = pair[0], file = pair[1] }
  }
}

resource "github_repository_file" "guard" {
  for_each = local.guard_deliveries

  repository          = each.value.repository
  branch              = "main"
  file                = each.value.file
  content             = local.guard_contents[each.value.file]
  overwrite_on_create = false

  # After the repository's ruleset, which lets the App push (design D5). Without this the
  # deliveries race the bypass, and one that lands first is refused with a 409.
  depends_on = [module.repo_troupe]

  # Changes exactly when the content does, so a delivery never reuses an earlier message
  # (design D3).
  commit_message = "chore(guard): deliver ${each.value.file} ${substr(sha256(local.guard_contents[each.value.file]), 0, 12)} from troupe-run/infrastructure"
}
