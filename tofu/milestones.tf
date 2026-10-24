# The release milestones, the same in every managed repository (spec: milestones; #68). They're
# troupe's releases: an issue in another repository is filed under the troupe release it serves, and
# the roadmap board (project 1) groups milestones by title, so the titles must match everywhere.
#
# Declared in milestones.json, which scripts/oob.py also reads to report a milestone made by hand.
# Each milestone's key names its address and never changes; its title can. A finished release is
# closed by setting its state to "closed", never removed: removing one fails the plan here, because
# deleting a milestone takes it off every issue it holds (release-milestones design D1, D2).
#
# A milestone may also have an interim_title, which is applied instead of its title while it's
# declared. GitHub refuses two milestones with one title in a repository, so titles that move
# between milestones go to interim titles in one apply and to their titles in the next
# (milestone-interim-titles design D1). The title stays the release's version: it's what the
# website's /status/ reads. The expression is copied in tofu/probe/main.tf; change both together.

locals {
  milestones = jsondecode(file("${path.module}/milestones.json"))

  release_milestones = {
    for pair in setproduct(local.milestones.repositories, local.milestones.milestones) :
    "${pair[0]}/${pair[1].key}" => { repository = pair[0], milestone = pair[1] }
  }
}

resource "github_repository_milestone" "release" {
  for_each = local.release_milestones

  owner       = "troupe-run"
  repository  = each.value.repository
  title       = try(each.value.milestone.interim_title, each.value.milestone.title)
  description = each.value.milestone.description
  state       = each.value.milestone.state

  lifecycle {
    prevent_destroy = true
  }
}
