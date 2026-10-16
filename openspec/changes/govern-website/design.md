# Design: govern-website

## Context

See proposal.md for why. What exists today:

- `tofu/guard_delivery.tf` delivers the guard's files to `guard_targets`, which holds only `module.repo_troupe.name`.
  Each delivery `depends_on = [module.repo_troupe]`, so the ruleset that lets the App push exists before the files
  are pushed (guard-delivery design D5). `overwrite_on_create = false`.
- `repo_website` has the `pull-request` ruleset (`protect main`), requires only `test` (its CI job, from
  `github-actions`), has no `app_bypass_id`, and `has_projects` is off. On GitHub, projects are off too, and the
  roadmap (project 1) is linked only to troupe.
- The guard has no sign-off rule. DCO is enforced only by the DCO App's check, required on troupe and this
  repository. The DCO App isn't installed on the website: its pull requests report only `test`.
- The guard needs three things from a repository it runs in. It needs `openspec/changes/` to match branches. It needs
  `scripts/check.py`, which the commit hook runs with `uv run` (10-minute limit), and whose failure line
  `check: <gate> failed` it quotes. It needs `uv` on the contributor's machine. `scripts/check-paths.toml` is
  optional and the repository's own. Without it, every commit runs the full check. In troupe and here, `check.py` also
  turns the hooks on, through `guard.activate_hooks`.
- The website's CI job `test` runs, in order, `npm ci`, a Playwright browser install, `npm run check`, `test:unit`,
  `build`, `assets:verify`, `linkcheck` and `test:e2e`. Its `deploy` workflow runs after each successful CI run on a
  push to `main`.
- Two other changes are open against the website: `website-pages` (#51) and `website-environment` (#52). Both touch
  `repo_website` or the `repositories` spec.

## Goals / Non-Goals

**Goals:**
- The website is governed exactly as troupe is, except that it has no DCO and no release process.
- No step leaves the website in a state where its own contributors can't merge a pull request, or where the guard
  runs before the website can satisfy it.

**Non-Goals:**
- Changing the guard itself. Nothing in `scripts/guard.py` is troupe-specific, and the website needs no new rule.
- Writing the website's own files from here. They arrive through the website's own pull request (fixed constraint).
- Check-path scopes in the website. A JavaScript test runner has no adapter for the guard's tag check (`TestReads`
  has only a pytest adapter), so the website declares `skip` groups only. Scopes can come later, with an adapter.

## Decisions

### D1. The website bootstraps itself first, by its own pull request

Before this change's plan is applied, a website pull request (with its own issue in `troupe-run/website`, on the
roadmap) merges:
- `openspec/`, from `openspec init`, with a project context for the site;
- a first change, on the PR's branch, which the PR itself archives. Its branch name matches a change it contains,
  so the PR passes the guard's check once that check exists;
- `scripts/check.py`, a stdlib-only uv script that runs the CI job's npm steps in the same order. It prints
  `check: <gate> failed` on a failure, and turns the hooks on through `scripts/guard.py` if it's there, as troupe's
  does;
- `scripts/check-paths.toml`, which skips at least `openspec/**`, so proposing, ticking and archiving don't run the
  site's build and e2e suite;
- the CI job `test`, which runs `uv run scripts/check.py`, so local and CI checks can't diverge. The job keeps its
  name, so the required check doesn't change;
- CONTRIBUTING.md and a CLAUDE.md: install uv, follow the workflow, Conventional Commits, no sign-off.

It must add none of the delivered paths. `overwrite_on_create = false` would fail the delivery of any it had.

*Why not deliver first?* The guard would arrive in a repository with no `openspec/` and no `check.py`. The first local
commit would be refused by the commit check, and the newly required `guard` check would refuse every pull request
until a branch carried an OpenSpec change. Bootstrapping first means the guard arrives in a repository that already
satisfies it.

### D2. One apply: bypass, required check, projects, then the files

The plan has one in-place ruleset update on `website` (the App as bypass actor, and `guard (workflow rules)` as a
required check), one in-place repository update (`has_projects`), and eight file creations. `depends_on` gains
`module.repo_website`, so the files wait for the ruleset. Between the ruleset update and `.github/workflows/guard.yml`
landing, a website pull request would wait for a check that can't yet report. That window lasts seconds, and none
is open while the apply runs. Two applies would close the window, but would cost the owner a second plan review for
no real gain.

`guard_targets` becomes `toset([module.repo_troupe.name, module.repo_website.name])`. It stays the one place that
names the receiving repositories (spec: guard-delivery).

### D3. "Without DCO" means DCO is left off, not turned off

Nothing in the guard checks sign-offs, so the website's freedom from DCO is two things. Its required checks don't list
DCO, and the DCO App isn't installed on it. This change touches neither. It records them in the `rulesets`
spec so a later change can't add DCO to the website without changing the spec. A test in
`scripts/tests/test_required_checks.py` checks that every repository that receives the guard requires
`guard (workflow rules)`. It reads `guard_targets` from `guard_delivery.tf`, so adding a target without its check
fails. The test doesn't assert anything about DCO, because the DCO entries are plain data in the same file and a test
would only restate them.

### D4. The roadmap link is checked by oob.py

OpenTofu can't link a Projects v2 board to a repository, and the guard makes `gh project link` owner-only. So the
owner links it (`gh project link 1 --owner troupe-run --repo troupe-run/website`), and `oob/projects.json` gains
`"repositories": ["troupe", "website"]`. `scripts/oob.py` reads the board's linked repositories in the same GraphQL
query, sorted by name, so an unlinked or extra repository shows as drift. `has_projects = true` gets the same reason
as troupe's. Turning projects off would hide the linked board from the repository.

### D5. Troupe-only wording is widened where it states a fact

- The `development-workflow` spec's Purpose names "this repository and `troupe`". The Purpose isn't a requirement, so
  a delta can't change it. It's edited in place, in this change's branch.
- README "Delivering the guard" and "To stop delivering" become "each repository that receives the guard". The
  stop-delivering steps name `app_bypass_id` on the repository being stopped, not `repo_troupe` alone.
- The README layout table and `docs/development-workflow.md` already say "each other governed repository" and need
  no change.

### D6. The redeploys are accepted

Each delivery commit is a push to the website's `main`. Each push runs CI, and each green run deploys. Up to eight
deploys of an unchanged site queue behind one another (`concurrency: pages`, not cancelled). That's harmless, and
it happens only on the first delivery and on later guard changes. Skipping CI for delivered paths would lose the only
check that a delivery didn't break the site's build, so the website keeps running it.

### D7. History rewrite stays outside this change

The guard checks the commits a push or pull request adds, never older history, so this change works the same whether
or not the website's 54 earlier commits are rewritten. If the owner chooses to rewrite them, it goes first: before
D1's bootstrap, while no App delivery commits exist to rewrite as well. It needs the owner's break-glass on
`protect main` (lift, force-push with committer dates kept, restore, then a clean plan). The recommendation stays
not to rewrite (issue #54).

## Risks / Trade-offs

- [The website's full check is slow, and every commit that touches the site runs it] → `check-paths.toml` skips
  `openspec/**`. D1's pull request measures the full check on macOS and records the time. If it's over the guard's
  10-minute limit, that pull request has to fix it (for example, the e2e suite's own build) before this change
  applies.
- [A contributor without `uv` can't commit to the website] → that's the same for troupe. The website's CONTRIBUTING
  says to install it, and the hook's refusal names what's missing.
- [`website-pages` and `website-environment` change the same module, spec and README] → whichever merges second
  rebases. Its plan is made after `main`'s state commit (memory: plan against current state).
- [The App's installation doesn't actually cover the website] → it manages the website's ruleset and labels today,
  so it does. The App's repository list is still confirmed by hand before the plan (teams-and-access).
- [A delivery lands while a website pull request is open] → that pull request's `guard` check reports once it next
  runs. Its branch already matches a change after D1, so it passes.

## Migration Plan

1. Owner: decide on the history rewrite (D7). If yes, it's done before step 2.
2. Website: D1's issue and pull request, merged by rebase.
3. Owner: confirm the App's installation lists `website`, and link the roadmap (D4).
4. Here: the pull request's plan shows exactly D2's changes, and `scripts/oob.py` is clean. The owner approves.
   After merge, `main`'s plan is the same, and the owner approves the apply.
5. Verify: eight App commits on the website's `main`, each with a green `guard` and CI run. The ruleset lists the
   App and both checks. A plan shows no changes. The website's next pull request shows `guard (workflow rules)` as
   required and merges without a sign-off.

Rollback is README's "To stop delivering", run for the website: drop it from `guard_targets`, using `removed`
blocks for its files, then remove its `app_bypass_id` and its `guard` required check.
