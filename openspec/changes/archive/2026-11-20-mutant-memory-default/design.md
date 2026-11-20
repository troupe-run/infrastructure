## Context

`2026-11-20-mutant-memory` (#367) built the cap with the setting null, and its design D4 set the rule for the
value: the larger measured `VmPeak` of mutmut's own process and of an ordinary mutant (one that didn't run away),
plus half, rounded up to 256 MB, recorded with the run that measured it. #371 made the measurement survive the run
being killed. Measuring dry run 44693481824 (2026-11-20), troupe, mutant 2,493 of 19,615 reached before the
runaway's OOM kill:

- mutmut's own process: `VmPeak` 1,111 MB, `VmHWM` 553 MB.
- The five largest mutant processes by `VmPeak`: `troupe.cli.render.x__changes__mutmut_28` 1,270 MB, `_29` 1,134,
  `_38`/`_71`/`_73` 1,070. All `VmHWM` 453 MB.
- 2,299 processes recorded.
- The runaway, killed by the kernel before it could record: `total-vm` 5,289 MB, `anon-rss` 4,481 MB (journal).
- Counts at the kill: 1,805 killed, 491 survived, 196 no tests, 1 timeout.

## Goals / Non-Goals

**Goals:** a cap that the runaway hits and the ordinary mutants don't, set from that measurement.

**Non-Goals:** excluding the runaway (the owner's decision, from #361's list once it's named); changing the cgroup.

## Decisions

### D1. 2,048 MB

1,270 MB, the largest of the two peaks, plus half is 1,905 MB, which rounds up to 2,048. The headroom is 778 MB
over the largest ordinary mutant, 937 MB over mutmut's own process (the size a forked mutant starts at), and the
runaway is stopped at under half its 5,289 MB. Resident worst case: two mutants at the cap plus mutmut is about
4.6 GB, well under the 12G cgroup.

### D2. The proof is a dry run, with two conditions

After the apply, the next troupe dry run must:
- (a) get past mutant ~2,410-2,493, where all three uncapped runs ended (44661743047, 44633465646 and 44693481824);
- (b) keep the killed/survived rate over its first 2,410 mutants near 44661743047's 1,734 killed and 480 survived.

If ordinary mutants die of `MemoryError` instead, survivors turn into kills and the summary's crashed list grows. In
that case `RLIMIT_AS` is too blunt, and the per-mutant cgroup (#367 D1's fallback) goes to the owner rather than the
cap being raised by guesswork.

## Risks / Trade-offs

- Peaks vary with the code under test → the measurement is recorded here, so a later run's `memory:` lines can be
  compared. A cap that trips ordinary mutants shows as (b) failing.
