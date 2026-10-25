# Proposal

Issue: #138.

## Why

On 2026-10-24 Dependabot security updates opened troupe-run/website#44, #45 and #46, and created two labels on
website for them: `dependencies` (`0366d6`, "Pull requests that update a dependency file") and `javascript`
(`168700`, "Pull requests that update javascript code"). Neither is declared, so every plan since shows
`module.repo_website.github_issue_labels.this` deleting them (first seen on #137's plan). Applying that would strip
the labels off the three open pull requests, and Dependabot would create them again on its next run. The drift would
keep coming back.

No repository has a `.github/dependabot.yml`. These are security updates, which the org's baseline code security
configuration turns on (#53). So there's no config file to point at a label we already declare. The labels have to be
declared instead.

troupe and infrastructure will hit the same drift on their first Dependabot pull request. Their dependency graphs
already list a `uv.lock` and workflows, and website's lists workflows too, which Dependabot labels with a label of
their own.

## What Changes

- **Dependabot's labels are declared** in a new set, `tofu/labels/dependabot.json`: the `dependencies` label every
  Dependabot pull request gets, and one label per package ecosystem, with the name, colour and description Dependabot
  gives it (design D1, D2).
- **Each repository gets the labels for the ecosystems its dependency graph lists** (design D3), as read on
  2026-10-25:

  | Repository | Dependency graph lists | Labels |
  |---|---|---|
  | website | `package.json`, `package-lock.json`, workflows | `dependencies`, `javascript`, `github_actions` |
  | troupe | `pyproject.toml` files, `uv.lock`, workflows | `dependencies`, `python:uv`, `github_actions` |
  | infrastructure | `pyproject.toml`, `uv.lock`, workflows | `dependencies`, `python:uv`, `github_actions` |
  | `.github` | nothing | none |

- **The names are confirmed on a throwaway repository** before they're declared (design D2). website's two labels are
  declared as they are on GitHub, so its plan shows no change to them. The uv and GitHub Actions names come from
  Dependabot's source (`dependabot/dependabot-core`). But website's live `javascript` description doesn't match what
  that source would write, so GitHub's hosted Dependabot doesn't always do what the source says. A probe repository,
  `troupe-run/infra-probe-dependabot-labels`, records what hosted Dependabot actually creates for uv and GitHub Actions.
- **`scripts/tests/test_labels.py` checks the new set**: every description is within GitHub's 100-character limit,
  and every repository's ecosystems are ones the set declares.

Out of scope:
- A `.github/dependabot.yml` in any repository. Version updates and custom labels are a separate decision. This change
  only stops the labels that security updates already create from drifting.
- A check that compares each repository's dependency graph with its declared ecosystems. A new ecosystem's label
  still shows up as drift in the next plan, as website's did. That's how this was found, and the plan already catches
  it (design, Non-goals).
- A `security` label. Dependabot's source creates one for security fixes, but website's three security update pull
  requests didn't get one, so nothing creates it here (design D2).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `labels`: adds a requirement that each managed repository's label set includes the labels Dependabot applies for
  the ecosystems its dependency graph lists, declared once with Dependabot's own name, colour and description, so
  Dependabot finds them and doesn't create its own.

## Impact

- `tofu/labels/dependabot.json` (new), `tofu/repositories.tf` (each repository's label set), and
  `scripts/tests/test_labels.py`.
- The plan creates `github_actions` on website, and `dependencies`, `python:uv` and `github_actions` on troupe and
  infrastructure. Nothing else is created, changed or deleted. website's `dependencies` and `javascript` stop showing
  as deletions.
- `README.md`'s row for `tofu/labels/` names the new set.
- A throwaway repository, `troupe-run/infra-probe-dependabot-labels`, is created and then deleted during the change.
