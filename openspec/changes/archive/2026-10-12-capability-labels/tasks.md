# Tasks

## 1. The decision

- [x] 1.1 Rewrite the constraint in `openspec/config.yaml` to design D1's wording, and verify with
      `openspec context --json` that the config still parses and carries the new text
- [x] 1.2 `parked` was removed from #22 at proposal time (2026-10-12, the owner's direction; it no longer waits on
      troupe). Verify with `gh issue view 22 --json labels` that it is still off

## 2. Reconcile troupe's labels

- [x] 2.1 Re-read usage: list every `cap:*` label on troupe-run/troupe issues and pull requests, open and closed,
      and verify every one of the 34 declared labels is still in `tofu/labels/troupe.json` (none removed or renamed;
      design D3)
- [x] 2.2 Add `cap:artifact-store`, `cap:runner-protocol` and `cap:scripted-runner` to `tofu/labels/troupe.json`
      (colour `1D76DB`, description `Capability: <name>`, sorted by name; design D2), and verify the file holds 37
      labels and `uv run scripts/check.py` passes (`tofu fmt`, `tofu validate`)
- [x] 2.3 Replace the "copied as they were on 2026-10-11" comment in `tofu/repositories.tf` with one saying
      `troupe.json` is troupe's capability labels, changed by pull request (spec: labels), and verify `tofu fmt`
      passes
- [x] 2.4 Run `uv run scripts/tofu.py plan` and verify it shows exactly three labels created on troupe-run/troupe and
      nothing deleted; quote the plan in the pull request

## 3. The spec check

- [x] 3.1 Write failing tests in `scripts/tests/test_oob.py`, each named for what it checks: a troupe spec folder
      with no label is reported, naming the folder and `tofu/labels/troupe.json`; a label with no spec is not
      reported; every spec labelled reports nothing; the `gh` call that lists the specs is a read (extend
      `test_every_github_call_is_a_read`). Verify they fail with `uv run pytest scripts/tests/test_oob.py`
- [x] 3.2 Add the one-way spec check to `scripts/oob.py` (design D4) and include it in `run` and in `main`'s
      "no differences" line; verify the tests from 3.1 pass and `uv run scripts/check.py` passes (mypy --strict,
      ruff)
- [x] 3.3 Run `uv run scripts/oob.py` against GitHub before 2.4's plan is applied and verify it reports exactly the
      three specs as unlabelled when run on `main`'s `troupe.json`, and nothing for troupe's specs on this branch
- [x] 3.4 Add a row for troupe's specs to `oob/README.md`'s check table (what's declared, why OpenTofu can't check
      it, how it's read), and verify the table renders with `uv run scripts/check.py` still passing

## 4. Document the path

- [x] 4.1 Change the `cap:` line in `org-profile/.github/ISSUE_TEMPLATE/feature.yml` and `decision.yml` to design
      D5's wording, and verify `uv run pytest scripts/tests/test_org_profile.py` passes and the plan shows both files
      updated in troupe-run/.github
- [x] 4.2 Update `README.md`'s `tofu/labels/` layout row to name `troupe.json` as troupe's capability labels, changed
      by pull request, and verify the row reads correctly in the rendered README
- [x] 4.3 Run `openspec validate capability-labels --strict` and verify it passes

## Workflow follow-up

- Open the pull request with `Closes #22`, the plan, `oob.py`'s output, the label-usage list from 2.1, and a note
  that `cap:lifecycle` is kept but appears nowhere in troupe (design D3).
- Archive the change on the branch before merging; the owner merges by rebase and approves the `apply` job.
- After the merge, comment on #22 with the pull request and the archived change, and on #1 that its last step is
  done.
