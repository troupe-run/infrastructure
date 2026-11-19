# Tasks

## 1. Each mutant in its own session (design D1)

- [ ] 1.1 Tests first in `test_mutation_run.py` (or the plugin's tests): with a mutant named, the hook makes the
      process a session leader; with `stats` or none, it doesn't. A real forked process that then does
      `os.killpg(0, SIGKILL)` leaves its parent alive and exits -9
- [ ] 1.2 `scripts/mutation_children.py`: `pytest_configure` calls `os.setsid()` for a mutant's test process

## 2. The run in its own session (design D2)

- [ ] 2.1 Tests first in `test_mutation_workflows.py`: both mutate steps run the mutation under `setsid --wait`,
      outside the sampler; a step script with a stand-in run that kills its own group fails the step without
      killing the step's shell
- [ ] 2.2 `mutation.yml` and `mutation-pr.yml`: prefix the run lines

## 3. Docs and verification

- [ ] 3.1 `docs/development-workflow.md`'s "Mutation testing": sessions, and why (the probe)
- [ ] 3.2 The full check passes (in a slot from the orchestrator)

## Workflow follow-up

- Read the pull request's plan: troupe's `mutation-pr.yml` and `mutation_children.py` updated, nothing else.
- After the merge and apply: dry-run troupe; report the scores, runtime, lowest free memory and crashed mutants. Then
  #339.
- Delete troupe-run/infra-probe-runner-pgkill once its `plain` job has resolved.
