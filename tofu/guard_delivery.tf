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

  guard_deliveries = {
    for pair in setproduct(local.guard_targets, local.guard_files) :
    "${pair[0]}:${pair[1]}" => { repository = pair[0], file = pair[1] }
  }
}

resource "github_repository_file" "guard" {
  for_each = local.guard_deliveries

  repository          = each.value.repository
  branch              = "main"
  file                = each.value.file
  content             = file("${path.module}/../${each.value.file}")
  commit_message      = "chore(guard): deliver ${each.value.file} from troupe-run/infrastructure"
  overwrite_on_create = false

  # Until the delivery commit messages carry the content (design D3, task 4.1), adopting the
  # existing files must not commit just to change a message.
  lifecycle {
    ignore_changes = [commit_message]
  }
}
