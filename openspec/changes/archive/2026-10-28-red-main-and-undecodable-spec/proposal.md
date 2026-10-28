# Proposal

## Why

Two small fixes to checks that run whenever `main` is planned. Both report the wrong thing when something goes wrong.

**A superseded run reports a red `main` (#202).** Since #178 (PR #200), a scheduled or manual run waits for green CI
on `main` (`scripts/main_ci.py`). Any CI conclusion other than success fails it. plans-wait-for-ci design D3 assumed a
cancelled `main` run can't be the one checked: only a newer push cancels it, and the walk would find that newer commit
first. But the walk reads `main` as fetched when the run started, so a merge landing *during* the wait goes unseen. In
[run 40510852586](https://github.com/troupe-run/infrastructure/actions/runs/40510852586), the gate was waiting for CI
on `60b5253` when `b496971` landed. CI's concurrency cancelled the run on `60b5253`, and the gate failed with
"concluded **cancelled**; not planning". `main` wasn't red. This fails safe, since the newer merge's own run plans
everything. But it's a false alarm: its summary sends the owner off to re-run jobs for nothing, and any daily run that
overlaps a merge can hit it.

**An undecodable troupe spec isn't reported by name (#203).** In `scripts/oob.py`, `spec_documents` decodes each
`spec.md` (`base64.b64decode(content).decode()`) after its `try`, so a `binascii.Error` or `UnicodeDecodeError` isn't
turned into the `UnreadableError` its docstring promises. Claude's review on #160 found this as a must-fix, and it
merged unfixed. The issue says this crashes the check. In fact, `Report.attempt` catches any exception, so the drift
job still runs its other checks and fails. But the message it gives is `troupe specs: couldn't read it (Incorrect
padding)`, with no spec named. Fetch failures do name it: `couldn't read 'cli''s spec.md (...)`.

## What Changes

- When the CI run a scheduled or manual plan waited for was **cancelled**, the gate asks GitHub whether `main` has
  moved past that commit with a commit CI runs on. If it has, the run is **superseded**. It plans nothing, asks for
  no approval and doesn't fail. Its summary names both the commit checked and the newer head, whose own run plans
  it. If `main` hasn't moved, or has moved only by state commits, the run fails as it does now. Every other
  non-success conclusion, an unknown status, the time limit and a failed read still fail as they do now. A failed
  or unexpected compare read also fails: it's never read as "superseded".
- `tofu.yml`'s plan job skips its later steps (guard wait, set-up, plan, mode and board plans, upload) on a
  superseded run, as it does now when `plan_target.py` says `plan=false`. The drift job is untouched and still runs.
- `scripts/oob.py` decodes each troupe `spec.md` inside the same `try` as its fetch. A spec whose content isn't valid
  base64, or isn't UTF-8, is reported as unreadable by name, exactly as a spec that can't be fetched is.
- README's "Running a plan" says a run superseded by a newer merge plans nothing and fails nothing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci-apply`: a scheduled or manual run whose CI a newer merge cancelled is superseded, not red. The scenario "A
  cancelled CI run isn't green" now says it covers a cancel with `main` unmoved.
- `labels`: a troupe spec that can't be read, because it couldn't be fetched or couldn't be decoded, is reported as
  unreadable, naming the spec.

## Impact

- `scripts/main_ci.py` gains the superseded outcome, a GitHub compare read for it, and a `superseded=` line on stdout
  for `$GITHUB_OUTPUT`. Its tests (`scripts/tests/test_main_ci.py`) and workflow test
  (`scripts/tests/test_main_ci_workflow.py`) change with it.
- `.github/workflows/tofu.yml`: the gate step gets an id and writes to `$GITHUB_OUTPUT`, and each later step's `if:`
  also checks that the run wasn't superseded.
- `scripts/oob.py` (`spec_documents`) and `scripts/tests/test_oob.py`.
- `README.md` ("Running a plan").
- Nothing in `tofu/` changes, so the plan should show no changes. This isn't a guard file, so nothing is delivered to
  troupe or website.
