# Design: declare the website's GitHub Pages settings

## Context

- **Live state (2026-10-16).** `gh api repos/troupe-run/website/pages` reports `cname: troupe.run`,
  `https_enforced: true`, `build_type: workflow`, `public: true`, and `source: {branch: main, path: /}`. The
  certificate covers `troupe.run` and `www.troupe.run`, and expires on 2027-01-06. No other managed repository has
  Pages (`has_pages` is false on `troupe`, `.github` and `infrastructure`).
- **The provider, integrations/github 6.13.0** (the locked version), offers two ways to declare Pages. Both were read
  in the provider's source at the `v6.13.0` tag:
  - `github_repository`'s inline `pages` block is **deprecated** ("Use the github_repository_pages resource instead.
    This field will be removed in a future version."). It has no `https_enforced`. It's read only when it's in the
    configuration, which is why leaving it out shows no drift (adopt-org's finding).
  - **`github_repository_pages`** is a resource of its own. It has `repository`, `build_type` (default `legacy`),
    `source`, `cname`, `https_enforced` (optional and computed, and needs `cname`), and `public` (optional and
    computed). It's imported by the repository's name. Its delete calls `DisablePages`.
- **What it does to `source` when `build_type = "workflow"`** (the issue's question):
  - The plan refuses a `source` with `workflow` ("'source' is not supported for workflow build type").
  - Read sets `source` to null for anything but `legacy`, so the `main /` that the API still reports is never compared.
  - Update sends `source` only for `legacy`.
  So declaring no `source` matches the live site, and nothing is sent that could change it.
- **Authentication.** The Pages API needs an authenticated read: without a token, `GET repos/troupe-run/website/pages`
  answers 404. The infrastructure App has `administration: write` and no `pages` permission
  (`oob/app-installations.json`, which matches the live installation).
- `github_repository` has `prevent_destroy` and `archive_on_destroy`, and the README gives a `removed` block with
  `destroy = false` as the way to stop managing something.

## Goals / Non-Goals

**Goals:**
- The site's domain, HTTPS and build type are declared once, in the website's module block, and drift in any of them
  shows in the plan.
- Adopting the site changes nothing on GitHub, and no later plan can disable it.

**Non-Goals:**
- Detecting a Pages site turned on by hand in another repository. The provider has no way to declare "no Pages": a
  repository without the resource isn't read. This is the same gap adopt-org recorded, now narrower.
- The site's visibility (`public`). It's left out of the configuration, so the provider reads it and never sends it.
  A public repository on GitHub Free can only publish a public site, and sending `public` errors on a repository
  without private Pages ("Private pages is not enabled for this repository").
- The `github-pages` environment (#52) and DNS (#55).

## Decisions

### D1. Use `github_repository_pages`, not the inline `pages` block

The resource is the only way to declare `https_enforced`, which the repositories spec already relies on, and the
inline block is deprecated and will be removed. The resource also has its own address, so it can carry its own
`prevent_destroy` (D3) and be imported on its own (D4) without touching the repository resource.

*Alternative:* the inline block. It can't check HTTPS, it would be removed again in a later provider upgrade, and
changing it rewrites the repository resource's plan.

### D2. An optional `pages` variable in the shared repository module

The module gains:

```hcl
variable "pages" {
  description = "The repository's GitHub Pages site, deployed from Actions. Null: Pages isn't managed here."
  type = object({
    cname          = string
    https_enforced = optional(bool, true)
  })
  default = null
}
```

and a `github_repository_pages.this` resource with `count = var.pages == null ? 0 : 1`,
`repository = github_repository.this.name`, `build_type = "workflow"`, and no `source`. Only `repo_website` sets it:
`pages = { cname = "troupe.run" }`.

Every repository's settings are declared in its module block, so the website's Pages settings belong there too. The
issue asks for this shape. `build_type` is fixed at `workflow` rather than being a variable: it's the only kind of site
the org builds, and a `legacy` site would need `source`, which nothing here would use. If a branch-built site is ever
wanted, the variable grows then. `https_enforced` defaults to true, so a site declared later gets HTTPS unless it says
otherwise.

*Alternatives:* a top-level resource in `repositories.tf`, beside the module. It's simpler, but it splits one
repository's settings across two places. Or a variable for each attribute: that's more surface than one site needs.

### D3. `prevent_destroy` on the Pages resource

Destroying `github_repository_pages` disables Pages, which takes https://troupe.run down and gives up the custom
domain. That's the same harm as deleting a repository, so it gets the same guard: `lifecycle { prevent_destroy = true }`.
Setting `pages = null`, or removing the module, fails the plan instead of disabling the site. To stop managing the
site, a `removed` block with `destroy = false` forgets it (README, "Changing the org", which gains this address as an
example).

`repository` forces replacement, which `prevent_destroy` would also refuse. A rename doesn't trigger it: the
provider's `diffRepository` compares the repository ID and keeps the resource when the ID is the same.

### D4. Adopt by import, and prove it with a no-change plan

An `import` block in `tofu/imports.tf`, beside the website's other two, with
`to = module.repo_website.github_repository_pages.this[0]` and `id = "website"`. The first plan must say
`1 to import, 0 to add, 0 to change, 0 to destroy`. Any change on the Pages resource means an attribute is wrong, and
it's fixed in the configuration, never applied.

### D5. The App gets the Pages permission only if a plan shows it needs it

GitHub's REST reference lists the fine-grained permissions each Pages endpoint needs (read in task 1.1, not assumed
here). The App has no Pages permission. The first local plan is the test: it reads the site as the App.

- If it's refused (403 or 404), the owner adds Pages **read and write** on the App's settings page and accepts the new
  permission on the org's installation. `oob/app-installations.json` gains `"pages": "write"` in the same pull request,
  so `oob.py` agrees with the installation.
- If it reads, no permission is added, and the design records that `administration: write` was enough.

**Result (2026-10-16, task 1.3):** the App read the site with no Pages permission, although GitHub's permissions table
lists Pages read for the GET. No permission was added. The PUT is listed under Administration write too, which the App
has, so a corrective apply is expected to work. If one is ever refused, the step above applies then.

Write is asked for, not read only: correcting drift (the point of declaring it) needs it. The App already holds
`administration: write` on every repository it's installed on, so Pages write adds no trust it didn't have.

### D6. How each scenario is shown, without changing the live site

The live site is never changed to test drift. Each spec scenario is shown this way:

| Scenario | Shown by |
|---|---|
| Adopting the site changes nothing | the local plan and the pull request's plan (D4) |
| Removing the declaration doesn't take the site down | a local plan with `pages` unset on `repo_website`, which must fail on `prevent_destroy`. It's a plan only, and the edit is reverted |
| Deploying from a branch shows as drift | the probe (`tofu/probe`): a throwaway repository with a site deployed from Actions, declared by `github_repository_pages`. Switch it to a branch with `gh api`, and the next probe plan shows `build_type` changing back |
| The custom domain, or HTTPS, changed by hand | can't be probed: a domain belongs to one repository, and `troupe.run` can't be lent to a probe (rename-website design). Shown by the provider's Read, which sets `cname` and `https_enforced` from the API on every refresh, so a difference from the declared value is a planned change. The task cites the lines, and says that this is reasoning from source, not a run |

The probe declares the resource directly, not through the module, because the module requires a domain. What it
tests is the provider's drift detection, and the module wiring is tested by the live plan.

## Risks / Trade-offs

- **[A wrong attribute changes the live site on the first apply]** → D4: the plan is read for no change on the Pages
  resource before the owner approves it. The values are copied from the live API response above.
- **[Correcting a removed domain needs two applies]** → if the domain is removed by hand, GitHub also turns off HTTPS
  and the certificate goes. One apply sends both `cname` and `https_enforced`, and GitHub refuses HTTPS until the
  certificate is issued again ("The certificate does not exist yet"). The first apply restores the domain and fails on
  HTTPS; a second apply, once the certificate is approved, enforces it. This is said in the comment on the website's
  `pages` setting, rather than designed around: it's a recovery from a hand change, and it ends in the declared state.
- **[The App can't read Pages]** → D5. The owner's step on the App is out of band and can't be done from here.
- **[Concurrent website changes]** → #52 (the `github-pages` environment) is being worked on in the
  `website-environment` worktree, and may also edit `repo_website` or `imports.tf`. Whichever merges second rebases
  onto `main` after its state commit (memory: branch-cleanup-and-merge-order), and plans again.
- **[A provider upgrade changes the resource]** → it's the provider's preferred resource, not the deprecated one, so
  an upgrade is less likely to remove it. Any change shows in the plan of the upgrade's pull request.

## Migration Plan

1. If the first local plan shows the App can't read Pages, the owner adds the permission (D5), and the plan runs again.
2. A local plan on this branch, fast-forwarded onto `origin/main`, imports the site with no change.
3. The pull request's CI plan says the same. After the merge, the owner approves `main`'s apply, which only imports.
4. After the apply, `gh api repos/troupe-run/website/pages` reports the same values as before, and https://troupe.run
   answers 200.

**Rollback:** a `removed` block for `module.repo_website.github_repository_pages.this[0]` with `destroy = false`
forgets the site, and leaves it serving as it is. If the App was given the Pages permission, removing it is the owner's
step on the App's settings page, with `oob/app-installations.json` changed to match.
