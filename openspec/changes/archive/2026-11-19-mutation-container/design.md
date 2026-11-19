# Design

## Context

- troupe's dry run 44469923116 lost its runner after 80 minutes in Mutate, with #341's two session layers live: no
  log, no artifacts. A mutant's own-group kill is contained, so the suspects left are a mutant that signals every
  process (`kill(-1, …)`, which crosses sessions; the runner agent runs as the same user) and memory starvation.
- The probe troupe-run/infra-probe-runner-killall (run 44480752897) tried both containments. In each, the job and its
  later step carried on:
  - `kill -9 -1` in `docker run --memory=1g --pids-limit=256`: only the container died.
  - `kill -9 -1` under `sudo systemd-run --scope -p MemoryMax=1G -p TasksMax=256 unshare --pid --fork --mount-proc
    --kill-child setpriv --reuid=runner …`, as the `runner` user: only the run died.
  - A 1 GB allocation under the same with `MemoryMax=256M`: "Killed", status 137.
  - The control, a plain `kill -9 -1`, was still "in progress" when the others had finished.
- The run needs the runner's own environment: uv's Python 3.15, the repository's `.venv`, git for blame, and the
  step's variables (`mutation_pr.py` reads `GITHUB_REPOSITORY`). It also needs the runner's non-root user, since troupe's
  tests behave differently as root.

## Decisions

### D1. Namespace and cgroup, not a container image (owner, 2026-11-19)

This replaces #345's first "Docker container" wording, with the probe as the evidence. It gives the same containment
(its own PID namespace, a memory and a task limit) without rebuilding the environment in an image: same filesystem,
same tools, same user.

### D2. One shell function, `run_contained`, in both mutate steps

It sits between `# containment: begin` and `# containment: end`, identical in both workflows, as the sampler's block
is. A test holds the two copies equal.

```
export -p > "$saved"
sudo systemd-run --scope --quiet --expand-environment=no --unit="$unit" \
    -p MemoryMax="$MUTATION_MEMORY_MAX" -p MemorySwapMax=0 -p TasksMax="$MUTATION_TASKS_MAX" \
  unshare --pid --fork --mount-proc --kill-child \
  setsid --wait \
  setpriv --reuid="$uid" --regid="$gid" --init-groups -- \
  bash -c 'source "$1"; shift; exec "$@"' restore "$saved" "$@"
```

- The step's environment is saved with `export -p` and restored inside, because the runner's sudo refuses
  `--preserve-env` and resets it. CI's first run of the real tests found `PROBE_VAR` arriving empty.
- `systemd-run --scope` runs the command in a transient cgroup with the limits: 12G of the runner's 16 GB, no swap,
  and 8192 tasks. `--expand-environment=no`, because systemd-run expands `$` in its command line, which turned a
  test's `$$` into `$`. The constants live in the function, one place for both workflows.
- `unshare --pid --fork --mount-proc --kill-child`: the run's processes see only each other, so `kill(-1)` reaches
  only them, sparing the namespace's init, as `kill(-1)` always does. They all die with the run.
- `setsid --wait`: a PID namespace doesn't separate process groups, and a `kill(0)` from inside reached the step's
  shell in CI's first run. A session of its own keeps it in.
- `setpriv` drops back to the runner's uid and gid with its groups, so everything runs as it did.
- `--unit` names the scope (`mutation-<run id>-<job>-<random>`), and only kernel log lines naming it count as its
  OOM. The generic "Memory cgroup out of memory" line also matched another scope's kill.

Every run line in both steps (`mutation_run.py`, `mutation_pr.py`, the `python3` and `uv run` forms) goes through it,
replacing #341's `setsid --wait`. #341's per-mutant `os.setsid()` stays: it keeps one mutant's own-group kill from
ending the whole run.

### D3. Saying why the run died

The function notes the time before it starts. After a non-zero exit it reads `sudo journalctl -k --since <time>` for
an OOM kill in a kernel line naming the run's scope unit (and only such lines, D2):
- if there is one: `::error::the mutation run ran out of memory (MemoryMax <limit>)`;
- otherwise, for 128+N: `::error::the mutation run was killed by signal N`, or for anything else
  `::error::the mutation run exited with status N`.

It returns the run's status unchanged, so the step fails as before.

### D3a. The containment tests can't quietly skip

The real tests need Linux with passwordless sudo, `systemd-run`, `unshare`, `setpriv` and `journalctl`, and skip
elsewhere, saying why. On GitHub Actions on Linux (CI's check leg, `GITHUB_ACTIONS=true`), a test fails if those
aren't there, so the four can't all turn into skips there unnoticed.

### D4. Local mutation runs are out

A `kill(-1)` mutant run on the owner's Mac would kill every process of their login: every session, editor and
terminal. macOS has no PID namespaces to contain it. Mutation runs happen only in CI, in the namespace above. Local
trials of the scripts use the tests, which never run a mutant.

## Risks / Trade-offs

- **`sudo` or `systemd-run` missing or refusing** on a runner image → the step fails at once, naming the command. The
  workflows run on `ubuntu-latest`, where both work (the probe).
- **12G may be too little** for a heavy run → D3 says "out of memory, MemoryMax 12G". Raising it is one constant,
  within the runner's 16 GB.

## Migration Plan

Merge and apply (troupe's `mutation-pr.yml`), then dry-run troupe, reporting scores, runtime, lowest free memory,
crashed mutants, and how the run ended if it fails. Then #339. Delete the probe repository once its control job has
resolved.
