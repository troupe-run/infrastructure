# Proposal: declare the website's GitHub Pages settings

## Why

https://troupe.run depends on three Pages settings on `troupe-run/website`: the custom domain `troupe.run`, HTTPS
enforced, and deploys from Actions (`build_type: workflow`). They were set by hand on GitHub, and nothing checks them.
The repositories spec already says the site keeps `troupe.run` with HTTPS enforced, but a plan can't see a change to
either. adopt-org left this for "a later change, if Pages settings are to be managed" (#51).

## What Changes

- The website's Pages site is declared with the provider's `github_repository_pages` resource: `cname = "troupe.run"`,
  `https_enforced = true`, `build_type = "workflow"`, and no `source`. It's adopted by an `import` block, and the first
  plan must show it imported with no change.
- The shared repository module gains an optional `pages` variable. Only `repo_website` sets it, so the other three
  repositories plan no change.
- An apply can't take the site down. The resource has `prevent_destroy`, as `github_repository` does, because
  destroying it disables Pages. Stopping management uses a `removed` block, as the README already says for
  repositories.
- The comment above `module "repo_website"` saying Pages isn't declared goes.
- The `troupe-run-infrastructure` App gains the **Pages** repository permission (read and write), and
  `oob/app-installations.json` records it. The App can read a Pages site without it, but an update is refused with a
  403, so drift would show and its correction would fail (design D5). Only the owner can change the App's permissions.

Out of scope: the `github-pages` environment and its main-only deploy rule (#52); troupe.run's DNS (#55); whether
the Pages site is public (`public` is left unset, so the provider reads it and never sends it: a public repository on
GitHub Free can only have a public site); the `www` redirect, which GitHub provides and the DNS change owns.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repositories`: a new requirement, "The website's Pages settings are declared". It says which settings are
  declared, that a change to any of them on GitHub shows as drift, and that no plan or apply disables the site.

`teams-and-access` needs no change: "Each App's installation is declared" already covers a new permission, which is a
change to the declaration's data.

## Impact

- `tofu/modules/repository/`: a new `pages` variable and a `github_repository_pages` resource counted on it.
- `tofu/repositories.tf`: `repo_website` sets `pages`, and the stale comment goes.
- `tofu/imports.tf`: one `import` block for the website's Pages site.
- `oob/app-installations.json`: the App's Pages permission, which the owner adds on GitHub.
- The live site: the first apply imports the site with no change. A wrong attribute would change the live domain or
  HTTPS, so the plan is read for `0 to change` on the Pages resource before it's approved.
