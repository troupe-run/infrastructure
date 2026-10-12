# Tasks

## 1. The rename and this repository's references (D1, D3)

- [ ] 1.1 Set `name = "website"` in `module "repo_website"`, and the two import IDs in `tofu/imports.tf`. Verify:
  - `scripts/check.py` passes;
  - a local plan shows exactly the repository renamed in place, the ruleset updated in place, and the labels
    replaced (D2).
- [ ] 1.2 Update the references in `oob/README.md`, `org-profile/CONTRIBUTING.md` and the guard test's example
  repository. Verify:
  - `scripts/check.py` passes;
  - `git grep troupe-run.github.io` outside `openspec/changes/archive` and the state finds only the delta specs' "renamed
    from" wording;
  - a local plan adds exactly the one `.github` file update to 1.1's changes.

## 2. The pull request (D4 step 1)

- [ ] 2.1 Open the pull request (`Closes #4`). Verify:
  - every check is green;
  - after the owner approves the PR plan run, its comment shows the D4 step 1 changes and nothing else.
- [ ] 2.2 Open the website repository's pull request for its three references (`README.md`, `astro.config.mjs`'s
  `editLink`, the footer's "Site source"), with a note to merge it only after the rename is applied. Verify: its
  checks are green, and its diff touches only those three references.

## Workflow follow-up

- Archive on the branch before the merge, syncing the `repositories` and `rulesets` deltas.
- **After the owner merges:**
  - Re-check that no website issue or PR carries a label (D2).
  - The owner approves the CI apply. Check:
    - the apply succeeds;
    - the App's state commit lands (the first live `commit_state.py` run);
    - the `.github` sync commit is named `chore: sync CONTRIBUTING.md <hash> from troupe-run/infrastructure`;
    - Pages keeps `cname: troupe.run` and HTTPS enforced;
    - https://troupe.run answers 200, and www redirects.
- **After the website PR merges:**
  - its deploy succeeds, and the site checks pass again;
  - rename `~/Projects/troupe/troupe-run.github.io` to `~/Projects/troupe/website`, and set its `origin` to
    `troupe-run/website`.
- Comment on #4 and close it; tick `rename-website` on #1.
