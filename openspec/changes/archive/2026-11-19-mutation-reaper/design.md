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
bash -c 'source "$1"; shift; "$@" & wait "$!"' restore "$saved" "$@"
```

`"$@" &` runs the command as bash's child, pid 2, and `wait "$!"` waits for it and returns its status: its exit
status, or 128 + N for signal N. While waiting, bash handles SIGCHLD by reaping with `waitpid(-1, …)`, which collects
any child, the reparented orphans included. When the command ends, bash exits with its status. The namespace then
ends (`--kill-child`), and anything left in it goes with it.

The command is no longer pid 1, which doesn't change what it can signal:
- a `kill(-1)` now spares bash (pid 1) and the caller, and still reaches nothing outside;
- a `kill(0)` reaches the run's session, bash included, but pid 1 ignores a SIGKILL from inside its namespace, so bash
  lives to report the command's 137.

*Alternative:* `tini` or `dumb-init`. Rejected because they aren't on the runner image, and installing one in every
run adds a download for what bash already does.

## Risks / Trade-offs

- **A signal sent to pid 1 from outside** (the step being cancelled) isn't forwarded to the command → `--kill-child`
  and the scope still end everything when the step's shell goes, as before.

## Migration Plan

Merge and apply (troupe's `mutation-pr.yml`), then the troupe dry run.
