# Tasks

## 1. The contained run (design D2, D3)

- [ ] 1.1 Tests first in `test_mutation_workflows.py`:
      - both workflows carry the same `# containment` block, and every run line uses `run_contained`, with no
        `setsid --wait` left;
      - the block's limits and command are as designed.
      Real tests, needing Linux, passwordless sudo, systemd-run, unshare and setpriv (CI's legs), skipped elsewhere
      saying why:
      - the contained command sees its own PID namespace (it's pid 1 or 2, and `ps` lists only its own processes);
      - it runs as the runner's uid, with a step variable and `PATH`;
      - an allocation over a small limit ends with 137, and the function says "ran out of memory";
      - a self-inflicted `kill -9 $$` says "killed by signal 9".
- [ ] 1.2 The function in both workflows; every run line through it

## 2. Docs and verification

- [ ] 2.1 `docs/development-workflow.md`'s "Mutation testing": the namespace and cgroup, the limits, the messages, and
      that local mutation runs are out
- [ ] 2.2 The full check passes (in the orchestrator's slot)

## Workflow follow-up

- Read the pull request's plan: troupe's `mutation-pr.yml` updated, nothing else.
- After the merge and apply: the troupe dry run; report scores, runtime, lowest free memory, crashed mutants, and how
  the run ended if it fails. Then #339.
- Delete troupe-run/infra-probe-runner-killall once its control job has resolved.
