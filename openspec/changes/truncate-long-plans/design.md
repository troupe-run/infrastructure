# Design

## Context

See proposal.md for why. Today two steps in `.github/workflows/tofu.yml` show `$RUNNER_TEMP/plan.txt` (the output of
`tofu show -no-color` on the saved plan, after `plan_secrets.py` has checked it holds no key):

- `pr-plan`, "Post the plan on the pull request": shell builds `comment.md` (heading, `Plan:` line, run link,
  `checks.md`, `modes.md`, then the plan in `<details>` with `head -c 60000`) and posts it with
  `gh pr comment --edit-last --create-if-none`.
- `plan`, "Show the plan for approval": shell appends the same kind of body, with `head -c 900000`, to
  `$GITHUB_STEP_SUMMARY`.

GitHub limits a comment body to 65,536 characters and one step's summary to 1 MiB. `head -c` counts bytes and cuts
anywhere, including inside a UTF-8 character. The other sections already come from tested scripts
(`plan_checks.py`, `hook_modes.py`), each writing a Markdown file the shell `cat`s in.

## Goals / Non-Goals

**Goals:**

- One tested function decides what of the plan is shown, for both places, with each place's limit named once.
- A plan under the limit is shown exactly as today: same `<details>` block on the PR, same code block in the summary.

**Non-Goals:**

- Changing the rest of the comment (heading, `Plan:` line, checks, modes) or how it's posted (`--edit-last`).
- The `apply` job's output and any other summary that doesn't show `plan.txt`.

## Decisions

### D1. A script renders the whole body, so it can measure the whole body

New `scripts/plan_comment.py` (standard library only, like the other scripts) takes the part of the body before the
plan as a file (`--head`, which the workflow still writes as today), the plan (`--plan`), the full plan's link
(`--plan-url`) and the target (`--target comment|summary`), and writes the whole body (`--out`). The plan's room is
the limit minus everything else in the body, including the truncation note and the resource list, so the result is
under the limit by construction, not by a guessed margin.

*Alternative:* keep the shell and only swap `head -c` for a line-aware cut. Rejected: the shell can't count what the
other sections take, and the resource list and note need tests, which this repo writes in Python.

### D2. Limits are counted in UTF-8 bytes, and named once

`COMMENT_LIMIT = 65_000` and `SUMMARY_LIMIT = 1_000_000`, in bytes, are constants at the top of `plan_comment.py`,
chosen by `--target`. A UTF-8 string never has more characters than bytes, so a byte limit under 65,536 keeps a
comment under GitHub's character limit whatever the plan holds. Each leaves a margin under GitHub's figure (536 bytes,
and about 48 KiB) for anything GitHub counts that we don't. Cutting at a line boundary also means a multi-byte
character is never split.

### D3. Resource lines are the plan's two-space `# ` headers

In `tofu show -no-color` output, each resource's header is a line indented by exactly two spaces: `  # <address>
will be created` (or `updated in-place`, `destroyed`, `read during apply`), `  # <address> must be replaced`, `  #
<address> has moved to <address>`, and so on. Comments inside a resource's body (`# (3 unchanged attributes
hidden)`) are indented further. The resource list is every line matching `^  # \S.* (will be|must be|has moved
to) `, in plan order, plus the first line starting `Plan:`. The test fixtures are real `tofu show` output (D6), so
the pattern is checked against what OpenTofu prints, not what we expect it to print.

*Alternative:* read the resource changes from `plan.json` (`resource_changes[].change.actions`). More robust to
wording, but it renders a second, differently worded summary of the same plan; the owner asked for the plan's own
lines, and a reader can match them to the text below. If the pattern misses a header OpenTofu adds later, the plan
text still shows it whenever the plan fits, and the fixture test is where to add it.

### D4. The truncated layout

When the plan doesn't fit, the plan section is:

1. **Resource changes** (`N`), the resource lines and the `Plan:` line, in a code block;
2. the plan, in the same `<details>` (PR) or bare code block (summary) as today, holding whole lines only;
3. after the code block: `Truncated: showing the first L of M lines (B of T bytes). The full plan: [plan.txt](URL).`

The note's own size is reserved using the totals' digit counts, since a shown count never has more digits than its
total. If items 1 and 3 alone don't fit, the script exits non-zero with `plan_comment.py: the resource list and
Plan: line take X bytes, over the <target> limit of Y` and writes nothing, so the step fails and nothing incomplete is
posted (spec: "A summary that can't fit fails the step"). At about 70 bytes a line, that is more than 900 resources on
a pull request.

The code block's fence is one backtick longer than the longest run of backticks anywhere in the plan (at least
three), so file content in the plan can't close it early. CommonMark only closes a fence on a line indented three
spaces or less, but counting every run is simpler and can't be wrong. Today's fixed fence has that
flaw too; fixing it costs one line, and an early close would hide the note.

### D5. The full plan is an artifact of the run

A new step after "The plan holds no key" uploads `plan.txt` with `actions/upload-artifact` (the version this workflow
already pins), as `pr-plan` in `pr-plan` and `main-plan` in `plan`, and its `artifact-url` output becomes the link.
It's uploaded on every run, not only when the plan is long, because the URL is needed before the body is built and
the upload is small. Retention is the repository default, as for the run's log.

*Alternative:* link to the run's log. It needs no new step, but the plan is interleaved with `init` output and the
link can only point at the run, not the plan. A gist would need a new credential. The artifact holds nothing the log
doesn't: `plan_secrets.py` has checked `plan.txt` first, and on a public repository both are readable by anyone
signed in to GitHub.

### D6. Tests

`scripts/tests/test_plan_comment.py`, with fixtures taken from real runs:

- **Under the limit, unchanged.** A small real plan renders byte-for-byte the same plan section as today's shell
  produces (fixture: a posted comment from a recent pull request). This is the "a plan under the limit is shown as
  today" non-goal, written to pass against today's output first.
- **Over the limit.** #96's plan (from run 39128121513's log, over 60 KB, two resources) renders under
  `COMMENT_LIMIT`, holds both resources' header lines (website's among them) and the `Plan:` line above the plan, ends
  the plan on a whole line, closes the block, and carries the note with correct counts and the link.
- **Fails rather than drops.** A plan whose resource list alone exceeds a small limit exits non-zero and writes
  nothing.
- **Fence.** A plan holding a run of backticks, at a line's start or inside it, gets a longer fence.
- **Sensitive content (D7).** A test reads `tofu/guard_delivery.tf` and `tofu/org_profile.tf` and fails unless each
  `github_repository_file`'s `content` is wrapped in `sensitive(`. It's a check of the configuration's text, and is
  named as one. What the plan prints is proven by the probe and by this pull request's plan, not by this test.
- **Modes still read the content.** A `hook_modes.py` test feeds it a `plan.json` resource whose `after_sensitive`
  marks `content`, shaped like the probe's output, and checks it still reads the content and computes the blob id.
- **Workflow.** A test next to `test_ci_workflow.py` fails if any step in `tofu.yml` runs `head -c` on `plan.txt`,
  or if either plan step doesn't run `plan_comment.py` with the upload step's `artifact-url`.

The tests call the render function with a small limit where needed, so the limits stay constants and aren't
parameters of the workflow.

### D7. A file's content is sensitive, so the plan shows its hash (owner, 2026-10-18)

`content` on `github_repository_file.guard` and `github_repository_file.org_profile` is wrapped in `sensitive()`.
The plan then prints `~ content = (sensitive value)` instead of the file. Each `commit_message` already carries
`substr(sha256(content), 0, 12)` (guard-delivery D3, org-profile), so a content change still shows as a hash going
old → new.

Probed offline on OpenTofu 1.13.1 (2026-10-18), with a `terraform_data` resource whose input switches to
`sensitive(file(...))`:

| What | Result |
|---|---|
| Switching an unchanged value to sensitive | `no-op`: no change planned, so no commit and no reused commit message |
| A sensitive value that changes | `~ input = (sensitive value)`, with no content lines |
| `tofu show -json` of that plan | `after` still holds the value, and `after_sensitive` marks it `true` |

`terraform_data` also printed its `output`, which echoes its input. `github_repository_file` has no attribute that
echoes `content`. This pull request's own plan checks both points against the real provider: it must show no change
to any file resource.

*Alternatives:* collapsing heredoc bodies in `plan_comment.py` means parsing text by guesswork, and only hides the
content in the comment, not the log. Moving delivery out of OpenTofu would redesign delivery to fix how it's
displayed. Neither keeps the hash in the plan as simply as this does.

## Risks / Trade-offs

- [GitHub counts the comment limit differently from bytes] → bytes are an upper bound on characters, and the posting
  of the rendered #96 body to a throwaway repository (tasks) proves GitHub accepts it.
- [An artifact needs a GitHub sign-in to download and can expire] → the same holds for the run's log today; the
  resource list in the comment doesn't expire.
- [OpenTofu changes its header wording] → the plan is still shown whole whenever it fits; the fixture test records
  the wording we rely on.
- [A drifted delivered file no longer shows what was changed in the target] → the plan still shows the file being
  restored, and the target's commit history on GitHub shows the change. Accepted by the owner (#98).
- [A later OpenTofu changes how a sensitivity-only change plans, or what JSON output holds] → the version is pinned
  (`OPENTOFU_VERSION`); an upgrade's plan shows it, and `hook_modes.py` refuses a resource with no known content
  rather than guessing.
- [The plan of `main` could now fail its summary step] → only in D4's case of a resource list over about 1 MB, where
  the owner couldn't review the plan from the summary anyway; the apply waits until it's split or planned locally.

## Migration Plan

None beyond merging: both steps change together, and the next pull request's run uses them. Rollback is reverting
the commit.

## Open Questions

- Whether `actions/upload-artifact`'s pinned version can upload `plan.txt` unzipped, so the link opens in the browser
  rather than downloading a zip. Either way the link reaches the full plan; the task checks the action's
  documentation and uses it if it's there.
