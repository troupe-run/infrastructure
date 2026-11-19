# Tasks

## 1. A reaping init (design D1)

- [ ] 1.1 Tests first in `test_mutation_workflows.py`. These are real tests, run on CI's Linux leg and skipped
      elsewhere like the others:
      - a Python command starts a child that starts a grandchild and exits, so the grandchild is reparented. The
        command kills the grandchild, which must be gone from `/proc` within 5 s, not a zombie. Show it fails on the
        current block;
      - a command exiting 3 gives the step 3, and one killed by SIGKILL gives 137 (the existing signal test keeps its
        child kill).
      Locally: a stub run shows the new line keeps the statuses.
- [ ] 1.2 The restore line in both workflows' `# containment` block: `"$@" & wait "$!"` in place of `exec "$@"`

## 2. Verification

- [ ] 2.1 The full check passes (in the orchestrator's slot); on CI the new tests run (the no-skip guard holds)

## Workflow follow-up

- Read the pull request's plan: troupe's `mutation-pr.yml` updated, nothing else.
- After the merge and apply: the troupe dry run; report scores, runtime, readings, crashed mutants, and how it ended
  if it fails. Then #339.
