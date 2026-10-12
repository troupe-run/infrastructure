# Proposal

Issue: #14 (part of #1, step 5). The owner's decisions of 2026-10-12, made when this change was proposed, are
recorded in design.md (D1, D2, D4, D7) and
[on #14](https://github.com/troupe-run/infrastructure/issues/14#issuecomment-6119985296).

## Why

`main` is protected on every managed repository (`protect-main`), but nothing has to pass before a pull request
merges. CI, the `guard` check and DCO run on every pull request, and a red one can still be merged. The guard's own
docs already promise that it "can't be merged once `required-checks` makes it required". `troupe-run/.github` has no
ruleset at all, so anyone with write access can edit files whose source is this repository. adopt-org also left four
findings for this change. Each is a repository setting that disagrees with how the org works.

## What Changes

- **Required checks on `main`,** added to each repository's existing `protect main` ruleset. Each check is pinned to
  the App that posts it.
  - **`infrastructure`:** `check`, the five `guard tests (<os>, Python <v>)` jobs, `guard (workflow rules)`, `DCO`,
    and `plan (pull request)`.
  - **`troupe`:** the six `check (<os>, Python <v>)` jobs, `guard (workflow rules)` and `DCO`.
  - **`website`:** `test`. DCO isn't installed there.
- **The names live in one file, `tofu/required-checks.json`.** OpenTofu reads it, and a test compares
  `infrastructure`'s entry with the jobs its workflows actually define, matrix legs included. troupe and website
  can't be read offline from here, so their entries aren't tested. A wrong name there blocks merging rather than
  letting a PR through.
- **The pull request's plan becomes required on `infrastructure`.** A pull request that changes only files OpenTofu
  never reads (`openspec/`, `docs/`, tests, and so on) skips the plan job. A skipped job passes and asks the owner for
  no approval. Every other pull request waits for the owner to approve its plan run, and needs a successful plan
  before it can merge.
- **A ruleset for `troupe-run/.github`:** only the infrastructure App may change `main`, with no bypass for anyone
  else. The owner's break-glass is editing the ruleset, as it is for every ruleset. Each of `.github`'s files gains a
  note saying it is written from `troupe-run/infrastructure` and changed there.
- **adopt-org's findings, in repository settings on all four repositories:**
  - merge commits and squash merges turned off, so the settings agree with the rebase-only ruleset;
  - branches deleted on merge;
  - the wiki turned off. No repository has a wiki.
  - classic projects turned off, except on `troupe` if the probe shows that turning them off affects the org
    roadmap, which is linked to `troupe`.
- **The unused read-only plan App (`troupe-run-infrastructure-plan`) is deleted** by the owner. Its declarations go
  from `oob/` and from the rulesets spec.

Out of scope:
- the remaining org-settings findings (2FA, members creating repositories), which are a later change;
- installing DCO on `website`;
- stopping an agent that holds the owner's credentials from merging a red pull request with `gh pr merge --admin`
  (see design, Risks);
- GitHub Pages settings.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- **`rulesets`:**
  - pull requests into `main` need the repository's required checks to pass;
  - `.github` gets its own ruleset, under which only the App changes `main`;
  - the scenario naming the read-only plan App goes with the App.
- **`ci-apply`:** a pull request's plan is a required check, and is skipped for a pull request that changes nothing
  OpenTofu reads.
- **`repositories`:** each repository allows only rebase merges, deletes branches on merge, and turns off the wiki
  and unused classic projects.
- **`org-profile`:** each file in `.github` says it is changed in this repository.
- **`teams-and-access`:** the read-only plan App leaves the declared installations.

## Impact

- **Changed:**
  - `tofu/modules/repository` (required checks; an App-only ruleset mode; new setting defaults);
  - `tofu/repositories.tf`;
  - a new `tofu/required-checks.json`;
  - `org-profile/*` (the note);
  - `.github/workflows/tofu.yml` (a job that decides whether to plan);
  - `scripts/tests` (the check-name test and the plan-skip test);
  - `pyproject.toml` (PyYAML and its stubs, for tests only; the guard stays standard library only);
  - `oob/app-installations.json`, `oob/README.md`;
  - `README.md` and `docs/development-workflow.md` (the guard is now required).
- **GitHub:**
  - four rulesets: three changed, one new;
  - four repositories' merge and feature settings;
  - four commits by the App to `.github`;
  - one App deleted.
- **Probe:** a throwaway repository (and a throwaway org project) to show, before anything live changes, that:
  - the App's bypass still pushes past required checks;
  - the owner's pull-request bypass merges past a failing check;
  - an App-only ruleset refuses everyone else;
  - turning off classic projects leaves a linked org project alone.
- **The owner, by hand:** deletes the plan App and its 1Password item; approves the plans and the apply.
