# Tasks

## 1. The descriptions

- [x] 1.1 Write the offline description test (design D3) in `scripts/tests/`, named for what it checks: a `cap:`
      description over 100 characters fails naming the label and length; one equal to `Capability: <name>` fails
      naming the label; `TBD` passes. Verify it fails on today's `troupe.json` (38 labels named) with
      `uv run pytest` on that file
- [x] 1.2 Replace the 38 descriptions in `tofu/labels/troupe.json` with #26's comment table, re-read from the issue
      at the time, leaving names, colours, order and `cap:infrastructure` unchanged. Verify with a `jq` diff that
      only `description` fields changed (38 of them), that 1.1's test passes, and that `uv run scripts/check.py`
      passes

## 2. The staleness check

- [ ] 2.1 Write failing tests in `scripts/tests/test_oob.py`, each named for what it checks: a labelled spec with
      no recorded Purpose is reported; a changed Purpose is reported, naming the label, `tofu/labels/troupe.json` and
      `oob/troupe-spec-purposes.json`; a Purpose differing only in line breaks or spacing isn't; a spec with no
      `## Purpose` section is reported as changed; a recorded entry with no spec is reported; an unlabelled spec is
      reported once, by the existing check only; the spec reads are reads (extend
      `test_every_github_call_is_a_read`). Verify they fail with `uv run pytest scripts/tests/test_oob.py`
- [ ] 2.2 Add the check to `scripts/oob.py` (design D2) and name it in `main`'s "no differences" line. Verify 2.1's
      tests and all existing `oob` tests pass, and `uv run scripts/check.py` passes (mypy --strict, ruff)
- [ ] 2.3 Create `oob/troupe-spec-purposes.json` with the 14 labelled specs' Purposes read from troupe's `main`
      (design D1). Verify `uv run scripts/oob.py` reports nothing for troupe's labels, and that it reports `cap:runs`
      when its entry is edited locally (then restore it)
- [ ] 2.4 Add a row for the new check to `oob/README.md`'s table, and say there how a new capability's label gets
      its description and recorded Purpose. Verify `uv run scripts/check.py` passes

## 3. Evidence

- [ ] 3.1 Run `uv run scripts/tofu.py plan` and verify it shows only description changes on troupe-run/troupe's
      labels resource (38), nothing created or removed; keep it for the pull request
- [ ] 3.2 Run `openspec validate cap-label-descriptions --strict` and verify it passes

## Workflow follow-up

- Open the pull request with `Closes #26`, the plan from 3.1 and `oob.py`'s output from 2.3.
- Archive the change on the branch before merging; the owner merges by rebase and approves the `apply` job.
- After the apply, verify a few descriptions on GitHub with `gh label list -R troupe-run/troupe --search cap:`, then
  comment on #26 with the pull request and the archived change.
