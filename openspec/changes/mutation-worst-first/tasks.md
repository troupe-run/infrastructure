# Tasks

## 1. Worst first

- [x] 1.1 Test first (`test_mutation_issues.py`): eight modules under the threshold with no issue and scores out of
      name order. The five lowest get issues, the 30% tie at the cap goes to the first by name, and the rest are
      deferred. It failed on name order.
- [x] 1.2 `plan_repository` judges every module first, then chooses the new issues lowest score first, ties by name.
      Updates and closes are unchanged.
- [x] 1.3 The full check passes (in the commit hook, in the orchestrator's slot, 2026-11-26).
