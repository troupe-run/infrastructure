# Tasks

Load rule: check `uptime` before a full check or a mutation trial; start only under a 1-minute load of 40, one at a
time.

## 1. Coverage is optional (design D4)

- [x] 1.1 Tests first: `parse_config` accepts a file with no `[coverage]` (`Config.coverage` is `None`), still refuses
      a malformed `[coverage]`; the `coverage` subcommand with none prints the not-measured line and exits 0. Verify they
      fail on the base code, then change `scripts/quality_gates.py`
- [x] 1.2 `check.py`: pytest's `--cov` options and the coverage step only when the config has `[coverage]`; otherwise
      the leg says coverage isn't measured here and still runs the audit. Tests first
- [x] 1.3 Remove `[coverage]` from infrastructure's `quality-gates.toml`; a test holds it to the list (infrastructure
      isn't listed, so it has no `[coverage]`). Verify the test fails while the table is there

## 2. One list (design D1, D2)

- [x] 2.1 `scripts/mutation.json`: `repositories` names troupe only, with D5's deselections. The run step's and the
      report's tests keep their three-repository cases on a fixture copy of the old settings
      (`scripts/tests/fixtures/mutation/settings-three.json`), so the code for every tool stays tested
- [x] 2.2 `mutation.yml`: a `targets` job reads the list (and a dispatch's `repository`, `all` or one listed name,
      refusing any other naming what's listed); `mutate`'s matrix comes from it. Tests: the matrix isn't fixed, a
      dispatch naming an unlisted repository fails `targets`

- [x] 2.3 `mutation-pr.yml`'s mutate job checks out the merge (`github.sha`) and diffs it against its first parent,
      not the pull request's head: a branch made before a delivery has no `scripts/mutation.json` (troupe#444's run,
      reported by #322's worker). Tests: the workflow's checkout and range; a scratch repository where main gains a
      delivered file after the branch point

- [x] 2.4 `mutation-pr.yml` runs `mutate` only where the list names the repository (a `listed` job reading
      `scripts/mutation.json` at the merge), so infrastructure's own pull requests mutate nothing rather than fail.
      Tests: the gate for a listed and an unlisted repository (from the review of #334)

## 3. Delivery follows the list (design D3)

- [x] 3.1 `tofu/guard_delivery.tf`: the seven report files go only to guard targets the list names; each target's
      `guard-delivery.json` lists what it receives. Tests: troupe receives them, website doesn't, quality_gates.py
      still goes to both, evaluated by OpenTofu from the real locals block (`test_delivery_targets.py`, after the
      review's finding that a string match on the .tf checked nothing)
- [x] 3.2 `scripts/dependabot_config.py`: each repository's delivered workflows, not the union; regenerate
      `tofu/dependabot/`. Verify website's no longer names `mutation-pr.yml`

## 4. troupe's mutation runs (design D5)

- [x] 4.1 Tests first in `test_mutation_run.py`: a package unit links the checkout's missing top-level entries into the
      package's parent, and `packages/packages`, and removes them after, failed runs too; the repository's own
      `addopts` reach mutmut without `--strict-markers` and `-p guard_pytest`. Then change `scripts/mutation_run.py`
- [x] 4.2 Verify on a scratch clone of troupe, under the load rule: the `troupe` package's stats pass completes with
      the three deselections, and a small mutation of one function reports killed and surviving mutants. Done
      2026-11-18 on troupe 868742f: the stats pass completed, and `--only troupe.core.config.aggregate.*` reported 10
      killed, 0 surviving, finished (that module has no survivor to show); the links were gone afterwards. 26 minutes
      on a shared machine, most of it the stats pass

## 5. Docs and verification

- [x] 5.1 `docs/development-workflow.md` ("Mutation testing", and the coverage gate's section) and README: where the
      list lives, that it covers coverage and mutation testing, and how to add a repository
- [ ] 5.2 The full check passes; the pull request's plan shows website's report files deleted, troupe's updated, and
      nothing else

## Workflow follow-up

- After the merge and apply: dispatch `mutation.yml` as a dry run for troupe alone; report each module's score, what
  would be filed, and the runtime against the 4-hour budget.
- Comment on #332 with the PR and the archived change, and check its card says Done.
