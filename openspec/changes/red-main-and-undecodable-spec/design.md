# Design

## Context

See proposal.md for why. Two independent fixes share one change and one pull request, at the owner's request.

**The gate** (`scripts/main_ci.py`, plans-wait-for-ci design D1-D6) walks `main` as the plan job fetched it
(`origin/main`), finds the commit CI runs on for its head, and polls that commit's newest CI push run. `wait_for_ci`
returns a `Result(passed, sha, summary, error)`. `main()` appends the summary and exits 0 (pass) or 1 (fail). In
`tofu.yml`, every plan-job step after `The commit to plan` is gated on `steps.target.outputs.plan == 'true'`. The gate
step itself also has `github.event_name != 'workflow_run'`. The drift job (`oob`) needs no other job, so it always runs.
`ci.yml` runs on `main` in one cancel-in-progress group (memory: CI on main runs cancel each other), so a newer merge's
push cancels the older run.

**The spec read** (`scripts/oob.py`, `spec_documents`) fetches each troupe spec's `spec.md` inside a `try` that raises
`UnreadableError` naming the spec, then decodes it outside that `try`. `Report.attempt` turns any other exception into
`troupe specs: couldn't read it (<reason>)`, so the drift job doesn't crash. It just loses the spec's name.

## Goals / Non-Goals

**Goals:**
- A run whose CI a newer merge cancelled ends green with nothing planned, and says why.
- Every other way the gate fails today still fails. When unsure, it fails: a false red is safe, but a false
  "superseded" would let an unchecked `main` go unplanned without anyone being told.
- An undecodable troupe `spec.md` is reported unreadable, by name, the same way a failed fetch is.

**Non-Goals:**
- Re-fetching `main` and waiting for the newer commit's CI. The issue rejects this: the run would check CI on one
  commit and plan another, unless the target step were redone too.
- Treating other conclusions (`failure`, `timed_out`, ...) as superseded. Only a cancel comes from a newer push.
- Changing how `plan_target.py` chooses the commit, or anything in the run after CI on a merge.
- Stricter base64 decoding. GitHub's `content` is wrapped with newlines, which `validate=True` would refuse.

## Decisions

### D1. Superseded means: cancelled, and GitHub's `main` is ahead of the checked commit by a commit CI runs on

Only a `completed` run with conclusion `cancelled` triggers the check. The gate then reads
`gh api repos/<repository>/compare/<sha>...main` once, and keeps its `status` and the names in `files`.

| compare answers | outcome |
|---|---|
| `status: ahead`, and `files` names something other than `tofu/terraform.tfstate` | **superseded** (D2) |
| `status: ahead`, and the only file is `tofu/terraform.tfstate` | red: only state commits since, and CI doesn't run on them (ci.yml's `paths-ignore`), so no newer run will plan it |
| `status: identical` | red, as now: `main` hasn't moved, so the cancel was by hand |
| `behind`, `diverged`, or anything else | red, naming the status: an unknown value is an error (learned rule: malformed input is an error) |
| the read fails, or isn't the shape expected | red, with the error |

The commit named in the summary is the newest one since that CI runs on, so the owner knows whose run to watch.
`main`'s head may be the App's state commit after that merge's apply, and CI never runs on that. So the gate walks the
listed `commits` from the newest, reading each one's files (`gh api repos/<repository>/commits/<sha>`, keeping the
file names), and names the first that changes more than `tofu/terraform.tfstate`. That's usually one or two reads,
and only after a cancel. A failed read, or an answer of the wrong shape, fails the run as for red CI. If no listed
commit changes more than the state file, the run fails too, rather than name a guess. That can only happen when the
compare's `files` (the net change) disagrees with its commits. The compare lists at most 250 commits. When
`total_commits` is more than it lists, the newest commits aren't listed, so it reads none and the summary says "the
newest merge on `main`" without a sha. Probed read-only on this repository's real `main`: `a1e39ab...main` gives
`ahead`, with files `["tofu/terraform.tfstate"]` (the App's state commit only), `8038320...main` gives `ahead` with
spec and state files, and `9d29f66...main` gives `identical` with no files.

*Alternatives:* `git ls-remote origin refs/heads/main`. Rejected: it gives the head but not what changed, so the
state-only case would need a fetch and a second walk. Comparing head shas alone ("main's head differs"). Rejected: a
state commit, or a force-push, would read as superseded. Checking for a CI run on the newer commit. Rejected: right
after the push it may not exist yet, which makes it a race, and the compare answers the question directly. The 300-file
cap on `files` doesn't matter: a file appears at most once, so a list that's full can't be all state file.

### D2. The superseded result, and how the workflow skips the rest of the plan

`Result` gains a `superseded: bool = False` field. A superseded result is `passed=True, superseded=True`. Its summary is
one section headed with no plan made: CI on `<short sha> (<subject>)` was cancelled, `main` has since moved on to the
newer merge `<short sha>` (D1), and the run that starts when CI passes on it plans `main`, so nothing was planned here.
It links the cancelled run.

`main()` prints exactly one line to stdout, `superseded=true` or `superseded=false`, and the gate step appends stdout to
`$GITHUB_OUTPUT` (as `plan_target.py` does). The current "CI passed on <sha>" line moves to stderr, because
`$GITHUB_OUTPUT` takes only `name=value` lines. It exits 0 for both a pass and a superseded run, and 1 on red, as now.

The gate step gets `id: ci`. Each later step in the plan job adds `&& steps.ci.outputs.superseded != 'true'` to its
`if:`. That's the guard wait, setup-uv, setup-opentofu, `Plan`, `The plan holds no key`, `Keep the full plan`,
`Modes to set after the apply`, the board's token and `Board descriptions to set after the apply`, `Check warnings` and
`Show the plan for approval`. `!= 'true'` rather than `== 'false'` because after CI on a merge the gate is skipped and
its output is empty, and those runs must plan as now. With `plan`, `modes` and `board` skipped, the job's `changes`
output is false, so `apply` and `board` don't run and nothing asks for approval. The "Keep the saved plan" step
already gates on those outputs. The drift job isn't touched.

*Alternatives:* a separate step after the gate that combines target and gate into one `go` output for every later
step. Rejected: it moves the "should this plan" decision into workflow expressions in two places. Exit code 78 or
similar for "neutral". Rejected: GitHub Actions has no neutral step outcome, so it would fail the job.

### D3. Workflow test pins the gating

`test_main_ci_workflow.py` adds to `problems()`: the gate has `id: ci` and appends to `$GITHUB_OUTPUT`, and every plan
step after the gate (except "Keep the saved plan", gated on the plan outputs) carries
`steps.ci.outputs.superseded != 'true'` in its `if:`. It also adds mutations each caught: the gate's id dropped, its
output not redirected, and one later step losing the condition. The existing check that the drift job neither needs
another job nor runs the gate stays, and covers "the drift job still runs".

### D4. Decode inside the fetch's `try` (#203)

`documents[spec] = base64.b64decode(content).decode()` moves into the `try`, so `binascii.Error` and
`UnicodeDecodeError` become `UnreadableError("troupe specs: couldn't read 'cli''s spec.md (<reason>)")`, through the
same `reason()` as a failed fetch. The docstring's promise then holds as written. The existing "label descriptions: not
checked" line follows from `attempt` returning False, unchanged.

*Alternatives:* a separate `try` around the decode with its own wording ("couldn't decode"). Rejected: the issue asks
for "reported as unreadable by name, the way a spec that can't be fetched is", and one message shape is easier to
search for. `reason()` already carries the decode error's own words (`Incorrect padding`, `'utf-8' codec can't
decode ...`).

## Risks / Trade-offs

- [A merge lands, but its CI then fails] → no run after CI on it starts, so nothing plans it. Mitigation: that red
  CI on `main` is the owner's signal already, and the next daily run fails on it through the gate as now. The summary
  says the newer commit's run plans `main` once CI passes on it, not that it will.
- [The compare read adds a GitHub call] → it runs only on a cancel, which is rare, and `github.token` can read
  `contents` on this public repository.
- [Every later step's `if:` grows] → the workflow test fails if any step loses the condition (D3).

## Migration Plan

None. This is a script and workflow change with no state. Rolling back means reverting the pull request.
