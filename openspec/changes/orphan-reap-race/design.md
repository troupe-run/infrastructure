# Design

## Context

On Linux, a process that has gone fails a read of `/proc/<pid>/stat` in one of two ways. `open` after the reap raises
`FileNotFoundError` (`ENOENT`). A reap between `open` and `read` makes the `read` fail with `ESRCH`, which Python
raises as `ProcessLookupError`. The mutation worker, who built the contained-run side, adds that the same race can
return an empty read.

## Decisions

### D1. Gone means `FileNotFoundError`, `ProcessLookupError` or an empty read

All three say the process has left `/proc`, so the poll reports "reaped" for each. A non-empty line with no `)` is
not one of them. It means the parsing is wrong, so it raises rather than passing as "reaped"
(learned--malformed-input-is-an-error).

### D2. The read is a function the test module runs too

`STATE_OF` is a string of source that defines `state_of(pid)`. It returns the state letter, or `None` when the
process is gone. `ORPHAN` is `STATE_OF` plus the poll, so the contained run uses exactly the code under test. The new
tests `exec` `STATE_OF` into a namespace whose `open` is a stub. The function looks `open` up in that namespace before
the builtins, so the stub replaces it without patching anything global. The tests don't need the container, so they
run on macOS and Windows too.

## Risks

- The stub tests prove the poll's handling, not that the kernel raises those errors. The contained test stays as the
  end-to-end check, on CI's Linux runner.
