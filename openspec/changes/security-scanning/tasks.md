# Tasks

## 1. The features are declared in the module and the org's defaults

- [x] 1.1 In `tofu/modules/repository/main.tf`, set `secret_scanning` and `secret_scanning_push_protection` to
      `enabled` (design D2). Add `github_repository_vulnerability_alerts.this` and
      `github_repository_dependabot_security_updates.this`, both `enabled = true`; the second gets
      `depends_on = [github_repository_vulnerability_alerts.this]` (D1). Comment that deleting either resource turns
      its feature off in every repository. Verify `tofu fmt -check` and `tofu validate` pass, through
      `uv run scripts/check.py`
- [x] 1.2 Add import blocks to `tofu/imports.tf` for both resources in each of `repo_troupe`, `repo_github`,
      `repo_infrastructure` and `repo_website` (id: the repository's name), in the file's existing pattern (D1).
      Verify `tofu validate` passes
- [x] 1.3 In `tofu/org.tf`, set the five `*_enabled_for_new_repositories` attributes for Dependabot alerts, security
      updates, dependency graph, secret scanning and push protection to `true`, and leave
      `advanced_security_enabled_for_new_repositories` `false`. Rewrite the comment above them to give D4's reasons:
      Advanced Security, and the closing-down notice with its fallback. Verify `tofu validate` passes
- [x] 1.4 Update the README: the layout row for `tofu/modules/repository/` names the security features, and "Adding a
      repository" says a new repository gets them from the module. Verify `uv run scripts/check.py` passes, the docs
      tests included

## 2. Probe on a throwaway repository (design D3)

- [x] 2.1 Create `troupe-run/infra-probe-security` (public, with a README). Ask the owner to add it to the
      `troupe-run-infrastructure` App's installation. Set the probe up as `tofu/probe/main.tf`'s header says. Verify
      `gh api repos/troupe-run/infra-probe-security` returns the repository, and record its settings before the probe
      (homepage, description, topics, merge settings, `security_and_analysis`)
      Done 2026-10-16: created; with the org's defaults still off, `vulnerability-alerts` already returned 204 and
      everything in `security_and_analysis` read `disabled`. The probe ran from a scratch copy, so `tofu/probe/`
      stayed clean. A first apply with `main`'s module brought the merge and feature settings to the module's
      values, and the settings after it were recorded as the baseline (`homepage` `null` to `""`, the known
      side effect every live repository has already had)
- [x] 2.2 Apply the probe with the module from group 1. Verify all of these by reading the repository back, and record
      them:
      - `vulnerability-alerts` returns 204;
      - `automated-security-fixes` reads `enabled: true`;
      - `security_and_analysis` has `secret_scanning` and `secret_scanning_push_protection` `enabled`;
      - every setting recorded in 2.1 is unchanged (`homepage` included);
      - a second probe plan shows no changes.
      Done 2026-10-16 with this branch's module: the plan was `2 to import, 0 to add, 2 to change`. Alerts were
      imported with no change, security updates went `false` to `true`, and `github_repository` changed only
      `secret_scanning` and `secret_scanning_push_protection` (38 attributes unchanged). Read back afterwards:
      `vulnerability-alerts` 204, `automated-security-fixes` `enabled: true`, both scanning settings `enabled`,
      and no other recorded setting different from the baseline. `security_and_analysis` still read
      `dependabot_security_updates: disabled` straight after the apply, then `enabled` a few seconds later (a
      read delay). The second plan: `No changes.`, exit 0
- [x] 2.3 Push protection lets the org's commits through. Push a commit holding a copy of the live
      `tofu/terraform.tfstate` to the probe repository, and apply the probe with `probe_delivery = true` (API
      commits, as the live delivery makes them). Verify both are accepted. Record the commit SHAs
      Done 2026-10-16. `git push` of the state: accepted as fc14ea8. `scripts/commit_state.py` commits the state
      through the contents API, so the probe applied `probe_delivery = true` with `probe_note` set to the state's
      exact bytes (`cmp` identical, sha256 prefix 72d5c7c087f0): all four API commits were accepted and GitHub
      verified them (8ddde92 `guard.yml`, d0b49d0 `guard-delivery.json`, 695668a `guard.py`, 1c3768b the state)
- [x] 2.4 The positive control: `git push` a commit whose file holds a fake GitHub token with a valid format and
      checksum, made up for this probe and never a real one. Verify the push is refused by push protection, and
      record the refusal's rule name. If it isn't refused, 2.3 proves nothing: stop and report to the owner
      Done 2026-10-16: refused, `GH013: Repository rule violations found` / `GITHUB PUSH PROTECTION` / "Push cannot
      contain secrets", detected as "GitHub Personal Access Token" at `fake-token.txt:1`. The commit was dropped
      locally and never reached GitHub
- [ ] 2.5 Add a manifest pinning a dependency version that has a published advisory, for example `requirements.txt`
      with `requests==2.19.0`. Wait for Dependabot's security-update pull request. Record its branch name, commit
      message, author and whether it has `Signed-off-by`. If none opens within an hour, record that and use
      Dependabot's documented branch shape (`dependabot/<ecosystem>/<package>-<version>`) for 3.1
- [ ] 2.6 Delete the probe repository, then the probe's state, `README.probe.md` and `terraform.tfvars`. Verify
      `gh api repos/troupe-run/infra-probe-security` returns 404 and `git status --short --ignored tofu/probe` shows
      nothing but caches

## 3. A Dependabot pull request has a tested path (design D5)

- [ ] 3.1 Add a test to `scripts/tests/test_guard_push_and_ci.py` that runs `run_ci` for a branch named like 2.5's
      Dependabot branch, with a conventional commit, in `troupe-run/troupe` and in `troupe-run/infrastructure`
      (parametrised). It checks that the branch-change rule refuses it. Name it for what it checks. Verify it passes,
      and that it fails when `reserved_release_branch` is made to return `True` for that branch (revert afterwards)
      Test added 2026-10-16 with Dependabot's documented branch shape: 2 passed; with `reserved_release_branch`
      returning `True` for `dependabot/` branches, both failed (reverted). Waiting on 2.5 for the observed branch
- [x] 3.2 Add a "Dependabot pull requests" section to `docs/development-workflow.md`. In troupe and infrastructure,
      such a pull request is an alert with a fix: take the bump into an issue and an OpenSpec change, and close
      Dependabot's pull request with a link. On the website it merges once `test` passes. Add a Known gaps entry: a
      security fix waits for a person. Verify `uv run scripts/check.py` passes, the docs tests included

## 4. Local plan

- [x] 4.1 Fast-forward onto `origin/main` (`git log HEAD..origin/main` shows only state commits, or nothing), then
      `uv run scripts/tofu.py plan`. Verify the plan has:
      - 8 imports (two per repository), and each `vulnerability_alerts` import with no change;
      - four in-place updates of `dependabot_security_updates` (`enabled` `false` to `true`);
      - four in-place updates of `github_repository.this`, each changing only `secret_scanning` and
        `secret_scanning_push_protection` in `security_and_analysis`;
      - one in-place update of `github_organization_settings.org`, changing only the five attributes from 1.3;
      - nothing else. Grep every `~`, `+` and `-` line.
      Record the summary line
      Done 2026-10-16 on 4268fb7's state (nothing ahead on `origin/main`): `Plan: 8 to import, 0 to add, 9 to
      change, 0 to destroy.` Exactly the list above: the four alerts imports change nothing; each repository's
      `github_repository.this` changes only the two `status` values; the org changes only the five attributes.
      No `+` or `-` lines
- [ ] 4.2 Run `uv run scripts/oob.py`. Verify it reports no differences, and record its output for the pull request
      2026-10-16: 5 differences, none from this change: the infrastructure App holds `pages: write`, which isn't
      declared (likely website-pages, #51/#57); troupe specs `flake-hunt`, `python-support` and `quality-check` have
      no `cap:` label; `cap:releases`'s Purpose isn't recorded. Left open for the owner

## 5. Evidence on GitHub

- [ ] 5.1 Push the branch and open the pull request (`Closes #53`), with 4.1's plan summary, 4.2's output and the
      probe's findings from group 2. Tell the owner the run link while `plan (pull request)` waits for approval.
      Verify every required check passes, and that the posted plan matches 4.1's

## Workflow follow-up

- Run `/opsx:archive` on the branch before merging. The owner merges by rebase and approves `main`'s `apply` job.
- After the apply, check each repository: `vulnerability-alerts` returns 204, `automated-security-fixes` reads
  `enabled: true`, `security_and_analysis` has secret scanning and push protection `enabled`, and the next daily plan
  is clean. Check that the App's state commit after the apply landed (push protection didn't refuse it).
- After the apply, list secret-scanning alerts in all four repositories (design D6). Report each one to the owner by
  type and location, never by content.
- After the apply, ask the owner to create a new public `infra-probe-*` repository. Read its `security_and_analysis`,
  `vulnerability-alerts` and `automated-security-fixes`, then have it deleted (design D4). If any of the four
  features is off, open a follow-up issue (on the roadmap board) for D4's fallback: a code security configuration
  declared in `oob/`. Record the result on #53.
- Comment on #53 with the pull request and the archived change, check it's closed, and set its card to Done.
