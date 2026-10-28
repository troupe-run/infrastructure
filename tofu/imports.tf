# Adoption (design D5): each existing object is imported, not created. Kept after the import as
# a record of what was adopted; once imported, an import block is a no-op.

import {
  to = github_organization_settings.org
  id = "334442748"
}

import {
  to = module.repo_troupe.github_repository.this
  id = "troupe"
}

import {
  to = module.repo_troupe.github_issue_labels.this
  id = "troupe"
}

import {
  to = module.repo_github.github_repository.this
  id = ".github"
}

import {
  to = module.repo_github.github_issue_labels.this
  id = ".github"
}

import {
  to = module.repo_infrastructure.github_repository.this
  id = "infrastructure"
}

import {
  to = module.repo_infrastructure.github_issue_labels.this
  id = "infrastructure"
}

# The four files .github had when it was adopted. Files added to org-profile/ since are created,
# not imported (pr-templates D1).
import {
  for_each = toset(["CONTRIBUTING.md", "SECURITY.md", "profile/README.md", ".github/dco.yml"])
  to       = github_repository_file.org_profile[each.key]
  id       = ".github:${each.key}:"
}

import {
  to = module.repo_website.github_repository.this
  id = "website"
}

import {
  to = module.repo_website.github_issue_labels.this
  id = "website"
}

# The website's Pages site, set by hand before website-pages declared it (design D4).
import {
  to = module.repo_website.github_repository_pages.this[0]
  id = "website"
}

# The files troupe already had when it was adopted. The generated list, and any file delivered since
# (scripts/guard_pytest.py, commit-check-paths), is created, not imported: importing a file troupe
# doesn't have fails the plan with a 404. Only troupe's were adopted: a repository that joins the
# guard later has none of them, so each of its files is created (govern-website).
locals {
  guard_adopted_files = toset([
    "scripts/guard.py",
    ".githooks/pre-commit",
    ".githooks/commit-msg",
    ".githooks/pre-push",
    ".claude/settings.json",
    ".github/workflows/guard.yml",
  ])
}

import {
  for_each = { for key, delivery in local.guard_deliveries : key => delivery if delivery.repository == module.repo_troupe.name && contains(local.guard_adopted_files, delivery.file) }
  to       = github_repository_file.guard[each.key]
  id       = "${each.value.repository}:${each.value.file}:"
}

# The website's github-pages environment and its one deployment branch policy, main, which GitHub
# created with Pages (website-environment design D2).
import {
  to = github_repository_environment.github_pages
  id = "website:github-pages"
}

import {
  to = github_repository_environment_deployment_policy.github_pages_main_only
  id = "website:github-pages:62248502"
}

# Dependabot alerts were already on in all four repositories, so their import plans no change;
# security updates were off, so theirs plans one (security-scanning design D1).

import {
  to = module.repo_troupe.github_repository_vulnerability_alerts.this
  id = "troupe"
}

import {
  to = module.repo_troupe.github_repository_dependabot_security_updates.this
  id = "troupe"
}

import {
  to = module.repo_github.github_repository_vulnerability_alerts.this
  id = ".github"
}

import {
  to = module.repo_github.github_repository_dependabot_security_updates.this
  id = ".github"
}

import {
  to = module.repo_infrastructure.github_repository_vulnerability_alerts.this
  id = "infrastructure"
}

import {
  to = module.repo_infrastructure.github_repository_dependabot_security_updates.this
  id = "infrastructure"
}

import {
  to = module.repo_website.github_repository_vulnerability_alerts.this
  id = "website"
}

import {
  to = module.repo_website.github_repository_dependabot_security_updates.this
  id = "website"
}

# troupe's alpha-0, adopted as its 0.1.0 and renamed in place, so its issues keep it (owner,
# 2026-10-17; release-milestones design D3).
import {
  to = github_repository_milestone.release["troupe/0.1.0"]
  id = "troupe-run/troupe/1"
}

# troupe.run's records as Cloudflare served them when it took over from Gandi: ten copied by its
# scan, and the Pages challenge the owner added. Imported, not recreated, because they're live
# (manage-dns-as-code design D2). The IDs are `<zone>/<record>`, read with the DNS token; they
# identify objects and aren't secret.

import {
  to = cloudflare_dns_record.troupe_run["apex-a-108"]
  id = "f716f063a26f15bcfcecd62791cdd202/be277d7b076adb4e5ce20835d1c51898"
}

import {
  to = cloudflare_dns_record.troupe_run["apex-a-109"]
  id = "f716f063a26f15bcfcecd62791cdd202/358fa37e927b4887ad5c893d6652a872"
}

import {
  to = cloudflare_dns_record.troupe_run["apex-a-110"]
  id = "f716f063a26f15bcfcecd62791cdd202/dea0be14dc4d244cd40f5e877f3bb8cd"
}

import {
  to = cloudflare_dns_record.troupe_run["apex-a-111"]
  id = "f716f063a26f15bcfcecd62791cdd202/660e903470158fa5dbf5a77c6f04b6db"
}

import {
  to = cloudflare_dns_record.troupe_run["apex-aaaa-8000"]
  id = "f716f063a26f15bcfcecd62791cdd202/d445ef5e762426d8f78b4a0eed0f2c23"
}

import {
  to = cloudflare_dns_record.troupe_run["apex-aaaa-8001"]
  id = "f716f063a26f15bcfcecd62791cdd202/5a337b22a47d23fc5f4cc1d4f94fcb93"
}

import {
  to = cloudflare_dns_record.troupe_run["apex-aaaa-8002"]
  id = "f716f063a26f15bcfcecd62791cdd202/bff4ac11cb1977de99fc16069bbe20b2"
}

import {
  to = cloudflare_dns_record.troupe_run["apex-aaaa-8003"]
  id = "f716f063a26f15bcfcecd62791cdd202/4a0260edaa4b749fa6b3329d14c4be3b"
}

import {
  to = cloudflare_dns_record.troupe_run["www"]
  id = "f716f063a26f15bcfcecd62791cdd202/1c76375044e1296ce02454c0c922b560"
}

import {
  to = cloudflare_dns_record.troupe_run["org-verify"]
  id = "f716f063a26f15bcfcecd62791cdd202/05b01811966bd3ed028215c1382805f4"
}

import {
  to = cloudflare_dns_record.troupe_run["pages-verify"]
  id = "f716f063a26f15bcfcecd62791cdd202/25be6a5ec9d1532102f26ba9aea140eb"
}

# troupe.run's Universal SSL setting, adopted as it is (on), so the first plan imports it and changes
# nothing. The ID is the zone's (declare-universal-ssl design D2).
import {
  to = cloudflare_universal_ssl_setting.troupe_run
  id = "f716f063a26f15bcfcecd62791cdd202"
}

# Each repository's Actions settings, adopted as they are (on, every action allowed), so the first
# plan imports them and changes only .github's (repository-features design D2).
import {
  to = module.repo_troupe.github_actions_repository_permissions.this
  id = "troupe"
}

import {
  to = module.repo_github.github_actions_repository_permissions.this
  id = ".github"
}

import {
  to = module.repo_infrastructure.github_actions_repository_permissions.this
  id = "infrastructure"
}

import {
  to = module.repo_website.github_actions_repository_permissions.this
  id = "website"
}
