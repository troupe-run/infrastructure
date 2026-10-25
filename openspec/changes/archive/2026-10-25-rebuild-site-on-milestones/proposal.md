# Proposal

## Why

troupe.run's `/status/` lists the release milestones. The website's build reads them from `tofu/milestones.json` on
this repository's `main` (troupe-run/website#32, its `roadmap` spec). But the website rebuilds only on a merge to the
website or a push to troupe's `main`, so a renumbered or re-described milestone stays out of date on the page until
something else happens to deploy it (#124).

## What Changes

- A new workflow here, on every push to `main` that changes `tofu/milestones.json`, dispatches troupe-run/website's
  `deploy.yml` on `main` with no inputs. It's the same notice troupe's release workflow sends after each push to its
  `main` (website spec `build-and-deploy`). A push that doesn't change the file starts nothing.
- The job that sends it checks out nothing, has no `GITHUB_TOKEN` permissions, and mints a token that can only start
  the website's workflows.
- **Reuse the existing `troupe-run-docs` App (owner, 2026-10-25, design D1),** which already does exactly this for
  troupe: "Actions: write" on website only, and nothing else. Its installation doesn't change. Its key gets a second
  home, a `docs` environment on infrastructure limited to `main` with no admin bypass, as the board App's key already
  has (`board` on website and on infrastructure).
- Declare that environment, its `main`-only deployment policy and the `DOCS_APP_CLIENT_ID` variable on infrastructure
  in `tofu/docs.tf`, and add the environment to the main-only test.
- The owner sets `DOCS_APP_PRIVATE_KEY` on infrastructure's `docs` environment from the same 1Password item, with a
  documented command that prints nothing. OpenTofu never holds it.
- The trigger is the file on `main`, not the apply: the website reads the file's text, not the milestones on GitHub
  (design D2).

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `milestones`: a new requirement, that a change to the declared milestones on `main` rebuilds troupe.run, and that
  no other push does.
- `docs-build-credentials`: the docs App's key and client ID are also held on infrastructure, in a `docs` environment
  limited to `main`, for the milestones notice. Its installation and permissions are unchanged.

## Impact

- `.github/workflows/milestones-notice.yml`: new. One job, `notify troupe.run`.
- `tofu/docs.tf`: infrastructure's `docs` environment, its `main`-only policy, and `DOCS_APP_CLIENT_ID` there. The
  infrastructure App already writes environments and variables on infrastructure (the `board` precedent).
- `scripts/tests/test_main_only_environments.py`: `("repo_infrastructure", "docs")` joins `MAIN_ONLY`.
- `scripts/tests/test_milestones_notice_workflow.py`: new. Pins the workflow's trigger, permissions, environment and
  token.
- `oob/README.md` (the docs App section) and `README.md` (layout table): the second home of the key, and the new
  workflow.
- GitHub, by hand (owner): set `DOCS_APP_PRIVATE_KEY` on infrastructure after the apply that creates the environment.
- troupe-run/website: no code change, since its deploy already accepts a dispatch on `main` with no inputs. A website
  issue documents the second sender in its `build-and-deploy` spec and `deploy.yml` header (owner, 2026-10-25,
  design D7).
