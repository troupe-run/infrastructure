# Design

## Context

`guard.py ci` re-checks the git-level rules on GitHub (`run_ci`): commit messages, schema commit types, the branch's
change, archived tasks and delivered files. It's standard library only and runs under `uv run --no-project` in
`.github/workflows/guard.yml`, which is delivered to troupe and website and is the required `guard (workflow rules)`
check. Nothing in the job installs Node today.

What OpenSpec 1.14.3 does, measured on 2026-10-24 against a probe repository in the scratchpad:

- `openspec validate --all --strict --json --no-interactive` validates every main spec and every active change in one
  call. It doesn't read `openspec/changes/archive/`. It exits 1 when anything fails, and prints a JSON report:
  `items[]` with `id`, `type` (`spec` or `change`), `valid` and `issues[]` (`level`, `path`, `message`).
- Strict mode fails an item on a `WARNING` as well as an `ERROR`. The length limit is a warning.
- A main spec's issue names its requirement by position only: `path` is `requirements[0]`, and the message ("Requirement
  text is very long (>500 characters). Move examples …") doesn't name it. A change's issue names its delta file in
  `path` (`foo/spec.md`) and quotes the requirement in the message (`ADDED "Nope" must include at least one scenario`).
- The run takes about a second here (17 specs). Today every spec and active change passes strict validation in all
  three governed repositories.
- The CLI reads `OPENSPEC_TELEMETRY` and `DO_NOT_TRACK`. It needs Node 20.19 or later.

## Goals / Non-Goals

**Goals:**

- A refusal a reader can act on without rerunning anything: the spec or change, the requirement's name, OpenSpec's
  message, and the command to reproduce it with the version CI used.
- One place for the OpenSpec version.
- The rule's logic tested on every OS and Python version, like the rest of the guard, without Node in the tests.

**Non-Goals:**

- Local hooks (D7).
- Failing a pull request for a spec it doesn't touch (D3).
- Validating archived changes, or the archive's task check (`openspec validate --archived`), which `archive-incomplete`
  already covers.
- Fixing anything OpenSpec reports: a repository that fails after delivery fixes its specs in its own change.

## Decisions

### D1. A guard rule, not a separate workflow step

`guard.py ci` gains one more decision, `openspec-strict`, and `guard.yml` only installs the CLI. Calling `openspec
validate` as its own step would be shorter, but its text output names a main spec's requirement only as
`requirements[0]`, has no fix, and doesn't read like the guard's other refusals (spec: "Refusals name the rule and the
fix"). In the guard, the rule's reading of OpenSpec's report is a function with tests, and `guard.py ci` stays the one
command the check runs.

The guard doesn't import or vendor anything: it runs the `openspec` on `PATH` with `subprocess`, as it runs `git`, and
stays standard library only. It finds it with `shutil.which`, because npm installs it as `openspec.cmd` on Windows,
which `subprocess` doesn't find by its bare name.

The rule is a pure function of the scope (D3) and a report, and the call to OpenSpec is a parameter with the real CLI
as its default, so tests pass a captured report instead of needing Node. `run_ci` keeps its git-level rules as they
are, and `run_ci_entry` adds `openspec-strict` after them. The existing `run_ci` tests build OpenSpec trees in
temporary repositories and expect no refusal; on a test leg with no OpenSpec installed they'd otherwise fail for a
missing CLI. The changed paths `run_ci` already lists move into a helper both use.

### D2. One call, read as JSON, and nothing else trusted

The guard runs `openspec validate --all --strict --json --no-interactive` at the repository root, with
`OPENSPEC_TELEMETRY=0` and `DO_NOT_TRACK=1` set for that process. It decides from the JSON report: every item with
`valid: false` is a failure, whatever the exit status. The exit status is only cross-checked: a non-zero exit with no
failing item, or a zero exit with one, is an unreadable result.

Each of these fails under `openspec-strict` with what happened (spec: "Strict validation that can't run fails the
check"), and none passes:

- no `openspec` on `PATH`: says so, and that the version is pinned in `.github/workflows/guard.yml`;
- output that isn't a JSON object with an `items` list whose entries have the fields above: names the exit status and
  the end of standard error;
- the cross-check above failing;
- the run outliving a timeout (60 seconds, a constant in the guard), so a hung CLI fails inside the job's 5 minutes
  with the guard's message rather than GitHub's.

A repository with no `openspec/` directory at its root passes without running anything: absent, not malformed.

Alternative considered: trusting the exit status and printing OpenSpec's text. Rejected for the naming reason in D1,
and because a crash and a failure would then read the same.

### D3. The scope comes from the range's paths, and the report is filtered to it

The owner chose this on 2026-10-24, on this change, after a side review pointed out that validating everything on
every run lets one broken spec on main fail every pull request. `run_ci` already lists the paths each commit in the
range changes. From them:

- `openspec/specs/<id>/…` puts the main spec `<id>` in scope;
- `openspec/changes/<name>/…`, other than under `archive/`, puts the active change `<name>` in scope, if it still
  exists at the head;
- any path in `OPENSPEC_ALL_PATHS` (a constant in the guard: `scripts/guard.py` and `.github/workflows/guard.yml`)
  puts everything in scope, because those files decide how validation runs and which version runs it;
- a push to `main` (a run with no pull request title whose branch is `main`) puts everything in scope, whatever it
  changed.

Archiving moves a change under `archive/` and syncs its deltas into `openspec/specs/<id>/`, so the specs it changes
are in scope through the first rule.

The guard still runs one `openspec validate --all` (D2) and keeps the items in scope. One call over a repository takes
about a second, so filtering costs less than a call per item and reads one report shape. An empty scope doesn't run
OpenSpec at all.

A change's delta isn't followed to the main spec it targets: until it's archived, the main spec hasn't changed, and the
change's own validation covers its delta.

Alternatives considered: skipping the rule unless `openspec/**` changed, which leaves the first spec-touching pull
request after a break failing for something it didn't do, and misses a pin bump unless the guard's paths are added
anyway; and validating everything on every run, the first draft, which is the problem above.

### D4. Naming a main spec's requirement by reading the spec

For an issue on a `spec` item whose `path` is `requirements[<n>]`, the guard reads `openspec/specs/<id>/spec.md` and
takes the `n`th `### Requirement:` heading (counting from 0, in file order, the headings OpenSpec itself parses). The
refusal then says `requirement "Steps are reported" (requirements[3])`. If the file or the heading can't be found, it
says `requirements[3]` alone: the path OpenSpec gave is still true, so the refusal stays accurate, just less helpful.

A `change` item's issues already quote the requirement in the message and name the delta file in `path`, so they're
reported as given, with the path under `openspec/changes/<id>/specs/`. Any other `path` (`overview`, a file name) is
reported as given too.

Apply first checks the counting against OpenSpec 1.14.3 with a probe that has a failing requirement that isn't the
first one, so the index → name mapping is measured, not assumed (task 1.1).

### D5. One refusal, listing every item

`openspec-strict` returns one `Decision`, like `nonconforming_commits`: the problem lists every failing item with its
issues (`spec runner-protocol: requirement "Steps are reported" (requirements[3]): Requirement text is very long …`),
and the fix is:

> Run `openspec validate <id> --type <spec|change> --strict` with OpenSpec `<version>` and fix what it reports. For a
> long requirement, move examples into scenarios, or split it.

with `<id>` and `<type>` filled in when one item fails, and `--all` when several do. `<version>` is what
`openspec --version` printed in the same run, so the message can't disagree with the CLI that produced it.

The rule isn't overridable: it runs only on GitHub, where no override is consumed. It's added to `RULES` beside
`TAMPER_RULE` as a CI-only rule, not to `OVERRIDABLE_RULES`, so `guard.py override openspec-strict` is refused by the
existing choice check.

### D6. The pin, in the workflow

`guard.yml` gets a job-level `OPENSPEC_VERSION: 1.14.3`, `actions/setup-node` with an exact Node version, and a step
`npm install --global "@fission-ai/openspec@${OPENSPEC_VERSION}"` before the guard runs. That's how the other tools
are pinned: an exact version in the workflow (`tofu_version: 1.13.1`, `python-version: "3.12"`). The guard doesn't
compare versions: it reports the one it ran (D5).

1.14.3 is the version sessions here run today. 1.15.0 was published on 2026-10-24, hours before this design. Moving
the pin is a one-line change to a delivered file, so it's made and delivered like any other guard change, and its
pull request's `guard` run validates everything with the new version (D3). That covers this repository only. The
same delivery takes the new version to troupe and website, where it lands on main with no pull request, so
`docs/development-workflow.md` gets a step for moving the pin: run the new version over all three repositories' main
and name any failure before asking for the delivery plan's approval.

Node is set up only for that step's sake. `setup-node` is pinned by SHA with a version comment, as the workflow's other
actions are: that's the file's style, not a policy (the org doesn't require SHA pinning).

### D7. CI only

The owner chose CI only (2026-10-24, on this change). The required check stops a broken spec before it merges, which
is what #123 is about. A local hook would need Node and OpenSpec on every contributor's machine, and a local version
that differs from the pin could refuse what CI accepts or the other way round. Nothing in `run_pre_commit`,
`run_commit_msg` or `run_pre_push` changes.

## Risks / Trade-offs

- [A new OpenSpec release changes what strict validation reports] → The pin means nothing changes until the pin does.
  That pull request validates everything here (D3), and the pin step checks troupe's and website's main before the
  delivery is approved (D6).
- [A spec breaks on main and stays broken, because pull requests that don't touch it pass] → main's own `guard` run
  fails at once and shows it (D3). It blocks no one, so it can be left red: the owner sees it on main's checks.
- [Two pull requests each pass alone but break a spec together] → main's `guard` run after the second merge shows it.
- [OpenSpec changes its JSON report's shape] → An unreadable report fails with the exit status and standard error
  (D2), so it can't pass silently. The shape is checked by tests built from a report captured from 1.14.3, not a
  hand-written one.
- [Delivery starts failing troupe's or website's pull requests] → Both pass today. The plan task runs the pinned CLI
  against each target's main again before the owner approves the plan, and names any failure first.
- [npm is unavailable during a run] → The install step fails and so does the check, visibly. A re-run is the fix; a
  spec that's broken can't merge in the meantime either way.
- [The job's 5-minute timeout] → Node setup and the install take seconds; the guard's own 60-second limit on the
  validation keeps a hung CLI from using the rest.
- [Requirement counting differs from OpenSpec's] → Measured in apply (D4); a mismatch would show the wrong name, so the
  test asserts the name for a requirement that isn't first.

## Migration Plan

1. Merge here once CI is green on all three OSes and the plan is approved. This change's own pull request changes
   `scripts/guard.py`, so its `guard` check validates every spec and active change here.
2. The plan shows `scripts/guard.py` and `.github/workflows/guard.yml` changing in troupe-run/troupe and
   troupe-run/website. Before asking for approval, run the pinned CLI against each one's main.
3. After the apply, check one `guard` run in each target shows OpenSpec installed and the rule passing.

Rollback: revert the commit here and deliver again. Nothing is stored, and no ruleset or required check changes.
