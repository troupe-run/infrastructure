## ADDED Requirements

### Requirement: A unit whose selected tests reach none of its code is judged, not a failed run
When mutmut stops because a unit's selected tests reach none of its mutants, recognised by mutmut's own message and
exit code exactly, the run SHALL count each of that unit's mutants as reached by no test, judge its modules, name the
unit and the reason in the summary, and carry on to the next unit. Any other mutmut failure SHALL still fail the run.

#### Scenario: troupe-vcs-git's unit tests reach none of its code
- **WHEN** mutmut stops for `troupe-vcs-git` with its "could not find any test case for any mutant" message
- **THEN** each of its modules is finished with every mutant reached by no test, the summary names the unit and why,
  and the run goes on to the next unit

#### Scenario: Another failure
- **WHEN** mutmut exits 1 without that message, or prints it with another exit code
- **THEN** the run fails, naming the unit, as before
