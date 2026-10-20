# Design

## Context

See proposal.md, Why. `guard_pytest._record` is the `open` audit hook. For each open of a path inside the
repository, it adds the path to every recording window that's open (collector, fixture, test). Hypothesis's
constant collection runs inside the test's call. It's synchronous, on the test's own thread, during a draw, so it
lands in the test's window.

Hypothesis 6.168 (the version both repositories pin) opens the module's source in `constants_from_module`
(`hypothesis/internal/constants_ast.py`) with `Path(module.__file__).read_bytes()`. A stack logged from the hook in
troupe's run shows `providers._get_local_constants → constants_ast.constants_from_module → pathlib.read_bytes →
open`.

## Goals / Non-Goals

**Goals:**
- A read that Hypothesis makes for itself never counts against a test.
- Any read the test makes still counts, including from inside a `@given` body, a strategy or a fixture.
- The guard stays standard-library only, and costs nothing for reads outside the repository.

**Non-Goals:**
- Other libraries that read source for themselves, such as `linecache` when a traceback is formatted. None has been
  seen to cause a false report. Each would be a named addition to the same rule if one turns up.

## Decisions

### D1: Recognise the read by the frame that made it

When an open inside the repository is about to be recorded, `_record` walks the stack from its caller
(`sys._getframe(1)` and `f_back`). It skips the read if any frame's `co_filename` ends with
`hypothesis/internal/constants_ast.py`, with `\` normalised to `/` for Windows. That file name is one named constant
in `guard_pytest.py`, with a comment pointing to this change. The walk runs only for in-repository paths while
recording, which is after the cheap checks that already return early.

*Alternatives:*
- **Prime Hypothesis's cache before each test**, outside the recording window. That would call Hypothesis's private
  `_get_local_constants`. The guard would import Hypothesis, which breaks the standard-library rule, and would depend
  on a private function.
- **Turn the constants off for the suite.** That changes how every repository's Hypothesis tests generate values. It
  isn't the guard's place to decide that.
- **Match any frame under `hypothesis/`.** That's too wide: a `@given` test's own body runs below Hypothesis's
  frames, so its reads would be skipped too. That's exactly what the second new scenario rules out.

### D2: If Hypothesis moves the code

If a later Hypothesis reads module source from another file, the old false report comes back loudly. It fails a
test, naming a file the test never read, so nothing goes silently wrong. The reproduction test pins the installed
Hypothesis's behaviour: it fails if the skipped file name stops matching, because then the false report returns.

## Risks / Trade-offs

- [A stack walk on every in-repository open while recording] → It's a handful of frames, compared with the cost of
  the open itself. Measure the guard test suite's time before and after (task 2.3).
- [A test that calls into `constants_ast` itself, to test Hypothesis] → Its reads would be skipped. No governed
  repository does this, and it would be Hypothesis's own read anyway.
