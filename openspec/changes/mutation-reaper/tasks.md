# Tasks

## 1. A reaping init (design D1)

- [x] 1.1 Tests first in `test_mutation_workflows.py`. These are real tests, run on CI's Linux leg and skipped
      elsewhere like the others:
      - a Python command starts a child that starts a grandchild and exits, so the grandchild is reparented. The
        command kills the grandchild, which must be gone from `/proc` within 5 s, not a zombie. Committed before
        the fix, it failed on CI's Linux leg against `exec "$@"` with "left as Z" (run 44530491024), and the SIGKILL
        status case failed too (0, not 137: the killed sh was pid 1, which ignores it);
      - a command exiting 3 gives the step 3, and one killed by SIGKILL gives 137 (the existing signal test keeps its
        child kill).
      Locally: a stub run shows the new line keeps the statuses.
- [x] 1.2 The restore line in both workflows' `# containment` block: `"$@" & wait "$!"` in place of `exec "$@"`

## 2. Verification

- [x] 2.1 The full check passes (in the commit hook, in the orchestrator's slot, 2026-11-19); on CI the new tests run (the no-skip guard holds)

## Workflow follow-up

- Read the pull request's plan: troupe's `mutation-pr.yml` updated, nothing else.
- After the merge and apply: the troupe dry run; report scores, runtime, readings, crashed mutants, and how it ended
  if it fails. Then #339.
