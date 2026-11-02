# Tasks

## 1. The declaration is checked (design D1, D3; spec: "A malformed ignore declaration fails the check")

- [ ] 1.1 Write the tests first, in `scripts/tests/test_dependabot_config.py`, beside the `releases` ones: a copy of
      the policy naming `npm` for troupe is named with troupe and `npm`; one naming an undeclared repository is named
      with it; an empty list for troupe's `uv` is named with troupe and `uv`; `troupe` twice is named with troupe,
      `uv` and `troupe`; a policy with no `ignore` has nothing to report. Verify they fail before 1.2, for the missing
      function only
- [ ] 1.2 Add `unknown_ignores` (or similarly named) to `scripts/dependabot_config.py`, run from `generated()` with
      the other checks, and mention `ignore` in the module docstring. Verify 1.1's tests pass and `uv run
      scripts/check.py` passes

## 2. The ignore is rendered (design D1, D2; spec: "An entry ignores only the dependencies declared for it")

- [ ] 2.1 Write the tests first: with a policy whose `ignore` is `{"troupe": {"uv": ["troupe", "troupe-*"]}}`,
      troupe's `uv` entry has `ignore` equal to `[{"dependency-name": "troupe"}, {"dependency-name": "troupe-*"}]` and
      nothing else in each condition; troupe's `github-actions` entry and every infrastructure and website entry have
      no `ignore`; the rendered file reads back as the configuration (`troupe-*` survives YAML). And a test on the real
      `tofu/dependabot.json` that its `ignore` is exactly troupe's `uv` with those two names, and the check reports
      nothing. Verify they fail before 2.2
- [ ] 2.2 Render `ignore` in `entry()` after `labels` and before `exclude-paths`, only when the repository and
      ecosystem have names. Add `"ignore": {"troupe": {"uv": ["troupe", "troupe-*"]}}` to `tofu/dependabot.json`, run
      `uv run scripts/dependabot_config.py`. Verify 2.1's tests pass, `git diff --stat tofu/dependabot/` lists only
      `troupe.yml`, its diff adds only the `ignore` block under `uv`, and `uv run scripts/check.py` passes
- [ ] 2.3 Check the rendered names against troupe's members: list `packages/*` and `plugins/*` names from troupe's
      `main` (`gh api repos/troupe-run/troupe/contents/packages` and `.../plugins`, each `pyproject.toml`'s `name`)
      and confirm each is `troupe` or starts with `troupe-`. Record the list in the pull request

## 3. Documentation

- [ ] 3.1 In `docs/development-workflow.md`'s version-updates paragraph, say that the dependencies an entry ignores
      are declared in `tofu/dependabot.json` too (`ignore`: troupe's `uv` ignores its own workspace members, which
      PyPI's unrelated `troupe` would otherwise shadow), and in `README.md`'s `tofu/dependabot.json` row add the
      ignored dependencies to what the policy holds. Verify `uv run scripts/check.py` passes (the docs gates)

## Workflow follow-up

- Open the pull request as a draft with `Closes #259`, with the diff of `tofu/dependabot/troupe.yml` and 2.3's list.
  Act on Claude's review of the last push, then mark it ready; the plan should show one in-place update,
  `github_repository_file.dependabot["troupe"]`.
- Comment on troupe-run/troupe#254 that troupe's `dependabot-uv-resolve` check can pass only once this is applied.
- Archive the change on the branch before merging. The owner merges by rebase through the merge queue and approves
  the `tofu` workflow's apply.
- After the apply, check troupe's `.github/dependabot.yml` on `main` has the ignore, and that the next Dependabot `uv`
  run in troupe (the push of the file should start one; otherwise the owner uses "Check for updates" on troupe's
  Dependabot page, or it waits for Monday's) finishes without `dependency_file_not_resolvable` and doesn't try to
  update `troupe`. The merge closes #259; comment on it with the PR, the archived change and that run, and check its
  card on the troupe roadmap board says Done. If the run still fails, open a new issue saying it arose from #259,
  rather than reopening it (design D4).
