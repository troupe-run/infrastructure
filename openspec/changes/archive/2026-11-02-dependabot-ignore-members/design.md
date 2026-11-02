# Design

## Context

See proposal.md for why. What shapes the approach:

- **The generator.** `scripts/dependabot_config.py` builds each entry from `tofu/dependabot.json` (the shared policy)
  and `tofu/labels/dependabot.json` (each repository's ecosystems and labels). Its one per-repository variation so far
  is `exclude-paths` on `github-actions` for guard targets. `releases` (security-updates-release design D4) is the
  precedent for a per-repository, per-ecosystem key in the policy, validated by `unknown_releases`, which
  `generated()` runs, so `scripts/check.py` (through `test_the_generated_files_are_up_to_date`) fails on it.
- **troupe's members.** `packages/*` and `plugins/*`: `troupe`, `troupe-artifacts-local`, `troupe-identity-local`,
  `troupe-run`, `troupe-stage-local`, `troupe-store-text`, `troupe-vcs-files`, `troupe-vcs-git`,
  `troupe-runner-claude-code` and `troupe-runner-scripted`, all as `{ workspace = true }` sources. Only `troupe` is
  taken on PyPI today; the others are skipped ("Latest version is" empty), but any of them could be registered by
  someone else tomorrow.
- **Dependabot's `ignore`.** Each condition takes `dependency-name`, which accepts `*` as a wildcard, and optional
  `versions` and `update-types`. A condition with only a name ignores every update to that dependency.
- **Delivery.** `tofu/dependabot.tf` commits each generated file to its repository's `main` through the App after
  the owner approves the plan. The plan shows a hash, not the file; the file is reviewed in the pull request's diff of
  `tofu/dependabot/`.

## Goals / Non-Goals

**Goals:**

- troupe's `uv` job finishes without trying to update a workspace member, now and when a member is added.
- A general way to declare an ignore, so the next one is a data change.

**Non-Goals:**

- Ignoring by version or update type. Nothing needs it; the shape leaves room (D1).
- infrastructure's own `uv` entry. Its project, `troupe-infrastructure`, is a workspace root that Dependabot hasn't
  failed on. A data change adds it if it ever does.
- troupe's check that every member is ignored: that's troupe-run/troupe#254's change, `dependabot-uv-resolve`.

## Decisions

### D1. A list of names per repository and ecosystem, in the policy

```json
"ignore": { "troupe": { "uv": ["troupe", "troupe-*"] } }
```

Beside `releases` in `tofu/dependabot.json`, so the policy stays the one place an entry's content comes from, and
keyed the same way (repository, then ecosystem). Each name renders as `- dependency-name: <name>`, after `labels`
and before `exclude-paths`. A plain list of names, not Dependabot's condition objects, because names are all that's
needed and a closed shape can't hold a typo'd key. If versions or update types are ever needed, a name can become an
object then.

Alternatives: in `tofu/labels/dependabot.json` beside each repository's ecosystems (rejected: that file is labels and
ecosystems, and the ignore isn't either); a free-form `extra` block merged into an entry (rejected: anything could
slip in, and nothing checks it).

### D2. `troupe` and `troupe-*`, not each member by name

The wildcard covers a member added later without a change here, which matters because a missed one fails troupe's
whole `uv` job again, and only when someone registers its name on PyPI. The cost is that it would also ignore a
third-party dependency named `troupe-…`; troupe has none, and troupe's own check (#254) names any member that isn't
covered. `troupe` itself is named exactly, so `troupe*` isn't needed and doesn't over-match `troupelike`.

### D3. Malformed declarations fail the check, not fall through

As with `releases`: an undeclared repository or ecosystem, an empty list and a repeated name are each named by
`scripts/check.py`, through the same `generated()` check. An empty list fails rather than meaning "ignore nothing",
because leaving the key out already means that, and an empty list is more likely a half-made edit. Unknown keys in the
policy aren't checked today, and this change doesn't start.

### D4. No probe; the delivered file is the test

The only GitHub behaviour this relies on is Dependabot honouring a documented `ignore` with a wildcard name. A probe
repository would need a uv workspace whose member is shadowed on PyPI, and the failure it would show is the one troupe
already has every week. Pushing a changed `.github/dependabot.yml` to the default branch starts a Dependabot run, so
the apply itself produces the evidence: troupe's next `uv` job either skips `troupe` or fails as today, harmlessly.
If it fails, a new issue says it arose from #259 (rules: reopen only for something forgotten).

## Risks / Trade-offs

- [Dependabot matches the wildcard differently for Python names, such as `_` against `-`] → troupe's members all use
  `-`, matching their normalised names. The post-apply run (D4) shows it; troupe's own check also reads the names.
- [An ignore on `uv` also suppresses security updates for those names] → wanted: a member never comes from PyPI, so
  an advisory against PyPI's `troupe` doesn't concern troupe's.
- [troupe's check lands before the apply and fails on `main`] → the proposal says troupe's change can merge only after
  this one is applied; say so on #254.

## Migration Plan

Merge, then the owner approves the `tofu` workflow's apply, which updates `github_repository_file.dependabot
["troupe"]` in place. Rollback is reverting the merge and applying again; the file goes back to having no ignore.
