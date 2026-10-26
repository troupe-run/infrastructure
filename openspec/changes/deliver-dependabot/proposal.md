# Proposal

## Why

No governed repository has a `.github/dependabot.yml`. So Dependabot runs only security updates, with its default
labels and commit messages, and no repository's configuration is declared anywhere (#171). #170's design starts here:
one policy, declared in infrastructure and delivered to every repository that has dependencies, with weekly version
updates. #172 (issues), #174 (the guard's exemption) and #173 (closing an issue, checked on GitHub) build on it.

## What Changes

- **One policy, declared once.** A new `tofu/dependabot.json` holds the settings every repository shares:
  - a weekly schedule on a fixed day and time;
  - a cooldown, shorter for patch and minor than for major;
  - `chore` as the commit prefix, with the `deps` or `deps-dev` scope, so titles read `chore(deps): …`;
  - the directory Dependabot scans for each ecosystem.

  Each repository's ecosystems, and their labels, stay where they're already declared, in
  `tofu/labels/dependabot.json`.
- **A generated file for each repository.** OpenTofu builds each repository's `.github/dependabot.yml` from the
  policy, the repository's ecosystems and the declared labels. Each update applies `dependencies` and its ecosystem's
  label, and Dependabot applies no labels of its own. One pull request per update: no `groups`. The open pull request
  limit stays Dependabot's default (owner, 2026-10-26).
- **Delivered by the App, as the guard's files are.** The infrastructure App commits the file to `main` in troupe,
  website and infrastructure. infrastructure gets it too (owner, 2026-10-26), so its file isn't a hand-kept copy. A
  hand edit anywhere shows in the next plan, and the apply restores it. A repository with no ecosystems (`.github`)
  gets no file.
- **Delivered workflows are left out where they're delivered.** In troupe and website, the `github-actions` updates
  skip the workflows the guard delivers (`guard.yml`, `claude-review.yml`). A bump there would be refused by the
  delivered-file rule. Those workflows are bumped in infrastructure, and the next apply delivers them (#170, 5b).
- **troupe's and website's delivered lists name the new file**, so the guard's delivered-file rule refuses a commit
  that changes it there.
- **OpenTofu's providers, if Dependabot can update them.** A throwaway repository checks whether Dependabot's
  `opentofu` ecosystem updates a `.terraform.lock.hcl` whose providers come from `registry.opentofu.org`. If it does,
  infrastructure gets an `opentofu` entry, with a declared label. If it doesn't, provider updates stay manual, and
  the docs say so.
- **Docs.** `docs/development-workflow.md` says version updates now run weekly and that their pull requests still go
  through security-scanning D5's manual path until #174 lands. The README's layout table names the policy file.

Version updates start with the first apply. Until #174 and #172 land, their pull requests fail `guard` like today's
security updates, and they get no issue. The owner chose that over holding them back (2026-10-26).

## Capabilities

### New Capabilities
- `dependency-updates`: how Dependabot updates each repository's dependencies. That covers the declared policy, the
  generated and delivered `dependabot.yml`, its schedule, cooldown, commit messages and labels, and the files it
  leaves out. #172 and #174 will add the issue for each update and the exemption here.

### Modified Capabilities
- None. `guard-delivery`'s delivered-list requirement already says a receiving repository's list names every file
  delivered to it. `labels`' Dependabot requirement already covers declaring a label for each ecosystem, an
  `opentofu` one included.

## Impact

- **OpenTofu:**
  - a new `tofu/dependabot.json` and `tofu/dependabot.tf`;
  - `tofu/guard_delivery.tf`, whose delivered list gains the file;
  - possibly `tofu/labels/dependabot.json`, for `opentofu`.

  The plan adds one file to each of troupe, website and infrastructure, and changes each target's
  `.github/guard-delivery.json`.
- **Tests:** `scripts/tests/`. The generated files are checked against the policy and the declared labels, and the
  delivered-workflow exclusions against the guard's file list.
- **GitHub:** three new commits to `main` by the App. Weekly version-update pull requests in troupe, website and
  infrastructure, which fail `guard` until #174.
- **Not changed:** the guard's rules, rulesets, the branch prefix (#174 reserves it), and Dependabot's security
  updates, which keep running and pick up the new labels and commit prefix.
