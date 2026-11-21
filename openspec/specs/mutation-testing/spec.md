# mutation-testing Specification

## Purpose
Mutation testing of the repositories one list in infrastructure names for coverage and mutation testing (troupe, since
#332), which reports and never blocks a merge. A weekly run keeps one
`test-quality` issue on the roadmap board for each module whose score is under the threshold or below its recorded
baseline, which only moves up, and names the pull request that added each new surviving mutant. On each ready pull
request, a report mutates the changed code and comments with the survivors on its changed lines and the run's time.
Every number they judge by is declared in one settings file.

## Requirements

### Requirement: Mutation testing runs weekly from infrastructure
A workflow in troupe-run/infrastructure SHALL run mutation testing weekly, and on demand, over each repository the list
names (the requirement on naming them in one place), each at its `main`, on Linux with Python 3.15. This weekly workflow SHALL NOT run on pull requests or merge groups. No
mutation testing SHALL be a required check, so none blocks a merge. The weekly workflow SHALL be one of the scheduled
workflows the schedule watch declares.

#### Scenario: The weekly run
- **WHEN** the weekly schedule fires and the list names only troupe
- **THEN** the workflow mutates and tests troupe at its `main`, and no other repository

#### Scenario: A pull request
- **WHEN** a pull request is opened, or enters the merge queue, in any repository
- **THEN** the weekly workflow doesn't run, and no required check waits for any mutation testing (a listed repository's
  ready pull request gets the report of its own changes instead)

#### Scenario: One repository on demand
- **WHEN** the owner dispatches the workflow naming one listed repository
- **THEN** only that repository is mutated, and its modules' issues are kept as on a weekly run

#### Scenario: A repository the list doesn't name, on demand
- **WHEN** the owner dispatches the workflow naming website, which the list doesn't name
- **THEN** the run fails before mutating anything, naming website and the repositories the list names

### Requirement: The jobs that run tests hold no secret
A job that runs a repository's code or tests under mutation SHALL have a read-only token and no environment, and
SHALL hand on only a report. The job that writes issues SHALL run no repository's tests, SHALL read each report as data
against a closed schema, and SHALL treat a missing or malformed report as an error naming the repository.

#### Scenario: A malformed report
- **WHEN** a repository's report has a field the schema doesn't name, or lacks one it requires
- **THEN** that repository's issues are left alone, the others are handled, and the run fails naming the repository and
  the field

#### Scenario: A repository's job failed
- **WHEN** the job for one repository fails or times out before writing its report
- **THEN** the other repositories' issues are handled, that repository's are left alone, and the run fails naming it

### Requirement: Mutation testing's settings are declared once
The score threshold, the ratchet's tolerance, the time budgets, how many mutants run at once, the fewest mutants a
module needs to be judged, the most new issues one run may open per repository, the tool versions, and what each
repository mutates and tests SHALL be declared in one file in infrastructure. Every job SHALL read them from there. An
unknown or malformed setting SHALL fail the check.

#### Scenario: The threshold moves
- **WHEN** a pull request changes the threshold in the settings file
- **THEN** the next run judges every module by the new threshold, and nothing else needs to change

#### Scenario: A misspelt setting
- **WHEN** the settings file has a key it doesn't declare, or a threshold outside 0 to 100
- **THEN** `scripts/check.py` fails, naming the file, the key and what's valid

#### Scenario: The job timeout follows the budget
- **WHEN** the budget changes and the workflow's job timeout doesn't
- **THEN** this repository's tests fail, naming both

#### Scenario: Fewer mutants at once
- **WHEN** the settings say 2 mutants run at once
- **THEN** the weekly run and the pull request report each run mutmut with at most 2 children

### Requirement: A module's score counts untested code against it
A module's mutation score SHALL be the mutants caught (killed, timed out or crashed) as a percentage of the mutants
caught, survived or not covered by any test. Skipped mutants SHALL NOT count. A module SHALL be judged only when it has
at least the declared fewest mutants and the run finished all of its mutants within the budget.

#### Scenario: A module with an untested function
- **WHEN** a module has 20 mutants, of which 10 are killed, 4 survive and 6 are in a function no test calls
- **THEN** its score is 50%

#### Scenario: A small module
- **WHEN** a module has fewer mutants than the declared floor
- **THEN** it's listed in the run's summary as not judged, and no issue is opened, updated or closed for it

#### Scenario: The budget runs out
- **WHEN** a repository's budget runs out before all of a module's mutants have run
- **THEN** that module is listed in the summary as not finished and isn't judged, and the modules that finished are
  judged as usual

### Requirement: Each module under the threshold or its baseline has exactly one issue
For each module judged under the threshold or below its baseline, the run SHALL keep exactly one open issue in the
module's repository,
labelled `test-quality`. The run SHALL recognise its own issue by a marker naming the repository and module, in an
issue its credential opened, and SHALL never open a second one for the same module.

#### Scenario: A module falls under the threshold
- **WHEN** a module scores under the threshold and has no issue from the run
- **THEN** an issue is opened in its repository, labelled `test-quality`, listing its surviving mutants

#### Scenario: A module stays under the threshold
- **WHEN** a module with an open issue scores under the threshold again
- **THEN** that issue's description is rewritten with this run's numbers and survivors, no other issue is opened, and
  a comment is added only if the score or the number of survivors changed

#### Scenario: A module recovers
- **WHEN** a module with an open issue scores at or over both the threshold and its baseline
- **THEN** the issue gets a comment with the new score and is closed as completed

#### Scenario: A module falls again after its issue closed
- **WHEN** a module whose issue was closed falls under the threshold or its baseline again
- **THEN** a new issue is opened; the closed one stays closed

#### Scenario: A person's issue quotes the marker
- **WHEN** an issue opened by a person contains a module's marker
- **THEN** the run doesn't edit or close it, and keeps its own issue for the module

#### Scenario: Two runs at once
- **WHEN** a dispatched run starts while another is in progress
- **THEN** it waits for the other to finish, so neither opens an issue the other opened

### Requirement: A module's issue lists its surviving mutants
A module's issue SHALL name the module, its score, the threshold, its mutant counts and the run. It SHALL list the
surviving mutants, each with its location and change: the first 30, then how many more and how to list them all.

#### Scenario: A module with 45 survivors
- **WHEN** a module under the threshold has 45 surviving mutants
- **THEN** its issue lists 30 of them with location and change, says 15 more survive, and names the command or report
  that lists them all

### Requirement: A run opens a bounded number of new issues
A run SHALL open at most the declared number of issues per repository. Modules beyond that SHALL be named
in the run's summary and handled by a later run. Open issues SHALL always be updated or closed.

#### Scenario: More modules than the cap
- **WHEN** eight modules in troupe fall under the threshold and the cap is 5, with none having an issue
- **THEN** five issues are opened, the summary names the other three, and the next run opens issues for those still
  under

### Requirement: New issues go on the roadmap board
Every issue the run opens SHALL be added to the troupe roadmap board, by the board's own credential, in a
job that only adds issues whose URL is an issue in troupe, infrastructure or website.

#### Scenario: A new issue
- **WHEN** the run opens an issue
- **THEN** it's on the troupe roadmap board when the run finishes

#### Scenario: An unexpected URL
- **WHEN** the board job is handed something that isn't an issue URL in one of the three repositories
- **THEN** it adds nothing and fails, naming what it was handed

### Requirement: A dry run only reports
A run dispatched as a dry run, and any run outside GitHub Actions, SHALL write no issue, comment or board item. It
SHALL report every module's score and what it would open, update, reopen or close.

#### Scenario: The calibration run
- **WHEN** the owner dispatches the workflow as a dry run
- **THEN** the run's summary lists each module's score and the issues it would open, and no issue changes

### Requirement: A module's baseline only moves up
Each repository's committed quality-gates file SHALL hold, in its mutation table, each judged module's baseline score.
A module SHALL count as having fallen when its score is below its baseline by more than the declared tolerance. A run
SHALL report every baseline it would raise, to max(baseline, score), in its summary and the module's issue, and SHALL
NOT write or lower one: a baseline changes only through an ordinary pull request.

#### Scenario: A module falls below its baseline
- **WHEN** a module with a 72.0% baseline scores 70.5%, above the 60% threshold, with a tolerance of 0
- **THEN** its issue is opened or updated, saying it fell below its 72.0% baseline

#### Scenario: A module improves
- **WHEN** a module with a 72.0% baseline scores 75.0%
- **THEN** the run reports the baseline it would raise to 75.0%, and no issue is opened

#### Scenario: A module with no baseline
- **WHEN** a module with no recorded baseline is judged at 64.0%
- **THEN** no issue is opened, and the run reports 64.0% as the baseline to record

### Requirement: A malformed mutation table is an error
A malformed mutation table SHALL fail the run for that repository, naming the file and the key, and SHALL NOT be read
as having no baselines.

#### Scenario: A malformed baseline
- **WHEN** a repository's mutation table gives a module a score of "high"
- **THEN** that repository's issues are left alone, and the run fails naming the file, the module and the key

### Requirement: New survivors are attributed to the pull request that added them
The weekly run SHALL call a surviving mutant new when the line it mutates was last changed by a commit that isn't in the
previous weekly run's tested commit for that repository. The module's issue SHALL list new survivors first, each naming
the commit and the merged pull request that contains it, so GitHub cross-references the issue on that pull request.
With no previous run to compare with, no survivor SHALL be called new.

#### Scenario: A pull request adds an untested branch
- **WHEN** a pull request merged since the last weekly run adds a line whose mutant survives
- **THEN** the module's issue lists that survivor under new survivors, naming the pull request, and the pull request's
  timeline shows the issue mentioning it

#### Scenario: An old survivor
- **WHEN** a survivor's line was last changed before the previous weekly run's tested commit
- **THEN** it's listed with the other survivors, with no pull request named

#### Scenario: The first run
- **WHEN** no previous weekly run's report is available
- **THEN** no survivor is called new

### Requirement: Each ready pull request's changed code is mutation tested, as a report
On every pull request that's ready for review in each repository the list names that receives the guard's files, a
workflow delivered from infrastructure SHALL mutate the code the pull request changed and report the surviving mutants on changed lines, in one
comment on the pull request, edited in place on later pushes, and in the run's summary, with its runtime. It SHALL NOT
be a required check, and SHALL conclude success when it finds survivors. Only its own failure to run SHALL fail it.

#### Scenario: A repository the list doesn't name
- **WHEN** a ready pull request in infrastructure, which holds the report's workflow as its source but isn't on the
  list, is tested
- **THEN** the report mutates nothing and runs no tests, says the repository isn't on the list, and doesn't fail

#### Scenario: A branch made before a delivery
- **WHEN** a ready pull request's branch was made before infrastructure delivered the report's scripts to its
  repository
- **THEN** the report runs on the pull request's merge with its base, which has them, and mutates only the lines the
  pull request changed

#### Scenario: A pull request leaves a changed line untested
- **WHEN** a ready pull request changes a function, and a mutant on a changed line survives
- **THEN** the pull request's mutation comment lists it with its location and change, the job succeeds, and the merge
  isn't held

#### Scenario: An exempted line
- **WHEN** a changed line carries the tool's exemption with a reason
- **THEN** no mutant on it is reported

#### Scenario: Unchanged code isn't reported
- **WHEN** a mutant survives on a line the pull request didn't change
- **THEN** it isn't in the comment

#### Scenario: Another push
- **WHEN** the pull request is pushed to again
- **THEN** the same comment is edited with the new result, and no second comment appears

#### Scenario: A draft
- **WHEN** a draft pull request is opened or pushed to
- **THEN** no mutation runs

#### Scenario: No source changed
- **WHEN** a ready pull request changes no file the repository's targets mutate
- **THEN** nothing is mutated, and the comment, if one exists, says so

#### Scenario: The runtime is recorded
- **WHEN** the run finishes, or stops at its budget
- **THEN** its comment and its report give the time of each step and of the whole job

### Requirement: The job that runs a pull request's code holds no write token
In the pull request workflow, the job that runs the pull request's code under mutation SHALL have a read-only token,
and SHALL hand on only a report. The job that comments SHALL check out only the pull request's base commit, never its
head, and SHALL read the report as data against a closed schema.

#### Scenario: A malformed pull request report
- **WHEN** the comment job reads a report with a field the schema doesn't name
- **THEN** it writes no comment and fails, naming the field

### Requirement: The repositories that get coverage and mutation testing are named in one place
One list in troupe-run/infrastructure SHALL name the repositories that get coverage and mutation testing: the weekly
mutation run, the pull request mutation report, and a coverage gate. The weekly run's jobs, and which repositories
receive the pull request report, SHALL follow it and nothing else. Infrastructure's own check SHALL measure coverage
only when the list names infrastructure. Adding a repository SHALL take one pull request to the list.

#### Scenario: The list today
- **WHEN** the list names only troupe
- **THEN** the weekly run mutates troupe alone, only troupe receives the pull request report, and infrastructure's own
  check measures no coverage

#### Scenario: A repository is taken off the list
- **WHEN** a pull request removes website from the list, and website held the delivered pull request report
- **THEN** the plan deletes the report's workflow and scripts from website, and website's delivered file list no
  longer names them

#### Scenario: Infrastructure's coverage follows the list
- **WHEN** infrastructure's `quality-gates.toml` declares `[coverage]` while the list doesn't name infrastructure
- **THEN** this repository's tests fail, naming the table and the list

### Requirement: A repository's mutation run finds the files its tests read
A mutation run SHALL let a repository's tests find the files they read beside their source, wherever the tool's copy
puts them, and SHALL keep the repository's own pytest options apart from those that can't work in the copy. A test that
can't run under the tool at all SHALL be deselected in the settings, with its reason.

#### Scenario: troupe's tests find the repository's files
- **WHEN** troupe's `troupe` package is mutated and a test reads `plugins/runner-anthropic/fixtures`, counting
  directories up from its own file
- **THEN** it finds the directory, as it does outside the run

#### Scenario: troupe's own pytest plugins load
- **WHEN** troupe's package is mutated
- **THEN** its tests run with the plugins troupe's pytest options load, without `--strict-markers` and the guard's tag
  plugin, which can't find their declarations from the copy

#### Scenario: A package's tests find a sibling package
- **WHEN** `troupe-store-text` is mutated and a test points a child process at `packages/troupe/tests`, counting two
  directories up from its own file
- **THEN** the child finds troupe's tests, as it does outside the run

### Requirement: A mutation run records the resources it uses
While a weekly or pull request mutation run mutates, its job SHALL record the runner's memory, swap, disk and load at
least once a minute, both in the job's log and in a file uploaded with the run's report, so a run whose runner is lost
still leaves what it last recorded.

#### Scenario: The runner is lost
- **WHEN** the runner stops responding while mutmut runs
- **THEN** the job's log, as far as it was kept, shows the readings up to then, each with its time

#### Scenario: The run finishes
- **WHEN** a run finishes
- **THEN** its uploaded report includes the readings file, and the run's summary gives the lowest free memory seen

### Requirement: A package's unit has its package's own files
When a unit's source is a package's `src`, its mutation run SHALL copy the package directory's other top-level entries
into mutmut's copy, as a unit at the repository's root copies the checkout's, so a test that finds them from its own
file finds them there too.

#### Scenario: A plugin's tools
- **WHEN** a test in `plugins/runner-anthropic/tests` reads `tools/capture_anthropic.py` from its package, counting
  one directory up from its own file
- **THEN** it finds the file inside mutmut's copy, as it does outside the run

### Requirement: A mutant can't stop the runner or the rest of the run
A mutation run SHALL run in a PID namespace and a cgroup of its own, as the runner's user and with the step's
environment, under a memory and a task limit; and each mutant's tests SHALL run in a session of their own. A mutant
that signals its own group ends only its tests, and is counted as crashed; one that signals every process, or runs the
runner out of memory, ends at most the run.

#### Scenario: A mutant kills its own process group
- **WHEN** a mutant makes the code under test send SIGKILL to its own process group
- **THEN** only that mutant's test process dies, the mutant is counted as crashed, and the run, the job and its log
  carry on

#### Scenario: The run itself dies
- **WHEN** the whole mutation run is killed
- **THEN** the step fails with the run's exit status, and the job still uploads its readings and keeps its log

#### Scenario: A mutant signals every process
- **WHEN** a mutant makes the code under test send SIGKILL to every process it may (`kill(-1, …)`)
- **THEN** only processes inside the run's namespace die (the run's first process, its init, is spared), no process
  outside it does, the step reports how the run ended, and the job and its log carry on

#### Scenario: The run runs out of memory
- **WHEN** the run's processes use more memory than its limit
- **THEN** the kernel ends the run, the step fails saying it ran out of memory and naming the limit, and the job and
  its log carry on

### Requirement: The contained run reaps its orphans
The mutation run's PID namespace SHALL have an init that reaps every process reparented to it, so a process the run's
code kills doesn't stay a zombie, and the run's exit status, whether a plain status or a signal, SHALL reach the step
unchanged.

#### Scenario: A killed grandchild
- **WHEN** code under test starts a child, which starts a grandchild and exits, and then kills the grandchild
- **THEN** the grandchild is reaped within moments, as it is outside the namespace, so a test that waits for it to be
  gone passes

#### Scenario: The run's status passes through
- **WHEN** the run exits with status 3, or is killed by SIGKILL
- **THEN** the step sees status 3, or 137, as before

### Requirement: A run's report names its crashed mutants
A mutation run's report SHALL record each crashed mutant as it records a survivor: its name, path, line and change,
and the tool's exit code where it gives one. The weekly run's summary SHALL list them with what each ended, so the
owner can decide on exclusions from them. No mutant SHALL be excluded without the owner.

#### Scenario: A mutant crashes its tests
- **WHEN** a mutant's tests die by a signal and mutmut records the mutant as crashed
- **THEN** the report lists it with its name, path, line, change and exit code, and the summary lists it as having
  ended only its own test process

#### Scenario: A crash that ends the run
- **WHEN** a mutant ends the unit's mutmut itself
- **THEN** the report has no entry for it, and the step says the run was killed or exited, as it does for any run
  that ends early

#### Scenario: A malformed list
- **WHEN** a report's module counts 2 crashed and lists 1 crashed mutant
- **THEN** reading the report fails, naming the module and both numbers

### Requirement: A run keeps the host's account of how it ended
When a mutate step ends, it SHALL save the journal lines since the step began from the sources that can name who ended
the run (the kernel's OOM lines, systemd-oomd, and systemd's lines on the runner's service or the run's own scope), and
no other units' lines, to the job's log and to a `journal-<repository>.log` uploaded with the readings, and SHALL save
nothing when there are none or the journal can't be read.

#### Scenario: The host ends the step
- **WHEN** something on the host sends the step SIGTERM, as in dry run 44633465646
- **THEN** the uploaded journal file and the log name it, if the kernel or systemd recorded it

#### Scenario: No journal
- **WHEN** the journal can't be read, or holds none of those lines
- **THEN** no journal file is written, and the step ends as it would have

### Requirement: A runaway mutant ends only its own tests
When the settings give a per-mutant memory cap, each process that tests a mutant SHALL run under it, so a mutant whose
tests allocate past it ends only those tests, and the run records it and goes on. The passes with no mutant SHALL run
without it. A cap that isn't null or a whole number in range SHALL be refused, naming the setting. The cap SHALL be
set from a recorded run's measured peaks, never by arithmetic on the cgroup's limit.

#### Scenario: A mutant allocates without bound
- **WHEN** a mutant makes its tests allocate memory past the cap
- **THEN** only that mutant's test process fails, the mutant is counted as killed or crashed (and named if crashed),
  and the run carries on to the next mutant

#### Scenario: The passes with no mutant
- **WHEN** mutmut runs its stats and clean passes
- **THEN** they run without the cap, as before

#### Scenario: No cap
- **WHEN** the setting is null
- **THEN** no mutant's process is capped, and the run behaves as before

#### Scenario: A malformed cap
- **WHEN** the setting is a string, a fraction, or out of range
- **THEN** reading the settings fails, naming the setting, its value and the range

#### Scenario: The cap troupe runs under
- **WHEN** troupe's weekly run reads the settings
- **THEN** each mutant's process is capped at 2,048 MB, set from dry run 44693481824's peaks (mutmut's own 1,111 MB
  and the largest ordinary mutant's 1,270 MB of virtual size, plus half, rounded up to 256 MB)

### Requirement: A run records the memory its passes peak at
For each unit, a run SHALL log the peak virtual size and peak resident size of mutmut's own process, where its stats
and clean passes run, and of the largest of its mutants' test processes, so a cap can be set from measured peaks. In
CI the peaks SHALL be kept in a file the job uploads, and the summary printed from outside the contained run, so a
run its cgroup kills still logs it.

#### Scenario: A unit's run ends
- **WHEN** a unit's mutmut run ends, whether or not it finished
- **THEN** the log has a `memory:` line for mutmut's own process and for the largest mutant processes, each with
  its peak virtual and resident size, and the mutant's name where there is one

#### Scenario: Nothing was recorded
- **WHEN** no process recorded its peaks (as off Linux, with no /proc)
- **THEN** the run logs that no peaks were recorded and carries on

#### Scenario: The run is killed
- **WHEN** the contained run is killed, as by its cgroup's OOM killer, after some of its processes recorded peaks
- **THEN** the step still logs the `memory:` lines for each unit reached, and the job uploads the peaks file

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
