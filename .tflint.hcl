# TFLint's rules for tofu/ (spec: ci-apply; lint-mutation design D1). scripts/check.py runs
# `tflint --chdir=tofu --recursive` with this file, locally when tflint is installed and always in CI.
#
# tflint v0.66.0
# The version CI installs (.github/workflows/ci.yml) and the one the check's install hint names.
# A test holds the workflow to it.
#
# Only the bundled terraform ruleset: no plugin is fetched, so the check runs no downloaded rules.
# A rule turned off here, or a finding accepted, carries the reason beside it: this file is the
# recorded baseline #323 allows.

config {
  call_module_type = "local"
}

plugin "terraform" {
  enabled = true
  preset  = "recommended"
}
