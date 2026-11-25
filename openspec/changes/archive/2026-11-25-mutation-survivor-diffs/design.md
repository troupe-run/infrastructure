# Design

## Context

mutmut 3.8.1's `show` is `find_mutant(name)` (load every `.meta` file until one holds the name), then
`get_diff_for_mutant(name, path=...)` (the original and mutant functions from the mutated module, rendered with libcst,
then `difflib.unified_diff`), printed after a `# <name>: <status>` header. `mutation_run.py` runs under the repository's
venv for troupe, but under the system `python3` for the workflow's other steps, so it can't always import mutmut.

## Decisions

### D1: mutmut's own functions, in mutmut's own interpreter

`mutation_show.py` runs as `<the python beside mutmut> mutation_show.py`, in mutmut's working directory. It reads
`{path: [names]}` on stdin and writes `{name: what mutmut show prints}`. For each file it loads mutmut's
`SourceFileMutationData`. For each name it builds the header from `status_by_exit_code` and the diff from
`get_diff_for_mutant(name, path=path)`, the same call `show` makes. So the text is mutmut's by construction. Only the
process start and `find_mutant`'s walk are no longer repeated per mutant.

*Alternative:* re-implement the rendering with `ast` and the source text, so infrastructure's tests could run it
without mutmut. That would be equal only by testing, and libcst's leading-comment rules (#377) show how easy it is to
get wrong.

### D2: The plumbing tested in CI, the equality proved in a container

infrastructure doesn't install mutmut. Its import chain is POSIX-only (`resource`, `fcntl`), and it brings libcst,
textual and more. So the split is:

- **CI tests the plumbing with a faked render:**
  - one render per unit;
  - by the interpreter beside `mutmut`;
  - the request's shape;
  - the errors;
  - `to_show`'s rules;
  - the report's survivors read by `show-equal`.
- **`show-equal` proves the equality** against real `mutmut show`, over every survivor of a real run.
  - Its results come from a CI run's report, marked into the `.meta` files that mutmut's text-only generation writes.
  - So no mutant runs, and nothing is produced locally.
  - Its result goes on #404 and the PR, and its docstring puts it on the mutmut-upgrade checklist.

## Risks / Trade-offs

- **[A future mutmut changes `show`]** → `show-equal` is on the upgrade checklist. A rendered map that leaves a mutant
  out fails the run rather than reporting a blank diff.
- **[A mutmut interpreter that isn't beside `mutmut`]** → the render fails naming the path. In the workflow, `mutmut`
  is installed into the repository's venv with `uv pip install`, so its `python` is beside it.
