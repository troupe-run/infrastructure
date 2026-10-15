## Context

`run_pre_commit` in `scripts/guard.py` gathers the staged paths (`git diff --cached --name-only`) for the
archived-tasks and delivered-file rules, then calls `commit_checks(root)` last. `commit_checks` refuses when tracked
files have unstaged changes. Otherwise it runs `uv run scripts/check.py`, streaming the output, under a 10-minute
timeout (troupe's archived workflow-guardrails change, design D4). It doesn't look at what's staged, and it passes
`check.py` no arguments. Neither repository's `check.py` takes any today.

The guard is delivered to troupe as `scripts/guard.py` (`tofu/guard_delivery.tf`). `scripts/check.py` and anything
else under `scripts/` stay each repository's own. The guard is standard-library Python 3.12+, so `tomllib` is
available, but `PurePath.full_match` (3.13) isn't.

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
- The repository declares this once, and the commit hook and CI read that one declaration with one function.
- What troupe#101 needs is already here, so that troupe#101 writes troupe's declaration and its `check.py --scope`,
  and nothing in the guard.
- Every case the guard can't classify for certain runs the full check, except a malformed declaration, which refuses.

**Non-Goals:**
- Changing the unstaged-changes refusal. It stays first, even when the commit would skip the check, so the rule reads
  the same for every commit.
- Validating the declaration in the `guard` GitHub check. A malformed one pushed with `--no-verify` refuses the next
  commit anyone makes, so it can't go unnoticed.
- Deciding what a scope runs. That's each repository's `check.py` (D8).
- `scripts/plan_needed.py`. It answers what OpenTofu reads, which is a different list.

## Decisions

### D1. The repository declares what its paths need, in `scripts/check-paths.toml`

troupe's file, once troupe#101 writes it, would look like this:

```toml
# What a change to these paths needs from scripts/check.py. Read by scripts/guard.py, for commits and for CI
# (spec: development-workflow). A path in no group needs the full check.
version = 1

[skip]  # no gate reads these
paths = ["openspec/**"]

[scopes.docs]  # the doc tests; `check.py --scope docs` runs them
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
check. A scope's name matches `[a-z][a-z0-9-]*` and isn't `none` or `full`, which are `check-scope`'s other answers
(D6).

*Alternatives:* a list inside `guard.py` (generic code holding one repository's knowledge, and a delivery for every
change to it); a section in `pyproject.toml` (a `[tool.troupe-guard]` table mixes the guard into the package's
metadata, and troupe's root `pyproject.toml` is a workspace file); JSON (no comments); listing what *is* read (a new
path would silently skip); naming test files in the declaration instead of scopes (the guard would then know how each
repository runs its tests, which is `check.py`'s job, D8).

### D2. Entries are exact paths or `dir/**`, and groups don't overlap

An entry is a relative POSIX path. Either it ends in `/**`, which means everything under that directory at any depth,
or it names one file exactly. Anything else is malformed: other wildcards (`*`, `?`, `[`), a bare `**`, an absolute
path, a backslash, an empty segment, or a `.` or `..` segment.

Python 3.12 has no matcher whose `**` means what git users expect (`fnmatch`'s `*` crosses `/`, and `full_match` is
3.13), and two forms cover every case known so far. Refusing anything else means a pattern can't quietly match more
or less than its author meant. The announcement prints entries as written, so `openspec/**` reads the same in the
file and in the message.

No path may match entries in two groups (skip and a scope, or two scopes). With only these two forms, overlap can be
decided exactly: `a/**` overlaps `a/b/**` and `a/b.md`, and two exact entries overlap only when they're equal. An
overlap is malformed rather than resolved by an order, because either reading could be what the author meant. The
error names both entries and their groups. The same entry twice in one group is harmless and allowed.

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
| every path skipped or in a scope, with at least one in a scope | `check.py --scope <a> [--scope <b> ...]`, the scopes the paths touch, sorted |

With no declaration, every path is in no group, so everything runs the full check.

The hook reads the *staged* declaration, which is what the commit will contain, with the same `ReadStaged` the
delivered-file rule uses. A commit that changes the declaration always runs the full check, whatever the new file
says, so a declaration can't widen itself and benefit in the same commit. When it isn't staged, the staged copy
equals `HEAD`'s.

Paths in several scopes run those scopes together, not the full check (owner, 2026-10-15). It's cheaper and still
exact: each scope covers its own paths, so their union covers the change. It does rely on scopes combining in one
`check.py` run, which D8 makes part of the contract.

### D5. A malformed declaration refuses, under `commit-checks`

A file that's present but wrong isn't treated as absent (rule: a malformed input is an error, never a fall-through).
The refusal names the file, what's wrong (for example, "skip.paths[1] `docs/*.md` uses a wildcard other than a
trailing `/**`", or "`docs/**` in scopes.docs overlaps `docs/cli/**` in skip"), and the fix ("write an exact path or
`dir/**`; see the comment at the top of the file", or "list each path in one group").

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
Scope names are `[a-z][a-z0-9-]*`, so the arguments split on spaces safely in any shell, and the list joins on commas
without ambiguity. When the declaration is malformed, it prints the refusal's text to stderr, prints nothing to
stdout, and exits 1, so the job fails rather than skipping. This is the same contract as `plan_needed.py`.

troupe#101 still has to start every required job and decide inside it, and has to work out the base itself, passing
an empty list when it can't (a new branch, a force push, a shallow history). Those are CI questions, so they stay with
troupe#101. If its design needs a different interface, it changes this subcommand here rather than adding a second
reader in troupe.

### D7. This repository skips `openspec/**`; troupe's file arrives through troupe

This repository gets `scripts/check-paths.toml` with `[skip] paths = ["openspec/**"]` and no scopes, since nothing
here would use one yet. It's the first real use, and its gates don't read `openspec/` (see Context).

troupe's declaration and its `check.py --scope docs` are troupe's own files, so they reach troupe through troupe#101's
change, which owns which tests a docs change runs. Until that lands, troupe's commits run the full check as they do
today. The guard ignores a missing file, so the order of the two doesn't matter.

To show #45's "Done when" in troupe before that, the evidence task uses a local scratch clone of troupe. It installs
this branch's `guard.py`, a declaration with a skip and a `docs` scope, and a minimal `--scope docs` in its
`check.py` that runs the six doc tests. It commits on a branch whose change exists, and records what ran each time.
Nothing is pushed.

### D8. The `--scope` contract with each repository's `check.py`

For scopes, the guard runs `uv run scripts/check.py --scope <a> --scope <b>`: one flag per scope, names sorted and
deduplicated. That's `argparse`'s `action="append"`, with no splitting rules for the two sides to agree on. The guard
treats a scoped run exactly like the full one. It's announced, naming the scopes, its output streams, it has the same
timeout, a non-zero exit refuses naming the failed gate, and `check.py`'s `check: <gate> failed` line is read the same
way.

The guard passes only names the declaration lists, and doesn't know what a scope runs. A repository that declares a
scope must make its `check.py` accept `--scope <name>` and run, for several scopes, everything each one needs.
`check.py` should refuse a name it doesn't know. That refusal reaches the person committing as a failed check, which
is the right outcome: the declaration and `check.py` disagree, and that has to be fixed in the repository. A
repository with no scopes never receives the flag, so neither `check.py` changes in this change.

## Risks / Trade-offs

- [A skipped path is in fact read by a gate, now or later] → The check is skipped for a commit that would have
  failed. CI catches it on the push until troupe#101 also skips there. After that, pushes to `main` still run
  everything (#101), so it shows before the next merge at the latest. The list only names deliberate exceptions, so
  only a deliberate entry can be wrong.
- [A scope misses a test that reads its paths] → The same mitigation as above. The scope's comment in the
  declaration says which tests it runs, and a reviewer can check it against `git grep` for the paths.
- [`check.py` doesn't implement a declared scope] → Every scoped commit fails with the check's own message, until
  `check.py` and the declaration agree. That fails closed.
- [A skip or scope hides a slow or broken full check from the person committing] → Each run is announced, and the
  next commit that stages anything undeclared runs the full check.
- [`--no-renames` disagrees with what the other rules see] → It applies only to this rule's decision. Seeing extra
  paths can only cause more to run, never less.
- [The `commit-checks` override now covers a malformed declaration too] → It already allowed a commit without the
  check, so it grants nothing new.

## Migration Plan

1. Merge here: the guard reads declarations, and this repository skips `openspec/**`.
2. Deliver `scripts/guard.py` to troupe (CI green on all three OSes, then the owner approves the plan). troupe has no
   declaration yet, so nothing changes there.
3. troupe#101's change adds troupe's declaration, `check.py --scope docs`, and its CI use of `check-scope`. From then
   on, troupe's `openspec/`-only commits skip the check, and its `docs/`-only commits run the doc tests.

Rollback: delete a repository's `scripts/check-paths.toml`, and its commits run the full check again. No delivery is
needed.
