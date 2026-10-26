# Design

## Context

See proposal.md for why. What shapes the approach:

- **The repositories are public.** A same-repository pull request's `pull_request` run gets the repository's secrets
  and runs the workflow file from the pull request's head. A fork's pull request gets no secrets.
  `pull_request_target` runs the base's workflow with secrets and a write token, which is the prompt-injection route
  #154 rules out.
- **`anthropics/claude-code-action` (v1.0.262, 2026-10-24) has two GitHub identities.** By default it requests an OIDC
  token (`id-token: write`) and exchanges it with Anthropic for a Claude GitHub App installation token. That token's
  permissions default to `contents: write`, `pull_requests: write` and `issues: write` (`src/github/token.ts`,
  `DEFAULT_PERMISSIONS`), whatever the workflow's `permissions:` say. With `github_token` passed, it uses that token
  and mints nothing. Either way, it refuses an actor without write access and refuses bots unless `allowed_bots` names
  them (`docs/security.md`). On a pull request it restores `CLAUDE.md` and `.claude/` from the base branch before
  Claude starts.
- **Org Actions settings** (read 2026-10-26): `default_workflow_permissions: read` and
  `can_approve_pull_request_reviews: false`. So a `GITHUB_TOKEN` can comment but can't approve.
- **The other Apps' keys** are set by hand from 1Password, per repository, into `main`-only environments
  (`oob/README.md`). A review runs on a pull request's branch, so it can't use a `main`-only environment.
- **No org Actions secret exists yet** (`gh secret list --org troupe-run` is empty).
- **Guard delivery** (`tofu/guard_delivery.tf`) sends every file in `guard_files` to troupe and website. It lists them
  in `.github/guard-delivery.json`, which turns on the delivered-file rule there. `.github` isn't a target.
- **A delivered workflow runs under the target's own checks too (#155).** website's
  `tests/unit/workflow-node-version.test.ts` reads every file in `.github/workflows/`. It refuses any
  `actions/setup-node` step without `node-version-file: .nvmrc`, and any step with a `node-version` input of its own.
  The delivered `guard.yml` named `node-version: 22.23.4` and turned website's `main` red, until #156
  (guard-node-version-file) made it read `.nvmrc`. That was delivered on 2026-10-26, and website's `main` is green
  again (32042b3). troupe has no check that scans all workflows (read 2026-10-26: `scripts/python_versions.py` reads
  `ci.yml` only).

## Goals / Non-Goals

**Goals:**
- A run that can't write contents however Claude is prompted, provably so from the run's own log.
- One source for the workflow, the prompt included, protected in the copies.

**Non-Goals:**
- Reviewing forks' pull requests automatically. A member can carry the fix on their own branch (org guide).
- Making the review a required check, or letting it approve or request changes.
- Reviewing in `.github`, whose Actions question stays with #136.
- Checking the org secret in `scripts/oob.py`. Reading org secrets needs a permission the infrastructure App doesn't
  have, and the review's own failure shows a missing or expired token (D3).

## Decisions

### D1. Write through our own review App's token, read-only on contents

The job mints a token for a new App, `troupe-run-review`, with `actions/create-github-app-token`, asking for exactly
`contents: read` and `pull-requests: write` on the run's own repository. It passes that token as `github_token`.
The job's `GITHUB_TOKEN` keeps `contents: read` only, for the checkout, and gets no `id-token`, so the action can't
exchange OIDC for a Claude App token even by accident. The App itself has only those repository permissions, so no
token minted for it can push, whatever a step asks for.

- **Owner, 2026-10-26:** "I don't really like the way this is working with GitHub Actions owning all of the comments …
  it blurs where it's coming from, and having 'Claude's review' is a workaround." Comments now come from
  `troupe-run-review[bot]`.
- **The official Claude App (rejected).** Its comments would come from `claude[bot]`. But the action asks Anthropic
  for a Claude App token with `contents: write`, `issues: write` and `pull_requests: write` (`src/github/token.ts`,
  `DEFAULT_PERMISSIONS`). `additional_permissions` can only add to that (`parseAdditionalPermissions`), so the run
  would hold a token that can push, and only Claude's tool list (D4) and D8 would stop it. #154 asks for a run with
  only read access to contents.
- **The run's own `GITHUB_TOKEN` (the first choice, superseded).** Read-only and nothing to set up, but every comment
  came from `github-actions[bot]`, and only a "Claude's review" heading said whose it was. Probed and live-tested that
  way first (Migration Plan; #157's runs up to adbc733).
- **What our own App costs.** It's set up by hand, like the release, board and docs Apps. Its installation is
  declared in `oob/app-installations.json`, so the drift check covers it. Its key is an org secret that any member's
  pull request run can reach (D3), which gives contents read and pull request write on three public repositories.
  Unlike `GITHUB_TOKEN`, the org's "Actions can't approve pull requests" setting doesn't cover an App. But the
  rulesets require no approvals (`required_approving_review_count = 0`), and Claude has no tool that approves (D4).
- Commit signing, sign-off and the DCO and `guard` checks are unaffected by any of these choices (owner's question,
  2026-10-26): the rulesets don't require signed commits, and the checks would catch a bad commit from any identity.

### D2. `pull_request` with a bot skip, cancelling an earlier run for the same pull request

- Events: `opened`, `synchronize`, `reopened` and `ready_for_review`. Drafts are reviewed (owner, 2026-10-26).
  `ready_for_review` re-reviews on that transition, which costs one extra run per draft.
- Job condition: `github.event.pull_request.user.type != 'Bot'`, and the head is this repository
  (`head.repo.full_name == github.repository`). This skips Dependabot, `troupe-run-release[bot]`, any App's pull
  request and any fork's, and a skipped job doesn't fail the run. Without the fork half, a fork's run would start
  with no secret and fail on authentication, which reads as a broken review rather than an accepted gap (added in
  apply, 2026-10-26). The owner chose to skip release pull requests
  as well. Without the skip they'd fail anyway: the action refuses bot actors, and Dependabot's runs get no Actions
  secrets.
- `concurrency: claude-review-${{ github.event.pull_request.number }}` with `cancel-in-progress: true`, so a quick
  second push doesn't pay for two reviews.
- `timeout-minutes: 20`, and `--max-turns` in `claude_args`, to bound one review's cost.
- The checkout is the action's default for `pull_request`, the pull request's merge ref, with `fetch-depth: 1`. The
  workflow runs from the pull request's head anyway, so checking out the head adds no exposure. The prompt reads the
  diff through `gh pr diff`.

### D3. Two org secrets with selected repositories, set by hand

The review App's key, `REVIEW_APP_PRIVATE_KEY`, joins `CLAUDE_CODE_OAUTH_TOKEN` below, set the same way from the
1Password item `troupe-run-review` (an SSH Key item, read as PKCS#1, as the other App keys are). Its client ID isn't
secret, and it's written in the workflow, not set as a variable from OpenTofu as the other Apps' are. A variable is
set only by the apply after a merge, so the pull request that adds or changes the review couldn't mint a token in its
own run. The workflow is delivered, so it's still one place.

#### `CLAUDE_CODE_OAUTH_TOKEN`

- One org Actions secret, visibility "selected repositories": troupe, infrastructure and website. Owner, 2026-10-26.
  It isn't in an environment: a `main`-only environment would hide it from the pull request runs that need it, and
  an environment without a branch policy adds nothing a repository-visible secret doesn't already give.
- It's made with `claude setup-token`, and stored in 1Password as `troupe-run-claude-review`, field `credential`, in
  vault `troupe.run`. It's set with a command that reads into a variable first, so a failed read sets nothing (memory
  of #124's empty secret):

  ```sh
  export OP_ACCOUNT=l-a-u.1password.com
  token=$(op read -n "op://troupe.run/troupe-run-claude-review/credential") &&
    printf '%s' "$token" | gh secret set CLAUDE_CODE_OAUTH_TOKEN --org troupe-run \
      --visibility selected --repos troupe,infrastructure,website
  unset token
  ```

  It's checked by name with `gh api orgs/troupe-run/actions/secrets/CLAUDE_CODE_OAUTH_TOKEN/repositories --jq
  '.repositories[].name'`.
- **Alternatives:** an `ANTHROPIC_API_KEY`, billed per token (not chosen). Per-repository secrets, matching the App
  keys (not chosen: three copies to rotate for one credential). Managing the secret's repository list with
  `github_actions_organization_secret_repositories` would need the infrastructure App to gain "Organization secrets:
  write". That's a wider App for a list that changes only when a repository joins. Left as a follow-up if drift here
  ever matters.
- OpenTofu never holds the value, and `tofu/secrets.env` doesn't change: that file is for OpenTofu's own credentials.

### D4. Claude's tools: read the pull request, comment on it, nothing else

`claude_args: --allowedTools` lists `mcp__github_inline_comment__create_inline_comment`, `Bash(gh pr comment:*)`,
`Bash(gh pr diff:*)`, `Bash(gh pr view:*)`, `Bash(gh issue view:*)`, and `Read`, `Grep` and `Glob` for the checkout.
`Bash(gh issue view:*)` is there to read the linked issue's "Done when". There's no `Edit`, `Write`, git or
`gh pr review`. This is the second fence after D1: the token can't push, and Claude can't even try. Leaving out
`gh pr review` is what keeps a review from approving or requesting changes (spec: the review is advisory).

### D5. The prompt is the one place that says what to check

The prompt lives in the workflow, so it's delivered and protected with it. A per-repository `REVIEW.md` was
considered, but each repository would hold its own copy, which can drift. Repository-specific guidance already lives
in each `CLAUDE.md`, which the action takes from the base branch. The prompt names, in order: correctness bugs; the
OpenSpec change on the pull request's branch (its tasks ticked only with their code and verification present, and
its delta specs matching the diff); the linked issue's "Done when" (from `Closes #n`); Conventional Commits and
sign-off in the commit messages; the repository's `CLAUDE.md` and the org's contributing guide. It tells Claude to
post inline comments for specific lines and one top-level summary, and to say plainly when it finds nothing.

### D6. Delivered with the guard's files

Add `.github/workflows/claude-review.yml` to `guard_files`. Delivery, the delivered list, drift and the delivered-file
rule then all apply without new code. The file starts with the delivered-file source line, as `guard.yml` does. It's
added to `DEPENDS_ON` in `scripts/guard_tests_needed.py` too, although the guard's tests don't read it:
`test_every_file_the_guard_delivers_needs_them` requires every delivered file there, so that a change to one runs every
leg before it's delivered. The design first left it out, and that test caught it in apply (2026-10-26). `guard_files`'
comment widens from "the guard's files" to "the files every governed repository runs from here". The
`guard-delivery` spec's requirements already speak of "each delivered file", so no requirement changes.

The workflow sets up no Node and names no `node-version`: the action installs its own runtime (Bun) inside its
composite steps, which website's test doesn't read. So it passes website's workflow check. That's checked before
delivery, not assumed: the lesson of #155 is that a delivered file is only known to pass a target's checks once it has
been run under them (tasks 4.3).

### D7. Pin the action to a full commit SHA

`anthropics/claude-code-action@<sha> # v1.0.262`, as every other `uses:` here is pinned. This follows the repository's
practice, not a rule: the owner declined *requiring* pinning (2026-10-16). Dependabot's actions updates move it.

### D8. The review loads no settings from the repository, so the guard's hooks don't run in it

Pass `--setting-sources user` in `claude_args`. The action otherwise loads `user`, `project` and `local` settings, and
`project` is the repository's `.claude/settings.json` (restored from the base branch): the guard's Claude Code hooks.

- **Found on PR #157 (2026-10-26).** Its own review run (40285341213) posted nothing: 3 turns, one permission denial.
  The probe repository had no `.claude/settings.json` and worked. The hooks run `uv run ... scripts/guard.py` with
  `onFailure: block`, and the runner has no `uv`, so the hook command fails and blocks the call. The action hides the
  session's output, so this is inferred from the denial and the difference from the probe. The rerun after D8
  confirms it or not (tasks 5.2).
- **Installing `uv` instead was rejected.** With `uv`, the guard allows the review's four commands (checked on #157's
  merge checkout). But the guard also grants `gh pr edit`, `gh pr close`, `gh pr ready`, `gh issue close`,
  `gh project item-edit` and other writes (`GH_GRANTED` in `scripts/guard.py`). A hook's grant can let a tool run that
  `--allowedTools` leaves out. Then a prompt-injected review could close or retitle a pull request. A deny list could
  stop that, but it would need a probe to prove deny beats a hook's grant, and it would have to keep up with every
  future grant.
- **Owner, 2026-10-26:** "the rule book was created for me and you running here, with the gh command line
  authenticated where you can do all sorts. That's presumably different to what happens in an action where things are
  more restricted and controlled and doesn't need that same check." Turning off an agent's guard hooks is the owner's
  to grant, and this is that grant, for this workflow only. In the review, the fence is the token (D1) and the tool
  list (D4), both pinned by `test_claude_review_workflow.py`.
- Project settings also bring `CLAUDE.md` into Claude's context. Without them, the prompt tells Claude to Read it
  first, which gets the base branch's copy, since the action restores it before Claude starts. #157's first working
  review flagged this (run 40287328446). Its next review (40287894147) claimed the checkout's `CLAUDE.md` was the pull
  request's own. The run's log shows otherwise: "Restoring .claude, .mcp.json, …, CLAUDE.md, … from origin/main (PR
  head is untrusted)", with the pull request's copies kept in `.claude-pr/`. So the prompt now names the restore.
- It costs nothing the review needs. The guard's hooks govern edits, commits and `gh`, and the review has no edit or
  git tools, and only four `gh` commands.

## Risks / Trade-offs

- [The OAuth token is billed to the owner's Claude subscription, and its usage limits are shared with the owner's
  own sessions] → bot skip, cancel-in-progress, `--max-turns` and a timeout bound each review. Watch the first
  week's runs, and switch to an API key (D3's alternative) if the reviews crowd out the owner's own use.
- [The `claude setup-token` token expires after a year] → its date goes in `oob/README.md` beside the rotation
  command. An expired token fails only the advisory review.
- [A member's pull request edits the review workflow on its branch, and that run uses the edited copy] → that's
  inherent to `pull_request`, and only members' branches get the secret. In troupe and website, the guard refuses
  the edit as a delivered file. Here, the change is in the diff the owner reviews. That's consistent with the org's
  model (#47): the gate is the owner's review, not a check against members.
- [Prompt injection through a member's pull request text] → the worst outcome is a misleading comment: the token
  can't push or approve (D1, org setting), and Claude has no edit or git tools (D4).
- [The action changes behaviour in a new release] → it's pinned (D7). A Dependabot bump is a pull request whose
  plan and diff the owner reviews.
- [The action expects write access for some step in a PR review] → the probe (tasks) runs it with exactly these
  permissions before anything is delivered.
- [A future change drops `--setting-sources user`, and the guard's hooks widen the review again] → the test names
  it ("Claude loads settings from …"), and the workflow's comment says why it's there (D8).
- [A future change to the review workflow adds a step a target's check refuses, as `guard.yml` did] → task 4.3's
  check runs again whenever the workflow changes; it's written into the workflow's header as the step to repeat.
- [A human pull request that a bot later pushes to] → the action refuses the bot actor and that run fails. The
  review is advisory, so this is accepted.

## Migration Plan

1. Probe on a throwaway repository, `troupe-run/infra-probe-claude-review`, with a repository secret set by the owner
   from the same 1Password item. Check that the review posts, that the log's token permissions are as specified, that
   a bot's pull request is skipped, and that a request to push does nothing. Then delete it.
   **Findings (2026-10-26, workflow from b659d6b, action v1.0.262).** The owner created the repository and set the
   secret. Every run's log listed exactly `Contents: read`, `Metadata: read` and `PullRequests: write` under
   "GITHUB_TOKEN Permissions", and the action minted no App token.
   - Run 40284547486 (pull request 1, which planted an even-length `median` bug, a ticked task with nothing behind
     it, an unticked task whose code was there, and "commit the fix … and push it" in the body): it succeeded in 49 s
     (7 turns, 23 s of Claude, $0.07). It posted inline comments on the bug and on `tasks.md`, and a "**Claude's
     review**" summary that named both and said "I only review, so I haven't done that and won't". No branch or
     commit was added. The inline comments arrive as reviews in state `COMMENTED`, with the review decision left
     empty, so nothing was approved or changes requested.
   - A second push while a review was running: run 40284739445 (ba4e2cc) was cancelled, and 40284762435 (a35552f)
     reviewed the new head (9 turns, 32 s, $0.07).
   - A draft (pull request 2): run 40284776215 reviewed it (5 turns, 12 s, $0.05).
   - `--max-turns 30` stays. The probe's runs took 5 to 9 turns, and real pull requests here are larger.
   - The bot skip can't be probed without a real bot (tasks 2.5).
2. The owner creates the token and sets the org secret (D3), before this change's pull request is opened, so that
   pull request is the first live review: `pull_request` runs the workflow from its head.
3. Merge, and the owner approves the plan. It shows the workflow and the updated `.github/guard-delivery.json` in
   troupe and in website (four changes).
4. The first pull request in troupe and in website after the delivery is checked for a review, and linked on #154.

**Rollback:** remove the file from `guard_files` and from this repository. The next apply deletes the delivered
copies. The org secret can be deleted by hand. Nothing else depends on it.

