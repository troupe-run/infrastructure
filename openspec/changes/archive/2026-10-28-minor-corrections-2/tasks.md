# Tasks

## 1. The board key's description (#143 comment 1)

- [x] 1.1 In `openspec/specs/board-credentials/spec.md`, rewrite the Purpose: the credential the org's automated
  runs use to write to the troupe roadmap board, which is the App's installation, the main-only `board` environments
  on troupe-run/website and troupe-run/infrastructure that hold its key, and the variable that names the App. Name
  both uses: putting an issue a run opened on the board (website's weekly link check, infrastructure's schedule watch
  and `dependabot-issues`), and setting the board's `Capability` options' descriptions after an approved apply
  (spec: labels). Verify by reading it against `tofu/board.tf` and every workflow that reads `BOARD_APP_PRIVATE_KEY`
  (`git grep -n BOARD_APP_PRIVATE_KEY -- .github`), and that `openspec validate board-credentials --type spec
  --strict` passes
- [x] 1.2 Make `README.md:28` (the `tofu/board.tf` row), `tofu/board.tf:1-6` and `oob/README.md:121-126` say the
  same, naming `dependabot-issues` and the board's descriptions. Verify `tofu fmt -check` and `tofu validate` are
  clean (run by `uv run scripts/check.py`), and that the three read consistently with the Purpose
- [x] 1.3 Check the delta `specs/board-credentials/spec.md` renames "The board key is readable from website's main
  only" to "The board key is readable from main only", and nothing else. Verify `openspec validate
  minor-corrections-2 --strict` passes

## 2. Change paths in file headers (#143 comment 2)

- [x] 2.1 Replace each `openspec/changes/<name>/design.md` with `<name> design`, as `tofu/` files cite a change:
  `.github/workflows/dependabot-issues.yml:4` and `scripts/dependabot_issues.py:2` (`dependabot-issues`),
  `.github/workflows/milestones-notice.yml:4` (`rebuild-site-on-milestones`), `.github/workflows/schedules.yml:4`
  (`watch-website-link-check`) and `.github/workflows/tofu.yml:3` (`ci-apply`). Rewrap each comment to its file's
  width. Verify `git grep -nE "openspec/changes/[a-z0-9-]+/design" -- ':!openspec' ':!scripts/tests'` prints
  nothing, and that `uv run scripts/check.py` passes (ruff, mypy and the tests; no workflow linter runs, so read each
  edited header as comment text). Found doing it: the planned exclusion was `scripts/tests/fixtures`, which left one
  hit, `test_guard_commit_rules.py:411`'s made-up change `add-thing`, a test input rather than a header
  citation

## 3. Integration

- [x] 3.1 Run `uv run scripts/check.py` and `openspec validate minor-corrections-2 --strict`, and verify both pass.
  Verify `git diff origin/main --stat` lists only the files named in groups 1 and 2 and this change
- [x] 3.2 Verify the pull request's `plan (pull request)`, once the owner approves it, shows no changes. If the owner
  is away, record that it's waiting rather than ticking it. PR #213's plan for 88f3288: "No changes. Your
  infrastructure matches the configuration.", and no modes to set

## Workflow follow-up

- Open the pull request with a Conventional title (`docs: ...`) and `Closes #143`. Set #143's card to In Progress
  (it already is) and act on Claude's review of the last push.
- Tick, archive (running `openspec validate board-credentials --type spec --strict` on the synced main spec), and
  rebase onto main's state commit in one push, then ask once for the `plan-pr` approval.
- After the owner merges, comment on #143 with the pull request and the archived change, check it's closed and its
  card says Done. Open the next "Minor corrections to batch" issue with `--project "troupe roadmap"`, check it's on
  the board, and update the minor-corrections memory to point at it.
