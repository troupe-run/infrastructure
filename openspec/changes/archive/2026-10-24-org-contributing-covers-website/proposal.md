# Proposal

## Why

The org's contributing guide (`org-profile/CONTRIBUTING.md`, delivered to `troupe-run/.github`) says "The website has
its own", and website's `CONTRIBUTING.md` repeats the workflow with small differences. The owner wants one guide for
every repository, so a contributor anywhere reads the same workflow, commit rules and milestone rules in one place
(#120, 2026-10-23). The org guide has to be right for website before website's own guide is deleted
(troupe-run/website#31, which waits for this).

## What Changes

- The guide's opening no longer says website has its own guide. It says it covers every troupe-run repository.
- **Licence and sign-off** becomes per repository:
  - troupe: Apache-2.0, with a DCO sign-off on each commit. Members who sign their commits cryptographically are
    excepted, as today.
  - infrastructure: Apache-2.0 and the same DCO sign-off as troupe. The licence is the owner's decision
    (2026-10-24). The sign-off is because its pull requests require the `DCO` check (`tofu/required-checks.json`).
  - website: MIT for code (`LICENSE`) and CC BY 4.0 for content (`LICENSE-CONTENT`), with no sign-off: no DCO, no
    CLA.
  - A trademark note for both troupe and website: the troupe name, logo, mark and characters are trademarks of
    HPS.GD PTY LTD and aren't covered by either licence.
- **A fix from outside** is a new section for every governed repository. A pull request made in GitHub's editor
  fails the `guard` check because it isn't on an OpenSpec change's branch. That's expected: a maintainer carries the
  fix on a change branch of their own, credits the author with `Co-authored-by:`, links the pull request and closes
  it when theirs merges.
- **How work flows** gains two things website's version has: commit messages are Conventional Commits, and the
  repository's check passes before every commit.
- A test ties the sign-off text to `tofu/required-checks.json`. Every repository whose pull requests require the
  `DCO` check must be named as taking the sign-off, and every governed repository that doesn't must be named as not
  taking it. So the guide can't drift from what the rulesets enforce.
- **infrastructure gets its licence**, set up the way troupe's is. Today it has no licence file, and GitHub reports
  none:
  - a root `LICENSE`, byte-identical to troupe's (the Apache-2.0 text);
  - `license = "Apache-2.0"` and `license-files = ["LICENSE"]` in `pyproject.toml`;
  - a `## Licence` section in `README.md`, in troupe's wording, with the trademark note.
- The same test checks that the guide's licence for infrastructure is the one `pyproject.toml` declares.

Setting up and running each repository stays in its own README. The Milestones section that `roadmap-milestones`
added is unchanged. Website-specific page notes ("Improve this page", docs pages living in troupe) stay with website
and move to its README in troupe-run/website#31.

## Capabilities

### New Capabilities

- `licensing`: the licence this repository is published under, declared in its own files and matched by the org's
  guide. A repository's licence files are neither `.github` content (`org-profile`) nor a GitHub setting OpenTofu
  manages (`repositories`).

### Modified Capabilities

- `org-profile`: adds a requirement that the org's contributing guide covers every governed repository, with each
  repository's sign-off as its rulesets enforce it and the outside-fix route.

## Impact

- `org-profile/CONTRIBUTING.md`: the text above.
- `scripts/tests/test_org_profile.py`: the sign-off and licence test.
- `LICENSE` (new), `pyproject.toml` and `README.md`: infrastructure's licence. None of them reach `.github`, so they
  add nothing to the plan.
- `troupe-run/.github`: one commit to `CONTRIBUTING.md` when `main` is applied. The plan shows only that file
  changing (`github_repository_file.org_profile["CONTRIBUTING.md"]`).
- website's own `CONTRIBUTING.md` is left as it is. Until troupe-run/website#31 deletes it, it still says the org's
  guide doesn't apply there. That's the order #120 sets.
- Builds on `roadmap-milestones` (#119), which is merged and archived, so there's no merge-order conflict left.
