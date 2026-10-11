# Outside OpenTofu's control

These parts of the org can't be managed by OpenTofu, so this directory declares them and
`scripts/oob.py` checks GitHub against the declarations. It only reads: it prints every
difference and exits 1 if there are any. Fix the difference on GitHub, or change the
declaration here in a pull request (design D6 in `openspec/changes/adopt-org/`).

Checked against provider `integrations/github` 6.13.0 with `tofu providers schema` (2026-10-11).

| File | What it declares | Why OpenTofu can't manage it | Read with |
|---|---|---|---|
| `issue-types.json` | the org's issue types: name, description, colour, enabled | the provider has no resource or data source for issue types | `gh api orgs/troupe-run/issue-types` |
| `org-settings.json` | org settings the provider has no attribute for: today, whether 2FA is required | `github_organization_settings` has no two-factor attribute | `gh api orgs/troupe-run` |
| `projects.json` | the org's projects: number, title, public, closed, short description | the provider supports only classic Projects; ours are Projects v2 | `gh api graphql` (`projectsV2`) |

Run it with your own `gh` login, which needs read access to the org:

```
uv run scripts/oob.py
```

It isn't run by CI: CI holds no credentials yet. Run it alongside every plan, and quote its
output in the pull request.
