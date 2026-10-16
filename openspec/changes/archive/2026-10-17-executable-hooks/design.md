# Design: delivered files keep their source's mode

## Context

- **What's on GitHub (2026-10-17).** `website`'s three `.githooks/*` files are `100644`, created by the App's
  deliveries b0cec50, e09c77f and e6bbe8e. `troupe`'s are `100755`. They were committed by hand (2ce56ec, 6c98500)
  before they were imported, and its three content deliveries since (38ce290, 1c2c083, 4d45b60) kept that mode. The
  blob hashes are the same in both. In this repository the hooks are `100755` and every other delivered source is
  `100644`.
- **Why the provider can't fix it.** `github_repository_file` (integrations/github 6.13.0) writes through the Contents
  API, which takes content but no mode. A file it creates is `100644`; a file it updates keeps its mode, as troupe's
  history shows.
- **What can set a mode.** The Git Data API: a tree that names the same blob with mode `100755`, a commit on `main`'s
  head, and a ref update. On governed repositories only the App can do this. `main` is protected with the App as the
  bypass (guard-delivery design D5), and the guard's CI check fails a commit to a delivered file by anyone else.
- **There's already a pattern for it.** The apply job already mints an App token (`actions/create-github-app-token`)
  and commits through the API afterwards (`scripts/commit_state.py`).
- **Activation.** `guard.activate_hooks(root) -> str | None` is the one place hook activation lives. The session-start
  hook calls it, and so does each repository's own `scripts/check.py`, which prints what it returns. `troupe`'s and
  `website`'s `check.py` aren't delivered.
- **Windows.** Git for Windows has no executable bit. It runs a hook whose file starts with `#!`, and ours do.

## Goals / Non-Goals

**Goals:**
- The owner sees and approves a mode change in the plan, as with any other change to a governed repository.
- Nothing lists which files must be executable. The source's mode in this repository's index says it.

**Non-Goals:**
- Failing the guard's CI check in a governed repository when a hook isn't executable. That repository can't fix it,
  so a red check there would block its pull requests for a fault that lies here. The daily plan reports it here
  instead, where the fix is.
- Setting modes after a local break-glass apply. The next CI plan shows the difference and sets it.
- Any file mode other than `100644` and `100755` (symlinks, submodules). No delivered file has one.

## Decisions

### D1. The plan's own JSON says what is delivered

The mode check reads `tofu show -json` of the saved plan. For each `github_repository_file.guard` instance in the
planned values, it gets the repository, the path and the content. It doesn't keep its own list of targets or files,
so it can't disagree with `guard_delivery.tf`, and a repository that this apply adds to the targets is already in it.

The source's mode comes from `git ls-files -s <path>` in this checkout, which is the commit being planned.
`.github/guard-delivery.json` has no source file because it's generated, so its mode is `100644`.

*Alternative:* a `tofu output` of the targets. Rejected: outputs come from the last apply's state, so a target added
by this plan would be missing.

### D2. One tree read per target, compared by blob

For each target, `GET repos/troupe-run/<repo>/git/trees/main?recursive=1` gives each path's mode and blob. A delivered
file needs its mode set when its source is `100755` and either:

- the target's mode differs, or
- the file is absent because this apply creates it, and a created file is always `100644` (D5).

The expected blob is the git blob hash of the planned content (`sha1("blob <len>\0" + content)`), computed with the
standard library. The plan records each entry as `{repository, path, mode, blob}` in `mode-plan.json`. It's uploaded
next to `main.tfplan` and listed in the run summary under the OpenTofu plan, as "Modes to set after the apply".

Reading uses the run's `GITHUB_TOKEN`, since the targets are public. Nothing in the plan job writes.

### D3. A mode difference is a change

The plan job's `changes` output becomes true when OpenTofu has changes or `mode-plan.json` isn't empty. So a
mode-only plan waits for the `apply` environment's approval and applies like any other. Its saved OpenTofu plan has
no changes, and applying it does nothing. Keeping that single apply path is simpler than adding a second job.
`commit_state.py` already skips a state that didn't change.

The pull-request plan runs the same check and posts its list under the plan. It's evidence only: it neither writes
nor needs a token beyond `GITHUB_TOKEN`.

### D4. After the apply, one commit per repository, made only if nothing moved

The apply job runs the fix only if `tofu apply` succeeded. A failed apply's modes stay pending for the next plan.

The plan job outputs the repositories in `mode-plan.json`, and the token step passes them as `repositories:`, so the
token reaches no other repository. For each repository, the fix:

1. reads `main`'s head commit and tree;
2. refuses, naming the repository and the file, if any listed path's blob differs from the planned blob (spec: "A
   file changed since the plan isn't touched");
3. creates a tree on the head's tree with each listed path at the source's mode and the same blob;
4. creates a commit whose parent is the head, with the message
   `chore(guard): set the mode of <path>[, <path>…] from troupe-run/infrastructure`;
5. updates `main` without force. A `main` that moved in between gets a 422, the run fails, and the next plan reads it
   again.

The commit sets no author, so GitHub records it as the App and its bot user. That's the author the guard's
delivered-file check accepts. Like `commit_state.py`, it's a standard-library script with an injectable HTTP layer,
so its tests run offline.

*Alternative (owner's choice, 2026-10-17):* a one-off manual fix with a runbook, or a fix in each clone (`chmod +x`
plus `core.fileMode=false`). Both were rejected: the first relies on memory every time a target is added, and the
second leaves clones that never run activation silent.

### D5. A newly delivered file is fixed in the same apply

D2 counts an absent file whose source is executable as needing its mode set. When the apply creates the file as
`100644`, its blob is the planned content, and D4's step sets the mode right after. A first delivery needs no second
plan.

### D6. Activation reports a hook git would skip, without changing the signature

`activate_hooks` keeps returning `str | None`. Its notice now also names each file in `.githooks/` that git would
skip, because it isn't executable (`os.access(path, os.X_OK)` is false). It's skipped where `os.name == "nt"`. So
`troupe`'s and `website`'s own `check.py` pick it up from the delivered `guard.py` with no change in those
repositories.

The wording depends on whether the file is delivered:

- **Delivered** (named in `.github/guard-delivery.json`): "git skips `.githooks/pre-push`: it isn't executable. It's
  delivered from troupe-run/infrastructure; the next plan there sets its mode."
- **Not delivered** (this repository, the source): it says to run `git update-index --chmod=+x <path>` and commit.

It's a notice, not a refusal (spec: "A hook git would skip is reported"). Refusing commits would block everyone in a
repository whose fix is elsewhere.

## Risks / Trade-offs

- **[A ref update by the App might be refused on a protected `main`]** → Verify it on a throwaway repository with the
  same ruleset shape before the first live apply (task 1.1). Deliveries already push to these `main`s through the
  same bypass.
- **[`github_repository_file` might see a mode commit as drift]** (its `commit_sha` changes) → Verify a plan after
  the throwaway mode commit shows no change (task 1.1), and again live after the first apply (task 5.2).
- **[The approved write isn't an OpenTofu change]** → The run summary lists it under the plan the owner approves, and
  the commit names each file. The source of truth is still this repository's index.
- **[A target's tree is too big for one recursive read (`truncated: true`)]** → Refuse with an error naming the
  repository rather than guess (malformed input is an error). The targets today have a few hundred files.

## Migration Plan

1. Merge. CI's plan of `main` shows three modes to set in `website` and nothing in `troupe`, plus the delivery of the
   new `guard.py` to both. The mode script runs only here, so it isn't delivered.
2. The owner approves. The apply delivers `guard.py`, and the mode step commits `website`'s three modes.
3. Check `git ls-tree origin/main .githooks/` in `website`, and that the next plan is clean.

Rollback: revert the workflow steps. Modes already set stay set, since content deliveries keep the mode.
