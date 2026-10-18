# Tasks

## 1. Regenerate the files

- [x] 1.1 Run `npx -y @fission-ai/openspec@1.14.3 update` (its `--version` prints `1.14.3`). Verify `git diff --stat
      origin/main -- .claude` lists exactly the nine files named in proposal.md, `grep -rh generatedBy .claude` prints
      `generatedBy: "1.14.3"` six times and nothing else, and `git diff --quiet origin/main -- openspec/config.yaml
      .claude/settings.json` succeeds
      Done 2026-10-18: `--version` 1.14.3; exactly the nine files; `generatedBy: "1.14.3"` six times;
      `openspec/config.yaml` and `.claude/settings.json` unchanged. (A first pass with 1.14.2, the issue's version,
      matched website's copies byte for byte; the owner then chose 1.14.3, and that pass was never pushed.)
- [x] 1.2 Regenerate a clean clone of `origin/main` with the same command in the scratchpad, and verify each of the
      nine files here is byte-identical to its copy there (`cmp`), so none was hand-edited. Record the result here
      Done 2026-10-18: the clean clone at `origin/main` (`f8328f8`) changed the same nine files and nothing else; all
      nine byte-identical
- [x] 1.3 Commit (`chore(openspec): regenerate the OpenSpec skills with 1.14.3`), signed off, after `uv run
      scripts/check.py` passes

## 2. Ignore the local settings

- [x] 2.1 Add `.claude/settings.local.json` to `.gitignore`. Verify `git check-ignore -v --no-index
      .claude/settings.local.json` names `.gitignore` (not the personal git config) as the rule's source, and `git
      check-ignore --no-index .claude/settings.json` prints nothing
      Done 2026-10-18: `.gitignore:21:.claude/settings.local.json`; `.claude/settings.json` not ignored (exit 1)
- [x] 2.2 Commit (`chore: ignore .claude/settings.local.json in the repository`), signed off, after `uv run
      scripts/check.py` passes. Verify `git diff --stat origin/main` touches only the nine generated files,
      `.gitignore` and this change's directory

## 3. Pull request

- [ ] 3.1 Open the pull request with `Closes #58`. Verify CI is green, and its plan (once the owner approves that
      run) reads `No changes.`, since none of these files is delivered. Record both here

## Workflow follow-up

- Archive the change on the branch before merging (`/opsx:archive`). The owner merges by rebase.
- After the merge, comment on #58 with the PR and the archived change, then check it's closed and its card says Done.
- website (1.14.2) and troupe (troupe#113, asking for 1.14.2) each move to 1.14.3 in their own pull request.
