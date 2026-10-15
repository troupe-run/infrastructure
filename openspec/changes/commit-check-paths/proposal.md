## Why

The commit guard runs the repository's whole `scripts/check.py` before every commit, whatever the commit stages
(#45). In troupe that's about 3.5 minutes on macOS, and the workflow makes many commits that change no code. On
troupe-run/troupe#99, the archive commit `606f03c` only moved a change folder under `openspec/`, and the guard still
ran 1669 tests in 214 s before allowing it. The proposal commit before it, four new files under `openspec/changes/`,
took about as long.

troupe-run/troupe#101 asks the same question of troupe's CI, and adds a second case: a `docs/**` change can't skip
the tests, because six tests check the docs against the code, but it needn't run the other 1600. Both issues need one
answer to "what does a change to these paths have to run?", and only the repository knows it. The guard is generic,
so the rule can't live in it. This change builds what both need. troupe#101 then only has to fill it in for troupe.

## What Changes

- **A repository declares what its paths need**, in `scripts/check-paths.toml`, which it owns (it isn't delivered).
  The format is closed: `version = 1`, a `[skip]` table of paths no gate reads, and any number of
  `[scopes.<name>]` tables, each listing the paths whose changes that part of the check covers. Each entry is an exact
  path or a directory written `dir/**`. Anything else, groups whose entries overlap, and a bad or reserved scope name
  are all malformed. A path in no group needs the full check, so a new folder runs everything until someone declares
  otherwise (design D1, D2).
- **A change's paths decide what runs** (design D4):
  - every path skipped: nothing runs;
  - every path skipped or in a scope: those scopes run, as `scripts/check.py --scope <a> --scope <b>`;
  - any path in no group, no paths at all, or a commit that stages the declaration itself: the full check runs.
- **The check's contract gains `--scope`** (design D8). The guard passes only names the declaration lists, sorted and
  deduplicated, and doesn't know what a scope does. A repository that declares a scope makes its `check.py` accept
  it, and refuse a name it doesn't know.
- **The pre-commit hook uses it.** The staged paths are listed with rename detection off, so a file moved out of a
  read path counts by both its old and its new name (design D3). Whatever runs is announced first, naming the paths
  and the file that decided, for example `guard: only openspec/** is staged; the check is skipped
  (scripts/check-paths.toml)` or `guard: only docs/** is staged; running scripts/check.py --scope docs
  (scripts/check-paths.toml)`. A scoped run streams its output and has the same timeout as the full check.
- **A malformed declaration refuses the commit** under `commit-checks`, naming the file, what's wrong and the fix. It
  isn't treated as absent (design D5).
- **The rest of the commit rules don't change.** The unstaged-changes refusal still comes first, and the branch
  match, Conventional Commits, archived tasks and delivered files apply as to any other commit.
- **CI reads the same declaration with the same function.** `guard.py check-scope` reads changed paths on stdin and
  prints `scope=none`, `scope=full` or `scope=<a>,<b>`, plus `check-args=` holding the arguments to pass to
  `check.py`, for `$GITHUB_OUTPUT`. It's shaped like `scripts/plan_needed.py`. No input means `full`, and a malformed
  declaration exits non-zero (design D6).
- **This repository declares `[skip] paths = ["openspec/**"]`**, since no gate here reads it. It needs no scope yet.
  troupe's declaration and its `check.py --scope docs` land in troupe through troupe#101's change (design D7). The
  troupe case is verified here first, on a local scratch clone of troupe.
- **Docs:** `docs/development-workflow.md` covers the declaration, scopes, the `--scope` contract and
  `check-scope`. troupe-run/troupe#101 gets a comment naming all of it.
- **Delivered to troupe**, like any guard change: CI green on all three OSes, then the owner approves the plan.

Not in this change: troupe's declaration, its `check.py --scope`, and its CI workflow (troupe#101);
`scripts/plan_needed.py`, which answers a different question (what OpenTofu reads).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: "Checks pass before a commit" lets a repository declare which paths need no check and
  which need only named parts of it. A commit runs the least the declaration allows and says what it ran, and a
  malformed declaration refuses the commit. A new requirement says CI gets the same decision from the guard.

## Impact

- `scripts/guard.py`: reading and validating `scripts/check-paths.toml` (`tomllib`, standard library); deciding a
  change's scope; running nothing, the scopes or the full check in `commit_checks`; the `check-scope` subcommand.
- `scripts/check-paths.toml`: new, skipping `openspec/**` for this repository.
- `scripts/tests/`: tests for the declaration's parsing, each outcome, the malformed refusal, renames, and
  `check-scope`.
- `docs/development-workflow.md`, `openspec/specs/development-workflow/spec.md`.
- troupe-run/troupe receives `scripts/guard.py` by delivery. The plan shows that file's delivery and nothing else.
  Until troupe holds a declaration, its commits run the full check as today.
