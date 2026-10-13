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
| `tofu/labels/troupe.json` (derived) | a `cap:<name>` label for each folder in troupe's `openspec/specs/`. One way: a label with no spec isn't reported, since a label can come before its spec. The fix is a pull request adding the label (spec: labels) | OpenTofu manages the labels but can't read troupe's files | `gh api repos/troupe-run/troupe/contents/openspec/specs` |
| `troupe-spec-purposes.json` | for each `cap:<name>` label whose troupe spec exists, the spec's Purpose its description was written from, verbatim. A Purpose that has changed, a labelled spec with nothing recorded, and a record with no spec are each reported (spec: labels) | OpenTofu manages the descriptions but can't read troupe's specs to tell when one is out of date | `gh api repos/troupe-run/troupe/contents/openspec/specs/<name>/spec.md` |

**A new capability's label** gets a description of 100 characters or fewer that says what the capability covers
(`scripts/tests/test_labels.py` refuses one that only repeats the name). If troupe has a spec for it, shorten the
spec's Purpose and record that Purpose here, with its whitespace collapsed, in the same pull request. If nothing in
troupe defines it yet, the description is `TBD`. When `oob.py` reports a changed Purpose, review the description
against the new text and update both files together.

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
| `dco` | `troupe`, `.github`, `infrastructure` | 2026-10-11, owner |
| `troupe-run-release` | `troupe` | 2026-10-13, owner |

A repository the infrastructure App isn't installed on shows only its public view to OpenTofu (merge settings read as
off, no security settings), so the first plan after adding one will show that it's missing from this list.

## troupe's release App (set up by hand)

troupe's release workflow (troupe-run/troupe#23) opens release pull requests with the `troupe-run-release` App's
token, because a pull request opened with `GITHUB_TOKEN` starts no workflows (spec: release-credentials). GitHub has no
API for creating an App, and OpenTofu never holds a secret, so these steps are the owner's. The App's ID, client ID and
bot user ID are recorded on #34. `tofu/release.tf` declares the `release` environment and the client-ID variable.

**Creating it** (done 2026-10-13). In the org's settings, under GitHub Apps, create a new App:
- name `troupe-run-release`, installable only on this account, webhook off;
- repository permissions: contents, issues and pull requests read and write, metadata read. No organisation or
  account permissions;
- install it on `troupe` only, and add its row to the table above.

Its installation is checked by `oob.py` against `app-installations.json`. Its client ID goes in `tofu/release.tf`.

**Its key.** Generate a private key in the App's settings. Store it in 1Password as an SSH Key item named
`troupe-run-release` in vault `troupe.run`, by importing the downloaded `.pem`, then delete the file. Once the
`release` environment exists (after the apply that creates it), set the secret. Nothing is printed:

```sh
export OP_ACCOUNT=l-a-u.1password.com
op read -n "op://troupe.run/troupe-run-release/private key" \
  | gh secret set RELEASE_APP_PRIVATE_KEY --env release -R troupe-run/troupe
```

Check it by name, never by value:

```sh
gh api repos/troupe-run/troupe/environments/release/secrets --jq '.secrets[].name'
```

**Rotating the key.** Generate a new key in the App's settings, replace the 1Password item's key with it, and run the
command above again. Then delete the old key in the App's settings. A release run between the two steps still works,
because both keys are valid until the old one is deleted.

**The infrastructure App's "Variables: write"** was granted for this (2026-10-13), so OpenTofu can write
`RELEASE_APP_CLIENT_ID`. It's declared in `app-installations.json`.
