# Design

## Context

- **The site** is an Astro + Starlight build, deployed by `deploy.yml` to Pages (`build_type: workflow`):
  - `cname: troupe.run`, `https_enforced: true`;
  - `site: 'https://troupe.run'` in `astro.config.mjs`, with no `base`, so nothing in the build depends on the
    repository's name;
  - the deploy runs on `workflow_run` after CI on `main`, through the `github-pages` environment, and has no manual
    trigger.
- **Before the change (2026-10-12):** https://troupe.run answers 200, and https://www.troupe.run answers 301 to it.
- **What a rename plans** (a local plan on this branch, with `name = "website"`):

  | Resource | Action | Why |
  |---|---|---|
  | `github_repository.this` | in place | `name` isn't a replace attribute |
  | `github_repository_ruleset.main` | in place | `repository` updates in place |
  | `github_issue_labels.this` | **replace** | `repository` forces replacement |

- **References to the old name:**
  - here: `tofu/repositories.tf`, `tofu/imports.tf`, `oob/README.md`, `org-profile/CONTRIBUTING.md`, two specs, and
    a guard test's example;
  - in the website repository: `README.md`, `astro.config.mjs` (`editLink`) and `src/content/copy/footer.md` ("Site
    source").
  - troupe has none.
- **How it applies:** changes now reach the org through `ci-apply`, so the PR is planned in CI and the merge is
  applied in CI after the owner approves it. That apply's state commit is the first live run of
  `scripts/commit_state.py` (#11).

## Goals / Non-Goals

**Goals:**
- The repository is `website`, and https://troupe.run serves throughout.
- The ruleset never lapses.
- No issue, PR or label assignment is lost.
- Every current reference uses the new name.

**Non-Goals:**
- Rewriting history: archived changes and old plans keep the old name, and GitHub redirects the old URLs.
- Testing the Pages behaviour on a throwaway repository. A custom domain can belong to only one repository, so
  `troupe.run` can't be attached to a probe. D4 makes the live change easy to watch and to undo instead.

## Decisions

### D1. One declaration change; the imports follow

`name = "website"` in `module "repo_website"`. The import IDs in `tofu/imports.tf` become `"website"` too:
- an import block for a resource already in state does nothing;
- the IDs matter only when the state is rebuilt (README, "The state passphrase"), and then they must name the
  repository as it is.

The module's address, `module.repo_website`, already says "website", so there's no `moved` block.

### D2. Accept the labels' replacement

Replacing `github_issue_labels` deletes the repository's labels and creates them again with the declared names and
colours. Anything that carried one would lose it. On 2026-10-12, none of the website repository's 2 issues and PRs
carries a label, so the replacement loses nothing.

The way to keep the existing labels would be to forget the resource (`removed`, `destroy = false`) in one apply and
import it under the new name in a second. That's two CI applies, and a window in which the labels aren't managed.
It isn't worth it for labels nobody uses.

Before approving the apply, the run is re-checked: if a label has been used since, stop and do the two-step instead.

### D3. The `.github` sync

`org-profile/CONTRIBUTING.md` links the website repository, so the same apply makes a sync commit into `.github`. It
is named `chore: sync CONTRIBUTING.md <hash> from troupe-run/infrastructure`, as `development-workflow` set up. This is
the first content sync since that fix, and its message is checked after the apply.

### D4. Order, and how to undo it

1. **This PR** carries the rename and this repository's references. CI plans it, after the owner approves the run.
   Expect:
   - 2 resources changed in place, the repository and its ruleset;
   - 1 replaced, the labels;
   - 1 `.github` file updated.
2. **The owner merges, then approves the apply** in CI. The App commits the state, the first live run of
   `commit_state.py`.
3. **Check the site straight away:**
   - `gh api repos/troupe-run/website/pages` shows `cname: troupe.run` and `https_enforced: true`;
   - https://troupe.run answers 200, and www redirects.

   The existing deployment should go on serving: Pages keeps the site's settings across a rename.
4. **The website PR** (its three references) is merged by the owner. Its CI and deploy then republish from the renamed
   repository, and the site is checked again.
5. **The local folder** is renamed, and the clone's `origin` is updated to `troupe-run/website`. GitHub redirects the
   old remote URL, but it shouldn't be left relying on that.

**To undo it:** if the site stops serving at step 3 and a redeploy at step 4 doesn't bring it back, set
`name = "troupe-run.github.io"` again in a follow-up PR. That's the same kind of in-place rename, and GitHub restores
the org-site name and its URL.

## Risks / Trade-offs

- **[Pages doesn't carry the custom domain across the rename]** → checked at step 3. If `cname` is lost, the owner can
  set it again with `gh api -X PUT repos/troupe-run/website/pages -f cname=troupe.run` while the fix-forward is
  prepared. The DNS records stay valid for a project site.
- **[A label is used before the apply]** → re-checked before approving (D2).
- **[The first live state commit fails]** → the run keeps the state as an artifact, and the README's break-glass path
  recovers it, as it did for #11.
- **[Links to the old URLs]** → GitHub redirects repository URLs after a rename. Only the bare
  `https://troupe-run.github.io/` stops serving the site.
