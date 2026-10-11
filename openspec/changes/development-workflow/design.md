# Design

## Context

See proposal.md for why. The specs are `development-workflow`, `guard-delivery`, and the deltas to `rulesets` and
`org-profile`.

**The guard today, in `troupe-run/troupe` at `6099deb`:**
- **Code:** `scripts/guard.py`, 1,031 lines, standard library only. Its design is troupe's archived
  `2026-10-11-workflow-guardrails/design.md`, D1–D11, which still hold and aren't repeated here.
- **Tests:** eight files under `scripts/tests/`, with a `conftest.py` that builds temporary git repositories.
  `test_check_activation.py` tests troupe's `check.py`, and `test_guard_docs.py` checks the rules table in
  `docs/development-workflow.md`.
- **Entry points:** `.githooks/` (three two-line shims), `.claude/settings.json` (a SessionStart hook and two
  PreToolUse hooks), and `.github/workflows/guard.yml`, which runs `guard.py ci`.
- **What it assumes about a repository:** `main`, `openspec/changes/`, `scripts/check.py`, `.githooks`. All four
  already hold here.
- **Why the move is cheap:** `scripts/check.py` imports `guard` to turn the hooks on, and that's the only coupling
  to the product.

**The owner's decisions, 2026-10-12 (#8):**
- this repo is authoritative from this change's merge;
- the guard's tests run on three OSes;
- troupe gets the guard by delivery, not by a PR. The App pushes troupe's copies straight to `main`, the way
  `.github`'s files already arrive.

That last decision reverses a constraint from the brief ("changes to a product repo's files arrive as pull requests
through its own checks, never as direct commits"). The owner's reasons:
- a narrow exemption belongs in what may reach `main`, not in troupe's branch rules;
- the credentials and approval OpenTofu already uses are enough.

If a step below can't be done, the fallback is the full workflow in troupe for every delivery: an issue, an OpenSpec
change and a PR.

**Provider facts this relies on** (from adopt-org):
- `github_repository_file` commits as the App, and GitHub verifies those commits.
- It reads back the message of the file's last commit, which is why `org_profile.tf` ignores `commit_message`. That
  ignore is the reason an update reused a stale message.

## Goals / Non-Goals

**Goals:**
- One editable copy of every guard file, here, from this change's merge on.
- The guard governs this repo, and troupe gets exactly this repo's files.
- Every delivery goes through the same plan-and-approve path as any other change to the org.

**Non-Goals:**
- **A security boundary.** As troupe's D1 says, the guard stops honest shortcuts. The `delivered-file` rule's
  author check trusts commit metadata.
- **Delivering when CI goes green.** Delivery is a local plan and apply until #6.
- **Merging a governed repo's own Claude Code settings** with the delivered ones. See the Risks.

## Decisions

### D1. Move the guard unchanged first, then change it

The first commits copy the guard, its tests, the hooks, the settings and the `guard` workflow from troupe at
`6099deb`, byte for byte. Only after they pass here does anything change.

Why not change and move at once?
- **A clean adoption:** troupe's existing files can be imported into state with a plan that shows no change and makes
  no commit. That's the same as `.github`'s adoption, and the `org-profile` spec's byte-for-byte requirement shows
  how.
- **A clear baseline:** any later test failure is caused by a change made here, not by the move.

troupe-specific references are reworded in the second step. The override directory stays `.git/troupe-guard/`: the
org is `troupe-run`, and renaming it would orphan logs in existing clones for no gain.

### D2. What is delivered, and how

`tofu/guard_delivery.tf` declares a `github_repository_file` for each delivered file in each governed repository
other than this one. Today that's only `troupe`. Each source is the same path in this repository, except the delivered
list, which is generated.

| Delivered file | Why it has to be delivered |
|---|---|
| `scripts/guard.py` | every rule |
| `.githooks/pre-commit`, `commit-msg`, `pre-push` | the git layer |
| `.claude/settings.json` | the Claude Code layer |
| `.github/workflows/guard.yml` | the GitHub layer |
| `.github/guard-delivery.json` | the delivered list (`guard-delivery` spec). It names this repo as the source and lists every delivered path, itself included. It is the one delivered file with no source file: OpenTofu generates it (`jsonencode`) from the same list that declares the deliveries, so the list can't disagree with what is delivered. |

**The source files carry their own note,** so the delivered copy is byte-identical to the source, and a drift diff
is exact. The note is true in both places: "Source: troupe-run/infrastructure. Change it there; copies in other
repositories are delivered." `settings.json` can't hold a comment, so the delivered list covers it.

**Rejected: adding the note at delivery time,** by templating in OpenTofu. Each copy would then differ from its
source. Inserting it after a shebang means string surgery in HCL. And a hand edit would show as a diff against
generated text, not against a file anyone can open.

`.github/guard-delivery.json` exists only in a repository that *receives* the guard. That's how the guard tells a
governed repository from its source (D4).

### D3. Delivery commit messages, and the stale-message fix

Every delivered or synced file has this commit message:

```
chore(guard): deliver <path> <first 12 of sha256(content)> from troupe-run/infrastructure
chore: sync <path> <first 12 of sha256(content)> from troupe-run/infrastructure       (.github's files)
```

The message changes exactly when the content does, so `ignore_changes = [commit_message]` goes.

**What the provider does with the message** (probe, 2026-10-12, D8). The adopt-org finding was half right:
- **On import,** it reads the message of the file's last commit into state.
- **After that,** state holds the configured message. GitHub's history is never compared again.

The cases, as the probe showed them:
- **No change:** the plan is clean.
- **A content change:** one commit, with the new message.
- **A hand edit:** the plan shows the content returning, though not the message. The apply restores the content with
  a fresh delivery commit.
- **A message-only difference after an apply** (a hand edit, then a revert): the plan is clean, and nothing is
  committed.
- **A message-only difference after an import:** the plan shows the message changing, and the apply makes an
  **empty** commit (no files changed).

So the stale message came from `ignore_changes` keeping the imported message as the "current" one. Removing it in
group 4 gives each adopted file whose content doesn't otherwise change one empty commit, which resets its message
once. In the live plan that's four files: troupe's `.claude/settings.json` (it can't carry the source note), and
`.github`'s `SECURITY.md`, `profile/README.md` and `.github/dco.yml`. Every commit after that is a real change.

**Until group 4,** the adopted files keep `ignore_changes`, so that adopting them makes no commit.

Both messages pass troupe's `commit-message` rule (scope `guard` matches `[a-z0-9][a-z0-9-]*`). They have to,
because the `guard` check runs on the push to `main`.

**Rejected: naming the source commit's SHA.** It changes on every commit, even when the content doesn't. Worse, it
changes again when the PR is merged by rebase, so a plan from `main` would want to redeliver unchanged files.

### D4. The `delivered-file` rule

A new overridable rule in `guard.py`, documented in `docs/development-workflow.md` like the others. It applies only
where `.github/guard-delivery.json` exists, so it never applies in this repository.

| Layer | Refuses |
|---|---|
| pre-commit | staged changes to any listed path |
| Claude Code PreToolUse (edits) | an edit to a listed path |
| `guard.py ci` | a commit in the range that changes a listed path and whose author isn't the App's bot account (`troupe-run-infrastructure[bot]`) |

**The fix:** change the file in `troupe-run/infrastructure`, and deliver it.

**What an override covers:** a local override covers one local action, as with every rule. The GitHub check ignores
overrides, as it does for every rule.

**Rejected: refusing deliveries by path in a push ruleset.** File-path restrictions aren't something we've shown to
work on Free, and the guard's own check already covers the rule.

### D5. troupe's ruleset lets the App through

`modules/repository` gains `delivery_bypass` (default false). When it's true, the "protect main" ruleset gains a
second bypass actor: `Integration`, `actor_id = 5272634` (the infrastructure App), `bypass_mode = "always"`. `repo_troupe`
sets it to true.

**Why this doesn't widen trust:** the bypass is ruleset-wide, not limited to the delivered files, so the App could
push anything to troupe's `main`. But the App already has org administration write, and can rewrite or delete the
ruleset itself. Whoever holds its key already controls `main`. The bypass makes routine use visible, and
attributable to the App, instead of needing the ruleset turned off.

**Rejected: the owner's `OrganizationAdmin` bypass in `always` mode.** It would undo protect-main's D3, which
exists to stop an agent using the owner's credentials pushing to `main`.

### D6. The App needs Workflows write

GitHub refuses a change under `.github/workflows/` unless the App has the Workflows permission. The App's
permissions today are recorded in `oob/app-installations.json`: administration, contents, issues, members and
organization administration are write; metadata is read.
- **The owner grants it:** on the App's settings page, then accepting the new permission on the installation.
- **Recorded:** `oob/app-installations.json` gains `"workflows": "write"`.

The App doesn't need Pull requests write, because nothing opens a PR.

### D7. No reusable workflow

The brief leaned towards a reusable `guard` workflow here, which troupe would call pinned to a SHA. That's
dropped.
- **Nothing left to share:** delivery already gives troupe this repo's exact `guard.yml`. A reusable workflow would
  add a second mechanism for the same file.
- **The pin breaks:** this repo merges by rebase, so the SHA a branch would pin isn't the SHA that lands on `main`.
  Either troupe pins a commit that `main` never has, or every delivery needs a second plan after the merge.
- **It buys no integrity on Free:** a PR in troupe can change its own workflow file and call something else. Only
  required workflows (Enterprise) close that, and the `delivered-file` rule flags the edit in the meantime.

### D8. Prove it on a probe first

The probe repo is `troupe-run/infra-probe-<date>`. The owner adds it to the App's installation. The probe reuses
`tofu/probe` with the module's `delivery_bypass` and a delivery of two files: a script and a workflow file.
1. **The bypass:**
   - the App's delivery to `main` is accepted with `delivery_bypass = true`, and refused with it false (so the
     bypass is what allows it);
   - the owner's direct push is still refused.
2. **Workflows write:** delivering a file under `.github/workflows/` succeeds. Recorded with the error for the case
   where it was granted after the first try.
3. **D3's three cases:**
   - an unchanged plan is clean;
   - a content change makes one commit with the new message;
   - a hand edit shows content and message drifting, and the apply restores both.
4. **The guard check on a delivery:** the probe gets this repo's `guard.yml` and `guard.py` as delivered files. A
   delivery push to the probe's `main` passes the check, and a hand-made commit changing a delivered file on a
   branch fails it.

Each output goes in the PR. Then the probe is deleted.

### D9. Order across the two repositories

1. **Here: move unchanged (D1).**
   - Add the CI job.
   - `scripts/check.py` turns the hooks on, and this repo's `.claude/settings.json` and hooks take effect.
   - From this point, commits here go through the guard.
2. **Here: adopt troupe's files.** Import the six existing files into state with byte-identical sources. The plan
   shows imports only, and makes no commit.
3. **Here: the probe (D8).**
4. **Here: generalise and add the rule:**
   - the notes (D2);
   - the delivered list;
   - `delivered-file` (D4) with tests;
   - the reworded wording;
   - `docs/development-workflow.md`;
   - a `CLAUDE.md`;
   - the `CONTRIBUTING.md` link;
   - the commit-message fix (D3).
5. **troupe: the matching change,** through troupe's own issue, OpenSpec change and PR, merged by the owner. It
   removes:
   - troupe's `development-workflow` spec (retired);
   - the guard's tests, keeping `test_check_activation.py`, which tests troupe's own `check.py`;
   - `docs/development-workflow.md`.

   It also points `CLAUDE.md` at this repo's doc. It has to merge before step 6: troupe's old `test_guard_docs.py`
   checks the rules table against `guard.RULES`, so it would fail once `delivered-file` arrives.
6. **Here: the live plan, then the apply.** The plan covers:
   - troupe's ruleset gaining the App bypass;
   - the changed delivered files, plus the new `guard-delivery.json`;
   - `.github`'s `CONTRIBUTING.md`.

   The owner approves the plan and it's applied. Then check three things: troupe's `guard` and CI runs on the
   delivery push are green, the plan is clean, and the oob check reports no differences.
7. **Here: the PR,** closing #8.

### D10. CI here

`ci.yml` keeps its Linux `check` job, which runs everything, the guard's tests included. A new job,
`guard-tests (macOS/Windows, Python 3.12/3.13)`, runs only `scripts/tests/test_guard_*.py`, because those are the
only tests that touch a contributor's machine. The Linux job runs 3.12 only, so 3.13 on Linux is added to the matrix
too.

The `guard` workflow arrives with D1 and runs on every push and PR here, as in troupe.

## Risks / Trade-offs

- **[A broken `guard.py` delivered to troupe refuses every commit there]** →
  - A delivery is applied only from a commit whose CI is green on all three OSes. The README's delivery steps say so,
    and the PR evidence shows it.
  - The way back is another delivery from here, which no troupe hook can block. A person can also override the local
    rules in a troupe clone.
- **[The App's bypass is ruleset-wide]** → D5: no trust beyond what the App already holds.
- **[troupe can't add its own shared Claude Code settings while `settings.json` is delivered whole]** → Personal
  settings stay in `settings.local.json`. If troupe needs shared settings of its own, a later change merges a
  delivered fragment with a local one. That isn't needed today.
- **[Seven delivery commits each start troupe's CI]** → Its concurrency group cancels the superseded runs. One
  delivery a change is the expected pace.
- **[The `delivered-file` author check trusts commit metadata]** → It's not a security boundary (Non-Goals). The plan
  still shows any hand edit that reaches `main` as drift.
- **[The pre-commit check here runs `tofu init` and `validate` on every commit]** → They take under 2 seconds
  (`-backend=false`, no network after the first run), well inside the 10-minute bound.

## Migration Plan

D9 is the plan. Existing troupe clones need nothing: the hooks path and override directory are unchanged.

**Rollback, in order:**
1. **Drop the delivered list from the delivery,** so the App deletes it from troupe. It goes first, while the App
   can still push. Its presence is what turns `delivered-file` on, and a `removed` block would leave it in place.
2. **Replace the other delivery resources with `removed` blocks.** That forgets them and leaves the files in place,
   and troupe's copies become editable through troupe's own workflow again.
3. **Remove `delivery_app_id` from `repo_troupe`.**
