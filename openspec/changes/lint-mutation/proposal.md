# Proposal

## Why

#321 decided the gates every pull request must pass before it can merge, and the slower checks that run on a schedule
and report instead (owner, 2026-11-17). If pull requests are to merge without the owner (#320), the gates are what
makes that safe. This change builds two of the four Features that came out of it, in this repository:

- **#323, linting:** infrastructure's check already runs `tofu fmt -check` (since the first check), but nothing lints
  the OpenTofu configuration beyond `tofu validate`. `tflint` is the missing gate. (website's ESLint, Prettier and
  `tsc --noEmit` are the other half of #323; they change website's own files, so they're a website change.)
- **#325, mutation testing:** coverage says a line ran, not that a test would notice it change. Mutation testing does,
  but it's too slow for every pull request, so #321 put it on a weekly schedule that reports as issues.

## What Changes

- **`tflint` joins infrastructure's check.** `scripts/check.py` runs `tflint` over `tofu/` after `tofu validate`,
  with its rules in `.tflint.hcl`, and blocks like every other gate, locally and in CI's `check` job. The OpenTofu
  configuration is brought into line, or a finding the owner accepts is recorded in `.tflint.hcl` with its reason.
  `tofu fmt -check` is already a gate and stays as it is.
- **A weekly mutation testing workflow** (`.github/workflows/mutation.yml`) runs on Linux with Python 3.15. One job
  per repository checks out troupe, infrastructure or website at `main`, with no secret, and runs `mutmut` (Python) or
  Stryker (website's TypeScript) within a time budget. Each writes a report of every module's score and surviving
  mutants.
- **Its settings live in one place**, `scripts/mutation.json`: the score threshold, the time budget, the smallest
  module judged, how many issues one run may open, the tool versions, and what each repository mutates and tests.
- **One issue per module under the threshold.** A script reads the reports and, for each module under the threshold,
  opens one issue in that module's repository, labelled `test-quality`, listing its surviving mutants, or updates the
  one already open: never a duplicate. A module back over the threshold gets a comment and its issue closed. New
  issues go on the troupe roadmap board.
- **It never blocks a merge.** It isn't a required check and runs on no pull request.
- **A `test-quality` label** in every managed repository, declared with the other kinds of work in
  `tofu/labels/kinds.json` (spec: labels, "Kinds of work beyond GitHub's defaults are declared once", unchanged).
- **A credential to file the issues** in troupe and website, which `GITHUB_TOKEN` can't write (design D4: the owner's
  decision).

## Capabilities

### New Capabilities

- `mutation-testing`: the weekly mutation run, its settings, and the issues it keeps for under-tested modules.
- `mutation-issue-credentials`: the credential the mutation run files its issues with, and where its key is held.

### Modified Capabilities

- `ci-apply`: the check gains `tflint` as a gate, so the scoped-check scenario that lists the gates names it.

## Impact

- `scripts/check.py`, `.github/workflows/ci.yml` (installs `tflint`), `.tflint.hcl`, and any `tofu/` file `tflint`
  finds fault with.
- New: `.github/workflows/mutation.yml`, `scripts/mutation.json`, `scripts/mutation_report.py` (turns a tool's results
  into the report), `scripts/mutation_issues.py` (keeps the issues), and their tests.
- `tofu/labels/kinds.json` (the label), the credential's environment and variable in `tofu/`, and
  `oob/app-installations.json` if the owner chooses a new App.
- `scripts/watched-schedules.json`: the weekly workflow is watched like the other scheduled ones.
- `docs/development-workflow.md` and `README.md`: the new gate and the weekly report.
- troupe and website: no file changes for #325; their code is read at `main`. Local developers need `tflint`
  installed for infrastructure's check.
- Not here: website's ESLint, Prettier and `tsc --noEmit` (a website change), #322 (coverage) and #324 (complexity
  and dependency audit), which change the same check script; whichever merges second rebases.
