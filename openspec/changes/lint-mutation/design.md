# Design

## Context

See proposal.md for why. What shapes the approach:

- **The check.** `scripts/check.py` runs ruff, `ruff format --check`, `mypy --strict`, the tests, `tofu fmt -check
  -recursive tofu`, `tofu init` and `tofu validate`, the same locally and in CI's `check` job (one Linux leg, Python
  3.12). A scoped check runs every non-test gate (spec: ci-apply). `tofu` is found on the PATH, the Python tools in
  the uv environment.
- **The OpenTofu configuration uses OpenTofu-only syntax**: the `encryption` block in `tofu/versions.tf`, and
  `removed` blocks. `tflint` is a Terraform linter (MPL-2.0, v0.66.0 as of 2026-11-08). It isn't in Homebrew on this
  machine, so how a developer installs it is part of the change.
- **How the org already files issues from a schedule.** `schedules.yml` (GITHUB_TOKEN, infrastructure's own issues)
  and `dependabot-issues.yml` (the `troupe-run-dependabot` App, issues in all three repositories) each hand the issue
  URLs to a `board` job, which adds them to the troupe roadmap board with the `troupe-run-board` App from the main-only
  `board` environment (spec: board-credentials). Both scripts only read and print outside GitHub Actions.
- **Code sizes** (2026-11-17): troupe's packages hold about 23k lines of Python (`packages/troupe/src` alone 17k),
  infrastructure's `scripts/` 9.8k in 21 modules, website's `src/**/*.ts` 8 files plus `scripts/*.mjs` 24.
- **mutmut 3.8.1** (Python ≥ 3.10, needs `fork`, so Linux) mutates functions that tests call, remembers results in
  `mutants/`, and can resume. **Stryker 10.1.1** with its vitest runner covers website's unit tests; it doesn't mutate
  `.astro` files.

## Goals / Non-Goals

**Goals:**
- `tflint` blocks a pull request and a commit like any other gate, with nothing in `tofu/` failing it when it lands.
- A weekly report that turns weak tests into board issues, one per module, kept up to date, without ever touching a
  merge.
- Every number the run judges by in one file, with conservative defaults the owner approves (D6).

**Non-Goals:**
- No change to troupe's or website's files for #325: the run reads their code at `main`.
- No required check: P reports and never blocks (D9).
- website's ESLint, Prettier and `tsc --noEmit` (a website change), coverage (#322), complexity and dependency audit
  (#324).

## Decisions

### D1. `tflint` is a gate after `tofu validate`, found on the PATH like `tofu`

`check.py` gains `("tflint", [tflint, "--chdir=tofu", "--recursive", "--config", <root>/.tflint.hcl])` after `tofu
validate`. It's found with `tool("tflint", path=None)`, whose fix names the install route (D2). CI's `check` job
installs it with `terraform-linters/setup-tflint`, at the version `.tflint.hcl`'s comment and the workflow both name,
and a test holds the two together. It's a non-test gate, so it runs in scoped checks too, as `tofu fmt` does.

`.tflint.hcl` enables the bundled `terraform` ruleset's `recommended` preset. No provider plugin: the
`integrations/github` and Cloudflare providers have no TFLint ruleset worth the download, and a plugin is fetched code
the check would run. A rule that can't read OpenTofu-only syntax, or a finding the owner accepts, is disabled in
`.tflint.hcl` with a comment saying why: that file is the recorded baseline #323 allows. Anything else `tflint` finds
is fixed in `tofu/` before the gate lands.

*Alternatives:* run `tflint` only in CI (rejected: #321 says blocking locally too, and the check is the same script in
both places, ci-apply design D8); `tofu fmt` alone (rejected by #321).

### D2. CI installs `tflint`; a local check without it says so and goes on (owner, 2026-11-17)

The owner chose CI first: no local install for now, and the draft pull request's CI leg is `tflint`'s first trial on
this configuration. So the gate is blocking where `tflint` must be present, and absent only where the owner said it
may be:

- **In GitHub Actions** (`GITHUB_ACTIONS=true`), a missing `tflint` fails the check, naming it. CI installs it, so a
  missing one there is a broken workflow, never a skip.
- **Locally**, a missing `tflint` prints `check: tflint isn't installed, so the tflint gate is skipped here; CI runs
  it` with the install command, and the other gates run. Absent is the only state that skips: a `tflint` that is
  installed and fails, or can't read `.tflint.hcl`, fails the check like any gate.

When the owner later installs it locally, nothing changes in the check: it's found and runs. The install command the
notice names is `go install github.com/terraform-linters/tflint@<version>`, the version from `.tflint.hcl`.

*Alternative:* fail locally when it's missing (rejected for now: every commit on every machine without `tflint` would
fail, against the owner's choice).

### D3. One workflow in infrastructure runs all three repositories

`.github/workflows/mutation.yml`, on `schedule` (weekly, Sunday 03:23 UTC, off the hour) and `workflow_dispatch`
(inputs: `repository` to run one, and `dry-run`, which reports without filing). Jobs:

```
  mutate (matrix: troupe, infrastructure, website)   no secret, contents: read
     checkout troupe-run/<repo>@main → run the tool within the budget → mutation_report.py → artifact report-<repo>.json
  issues   needs mutate, env mutation-issues (main only)   the credential of D4
     checkout infrastructure@main only → mutation_issues.py over the reports → output issue-urls
  board    needs issues, env board (main only)   troupe-run-board App, as schedules.yml
```

- **One place, not three.** Settings, the issue script and the workflow live together, and troupe and website need no
  change. A workflow in each repository would copy the script three times and need a board key in troupe, which has
  no `board` environment (spec: board-credentials). The constraint that a product repository's files change only by
  pull request isn't touched: the run only reads them.
- **The jobs that run other code hold nothing.** `mutate` runs each repository's tests on `main`'s code with a
  read-only `GITHUB_TOKEN` and no environment. The `issues` job checks out only infrastructure and reads the reports
  as data: `mutation_issues.py` validates each against a closed schema, and a malformed report is an error naming the
  repository, never a skipped one.
- **Python 3.15 on `ubuntu-latest`**, through `astral-sh/setup-uv`, for both Python legs; website's leg uses Node
  from website's `.nvmrc`.
- **mutmut per package.** troupe's tests live beside each package, so the troupe leg runs mutmut once per package
  under `packages/`, each with its own `source_paths` and tests. The leg writes the run's `setup.cfg` `[mutmut]`
  section into its throwaway checkout from `scripts/mutation.json`; nothing is committed to troupe.
- **Stryker from the settings' pinned versions.** The website leg runs `npm ci`, then
  `npx -p @stryker-mutator/core@<v> -p @stryker-mutator/vitest-runner@<v> stryker run` with a config written from
  the settings: mutate `src/**/*.ts` and `scripts/**/*.mjs`, run `tests/unit`, JSON reporter.
- **What a trial of mutmut 3.8.1 on Python 3.15 taught** (2026-11-17, on this repository's `scripts/`), and how
  `scripts/mutation_run.py` answers each:
  - mutmut names a module by its path from where it runs, stripping only `src/`, and infrastructure's tests import
    `mutation_settings`, not `scripts.mutation_settings`. So mutmut runs where `src` is the unit's source: a troupe
    package's own directory, and infrastructure's checkout root with `src` linked to `scripts`. A survivor's path is
    mapped back to the unit's real source.
  - The tests run in mutmut's copy (`mutants/`) and find the repository's files from their own place, so every other
    top-level entry is copied in beside the source (a hand-kept list missed `.tflint.hcl`). The tests themselves are
    run, never mutated.
  - The repository's pytest `addopts` load the guard's tag-check plugin, which looks for files from the repository's
    root; a mutation run clears them (`-o addopts=-ra`).
  - Tests that run a script in a subprocess (the guard's) crashed mutmut's stats pass, and a git hook running a
    mutated copy under another Python couldn't import mutmut. A pytest plugin loaded only in mutation runs
    (`scripts/mutation_children.py`) gives each child a no-mutant value during stats and the mutant's name during a
    mutant's run, with mutmut on `PYTHONPATH`. **Limit:** mutmut's stats don't see what a child process runs, so a
    function reached only through a subprocess counts as not covered by any test.
  - A mutmut run that fails is an error naming the unit, never a report of empty modules.
  - `mutation_settings.py` alone, with only its own tests selected: 381 mutants in 21 s (323 killed, 58 survived,
    84.8%); every survivor's computed line matched the source.
- **Results to one report.** `scripts/mutation_report.py` turns mutmut's per-mutant results or Stryker's
  `mutation.json` into one shape: per module, the counts, the score, and each surviving mutant's name, line and diff
  (from `mutmut show` or Stryker's replacement), plus whether the run finished within the budget.
- **It stays in the schedule watch.** `scripts/watched-schedules.json` gains `mutation.yml` with `max_age_days: 8`,
  so a paused schedule is reported like website's weekly link check.

### D4. The issues are filed by a new, narrow App (owner, 2026-11-17: option A)

`GITHUB_TOKEN` can only write infrastructure's issues, and the issues belong in the module's own repository. Options:

| | Option | For | Against |
|---|---|---|---|
| **A** | **A new App `troupe-run-test-quality`**: Issues read and write, Metadata read, on troupe, website and infrastructure; key in a new main-only `mutation-issues` environment in infrastructure, no reviewers (spec: mutation-issue-credentials) | Narrow; mirrors `troupe-run-dependabot` exactly; a leaked key can only write issues | The owner creates the App and sets its key by hand (oob/README) |
| B | The `troupe-run-dependabot` App, from a second environment | No new App | Its spec says it serves Dependabot's pull requests; reusing it blurs what the drift check and its spec guard |
| C | The `troupe-run-infrastructure` App | Already installed with issues write | Its key also holds administration, contents and workflows write; today it's only in `plan-main` and the reviewed `apply`. An unattended weekly job beside it widens what a mistake can reach |
| D | `GITHUB_TOKEN`, all issues in infrastructure | No credential at all | The issue isn't where the code is, so troupe's work tracking misses it |

**Chosen: A** (owner, 2026-11-17). It's the least a leaked key can do, and it follows the pattern the org already uses. Issues
opened by an App start no workflow trouble: no repository runs anything on `issues` events from it.

### D5. One issue per module, found by a marker, updated in place

- **Identity of a module:** `<repository>:<module>`, where a module is a Python dotted module (`troupe.store.events`)
  or a website source path (`src/lib/site-path.ts`). The issue body starts with
  `<!-- mutation-testing: <repository>:<module> -->`, and the script finds its issue by listing the repository's
  issues labelled `test-quality` and reading that line, open ones only. Only issues the
  credential's App opened are read as its own (the login is checked), so a person's issue quoting the marker isn't
  edited.
- **Under the threshold or its baseline (D7), no open issue:** open one, type Task, label `test-quality`, title
  `Mutation score <score>% in <module> (under <threshold>% | below its <baseline>% baseline)`. The URL goes to the
  `board` job. No reopening (D7).
- **Under the threshold, open issue:** rewrite its body with this run's numbers and survivors, and add a comment only
  when the score or the number of survivors changed, so a quiet week makes no noise.
- **At or over the threshold, open issue:** comment with the new score and close it as completed.
- **Not judged:** a module with fewer mutants than the floor (D6), or one the run didn't finish within its budget; an
  open issue for it is left alone.
- **The body** names the score, the counts (killed, survived, no tests, timed out), the threshold, the run's link, the
  settings' link, and the surviving mutants: name, line and diff, the first 30, then "and N more" with the command
  that lists them all (`mutmut results`, or Stryker's HTML report in the run's artifact).
- **New issues per run are capped** (D6). The rest are named in the run's summary and raised in a later week, so a
  first run can't flood the board.
- **Errors:** a repository whose report is missing or malformed, or an API write that fails, fails the run after the
  others are handled, like `dependabot_issues.py`. Outside GitHub Actions, or with `dry-run`, it only prints what it
  would do.

### D6. Thresholds and budget (owner, 2026-11-17; the ratchet in D7)

All in `scripts/mutation.json`, read by both scripts; the workflow's job timeout is derived from the budget by a test.

| Setting | Proposed | Why |
|---|---|---|
| `threshold` (score for a module with no baseline yet) | **60%** | Conservative: far enough below typical well-tested code (70-85%) that an issue means real gaps, not noise; raise it once the first runs show where the code sits |
| Score | caught ÷ (caught + survived + no tests); caught = killed, timed out or crashed; skipped and suspicious mutants don't count | Stryker's definition; untested code counts against a module |
| `min_mutants` per module | **10** | A module with a handful of mutants swings 20 points on one survivor |
| `budget_minutes` per repository | **240** | Weekly, well inside GitHub's 6-hour job limit; job timeout = budget + 30 for setup and the report |
| `max_new_issues` per repository per run | **5** | 15 a week at most across the org; existing issues are always updated |
| `tolerance` | **0** points | The ratchet (D7): any drop below a module's baseline counts |
| `pr_budget_minutes` | **45** | P's bound on one pull request's runner time (D9) |
| Schedule | weekly, Sunday 03:23 UTC | #321: weekly; off the hour |
| Tools | mutmut 3.8.1; Stryker 10.1.1 with its vitest runner | Current releases; pinned, moved by pull request |

**Calibration:** the first run after merge is dispatched with `dry-run`. Its summary lists every module's score, so
the owner sees how many issues 60% would open before any is filed, and the threshold can move in the same pull
request that turns filing on. This repository's own scripts are trialled small locally (one module) before that.

### D7. A ratchet: each module's baseline only moves up (owner, 2026-11-17)

The owner made the score a ratchet and dropped the 90-day reopen rule.

- **When a module is judged** (≥ `min_mutants` mutants, finished within the budget), its baseline becomes
  max(baseline, score). A module with no baseline gets its first judged score.
- **Its issue is open** while score < 60% (the starting `threshold`, for code that has never reached it) or
  score < baseline − `tolerance` (default 0 points). A module first measured at 40% has an issue for being under 60%;
  if it falls to 35%, the issue says it fell below its 40% baseline. When both clear, the issue gets a comment and
  closes. If it falls again later, a new issue is raised: no reopen window.
- **Baselines live in each repository's committed `quality-gates.toml`** (owner), the file #322 keeps its coverage
  baselines in, under a `[mutation]` table this change owns (agreed with #322's worker):

  ```toml
  [mutation.baselines."troupe.store.events"]
  score = 71.2        # percent, one decimal
  mutants = 140       # how many it was judged on
  judged_at = "<sha>" # the commit of that repository's main it was judged at
  ```

  #322's loader reads the file strictly for its own tables and hands `[mutation]` over untouched; this change's code
  validates it as a closed schema, so an unknown key or a malformed score fails, naming the file and key, and is never
  read as "no baseline". The weekly run reads each repository's file at the `main` it tests.
- **Raising them is a pull request** (owner): never a direct write, and the test-quality App doesn't get contents write.
  Lowering one is an ordinary pull request too. The weekly run names the raises; a person or agent makes the pull
  request (D10).
- **The dry run** reports the baselines it would raise and every drop, and writes nothing.

### D8. W: the weekly run names who added each new survivor (owner, 2026-11-17)

Each weekly report uploads as a run artifact (kept 90 days). The next run downloads the previous successful run's
reports to learn the commit each repository was judged at. The `mutate` job checks out with full history, and for each
surviving mutant runs `git blame --porcelain -L <line>,<line>` on its file at the tested commit. A survivor whose line
was last changed by a commit that isn't an ancestor of the previously judged commit is **new**. The report carries the
commit, and the `issues` job asks GitHub which merged pull request contains it (`commits/<sha>/pulls`). Then:

- the module's issue lists new survivors first, under "New since the last run", each with its commit and pull request;
- naming the pull request in the issue ("added in #412") makes GitHub show the issue on that pull request's timeline.

**Pending the owner (2026-11-18):** whether the run also comments on the pull request (option A). A GitHub App token
reaches only what its permissions name, so commenting needs "Pull requests: read and write" on the test-quality App,
which could then also edit or close pull requests (never push or merge). Built provisionally as option B, the
cross-reference only, which keeps the App issues-only (orchestrator, 2026-11-18). Choosing A later adds the App
permission, its token input and the comment; nothing else changes. Which pull request a commit came from is read with
the run's own read-only token (`READ_TOKEN`), since the App's issues-only token can't read pull requests.

With no previous run (the first, or one older than 90 days), nothing is called new. Cost: one blame per survivor,
seconds.

### D9. P: each ready pull request's changed code is mutated, as a report (owner, 2026-11-17)

On every pull request that's ready for review, in troupe, website and infrastructure, a workflow mutates only what the
pull request changed and reports surviving mutants on changed lines. **It never blocks**: it isn't a required check,
and it concludes success when it finds survivors; only its own failure to run turns it red. It records its runtime so
the owner can decide later whether it should block.

- **Delivered like the guard's files.** `.github/workflows/mutation-pr.yml`, `scripts/mutation_pr.py` and
  `scripts/mutation.json` (the settings, read for the repository's own targets) join `guard_files` in
  `tofu/guard_delivery.tf`, so troupe and website run the same files, delivered after an approved plan.
- **Two jobs, so the job that runs the pull request's code holds nothing.** `mutate` checks out the pull request with
  its base, has a read-only token, and writes a report artifact. `comment` checks out only the base commit (for the script that reads the report), reads the report as data
  against a closed schema, and writes one comment on the pull request, found by a marker and edited in place on later
  pushes (GITHUB_TOKEN, `pull-requests: write`).
- **What is mutated.** `git diff --unified=0 <base>...<head>` gives the changed lines of files in the repository's
  targets. Python: the functions containing them (from `ast`), run as mutmut's name globs; TypeScript and JavaScript:
  Stryker's `--mutate <file>:<start>-<end>` for each changed range. Only survivors whose mutated line is a changed line
  are reported. The tools' own exemptions (`# pragma: no mutate`, `// Stryker disable next-line <mutator>: <reason>`)
  are honoured by the tools themselves. A pull request that changes no target code says so and runs nothing.
- **The comment and summary** give the survivors on changed lines (location and change, the first 30), the counts,
  and the runtime of each step: mutmut's test-mapping pass, the mutants, the whole job. The report artifact holds the
  same numbers for later reading.
- **Its own budget**: `pr_budget_minutes` in the settings (proposed 45), so a pull request's runner time is bounded;
  past it, the comment says the run didn't finish and which functions weren't reached.
- **Drafts** run nothing, like CI; marking ready runs it.

Estimated cost per pull request, from today's CI timings: infrastructure ~10-15 min, troupe ~20-35 min, website
~5-10 min. The runtimes P records replace these estimates.

### D10. A raised baseline reaches main by an ordinary pull request (owner, 2026-11-17: option C)

The weekly run names the baselines it would raise in its summary and in each module's issue, and a person or agent
raises them in an ordinary pull request, as #322 does for coverage. There's no bot pull request and no baselines App:
opening one would need contents write and its own guard exemption. Rejected: **A** a new App (`troupe-run-baselines`)
with a reserved branch prefix and a guard exemption, filed as a follow-up Feature; **B** GITHUB_TOKEN, whose pull
requests start no workflows and so can't merge; **D** the release App with a new prefix, which blurs its purpose.

## Risks / Trade-offs

- **`tflint` can't parse OpenTofu-only syntax** (the `encryption` block) → trialled in CI on the draft pull request
  first (D2); a file it can't read is excluded in `.tflint.hcl` with the reason, and if it can't read the configuration at
  all, that goes back to the owner rather than a silent skip.
- **mutmut or libcst has no Python 3.15 build yet** → trialled before the workflow lands; if not, the owner decides
  between 3.14 for this job and waiting.
- **troupe's packages take longer than the budget** → the report marks modules not finished, those aren't judged, and
  mutmut's cache isn't kept between runs, so a package that never finishes shows in every summary. Then raise the
  budget or split the leg; the summary says which.
- **Flaky tests make mutants look killed or survived** → mutmut runs each mutant's tests once; a module's issue only
  changes its comment on a change of score, so one flaky week shows as one comment.
- **A first run opens many issues** → the cap (D6) and the dry run.
- **The mutate job runs other repositories' code on infrastructure's runners** → it's their `main`, which passed
  their own checks; the job holds no secret and a read-only token.

## Migration Plan

1. Land `tflint` with `tofu/` brought into line; CI runs it, and a local check without it says so (D2).
2. The owner creates the App (D4) and sets its key; the plan adds the environment, variable and label.
3. Merge the workflow; dispatch it with `dry-run`; the owner confirms or moves the threshold.
4. The weekly schedule files issues from then on.

Rollback: `gh workflow disable mutation.yml` stops the run; removing `tflint` from `check.py` removes the gate.

## Open Questions

- The exact Sunday time can move if it clashes with other weekly jobs; nothing depends on it.
