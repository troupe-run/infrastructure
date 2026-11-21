## ADDED Requirements

### Requirement: A mutant is placed on the line mutmut changed
A run SHALL place each survivor and crashed mutant on the source line its mutation changes, counting from where
mutmut's own diff starts the function, so comments directly above a function don't shift it.

#### Scenario: A function with a comment above it
- **WHEN** a survivor is in a function with a comment directly above its `def`, as `run_flush` in troupe's
  `cli/config.py` (`# flush` at 205, the `def` at 208, the mutated print at 221)
- **THEN** the report places it on line 221

#### Scenario: Every mutant in a package
- **WHEN** real mutmut 3.8.1 generates the mutants of every troupe source file at 0515e2d
- **THEN** each is placed where its diff's old lines match the file's lines

### Requirement: A survivor that can't be attributed is named, and the report stands
When the commit that last changed a survivor's line can't be found, the run SHALL report that survivor with no commit
and not new, log why, and write the report. The weekly summary SHALL name each such survivor as unattributed.

#### Scenario: A blame fails
- **WHEN** `git blame` fails for one survivor's line
- **THEN** the report is written with every module's results, that survivor has no commit, and the summary names it
  as unattributed

#### Scenario: Every blame succeeds
- **WHEN** every survivor's line can be blamed
- **THEN** the summary has no unattributed section
