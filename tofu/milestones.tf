# The release milestones, the same in every managed repository (spec: milestones; #68). They're
# troupe's releases: an issue in another repository is filed under the troupe release it serves, and
# the roadmap board (project 1) groups milestones by title, so the titles must match everywhere.
#
# Declared in milestones.json, which scripts/oob.py also reads to report a milestone made by hand.
# Each milestone's key names its address and never changes; its title can. A finished release is
# closed by setting its state to "closed", never removed: removing one fails the plan here, because
# deleting a milestone takes it off every issue it holds (release-milestones design D1, D2).

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
  title       = each.value.milestone.title
  description = each.value.milestone.description
  state       = each.value.milestone.state

  lifecycle {
    prevent_destroy = true
  }
}
