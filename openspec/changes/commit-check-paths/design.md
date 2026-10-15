## Context

`run_pre_commit` in `scripts/guard.py` gathers the staged paths (`git diff --cached --name-only`) for the
archived-tasks and delivered-file rules, then calls `commit_checks(root)` last. `commit_checks` refuses when tracked
files have unstaged changes. Otherwise it runs `uv run scripts/check.py`, streaming the output, under a 10-minute
timeout (troupe's archived workflow-guardrails change, design D4). It doesn't look at what's staged, and it passes
`check.py` no arguments. Neither repository's `check.py` takes any today.

The guard is delivered to troupe as `scripts/guard.py` (`tofu/guard_delivery.tf`), along with its hooks and workflow.
`scripts/check.py` and anything else under `scripts/` stay each repository's own. The guard is standard-library
Python 3.12+, so `tomllib` and `sys.addaudithook` are available, but `PurePath.full_match` (3.13) isn't. Both
repositories run their tests with pytest.

This repository already has a path classifier: `scripts/plan_needed.py` decides from a pull request's changed paths
whether OpenTofu needs a plan. It lists what's *never read*, takes paths on stdin, and prints `plan=true|false` for
`$GITHUB_OUTPUT`. An empty list plans. This change follows the same shape, for a different reader.

What the checks read:
- **This repository:** no gate reads `openspec/`. ruff and mypy read Python, the tests build their OpenSpec trees in
  temporary directories, and `tofu` reads `tofu/`. `test_guard_docs.py` reads `docs/development-workflow.md`.
- **troupe:** no test reads `openspec/` (`git grep openspec` over the tests, #101). Six tests in
  `packages/troupe/tests/` check `docs/**` against the code: `test_cli_docs`, `test_runs_doc`, `test_runners_doc`,
  `test_event_store_doc`, `test_exit_codes_doc` and `test_platform_docs`. They run documented commands, and compare
  tables with enums, schemas and defaults. They only read files, so a `docs/**` change needs them and nothing else.
  `test_scripted_schemas.py` reads `plugins/runner-scripted/README.md`. No test reads the root `README.md`, although
  #101 lists it with `docs/**`.

## Goals / Non-Goals

**Goals:**
- A change runs the least its paths need: nothing, named scopes of the check, or the full check. It says which.
- The repository declares this once. The commit hook and CI read that one declaration with one function, and the
  tests' own tags say which tests a scope runs.
- The declaration can't silently go wrong: every test run fails a test that reads what its tags or the skip list
  say it doesn't.
- What troupe#101 needs is already here, so that troupe#101 writes troupe's declaration, tags and `check.py --scope`,
  and nothing in the guard.
- Nothing ties the contract to Python. A TypeScript repository with vitest follows the same declaration, the same
  `--scope` contract and the same tag rule, with its own adapter.
- Every case the guard can't classify for certain runs the full check, except a malformed declaration, which refuses.

**Non-Goals:**
- Changing the unstaged-changes refusal. It stays first, even when the commit would skip the check, so the rule reads
  the same for every commit.
- Validating the declaration in the `guard` GitHub check. A malformed one pushed with `--no-verify` refuses the next
  commit anyone makes, and fails the next test run, so it can't go unnoticed.
- A vitest adapter. The first TypeScript repository's change writes it against D8 and D9.
- Catching reads the audit hook can't see: files read by a subprocess a test starts. See Risks.
- `scripts/plan_needed.py`. It answers what OpenTofu reads, which is a different list.

## Decisions

### D1. The repository declares what its paths need, in `scripts/check-paths.toml`

troupe's file, once troupe#101 writes it, would look like this:

```toml
# What a change to these paths needs from scripts/check.py. Read by scripts/guard.py, for commits and for CI
# (spec: development-workflow). A path in no group needs the full check. A scope's tests are tagged with its name
# (pytest: @pytest.mark.<name>), and every test run checks the tags against what each test reads.
version = 1

[skip]  # no test reads these
paths = ["openspec/**"]

[scopes.docs]  # the tests that check the docs against the code
paths = ["docs/**", "plugins/runner-scripted/README.md"]
```

The file names what's needed *less* than everything, never what's read. A new folder, or a file nobody thought
about, then runs the full check, so a mistake costs a few minutes rather than a commit that should have failed.
`plan_needed.py` makes the same choice for the same reason.

It's TOML because the guard can parse it with the standard library, and it takes comments, so each group can say why
it's safe. It lives in `scripts/` beside `check.py`, the thing it describes. It isn't delivered: what a repository's
tests read is that repository's knowledge, and it changes when its tests do, through its own pull requests.

The schema is closed. The top level holds `version`, `skip` and `scopes`. `skip` and each scope hold only `paths`, a
list of strings. Both tables are optional, and an empty file apart from `version = 1` means everything runs the full
check.

A scope's name matches `[a-z][a-z0-9_]*`, so it's a valid tag in any test runner: a Python attribute for
`@pytest.mark.<name>`, a word in pytest's `-m` expressions, and an identifier in JavaScript. The first version allowed
hyphens. That was narrowed before any declaration existed, since narrowing later would break existing files. `none`
and `full` are reserved, because they're `check-scope`'s other answers (D6).

*Alternatives:* a list inside `guard.py` (generic code holding one repository's knowledge, and a delivery for every
change to it); a section in `pyproject.toml` (a `[tool.troupe-guard]` table mixes the guard into the package's
metadata, and troupe's root `pyproject.toml` is a workspace file); JSON (no comments); listing what *is* read (a new
path would silently skip); listing test files per scope (a hand-kept list that goes stale, which D8's tags and D9's
check replace).

### D2. Entries are exact paths or `dir/**`; skip and scopes don't overlap, scopes may

An entry is a relative POSIX path. Either it ends in `/**`, which means everything under that directory at any depth,
or it names one file exactly. Anything else is malformed: other wildcards (`*`, `?`, `[`), a bare `**`, an absolute
path, a backslash, an empty segment, or a `.` or `..` segment.

Python 3.12 has no matcher whose `**` means what git users expect (`fnmatch`'s `*` crosses `/`, and `full_match` is
3.13), and two forms cover every case known so far. Refusing anything else means a pattern can't quietly match more
or less than its author meant. The announcement prints entries as written, so `openspec/**` reads the same in the
file and in the message.

**Scopes may overlap.** A path belongs to every scope with an entry that matches it, so `path1/**` in both `blah` and
`blech` means a change to `path1/blah.py` runs both scopes (owner, 2026-10-15). That's the natural reading when a file
is read by tests of two concerns.

**Skip and a scope may not overlap.** "No test reads this" and "tests tagged `x` read this" contradict each other, so
neither reading can be assumed. With only the two entry forms, overlap can be decided exactly: `a/**` overlaps
`a/b/**` and `a/b.md`, and two exact entries overlap only when they're equal. The error names both entries.

### D3. The staged paths are listed with rename detection off

The guard lists paths with `git diff --cached --name-only --no-renames`, for this rule only. With rename detection
on, which is git's default, `--name-only` prints only a moved file's new name. So moving `src/a.py` to
`openspec/a.py` would look like an `openspec/`-only commit, and the check would be skipped for a commit that deletes
code. With `--no-renames`, the move shows as a deletion and an addition, and the deleted path counts. An archive
commit moves a folder within `openspec/`, so both of its names are skipped and it still skips.

The other rules keep their own path list unchanged.

### D4. The decision, and everything uncertain runs the full check

`check_scope(paths, declaration)` returns one of three things: nothing to run, a sorted set of scope names, or the
full check.

| Paths | Runs |
|---|---|
| none at all (`--allow-empty`, or CI can't tell) | full check |
| any path in no group | full check |
| `scripts/check-paths.toml` among them | full check |
| every path skipped | nothing |
| every path skipped or in at least one scope, and at least one in a scope | `check.py --scope <a> [--scope <b> ...]`: every scope any path is in, sorted |

With no declaration, every path is in no group, so everything runs the full check.

The hook reads the *staged* declaration, which is what the commit will contain, with the same `ReadStaged` the
delivered-file rule uses. A commit that changes the declaration always runs the full check, whatever the new file
says, so a declaration can't widen itself and benefit in the same commit. When it isn't staged, the staged copy
equals `HEAD`'s.

Paths in several scopes run those scopes together, not the full check (owner, 2026-10-15). It's cheaper and still
exact: each scope covers its own paths, so their union covers the change.

### D5. A malformed declaration refuses, under `commit-checks`

A file that's present but wrong isn't treated as absent (rule: a malformed input is an error, never a fall-through).
The refusal names the file, what's wrong (for example, "skip.paths[1] `docs/*.md` uses a wildcard other than a
trailing `/**`", or "`docs/**` in skip overlaps `docs/cli/**` in scopes.docs"), and the fix ("write an exact path or
`dir/**`", or "list each path in one group").

It uses the existing `commit-checks` rule id rather than a new rule. It refuses for the same reason: the guard can't
show that the check passes. The owner's override for `commit-checks` already means "commit without the check", so a
new id would add a second override with the same effect. Parsing and deciding are pure functions,
`check_paths(text) -> CheckPaths` and `check_scope(paths, declaration) -> Scope`, so the hook and CI can't drift
apart.

### D6. `guard.py check-scope` is CI's entry to the same rule

```
git diff --name-only --no-renames "$BASE...$HEAD" | uv run --no-project scripts/guard.py check-scope
```

It reads the paths on stdin, reads `scripts/check-paths.toml` from the working tree (CI has checked out the head),
and prints two lines for `$GITHUB_OUTPUT`:

| Decision | Output |
|---|---|
| nothing | `scope=none` and `check-args=` |
| scopes | `scope=api,docs` and `check-args=--scope api --scope docs` |
| full | `scope=full` and `check-args=` |

A job then reports success when `scope` is `none`, and otherwise runs `uv run scripts/check.py ${{ check-args }}`.
Scope names are `[a-z][a-z0-9_]*`, so the arguments split on spaces safely in any shell, and the list joins on commas
without ambiguity. When the declaration is malformed, it prints the refusal's text to stderr, prints nothing to
stdout, and exits 1, so the job fails rather than skipping. This is the same contract as `plan_needed.py`.

troupe#101 still has to start every required job and decide inside it, and has to work out the base itself, passing
an empty list when it can't (a new branch, a force push, a shallow history). Those are CI questions, so they stay with
troupe#101. If its design needs a different interface, it changes this subcommand here rather than adding a second
reader in troupe.

### D7. Both repositories adopt it; troupe's files arrive through troupe

This repository gets the whole pattern, so it's proven here before troupe relies on it:
- `scripts/check-paths.toml` with `[skip] paths = ["openspec/**"]` and no scopes. Its gates don't read `openspec/`
  (see Context).
- `--scope` in its `check.py`. With no scopes declared, every name is refused, but the contract is in place.
- The plugin loaded from `pyproject.toml`, so every test run here proves that no test reads `openspec/`.

troupe's declaration, its `docs` markers, its `check.py --scope` and its pytest configuration are troupe's own files,
so they reach troupe through troupe#101's change. Until that lands, troupe's commits run the full check as they do
today. The guard ignores a missing declaration, so the order of the two doesn't matter.

To show #45's "Done when" in troupe before that, the evidence task uses a local scratch clone of troupe with all of
the above in place, and nothing is pushed.

### D8. A scope is a test tag, and narrows only the tests

The guard runs `uv run scripts/check.py --scope <a> --scope <b>`: one flag per scope, names sorted and deduplicated
(`argparse`'s `action="append"`). It treats a scoped run exactly like the full one. It's announced, naming the scopes,
its output streams, it has the same timeout, and a non-zero exit refuses, naming the failed gate from `check.py`'s
`check: <gate> failed` line. The guard doesn't know what a scope runs.

The contract for each repository's `check.py`, whatever its language:
- **Every gate still runs.** Linters, type checkers and `tofu validate` take seconds, and a scope then can't skip a
  lint error. Only the tests, the slow part, are narrowed.
- **The tests narrow to those tagged with any of the scopes.**
- **A scope the declaration doesn't list is refused**, before any gate runs, naming the scope and the file. The guard
  never passes one, so this catches only a hand-typed mistake.

For pytest, the tag is a marker named for the scope: `@pytest.mark.docs` on a test, or `pytestmark = pytest.mark.docs`
on a module. `check.py` runs `pytest -m "api or docs"`. pytest's `-m` takes a boolean expression, and
`guard.marker_expression(names)` builds it, so no repository writes that by hand.

For a future vitest repository, `check.py` (still Python, since every governed repository already runs the guard with
uv) runs eslint and tsc, then vitest narrowed to the tests tagged with those scopes, by whatever tagging vitest
offers then. It also runs a vitest adapter for D9. Nothing in the declaration, the guard or the spec changes.

### D9. Every test run checks the tags against what each test reads

The rule is a pure guard function over plain data, so any runner can use it:

```python
@dataclass(frozen=True)
class TestReads:
    test: str                  # the runner's id for the test
    tags: frozenset[str]
    reads: frozenset[str]      # repository-relative POSIX paths the test opened

def tag_violations(test: TestReads, declaration: CheckPaths) -> list[str]
```

For each file a test read, the scopes whose entries match it must all be in the test's tags, and no skip entry may
match it. Each violation names the test, the file, and either the tags to add or the skip entry it contradicts. Files
in no group are ignored: the full check covers them.

The pytest adapter is a plugin, `scripts/guard_pytest.py`. It's delivered with the guard, so both repositories run
one copy. It's loaded with `-p guard_pytest` in `addopts`, with `scripts` on pytest's `pythonpath`, the way troupe
already loads its `protocol_guard` plugin. A `pytest_plugins` line works only in a root `conftest.py`, which neither
repository has. It:
- reads `scripts/check-paths.toml` at the start of the session (a malformed one fails the session with D5's message),
  and registers each scope as a marker, so `--strict-markers` accepts them and the declaration is the one list;
- records the `open` audit event (`sys.addaudithook`, standard library) for every file opened during each test's
  setup, call and teardown, keeping only files inside the repository;
- after each test, fails it if `tag_violations` finds anything, so the failure names the test as pytest reports it.

An audit hook can't be removed, so the plugin installs one hook per process. It records only while a test is running.
`Path.read_text`, `open` and `json.load(open(...))` all raise the event, which covers how the doc tests read.

The check runs on every test run, scoped or full. A scoped run checks the tests it runs. A full run checks them all,
and it's what catches a new test that reads `docs/` without its tag. A docs-only change can't introduce that gap,
because adding a test isn't a docs-only change.

*Alternatives:* static analysis of test sources for path strings (misses computed paths such as
`DOC.parent / "runs.md"`); a hand-kept list of test files per scope (goes stale silently, the problem this replaces);
the plugin as code each repository copies (two copies drift; delivering it keeps one).

## Risks / Trade-offs

- [A test reads a file through a subprocess, such as a CLI run with `subprocess`] → The audit hook sees only the test
  process, so that read isn't checked. troupe's doc tests call `main()` in-process, so they're seen. A scope whose
  tests read through subprocesses needs its tags kept by hand, and the declaration's comment should say so. Pushes to
  `main` still run everything (#101).
- [A declared scope isn't implemented by `check.py`] → `check.py` refuses an undeclared scope, and a declared one
  with no tagged tests runs no tests but still every other gate. The tag check fails any test that reads the scope's
  paths untagged, so an empty scope can only stay empty while no test reads its paths.
- [The audit hook slows the tests] → It does a string comparison per opened file while a test runs. That's
  negligible next to the tests, and it's measured in the evidence task.
- [A skip or scope hides a slow or broken full check from the person committing] → Each run is announced, and the
  next commit that stages anything undeclared runs the full check.
- [`--no-renames` disagrees with what the other rules see] → It applies only to this rule's decision. Seeing extra
  paths can only cause more to run, never less.
- [The `commit-checks` override now covers a malformed declaration too] → It already allowed a commit without the
  check, so it grants nothing new.

## Migration Plan

1. Merge here: the guard reads declarations, the plugin checks tags, and this repository skips `openspec/**`.
2. Deliver `scripts/guard.py` and `scripts/guard_pytest.py` to troupe (CI green on all three OSes, then the owner
   approves the plan). troupe has no declaration and doesn't load the plugin yet, so nothing changes there.
3. troupe#101's change adds troupe's declaration, its `docs` markers, `-p guard_pytest`, `check.py --scope`, and
   its CI use of `check-scope`. From then on, troupe's `openspec/`-only commits skip the check, its `docs/`-only commits
   run the doc tests, and every test run checks the tags.

Rollback: delete a repository's `scripts/check-paths.toml`, and its commits run the full check again. The plugin then
registers no markers and checks nothing. No delivery is needed.
