# Tasks

The text was settled with the owner on 2026-10-20 (proposal.md, What Changes). Groups 1 and 2 need nothing more from
the owner apart from approving the PR's plan run. Group 3 opens issues in troupe and website. The apply follows the
merge (Workflow follow-up).

## 1. The declaration and its check (spec: descriptions; design D1, D2)

- [x] 1.1 Write `scripts/tests/test_descriptions.py` first, tagged `@pytest.mark.descriptions`. Its tests: the
      profile carries the tagline as its bold line; a paragraph starts with the sentence; the status line is there;
      tagline plus sentence come to 160 characters or fewer. Each failure names the missing string, or gives the length
      and the limit. Add pure-function tests that feed in a profile with the old sentence and an over-long sentence,
      and check that each is refused with that message. Verify the tests fail because `tofu/descriptions.json`
      doesn't exist yet
- [x] 1.2 Add `tofu/descriptions.json` with the three strings exactly as in design D1, and a `[scopes.descriptions]`
      entry for it in `scripts/check-paths.toml`, next to `dns` and `milestones`. Verify the profile tests still fail
      (the profile has the old paragraph), the length test passes (119 characters), and
      `uv run scripts/guard.py check-scope` names `descriptions` for a change to that file alone
- [x] 1.3 Change the paragraph in `org-profile/profile/README.md` so that it opens with the sentence, leaving the
      source note, tagline, status line and links as they are. Verify `uv run scripts/check.py` passes, and that
      `git diff` shows only the paragraph's lines changing

## 2. GitHub's side (spec: descriptions; design D1, D3, D5)

- [x] 2.1 In `tofu/repositories.tf`, decode `descriptions.json` into a local, with a comment naming the brand guide as
      the reference across repositories (design D3). Set `repo_troupe`'s description to tagline plus sentence and its
      topics to `["ai-agents", "developer-tools", "human-in-the-loop", "python", "workflow"]`. Set `repo_website`'s
      description to "The troupe.run website and landing page" and its topics to `["astro", "website"]`. In
      `tofu/org.tf`, set `description` from the same local. Verify `uv run scripts/check.py` passes (tofu fmt,
      validate)
- [x] 2.2 Fast-forward onto `origin/main` if its state commit is ahead, then run `uv run scripts/tofu.py plan`. Verify
      the plan's every `~`, `+` and `-` line is one of: the org's `description`, troupe's and website's `description`
      and `topics`, and the profile file's content and commit message in `.github`. Nothing else changes, and in
      particular no `homepage_url`
- [ ] 2.3 Record the plan's summary in the PR description as evidence, alongside CI's posted plan. Verify the two
      agree

## 3. The other repositories (design D4)

- [x] 3.1 Open an issue in troupe-run/website with `--project "troupe roadmap"`: record the canonical set in the brand
      guide (tagline, sentence, paragraph, status line, one-line description, page title and the deliberate variants),
      then apply it to `src/content/copy/hero.md` (subtitle), and to `src/pages/index.astro` (title "troupe: your
      agents need a director", and the one-line description plus the status line as the description). Quote the text
      exactly, cite #108 and the owner's decision of 2026-10-20. Link it as a sub-issue of #108. Verify with
      `gh issue view <n> -R troupe-run/website --json projectItems` that its card is there
- [x] 3.2 Open an issue in troupe-run/troupe the same way, to change the README's paragraph so that it opens with the
      sentence, keeping its status paragraph after "Pre-alpha: there's nothing to install yet". Link it as a sub-issue
      of #108. Verify its card is on the board in the same way
- [ ] 3.3 Name both issues in the PR description. Verify the PR body says `Closes #108` and links both

## Workflow follow-up

- Archive the change on the branch, rebase onto `main`'s latest state commit, then push once, so the plan-pr approval
  is asked for once (memory: archive before plan approval).
- After the merge, the owner approves `apply` on main. Then check the org's page, troupe's and website's repository
  pages, and the profile on `.github`, and that a fresh plan is clean (no topic reorder).
- Close-out: check #108 is closed and its card says Done. Comment on #108 with the PR, the archived change and the two
  sub-issues.
