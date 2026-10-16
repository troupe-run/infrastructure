# Design: declare the release milestones in every managed repository

## Context

See proposal.md for why. What shapes the approach:

- **Live state, read 2026-10-17:** troupe has one milestone, number 1, `alpha-0`, open, no due date, description
  "Walking skeleton: troupe perform runs one actor end to end; status and logs read from projections", with 3 closed
  issues (troupe#18, #22 and #23). infrastructure, website and `.github` have none. No troupe release has been made
  yet: release-please's PR, troupe#89, is open.
- **Provider:** integrations/github 6.13.0 has `github_repository_milestone` (owner, repository, title, description,
  due date, state). One resource is one milestone in one repository. Unlike `github_issue_labels`, nothing in the
  provider manages a repository's whole set of milestones, so an apply can't see a milestone it doesn't declare.
- **Precedents here:** labels are declared as JSON in `tofu/labels/` and read with `jsondecode`. `oob.py` checks what
  OpenTofu can't see, from a declaration in `oob/` or one derived from a source this repository already holds (the
  `.github` files from `org-profile/`). Adoption is by `import` block in `tofu/imports.tf`, proved by a plan that
  imports and changes nothing it shouldn't.
- **Permissions:** milestones need `issues: write`, which the infrastructure App already has on every managed
  repository (`oob/app-installations.json`).
- **The board:** the troupe roadmap (project 1) has GitHub's built-in Milestone field. Its group-by shows milestones by
  title across repositories, which is why the titles must match exactly.

## Goals / Non-Goals

**Goals:**
- One declaration of the release milestones, applied identically to every managed repository.
- No apply can delete a milestone or take an issue out of one.
- A milestone made by hand is reported, since no plan will show it.

**Non-Goals:**
- Assigning issues to milestones. That's triage, done on GitHub (the first sweep is recorded on #68).
- Due dates. None are set, and the declaration can add them later without a design change.
- Closing a milestone from troupe's release workflow.

## Decisions

### D1. One declaration, `tofu/milestones.json`, with a stable key for each milestone

```json
{
  "repositories": ["troupe", "infrastructure", "website", ".github"],
  "milestones": [
    {"key": "0.1.0", "title": "0.1.0", "state": "open", "description": "..."},
    {"key": "0.2.0", "title": "0.2.0", "state": "open", "description": "..."},
    {"key": "1.0.0", "title": "1.0.0", "state": "open", "description": "..."}
  ]
}
```

The `key` names the milestone's OpenTofu address and never changes. The title can. Releases get reshuffled (the owner
expects to move things between them), and if the resource were keyed by title, a rename would be a destroy and a
create: the old milestone would be deleted and every issue in it would lose its milestone. With a stable key, a rename
is an in-place update. Each key starts out equal to its title, for readability, and a comment in the file says the
key is never changed.

- Not a variable on the `repository` module, like labels: the milestones must be identical everywhere, so passing the
  same list into four module calls would only be four places to forget. One top-level resource over
  `repositories × milestones` makes "every listed repository gets every milestone" true by construction.
- Not in `oob/`: OpenTofu manages the milestones themselves. `oob.py` reads this same file to know what's declared,
  as it derives the `.github` files from `org-profile/`, so there's no second list.

### D2. `tofu/milestones.tf`: one resource, `for_each` over each repository and milestone, never destroyed

`github_repository_milestone.release` has one instance per (repository, key), addressed `"<repository>/<key>"`. Its
`lifecycle` sets `prevent_destroy = true`. Removing a milestone from the declaration then fails the plan instead of
deleting the milestone. Retiring a milestone means setting its state to `closed`. If a milestone really must be
deleted, that's a deliberate change that removes the guard in the same diff, where review can see it.

Descriptions (no due dates):

- **0.1.0:** alpha-0's description, unchanged: "Walking skeleton: troupe perform runs one actor end to end; status
  and logs read from projections".
- **0.2.0:** "Actors defined in config, run through Claude Code on a local worktree stage".
- **1.0.0:** "The first stable release: roles, gates, the house and plugins; split into earlier releases as work comes
  up".

These describe troupe's releases, and the copies in infrastructure, website and `.github` say the same thing on
purpose: an issue there is filed under the troupe release it serves.

### D3. Adopt alpha-0 by import, then rename it in the same plan

An `import` block adopts troupe's milestone 1 as `github_repository_milestone.release["troupe/0.1.0"]`. Its declared
title is `0.1.0`, so the first plan shows that import with an in-place title change, the other 11 milestones
created, and nothing destroyed. Unlike website-environment's two commits, this doesn't adopt first and change
second: the rename is the owner's decision (2026-10-17), and the plan shows the import and the change together. Its
summary line must read `1 to import, 11 to add, 1 to change, 0 to destroy`.

Two facts are proved on a throwaway repository before this plan is trusted, because the spec depends on them:

1. The import ID's format (the provider's documentation gives `<owner>/<repository>/<number>`).
2. A title change is an in-place update that keeps the milestone's number and its issues, not a replacement. If the
   provider replaces on a title change, D1's rename-in-place doesn't hold, and the change stops and goes back to the
   owner.

The same throwaway repository also proves that the plan shows drift when a title is changed by hand.

### D4. `check.py` keeps the declaration honest

Two tests in `scripts/tests/`:

- **The repository list matches the managed repositories:** the names passed to each `module "repo_*"` in
  `tofu/repositories.tf` equal `milestones.json`'s `repositories`. A failure names each repository that's in one and
  not the other, and the file to change.
- **The declaration is well formed:** keys and titles are unique, and each state is `open` or `closed`. A failure
  names the milestone and what's wrong. An unknown state is an error rather than a default.

### D5. `oob.py` reports a milestone that isn't declared

A new check, for each repository in `milestones.json`, reads `repos/troupe-run/<repo>/milestones?state=all` and
reports each title on GitHub that isn't declared, as `milestones: <repo>: '<title>' is on GitHub but not declared;
declare it in tofu/milestones.json`. It's one way, like the spec-label check: a declared milestone that's missing or
different is the plan's business, not the drift check's. A repository it can't read is an `UnreadableError`, not
"no milestones".

## Risks / Trade-offs

- **A rename by hand between plans.** Someone renames 0.2.0 on GitHub, so the board briefly shows two groups. →
  The daily plan of `main` shows the title changing back, and the apply restores it.
- **The provider replaces on a title change.** → D3 proves it on a throwaway repository first, and the change stops
  if it does.
- **`.github` gets milestones it may never use.** → They cost nothing, and keeping the list equal to the managed
  repositories means nobody has to decide again for each new repository.
- **The milestones describe troupe's releases, not infrastructure's.** infrastructure and website don't release.
  Filing their issues under the troupe release they serve is the point: the board shows one roadmap.

## Migration Plan

1. Prove D3's two facts on a throwaway repository, then delete it.
2. Add the declaration, the resource and the import. `tofu fmt` and `tofu validate` must pass. Run a local plan, and
   check that it shows exactly the summary in D3.
3. Add the check.py tests and the oob.py check, with their tests.
4. Open a pull request. CI posts the plan. The owner approves the apply after merge.
5. After the apply: check every repository on GitHub, run `oob.py`, then sweep the issues into the milestones and
   record the sweep on #68.

Rollback: the milestones are harmless if unused. To undo the rename, change troupe's `0.1.0` title back to `alpha-0`
in the declaration. The other milestones can be closed by state. Deleting any of them needs the deliberate change
D2 describes.
