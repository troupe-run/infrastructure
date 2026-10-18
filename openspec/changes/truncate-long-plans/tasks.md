# Tasks

## 1. Fixtures from real runs (design D3, D6)

- [ ] 1.1 Take #96's plan text from run 39128121513's `plan (pull request)` log (`gh run view 39128121513 --log`,
  the `tofu show` part of the Plan step) and save it as a fixture under `scripts/tests/`. Verify it's over 60,000
  bytes, holds both `github_repository_file` headers (troupe's and website's) and a `Plan:` line, and that
  `uv run --no-project scripts/plan_secrets.py` passes on it.
- [ ] 1.2 Save a small real plan comment from a recent pull request (its plan section, from `gh api
  .../issues/<n>/comments`) as the under-the-limit fixture. Verify its plan section starts with `<details><summary>Full
  plan</summary>` and ends with `</details>`.

## 2. The renderer (design D1, D2, D3, D4)

- [ ] 2.1 Write `scripts/tests/test_plan_comment.py` first: under the limit, the plan section matches 1.2's byte for
  byte and has no note; over the limit (1.1's plan, `COMMENT_LIMIT`), the body is at most `COMMENT_LIMIT` bytes, lists
  both resource headers and the `Plan:` line above the plan, the plan ends on a whole line of the fixture, the code
  block and `<details>` close, and the note's line and byte counts and link are right; a resource list over a small
  limit exits non-zero and writes nothing; a plan line starting with ```` ``` ```` gets a longer fence; the summary
  target uses a bare code block. Run `uv run pytest scripts/tests/test_plan_comment.py` and see them fail.
- [ ] 2.2 Write `scripts/plan_comment.py` (`--head`, `--plan`, `--plan-url`, `--target comment|summary`, `--out`),
  with `COMMENT_LIMIT` and `SUMMARY_LIMIT` named once at the top. Verify 2.1's tests pass, and that each fails when its
  property is broken (for example, cutting with `[:limit]` instead of at a line).
- [ ] 2.3 Render 1.1's plan as a comment and post it as an issue comment on a throwaway `troupe-run/infra-probe-*`
  repository. Verify GitHub accepts it, the `<details>` and code blocks render closed, and the note and resource list
  show; record the result in design.md; then delete the repository.
- [ ] 2.4 Run `uv run scripts/check.py`, which must pass.

## 3. The workflow (design D5)

- [ ] 3.1 Check whether the pinned `actions/upload-artifact` can upload a single file unzipped (design's open
  question), from the action's README at that version, and record the answer in design.md.
- [ ] 3.2 In `.github/workflows/tofu.yml`, add an upload of `plan.txt` after "The plan holds no key" in `pr-plan`
  (`pr-plan`) and in `plan` (`main-plan`), with an `id` so the next step reads its `artifact-url`. Change "Post the
  plan on the pull request" to write the head as today and build `comment.md` with `plan_comment.py --target
  comment`, and "Show the plan for approval" to do the same with `--target summary` into `$GITHUB_STEP_SUMMARY`. Add a
  workflow test that fails if any step runs `head -c` on `plan.txt`, or if either plan step doesn't call
  `plan_comment.py` with the upload's `artifact-url`; verify each by mutating a copy of the loaded workflow in the
  test. Run `uv run scripts/check.py`.
- [ ] 3.3 On this change's pull request, once the owner approves the plan run, check the posted comment: its plan is
  whole with no note (this change's plan is small), and the `pr-plan` artifact exists on the run and holds the same
  plan. Quote both in the PR.

## Workflow follow-up

- Open the PR with `Closes #98`, with 2.3's probe result and 3.3's check.
- Archive on the branch before the owner merges by rebase.
- After the merge, check the next plan of `main` uploads `main-plan` and shows its plan in the run summary. Comment on
  #98 with the PR and the archived change, check #98 is closed, and set its card to Done.
