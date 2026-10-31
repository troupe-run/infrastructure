# Tasks

## 1. The new wording

- [x] 1.1 Rebase this branch onto `origin/main` after its latest state commit. Verify
  `git rev-list --count HEAD..origin/main` is 0.
- [x] 1.2 In `tofu/milestones.json`, change 0.1.0's description to end "Installed with uv" instead of "Installed with
  uv from a tag". Verify `git diff` changes only that line and `uv run scripts/check.py` passes.
- [x] 1.3 Run a local plan. Verify it shows four updates in place, milestone 0.1.0 in each of troupe, infrastructure,
  website and `.github`, each changing only `description`, and nothing created, destroyed or replaced.
- [ ] 1.4 Open a draft pull request with `Closes #236`, using `--body-file`. Verify the CI plan comment, once the
  pull request is ready and its plan has run, shows the same four updates as 1.3.

## Workflow follow-up

- Act on Claude's review of the last push, then archive the change on the branch in the same push as ticking 1.4,
  and rebase onto `main`'s latest state commit before asking for the plan approval (memory: archive before plan
  approval).
- After the owner merges and approves the apply, check on GitHub that milestone 0.1.0's description ends "Installed
  with uv" in all four repositories (`gh api repos/troupe-run/<repo>/milestones?state=all`).
- Check that the merge dispatched a website Deploy run on `main`, and once it and the apply have finished, that
  troupe.run/status/ shows "Installed with uv" for 0.1.0 and no longer "from a tag". If the deploy ran before the
  apply finished, ask the owner to run `gh workflow run deploy.yml -R troupe-run/website`.
- Check #236 is closed with a comment naming the pull request and the archived change, and its card says Done.
