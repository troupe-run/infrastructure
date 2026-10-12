# Tasks

## 1. The read-only App (D2, D11 step 1)

- [x] 1.1 The owner creates the GitHub App `troupe-run-infrastructure-plan` with read-only permissions:
  - administration, contents, issues, members and organization administration: read;
  - metadata: read;
  - no webhook.

  The owner installs it on the same repositories as `troupe-run-infrastructure`, and stores its private key in
  1Password next to the write App's. Verify: `gh api orgs/troupe-run/installations` lists both Apps, with the plan
  App's permissions all `read`.
- [x] 1.2 Record the plan App in `oob/app-installations.json`, and its App and installation IDs in this change's
  design. Add "install both Apps" to the README's "Adding a repository". Verify: `uv run scripts/oob.py` reports no
  differences.

## 2. Probe the assumptions (D8)

- [x] 2.1 Extend `tofu/probe` with the ephemeral `github_app_*` variables, wired as in D3. On a throwaway repository:
  - plan a change as the read-only App with `-out`;
  - apply that saved plan as the write App.

  Verify:
  - the apply succeeds and the change is on GitHub;
  - the plan's `tofu show -json` contains neither key nor either App's ID as a variable value;
  - applying the saved plan without the key supplied fails, rather than using a stored one.
- [x] 2.2 With the read-only App's installation token, attempt a write on the probe repository, for example creating
  a label. Verify: GitHub answers 403. Note any 403 that the read-only plan in 2.1 hit, and add that read permission
  in 1.1.
- [x] 2.3 On a throwaway repository, create the probe environments with the same settings as D2: `apply` (owner
  reviewer, `main` only, no admin bypass) and `plan` (open). Add a small workflow, then show that:
  - a run on a branch requesting `apply` is refused;
  - a run on `main` waits for approval;
  - a pull request's run reaches `plan` and gets its secret (a dummy secret, checked by length only);
  - whether `environment: { name: plan, deployment: false }` avoids a deployment entry on the pull request.

  Verify by each run's outcome, linked in the findings.
- [x] 2.4 Delete the probe repositories and the probe's local state. Record the findings in this design (which D3
  path holds, and whether `deployment: false` works) and in the adopt-org findings memory. Verify:
  `gh repo list troupe-run` shows no probe repository, and `git status` shows no probe state.

## 3. The ephemeral identity and the environments (D3, D2, D11 step 3)

- [x] 3.1 In `tofu/providers.tf`, make `github_app_pem` ephemeral (D3). Verify:
  - `scripts/check.py` passes;
  - a local plan reports no changes;
  - that plan, saved, holds no private key (`tofu show -json` grep) and applies only with the key supplied.
- [x] 3.2 Add `tofu/environments.tf`: `plan-pr`, `plan-main` and `apply` on `infrastructure` with the D2 settings, and
  the `main`-only deployment policies for `plan-main` and `apply`. Verify: `scripts/check.py` passes, and the saved
  plan shows exactly the three environments and the two policies to add.
- [x] 3.3 Show the owner the saved plan. After their approval, apply it, then commit the state. Verify:
  - the next plan reports no changes;
  - `gh api repos/troupe-run/infrastructure/environments` shows all three environments, with the reviewers and
    branch policies as declared.
- [x] 3.4 The owner sets the nine secrets from 1Password (D9). I give the exact commands; the owner runs them.
  Verify: `gh secret list --env` for each of `plan-pr`, `plan-main` and `apply` lists the three names (names only).

## 4. The workflow and the bypass (D1, D4–D7)

- [x] 4.1 Add `.github/workflows/tofu.yml` with:
  - the PR path: plan in `plan-pr` (with `deployment: false`) on the merge ref, posted as one edited comment,
    stopping with a message when no secrets are available;
  - the `workflow_run` and `workflow_dispatch` path, made of the jobs `plan`, `apply` and `state`:
    - `plan` runs in `plan-main` (with `deployment: false`), waits for `guard`, shows the plan in the summary, and
      skips on no changes or on the App's own state commit;
    - `apply` runs in the `apply` environment;
    - `state` uploads the state artifact and makes the `PUT` commit.

  Actions are pinned by SHA, as in `ci.yml`. Verify:
  - `scripts/check.py` passes;
  - `actionlint` passes, if it can be run with `uvx` or `brew`; otherwise say so;
  - after the owner approves the pull request's plan run, a plan comment appears that reports no changes.
- [x] 4.2 Rename the module variable `delivery_app_id` to `app_bypass_id` and set it on `repo_infrastructure`. Update
  the README's "To stop delivering" and the comment in `main.tf`. Verify:
  - `scripts/check.py` passes;
  - a local plan shows exactly one change, the bypass actor added to infrastructure's ruleset;
  - the pull request's CI plan comment, updated by the push, shows the same.
- [x] 4.3 Update the README ("Changing the org", a new "Break-glass: applying from your machine", the secrets
  commands, the "Adding a repository" note), `CLAUDE.md` and `org-profile/CONTRIBUTING.md`: the plan comes from CI,
  and approval happens on the run. Remove the "the state is committed on the change's branch" line. Verify:
  - `scripts/check.py` passes;
  - `grep` finds no remaining instruction to commit state on a branch, except in the break-glass section.
- [x] 4.4 Comment the owner's decisions on #6, if not done already, and link them from the proposal. Verify: the
  comment URL.

## 5. Land it and verify the first CI apply (D11 steps 5–6)

- [x] 5.1 Open the pull request (`Closes #6`). Its evidence:
  - the CI plan comment (after the owner approves its run), showing only the bypass;
  - the local plan and apply from 3.3;
  - the probe's findings.

  Verify: every check is green, and the plan comment is present.

## Workflow follow-up

- Archive on the branch before the merge (`/opsx:archive`), syncing the `ci-apply`, `state-and-apply` and `rulesets`
  specs.
- After the owner merges, check the first CI apply:
  - the `tofu` run plans the bypass, waits for the owner, and applies;
  - `main` gains one App commit `chore(tofu): commit the state after applying <sha7>` that changes only the state;
  - no second plan-and-apply run follows it;
  - a manual `gh workflow run tofu.yml` then reports no changes and asks for no approval.

  Report the run links.
- Comment on #6 and close it; tick `ci-apply` on #1.
