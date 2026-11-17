# Tasks

Load rule for every full or coverage run below: check `uptime` first, start only when the 1-minute load is under 40,
and run one at a time.

## 0. Owner approval

- [x] 0.1 Send design's Calibration (proposed defaults) and D1 (a delivered module) to the owner through the
      orchestrator, and record the answer in design.md. Verify: the answer is quoted in design.md with its date

Tasks 1–4 were built while the owner's answer on design's Calibration was pending (orchestrator, 2026-11-17: build the
measures, thresholds read from config, nothing that depends on D1's delivery or the board). The tests were written
alongside the module rather than strictly first. Instead of a fail-first run, each rule was broken in turn and a test
was required to catch it: 10 sabotages, all caught after the duplicate-advisory test was made to count OSV lookups.
One check is redundant by construction and says so in a comment: a function the diff doesn't touch can't be more
complex than at the base.

## 1. The config (design D2)

- [x] 1.1 Tests first, in `scripts/tests/test_quality_gates.py`: a valid config parses; a missing file, an unknown
      table, an unknown key, a wrong type, a percentage outside 0–100, a negative tolerance, an unknown severity and two
      packages with overlapping paths each fail naming the key and what's valid. Verify they fail before 1.2
- [x] 1.2 Write the config reader in `scripts/quality_gates.py` (stdlib only, delivered-file note at the top). Verify
      1.1 passes and `mypy --strict` and `ruff` are clean

## 2. Complexity (design D6)

- [x] 2.1 Tests first: from a scratch git repository, a new function above the limit fails; an old one made worse
      fails, naming before and after; an old one edited without change passes; an excluded path passes; staged and
      unstaged edits are both judged; a missing base fails saying `git fetch origin main`; TypeScript and `.mjs` files
      are measured when the config names those languages. Verify they fail before 2.2
- [x] 2.2 Implement the diff, the lizard runs (base and work) and the rule. Verify 2.1 passes, and replaying it over
      the last 20 merged pull requests here matches the calibration script's answer for each. Done: at a limit of
      10 both flag the same four functions (#302); this found the calibration's guard.py skip (design, corrected)

## 3. Coverage (design D3, D4)

- [x] 3.1 Tests first: per-package totals from a coverage.py JSON report and from a Vitest `coverage-summary.json`
      fixture copied from real runs; below baseline minus tolerance fails; within tolerance passes; no baseline below
      the floor fails; a file under no package fails; the report lists every package with headroom. Verify they fail
      before 3.2
- [x] 3.2 Implement the Python and Vitest readers and the comparison. Verify 3.1 passes

## 4. Audit (design D7)

- [x] 4.1 Tests first, with pip-audit, OSV and npm audit output captured from real runs as fixtures (the vulnerable
      `requests==2.19.0` probe, and website's current lock file): a fixable high fails; a fixable moderate passes; a
      high with no fix passes; a missing severity blocks; an unchanged lock file skips; a tool or network failure
      fails. Verify they fail before 4.2
- [x] 4.2 Implement the uv.lock and package-lock.json audits and the OSV severity lookup. Verify 4.1 passes, and a
      real run against this repository's `uv.lock` reports no advisories. Done: 0 here; a probe project pinning
      requests 2.19.0 gives 19 advisories, 7 blocking (high, with a fix), severities read live from OSV

## 5. This repository's adoption (design D5)

- [x] 5.1 Add coverage, pytest-cov, lizard and pip-audit to the dev group (`uv add --dev`, then check the lock diff by
      package: only these and their dependencies). Verify `uv sync --locked` passes
- [x] 5.2 Wire `scripts/check.py`: the complexity gate always (`--base` optional); coverage and audit only when
      `QUALITY_GATES_LEG=true` under `GITHUB_ACTIONS=true` (the variable anywhere else fails, naming it; no flag, owner
      2026-11-18); a scoped check on the leg says coverage wasn't measured. Tests in `scripts/tests/test_check.py`.
      Verify they pass, and a local full check stays within a few seconds of today's. Done: the complexity gate
      takes 0.5 s; a simulated leg run (GITHUB_ACTIONS and the variable set) ran every gate, tests 130 s under
      coverage, audit 24 s
- [ ] 5.3 Write `quality-gates.toml` with the approved defaults and the `scripts` baseline. Verify the full check
      with `--coverage --audit --base origin/main` passes here
- [x] 5.4 CI: `check` on Python 3.15 with the base fetched and the flags passed; the guard's legs gain Linux 3.12.
      Update `scripts/tests/` workflow tests to match. Verify they pass

## 6. Weekly report (design D8)

- [ ] 6.1 Tests first for `quality_gates.py report`: opens one issue when there are advisories, updates the open one,
      closes it when clear, never opens a second (a fake `gh`). Verify they fail, then implement, then pass
- [ ] 6.2 Add `.github/workflows/dependency-report.yml` with its board job, and troupe's `board` environment and
      variable in `tofu/board.tf`. Verify workflow tests pass and the plan shows the troupe environment

## 7. Delivery and docs

- [ ] 7.1 Add `scripts/quality_gates.py` to `tofu/guard_delivery.tf`. Verify the plan delivers it to troupe and
      website and nothing else changes
- [ ] 7.2 Document the gates in `docs/development-workflow.md` (what each blocks, where its thresholds live, how to
      raise a baseline). Verify the docs tests pass

## Workflow follow-up

- troupe's and website's `quality-gates` changes, after the delivery is applied (design D9).
- The after-merge comment on #322 and #324, and the board cards.
