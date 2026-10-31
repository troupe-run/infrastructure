# Design

## Context

See proposal.md for why. What shapes the approach:

- **troupe's releases.** `release-please-config.json` puts every `packages/*` and `plugins/*` package in release-please
  as its own path, linked into one `troupe` group (the runners join it in troupe-run/troupe#215), with
  `bump-minor-pre-major`. `.github/workflows/release.yml` runs `googleapis/release-please-action` v5.0.0, which takes
  `release-please` `^17.6.0`. release-please assigns a commit to a package by the files it changes. A commit that
  changes only root files, such as `uv.lock` or the workspace `pyproject.toml`, belongs to no package and releases
  nothing.
- **troupe's Dependabot commits.** Runtime dependency bumps raise the floor in the package's `pyproject.toml` as well
  as `uv.lock` (b67178f, `chore(deps): Bump eventsourcing from 9.5.5 to 9.5.6`, changed
  `packages/troupe/pyproject.toml` and `packages/troupe-store-text/pyproject.toml`). Dev bumps are
  `chore(deps-dev)` and change the root `pyproject.toml` (1d6d9d1) or a package's `[build-system]` (4c00c48). The
  workspace root is `package = false` with dev groups only, so in troupe's `uv` entry, `chore(deps):` always means a
  shipped package's runtime dependency.
- **How people install.** `uv tool install "git+…@<tag>#subdirectory=packages/troupe-run"` resolves from the
  packages' declared ranges, not from `uv.lock`. So only a raised floor in a package changes what an install gets,
  and that's exactly the change release-please can see.
- **Merges.** troupe merges by rebase through the merge queue, so Dependabot's own commit lands on `main` with its
  `chore(deps):` subject. A commit message on `main` can't change after the merge.
- **`dependabot-issues` today.** `scripts/dependabot_issues.py` already tells a security update by the repository's
  open alerts (`is_security`, #229, #238), and already edits each Dependabot pull request's description to add
  `Closes #<n>`, putting it back when Dependabot rewrites the description (`line` action). It reads only API
  metadata and never a pull request's files. The App already has `pull_requests: write` and `vulnerability_alerts:
  read`.

## Goals / Non-Goals

**Goals:**

- A shipped runtime dependency's security update shows in troupe's release pull request as a fix and releases a patch,
  with nobody doing anything by hand.
- Evidence from a probe that the mechanism works on a rebase merge through a merge queue before any code relies on it.

**Non-Goals:**

- Transitive dependencies. A security update that changes only `uv.lock` changes no package, so release-please doesn't
  release it, and a release wouldn't change what an install resolves anyway.
- Severity. Any severity releases (troupe-run/troupe#214).
- website and infrastructure: neither releases with release-please.
- Changing the generated `dependabot.yml` files, or Dependabot's commit prefix.
- troupe's `contributing/releasing.md`: troupe-run/troupe#215 rewrites it. This change comments there with what to
  say.

## Decisions

### D1. release-please's commit override in the pull request's description

For each commit it reads, release-please looks up the pull request it came from and, when that pull request's
description has a `BEGIN_COMMIT_OVERRIDE` … `END_COMMIT_OVERRIDE` block, parses the block in place of the commit's
message. The commit keeps its files, so package assignment is unchanged. The run writes:

```
BEGIN_COMMIT_OVERRIDE
fix(deps): Bump eventsourcing from 9.5.5 to 9.5.6
END_COMMIT_OVERRIDE
```

It's the pull request's title, with `chore(deps):` replaced by `fix(deps):`, so the changelog reads like Dependabot's
own entry.

Alternatives:

- **Retitle the pull request.** On a rebase merge, the title isn't the commit message, so release-please never sees it.
- **Squash-merge Dependabot's pull requests.** It would make the title the commit, but troupe merges by rebase only,
  through the merge queue.
- **A different Dependabot prefix for security updates.** `commit-message` has `prefix` and `prefix-development`,
  but nothing for security updates, so a security update can't be told apart in Dependabot's configuration.
- **A follow-up `fix` commit or `Release-As` by hand.** It works, but it's a manual step that's easy to forget. The
  decision (troupe-run/troupe#214) rejected manual steps for the bundle for the same reason.

What isn't known yet: how release-please finds a commit's pull request after a rebase merge through a merge queue. As
far as we know it reads GitHub's associated pull requests for the commit and takes the one whose merge commit is that
commit. For a one-commit pull request merged by rebase, that's the commit on `main`. Dependabot's pull requests always
have one commit. That's the claim D2 tests.

### D2. The probe gates the build

The probe runs before any code is written, in `troupe-run/infra-probe-release-override`, a public repository so that
rulesets apply. It's created, configured, used and deleted as the development workflow allows for `infra-probe-*`.

- **Layout:** two Python packages, `packages/a` and `packages/b`, each with a `pyproject.toml`, linked in one
  release-please group, `bump-minor-pre-major`, manifest at `0.1.0`, and a `bootstrap-sha` at the setup commit. That's
  troupe's config cut down.
- **Merges:** a ruleset on `main` that requires a pull request and a merge queue with the `REBASE` merge method, as
  troupe's does. Read troupe's ruleset and copy its merge-queue settings.
- **Pull requests, each one commit, merged through the queue:**
  - A: `chore(deps): Bump x from 1.0.0 to 1.0.1`, changing `packages/a/pyproject.toml`, with an override reading
    `fix(deps): …`.
  - B: `chore(deps): Bump y from 2.0.0 to 2.0.1`, changing `packages/b/pyproject.toml`, with no override.
  - C: `chore(deps): Bump z from 3.0.0 to 3.0.1`, changing only the root `uv.lock`, with an override.
- **Reading the result:** a `workflow_dispatch` workflow in the probe runs the `release-please` CLI, at the version
  release-please-action v5.0.0 resolves, as `release-pr --dry-run` with the workflow's read-only `GITHUB_TOKEN`. It
  prints the release pull request it would open, and writes nothing. That's the same code path as troupe's release
  job, apart from the final write, and needs no App or token from outside the probe.
- **Passes when:** the dry run proposes `0.1.1` for the group, lists A under bug fixes, and lists neither B nor C.
- **D, recovery:** open and merge a fourth pull request like A, but without the override. Then add the override to its
  description after the merge and run the dry run again. It passes when D is now listed too. That's the recovery
  D6 documents.

If A isn't listed, or the version isn't `0.1.1`, the change stops. The finding goes on #240, and the owner chooses
between the alternatives in D1. Nothing in tasks 2 onwards starts until the probe has passed and its output is on
#240.

### D3. Who gets an override: four tests, and release-please has the last word

A pull request gets an override when all of these are true:

1. it counts as a security update by the existing open-alerts rule;
2. its title starts `chore(deps):`, which Dependabot uses for a runtime dependency (it uses `chore(deps-dev):` for a
   development dependency);
3. its repository and ecosystem (from the branch, as the alerts rule reads it) are declared as shipping (D4).

Then, fourth, release-please releases only the packages whose files the commit changes. So the script doesn't need to
know which paths ship, and a root-only commit with an override releases nothing (probe case C).

Alternatives:

- **Read the pull request's changed files** (`pulls/<n>/files`) and match `packages/*/pyproject.toml`. That breaks the
  script's promise to read only metadata, and duplicates the path assignment release-please already does from its own
  config.
- **The alert's `dependency.scope`** (`runtime` or `development`). A grouped pull request, or one whose package can't be
  read, matches no single alert, and Dependabot's title already carries the same split.

### D4. The declaration: `releases` in `tofu/dependabot.json`

```json
"releases": { "troupe": ["uv"] }
```

It goes next to the policy the configurations are generated from, because it's policy about Dependabot's updates. The
generator ignores it (the generated files don't change). `scripts/check.py`, through the same validation that checks
`directories`, fails when it names a repository or an ecosystem not declared for that repository in
`tofu/labels/dependabot.json`. `dependabot_issues.py` reads it when it reads the repositories.

Alternative: read troupe's `release-please-config.json` through the API. That ties this repository to the product's
file layout, adds a read that can fail every run, and still wouldn't say which Dependabot ecosystem the packages'
dependencies come from.

### D5. One description write per pull request, and an override is never rewritten

`line` and the new `override` each patch the description from the body read at the start of the run. Done as two
writes, the second would drop what the first added. So the plan yields one `body` action per pull request, carrying
whatever is missing: the closing line, the override, or both. It's built from the body read once, and its log line
names each part.

"Has an override" means the description has a `BEGIN_COMMIT_OVERRIDE` line, whatever is in the block. The run never
edits or removes one (the spec: "A run never takes an override away"). An unneeded patch release costs little, but
removing a fix's override by mistake would drop a security release silently. That's the conservative side, and an
owner's edit to the block stands.

### D6. Misses and recovery

A due override that's missing counts as a miss, on the same one-hour rule as a closing line. The script already
compares each open pull request's `updated_at` with the run's start.

If a security update merges before any run added its override (for example, merged within minutes of Dependabot
opening it), the owner adds the block to the merged pull request's description before the release pull request
merges, and re-runs troupe's `release` workflow. Probe case D verifies this. `docs/development-workflow.md` says so.

## Risks / Trade-offs

- [The probe passes, but troupe behaves differently, for example the merge queue's commit isn't the pull request's
  merge commit there] → The first real security update in troupe is checked against its release pull request, and
  #240 stays open until it's seen (the issue's "Done when" also accepts a probe). If it fails, D6's recovery covers
  that release while it's fixed.
- [Dependabot updates the same pull request to a newer version and retitles it, leaving an override with the old
  versions] → It's still a `fix(deps)` for the same dependency, so the release is right and only the changelog line's
  versions are stale. That's accepted, since rewriting the block would go against D5.
- [A security update merges before the run adds the override] → D6's miss reporting and recovery.
- [A probe repository left behind] → The last probe task deletes it and checks `gh repo view` fails.
- [Another open change to `dependabot_issues.py`] → #238 (PR #239) already merged before this branch, so there's
  nothing to rebase over. Any later one rebases onto whichever merges first. A clean rebase is not enough: re-run the
  script's tests (memory: rebase carries stale conditions).

## Migration Plan

It deploys with the merge to `main`: the next `dependabot-issues` run adds overrides to any open troupe security
update. Nothing is applied by OpenTofu: `releases` changes no resource. To roll back, revert the commit. Overrides
already in descriptions stay, and still release a patch for those pull requests, until they're removed by hand.
