# Design

## Context

See proposal.md, Why. What's on today was read from GitHub on 2026-10-28, and matches the issue's table from
2026-10-25:

| Feature | troupe | infrastructure | website | .github | Declared in |
|---|---|---|---|---|---|
| Discussions | off | off | off | off | module, hard-coded `false` |
| Issues | on | on | on | on | module, hard-coded `true` |
| Projects | on | off | on | off | `has_projects` variable |
| Actions | on, all actions | on | on | on, no workflows | nowhere |
| Private vulnerability reporting | on | **off** | on | on | nowhere |

What provider `integrations/github` 6.13.0 can manage (`tofu providers schema`, 2026-10-28):

- `github_repository` has `has_discussions`, `has_issues` and `has_projects`.
- `github_actions_repository_permissions` manages a repository's Actions: `enabled`, `allowed_actions` and
  `sha_pinning_required`. It's imported by repository name.
- There's no resource for private vulnerability reporting or for discussion categories. GraphQL can read categories
  (`discussionCategories`: `name`, `slug`, `isAnswerable`, `description`, `emoji`), but no mutation creates or edits
  them, and no field says a category is announcement-only.
- `github_organization_settings` has `members_can_create_pages`, `members_can_create_public_pages` and
  `members_can_create_private_pages`.

Other facts this rests on:

- troupe, infrastructure and website have no issue forms of their own, so all three use the org's from `.github`.
  The issue chooser's `config.yml` is delivered by the plan from `org-profile/` (spec: org-profile).
- The roadmap (project 1) is linked to troupe and website only (`oob/projects.json`). Linking is owner-only in the
  guard.
- The infrastructure App has repository administration (write), which reads private vulnerability reporting, but
  no Discussions permission (`oob/app-installations.json`).
- The org's only member is its owner.
- `.github` has no dependency ecosystems (`tofu/labels/dependabot.json`), so Dependabot has nothing to run there with
  Actions off. Claude's review leaves `.github` out (#154; owner, 2026-10-26).

## Goals / Non-Goals

**Goals:**

- Each feature that differs between repositories is a module variable with the common value as its default, so a
  repository's declaration names only what's different, with the reason beside it.
- Every chosen feature is either in the plan or in `oob.py`. Nothing chosen is left set by hand without a check.

**Non-Goals:**

- Moderation tooling, discussion templates or a code of conduct for troupe's discussions. The owner moderates as org
  owner.
- An allow-list or SHA pinning for Actions (owner, 2026-10-16). `allowed_actions` is declared as `all`, as it is.
- Turning off forking: GitHub doesn't allow it on a public repository.
- `has_downloads`: GitHub no longer uses it, and it's already off everywhere.

## Decisions

### D1. Three new module variables, defaults as most repositories have them

`has_discussions` (default `false`), `has_issues` (default `true`) and `actions_enabled` (default `true`) join
`has_wiki` and `has_projects`. troupe sets `has_discussions = true`. `.github` sets `has_issues = false` and
`actions_enabled = false`. infrastructure sets `has_projects = true`. Each override carries a comment saying why, as
`has_projects` already does.

*Alternative:* a single `features` object per repository. Rejected: it would differ from the existing flat
variables, and a typo in one field would need its own validation.

### D2. Actions declared for every repository, adopted before it's changed

The module gains a `github_actions_repository_permissions` resource, with `enabled = var.actions_enabled`,
`allowed_actions = "all"` and `sha_pinning_required = false`, matching what GitHub reports today. `allowed_actions`
is null when Actions is off, since there's nothing to allow; if the provider then plans a change on every run, it
keeps `"all"` instead, whichever plans clean. `.github` has no issues and has never run a workflow (read 2026-10-28),
so turning either off hides nothing. Four `import` blocks in `tofu/imports.tf` adopt the
current settings, so the plan shows four imports with no change for troupe, infrastructure and website, and one change
for `.github`.

Declaring it everywhere, rather than only in `.github`, is what makes Actions turned off by hand in troupe show as
drift. Destroying the resource resets Actions to on with every action allowed, which loses nothing, so it needs no
`prevent_destroy`.

### D3. The owner makes the hand-set parts before the merge

Three settings can only be set by the owner. They're made while the pull request is open, so the plan that's
approved shows only what OpenTofu changes, and the drift check is green on the first plan of `main`:

1. **Discussions in troupe, last, just before the merge.** The owner turns them on and trims the categories to Q&A,
   Ideas and Announcements (deleting General, Polls and Show and tell, and making Announcements announcement-only).
   Until the merge, `main` still declares discussions off, so every plan of `main` in between shows troupe's
   discussions turning off, and an approved apply of `main` would turn them off, hiding any posts. So this step
   comes after review, archive and the other evidence, immediately before the merge, and the owner checks any plan
   of `main` in between for that change before approving it.
2. **Private vulnerability reporting in the baseline.** The owner sets it to `enabled` in the "troupe-run baseline"
   code security configuration (D4), which turns it on in all four and in each repository created later.
   **Pull requests in `.github`** are turned off by the owner too, once the probe in D4a has passed (Settings →
   General → Features). Neither is managed by OpenTofu, so no plan of `main` undoes them.
3. **The roadmap linked to infrastructure.** The owner runs
   `gh project link 1 --owner troupe-run --repo troupe-run/infrastructure`. With projects still off there, the link
   exists but isn't shown, until the apply turns projects on.

*Alternative:* merge first, then make them. For discussions, the apply would turn them on, GitHub would create its six
default categories, and the drift check would fail until the owner trimmed them. That's safe, but the merge's own
drift job is red. Rejected for now in favour of a short window before the merge (owner may choose otherwise). For
private vulnerability reporting and the project link, OpenTofu doesn't manage either, so no plan of `main` can undo
them, and they can be done any time before the merge.

### D4. Private vulnerability reporting is an `oob.py` check, one read per repository

It's turned on by the "troupe-run baseline" code security configuration, not repository by repository (owner,
2026-10-29). The baseline had it `not_set`, which leaves each repository's own setting alone: troupe, website and
`.github` had it on by hand, and infrastructure didn't. Set to `enabled`, the baseline turns it on in every attached
repository, all four, and in each new public repository, which it's the default for. The provider has no resource
for configurations, so the owner sets it on GitHub, and `oob/code-security.json` declares it, so `oob.py` checks the
configuration too.

The baseline is unenforced, so a repository can still turn it off by itself. So each repository's own setting is
checked as well:

`oob/private-vulnerability-reporting.json` lists each managed repository with `enabled: true`. The check reads
`GET repos/troupe-run/<repo>/private-vulnerability-reporting` for each declared repository, as `code_security` reads
each repository's attachment. A refused read is an error naming the repository, never "off" (spec: org-settings,
"A refused read is an error"). A managed repository missing from the declaration isn't caught by this check; it's
caught by review, as `code-security.json`'s list is.

*Alternative:* derive the repository list from `tofu/repositories.tf`. Rejected: `oob.py` reads no HCL today, and
the list of four changes rarely.

### D4a. Pull requests and Sponsorships are an `oob.py` check, read through GraphQL

GraphQL's `Repository` has `hasPullRequestsEnabled` and `hasSponsorshipsEnabled`, and `updateRepository` sets both;
provider 6.13.0 has neither (read 2026-10-28, when both read `true` and `false` respectively in all four).
`oob/repository-features.json` declares, for each managed repository, `hasPullRequestsEnabled` (`false` for
`.github` only) and `hasSponsorshipsEnabled` (`false` everywhere). The check reads each declared repository with one
GraphQL query, so a refused read is an error naming the repository, never "off".

**Why pull requests are off in `.github`:** its "app only" ruleset lets only the infrastructure App change `main`,
by commits through the contents API, and every file there is written from `org-profile/` here (spec: org-profile,
rulesets). A pull request opened there could never merge, and an apply would overwrite it if it did. A fix to those
files is a pull request to `org-profile/` in this repository.

The owner turns it off by hand (D3). Before that, the App's way of writing (a commit through the contents API) is
tried on an `infra-probe-*` repository with pull requests off, to show it doesn't depend on pull requests. If it does,
`.github` keeps them on and the declaration says why.

**Probe result (2026-10-28, `infra-probe-20261028-prs`, since deleted):** REST's `has_pull_requests=false` turned
pull requests off (GraphQL then read `hasPullRequestsEnabled: false`). A commit through the contents API
(`PUT .../contents/probe.txt`) then landed on `main`. A branch pushed with git could not be proposed:
`gh pr create` was refused with "does not have the correct permissions to execute `CreatePullRequest`", for the org
owner too. The commit was made with the owner's login, not the App's: what it shows is that a contents-API commit
doesn't need pull requests, which is how the App writes.

*Alternative:* Sponsorships noted as unmanaged, as the issue guessed. Rejected: it has an API, so it's checked
like the other features the provider can't set.

### D5. Discussion categories are an `oob.py` check, and the App gets Discussions: read

`oob/discussion-categories.json` declares troupe's categories by `name`, with `slug` and `isAnswerable`. It's a
`Check` like issue types, reading `repository(owner: "troupe-run", name: "troupe") { discussionCategories }` through
GraphQL. Category descriptions and emoji are left to the owner and not checked: they're wording, and the issue asked
only which categories there are.

Whether a category is announcement-only can't be read through any API, so it isn't checked. `oob/README.md` says so.

CI's drift job reads as the infrastructure App, which has no Discussions permission. The owner grants
**Discussions: read** to the App before the merge, and `oob/app-installations.json` declares it, as "Issue types:
read" was declared (oob/README.md). Without it, the read is refused, which the check reports as an error.

### D6. Issues off in `.github`, verified on a repository that uses its forms

GitHub takes an org's default issue forms from the `.github` repository's default branch, not from its issue
tracker, so turning its issues off shouldn't affect the other repositories. That can't be tried on a throwaway
repository, since the forms are the org's. So the apply is verified on the live org at once: the new-issue page of
infrastructure must still offer the Feature, Bug and Decision forms and the new contact link. If it doesn't, a pull
request sets `has_issues` back to `true` on `.github` straight away, and the requirement goes back to the owner.

### D7. Questions go to troupe's Q&A

The org's `config.yml` gains a contact link: name "Ask a question", URL
`https://github.com/troupe-run/troupe/discussions/categories/q-a`, about "Questions about troupe, or how to
contribute: ask in troupe's discussions." `blank_issues_enabled` stays `true`. The link shows in every repository
that uses the org's forms, which today is all three besides `.github`. That's intended: a question about any of them
is a question about troupe.

`org-profile/CONTRIBUTING.md` gets a short "Questions" section before "How work flows", saying to ask in troupe's
discussions, not in an issue.

### D8. Members can't create Pages sites

`tofu/org.tf` sets `members_can_create_pages`, `members_can_create_public_pages` and
`members_can_create_private_pages` to `false` (owner, 2026-10-28). The only member is the owner, and the website's
site already exists and is managed by its own declaration.

GitHub's documentation says restricting this doesn't unpublish an existing site. Whether it stops the website's
deploys from Actions, or stops the App from changing the site's settings, isn't stated. It can't be tried on a
throwaway repository without changing the live org setting. So the apply is checked straight away: the website's
deploy job is re-run on `main`, and the next plan shows no change to `github_repository_pages`. If either fails, a
pull request restores the public setting, and the choice goes back to the owner.

### D9. What can't be managed is listed in `oob/README.md`

A new section, "Not managed", lists the repository home page's Releases, Packages and Deployments panels: each is a
setting on GitHub's website only, with no API field (GraphQL's `Repository` and `UpdateRepositoryInput` checked
2026-10-28), so neither OpenTofu nor `oob.py` can see it. It also notes that forking can't be turned off for a public repository, and that a discussion category's
announcement-only format can't be read.

## Risks / Trade-offs

- [Issues off in `.github` stops the org's forms reaching other repositories] → D6: checked on the live org right
  after the apply, with the revert ready.
- [Members' Pages off breaks the website's deploys or its Pages settings] → D8: the deploy is re-run and the next plan
  read straight after the apply, with the revert ready.
- [Between turning troupe's discussions on by hand and the merge, every plan of `main` turns them back off, and an
  approved apply would hide any posts and fail the categories check] → D3: the step is the last before the merge,
  so the window is minutes, and the owner checks any plan of `main` in that window for that change before approving
  it. Turning discussions off hides posts but doesn't delete them; turning them on again restores them.
- [A category's announcement-only format changed by hand goes unseen] → No API can read it. Noted in
  `oob/README.md`; accepted.
- [The App gains a permission] → Read-only, used only by the drift check, and declared in
  `oob/app-installations.json`, where a change shows as drift.

## Migration Plan

1. Merge order: the probe and then pull requests off in `.github` (D4a), private vulnerability reporting, the project
   link (D3) and the App's Discussions: read (D5) any time
   before the merge; troupe's discussions and categories last, immediately before the merge (D3).
2. The apply imports the four Actions settings, turns off `.github`'s Actions and issues, turns on infrastructure's
   projects, sets the org's Pages settings, and delivers `config.yml` and `CONTRIBUTING.md` to `.github`.
3. Checked straight after: D6 (the forms and contact link on infrastructure), D8 (website deploy and a clean plan),
   and the drift job of the next plan of `main`.

**Rollback:** each setting is a declared value. A pull request reverting it, applied, restores it. Nothing here
deletes data: a repository's issues and discussions are kept by GitHub while the feature is off.
