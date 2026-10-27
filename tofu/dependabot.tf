# Each repository's Dependabot configuration (spec: dependency-updates; deliver-dependabot design
# D2, D4). scripts/dependabot_config.py generates tofu/dependabot/<repository>.yml from
# tofu/dependabot.json and tofu/labels/dependabot.json, and the App commits each to its
# repository's main, this one's included (owner, 2026-10-26).

locals {
  dependabot_path = ".github/dependabot.yml"

  # Dependabot's App, which GitHub lets a ruleset name as a bypass actor (gh api /apps/dependabot;
  # dependabot-exemption task 1.1).
  dependabot_app_id = 29110

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

# Only Dependabot creates or updates a dependabot/ branch, so in these repositories the branch's
# name is proof of who wrote it, and the guard exempts a minor or patch update of dependency files
# by that name (spec: dependency-updates; dependabot-exemption design D2, D3). A repository gets it
# exactly when it gets a dependabot.yml. The pattern is **/*, not **: the probe showed GitHub
# matches refs/heads/dependabot/** to no dependabot/<ecosystem>/<name> branch (task 1.3). No
# non_fast_forward rule, because Dependabot force-pushes when it rebases, and no owner bypass; the
# break-glass is editing the ruleset on GitHub. No deletion rule, so delete-on-merge removes the
# branch.
resource "github_repository_ruleset" "dependabot_branches" {
  for_each = local.dependabot_files

  name        = "dependabot branches"
  repository  = each.key
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["refs/heads/dependabot/**/*"]
      exclude = []
    }
  }

  rules {
    creation                      = true
    update                        = true
    update_allows_fetch_and_merge = false
  }

  bypass_actors {
    actor_type  = "Integration"
    actor_id    = local.dependabot_app_id
    bypass_mode = "always"
  }

  depends_on = [module.repo_troupe, module.repo_website, module.repo_infrastructure]
}
