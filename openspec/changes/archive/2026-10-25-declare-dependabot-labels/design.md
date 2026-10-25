# Design

## Context

Each managed repository's labels are one `github_issue_labels` resource (`tofu/modules/repository/main.tf`), which
owns the full set. A label on GitHub that isn't in the set is deleted by the next apply. The sets are built in
`tofu/repositories.tf` by concatenating JSON files in `tofu/labels/`: GitHub's defaults, the workflow's labels and
the kinds of work for every repository, plus `troupe.json` and `release.json` for troupe.

How Dependabot labels a pull request, from `dependabot/dependabot-core`
(`common/lib/dependabot/pull_request_creator/labeler.rb`, read on 2026-10-25):

- With no custom labels configured, it applies a dependencies label and, for repositories with more than one
  ecosystem, a language label.
- **Dependencies label.** Any existing label matching `^[^/]*dependenc[^/]+$` (case-insensitive) counts, with an exact
  `dependencies` preferred. Only if none exists does it create `dependencies`, `0366d6`, "Pull requests that update a
  dependency file".
- **Language label.** It looks for the ecosystem's label by name, ignoring case, and creates it only if it's missing.
  The names and colours registered for the ecosystems here are `javascript` / `168700` (npm), `python:uv` / `2b67c6`
  (uv; `pip` is `python`), and `github_actions` / `000000` with "Pull requests that update GitHub Actions code"
  (GitHub Actions). With no registered description, the source writes "Pull requests that update
  `<Name capitalised>` code".
- **Security label.** For security fixes the source also creates `security` (`ee0701`).

What GitHub's hosted Dependabot did on website on 2026-10-24 doesn't fully match that source. It created `javascript`
with "Pull requests that update **j**avascript code" (lower case), and three security update pull requests got no
`security` label. So the source tells us what to expect, and the probe below confirms what's real.

The dependency graph manifests, read on 2026-10-25 with GraphQL `dependencyGraphManifests`, are in the proposal's
table.

## Goals / Non-Goals

**Goals:**
- website's plan shows no change to `dependencies` or `javascript`.
- troupe and infrastructure have the labels before Dependabot's first pull request there, so Dependabot applies ours
  and creates none.

**Non-Goals:**
- **Checking the dependency graph against the declared ecosystems.** `scripts/oob.py` could read each repository's
  manifests and report an ecosystem with no declared label. But a missing label already shows up: Dependabot creates
  it, and the next plan shows it being deleted, which is how this issue was found. A check would only catch it one
  pull request earlier, and it would need a manifest-to-ecosystem table of its own to keep up to date. It can be added
  later without changing this design.
- **Custom Dependabot labels.** A `dependabot.yml` could point Dependabot at labels we choose. That would need a
  config file in each repository, delivered as a pull request through its own checks, for something declaring the
  defaults already does.

## Decisions

### D1. One set, keyed by ecosystem, with each repository's ecosystems beside it

`tofu/labels/dependabot.json` holds three things:

```json
{
  "dependencies": { "name": "dependencies", "color": "0366d6", "description": "Pull requests that update a dependency file" },
  "ecosystems": {
    "github-actions": { "name": "github_actions", "color": "000000", "description": "Pull requests that update GitHub Actions code" },
    "npm": { "name": "javascript", "color": "168700", "description": "Pull requests that update javascript code" },
    "uv": { "name": "python:uv", "color": "2b67c6", "description": "Pull requests that update python:uv code" }
  },
  "repositories": {
    ".github": [],
    "infrastructure": ["github-actions", "uv"],
    "troupe": ["github-actions", "uv"],
    "website": ["github-actions", "npm"]
  }
}
```

The ecosystem keys are Dependabot's own `package-ecosystem` names, the ones a `dependabot.yml` would use. These keys
aren't the label names: `github-actions` becomes `github_actions`. `repositories.tf` builds a map of each
repository's Dependabot labels from the file (`dependencies`, plus each of its ecosystems' labels) and adds that to
each module's `labels`, after the kinds of work.

Every managed repository has an entry, including `.github` with none, and each module reads its own entry by index.
A repository missing from the file fails the plan. It doesn't quietly get no labels. An ecosystem that isn't declared
fails the plan too, and `scripts/check.py` names it first (D4).

Alternatives:
- **Each repository's ecosystems in `repositories.tf`, next to its module.** That's closer to the module, but then
  the test in D4 would have to parse HCL to check them. Keeping the mapping in the JSON puts all of Dependabot's
  labelling in one file.
- **One flat list of labels that every repository gets.** That's simpler, but `.github` would get `dependencies` and
  infrastructure would get `javascript`, labels nothing applies there. The spec's sets are each repository's real
  labels, so a label nothing uses would be noise.
- **A file per repository.** That repeats `dependencies` and `github_actions` three times, so a colour fix would mean
  three edits.

### D2. The values are what GitHub's Dependabot creates, confirmed on a probe repository

`dependencies` and `javascript` are declared exactly as they are on website (colour lower case, as GitHub returns
it), so adopting them changes nothing. That's the labels spec's "adopted labels match GitHub exactly" rule.

The uv and GitHub Actions labels haven't been created anywhere in the org yet. Only the **name** matters to
Dependabot, which looks a label up by name, ignoring case. But a wrong name means Dependabot creates its own, and the
drift is back. Since the hosted service already differed from the source once, the names are read from what it
does:

1. Create `troupe-run/infra-probe-dependabot-labels` (public, so security updates run on the Free plan), holding a
   `pyproject.toml` and a `uv.lock` that pin one dependency with a known advisory (for a security update) and one
   that's only out of date (for a version update), and a workflow on an old major version of an action, triggered
   only by `workflow_dispatch` so it never runs.
2. Turn on Dependabot security updates, and add a `.github/dependabot.yml` for `uv` and `github-actions` version
   updates so the GitHub Actions label appears without needing a vulnerable action.
3. Read each Dependabot pull request's labels, and `gh label list --json name,color,description`.
4. Delete the repository.

The declared values are the probe's, wherever it differs from the source. If uv's security update uses a different
name from its version update, both are declared for the `uv` ecosystem (the file's ecosystem value becomes a list),
and the spec scenario's names are updated to match. If the probe gets a `security` label, it's declared with
`dependencies`, since then every repository would get it. If the probe can't get a pull request for an ecosystem
within a day, the source's values are declared and the PR says so.

**What the probe found (2026-10-25).** Dependabot opened a GitHub Actions version update and two uv version updates.
It created `dependencies` (`0366d6`), `github_actions` (`000000`, "Pull requests that update GitHub Actions code")
and `python:uv` (`2b67c6`, "Pull requests that update python:uv code"). The names and colours match the source. The
`python:uv` description doesn't: hosted Dependabot writes the name as it is, not capitalised, just as it did for
website's `javascript`. No `security` label was created. `requests`'s advisories opened six alerts, but its version
update already fixed them, so no separate uv security update was opened. The security path's labels are therefore the
ones website#44, #45 and #46 show: `dependencies` and the ecosystem's label, with no `security`. D1 holds the observed
values.

### D3. Ecosystems come from the dependency graph, not from guessing

A repository gets an ecosystem's label when its dependency graph lists a manifest for that ecosystem. Security
updates are raised only for what the graph sees. `.github` lists nothing, so it gets no Dependabot label. troupe's
package `pyproject.toml` files belong to the workspace's single `uv.lock`, so they're uv, not pip. infrastructure's
Python is the same. Every repository with workflows gets `github_actions`, since GitHub Actions advisories raise
security updates too.

### D4. `scripts/check.py` checks the set offline

GitHub refuses a description over 100 characters only at apply time, after the merge. So `test_labels.py` checks
the set, the same way it checks `kinds.json` and `release.json`:

- every declared Dependabot label's description is within the limit, and an over-limit one is named with its length;
- every ecosystem a repository lists is declared, and an undeclared one is named with its repository;
- the file's repositories are exactly the managed repositories (`name = "…"` in `tofu/repositories.tf`'s
  `module "repo_*"` blocks), so a misspelt or missing entry fails before the plan does.

## Risks / Trade-offs

- **[Hosted Dependabot changes a name later]** → It would create a label of its own, and the next plan or drift run
  would show it being deleted, as website's did. Then the declaration is updated to match. No pull request loses a
  label unless an apply runs first, and every apply is a plan the owner reads.
- **[The probe repository is left behind]** → Deleting it is its own task, verified with `gh repo view` failing. The
  repository is named `infra-probe-*`, which the guard lets an agent create, configure and delete.
- **[website's labels are deleted before this merges]** → Only an apply of a plan that shows the deletion would do
  that. Any plan approved before this merges shows the deletion, and the owner can decline it. If it happens anyway,
  Dependabot recreates the labels with the same values, and this change re-adopts them unchanged.

## Migration Plan

The plan from the branch shows only the creations in the spec's second scenario. After the merge, the owner
approves the `apply` job, and `gh label list` on each repository confirms the labels. Rolling back means removing the
labels from the declaration, and the next apply deletes them from GitHub. That's safe while no pull request carries
them, and it returns website to the drift this change fixes.
