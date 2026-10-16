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

- [ ] 2.1 Create `troupe-run/infra-probe-security` (public, with a README). Ask the owner to add it to the
      `troupe-run-infrastructure` App's installation. Set the probe up as `tofu/probe/main.tf`'s header says. Verify
      `gh api repos/troupe-run/infra-probe-security` returns the repository, and record its settings before the probe
      (homepage, description, topics, merge settings, `security_and_analysis`)
- [ ] 2.2 Apply the probe with the module from group 1. Verify all of these by reading the repository back, and record
      them:
      - `vulnerability-alerts` returns 204;
      - `automated-security-fixes` reads `enabled: true`;
      - `security_and_analysis` has `secret_scanning` and `secret_scanning_push_protection` `enabled`;
      - every setting recorded in 2.1 is unchanged (`homepage` included);
      - a second probe plan shows no changes.
- [ ] 2.3 Push protection lets the org's commits through. Push a commit holding a copy of the live
      `tofu/terraform.tfstate` to the probe repository, and apply the probe with `probe_delivery = true` (API
      commits, as the live delivery makes them). Verify both are accepted. Record the commit SHAs
- [ ] 2.4 The positive control: `git push` a commit whose file holds a fake GitHub token with a valid format and
      checksum, made up for this probe and never a real one. Verify the push is refused by push protection, and
      record the refusal's rule name. If it isn't refused, 2.3 proves nothing: stop and report to the owner
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
- [ ] 3.2 Add a "Dependabot pull requests" section to `docs/development-workflow.md`. In troupe and infrastructure,
      such a pull request is an alert with a fix: take the bump into an issue and an OpenSpec change, and close
      Dependabot's pull request with a link. On the website it merges once `test` passes. Add a Known gaps entry: a
      security fix waits for a person. Verify `uv run scripts/check.py` passes, the docs tests included

## 4. Local plan

- [ ] 4.1 Fast-forward onto `origin/main` (`git log HEAD..origin/main` shows only state commits, or nothing), then
      `uv run scripts/tofu.py plan`. Verify the plan has:
      - 8 imports (two per repository), and each `vulnerability_alerts` import with no change;
      - four in-place updates of `dependabot_security_updates` (`enabled` `false` to `true`);
      - four in-place updates of `github_repository.this`, each changing only `secret_scanning` and
        `secret_scanning_push_protection` in `security_and_analysis`;
      - one in-place update of `github_organization_settings.org`, changing only the five attributes from 1.3;
      - nothing else. Grep every `~`, `+` and `-` line.
      Record the summary line
- [ ] 4.2 Run `uv run scripts/oob.py`. Verify it reports no differences, and record its output for the pull request

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
