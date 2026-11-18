# The files every governed repository runs from here: the guard's, the quality gates' measures
# (spec: quality-gates), Claude's review workflow (spec: pr-review; claude-pr-review design D6),
# the dispatcher that starts dependabot-issues (spec: dependency-updates; dependabot-issues-on-events
# design D2), and, to the repositories scripts/mutation.json lists, the pull request mutation report
# (spec: mutation-testing; lint-mutation design D9; quality-scope design D3). Their source is this
# repository
# (spec: guard-delivery, design D2), and the App commits them straight to main.

locals {
  # Each governed repository other than this one, which is the source. A repository joins only
  # once its main holds openspec/ and scripts/check.py (spec: guard-delivery; govern-website D1).
  guard_targets = toset([module.repo_troupe.name, module.repo_website.name])

  guard_files = toset([
    "scripts/guard.py",
    # The pytest adapter for the guard's tag check (commit-check-paths design D9).
    "scripts/guard_pytest.py",
    # The merge gates' measures, so every repository measures alike (spec: quality-gates;
    # quality-gates design D1). Each repository's thresholds stay in its own quality-gates.toml.
    "scripts/quality_gates.py",
    ".githooks/pre-commit",
    ".githooks/commit-msg",
    ".githooks/pre-push",
    ".claude/settings.json",
    ".github/workflows/guard.yml",
    # Claude's pull request review (spec: pr-review).
    ".github/workflows/claude-review.yml",
    # Starts infrastructure's dependabot-issues when Dependabot acts there (spec:
    # dependency-updates; dependabot-issues-on-events design D2).
    ".github/workflows/dependabot-dispatch.yml",
  ])

  # Mutation testing of each ready pull request's changes, as a report that never blocks (spec:
  # mutation-testing; lint-mutation design D9), with the scripts and settings it runs. Delivered
  # only to the targets scripts/mutation.json's `repositories` names: the one list of repositories
  # that get coverage and mutation testing (#332; quality-scope design D3). Taking one off the list
  # deletes these files there.
  mutation_report_files = toset([
    ".github/workflows/mutation-pr.yml",
    "scripts/mutation.json",
    "scripts/mutation_children.py",
    "scripts/mutation_pr.py",
    "scripts/mutation_report.py",
    "scripts/mutation_run.py",
    "scripts/mutation_settings.py",
  ])

  mutation_listed = toset(keys(jsondecode(file("${path.module}/../scripts/mutation.json")).repositories))

  # What each target receives, apart from its list.
  guard_target_files = {
    for repository in local.guard_targets : repository => setunion(
      local.guard_files,
      contains(local.mutation_listed, repository) ? local.mutation_report_files : toset([]),
    )
  }

  # The list a receiving repository holds (spec: guard-delivery). Generated from what it receives,
  # so it can't disagree with what is delivered; its presence is what turns on the delivered-file
  # rule. It names the Dependabot configuration delivered beside the guard too (dependabot.tf;
  # spec: dependency-updates), so the rule covers that file as well.
  guard_list_path = ".github/guard-delivery.json"
  guard_lists = {
    for repository, files in local.guard_target_files : repository => "${jsonencode({
      source = "troupe-run/infrastructure"
      files  = sort(concat(tolist(files), [local.guard_list_path, local.dependabot_path]))
    })}\n"
  }

  guard_sources = {
    for source in setunion(local.guard_files, local.mutation_report_files) :
    source => file("${path.module}/../${source}")
  }

  guard_deliveries = merge(
    {
      for pair in flatten([
        for repository, files in local.guard_target_files : [
          for source in files : { repository = repository, file = source }
        ]
      ]) : "${pair.repository}:${pair.file}" => merge(pair, { content = local.guard_sources[pair.file] })
    },
    {
      for repository, list in local.guard_lists : "${repository}:${local.guard_list_path}" => {
        repository = repository, file = local.guard_list_path, content = list
      }
    },
  )
}

resource "github_repository_file" "guard" {
  for_each = local.guard_deliveries

  # content is sensitive, so a plan shows its hash in commit_message, not the file (spec:
  # ci-apply; truncate-long-plans D7). It's reviewed in the pull request's diff of its source.
  repository          = each.value.repository
  branch              = "main"
  file                = each.value.file
  content             = sensitive(each.value.content)
  overwrite_on_create = false

  # After each receiving repository's ruleset, which lets the App push (design D5). Without
  # this the deliveries race the bypass, and one that lands first is refused with a 409. After the
  # Dependabot branch rulesets too, so the guard's exemption never arrives before the reservation
  # it trusts (dependabot-exemption design D7). After the review's model variable, which the
  # delivered review workflow fails without (review-covers-the-diff design D6).
  depends_on = [
    module.repo_troupe,
    module.repo_website,
    github_repository_ruleset.dependabot_branches,
    github_actions_variable.review_model,
  ]

  # Changes exactly when the content does, so a delivery never reuses an earlier message
  # (design D3).
  commit_message = "chore(guard): deliver ${each.value.file} ${substr(sha256(each.value.content), 0, 12)} from troupe-run/infrastructure"
}
