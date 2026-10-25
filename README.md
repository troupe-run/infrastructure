# troupe-run/infrastructure

How the troupe-run GitHub organisation builds software. This repo is not the product: troupe itself lives in
[troupe-run/troupe](https://github.com/troupe-run/troupe). It owns two things (Decision troupe-run/troupe#25):

- **The org as code.** OpenTofu declares the org's settings, its repositories and their labels, and the files of
  [troupe-run/.github](https://github.com/troupe-run/.github), which is a target only. What OpenTofu can't manage is
  checked for drift from [`oob/`](oob/README.md).
- **The development process.** The `development-workflow` spec and its guard, which governs this repo and is
  delivered to troupe and the website. The rules are in
  [docs/development-workflow.md](docs/development-workflow.md).

Work follows OpenSpec: an issue, then a change under `openspec/changes/`, on a branch named after it, then a pull request
that closes the issue. Specs live in `openspec/specs/`.

## Layout

| Path | What it holds |
|---|---|
| `tofu/` | The OpenTofu root module and its encrypted, committed state |
| `tofu/modules/repository/` | One managed repository: settings, labels, security features (Dependabot alerts and security updates, secret scanning and push protection), and protection against deletion |
| `tofu/labels/` | Label sets as data. `troupe.json` is troupe's `cap:*` capability labels: a new capability gets its label by a pull request here. `release.json` is release-please's two labels on troupe. `dependabot.json` is the labels Dependabot applies, and which ecosystems each repository has, so Dependabot uses them rather than creating its own |
| `tofu/probe/` | Points the same module at a throwaway repo, to show drift behaviour without touching a live one |
| `tofu/guard_delivery.tf` | The guard's files in each repository that receives it, and the generated list of them |
| `tofu/environments.tf` | CI's three environments on infrastructure (`plan-pr`, `plan-main`, `apply`), and the website's `github-pages`, which only `main` may deploy through |
| `tofu/release.tf` | What troupe's release workflow needs: the `release` environment, limited to `main`, the release App's client ID, and the ruleset that lets only the App create or update `release-please--*` branches. The App and its key are set up by hand ([oob/README.md](oob/README.md#troupes-release-app-set-up-by-hand)) |
| `tofu/board.tf` | What website's weekly link check and the schedule watch need to put their issues on the troupe roadmap board: a `board` environment on website and on infrastructure, each limited to `main`, and the board App's client ID in each. The App and its key are set up by hand ([oob/README.md](oob/README.md#the-board-app-set-up-by-hand)) |
| `tofu/docs.tf` | What troupe's release workflow and infrastructure's milestones notice need to start the website's build: a `docs` environment on troupe and on infrastructure, each limited to `main`, and the docs App's client ID in both. The App and its key are set up by hand ([oob/README.md](oob/README.md#the-docs-app-set-up-by-hand)) |
| `tofu/milestones.json`, `tofu/milestones.tf` | The release milestones (0.1.0 to 0.20.0, and 1.0.0; each a planned troupe release described by what a user gets), the same in every managed repository so the roadmap board groups them by title. A finished release is closed by setting its state, never removed, and a milestone's key never changes, so a rename happens in place. A key and a title can differ: the title is the version, so anything that reads the file uses the title. GitHub refuses two milestones with one title, so titles that move between milestones take two applies: each first gets an `interim_title`, such as `0.2.0 (renumbering)`, applied instead of its title, and a later change removes it |
| `tofu/dns.json`, `tofu/dns.tf` | troupe.run's DNS records in Cloudflare: the site's, the org's and Pages' domain verification, the mail lockdown and the CAA policy, and the zone's Universal SSL setting, declared off so Cloudflare adds no CAA records of its own. No record is proxied, TTLs are automatic, and a record's key never changes, so an edit happens in place. The zone, the token and the nameservers at Gandi are set up by hand ([oob/README.md](oob/README.md#trouperuns-dns-set-up-by-hand)) |
| `org-profile/` | The source of `troupe-run/.github`'s files, byte for byte |
| `scripts/guard.py`, `scripts/guard_pytest.py`, `.githooks/`, `.claude/settings.json`, `.github/workflows/guard.yml` | The guard: this repo's own, and the source of every delivered copy |
| `docs/development-workflow.md` | Every rule the guard enforces, and how an override works |
| `oob/` | What OpenTofu can't manage, and `scripts/oob.py`'s declarations |
| `.github/workflows/schedules.yml`, `scripts/watch_schedules.py`, `scripts/watched-schedules.json` | The schedule watch: daily, it checks each scheduled workflow listed in `watched-schedules.json` (today, website's weekly link check) is still on and has run on its schedule, and keeps one "Scheduled workflows stopped running" issue on the board while one isn't (spec: schedule-watch, #60). A new scheduled workflow is watched by adding it to the list |
| `.github/workflows/milestones-notice.yml` | The milestones notice: on a push to `main` that changes `tofu/milestones.json`, it dispatches the website's deploy with the docs App's token, so troupe.run's `/status/` shows the new release list (spec: milestones, #124) |
| `scripts/` | `tofu.py` (the only way to run `tofu`), `oob.py` (drift checks), `plan_checks.py` (a plan's failed check blocks as warnings on the run), `plan_secrets.py` (fails a plan job if any rendering of the plan holds a key), `check.py` (the repo's check), `check-paths.toml` (what a change to each path needs from the check), `guard.py` |

## Setup

You need:
- [uv](https://docs.astral.sh/uv/);
- OpenTofu 1.8 or later (`brew install opentofu`);
- the 1Password CLI (`op`), signed in to the account named in `scripts/tofu.py`;
- `gh`, logged in with read access to the org.

```
uv sync
uv run scripts/check.py          # ruff, mypy --strict, pytest, tofu fmt and validate; needs no secret
```

The first run of the check turns the git hooks on (`core.hooksPath = .githooks`), and says so. From then on, each
commit runs the check first and needs a Conventional Commit message on a branch named after an OpenSpec change. A
Claude Code session turns the hooks on too, and its hooks refuse the same shortcuts.

## Running a plan

```
uv run scripts/tofu.py init
uv run scripts/tofu.py plan
uv run scripts/oob.py            # drift in what OpenTofu can't manage (CI runs it too, with --ci)
```

`scripts/tofu.py` runs `tofu` in `tofu/` as the `troupe-run-infrastructure` GitHub App:
- **When the secrets are already in the environment** (`TF_VAR_github_app_pem`, `TF_VAR_state_passphrase`,
  `TF_VAR_billing_email` and `TF_VAR_cloudflare_api_token`), as they are in CI, it uses them.
- **Otherwise** it runs `tofu` under `op run`, which takes the secrets from the 1Password references in
  `tofu/secrets.env` for that one run. Expect a 1Password prompt.
- **Without either,** it stops before contacting GitHub or Cloudflare and names what's missing.

No secret is ever written to the repo. The state is encrypted, and is unreadable without the passphrase. The App's
key is ephemeral input, so a saved plan doesn't hold it either: applying a saved plan asks for the key again.

A local plan is read-only and always safe to run. Changes reach the org through CI (below).

CI also plans `main` every day at 06:00 UTC, so drift (a change made on GitHub rather than declared here) shows within
a day. A plan with changes waits for your approval like any plan of `main`; one with none asks nothing. Beside each
plan of `main`, the `drift (out of band)` job runs `scripts/oob.py --ci`, and fails on any difference in what OpenTofu
can't manage ([oob/README.md](oob/README.md)). GitHub pauses a public repository's scheduled workflows after 60 days
without activity in it. `gh workflow enable tofu.yml` turns the daily plan and that check back on.

The schedule watch (`schedules.yml`, daily at 12:00 UTC) notices when that happens to a watched workflow in another
repository, such as website's weekly link check: it opens an issue here, on the board, that names the workflow and the
command that turns it back on. It can't notice this repository going quiet, since it's paused with it. GitHub doesn't
say what counts as activity; commits are assumed to, so merges and the state commits after each apply should keep
this repository active. Run `uv run scripts/watch_schedules.py` to see what it would report; outside CI it changes
nothing.

## Changing the org

Changes are planned and applied by the `tofu` workflow (`.github/workflows/tofu.yml`, spec `ci-apply`). Your part
is two approvals:

1. **Open a pull request.** Its `plan (pull request)` job waits for your approval, because a pull request runs its
   own copy of the workflow, and an approved run holds the App's key. Look at whether the pull request changes
   `.github/workflows/`, then approve: on the run, **Review deployments**, tick `plan-pr`, **Approve and deploy**.
   GitHub notifies you of each waiting run. The plan appears as one comment on the pull request, updated on each
   push. Put `scripts/oob.py`'s output in the pull request yourself.

   The plan is a required check: the pull request can't merge until you've approved the run and the plan has
   succeeded. A pull request that changes only files OpenTofu never reads (`openspec/`, `docs/`, `oob/`,
   `scripts/tests/`, `README.md`, `CLAUDE.md`; the list is in `scripts/plan_needed.py`) skips the plan, which counts
   as passed and asks you for nothing. Anything else is planned, including a file the list doesn't know about.
2. **Merge.** Once CI and `guard` pass on `main`, the `plan (main)` job plans unattended and shows the plan in the
   run's summary, with any delivered file's mode to set below it ("Delivering the guard"). A plan with neither ends
   there.
3. **Read that plan, then approve the `apply` job** (`apply` environment). It applies exactly the saved plan you
   read, sets the modes it listed, then commits the new encrypted state to `main` as the App:
   `chore(tofu): commit the state after applying <sha>`. That commit starts no further plan.

Rejecting the approval applies nothing. To plan `main` again later, for example after drift or a rejection, run
`gh workflow run tofu.yml --ref main`.

| Environment | Who may use it | Approval | Used by |
|---|---|---|---|
| `plan-pr` | any branch | the owner, each run | a pull request's plan |
| `plan-main` | `main` only | none | the plan after a merge, and manual runs |
| `apply` | `main` only | the owner | the apply |

Each holds the same four secrets. OpenTofu declares the environments (`tofu/environments.tf`) but never their
values: the owner sets them from 1Password, so no value is printed or passes through a session:

```sh
export OP_ACCOUNT=l-a-u.1password.com
# Each value is read once, and gh runs only once all four reads succeed, so a failed read can't set
# an empty secret.
pem=$(op read -n "op://troupe.run/troupe-run-infrastructure/private key") &&
  passphrase=$(op read -n "op://troupe.run/troupe-run-infrastructure tofu state/password") &&
  email=$(op read -n "op://troupe.run/troupe-run-infrastructure tofu state/billing email") &&
  cloudflare=$(op read -n "op://troupe.run/troupe-run-cloudflare-dns/credential") &&
  for env in plan-pr plan-main apply; do
    printf '%s' "$pem" | gh secret set TF_VAR_github_app_pem --env "$env" -R troupe-run/infrastructure
    printf '%s' "$passphrase" | gh secret set TF_VAR_state_passphrase --env "$env" -R troupe-run/infrastructure
    printf '%s' "$email" | gh secret set TF_VAR_billing_email --env "$env" -R troupe-run/infrastructure
    printf '%s' "$cloudflare" | gh secret set TF_VAR_cloudflare_api_token --env "$env" -R troupe-run/infrastructure
  done
unset pem passphrase email cloudflare
```

Run it again after rotating any of them.

### Break-glass: applying from your machine

When CI can't apply (GitHub Actions down, or the workflow itself broken), apply locally. Do it only while no `tofu`
run is in progress: nothing locks the state between CI and your machine.

1. On a branch named after the change, `uv run scripts/tofu.py plan -out=change.tfplan`, and show the plan to the
   owner.
2. **After the owner approves it,** `uv run scripts/tofu.py apply change.tfplan`.
3. Commit the updated `tofu/terraform.tfstate` on that branch, and merge it through a pull request.

A local apply doesn't set delivered files' modes: only CI's apply job does. If your apply delivers a file whose mode
differs from its source's (a hook to a new repository, say), the next CI plan of `main` lists it, and its apply sets
it.

**If CI applied but couldn't commit the state,** the run fails and keeps the state as its `state-after-apply`
artifact. Download it (`gh run download <run> -n state-after-apply`), copy it over `tofu/terraform.tfstate` on a
branch, and merge that through a pull request.

**An apply can't delete a repository, but it can archive one and lose its labels.** `prevent_destroy` fails the plan
only while the repository's `module` block is there, refusing a `count = 0` or a change that would replace the
repository. Deleting `module "repo_<name>"` deletes that guard with it: the plan lists the repository and its labels,
ruleset and Dependabot settings as destroyed, and nothing refuses. Only reading the plan stops it. If it's applied,
`archive_on_destroy` archives the repository rather than deleting it, but the apply first deletes its labels, which
takes them off every issue and pull request, its ruleset, and its Dependabot alerts and security updates. To get it
back, unarchive it (`gh repo unarchive troupe-run/<name>`), restore its declaration and `import` blocks, and apply: the
repository is imported again and everything else is recreated, but issues and pull requests don't get their labels back.

To stop managing a repository but keep it, replace its `module` block with:

```hcl
removed {
  from = module.repo_<name>
  lifecycle {
    destroy = false
  }
}
```

The plan then shows it as "forget", with nothing destroyed.

**Unsetting the website's Pages settings can't disable it.** Destroying a Pages site turns Pages off and takes
https://troupe.run down, so the website's Pages site has `prevent_destroy` too, and removing its `pages` setting fails
the plan. Deleting `module "repo_website"` removes that guard with it, so read a plan for a destroyed
`github_repository_pages` before approving it. To stop managing the site but keep it serving, remove `pages` from
`module "repo_website"`, delete the `github_repository_pages` block (and the `pages` variable) from
`tofu/modules/repository/`, and add the block below. A `removed` block refuses an instance key such as `[0]`, and
refuses to run while the resource block still exists.

```hcl
removed {
  from = module.repo_website.github_repository_pages.this
  lifecycle {
    destroy = false
  }
}
```

**Adding a repository:** add it to the `troupe-run-infrastructure` App's installation first, and update the list in
`oob/README.md`. Without the App, OpenTofu sees only the repository's public view. A new repository gets the "protect
main" ruleset unless its `module` block sets `main_ruleset` to `app-only` or `none`. It gets Dependabot alerts and
security updates, secret scanning and push protection from the module too. Its dependency graph, which Dependabot
needs, is turned on by the org's code security configuration: add the repository to `oob/code-security.json` and
have the owner attach the configuration to it (`oob/README.md`).

## How main is protected

`.github` has a ruleset named "app only": nobody but the infrastructure App can change its `main`, not by a push and
not by merging a pull request, and the owner has no bypass. Its files are written from `org-profile/` here, so change
them there. The break-glass is the same as below: edit or disable the ruleset on GitHub, and the next plan restores it.

Every other managed repository has a ruleset named "protect main" on its default branch:
- **Changes reach `main` only through a pull request,** merged with a rebase. No approval is required. A direct push,
  a force-push, a merge commit and a squash are all refused, for the owner too. GitHub refuses to delete a default
  branch anyway.
- **A pull request merges only when its required checks pass.** Each repository's checks are listed in
  `tofu/required-checks.json`, as GitHub names them (`guard (workflow rules)`, not the workflow's job id `guard`), each
  pinned to the App that posts it, so a status of the same name posted by anything else doesn't count. A skipped job
  counts as passed. Here, the guard's eleven OS and Python legs report through one `guard tests` job, and in troupe its
  twelve legs report through one `check` job: they run only when a pull request changes what they test, and a skipped
  matrix job reports under its unexpanded name, which no required check could match. A test checks this repository's list against its workflows; when you rename a job or
  change a matrix in troupe or the website, change the list here too, or their pull requests wait for a check that
  never reports.
- **The owner's bypass works only on pull requests.** An org admin can merge a PR past a rule that blocks it with
  `gh pr merge --rebase --admin` (or the checkbox in the UI), past failing or missing required checks too, and the
  ruleset's insights record it as a bypass. The bypass doesn't allow a merge commit or a squash, and doesn't allow a
  direct push.
- **Break-glass:** an org owner can always edit or disable a ruleset on GitHub. The next plan shows the edit as
  drift, and an apply restores the declared ruleset. Follow it with a PR.

troupe also has a ruleset named "release branches" (`tofu/release.tf`): only the `troupe-run-release` App can create
or update a `release-please--*` branch, and the owner has no bypass. So on troupe a release branch's name says who
wrote it, and the guard exempts it from its branch rule by that name alone (`RELEASE_REPOSITORIES` in
`scripts/guard.py`). Nowhere else reserves the name, so the exemption never holds in another repository or for a
fork's branch. Deletion isn't restricted, so GitHub's delete-on-merge removes the release branch once its pull request
merges, and release-please creates it again for the next release. The break-glass is the same: edit or disable the
ruleset on GitHub, and the next plan restores it.

After a CI apply, the App commits the encrypted state straight to this repository's `main`. Its ruleset lets the App
through for that, and only the App.

## The state passphrase

The passphrase is in 1Password, as the item named in `tofu/secrets.env`. If it is lost, the state can be rebuilt:
- delete `tofu/terraform.tfstate`;
- set a new passphrase;
- run a plan and an apply. The import blocks in `tofu/imports.tf` re-adopt everything.

You lose time, not data.

## Delivering the guard

Each repository that receives the guard (troupe and the website, `guard_targets` in `tofu/guard_delivery.tf`) holds
copies of the guard's files, delivered from this repo by the App straight to its `main` (spec: `guard-delivery`). A
change to the guard reaches them like any other change to the org, with one extra condition:

1. Change the guard's source here, on the change's branch, with its tests.
2. **Merge it.** The `tofu` workflow plans the delivery only after CI is green on all three OSes, and `guard` has
   passed, for that commit. The receiving repositories' own CI doesn't see the files before they land, so this is
   their only check.
3. Read the plan, and approve the apply. Each changed file becomes one commit on each receiving repository's `main`,
   by the App, named `chore(guard): deliver <path> <content hash> from troupe-run/infrastructure`.
4. Check each receiving repository's `guard` and CI runs on those commits.

**A delivered file keeps its source's mode.** `github_repository_file` can't set one, so a file it creates is
`100644`, and git skips a hook that isn't executable. So each plan of `main`, and each pull request's plan, runs
`scripts/hook_modes.py plan`. It reads what is delivered from the saved plan, and lists each file in a receiving
repository whose mode isn't its source's here (`git ls-files -s`), including a hook this apply creates. A listed mode
is a change: the run waits for your approval even when OpenTofu has nothing to do. After the apply succeeds, the
apply job sets each mode as the App with `hook_modes.py apply`: one commit per repository, named
`chore(guard): set the mode of <paths> from troupe-run/infrastructure`, which keeps each file's content. It refuses,
writing nothing, if a listed file's content isn't what the plan read, and it never forces `main`. If it fails, the
run fails, and the next plan (daily at the latest) lists the modes again. The script's docstring has the details.

The probe showed how this behaves (design D3 and D8 of the `development-workflow` change):
- a receiving repository's ruleset lets only the App push to `main`; the owner's own push is still refused;
- a hand edit to a delivered file there fails that repository's `guard` check (`delivered-file`), and shows in the
  next plan, at the latest the next daily one, whose apply restores the file. The check catches mistakes, not
  forgery: a change that gets past it is drift like any other (docs/development-workflow.md, Known gaps);
- an unchanged file is never recommitted.

**To add a repository,** its `main` must first hold `openspec/`, a `scripts/check.py` that runs its checks, and docs
that say to install uv, through its own pull request, and none of the delivered paths (spec: `guard-delivery`). Then
add it to `guard_targets` and `depends_on`, give its module `app_bypass_id`, and require `guard (workflow rules)` in
`tofu/required-checks.json` (`scripts/tests/test_required_checks.py` fails without it).

**If a delivery breaks a repository,** fix the source here and deliver again: no hook there can block a delivery. A
person can also grant themselves a local override in a clone of it.

**To stop delivering to a repository,** in this order:
1. Drop `.github/guard-delivery.json` from its delivery, and apply. The App deletes it from that repository, which
   turns `delivered-file` off there. It has to go first, while the App can still push.
2. Replace its remaining delivery resources with `removed` blocks (see "Changing the org"). That leaves the files in
   the repository, which then change through its own workflow.
3. Remove it from `guard_targets` and `depends_on`, remove `app_bypass_id` from its module, and drop
   `guard (workflow rules)` from its required checks.

## Licence

[Apache-2.0](LICENSE). The troupe name, logo, mark and characters are trademarks of HPS.GD PTY LTD, and aren't
covered by the licence.
