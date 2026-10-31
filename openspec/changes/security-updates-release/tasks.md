# Tasks

## 1. Probe: release-please honours an override on a rebase merge through a merge queue (design D1, D2)

- [x] 1.1 Read what the probe copies: troupe's `main` ruleset's merge-queue settings (`gh api
      repos/troupe-run/troupe/rulesets` and the ruleset by id), and the exact `release-please` version
      release-please-action v5.0.0 bundles (its `package-lock.json` at the tag). Note both on #240. Verify the note
      names the merge method, the queue's settings and a `17.x.y` version
- [x] 1.2 Create `troupe-run/infra-probe-release-override` (`gh repo create troupe-run/infra-probe-release-override
      --public --add-readme`), and push the layout from design D2: `packages/a` and `packages/b`, each with a
      `pyproject.toml`, a root `uv.lock` placeholder, `release-please-config.json` (linked group,
      `bump-minor-pre-major`, `bootstrap-sha` at this commit), `.release-please-manifest.json` at `0.1.0`, and a
      `workflow_dispatch` workflow that runs `npx release-please@<1.1's version> release-pr --dry-run` with
      `permissions: {contents: read, pull-requests: read}`. Then add a ruleset requiring a pull request and a merge
      queue with 1.1's settings. Verify `gh api repos/troupe-run/infra-probe-release-override/rules/branches/main`
      lists `pull_request` and `merge_queue`, and a dispatched dry run before any pull request proposes no release
- [x] 1.3 Open pull requests A, B and C from design D2, each one commit, with A's and C's descriptions holding the
      override block, and merge each through the queue (`gh pr merge <n> --rebase -R
      troupe-run/infra-probe-release-override`). Verify `gh pr view <n> --json mergeCommit,commits` shows each merge
      commit equals the single commit now on `main` (`git log` of the probe), and record whether it does
- [x] 1.4 Dispatch the dry run and save its log. Verify it passes design D2's test: version `0.1.1` for the group, A
      under bug fixes, and neither B nor C listed. If it doesn't, stop: post the log on #240, and ask the owner with
      AskUserQuestion which of design D1's alternatives to take, before any task in groups 2 to 5
- [x] 1.5 Case D: open and merge a fourth pull request like A without an override, run the dry run, add the override
      to its description after the merge, and run it again. Verify D is missing from the first output and listed in
      the second. If it isn't listed, take the recovery out of 5.1 and say so on #240
- [x] 1.6 Post the probe's findings on #240 (setup, each pull request's merge commit, the dry-run excerpts for 1.4 and
      1.5), then delete the probe (`gh repo delete troupe-run/infra-probe-release-override --yes`). Verify `gh repo
      view troupe-run/infra-probe-release-override` fails, and the comment is on #240

## 2. The declaration of what ships (design D4; spec: "The ecosystems whose runtime dependencies ship are declared once")

- [x] 2.1 Write the tests first, in `scripts/tests/test_dependabot_config.py`: the declaration names troupe's `uv` and
      nothing else; a copy naming `npm` for troupe fails the check, naming troupe and `npm`; a copy naming an
      undeclared repository fails naming it; and every generated `dependabot.yml` is byte-for-byte what `main`
      generates (the files in `tofu/dependabot/`). Verify the new tests fail before 2.2, for the missing key only
- [x] 2.2 Add `"releases": {"troupe": ["uv"]}` to `tofu/dependabot.json` and its validation to
      `scripts/dependabot_config.py`, next to the `directories` check, so `scripts/check.py` runs it. Verify 2.1's
      tests pass, `uv run scripts/check.py` passes, and `git diff tofu/dependabot/` is empty

## 3. The override (design D1, D3, D5; spec: "A shipped runtime dependency's security update releases a fix", "A run never takes an override away")

- [ ] 3.1 Write a test first that passes on this branch before any script change: for a set of pull requests that
      don't qualify (a version update, a `chore(deps-dev):` security update, a security update in website and from
      troupe's `github-actions`), the planned actions and the description written are exactly what the current script
      produces. Keep it as the test that nothing else changes (rule: differential tests for rewrites). Verify it
      passes before 3.2
- [ ] 3.2 Write the tests for each scenario of the two spec requirements in `scripts/tests/test_dependabot_issues.py`,
      using a troupe fixture whose shape is copied from a real Dependabot pull request (e.g. troupe's eventsourcing
      one, `gh api repos/troupe-run/troupe/pulls/<n>`), not hand-written: an override added with the closing line in
      one write; one put back after a rewrite; one present (with any content) left alone; none added when removed by
      hand from a pull request that no longer qualifies; the override's text is the title with `fix(deps):`. Verify
      they fail before 3.3, for the missing behaviour only
- [ ] 3.3 In `scripts/dependabot_issues.py`, read `releases`, add the override rule (design D3), and fold `line` into
      one body action per pull request that carries whatever is missing (design D5), with `describe` naming each part
      and the local dry-run printing it. Update the module docstring. Verify 3.1's and 3.2's tests pass, and `uv run
      scripts/check.py` passes (mypy --strict, ruff)
- [ ] 3.4 Run the script locally (`uv run scripts/dependabot_issues.py`, which only reads) and verify it prints no
      error, and an override only for an open troupe security update, if one exists. Record the output in the pull
      request

## 4. Misses (design D6; spec: "A missed event is reported")

- [ ] 4.1 Write the tests first: a troupe security update rebased three hours ago with its line but no override is a
      miss, is fixed and fails the run; one rewritten ten minutes ago is fixed and isn't a miss; a pull request not due
      an override is never a miss for lacking one. Then widen `misses` to count a missing due override. Verify the
      tests fail before the change and pass after, and `uv run scripts/check.py` passes

## 5. Documentation and troupe

- [ ] 5.1 In `docs/development-workflow.md`'s `dependabot-issues` paragraph, say that a security update to a runtime
      dependency in an ecosystem declared in `tofu/dependabot.json`'s `releases` gets release-please's override, so it
      releases a patch; that the override is never removed by the workflow; and the recovery from design D6 (unless
      1.5 showed it doesn't work). Verify `uv run scripts/check.py` passes (the docs gates)
- [ ] 5.2 Comment on troupe-run/troupe#215 with what `contributing/releasing.md`'s "What bumps what" should say about
      Dependabot's updates (security to a runtime dependency: patch, through this override; version and dev updates:
      nothing on their own), linking this change. Verify the comment is on #215

## Workflow follow-up

- Open the pull request as a draft with `Closes #240`, act on Claude's review of the last push, then mark it ready.
- Archive the change on the branch before merging. The owner merges by rebase through the merge queue.
- After the merge, check the next `dependabot-issues` run on `main` passes. Comment on #240 with the pull request, the
  archived change and the probe. The issue's "Done when" is met by the probe (1.4), so it closes with the merge;
  check its card on the troupe roadmap board says Done. If troupe's first real security update then doesn't show as
  a fix, open a new issue saying it arose from #240 (design, Risks).
