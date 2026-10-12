# Design

## Context

- **The rulesets today** (`tofu/modules/repository/main.tf`). One `protect main` ruleset is on each of `troupe`,
  `infrastructure` and `website`:
  - it refuses deletion and force-pushes, and requires linear history;
  - changes arrive by pull request, with no review needed and rebase as the only merge method;
  - `OrganizationAdmin` bypasses in `pull_request` mode;
  - on `troupe` and `infrastructure`, the infrastructure App (5272634) has an `always` bypass, for guard deliveries
    and state commits.

  `.github` has `protect_main = false` and no ruleset at all.
- **The checks GitHub reports today,** read from the latest merged pull requests (infrastructure#13, troupe#31,
  website#3 and .github#1) on 2026-10-12, with the App that posted each:

  | Repository | Check | App (id) |
  |---|---|---|
  | infrastructure | `check` | github-actions (15368) |
  | infrastructure | `guard tests (ubuntu-latest, Python 3.13)`, `(macos-latest, Python 3.12)`, `(macos-latest, Python 3.13)`, `(windows-latest, Python 3.12)`, `(windows-latest, Python 3.13)` | github-actions |
  | infrastructure | `guard (workflow rules)` | github-actions |
  | infrastructure | `plan (pull request)` (waits for the owner) | github-actions |
  | infrastructure | `DCO` | dco (1861) |
  | troupe | `check (<os>, Python <v>)` for 3 OSes × 2 versions | github-actions |
  | troupe | `guard (workflow rules)` (delivered from here) | github-actions |
  | troupe | `DCO` | dco |
  | website | `test` | github-actions |
  | .github | `DCO` | dco |

  On a pull request, `plan (main)` and `apply (main)` also appear, as skipped. They never run on a pull request.
- **Each repository's settings** still have their adopted defaults: merge commits, squash and rebase all allowed,
  branches kept after merge, and the wiki and classic projects on. No repository has a wiki (`git ls-remote` of each
  `.wiki.git` finds nothing). The org project "troupe roadmap" (number 1, 26 items) is linked to `troupe`.
- **Provider and GitHub behaviour this change depends on**, from earlier changes:
  - Updating `github_repository` sends a `PATCH` of the whole repository. adopt-org saw it turn `homepage: null`
    into `""`.
  - The owner's `pull_request` bypass did not override the merge-method rule (`--merge --admin` was refused).
  - A file commit by the App can race a ruleset change in the same apply (development-workflow D5).
- **The read-only plan App** (`troupe-run-infrastructure-plan`, 5280157) has been unused since ci-apply D2. It is
  declared in `oob/app-installations.json` and `oob/README.md`, and named in the rulesets spec.

## Goals / Non-Goals

**Goals:**
- A pull request whose checks haven't passed can't be merged, except by the owner's explicit bypass.
- Every required name is declared in one place. For this repository, the names are tested against the workflows
  that produce them.
- Nothing about required checks gets in the way of the App's direct commits: guard deliveries, state commits and
  `.github` syncs.
- Every GitHub behaviour the design relies on is shown on a throwaway repository first.

**Non-Goals:**
- Changing troupe's or website's workflows. Their check names are taken as they are.
- Required reviews. The org has one maintainer.
- A merge queue.

## Decisions

### D1. Required checks are declared in `tofu/required-checks.json`, and pinned to an App

The file maps each repository to its list of `{ "context": "<check name>", "app": "<slug>" }`. OpenTofu reads it with
`jsondecode(file(...))`, the same way it reads the labels. The module gets a `required_checks` variable, and the
ruleset gets a `required_status_checks` rule with one `required_check` per entry. Each entry's `integration_id` comes
from a small map in `tofu/repositories.tf`: `github-actions = 15368`, `dco = 1861`.

Pinning the App means a commit status with the same name, posted with someone's token, doesn't satisfy the check.

**Why JSON, not an HCL local:** a test has to read it. Python can read JSON with the standard library, but not HCL.

**The test** is `scripts/tests/test_required_checks.py`. For `infrastructure`, it reads `.github/workflows/ci.yml`,
`guard.yml` and `tofu.yml`. For each job that runs on `pull_request`, it expands the job's `name`, including
`${{ matrix.* }}` over the matrix with its `exclude` and `include`. It then asserts that the result equals
`infrastructure`'s `github-actions` entries. The `changes` job (D2) is the exception: it is deliberately not
required. The test also asserts that `DCO` is listed.

- Reading YAML needs **PyYAML**, plus `types-PyYAML` for `mypy --strict`. Both are dev dependencies only. The guard
  stays standard library only.
- `troupe`'s guard check comes from the same `guard.yml`, which is delivered from here. So its name is covered too.
- `troupe`'s CI names and `website`'s can't be read offline. They are listed as read on 2026-10-12, and the test
  doesn't cover them. A wrong name there fails safe: the check never reports, the pull request can't merge, and the
  owner's bypass gets it through.

**Alternative: one "all passed" job per workflow** (`needs:` every leg, `if: always()`), with only that job
required. Matrix changes would then need no ruleset change. The owner chose explicit names (2026-10-12). Adding an
aggregator to troupe would also need a pull request in troupe.

### D2. The PR plan is required, and skipped for pull requests that touch nothing OpenTofu reads

`tofu.yml` gets a `changes` job on `pull_request`, with no environment and no secrets. It:
- checks out the pull request with full history;
- lists the files changed between the base and the head (`git diff --name-only base...head`);
- runs `python3 scripts/plan_needed.py` on that list. The script is standard library only.

The script prints `plan=true` unless **every** changed file sits under a short list of prefixes that OpenTofu is
known never to read:
- `openspec/`, `docs/`, `oob/`, `scripts/tests/`;
- `README.md`, `CLAUDE.md`, and the `.claude/rules/` and `.claude/learnings/` trees.

`pr-plan` then gets `needs: changes`, and runs when
`!cancelled() && (needs.changes.result != 'success' || needs.changes.outputs.plan == 'true')`.

- **A failing `changes` job means "plan".** A skipped `pr-plan` counts as passed, so if a broken `changes` job could
  skip the plan, a pull request could merge without one.
- **The list names what's safe to skip, not what to plan.** OpenTofu reads:
  - `tofu/`;
  - `org-profile/`;
  - every file the guard delivers (`scripts/guard.py`, `.githooks/*`, `.claude/settings.json`,
    `.github/workflows/guard.yml`).

  A list of those would have to grow with every new delivery, and forgetting one would hide a delivery from the
  pull request's plan. An ignore-list fails the other way: a file nobody listed costs one approval. A `tofu/**`
  filter, as first suggested, would have missed every guard delivery.
- **A test keeps the list honest.** `test_plan_needed.py` takes every path OpenTofu reads and asserts the script
  plans for it:
  - `tofu/*.tf`, scanned for `file(` and `fileset(` arguments;
  - the `guard_files` set, parsed from `guard_delivery.tf`;
  - every file under `org-profile/`.

  It also checks the edge cases: a mix of ignored and read files plans, an empty list plans, and a path is matched
  by prefix, not by substring (`docs-old/` isn't `docs/`).

**Why not a workflow-level `paths:` filter:** a workflow that a filter skips never reports its jobs, so a required
`plan (pull request)` would stay "expected" forever. Job-level skips report "skipped", which counts as passed.

### D3. The checks don't have to be run against the latest `main`

`strict_required_status_checks_policy = false`. The App commits the state to `main` after every apply. With a strict
policy, that commit would put every open pull request out of date, and each one would need rebasing and re-checking,
and its plan approving again. The guard on `main` already re-checks every commit. The `plan (main)` that follows each
merge, made against `main` itself, is what the owner approves before anything applies.

**Alternative: strict.** It would catch a pull request that passes alone but fails combined with another. With one
maintainer and few concurrent pull requests, that's rare, and `main`'s own CI catches it before the plan.

### D4. The module's ruleset gets a mode: `pull-request`, `app-only` or `none`

`protect_main` (bool) becomes `main_ruleset`, with a default of `pull-request`.

- **`pull-request`** is today's ruleset, plus the required checks (D1).
- **`app-only`** is a ruleset named `app only`. It refuses all of these, and its only bypass actor is the App, in
  `always` mode:
  - `update` (with `update_allows_fetch_and_merge = false`), so no push and no pull request merge changes `main`;
  - `deletion`;
  - `non_fast_forward`.

  The owner has no bypass (owner's decision, 2026-10-12). The break-glass is editing the ruleset on GitHub, which the
  "owner can't be locked out" requirement already guarantees. The next plan restores it.
- **`none`** is for the probe, and for any repository taken under management before it is protected.

The ruleset carries the App's bypass from the moment it is created, so the four `.github` commits that add the note
(D6) can't race it. Nothing is being added to an existing ruleset. The probe still makes an App file commit after
creating an `app-only` ruleset.

**Alternative: a separate resource for `.github`'s ruleset** outside the module. That would duplicate the
conditions and bypass blocks, and the module's job is one repository's settings and protection.

### D5. adopt-org's setting findings become the module's defaults

The defaults change to:
- `allow_merge_commit = false`, `allow_squash_merge = false`, `allow_rebase_merge = true`;
- `delete_branch_on_merge = true`;
- `has_wiki = false`, `has_projects = false`.

No repository overrides them, so all four take them. The one possible exception is `has_projects` on `troupe`,
which the probe settles:
- **If** turning classic projects off on a repository linked to an org project hides the project or unlinks it,
  `troupe` keeps `has_projects = true`, and its declaration says why.
- **Otherwise,** `troupe` takes the default like the others.

`merge_commit_title` and the other merge-message fields stay declared. They are ignored while those merge methods are
off, and removing them would show as drift.

Because the provider `PATCH`es the whole repository, the probe saves the repository's full JSON before and after the
same settings change, and diffs the two. Only the intended fields may differ.

### D6. `.github`'s files name their source in a comment GitHub doesn't render

Each file in `org-profile/` gets a first line:
- **the Markdown files** (`CONTRIBUTING.md`, `SECURITY.md`, `profile/README.md`):
  `<!-- Source: troupe-run/infrastructure (org-profile/<path>). Change it there; this copy is written by the App. -->`;
- **`.github/dco.yml`:** the same text as a `#` comment.

This matches the guard files' `# Source:` line. HTML comments aren't rendered on the org profile or in GitHub's view
of a Markdown file. Each changed file means one App commit to `.github`, through the existing
`chore: sync <file> <sha12> ...` message.

### D7. The read-only plan App is deleted by the owner

Only the owner can delete an App. The steps are:
- GitHub, Settings → Developer settings → GitHub Apps → `troupe-run-infrastructure-plan` → Advanced → Delete. This
  also removes its installation.
- Delete its private key from 1Password. ci-apply stored it in vault `troupe.run`, next to the write App's item, but
  didn't record the item's name, so the owner identifies it there.

The README's "Adding a repository" already names only the write App. Its `protect_main = false` and its "How main
is protected" section change with D4.

This repository then removes it from:
- `oob/app-installations.json`;
- `oob/README.md`'s table;
- the comment in `tofu/probe/main.tf`, which describes the identity-switch probe. That probe stays as a record and
  says that App is gone.

`uv run scripts/oob.py` must then report no difference.

It's deleted rather than kept for later because:
- read-only plans can't read merge settings (ci-apply D2), so it has no use left;
- an installed App with a live key is attack surface;
- recreating one takes minutes.

### D8. Probe first, on a throwaway repository

The probe runs before anything live changes, using `tofu/probe` (with a new `probe_main_ruleset` and
`probe_required_checks`) on `troupe-run/infra-probe-<yyyymmdd>`. That repository holds a one-job workflow,
`probe-check`, which passes or fails depending on a file in the commit. It shows that:

1. **A required check blocks a merge:** a pull request with a failing `probe-check` can't be merged by a normal
   merge.
2. **The owner's bypass merges past it:** `gh pr merge --rebase --admin` succeeds.
3. **A status from the wrong source doesn't count:** a commit status named `probe-check`, posted with the owner's
   token on a pull request whose workflow didn't run, leaves the pull request unmergeable.
4. **A skipped job counts as passed:** a required job skipped by its `if:` lets the pull request merge.
5. **The App pushes past required checks:** with the `pull-request` ruleset and a required check, a
   `github_repository_file` commit by the App to `main` succeeds.
6. **`app-only` holds:**
   - the owner's direct push is refused;
   - the owner's pull request can't be merged, even with `--admin`;
   - the App's file commit succeeds.
7. **The setting changes are clean:** the D5 settings applied to the probe repository change only those fields,
   shown by a diff of the full repository JSON before and after.
8. **Classic projects:**
   - make a throwaway org project, link it to the probe repository, and add one of its issues;
   - set `has_projects = false`;
   - check that the link and the item survive, and that `gh project list` and the repository's linked projects still
     show it;
   - delete the project afterwards. `oob.py` will report it while it exists.

The probe's results go into this design, as they did for ci-apply. Then the repository and the project are deleted.

## Risks / Trade-offs

- **[A required check name drifts from the workflow, and every pull request blocks]** → For this repository, the test
  in D1 fails first, in `check.py`, before the commit. For `troupe` and `website`, the owner's pull-request bypass
  merges, and the next change fixes `required-checks.json`.
- **[An agent holding the owner's credentials merges a red pull request with `gh pr merge --admin`]** → The rulesets
  can't tell the owner from an agent using the owner's token. This is the same gap `protect-main` accepted, so the
  bypass stays pull-request-only and every bypass is visible in the pull request's timeline. Closing the gap needs a
  guard rule refusing `--admin` in Claude Code sessions. That belongs to the development workflow, not this change.
  It's raised as a follow-up issue (task 6.3) rather than built here.
- **[Every infrastructure pull request now waits for the owner's approval of its plan]** → That was already true for
  the plan to appear. D2 removes the wait for pull requests that change nothing OpenTofu reads, which covers most
  OpenSpec-only and docs-only pull requests.
- **[A broken `changes` job lets a pull request skip its plan]** → D2's condition plans whenever `changes` didn't
  succeed.
- **[The `.github` ruleset blocks a break-glass fix to `.github`]** → An org owner can always edit or disable a
  ruleset (rulesets spec, "The owner can't be locked out"). The next plan shows that as drift, and an apply restores
  it.
- **[Turning projects off on `troupe` hides the roadmap]** → The probe (D8.8) decides it before `troupe` is touched.
  If in doubt, `troupe` keeps them on, because it's the reversible choice.
- **[The provider's whole-repository `PATCH` changes something unintended]** → D8.7 diffs it on the probe first. The
  CI plan then shows the live change field by field before the owner approves.
- **[The apply makes four `.github` commits, three ruleset updates, one ruleset creation and four repository
  updates in one run]** → It is one plan, one approval. The App's commits to `.github` happen under a ruleset that
  already names it. A partial failure leaves the state committed (ci-apply), and the next run plans the rest.

## Migration Plan

1. Probe (D8), and record the results here.
2. On the branch:
   - the module changes (D1, D4, D5), `required-checks.json`, the note (D6), `tofu.yml` with `plan_needed.py` (D2),
     and the tests;
   - the owner deletes the plan App (D7), and `oob/` follows.
3. Open the pull request. Its plan, approved by the owner, is the evidence. It must show only:
   - the three updated rulesets and the new one;
   - the four repositories' setting changes;
   - the four `.github` file updates.

   Checks aren't required yet, so this pull request merges as before.
4. After the merge, `plan (main)` → the owner approves → the apply → the App's state commit, which is accepted under
   the new ruleset. Verify each of these:
   - the rulesets read back;
   - a later documentation-only pull request skips its plan, and a later tofu pull request waits for it.

**Rollback:** revert the commit through a pull request, which needs its plan approved. Or, as break-glass, the owner
disables a ruleset on GitHub, and the next plan shows it. Nothing here deletes data. The wiki and classic projects
hold nothing, and turning branch deletion on removes only branches that were already merged.

## Open Questions

- **Whether `website` should get DCO** (installing the DCO App there and requiring it). That is the owner's call,
  and can be a later change. It adds one entry to `required-checks.json`.
