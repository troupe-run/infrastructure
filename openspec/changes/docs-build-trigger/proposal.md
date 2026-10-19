# Proposal

## Why

troupe-run/troupe#120 decided that everything under troupe.run's `/docs` comes from troupe, and that the website
rebuilds on every push to troupe's `main` and on every new `troupe-v*` tag, with troupe's workflow notifying it. A
workflow in troupe can't start one in troupe-run/website with its own `GITHUB_TOKEN`, which covers only its own
repository. So troupe needs a credential that can start the website's build and can do nothing else, declared here
(#109).

## What Changes

- Give troupe's workflows a credential that can start a run of a workflow in troupe-run/website. It's an App
  installation token, minted in the run from the App's private key, like the release and board Apps.
- The trigger is a `workflow_dispatch` event, which needs the repository permission "Actions: write". A
  `repository_dispatch` event would need "Contents: write", which can also push branches and tags to the website
  (design D2).
- **Recommended, for the owner to confirm (design D1):** a new App, `troupe-run-docs`, with only "Actions: write" on
  repositories (plus the metadata read GitHub always grants), installed on troupe-run/website only. The alternatives
  are widening the release App to website, or using the infrastructure App, whose key would then sit in troupe.
- Declare a `docs` environment on troupe-run/troupe that only `main` may use and that no admin can bypass. The App's
  key is held only as that environment's secret, `DOCS_APP_PRIVATE_KEY`. The owner sets it from 1Password with a
  documented command that prints nothing. OpenTofu never holds or sets it.
- `main`-only is enough for tags too: release-please creates each `troupe-v*` tag inside troupe's release workflow,
  which runs on `main`. So the sending step for a new tag runs there, not in a run on the tag (design D3).
- Declare the App's client ID as the repository variable `DOCS_APP_CLIENT_ID` on troupe.
- Record the App's installation in `oob/app-installations.json` and `oob/README.md`, so the drift check notices if it
  gains a permission or a repository. Add the `docs` environment to the main-only test.
- Prove the permission on a throwaway repository before anything is applied: a token with only "Actions: write"
  starts a `workflow_dispatch` run, and can't write contents (design D5).
- **Not in this change:** the website's workflow accepting the trigger, and troupe's step that sends it. #109's
  outcome lists the website's side, but troupe-run/website#23 (written after it) says it "owns both ends of the
  trigger": the website's side and the sending step in troupe's workflows, through their own pull requests. This
  change hands that work the constraints it needs (design D4).

## Capabilities

### New Capabilities
- `docs-build-credentials`: the credential troupe's workflows use to start the website's docs build. That covers the
  App's installation and permissions, the main-only environment on troupe that holds its key, and the variable that
  names the App.

### Modified Capabilities
<!-- None. teams-and-access's drift check already covers every row in oob/app-installations.json, and the main-only
     test is named by each credential spec; this adds a row and an entry, not a requirement. -->

## Impact

- `tofu/`: a new `docs.tf` with troupe's `docs` environment, its `main`-only deployment policy and the
  `DOCS_APP_CLIENT_ID` variable. The infrastructure App already writes environments and variables on troupe.
- `oob/app-installations.json` and `oob/README.md`: the new App's row, its repository, and its setup steps.
- `scripts/tests/test_main_only_environments.py`: `("repo_troupe", "docs")` joins `MAIN_ONLY`, and `tofu/docs.tf`
  joins the files it reads.
- `README.md`: `tofu/docs.tf` in the layout table.
- GitHub, by hand (owner): create the App, install it on website, store its key, and set the secret after the apply.
- troupe-run/website#23: uses the credential, under the constraints in design D4.
