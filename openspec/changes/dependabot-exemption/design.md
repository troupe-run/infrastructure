# Design

## Context

See proposal.md for why. Current state, read on 2026-10-27 at infrastructure `1d425ec`:

- **The release exemption is the model.** `reserved_release_branch(branch, repository)` in `scripts/guard.py` exempts
  a `release-please--` branch from `commit-branch-change`, and from `pr-closes-issue`, when `repository` is in
  `RELEASE_REPOSITORIES` (troupe). `tofu/release.tf`'s `release branches` ruleset makes the name proof: `creation`
  and `update` refused, `update_allows_fetch_and_merge = false`, no `non_fast_forward` or `deletion` rule, one bypass
  actor (the release App, `Integration`, `always`), no owner bypass. `release_ruleset_repositories` in
  `scripts/tests/test_guard_push_and_ci.py` reads the tofu text and fails if a repository in `RELEASE_REPOSITORIES`
  loses that ruleset.
- **D5's pin.** `test_a_dependabot_branch_in_a_governed_repository_fails_the_branch_rule` (same file) checks
  `dependabot/pip/requests-2.33.0`, a minor update of `requirements.txt`, is refused in troupe and infrastructure. Its
  comment says a later exemption has to change it deliberately. This change is that.
- **Where the check runs.** `guard.yml` runs on every push (`branches: ["**"]`) and on `pull_request` (`opened,
  edited, synchronize, reopened`). A push has no title; a pull request's head repository comes from the payload. The
  check runs the pull request branch's own `scripts/guard.py`, so a delivered rule reaches an open pull request only
  once its branch is rebased onto `main`.
- **Dependabot's commits**, read from the open pull requests on 2026-10-27:

  | Pull request | Subject | `update-type` | Files |
  |---|---|---|---|
  | website #44 | `chore(deps): Bump zod from 4.6.5 to 4.6.7` | none (security) | `package-lock.json` |
  | website #54 | `build(deps): Bump postcss-selector-parser from 6.1.4 to 6.1.5` | none (security) | `package-lock.json` |
  | website #58 | `chore(deps-dev): Bump @axe-core/playwright from 4.13.0 to 4.14.0` | semver-minor | `package.json`, `package-lock.json` |
  | website #55 | `chore(deps-dev): Bump typescript from 6.0.3 to 7.0.2` | semver-major | `package.json`, `package-lock.json` |
  | troupe #174 | `chore(deps): Bump eventsourcing from 9.5.5 to 9.5.6` | semver-patch | 2 × `pyproject.toml`, `uv.lock` |
  | troupe #175 | `chore(deps-dev): Update uv-build requirement` | none | 9 × `pyproject.toml` |
  | infrastructure #184 | `chore(deps): Bump actions/download-artifact from 8.0.1 to 8.0.2` | semver-patch | `.github/workflows/tofu.yml` (+2 −2) |

  So security updates carry no `update-type`, and their prefix isn't the configured one (`build`). Every commit is
  signed off as `dependabot[bot] <support@github.com>`, and its message ends in an `updated-dependencies` YAML block.
- **Dependabot as a bypass actor.** GitHub's ruleset docs list Dependabot among the actors a bypass list can hold.
  Its App id is 29110 (`gh api /apps/dependabot`). Reports elsewhere say the API takes it as an `Integration` actor,
  and refuses a ruleset that names it in a repository where Dependabot doesn't run (422). None of that is proof that
  Dependabot's own pushes pass a ruleset that refuses everyone else, which is what this change needs (D1).
- **`dependabot_issues.py`** (#172) already counts an update's kind from its title: `TITLE`, `VERSION` and
  `update_type`, "Dependabot's counting" (dependabot-issues design D4).

## Goals / Non-Goals

**Goals:**
- A minor or patch Dependabot update that changes only dependency files passes `guard` with nothing done to it but
  its issue's closing line.
- The exemption can't be claimed by naming a branch: GitHub enforces who writes it, as for release-please.
- Everything but the branch rule still judges a Dependabot pull request.

**Non-Goals:**
- Merging anything automatically. The owner's merge stays the one approval.
- Checking who authored a commit (D3).
- Requirement-range updates (troupe #175's kind). Their versions aren't a version pair, so they take the full path.
  If they turn out to be frequent, a later change can read them.
- Ecosystems beyond `npm`, `uv` and `github-actions`. A new one needs its files added to the list (D4).

## Decisions

### D1. Prove the reservation first, and stop if it fails

A throwaway repository, `troupe-run/infra-probe-dependabot-branches`, gets a small `package.json` and
`package-lock.json` pinned to an old patch release, a `.github/dependabot.yml` for `npm`, and a ruleset matching
D2's (made with `gh api -X POST .../rulesets`, which the guard allows on a probe). It's private, so the probe can't
leak, unless Dependabot needs it public. Then it checks:

1. GitHub accepts the ruleset with Dependabot (`Integration` 29110, `always`) as its only bypass actor.
2. Dependabot opens its pull request (creates the branch) under the ruleset.
3. `@dependabot rebase`, after `main` moves, force-pushes the branch.
4. The owner can't push a new `dependabot/x` branch, push a commit to Dependabot's branch, or use "Update branch".
5. Merging with delete-on-merge removes the branch.

Creating the repository and installing nothing else needs the owner where the permission check refuses it (as on
2026-10-26). The owner runs step 4's pushes, since they use the owner's login. **If 1, 2 or 4 fails, nothing else in
this change is built** (owner, 2026-10-26): the change records the result, the issue gets a comment saying what
failed, and Dependabot's pull requests keep the manual path. If 3 or 5 fails, the change pauses and asks the owner,
since the reservation holds but Dependabot's workflow would need working round. The probe repository is deleted
afterwards.

Alternatives: trusting the commit's author or GitHub's "verified" signature was rejected in #170 (a pusher can write
an author; the signature's reach is unproven), and doing nothing until GitHub documents it leaves every Dependabot
pull request red.

### D2. One ruleset per repository with a Dependabot configuration

`tofu/dependabot.tf` declares `github_repository_ruleset.dependabot_branches`, `for_each` over the same repositories
`local.dependabot_files` has (troupe, website, infrastructure), so a repository gets the ruleset exactly when it gets
a `dependabot.yml`. Its body copies `release_branches`: `refs/heads/dependabot/**`, `creation` and `update` true,
`update_allows_fetch_and_merge = false`, no `deletion` or `non_fast_forward` rule, one bypass actor (`Integration`,
`local.dependabot_app_id = 29110`, `always`). No owner bypass; the break-glass is editing the ruleset on GitHub, which
the next plan shows as drift.

`dependabot/` is Dependabot's default prefix with its default `/` separator. The generated configuration sets neither,
and a test pins that, so the policy can't move Dependabot's branches out from under the ruleset.

The guard's own list, `DEPENDABOT_REPOSITORIES`, names the three repositories. The guard is delivered on its own and
reads nothing from infrastructure, so it can't derive the list. A tofu-text test (`dependabot_ruleset_repositories`,
the release one generalised) fails if a repository in the list has no such ruleset, and if weakening `creation`,
`update` or the pattern leaves it uncovered.

### D3. The name proves who wrote the branch; authors aren't read

Like `reserved_release_branch`, the exemption trusts a `dependabot/` name only where the ruleset makes it true, and
never reads a commit's author. With the ruleset, "only Dependabot's commits" (#174's condition 2) is enforced by
GitHub for everyone, owner included. Reading the author on top would be a check guessed from what a pusher wrote,
which the owner ruled out on GitHub (#47; `docs/development-workflow.md`, Known gaps). Without the ruleset, the name
exempts nothing.

The pull request's title isn't read either: a person with write access can edit it. The update's kind comes from the
commit messages, which only Dependabot can write on a reserved branch, and a push has them too.

### D4. Dependency files, from one list in the guard

`DEPENDENCY_FILES = ("package.json", "package-lock.json", "pyproject.toml", "uv.lock")`, matched by file name in any
directory (troupe's packages each have a `pyproject.toml`). A workflow (`.github/workflows/*.yml` or `.yaml`) counts
only when every added and removed line of its diff, ignoring the `+++`/`---` headers, matches `^\s*(-\s+)?uses:\s`.
Every path must be modified (`M` in `git diff-tree --name-status`): an added, deleted or renamed file isn't a version
bump. Any other path fails the condition, and the refusal names the paths. This covers the three ecosystems the
policy declares; a new ecosystem's files are added here, and a test lists each declared ecosystem against the list so
that's not forgotten.

### D5. Minor or patch, read from each commit

For every commit in the range:

- Its subject, with its Conventional prefix, must match `TITLE` from `dependabot_issues.py` (copied, since the guard
  imports nothing of infrastructure's), giving one dependency and two versions. Both must match `VERSION`, and
  `update_type`'s counting must say `minor` or `patch`. A subject that doesn't match, such as `Update uv-build
  requirement`, or a version that isn't dotted digits, is unreadable and fails the condition.
- Every `update-type:` line in its message must say `version-update:semver-minor` or `version-update:semver-patch`.
  None is fine (security updates have none). One that says major, or anything else, fails it, even if the versions
  count as a patch: two readings that disagree are refused, not reconciled.

A differential test runs the guard's reading and `dependabot_issues.read_update` over every real subject above and
over generated version pairs, and asserts they give the same kind, so the issue and the check can't drift apart.

### D6. One rule, with a better reason

The exemption sits in `run_ci` beside the release one: `commit_branch_change` is skipped only when
`exempt_dependabot_branch(root, commits, branch, repository)` holds. For a `dependabot/` branch in a reserved
repository that fails a condition, `run_ci` returns the usual `commit-branch-change` refusal with the failed
condition added to its problem (the paths, "major", or "versions can't be read") and the fix "take the update through
an OpenSpec change for its issue", linking the Dependabot section. Elsewhere the refusal is unchanged. The exemption
reads nothing it can't parse silently: a condition it can't confirm is a failure with a reason, never a pass.

`pr-closes-issue` isn't exempted: a Dependabot pull request still closes its issue, through the line
`dependabot-issues` writes. The local pre-commit rule has no exemption, so an agent still can't commit on a
`dependabot/` branch.

### D7. Delivery and the open pull requests

One pull request carries the guard, the tests, the docs and the ruleset. Its plan adds three rulesets and changes the
delivered `scripts/guard.py` in troupe and website. `github_repository_file.guard` gains a `depends_on` on the
rulesets, so in troupe and website the reservation exists before the exemption arrives.

Open Dependabot pull requests pick the rule up when Dependabot rebases them (`@dependabot rebase`), or when it next
updates them. After the apply, website #44, #45 and #46 (or their successors) are rebased that way and must pass
`guard`, and website #55 (major) must still fail it, naming the major update. infrastructure's open ones (#182-#186)
are checked the same way.

## Risks / Trade-offs

- **[Risk] Dependabot can't be the ruleset's only writer.** → D1 stops the change before anything is built, as the
  owner decided.
- **[Trade-off] In infrastructure the exemption is live from the merge, the ruleset from the apply.** The guard here
  runs from the branch, so between the merge and the owner's approval of the apply a `dependabot/` branch here isn't
  yet reserved. Agents can't use the gap (the local rule has no exemption, and the owner's review is the gate,
  #47), and the apply follows the merge. Splitting into two pull requests would close it at the cost of a second
  review; not worth it.
- **[Trade-off] "Update branch" stops working on Dependabot's pull requests.** The ruleset refuses it. The docs say to
  use `@dependabot rebase`, which is what Dependabot expects anyway.
- **[Risk] Dependabot changes its commit format.** → The exemption reads nothing it can't parse, so a new format makes
  pull requests red, not wrongly green. The fixtures are real commits, so the test shows what changed.
- **[Trade-off] A copy of `TITLE`/`VERSION`/`update_type` in the guard.** The guard is delivered alone and imports
  nothing from infrastructure. The differential test keeps the copies in step.
- **[Risk] The 422 for repositories where Dependabot doesn't run.** All three have a `dependabot.yml` before the
  ruleset is applied, and `.github`, which has none, gets no ruleset.
