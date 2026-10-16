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
      Superseded by 3.5: design D4 was revised on 2026-10-16, after the dependency graph was found off
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
- [x] 2.5 The owner creates the "troupe-run baseline" configuration (design D4) and attaches it to the probe only,
      with the commands given at the time (`gh api -X POST orgs/troupe-run/code-security/configurations ...`, then
      `.../{id}/attach` with `scope: selected` and the probe's ID, 1421864669). Verify `gh api
      orgs/troupe-run/code-security/configurations` lists it with exactly D4's settings, `gh api
      repos/troupe-run/infra-probe-security/code-security-configuration` names it, and the probe's
      `dependency-graph/sbom` returns 200
      The vulnerable pin (`requirements.txt`, `requests==2.19.0`, 5e43181) was pushed at 08:37 UTC, before the
      configuration: no alert and no pull request after an hour, and the SBOM returned 404 (design, Context)
      Done 2026-10-16. The owner created "troupe-run baseline" (id 284304) on the third try: GitHub refused
      `code_security`/`secret_protection` on this plan, then needed `advanced_security: enabled` (design D4).
      Read back: `advanced_security`, `dependency_graph`, `dependabot_alerts`, `dependabot_security_updates`,
      `secret_scanning` and `secret_scanning_push_protection` `enabled`, every other feature `not_set`,
      `enforcement: unenforced`. Attached to the probe (`scope: selected`, 1421864669):
      `code-security-configuration` reads `attached`, "troupe-run baseline"; the SBOM returns 200 and lists
      `requests`; `security_and_analysis` still reads on
- [x] 2.6 Wait for Dependabot's alert and its security-update pull request on the probe. Verify `gh api
      repos/troupe-run/infra-probe-security/dependabot/alerts` lists the `requests` alert. Record the pull request's
      branch name, commit message, author and whether it has `Signed-off-by`. If none opens within an hour of the
      alert, record that and use Dependabot's documented branch shape (`dependabot/<ecosystem>/<package>-<version>`)
      for 4.1
      Done 2026-10-16. 5 alerts on `requests` (1 high, 4 medium) after the configuration was attached. Pull request
      #1 by `app/dependabot`, found at 11:20 UTC: branch `dependabot/pip/requests-2.33.0`, commit 23dea8c
      `build(deps): Bump requests from 2.19.0 to 2.33.0` (a Conventional Commit, following the repository's
      `build:` history), author `49699333+dependabot[bot]@users.noreply.github.com`, and signed off as
      `dependabot[bot] <support@github.com>`. It does have a sign-off, so the design's "no sign-off, DCO fails" was
      corrected in the docs, design and proposal: the branch rule is what stops it
- [x] 2.7 Delete the probe repository, then the probe's scratch copy. Verify `gh api
      repos/troupe-run/infra-probe-security` returns 404 and `git status --short --ignored tofu/probe` shows nothing
      but caches
      Done 2026-10-16: deleted; `gh api repos/troupe-run/infra-probe-security` returns 404; the scratch copy is
      removed, and `git status --short --ignored tofu/probe` prints nothing

## 3. The configuration on the live repositories (design D4, D6, D7)

- [ ] 3.1 The owner attaches the configuration to troupe (1413896926), .github (1413955208), infrastructure
      (1414209818) and website (1408722166), and sets it as the default for new public repositories (`PUT
      .../{id}/defaults`, `default_for_new_repos: public`). Verify, for each of the four, that
      `code-security-configuration` names it and `dependency-graph/sbom` returns 200, that `gh api
      orgs/troupe-run/code-security/configurations/defaults` lists it for `public`, and that each repository's
      `vulnerability-alerts`, `automated-security-fixes` and `security_and_analysis` read on. Record what `gh api
      orgs/troupe-run` reads for the five `*_enabled_for_new_repositories` settings
- [ ] 3.2 The owner creates a new public repository, `troupe-run/infra-probe-defaults`. Verify, with nothing applied to
      it, that its SBOM returns 200 and that alerts, security updates, secret scanning and push protection read on,
      and that `code-security-configuration` names the configuration. Record the result. Then the owner deletes it,
      and `gh api repos/troupe-run/infra-probe-defaults` returns 404. If any feature is off, stop and report to the
      owner before going on
- [ ] 3.3 List the open secret-scanning alerts in all four repositories (design D6). Record each by type and location,
      never content, and report them to the owner. Verify the list is complete: `gh api
      repos/troupe-run/<repo>/secret-scanning/alerts --paginate` for each
- [ ] 3.4 Write `oob/code-security.json` (design D7): the configuration by name with D4's settings, its default, and the
      four repositories it's attached to. Add the checks to `scripts/oob.py`: the configuration (including any
      undeclared one), the default, each managed repository's attachment, and each managed repository's dependency
      graph, where 200 is on, 404 is reported as off, and any other status is an error naming the repository and the
      status. Add tests to `scripts/tests/test_oob.py`, one per behaviour, each named for what it checks, including
      that a non-404 error is never read as "off". Add the row to `oob/README.md`. Verify `uv run scripts/check.py`
      passes, and that `uv run scripts/oob.py` reports none of these checks as different
- [ ] 3.5 In `tofu/org.tf`, set the five `*_enabled_for_new_repositories` attributes to 3.1's recorded values, and
      rewrite their comment: the configuration in `oob/code-security.json` decides new repositories' defaults, and
      these closing-down parameters are only kept in step with what GitHub reads (D4). Verify `uv run
      scripts/check.py` passes

## 4. A Dependabot pull request has a tested path (design D5)

- [x] 4.1 Add a test to `scripts/tests/test_guard_push_and_ci.py` that runs `run_ci` for a branch named like 2.6's
      Dependabot branch, with a conventional commit, in `troupe-run/troupe` and in `troupe-run/infrastructure`
      (parametrised). It checks that the branch-change rule refuses it. Name it for what it checks. Verify it passes,
      and that it fails when `reserved_release_branch` is made to return `True` for that branch (revert afterwards)
      Test added 2026-10-16 with Dependabot's documented branch shape: 2 passed; with `reserved_release_branch`
      returning `True` for `dependabot/` branches, both failed (reverted). Waiting on 2.6 for the observed branch
      Done 2026-10-16 with 2.6's observed branch, author, message and sign-off: 2 passed, each refused by the branch
      rule only (the guard accepts the message); with `dependabot/` exempted in `reserved_release_branch`, both
      failed (reverted, `git diff` clean)
- [x] 4.2 Add a "Dependabot pull requests" section to `docs/development-workflow.md`. In troupe and infrastructure,
      such a pull request is an alert with a fix: take the bump into an issue and an OpenSpec change, and close
      Dependabot's pull request with a link. On the website it merges once `test` passes. Add a Known gaps entry: a
      security fix waits for a person. Verify `uv run scripts/check.py` passes, the docs tests included

## 5. Local plan

- [ ] 5.1 Fast-forward onto `origin/main` (`git log HEAD..origin/main` shows only state commits, or nothing), then
      `uv run scripts/tofu.py plan`, after group 3. Verify the plan has 8 imports (two per repository), each one
      changing nothing, because the configuration has already turned the features on. Any remaining change must be
      one this change declares: list each, and grep every `~`, `+` and `-` line. Record the summary line
      First run, before the configuration (2026-10-16), on 4268fb7's state (nothing ahead on `origin/main`): `Plan: 8 to import, 0 to add, 9 to
      change, 0 to destroy.` Exactly the list above: the four alerts imports change nothing; each repository's
      `github_repository.this` changes only the two `status` values; the org changes only the five attributes.
      No `+` or `-` lines
- [ ] 5.2 Run `uv run scripts/oob.py`. Verify it reports none of the code-security checks as different, and record its
      output for the pull request
      2026-10-16: 5 differences, none from this change: the infrastructure App holds `pages: write`, which isn't
      declared (likely website-pages, #51/#57); troupe specs `flake-hunt`, `python-support` and `quality-check` have
      no `cap:` label; `cap:releases`'s Purpose isn't recorded. After rebasing onto b8e2ee3, which records
      `pages: write` (website-pages), 4 remain. They're unrelated to this change, tracked in #63 (owner,
      2026-10-16), and noted as such in the pull request


## 6. Evidence on GitHub

- [ ] 6.1 Push the branch and open the pull request (`Closes #53`), with 5.1's plan summary, 5.2's output, the probe's
      findings from group 2, and 3.2's and 3.3's results. Tell the owner the run link while `plan (pull request)`
      waits for approval. Verify every required check passes, and that the posted plan matches 5.1's

## Workflow follow-up

- Run `/opsx:archive` on the branch before merging. The owner merges by rebase and approves `main`'s `apply` job.
- After the apply, check each repository: the SBOM returns 200, `vulnerability-alerts` returns 204,
  `automated-security-fixes` reads `enabled: true`, `security_and_analysis` has secret scanning and push protection
  `enabled`, and the next daily plan is clean. Check that the App's state commit after the apply landed (push
  protection didn't refuse it), and that `uv run scripts/oob.py` reports none of the code-security checks.
- Comment on #53 with the pull request and the archived change, check it's closed, and set its card to Done.
