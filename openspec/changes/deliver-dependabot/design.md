# Design

## Context

See proposal.md for why. Section 1 and 5b of #170's design are the source. What this builds on:

- `tofu/labels/dependabot.json` already declares each repository's Dependabot ecosystems (`repositories`) and the
  label for each (`ecosystems`, plus `dependencies`). These are the names Dependabot's `package-ecosystem` takes:
  `github-actions`, `npm`, `uv` (declare-dependabot-labels D1). Its tests check every repository's ecosystems are
  declared, and that the set names exactly the managed repositories.
- `tofu/guard_delivery.tf` delivers the guard's files to troupe and website with `github_repository_file`, commits
  straight to `main` as the App, and writes the delivered list `.github/guard-delivery.json` from `guard_files`. Two
  tests already read `guard_files` from the file's text by regex (`test_needs_guard_tests.py`, `test_plan_needed.py`).
- The App bypasses `main`'s ruleset on troupe, website and infrastructure, so it can commit to all three.
  infrastructure's `main` already gets the App's state commits.
- The tests read `tofu/` as text. None runs `tofu console`, which would need the encrypted state. `scripts/check.py`
  runs only `tofu init -backend=false` and `tofu validate`. pyyaml is a dev dependency.

Dependabot's options, from GitHub's
[options reference](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference),
read 2026-10-26:

- **`cooldown`:** takes `default-days` and `semver-{major,minor,patch}-days`. The semver keys work for `npm` and `uv`,
  but not for `github-actions` or `opentofu`, which take `default-days` only. Cooldown applies to version updates
  only, never to security updates.
- **`labels`:** replaces Dependabot's default labels. A label that isn't in the repository is ignored.
- **`commit-message`:** `prefix` plus `include: scope` gives `prefix(deps): …` or `prefix(deps-dev): …`. Titles
  follow it.
- **`exclude-paths`:** globs relative to the entry's `directory`. The docs say "each ecosystem can have its own" but
  don't list which ecosystems honour it, so `github-actions` is unconfirmed.
- **`open-pull-requests-limit`:** defaults to 5 per entry. Security updates have their own fixed limit.
- **`opentofu`:** is a `package-ecosystem` value. Nothing says whether it reads `.terraform.lock.hcl` providers from
  `registry.opentofu.org`.
- **`schedule`:** `weekly` takes `day`, `time` (`hh:mm`) and `timezone` (IANA, default UTC).
- **`pull-request-branch-name.prefix`:** exists, defaulting to `dependabot`.

## Goals / Non-Goals

**Goals:**
- Each repository's YAML is readable in the pull request that changes it, and tested, before it's delivered.
- Changing the policy, an ecosystem or a label is one edit in one file.

**Non-Goals:**
- **Branch names.** `pull-request-branch-name` keeps its default, `dependabot/…`. #174 reserves that prefix and
  builds the exemption on it.
- **Issues for updates, the exemption, and the closing-issue check.** These are #172, #174 and #173.
- **`.github`'s dependencies.** It has none, so it gets no file (spec).
- **A local rule in infrastructure against editing its own `.github/dependabot.yml`.** The delivered-file rule runs
  only where a delivered list exists. In infrastructure, a hand edit merged to `main` shows in the next plan and is
  restored. A guard rule for the source repository's own delivered files would be new guard behaviour, and would be
  delivered everywhere.

## Decisions

### D1. The policy lives in `tofu/dependabot.json`, and the ecosystems stay in the labels file

```json
{
  "schedule": { "interval": "weekly", "day": "monday", "time": "00:00", "timezone": "UTC" },
  "cooldown": { "default-days": 7, "semver-patch-days": 3, "semver-minor-days": 7, "semver-major-days": 14 },
  "semver_cooldown": ["npm", "uv"],
  "commit-message": { "prefix": "chore", "include": "scope" },
  "directories": { "github-actions": "/", "npm": "/", "uv": "/" }
}
```

- **Which ecosystems a repository has stays in `tofu/labels/dependabot.json`'s `repositories`.** Its labels, its
  config and its tests then all read one list.
  - *Alternative:* a second per-repository list here. It could disagree with the labels file.
- **`semver_cooldown` names the ecosystems that take semver days.** This follows the docs, so the generator doesn't
  write keys Dependabot would reject. An ecosystem not listed gets `default-days` only.
- **`directories` gives each ecosystem the directory its manifests are under.**
  - `/` for all three. troupe's `uv` workspace resolves from its root `uv.lock`, and `github-actions` scans
    `.github/workflows` from `/`.
  - A test fails when a declared ecosystem has no directory (spec).
- **The numbers are the builder's call (#170, "Left to the builder").**
  - Cooldown: 3 days for patch, 7 for minor and 14 for major. A week is the default for ecosystems with no semver
    days.
  - Schedule: Monday 00:00 UTC, clear of this repository's other schedules: the `tofu` drift plan at 06:00 and the
    schedule watch at 12:00.

  All of them are values in this file, changed by a pull request.

### D2. A script generates each repository's YAML into `tofu/dependabot/`, and OpenTofu delivers it

`scripts/dependabot_config.py` reads the policy, the labels file and `guard_files`. It writes
`tofu/dependabot/<repository>.yml` for each repository with ecosystems: `troupe.yml`, `website.yml` and
`infrastructure.yml`. A test regenerates them in memory and fails, naming the file and the command to run, when a
checked-in copy differs. `tofu/dependabot.tf` delivers each one with `file()`, as `guard_delivery.tf` delivers the
guard's files.

- **Why generate in Python:**
  - The tests can parse the output (pyyaml) and check each spec scenario against it.
  - The pull request shows each repository's actual YAML in its diff.
  - The file can open with a comment saying where it comes from.
- **Alternative: build it in OpenTofu with `yamlencode`,** with no checked-in output. That's one generator fewer, but
  nothing here can test it without `tofu console`, which needs the encrypted state. It also can't carry a comment
  except by string concatenation, and the reviewer sees HCL rather than the YAML Dependabot reads.
- This isn't the "checked in, test-matched" copy the owner declined for infrastructure. There is still one source
  (the policy and labels files), and every repository's copy, infrastructure's too, is delivered by the App (D4). The
  checked-in files are the generator's output, in the same place for all three, like the guard's sources that
  `guard_delivery.tf` reads.

The generated file:

```yaml
# Generated in troupe-run/infrastructure from tofu/dependabot.json and tofu/labels/dependabot.json,
# and delivered by its App. Change it there: an edit here is drift, and the next apply reverts it.
version: 2
updates:
  - package-ecosystem: uv
    directory: /
    schedule: {interval: weekly, day: monday, time: "00:00", timezone: UTC}
    cooldown: {default-days: 7, semver-patch-days: 3, semver-minor-days: 7, semver-major-days: 14}
    commit-message: {prefix: chore, include: scope}
    labels: [dependencies, "python:uv"]
  - package-ecosystem: github-actions
    directory: /
    ...
    exclude-paths: [.github/workflows/claude-review.yml, .github/workflows/guard.yml]
```

Entries are in the labels file's order for that repository, and keys are in a fixed order, so the output is stable.

### D3. Delivered workflows are left out with `exclude-paths`, taken from `guard_files`

- **In each guard target, the `github-actions` entry's `exclude-paths` lists every `guard_files` entry under
  `.github/workflows/`.** The script reads `guard_files` with the same regex the two existing tests use, and moves it
  into one shared helper. The targets come from `guard_targets`, read the same way. A workflow added to `guard_files`
  is then excluded on the next generation, and the freshness test fails until it's regenerated (spec).
- **infrastructure has no `exclude-paths`.** It's the source, so its Dependabot bumps the actions these workflows pin.
  The next apply delivers the bump (#170, 5b).
- **Confirmed on 2026-10-27: `github-actions` honours `exclude-paths`.** The probe (D6) had two workflows pinning
  `actions/checkout@v3`, and `.github/workflows/delivered.yml` was listed in `exclude-paths`. Dependabot's only pull
  request there (#1, `chore(deps): bump actions/checkout from 3 to 7`) changed `.github/workflows/own.yml` alone. So
  `exclude-paths` is the mechanism, and the `ignore` fallback (an entry for each action the delivered workflows pin,
  which would have stopped troupe's and website's own workflows getting those bumps too) isn't needed.

### D4. One resource delivers all three, and the delivered lists gain the path

- **`github_repository_file.dependabot` has one instance per generated file.** Each instance is keyed by repository,
  and writes to `.github/dependabot.yml` on `main`. It has `overwrite_on_create = false`, as the guard's deliveries
  have, so an existing file fails the apply rather than being replaced. None exists today.
- **The commit message is `chore(dependabot): deliver .github/dependabot.yml <sha256[:12]> from
  troupe-run/infrastructure`.** It changes exactly when the content does (guard-delivery D3).
- **The content is `sensitive()`, like every file OpenTofu writes.** The ci-apply spec has a plan show a delivered
  file's hash, never its content, and `test_file_content_sensitive.py` holds every `github_repository_file` to it.
  The YAML is reviewed in the pull request's diff of `tofu/dependabot/`. The first draft left it unwrapped so the plan
  could show the YAML, and that test refused it (apply, 3.1).
- **`depends_on` the three repository modules**, so the App's bypass exists before the commit (guard-delivery D5).
- **The delivered list.** `guard_delivery.tf`'s `guard_list` gains `.github/dependabot.yml` for the guard targets.
  The path is the same in both targets, so the list stays one value. That turns on the delivered-file rule for it in
  troupe and website, with no guard change: the rule reads the list.
- **infrastructure gets its file but no delivered list** (owner, 2026-10-26: the App delivers it too).

### D5. infrastructure's delivery commit is tested like any other push to `main`

The App's commit of `.github/dependabot.yml` to infrastructure's `main` is a push to `main`, so `ci.yml` runs, and
then `tofu.yml`'s plan of `main`, which shows no change. The ci-apply spec has CI test every push to `main` that
changes more than the state file, and `test_required_checks.py` pins `paths-ignore` to the state file alone. So the
delivery commit gets no skip.

- *Rejected during apply:* adding `.github/dependabot.yml` to `ci.yml`'s `paths-ignore`. It would have saved one CI
  run and one no-change plan for each delivery, but it contradicts the spec and the test. The cost is small: a
  delivery happens only when the policy, an ecosystem or a label changes.

### D6. OpenTofu providers: probe first, then add or record

The probe ran on a throwaway private repository, `troupe-run/infra-probe-dependabot`, on 2026-10-26 and 27. It held:
- `tofu/versions.tf` requiring `integrations/github`;
- the `tofu/.terraform.lock.hcl` that `tofu init` writes, locking `registry.opentofu.org/integrations/github` at
  6.2.0 (6.13.0 is current);
- a `dependabot.yml` with an `opentofu` entry for `/tofu`, beside D3's `github-actions` check.

There were two outcomes to tell apart:

- **A pull request that changes the lockfile's version and hashes:** infrastructure would get an `opentofu` entry,
  with a declared label.
- **No such pull request:** no entry, and the docs say provider updates are made by hand.

**Result: no `opentofu` pull request, so no entry.**

- **First run:** the constraint was `~> 6.2` with 6.2.0 locked. `github-actions` opened its pull request within 20
  minutes, and `opentofu` opened none.
- **Second run:** the constraint was pinned exactly to `6.2.0`, in both files, so an update had to change the
  requirement. Changing the schedule to daily started another run, and after 15 minutes there was still no
  `opentofu` pull request.

Dependabot's job log is only on the repository's web page, which wasn't read, so why it proposed nothing is
unknown. The spec's rule is "shown to update", and it wasn't. infrastructure's `repositories` keeps `github-actions`
and `uv`, and `docs/development-workflow.md` says provider updates are made by hand with `tofu init -upgrade`. Such a
change takes the full path, plan and apply approvals included (#170, 5a). The probe repository was deleted afterwards.

## Risks / Trade-offs

- **[Risk] Version-update pull requests can't merge until #174, and get no issue until #172.**
  → The owner chose to start now (2026-10-26). `docs/development-workflow.md` says they take security-scanning D5's
  manual path until then. Up to 5 per entry stay open.
- **[Risk] Explicit `labels` stop Dependabot adding a `security` label to security updates.**
  → It added none on website's three (declare-dependabot-labels). Nothing reads one.
- **[Risk] `exclude-paths` isn't honoured for `github-actions`.**
  → Probed before anything is built on it (D3), with a fallback whose cost is written down.
- **[Risk] A stale generated file.**
  → The freshness test is in `scripts/check.py`, which runs before every commit and in CI. A new `dependabot` scope
  in `scripts/check-paths.toml` covers the policy, the generated files, `dependabot.tf` and the generator's inputs.
- **[Trade-off] infrastructure's file can be edited in a pull request there with no local refusal.**
  → It's reverted by the next apply after merge, and the pull request's plan shows the revert (Non-Goals).

## Migration Plan

1. Probe (D6, D3). Then build, test, and open the pull request. The plan shows three new files and two changed
   delivered lists.
2. The owner approves the plan, and the apply after merge delivers. Check each repository's `main` has the file. Then
   check Dependabot shows the configuration (Insights → Dependency graph → Dependabot) with no errors.
3. Check the first scheduled run, or a manual "Check for updates", opens a `chore(deps): …` pull request carrying only
   declared labels (the issue's "Done when").

Rollback: remove the entries from the generator's output and delete the files. Deleting `github_repository_file`
removes the file with a commit, and Dependabot goes back to security updates only.
