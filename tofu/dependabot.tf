# Each repository's Dependabot configuration (spec: dependency-updates; deliver-dependabot design
# D2, D4). scripts/dependabot_config.py generates tofu/dependabot/<repository>.yml from
# tofu/dependabot.json and tofu/labels/dependabot.json, and the App commits each to its
# repository's main, this one's included (owner, 2026-10-26).

locals {
  dependabot_path = ".github/dependabot.yml"

  # One file per repository with ecosystems, so a repository with none (.github) gets none.
  dependabot_files = {
    for name in fileset("${path.module}/dependabot", "*.yml") :
    trimsuffix(name, ".yml") => file("${path.module}/dependabot/${name}")
  }
}

resource "github_repository_file" "dependabot" {
  for_each = local.dependabot_files

  # content is sensitive, so a plan shows its hash in commit_message, not the file (spec:
  # ci-apply; truncate-long-plans D7). It's reviewed in the pull request's diff of
  # tofu/dependabot/.
  repository          = each.key
  branch              = "main"
  file                = local.dependabot_path
  content             = sensitive(each.value)
  overwrite_on_create = false

  # After each repository's ruleset, which lets the App push (guard-delivery design D5).
  depends_on = [module.repo_troupe, module.repo_website, module.repo_infrastructure]

  # Changes exactly when the content does (guard-delivery design D3).
  commit_message = "chore(dependabot): deliver ${local.dependabot_path} ${substr(sha256(each.value), 0, 12)} from troupe-run/infrastructure"
}
