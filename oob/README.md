# Outside OpenTofu's control

These parts of the org can't be managed by OpenTofu, so this directory declares them and
`scripts/oob.py` checks GitHub against the declarations. It only reads: it prints every
difference and exits 1 if there are any. Fix the difference on GitHub, or change the
declaration here in a pull request (design D6 in `openspec/changes/archive/2026-10-11-adopt-org/`).

Checked against provider `integrations/github` 6.13.0 with `tofu providers schema` (2026-10-11).

| File | What it declares | Why OpenTofu can't manage it | Read with |
|---|---|---|---|
| `issue-types.json` | the org's issue types: name, description, colour, enabled | the provider has no resource or data source for issue types | `gh api orgs/troupe-run/issue-types` |
| org-profile/ (derived) | the files `troupe-run/.github` should hold: exactly the files under `org-profile/` | `github_repository_file` manages declared files only, so a file added by hand would never show in a plan | `gh api repos/troupe-run/.github/git/trees/main` |
| `app-installations.json` | each App installed in the org: its permissions and repository selection | the provider can't read installations as the App (403, design D9) | `gh api orgs/troupe-run/installations` |
| `org-settings.json` | org settings the provider has no attribute for: today, whether 2FA is required | `github_organization_settings` has no two-factor attribute | `gh api orgs/troupe-run` |
| `projects.json` | the org's projects: number, title, public, closed, short description | the provider supports only classic Projects; ours are Projects v2 | `gh api graphql` (`projectsV2`) |

Run it with your own `gh` login, which needs read access to the org:

```
uv run scripts/oob.py
```

It isn't run by CI: CI holds no credentials yet. Run it alongside every plan, and quote its
output in the pull request.

## Which repositories each App is installed on (confirmed by hand)

No token this repo can hold is allowed to read these lists: the App's own installation token, `gh`'s OAuth token and
a classic personal access token (even with `repo`) were all refused with a 403 on 2026-10-11 (design D9). So the
lists below are checked by hand in each App's settings, by any change that adds, removes or depends on a repository
(spec: teams-and-access).

| App | Repositories | Confirmed |
|---|---|---|
| `troupe-run-infrastructure` | `troupe`, `.github`, `infrastructure`, `website` | 2026-10-11, owner |
| `troupe-run-infrastructure-plan` (unused, see ci-apply design D2) | `troupe`, `.github`, `infrastructure`, `website` | 2026-10-12, owner |
| `dco` | `troupe`, `.github`, `infrastructure` | 2026-10-11, owner |

A repository the infrastructure App isn't installed on shows only its public view to OpenTofu (merge settings read as
off, no security settings), so the first plan after adding one will show that it's missing from this list.
