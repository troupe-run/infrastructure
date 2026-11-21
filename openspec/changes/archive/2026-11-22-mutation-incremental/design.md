## Context

mutmut 3.8.1, read from its source (`__main__.py`, `mutation/file_mutation.py`, `stats.py`):
- each result is written to `mutants/<path>.meta` as its mutant finishes (`_register_mutant_result` → `save()`, a
  plain overwrite), with one `.meta` per source file holding all that file's mutants;
- on a run, a source newer than its mutated copy (always, on a fresh checkout) is regenerated, and each function's
  stored results are kept while `sha256(ast.dump(func))` (its code, without line numbers or comments) is unchanged; a
  changed or new function's mutants are reset to "not run";
- a run given no mutant names skips stored results ("let the result stand"); one given names or globs re-runs every
  match;
- `mutmut-stats.json` keeps which tests reach which function; new tests get a stats run, deleted ones are dropped, an
  edited test body is never detected; callers aren't re-tested when a callee changes; non-Python files changed since
  the last full run only warn by default (`on_dependency_change = "warn"`).

Only the `.meta` files and `mutmut-stats.json` need keeping: a missing mutated copy is regenerated and the `.meta`
merged by hash. Measured at troupe 0515e2d: about 2.4 MB for the `troupe` unit, under 1 MB for the plugins together.

## Goals / Non-Goals

**Goals:** troupe's whole baseline filled over a few runs and kept current nightly within the budget; every way the
kept state can be lost, stale or damaged named, and failing visibly where state was expected.

**Non-Goals:** `mutation-pr` (unchanged); splitting a run across jobs (the owner's earlier option, set aside).

## Decisions

### D1. One cache entry per repository per run, restored newest-first

The mutate job restores before mutating and saves after, with `actions/cache/restore` and `actions/cache/save` (the
save `if: always()`, so a run the budget or a failure stops keeps its progress). The key is
`mutmut-state-<repo>-mutmut<version>-<run id>-<attempt>`; the restore key is the prefix up to the version, so the newest
entry for that repository and mutmut version wins, and a new mutmut version can never restore old state. A dispatch
started after another finishes restores the entry that run saved, since the concurrency group runs them one at a time.

The entry holds `state/<unit>/` for each unit (its `.meta` files and `mutmut-stats.json`, at their paths under
`mutants/`) and `state/manifest.json`: the mutmut version, and per unit its source and tests (as `scripts/mutation.json`
names them), the commit and date its fill started, and the run that saved it. One entry per repository rather than per
unit, because a workflow's steps are fixed while the units vary by repository; a unit dispatch restores every unit,
runs one, and saves them all back. About 3 MB a night against the repository's shared 10 GB; a nightly run keeps the
newest entry inside the 7-day eviction window.

### D1a. Overlapping runs never drop a unit's progress they didn't make

The concurrency group runs one mutation run at a time, but the save mustn't depend on that. Suppose a nightly run and a
unit dispatch ever overlapped: the one saving later would otherwise write back, for units it didn't run, the state it
restored at its start, dropping what the other run saved in between. So before saving, the job moves its own `state/`
aside, restores the newest entry again into `state/` (`actions/cache` restores an entry only to the path it was saved
from), and copies back only the units this run ran (`mutation_run.py state-merge`, reading the run's state record).
Every other unit is the newest saved copy, byte for byte. Overlap can then cost at most the progress on a unit both runs
ran, never on a unit only one of them ran.

### D2. The run restores, validates, resumes and saves each unit

`run_mutmut` already clears `mutants/` first; it then copies `state/<unit>/` in, after checks:
- the manifest's mutmut version isn't the settings' → the whole state is discarded (the key makes this unexpected);
- the unit's source or tests differ from the settings' → that unit's state is discarded;
- a `.meta` or `mutmut-stats.json` that isn't valid JSON → only that file is left out, so mutmut regenerates it and
  re-tests that source file's mutants (or re-collects stats);
- the unit's fill is older than `full_refresh_days`, or the dispatch asks for a full refresh → discarded on purpose.

The unit then runs with no mutant names, so mutmut resumes. After it, finished or not, the unit's `.meta` files and
stats go back to `state/<unit>/`. A dispatch can name one unit (`unit` input → `--unit`); module globs aren't offered,
since they make mutmut re-run instead of resume.

### D3. The run records what it restored and saved, which is how an evicted cache shows

`mutation_run` writes `out/state-<repo>.json`, uploaded with the report artifact: per unit, whether state was restored
and from which run, how many results were carried and how many tested, any file or unit discarded and why, and that
state was saved. The previous run's artifact is already fetched for its tested commit; its state record comes with it.
When the previous record says a unit's state was saved and this run restored none for it, the state is gone (evicted
or lost): the unit starts afresh, named, and the run fails. With no previous record, or one that saved nothing for the
unit, it's a first fill, which doesn't fail.

The run writes its report either way, then exits 3 when any state was lost, didn't fit or couldn't be read, so the
mutate job fails visibly while the issues job (which runs on any outcome but cancelled) still reads the report.
Modules with a mutant not yet run aren't finished, so they're never judged, as now.

### D4. The summary says where results came from

The weekly summary (now nightly) gains a state section from `state-<repo>.json`: per unit, carried and tested counts,
the restored run, the age of the fill, and each discarded file or unit with its reason. It names the non-Python files
mutmut warns about and keeps cached results despite ("warn", as the owner chose): `mutation_state.non_python_changes`
computes them as mutmut does, `git diff --name-only` from the baseline commit in `mutmut-stats.json`, without `.py`
files and with mutmut's own exclusion list, rather than parsing mutmut's output. The next full refresh re-tests them.

### D5. The schedule, the refresh and the inputs

- Nightly: `23 3 * * *`; the schedule watch's expected age for the workflow drops to 2 days.
- `full_refresh_days` (28) in `scripts/mutation.json`, a whole number from 1 to 365, checked like the other settings.
- Dispatch inputs `unit` (one unit's name, checked against the settings) and `full-refresh` (boolean).

### D6. Seeding, by back-to-back dispatches (runbook)

The docs set out the fill: dispatch `gh workflow run mutation.yml -R troupe-run/infrastructure -f repository=troupe -f
dry-run=true`, wait for it to end, and dispatch again; each run resumes from the last. troupe's `troupe` unit needs
about
3 runs, the plugins about 1 (from the proving run's rate: about 9-10 hours for the unit, 7,877 plugin mutants). The
summary's carried and tested counts show progress, and the fill is done when every module is finished. Dry runs write no
issues while the baseline is partial; the first nightly run after the fill judges every module.

## Risks / Trade-offs

- Cache eviction under pressure from the repository's other caches → detected (D3) and named; the next runs refill.
- mutmut's warn-only non-Python change detection and its blind spots for edited tests and changed callees → named in the
  summary and cleared by the refresh (D4, D5).
- A kill mid-write truncates one `.meta` → only that file's results are re-tested (D2).
- A mutmut upgrade changes the key, so the first run after one refills from empty, which is said in the summary.
