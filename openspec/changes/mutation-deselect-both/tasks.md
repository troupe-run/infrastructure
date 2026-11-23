# Tasks

## 1. Both ids for each deselect

- [ ] 1.1 The new ids, from #507's worker (the orchestrator sends them): each of the three tests' node id after the move
- [ ] 1.2 Test first in `test_mutation_settings.py`: troupe's declared deselects name each of the three tests by both
      its id before #507 and after it, with the same reason
- [ ] 1.3 `scripts/mutation.json` gains the three new ids beside the old
- [ ] 1.4 The full check passes (in the orchestrator's slot)

Applied before troupe#507 merges; #394 removes the old ids after it.
