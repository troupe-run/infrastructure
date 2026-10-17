# Design: Run only the checks a change's paths need

## Context

See proposal.md for why. What exists today:

- `scripts/check-paths.toml` declares `[skip] paths = ["openspec/**"]` and no scope. Entries are exact paths or
  `dir/**` (commit-check-paths D2). Scopes may overlap each other, not the skip list.
- `guard.check_scope(paths, declaration)` is the one decision. The pre-commit hook calls it on the staged paths, and
  `guard.py check-scope` prints `scope=` and `check-args=` for `$GITHUB_OUTPUT` (commit-check-paths D6). Nothing in
  this repository's CI calls it yet.
- `scripts/check.py --scope <name>` runs every gate and narrows only pytest, to `-m "<a> or <b>"` (D8). pytest's
  "no tests ran" (exit 5) counts as a pass for a scope with no tagged tests.
- `scripts/guard_pytest.py` records every file a test opens (its own window, its collectors', its fixtures') and fails
  the test if it reads a scope's path without that scope's marker (D9). It can't see reads made by a subprocess, or
  imports after the first.
- `.github/workflows/ci.yml` has two jobs: `check` (the full `check.py`, Linux, Python 3.12) and `guard-tests` (the
  `test_guard_*.py` files on 3 OSes × 4 Pythons, less ubuntu/3.12, which `check` covers: 11 legs). All 12 contexts
  are required (`tofu/required-checks.json`).
- `tofu.yml`'s `changes` job and `pr-plan` are the pattern for a required job that's skipped when nothing it checks
  changed: a decision job with no secrets, and `if: !cancelled() && (needs.changes.result != 'success' || ...)` so a
  failed decision runs the job.

What the tests read was recorded on 2026-10-17 with a throwaway pytest plugin that dumped `guard_pytest`'s per-test
reads over the whole suite (889 tests). The files that matter here:

| File | Tests that read it |
|---|---|
| `tofu/dns.json` | `test_dns.py` |
| `tofu/milestones.json` | `test_milestones.py` |
| `tofu/labels/release.json`, `troupe.json` | `test_labels.py` |
| `tofu/labels/workflow.json` | `test_org_profile.py` |
| `tofu/*.tf` (every file) | `test_plan_needed.py` |
| `tofu/repositories.tf` | also `test_milestones.py`, `test_required_checks.py`, `test_guard_push_and_ci.py` |
| `tofu/guard_delivery.tf` | also `test_required_checks.py` |
| `tofu/release.tf` | also `test_guard_push_and_ci.py` |
| `tofu/required-checks.json` | `test_required_checks.py` (and named in `test_plan_needed.py`) |
| `docs/development-workflow.md` | `test_guard_docs.py` |
| `README.md`, `CLAUDE.md` | none |

The guard's tests (`test_guard_*.py`) read `.githooks/*`, `.github/workflows/guard.yml`, `scripts/guard.py`,
`scripts/guard_pytest.py`, `docs/development-workflow.md`, `tofu/guard_delivery.tf`, `tofu/release.tf` and
`tofu/repositories.tf`, and import `guard` and `conftest`.

## Goals / Non-Goals

**Goals:**
- The scoped run selects every test that reads a changed file, and the tag check keeps that true as tests change.
- A pull request's required checks all report, whether the matrix runs or not.
- Unknown paths keep running everything.

**Non-Goals:**
- Changing any delivered guard file, or the declaration's format.
- Narrowing ruff, mypy or the tofu gates. They take seconds (D8 of commit-check-paths).
- Narrowing the guard's matrix to the legs a change needs. It's all or none.

## Decisions

### D1. Five scopes, each named for what its files declare

```toml
[skip]
paths = ["openspec/**"]

[scopes.dns]          # tofu/dns.json: the troupe.run records
paths = ["tofu/dns.json"]

[scopes.milestones]
paths = ["tofu/milestones.json"]

[scopes.labels]
paths = ["tofu/labels/**"]

[scopes.tofu]         # the configuration itself, file by file, and the required checks it reads
paths = ["tofu/dns.tf", "tofu/environments.tf", ..., "tofu/versions.tf", "tofu/modules/**",
         "tofu/required-checks.json"]

[scopes.docs]
paths = ["docs/**", "README.md", "CLAUDE.md"]
```

The tests in the table above get the matching marker, at module level (`pytestmark`) where the module reads the file
at collection or in a shared fixture, or on the test itself where only some tests read it (`test_org_profile.py`'s
workflow-labels tests, `test_guard_push_and_ci.py`'s release-ruleset tests). `guard_pytest` reports any one missed on
the first full run, so the list in the apply is the plugin's, not a guess.

`docs` goes beyond the issue's examples. It costs one marker, and a docs-only change today runs 160 seconds of tests
that don't read docs. troupe already has the same scope.

*Alternatives:* one `declarations` scope for all of `tofu/**` (a DNS edit would then run every test that reads any
`.tf` file, including the guard's release-ruleset tests); scopes for `org-profile/**` and `oob/` (no recent pull
request changed only those; easy to add later in the same way).

### D2. `tofu` lists its files by name

The declaration allows only exact paths and `dir/**`, so `tofu/*.tf` can't be written. `tofu/**` would overlap `dns`,
`milestones` and `labels`, and every DNS change would also run every `tofu`-tagged test. Listing each top-level `.tf`
file keeps them apart. A new `.tf` file is in no group until it's added, so its first change runs the full check:
the safe direction. `tofu/terraform.tfstate`, `tofu/secrets.env` and `tofu/probe/` stay in no group. The App's state
commit doesn't run CI at all, and the other two change rarely.

### D3. No scope for Python sources

A test reads `scripts/tofu.py` by importing it, and Python imports a module once per process. The audit hook sees
the first import only, so a scope over a script couldn't be enforced: the tag check would miss every test after the
first that depends on it. `scripts/**` stays in no group, and a script change runs the full check. This is why #74
and #77, which changed `scripts/tofu.py` and `scripts/plan_checks.py`, would still have run the full `check`; what
they would have saved is the guard's matrix (D5).

### D4. `ci.yml` asks `check-scope` in a `changes` job

```
changes  (pull_request only; no secrets)
  git diff --name-only --no-renames "$BASE...$HEAD" > paths
  uv run --no-project scripts/guard.py check-scope < paths   >> $GITHUB_OUTPUT   # scope=, check-args=
  python3 scripts/guard_tests_needed.py < paths              >> $GITHUB_OUTPUT   # guard=true|false
check
  needs: changes; if: !cancelled() && needs.changes.outputs.scope != 'none'
  uv run scripts/check.py ${{ needs.changes.outputs.check-args }}
```

`BASE` and `HEAD` are the pull request's base and head SHAs, with `fetch-depth: 0`, as `tofu.yml`'s `changes` job
does. `--no-renames` matches the commit hook (commit-check-paths D3): a rename lists both paths.

- **A failed `changes` job** gives empty outputs. `check` then runs with no `check-args`, which is the full check, and
  the matrix runs (D5). A malformed declaration fails `changes`, and `check` then runs the full check, which fails at
  `guard_pytest`'s session start with the declaration's message. Either way the pull request is blocked, naming the
  file.
- **`scope=none`** skips `check` at the job level. A skipped required job counts as passed, the same as the plan
  job. `check` isn't a matrix job, so its skipped check run keeps its name.
- **On `push` to `main`**, `changes` doesn't run, its outputs are empty, and `check` runs in full (D7).

*Alternative:* deciding inside the `check` job, after installing uv and OpenTofu. That spends the setup on a run that
does nothing, and two steps would need the same condition.

### D5. `scripts/guard_tests_needed.py` lists what the matrix depends on

Like `plan_needed.py`: standard library, run with the runner's `python3` before anything is installed, paths on
stdin, `guard=true` or `guard=false` out. It names what the guard's tests depend on, with `/`-ending entries as
prefixes:

```python
DEPENDS_ON = (
    # The guard's files, delivered to every governed repository (tofu/guard_delivery.tf).
    "scripts/guard.py", "scripts/guard_pytest.py", ".githooks/", ".claude/settings.json",
    ".github/workflows/guard.yml",
    # Its tests, what they share, and what they run with.
    "scripts/tests/test_guard_", "scripts/tests/conftest.py", "scripts/check-paths.toml",
    "pyproject.toml", "uv.lock",
    # The matrix itself.
    ".github/workflows/ci.yml",
)
```

An empty list answers `true`.

This is a list of what's read, the opposite of `plan_needed.py`'s list of what isn't. The matrix doesn't guard a
merge on its own: whenever any path here changes, `check` also runs the full check, which includes every guard test on
Linux. The legs add the other OSes and Pythons, and those matter only for the guard's own code and how it runs. So
a path missing here costs cross-OS coverage on one pull request, and `main` runs every leg after the merge (D7), before
any delivery. Listing what isn't read instead would mean listing every declaration, script and doc, and it would grow
with each.

Two things keep the list honest:
- a test reads `guard_files` from `tofu/guard_delivery.tf` (as `test_required_checks.py` already reads that file) and
  fails, naming the file, if one isn't covered by `DEPENDS_ON`;
- a test feeds the script every `test_guard_*.py` file and `conftest.py` and expects `true`.

The guard's tests also read `docs/development-workflow.md` and three `tofu/*.tf` files. Those are consistency checks
between the guard and its documentation or its targets; they don't depend on the OS, and `check` runs them on Linux
under the `docs` and `tofu` scopes. They aren't listed.

*Alternatives:* a `guard` scope in `check-paths.toml` (D3: the guard is Python, so its scope couldn't be enforced);
reading the guard's file list from `tofu/guard_delivery.tf` at run time (HCL, before Python dependencies are
installed; the test gives the same safety).

### D6. One `guard tests` check reports for the matrix

GitHub names a skipped matrix job's check run with its unexpanded name, `guard tests (${{ matrix.os }}, Python ${{
matrix.python }})`, because the matrix is expanded only when the job runs. The 11 per-leg required contexts would
then never report, and a pull request that skipped the matrix could never merge. This is proven on a throwaway
repository before anything here depends on it (task 1.1).

So the legs stop being required, and one job is:

```yaml
guard-tests-result:
  name: guard tests
  needs: [changes, guard-tests]
  if: always()
  runs-on: ubuntu-latest
  steps:
    - run: python3 -c '...'   # passes if guard-tests succeeded, or was skipped because changes said guard=false
```

It fails when a leg failed or was cancelled, and when the legs were skipped although `changes` didn't succeed or said
`true` (something else skipped them). It runs on `push` to `main` too, where the legs always run. The legs keep their
names; `tofu/required-checks.json` lists `guard tests` in their place, and `test_required_checks.py` keeps comparing
that list with the jobs a pull request reports.

*Alternatives:* running every leg and skipping their steps (11 runners, macOS and Windows among them, each starting
up to do nothing; it's what the issue asks to stop); a path filter on the workflow (a required check that never
starts blocks the merge).

### D7. `main` keeps everything

On `push` to `main`, `changes` doesn't run, so `check` runs in full and every leg runs. `main` doesn't require a
branch to be up to date, so its merged tree may be one no pull request tested. The full run also catches what a
scoped run can't: a test that reads a scoped file without its tag fails only on a run that includes it, and a change
that adds such a test runs the full check anyway (adding a test isn't a scoped change). A guard delivery is planned
from a `main` commit whose run was green on all three OSes, which only this full run gives. `tofu.yml`'s plan of
`main` follows the CI run as before.

### D8. Proving it: a differential over past pull requests

#53 taught that the new path has to be checked against the old, not just tested on its own cases. The evidence task:

1. records each test's reads over the full suite, with the plugin used for the table above;
2. takes the changed paths of the last 40 merged pull requests here (`gh pr view --json files`);
3. for each, computes the new selection (`check-scope`, then `pytest --collect-only -m <expr>` for the selected
   tests, and `guard_tests_needed.py`), and checks that every test that reads a changed path is selected, or the
   answer is `full`;
4. lists, per pull request, what ran before (full check, 11 legs) and what runs now, with the time saved.

Any test that reads a changed path and isn't selected is a bug in the declaration or a missing tag; the apply stops
until it's fixed. The table goes in the pull request as evidence. Reads through a subprocess aren't in the recording;
the task also greps the tests for subprocesses that read a scoped file, and none were found while drafting this
design (`test_tofu_wrapper.py` runs a fake `tofu`).

## Risks / Trade-offs

- [Between the merge and the apply, the ruleset still requires the 11 leg names] → A pull request that skips the
  matrix in that window waits on checks that report under the unexpanded name. The apply follows the merge as soon as
  the owner approves main's plan; until then, pull requests that need the legs still pass. This pull request itself
  changes `ci.yml`, so its own legs run under their old names and satisfy the old ruleset.
- [A scope's tests read a file through a subprocess, unseen by the tag check] → None do today (D8). The declaration's
  comment says a scope's tags are kept by the plugin only for in-process reads.
- [`DEPENDS_ON` misses something the guard's tests depend on] → `check` still runs them on Linux, `main` runs every
  leg, and the delivery test catches a new guard file.
- [A scoped `check` hides a broken test elsewhere] → Only if that test reads none of the changed paths, so the change
  can't have broken it. `main`'s full run catches drift such as a dependency update.
- [`guard tests` is a new single point that must run] → It has `if: always()`, needs no setup, and fails closed on any
  result it doesn't recognise.

## Migration Plan

1. Prove the skipped-matrix naming and the result job on a throwaway repository (`troupe-run/infra-probe-*`), and
   delete it.
2. Merge the pull request: scopes and tags, `ci.yml`, the script, `required-checks.json`. Its plan shows the
   `infrastructure` ruleset's required checks changing from the 11 legs to `guard tests`.
3. The owner approves main's plan, and the apply updates the ruleset.
4. The next scoped pull request shows it working: `check` scoped or skipped, the legs skipped, `guard tests` green.

Rollback: revert the commit. The revert changes `ci.yml` and `required-checks.json`, so its own pull request runs every
leg, and its apply puts the 11 contexts back.
