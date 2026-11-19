# Design

## Context

`run_contained` (#345) ends `… setpriv … -- bash -c 'source "$1"; shift; exec "$@"' restore "$saved" "$@"`. Every
step execs, so the command (`uv` → `python mutation_run.py`) is pid 1 of the PID namespace. The kernel reparents
orphans in a namespace to its pid 1. Python never `waitpid`s a child it didn't start, so an orphaned grandchild that's
killed stays a zombie until the namespace ends. troupe's `processes.is_running` counts a zombie as running (documented
in troupe's `contributing/platform.md`), so its grandchild test waited 10 s and failed in dry run 44495333443.

## Decisions

### D1. The restoring bash stays as the namespace's init

```
bash -c 'source "$1"; shift; "$@"; exit $?' restore "$saved" "$@"
```

`"$@"` runs the command in the foreground as bash's child (pid 2). Because it isn't the last command, bash can't
optimise it into an `exec`. While bash waits for it, its SIGCHLD handling reaps any child with `waitpid(-1, …)`,
reparented orphans included. `exit $?` then returns the command's status: its exit status, or 128 + N for signal N.
When bash exits, the namespace ends (`--kill-child`) and anything left goes with it.

In the foreground, the command keeps its stdin and its signal dispositions. The review of #360 caught that an
earlier form, `"$@" & wait "$!"`, didn't: in a non-interactive bash, a backgrounded command gets `/dev/null` as stdin
and SIGINT/SIGQUIT ignored, and every process it starts inherits that. A local check confirmed it (SIGINT ignored,
stdin empty), and a CI test now holds the foreground form to the default SIGINT handler and the step's stdin.

The command is no longer pid 1. That doesn't change what it can signal, but it does change what can signal it, as the
review of #360 pointed out:
- A mutant's `kill(-1)` now reaches `mutation_run.py` too: it spares only pid 1 (bash) and the caller. Under `exec`,
  `mutation_run.py` was pid 1 and survived. But mutmut's own main process, its subprocess, never did. So under either
  form a `kill(-1)` mutant ends the unit's mutmut, the unit gets no report, and the run fails. The run used to end
  with 2 ("mutmut failed for <unit>"); it now ends with 137, and the step says "killed by signal 9". **Accepted:** the
  runner and the job are untouched either way, which is what #345 secures. Letting the run go on past such a mutant
  would take a PID namespace per mutant, beyond this change, and to raise if it shows up in practice.
- A mutant's `kill(0)` reaches only its own session (#341's per-mutant `setsid`), so it ends only that mutant, as
  before.
- A `kill(0)` from the command itself reaches the run's session, bash included. pid 1 ignores a SIGKILL from inside
  its namespace, so bash lives to report the command's 137.

*Alternative:* `tini` or `dumb-init`. Rejected because they aren't on the runner image, and installing one in every
run adds a download for what bash already does. *Alternative:* `set -m` before a background launch. Rejected because
job control in a non-interactive shell is more moving parts for what the foreground form gives directly.

## Risks / Trade-offs

- **A signal sent to pid 1 from outside** (the step being cancelled) isn't forwarded to the command → `--kill-child`
  and the scope still end everything when the step's shell goes, as before.

## Migration Plan

Merge and apply (troupe's `mutation-pr.yml`), then the troupe dry run.
