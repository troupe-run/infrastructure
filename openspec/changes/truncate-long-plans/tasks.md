# Tasks

## 1. Fixtures from real runs (design D3, D6)

- [x] 1.1 Take #96's plan text from run 39128121513's `plan (pull request)` log (`gh run view 39128121513 --log`,
  the `tofu show` part of the Plan step) and save it as a fixture under `scripts/tests/`. Verify it's over 60,000
  bytes, holds both `github_repository_file` headers (troupe's and website's) and a `Plan:` line, and that
  `uv run --no-project scripts/plan_secrets.py` passes on it. (Done: `scripts/tests/fixtures/plan-pr96.txt`, 256,078
  bytes, both headers, `Plan:` at line 4722. The log holds `tofu plan`'s output, so the fixture is its part from the
  blank line before "OpenTofu used…" to the `Plan:` line; its first 60,000 bytes equal #96's posted comment byte for
  byte. `plan_secrets.py` needs the keys locally, so instead of a 1Password prompt the evidence is that run's own
  "The plan holds no key" step, which passed on this plan.)
- [x] 1.2 Save a small real plan comment from a recent pull request (its plan section, from `gh api
  .../issues/<n>/comments`) as the under-the-limit fixture. Verify its plan section starts with `<details><summary>Full
  plan</summary>` and ends with `</details>`. (Done: `scripts/tests/fixtures/comment-pr93.md`, #93's whole body, 2,015
  characters as the API reports, a three-resource plan.)

## 2. The renderer (design D1, D2, D3, D4)

- [x] 2.1 Write `scripts/tests/test_plan_comment.py` first: under the limit, the plan section matches 1.2's byte for
  byte and has no note; over the limit (1.1's plan, `COMMENT_LIMIT`), the body is at most `COMMENT_LIMIT` bytes, lists
  both resource headers and the `Plan:` line above the plan, the plan ends on a whole line of the fixture, the code
  block and `<details>` close, and the note's line and byte counts and link are right; a resource list over a small
  limit exits non-zero and writes nothing; a plan holding a run of backticks (at a line's start or inside it) gets a longer fence; the summary
  target uses a bare code block. Run `uv run pytest scripts/tests/test_plan_comment.py` and see them fail.
- [x] 2.2 Write `scripts/plan_comment.py` (`--head`, `--plan`, `--plan-url`, `--target comment|summary`, `--out`),
  with `COMMENT_LIMIT` and `SUMMARY_LIMIT` named once at the top. Verify 2.1's tests pass, and that each fails when its
  property is broken (for example, cutting with `[:limit]` instead of at a line). (Done: 18 tests, a hypothesis
  property test among them. Six mutations of the script, cutting mid-line by bytes, counting characters, a fixed
  fence, no resource list, never refusing, and no note, each fail at least one test.)
- [x] 2.3 Render 1.1's plan as a comment and post it as an issue comment on a throwaway `troupe-run/infra-probe-*`
  repository. Verify GitHub accepts it, the `<details>` and code blocks render closed, and the note and resource list
  show; record the result in design.md; then delete the repository.
- [x] 2.4 Run `uv run scripts/check.py`, which must pass.

## 3. The workflow (design D5)

- [x] 3.1 Check whether the pinned `actions/upload-artifact` can upload a single file unzipped (design's open
  question), from the action's README at that version, and record the answer in design.md. (Done: `archive: false`
  is supported; the artifact is then named after the file, `plan.txt`, so 3.2 uses that, not `pr-plan`/`main-plan`.)
- [x] 3.2 In `.github/workflows/tofu.yml`, add an upload of `plan.txt` (`archive: false`) after "The plan holds no key" in
  `pr-plan` and in `plan`, with an `id` so the next step reads its `artifact-url`. Change "Post the
  plan on the pull request" to write the head as today and build `comment.md` with `plan_comment.py --target
  comment`, and "Show the plan for approval" to do the same with `--target summary` into `$GITHUB_STEP_SUMMARY`. Add a
  workflow test that fails if any step runs `head -c` on `plan.txt`, or if either plan step doesn't call
  `plan_comment.py` with the upload's `artifact-url`; verify each by mutating a copy of the loaded workflow in the
  test. Run `uv run scripts/check.py`. (Done: `test_plan_display_workflow.py` fails on the old `tofu.yml` and
  catches 7 mutations in each job. Run locally on #93's inputs, the new post step's shell reproduces #93's posted
  comment byte for byte.)
- [ ] 3.3 On this change's pull request, once the owner approves the plan run, check the posted comment: its plan is
  whole with no note (this change's plan is small), and the `plan.txt` artifact exists on the run and holds the same
  plan. Quote both in the PR.

## 4. A written file's content is sensitive (design D7)

- [x] 4.1 Write the tests first (design D6). One fails unless `content` on each `github_repository_file` in
  `tofu/guard_delivery.tf` and `tofu/org_profile.tf` is wrapped in `sensitive(`. Name it as a check of the
  configuration's text. The other feeds `hook_modes.py` a `plan.json` resource whose `after_sensitive` marks
  `content`, and checks it still reads the content and its blob id. Run them: the first fails, and the second passes
  already, since the script ignores the marker. (Done: OpenTofu marks it in `planned_values`'s `sensitive_values`,
  which `hook_modes.py` reads, so the test uses that. `test_file_content_sensitive.py` scans every `.tf` file and
  found the drift probe's three file resources too; 5 cases fail on the old config.)
- [x] 4.2 Wrap both `content` expressions in `sensitive()`. Leave `commit_message` as it is: it hashes the source
  directly. Verify 4.1's tests pass and `uv run scripts/check.py` passes (`tofu validate` included). (Done, with the drift probe's
  three file resources in `tofu/probe/main.tf` wrapped too, design D7.)
- [ ] 4.3 On this change's pull request, once the owner approves the plan run, check that the plan shows no change to
  any `github_repository_file` resource and no mode to set (design D7, spec "Hiding the content changes nothing on its
  own"). Quote the plan's `Plan:` / `No changes` line in the PR.

## Workflow follow-up

- Open the PR with `Closes #98`, with 2.3's probe result and the checks from 3.3 and 4.3.
- The first delivery after the merge that changes a delivered file's source: check its plan shows
  `~ content = (sensitive value)`, the commit message's hash going old → new, and none of the file's content.
- Archive on the branch before the owner merges by rebase.
- After the merge, check the next plan of `main` uploads `plan.txt` and shows its plan in the run summary. Comment on
  #98 with the PR and the archived change, check #98 is closed, and set its card to Done.
