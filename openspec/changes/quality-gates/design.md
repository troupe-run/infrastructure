# Design: quality-gates

## Context

#321 decided the gates; #322 (coverage) and #324 (complexity, dependency audit) build them in troupe, infrastructure
and website. #320's auto-merge relies on them and applies a stricter limit on the same complexity measure. Each
repository already has one `scripts/check.py`, run before every commit by the guard and in CI. In this repository CI's
`check` job runs it on Linux with Python 3.12, and the guard's legs run only the guard's tests on the other OS and
Python combinations (3.15 on Linux among them). troupe runs the whole check on 12 legs (3 OSes × 3.12–3.15). website
runs it in one `test` job on Linux.

This change is the infrastructure half and the shared module. troupe and website each adopt it in their own
`quality-gates` change once it's delivered.

## Goals / Non-Goals

**Goals:** one implementation of each measure for the three repositories and #320; every threshold in one config
file per repository, read strictly; defaults calibrated on today's code (below) and approved by the owner; a local
commit stays well inside the guard's 600 s limit.

**Non-goals:** raising coverage (the weekly mutation testing in #325 raises issues for weak spots); refactoring
today's complex functions; linting (#323); replacing Dependabot's alerts or security updates, which keep running.

## Decisions

### D1. One delivered module, one config per repository

`scripts/quality_gates.py` is written here and delivered to troupe and website with the guard's files
(`tofu/guard_delivery.tf`). It is standard library only, like the guard, and runs the measuring tools as processes:
coverage.py through pytest-cov, or Vitest's coverage; lizard; pip-audit or npm audit. Each repository's check calls
it with what that repository needs, and `quality-gates.toml` at the root, never delivered, holds that repository's
thresholds and packages.

*Alternatives:* a copy per repository (three implementations of the same measure to keep in step, and #320 would need
a fourth); a published package (nothing else in the org is published that way, and a version bump in three lock files
for each fix). Delivery puts the module on #320's protected list automatically, as the guard's delivery already is.

*Cost:* the troupe and website halves can land only after this one is merged and its delivery applied.

### D2. The config file

```toml
version = 1

[coverage]
floor = 80.0       # a package with no baseline (percent)
tolerance = 0.2    # how far below its baseline a package may measure (percentage points)

[coverage.packages.scripts]
paths = ["scripts"]
baseline = 00.0    # measured when the gate lands (see Calibration)

[complexity]
block_above = 25   # cyclomatic complexity
exclude = ["scripts/tests/**"]
languages = ["python"]   # website: ["javascript", "typescript"]

[audit]
lock_files = ["uv.lock"]
block = ["high", "critical"]
```

Read with `tomllib`. Unknown tables or keys, wrong types, percentages outside 0–100, a negative tolerance, overlapping
package paths and a missing file each fail with the file, the key and what's valid (the malformed-input rule: a typo
must never quietly disable a gate). #320 adds its own stricter key (for example `[complexity] auto_merge_above`) when
it's built. #325's mutation baselines live in the same file, in a `[mutation]` table that this module passes
through raw to #325's script, which validates it (agreed with #325's worker). `quality-gates.toml` should go on
#320's protected list, since lowering a baseline must be the owner's call.

### D3. What coverage measures

Branch coverage as coverage.py defines it with `branch = true`: covered statements plus covered branch destinations,
over all statements and branch destinations. Website's Vitest (V8 provider) reports statements and branches
separately, and the gate combines them the same way, so "90%" means the same thing in all three repositories. Test
files are omitted. Subprocesses are measured (`[run] patch = ["subprocess"]`): most of this repository's scripts, and
troupe's CLI, are tested by running them as processes, so without it their coverage would read far lower than
what the tests exercise.

A "package" is a set of path prefixes in the config: here one (`scripts`), in troupe one per workspace member plus
`scripts`, in website `src` and `scripts`. A measured file under no package fails the gate (spec), so new code can't
sit outside every baseline.

### D4. Baselines and tolerance

Each baseline is the package's measurement on the coverage leg when the gate lands, rounded down to one decimal. The
gate fails when a package measures below `baseline - tolerance`. The tolerance absorbs run-to-run noise (Hypothesis
examples, timing branches, xdist scheduling), calibrated by measuring the same commit twice (below). The baseline
doesn't ratchet by itself: the report prints the headroom, and raising it is a one-line config edit any pull request
may make. Lowering it shows in the diff, for review.

*Alternative:* ratchet automatically from main's last measurement. Rejected: it needs a commit or an artifact store on
every merge, and #321 named a baseline taken when the gate lands.

### D5. Where each gate runs

| Gate | Local check (guard) | CI |
|---|---|---|
| complexity | yes (seconds, diff only) | every leg that runs the check |
| coverage | no | one leg, full check only |
| audit | no | the same leg, when a lock file changed |

`check.py` takes `--base REV` for the diff gates. Coverage and the audit have no flag: the owner chose that coverage
is never measured locally, not even on request (2026-11-18). `check.py` runs them only when the CI leg sets
`QUALITY_GATES_LEG=true` and GitHub Actions is running it (`GITHUB_ACTIONS=true`); the variable set anywhere else
fails the check, naming it, so it can't become a local switch. A local check runs only the complexity gate, so a
commit's check gets no slower to speak of and needs no network. A scoped run's coverage would be partial, so on the
leg a scoped check says "coverage not measured: the tests were scoped" and passes that gate; every change to a Python
source runs the full check (run-checks-by-path design D3), so code changes are always measured.

Here, CI's `check` job moves from Python 3.12 to 3.15 and becomes the coverage leg; the guard's legs swap their
`exclude` from Linux 3.12 to Linux 3.15 (the check job runs the guard's tests there), so 3.12 is still tested on
Linux and the leg count stays 11. The job's limit goes from 10 to 15 minutes for coverage and the audit; a local
run of the leg took 130 s for the tests under coverage and 24 s for the audit. In troupe, the Linux 3.15 leg gets `gates: true` in the
matrix. In website, the one `test` job is the leg.

### D6. The complexity rule

For each file in the diff from the base to the working tree (staged and unstaged included, so a commit's check judges
what it commits), in a language the config names and not excluded: lizard measures the file at the base and now. A
function is *changed* when its line range now overlaps a line the diff adds or modifies. A changed function fails when
its cyclomatic complexity is above `block_above` and either it didn't exist at the base (matched by file and lizard's
long name) or its complexity rose. An existing function above the limit can be edited, but not made worse: the old
code is grandfathered, as #321 grandfathered coverage.

Excluded by default: tests (`**/tests/**`), delivered files in the receiving repositories (`scripts/guard.py`,
`scripts/guard_pytest.py`, `scripts/quality_gates.py`, measured here at their source), and generated code (troupe's
`config/models.py`). A renamed function counts as new, which errs towards measuring.

lizard is a dev dependency in troupe and here, and an inline script dependency of website's `check.py` (which is run
by `uv run` with no project environment).

### D7. The audit

Runs only when a configured lock file differs between the base and the work.

- **uv.lock:** `uv export --frozen --all-groups --all-packages --no-emit-workspace --no-hashes` to a temporary
  requirements file, then `pip-audit -r <file> --no-deps --disable-pip -s osv -f json`. pip-audit reports each
  advisory's fixed versions but not its severity, so the module reads the severity from OSV
  (`https://api.osv.dev/v1/vulns/<id>`, the GitHub advisory alias's `database_specific.severity`: LOW, MODERATE, HIGH,
  CRITICAL). An advisory with no GitHub alias or no severity counts as blocking.
- **package-lock.json:** `npm audit --package-lock-only --json`, which gives each vulnerability's severity and
  `fixAvailable`.

Blocking: severity in `[audit] block` and a fixed version exists. A network or tool failure fails the leg. `uv audit`
(uv 0.13) does the same from `uv.lock` directly but is marked experimental and also omits severity; it can replace
the export and pip-audit once it's stable.

### D8. The weekly report

`.github/workflows/dependency-report.yml` in each repository, Mondays, and by hand: audits every lock file on `main`
(`quality_gates.py report`), and keeps one issue titled "Dependency advisories", labelled `dependencies`: opened when
there are advisories, its body replaced while there are, closed with a comment when there are none. It finds its
issue by title and label among open issues, so it never opens a second. A separate `board` job adds a new issue to the
board with the troupe-run-board App's token, as website's weekly link check does (`tofu/board.tf`). troupe has no
`board` environment yet; this change adds it there (or #325, if it lands first, does).

The report job's own failure (a tool or the network) fails the run. The schedule watch (spec: schedule-watch) is told
about each report only after its first scheduled run, in a follow-up: it reads a workflow that has never run on its
schedule as stopped (#328's review).

### D9. Sequencing

1. This change: the module, its tests, this repository's adoption, the delivery and the report. Merged; the owner
   approves the plan that delivers `scripts/quality_gates.py` to troupe and website.
2. troupe's and website's `quality-gates` changes: their config, `check.py` wiring, CI leg, report workflow and
   baselines measured on their own CI legs.

Worker 2's #323 (linting) and #325 (mutation testing) change the same `check.py` files; whichever merges second
rebases.

## Owner's decisions

Owner, 2026-11-18, through the orchestrator, on the six items sent with the calibration below:

1. **D1 approved:** one stdlib-only `scripts/quality_gates.py`, delivered to troupe and website with the guard's files;
   a per-repository `quality-gates.toml`, never delivered.
2. **Complexity:** block new or worsened functions over CCN 25, tests, delivered and generated code excluded, on the
   corrected calibration (infrastructure 9 of 119). #320 uses about 15.
3. **Coverage:** an 80% floor for a new package; no package below its baseline, with a 0.5-point tolerance until the
   same commit has been measured twice on CI; baselines are the CI leg's measurement rounded down to 0.1, raised by
   hand. troupe's runner subprocess gap and website's `.astro` gap are handled in their own changes.
4. **Where:** complexity in the local commit check; coverage and the audit on one CI leg only, and no local coverage
   at all, not even an opt-in flag (D5 as amended).
5. **Audit as proposed:** high and critical advisories with a fix block a lock-file change; unknown severity blocks; a
   network failure fails; severity from OSV.
6. **Weekly report as proposed**, one "Dependency advisories" issue per repository, and troupe gets its `board`
   environment here.

## Calibration (the defaults the owner approved)

Measured 2026-11-17 on each repository's `origin/main`.

### Complexity

lizard 1.26.1 over source files (tests excluded unless noted).

| Repository | Functions | CCN > 15 | CCN > 20 | CCN > 25 | CCN > 30 | Highest |
|---|---|---|---|---|---|---|
| infrastructure (with tests) | 2411 | 43 | 22 | 15 | 10 | 51 (a test), 50 (`guard.py: gh_decision`) |
| troupe | 2106 | 58 | 26 | 10 | 7 | 45 |
| website | 300 | 2 | 0 | 0 | 0 | 18 |

Replaying the rule (D6) over each repository's last ~120 merged pull requests: how many would it have blocked?

| Limit | infrastructure (src) | infrastructure (with tests) | troupe (src) | website |
|---|---|---|---|---|
| 15 | 14 of 119 | 33 | 34 | 1 of 47 |
| 20 | 9 | 24 | 24 | 0 |
| **25** | **9** | 21 | **11** | **0** |
| 30 | 8 | 18 | 11 | 0 |
| 40 | 3 | — | 4 | 0 |

In infrastructure, `scripts/guard.py` is the source, so it's measured; in troupe and website it's a delivered copy
and isn't. (A first pass skipped it here too and undercounted infrastructure: 5 at 25, corrected to 9.) The module's
own rule, replayed over infrastructure's last 20 merged pull requests at a limit of 10, flagged exactly the functions
the calibration script did (four, all in #302).

**Proposed: `block_above = 25`, tests excluded.** It blocks about 8% of infrastructure's and 9% of troupe's pull
requests, each one a function that is genuinely hard to follow: `dependabot_issues.plan` at 38, `projection.plan` at
36, the scripted runner's `_step` growing 31 → 34 → 37 over three pull requests, and the guard's `gh_decision` growing
47 → 48 → 49 → 50 over three. That last one shows the rule's cost: once a function is over the limit, each pull
request that adds a branch to it must split it first. Including tests would block 18% of infrastructure's, nearly all
its workflow tests' `problems` checklists (CCN 36–63), which are long but flat lists of conditions; #325's mutation
testing judges tests instead. #320's stricter limit would sit lower, around 15.

### Dependency audit

Today: no advisory in infrastructure's or troupe's `uv.lock` (pip-audit 2.10.1, OSV). website's `package-lock.json`
has 4 moderate (one, `linkinator`, with a fix). **Proposed: block high and critical with a fix; unknown severity
blocks.** Nothing blocks today; website's 4 moderates go in its first weekly report.

### Coverage

Measured on macOS with Python 3.15 (coverage 7.17.3, sys.monitoring, subprocesses measured, tests and delivered
files omitted), and Vitest 5.0.3 with the V8 provider. The baselines themselves are re-measured on each repository's
CI leg when its gate lands; these numbers set the floor and show the spread.

| Repository | Package | Branch coverage |
|---|---|---|
| infrastructure | `scripts` | 91.5% |
| troupe | `troupe` | 92.2% |
| troupe | `troupe-plugin-sdk` | 94.7% |
| troupe | `troupe-store-text` | 93.0% |
| troupe | `troupe-vcs-git` | 93.4% |
| troupe | `troupe-vcs-files`, `-identity-local`, `-artifacts-local`, `-stage-local` | 91.8–100% (under 100 lines each) |
| troupe | `runner-openai` | 91.5% |
| troupe | `runner-mistralrs` | 82.8% |
| troupe | `runner-ollama` | 81.1% |
| troupe | `runner-anthropic` | 76.4% |
| troupe | `runner-claude-code` | 60.5% |
| troupe | `runner-scripted` | 50.7% |
| troupe | `scripts` (delivered files omitted) | 88.3% |
| website | `scripts` (`.mjs`) | 80.8% |
| website | `src` (`.ts` only) | 79.6% |

Findings that shape the troupe and website changes, not this one:

- **troupe's runners read low because their processes aren't measured.** troupe starts a runner with an allow-listed
  environment (`processes.build_environment`), which drops coverage's subprocess setting, so the runner code those
  tests drive counts as unrun. troupe's change either lets the test suite pass coverage's variable through (tests
  only), or records those baselines as they are. Either way the gate works: it stops a drop from today.
- **website's components and pages aren't unit-tested.** `.astro` and Markdown are exercised by the Playwright tests,
  which Vitest can't measure (`src/components` reads 15.7%, the rest 0%). website's packages measure `.ts` and `.mjs`
  only; the e2e tests stay the guard for the rest.
- **troupe-run** is a metapackage with no code: a package with nothing to measure passes and says so.

**Proposed:**
- **Floor for a new package: 80%.** Below every core package and most plugins today, above the three runners whose
  processes go unmeasured; a new package written with its tests meets it.
- **Tolerance: 0.5 points**, until the same commit has been measured twice on a CI leg; then the smallest value that
  covers the difference, rounded up to 0.1, recorded here.
- **Baselines: each package's measurement on its CI leg when the gate lands, rounded down to 0.1.**

### Time

Under coverage, infrastructure's suite took 735 s with 2 workers at load 40–88, and troupe's 823 s with 3 workers at
load 30–60. Neither number is comparable with CI's (4 workers, an idle runner), and the cost of coverage on a CI leg
is measured on this change's pull request before it's ready: infrastructure's `check` job has a 10-minute limit,
which may need raising.
