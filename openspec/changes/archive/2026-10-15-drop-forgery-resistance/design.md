## Context

See proposal.md for why. What exists today:

- **The exemption** is `release_branch_by_the_bot` in `scripts/guard.py`, called from `run_ci`. It passes a branch
  only when all of these hold:
  - the name starts with `RELEASE_BRANCH_PREFIX`;
  - the repository is in `RELEASE_REPOSITORIES` (troupe only);
  - `RELEASE_AUTHOR_EMAIL` is set;
  - every commit the branch adds to `origin/main` is authored by that address, and there's at least one.

  The repository comes from `github_ci_inputs`: a push uses the run's repository, and a pull request uses its head
  repository, so a fork's branch carries the fork's name. `ci --repository` supplies it by hand.
- **The exemption exists only on GitHub.** Locally, `commit_branch_change` (pre-commit) has no release exemption. This
  change leaves that as it is.
- **The ruleset** is `github_repository_ruleset.release_branches` in `tofu/release.tf`, on troupe. It holds the
  `creation`, `update` and `deletion` rules over `refs/heads/release-please--*`, and its one bypass is the release App.
  `tofu/probe/main.tf` has a copy behind `probe_release_ruleset`, with toggles that make the App create and commit to
  `release-please--probe` (release-app design D8). The probe has no committed state.
- **The tests** are in `scripts/tests/test_guard_push_and_ci.py`, in the section headed "release-please-prs":
  - the exemption's cases, which monkeypatch a test address and commit as it;
  - a test that the real address matches the API;
  - two tests that every repository in `RELEASE_REPOSITORIES` has a ruleset declared over `release-please--*`;
  - tests for the head-repository inputs and `--repository`.
- **Delete-on-merge was probed on 2026-10-13** (release-app design D8 step 6). With `deletion` in the ruleset, GitHub
  refused its own delete and kept the branch. troupe has `delete_branch_on_merge` on, which is the module's default.

## Goals / Non-Goals

**Goals:**
- On troupe, a release branch's name is the whole test, because GitHub enforces who creates and updates it.
- The release branch goes once its pull request merges.
- Every place that says a GitHub check resists forgery says what the check is actually for.

**Non-Goals:**
- Exempting release branches anywhere GitHub doesn't reserve the name: this repository, forks, and any future
  repository without the ruleset.
- Changing the local hooks, the delivered-file rule's logic, or the daily plan's behaviour. Only how they're
  described changes.

## Decisions

### D1. Drop the author check. Keep the repository limit.

`release_branch_by_the_bot` becomes `reserved_release_branch(branch, repository)`. It returns true when the branch
starts with `RELEASE_BRANCH_PREFIX` and the repository is in `RELEASE_REPOSITORIES`. These go:
- the git call;
- `RELEASE_AUTHOR_EMAIL`;
- "at least one commit", which existed only to stop the author check passing an empty set.

These stay as they are:
- `RELEASE_REPOSITORIES`, with its docstring reworded to say "creation and update";
- `github_ci_inputs`, `_head_repository` and `UnreadableHeadRepositoryError`;
- `ci --repository`.

The author check is the one piece of #47's concern here: GitHub-side code inferring identity from what the pusher
wrote. The repository limit isn't. It doesn't ask who pushed. It asks whether GitHub enforces the name where the
branch lives. In a fork it doesn't, and the owner said not to trust that (proposal).

*Alternative:* trust the name everywhere and drop the repository plumbing. Rejected by the owner: the name means
something only where the ruleset applies.

### D2. The ruleset keeps `creation` and `update`, and loses `deletion`

The change is one line in `tofu/release.tf`, plus its comment, which says deletion is allowed so delete-on-merge
works. The plan shows an in-place update of `github_repository_ruleset.release_branches`.

With `deletion` gone, anyone with write access can delete a release branch. That's harmless: `creation` stops anyone
but the App making it again, so the name stays proof. At worst a deletion makes release-please open a fresh pull
request.

`update` stays. Without it anyone could push to the App's branch, and the name would no longer say who wrote it.

### D3. Probe delete-on-merge first, on a throwaway repository

Release-app D8 showed that `deletion` blocks delete-on-merge. Nobody has shown that removing it lets delete-on-merge
through while `creation` and `update` still hold, so this is probed before troupe changes. The probe's copy of the
ruleset loses `deletion` too, keeping it an exact copy. The steps, on a new `troupe-run/infra-probe-<date>` added to
the infrastructure App's installation, with the App standing in for the release App as before:

1. `probe_release_ruleset` and `probe_release_branch`: the App creates `release-please--probe`.
2. The owner's push to it is refused (`update`).
3. `probe_release_commit`: the App commits to it.
4. The owner opens a pull request from it into `main` and merges it with `gh pr merge --rebase`, with
   delete-on-merge on. **Expected:** the branch is deleted (a `head_ref_deleted` event), and
   `gh api repos/<probe>/branches/release-please--probe` returns 404.
5. The owner's `git push` creating `release-please--probe` again is refused (`creation`).
6. The App creates it again (re-apply with `probe_release_branch`), and it succeeds.

Unset the toggles, then delete the probe repository and the probe's local state. The findings go in this design.

**If step 4 keeps the branch,** GitHub's delete is refused by something other than `deletion`. Stop and ask the owner.
Don't add workarounds.

**Findings (2026-10-15, `troupe-run/infra-probe-20261015`, since deleted).** As GitHub stored it, the ruleset (id
25144363) has the rules `creation` and `update` on `refs/heads/release-please--*`. Its one bypass is the
infrastructure App (`Integration` 5272634, `always`), and it reports `current_user_can_bypass: never` for the owner.
The repository had `delete_branch_on_merge: true` and rebase merges only.

1. **App creates:** succeeded. `github_branch` created `release-please--probe` from `main` (`6aaae48`).
2. **Owner updates:** refused. A push and a force-push from the owner's login both gave `GH013 … Cannot update this
   protected ref.`, and the branch stayed at `6aaae48`.
3. **App commits:** succeeded. `github_repository_file` committed `739cf53` to the branch, authored by
   `troupe-run-infrastructure[bot]` and verified.
4. **Delete-on-merge:** the branch is **deleted**. The owner's login opened probe#1 from the branch and merged it with
   `gh pr merge 1 --rebase`. Its events are `merged`, `closed` and `head_ref_deleted`, and
   `gh api repos/troupe-run/infra-probe-20261015/branches/release-please--probe` returned 404. This is the opposite
   of release-app D8 step 6, where `deletion` made GitHub keep the branch.
5. **Owner recreates:** refused. Pushing `release-please--probe` from the owner's login gave `GH013 … Cannot create
   ref due to creations being restricted.`
6. **App recreates:** succeeded. A re-apply saw the branch gone and created it again.

So dropping `deletion` gives delete-on-merge back, and the name stays reserved: only the App can create the branch
again.

### D4. One apply updates the ruleset and delivers the guard

After the merge, the plan of `main` holds:
- the ruleset's in-place update;
- the delivery of `scripts/guard.py` to troupe.

The pull request's plan shows the same two, since the delivery reads the working tree. Neither order opens anything:
- the old guard is stricter than the new one;
- the ruleset still refuses everyone but the App for `creation` and `update` throughout.

### D5. The principle is written once, and pointed to

`docs/development-workflow.md` gets a short paragraph at the head of Known gaps, which is the one named place:

> GitHub enforces rules that apply to everyone, or that protect a secret, such as an App's key. It doesn't try to
> tell an agent from the owner: agents work with the owner's `gh` login, so GitHub sees one identity. Agents are
> governed locally by the guard's hooks and `gh` allow-list. The owner's review at merge is the gate, and required
> checks are evidence for that review. A GitHub check that a pusher can satisfy by writing an author, naming a branch
> or editing a workflow catches mistakes, not forgery. A rule that GitHub enforces for everyone but an App, like
> `protect main` or troupe's release ruleset, is different: getting past it takes the App's key.

The Known gaps entries are rewritten to match:
- **Forged delivery:** the check catches honest mistakes. A change that gets past it is drift, which the daily plan
  shows.
- **Release exemption:** it's by name, on troupe only, where the ruleset lets only the release App create or update
  those branches. A release branch in a fork or another repository isn't exempt.

`openspec/config.yaml`'s context gains one constraint line that states the principle and cites #47. README's "release
branches" paragraph is reworded:
- the exemption is by name, and holds where the ruleset reserves it;
- the release branch is now deleted on merge.

README's delivery bullet and `tofu.yml`'s header comment are reworded too. They describe drift detection, not
catching forgeries.

### D6. Tests follow the spec's scenarios

The tests in the release-please-prs section are rewritten, each named for what it checks. They use real git repos, as
now, and commit as an ordinary author unless the case is about the bot. The monkeypatched address goes.

| Test | Repository | Commits | Expect |
|---|---|---|---|
| Release PR | troupe | `chore: release main` | pass |
| Any author | troupe | conventional, ordinary author | no branch-rule refusal |
| Infrastructure | `troupe-run/infrastructure` | conventional | branch rule fails |
| Fork | `someone/troupe` | conventional | branch rule fails |
| No repository | none | conventional | branch rule fails |
| Other branch | troupe, not a release branch | bot-authored | branch rule fails |
| Message | troupe | non-conventional | commit-message fails, naming the commit |
| Delivered file | troupe, with `guard-delivery.json` | changes a listed file | delivered-file fails |
| Force push | troupe, rebuilt branch | as now | pass |

These stay: the head-repository input tests, the `--repository` tests and the unreadable-head-repository test. The
`--repository` tests switch to an ordinary author.

These go:
- the address-from-the-API test;
- "someone else's commit, alone or after the bot's";
- "a branch adding nothing";
- "no bot recorded".

The ruleset-coverage helper also checks that the ruleset's rules include `creation = true` and `update = true`. A
ruleset that stopped reserving the name then fails the test, not only one that was removed. Its removal test gains a
case where `creation` is set to false.

The differential rule applies before the rewrite. The message, delivered-file and force-push cases must pass on
`main` with the bot's author, and still pass afterwards with an ordinary one.

## Risks / Trade-offs

- [Anyone with write access can delete a release branch on troupe] → Harmless: only the App can create it again, and
  release-please opens a new pull request on its next run.
- [Delete-on-merge still keeps the branch after `deletion` is gone] → D3's probe finds out before troupe changes, and
  stops for the owner if so.
- [Release-please doesn't recreate a deleted branch] → It creates the branch when none exists, as on troupe's first
  release. The first release after this lands confirms it (Workflow follow-up).
- [The plan holds more than the ruleset update and `guard.py`] → The plan is read before approval. Anything else
  stops the apply.

## Migration Plan

1. On this branch:
   - the probe (D3) and its findings;
   - the guard and its tests;
   - `tofu/release.tf` and `tofu/probe`;
   - the docs and `openspec/config.yaml`.

   `uv run scripts/check.py` passes, and the pull request's plan shows exactly D4's two changes.
2. Archive on the branch. The owner merges by rebase.
3. The owner approves the apply of `main`.
4. Verify:
   - `gh api repos/troupe-run/troupe/rulesets/<id>` shows `creation` and `update` and no `deletion`, and still only
     the release App as bypass;
   - troupe's `scripts/guard.py` matches this repository's;
   - troupe's `guard` and CI runs pass on the delivery commit.
5. Comment on #47 with the PR and the archived change, and close it.

Rollback: revert the merge and approve the apply. That restores `deletion` and delivers the previous guard.
