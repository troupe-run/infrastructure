# The files every governed repository runs from here: the guard's, and Claude's review workflow
# (spec: pr-review; claude-pr-review design D6). Their source is this repository (spec:
# guard-delivery, design D2), and the App commits them straight to main.

locals {
  # Each governed repository other than this one, which is the source. A repository joins only
  # once its main holds openspec/ and scripts/check.py (spec: guard-delivery; govern-website D1).
  guard_targets = toset([module.repo_troupe.name, module.repo_website.name])

  guard_files = toset([
    "scripts/guard.py",
    # The pytest adapter for the guard's tag check (commit-check-paths design D9).
    "scripts/guard_pytest.py",
    ".githooks/pre-commit",
    ".githooks/commit-msg",
    ".githooks/pre-push",
    ".claude/settings.json",
    ".github/workflows/guard.yml",
    # Claude's pull request review (spec: pr-review).
    ".github/workflows/claude-review.yml",
  ])

  # The list a receiving repository holds (spec: guard-delivery). Generated from guard_files, so it
  # can't disagree with what is delivered; its presence is what turns on the delivered-file rule.
  # It names the Dependabot configuration delivered beside the guard too (dependabot.tf; spec:
  # dependency-updates), so the rule covers that file as well.
  guard_list_path = ".github/guard-delivery.json"
  guard_list = "${jsonencode({
    source = "troupe-run/infrastructure"
    files  = sort(concat(tolist(local.guard_files), [local.guard_list_path, local.dependabot_path]))
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

  # content is sensitive, so a plan shows its hash in commit_message, not the file (spec:
  # ci-apply; truncate-long-plans D7). It's reviewed in the pull request's diff of its source.
  repository          = each.value.repository
  branch              = "main"
  file                = each.value.file
  content             = sensitive(local.guard_contents[each.value.file])
  overwrite_on_create = false

  # After each receiving repository's ruleset, which lets the App push (design D5). Without
  # this the deliveries race the bypass, and one that lands first is refused with a 409. After the
  # Dependabot branch rulesets too, so the guard's exemption never arrives before the reservation
  # it trusts (dependabot-exemption design D7).
  depends_on = [module.repo_troupe, module.repo_website, github_repository_ruleset.dependabot_branches]

  # Changes exactly when the content does, so a delivery never reuses an earlier message
  # (design D3).
  commit_message = "chore(guard): deliver ${each.value.file} ${substr(sha256(local.guard_contents[each.value.file]), 0, 12)} from troupe-run/infrastructure"
}
