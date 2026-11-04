# Tasks

## 1. Record the Purpose and reword the description

- [ ] 1.1 Read the `runtimes` Purpose from troupe#287's branch
      (`gh api "repos/troupe-run/troupe/contents/openspec/changes/runtimes/specs/runtimes/spec.md?ref=runtimes"`,
      through `scripts/oob.py`'s `purpose()`), and add it to `oob/troupe-spec-purposes.json` where design D1 says.
      Verify the file has 31 entries, its keys are sorted, the entry matches #272's quote, and `git diff` shows only
      that added line
- [ ] 1.2 Set `cap:config`'s description in `tofu/labels/troupe.json` to design D2's text. Verify the file still holds
      36 labels, `git diff` shows only that description, it is 98 characters, and `scripts/tests/test_labels.py`
      passes

## 2. Verify against troupe's main

- [ ] 2.1 Once troupe#287 has merged (design D3), re-read the Purpose from troupe's `main`
      (`gh api repos/troupe-run/troupe/contents/openspec/specs/runtimes/spec.md`, through `purpose()`) and compare it
      with the record. Verify the spec's `Capability:` line still names `cap:config` and `cap:actor-runners`. If the
      Purpose changed, update the record, check design D2 against the new text, and re-run 1.1–1.2's checks. Stop and
      revise the change if the spec is renamed, dropped or names other labels
- [ ] 2.2 Fast-forward the branch onto `origin/main` and run `uv run scripts/oob.py`. Verify it reports nothing about
      troupe's specs or Purposes, and exactly one difference of this change's: the board's `config` option still has
      the old description (design D3). Keep the output for the pull request. Stop and revise the change if it reports
      anything else
- [ ] 2.3 Once the owner approves the pull request's first `plan-pr` run, read its plan comment and verify it shows only
      `cap:config`'s description updated in place on troupe-run/troupe, and nothing else of this change's created,
      changed or deleted (name anything `main` has pending separately). Tick this in the same push as the archive, so
      the owner approves one more run
- [ ] 2.4 Run `openspec validate runtimes-spec-purpose --strict` and verify it passes

## Workflow follow-up

- Open the draft pull request with `Closes #272` once group 1 is done. Mark it ready only after 2.1 and 2.2 have run
  against troupe's `main` (design D3), with `oob.py`'s output from 2.2. Its plan comment is 2.3's evidence. Before the
  second `plan-pr` approval, archive the change and rebase onto `main`'s state commit in one push.
- The owner merges by rebase, through the merge queue, after troupe#287.
- After the merge, the owner reads the `plan (main)` plan, which also lists the `config` option's description to set,
  and approves the `apply` job. Verify the description with `gh label list -R troupe-run/troupe --search cap:config`,
  check `board descriptions (main)` succeeded, then check the next `drift (out of band)` run passes (or re-run that
  job), since the merge's own run checks before the board is set.
- Check #272 is closed and its card on the troupe roadmap board says Done; fix either if not.
- Comment on #272 with the pull request and the archived change.
