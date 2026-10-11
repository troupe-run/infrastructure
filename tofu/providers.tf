# The provider acts as the troupe-run-infrastructure App (design D3). With `app_auth {}` empty it
# reads GITHUB_APP_ID, GITHUB_APP_INSTALLATION_ID and GITHUB_APP_PEM_FILE (the key's contents),
# which scripts/tofu.py supplies, so this block is the same locally and in CI.
provider "github" {
  owner = "troupe-run"

  app_auth {}
}
