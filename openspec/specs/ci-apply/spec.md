# ci-apply Specification

## Purpose

How a declared change reaches the org from CI: the plan on every pull request, and the plan, approval and apply on
`main`. Covers the environments that gate them, and the commit of the new state after an apply.

## Requirements

### Requirement: Every pull request is planned in CI
A pull request into `main` SHALL get a plan made in CI, against the state on `main`, posted on the pull request,
once the owner has approved that run. The plan is the pull request's evidence. When the pull request is updated, the posted plan SHALL be replaced rather
than added to. A pull request from a fork SHALL NOT be planned, because it gets no secrets. A pull request that
changes only files OpenTofu never reads SHALL NOT be planned, and SHALL NOT ask the owner for an approval.

#### Scenario: A pull request that changes the org shows its plan
- **WHEN** a pull request changes what is declared
- **THEN** a plan showing that change is posted on the pull request once the owner approves the run, without the
  owner running anything locally

#### Scenario: A new push replaces the plan
- **WHEN** a pull request that already has a posted plan is pushed to again
- **THEN** the pull request shows one plan: the latest

#### Scenario: A pull request that changes only documentation isn't planned
- **WHEN** a pull request changes only files OpenTofu never reads, such as OpenSpec artifacts or `docs/`
- **THEN** its plan job is skipped, no approval is requested, and the skipped job counts as passed

#### Scenario: A change to a delivered file is planned
- **WHEN** a pull request changes only a file this repository delivers elsewhere, such as `scripts/guard.py`
- **THEN** it is planned like any other, and its plan shows the delivery

### Requirement: A pull request's run holds no credential without the owner's approval
A workflow run for a pull request SHALL NOT get any credential (the App's key, the state passphrase or the DNS host's
API token) until the owner has approved that run. A run that isn't approved SHALL NOT plan. A pull request's run
SHALL NOT be able to reach the credential for planning `main`, which needs no approval.

#### Scenario: An unapproved pull request run gets nothing
- **WHEN** a pull request is pushed and the owner hasn't approved its plan run
- **THEN** the run waits, and no step in it has received a secret

#### Scenario: A pull request can't borrow main's plan credential
- **WHEN** a pull request's run asks for the environment that plans `main`
- **THEN** GitHub refuses the deployment

### Requirement: Main is applied only after the owner approves its plan
After every push to `main`, CI SHALL plan and show the plan before asking for approval. It SHALL then wait for the
owner's approval, and apply exactly the saved plan the owner saw. A plan with no changes SHALL end the run without
asking for approval. Only the owner SHALL be able to approve. Rejecting it, or not approving it, SHALL leave the org
unchanged.

#### Scenario: An approved plan is applied
- **WHEN** a merge to `main` changes what is declared and the owner approves the plan shown in the run
- **THEN** that saved plan, and nothing else, is applied

#### Scenario: A rejected plan changes nothing
- **WHEN** the owner rejects the approval
- **THEN** nothing is applied, and the change stays pending until a later run is approved

#### Scenario: Nothing to apply asks nothing
- **WHEN** a push to `main` leaves the declaration and the org in agreement
- **THEN** the run ends after the plan, with no approval requested

### Requirement: Only main can apply
An apply SHALL run only on `main`, after the owner's approval. The credential that can change the org SHALL reach a
workflow run only when the run is on `main` or the owner has approved it. A run on any other branch SHALL NOT reach
the environments that `main` uses.

#### Scenario: A branch can't apply
- **WHEN** a workflow run on a branch other than `main` asks for the apply environment
- **THEN** GitHub refuses the deployment, and the run gets no secret from that environment

#### Scenario: Removing or weakening main's environments fails the check
- **WHEN** a change deletes the declaration of the environment that plans `main` or the apply environment, lets
  either deploy from a branch other than `main`, lets admins bypass either, or removes the owner as the apply
  environment's required reviewer
- **THEN** `scripts/check.py` fails, naming the environment and what changed, before any plan is made

### Requirement: Applies don't overlap
At most one of CI's plan-and-apply runs on `main` SHALL be in progress at a time. A later run SHALL wait for the
earlier one to finish. An apply SHALL refuse a saved plan whose state has changed since the plan was made.

#### Scenario: Two merges in a row
- **WHEN** a second merge lands while the first run is waiting for approval
- **THEN** the second run starts after the first has finished, and plans against the state the first left

### Requirement: A plan of main reads main's current state
Every plan of `main` SHALL be made with the state on `main` when the plan starts, never an older one. A run after CI on
a merge SHALL plan the newest commit with that merge's declaration and `main`'s current state: the merge, or an App
state commit straight after it. If none has, because state was committed after a later merge, it SHALL plan nothing,
say why in its summary, and ask for no approval.

#### Scenario: A merge another run already applied asks nothing
- **WHEN** a scheduled or manual run applies a merge before CI on that merge has finished, and the merge's own run
  then starts
- **THEN** that run plans `main`'s head with the state the apply left, shows no changes, and asks for no approval

#### Scenario: Two merges in a row
- **WHEN** a second merge's run waits behind the first's approval, and the first's apply commits new state
- **THEN** the second run plans with that new state, and its plan shows only what the second merge changes

#### Scenario: An apply before a later merge doesn't hold the earlier merge up
- **WHEN** a merge's run starts after an apply has committed state and then a later merge has landed, with no state
  committed since
- **THEN** the run plans the merge's declaration with that state, whatever the later merge's CI concludes

#### Scenario: State committed after a later merge
- **WHEN** a merge's run starts after a later merge has landed and an apply has then committed state
- **THEN** the run plans nothing and asks for no approval, and its summary names the later merge whose run plans
  with the current state

#### Scenario: A merge with the current state is planned as itself
- **WHEN** a merge's run starts and the merge's state file is the one on `main`'s head, whether or not later merges
  have landed
- **THEN** the run plans that merge, as before this requirement

#### Scenario: A scheduled run that waited plans main's head
- **WHEN** a scheduled or manual run waits behind another run's apply, and the apply commits new state
- **THEN** it plans `main`'s head as it is when its plan starts, not the commit it was started on

#### Scenario: The summary names what was planned
- **WHEN** a run on `main` plans a commit other than the one it was started for
- **THEN** its summary names both commits and why the other was planned

#### Scenario: A commit that isn't on main fails the run
- **WHEN** a run after CI is for a commit that `main`'s history doesn't contain
- **THEN** the plan job fails, naming the commit, and nothing is planned or offered for approval

### Requirement: The new state reaches main after every apply
After an apply, whether it succeeded or failed part way, CI SHALL commit the resulting encrypted state to `main` as
the infrastructure App, in one Conventional Commit that names the commit that was applied, whatever the state's
size. That commit SHALL NOT start another plan. If the commit can't be made, the run SHALL fail, and keep the
encrypted state where the owner can recover it.

#### Scenario: State follows an apply
- **WHEN** an approved apply finishes
- **THEN** `main` has a new commit by the App that changes only `tofu/terraform.tfstate`, and no plan-and-apply run
  starts for it

#### Scenario: A large state is committed
- **WHEN** an approved apply finishes and the state is larger than an operating system allows in one command-line
  argument (128 KB on Linux)
- **THEN** the state is committed to `main` like any other

#### Scenario: A failed state commit isn't lost
- **WHEN** an apply succeeds but committing the state fails
- **THEN** the run fails, and the encrypted state is kept as an artifact of the run

### Requirement: CI runs can be started by hand on main
The owner SHALL be able to start a plan-and-apply run on `main` by hand, for example after drift or a rejected
approval. It follows the same plan, approval and apply.

#### Scenario: Drift is planned on demand
- **WHEN** the owner starts the run by hand after a change was made on GitHub outside OpenTofu
- **THEN** the run plans the drift's reversal and waits for approval like any other

### Requirement: Main is planned every day
CI SHALL plan `main` once a day, whether or not anything merged. The plan SHALL be shown, and a plan with changes
SHALL wait for the owner's approval and apply as any plan of `main` does. A plan with no changes SHALL end the run
without asking for approval. The daily plan SHALL run whatever commit `main`'s head is, the App's state commit
included.

#### Scenario: Drift shows within a day
- **WHEN** a managed file or setting is changed on GitHub outside a delivery or an apply, and nothing merges
  afterwards
- **THEN** within a day, a run on `main` shows a plan restoring it and waits for the owner's approval

#### Scenario: The state commit is planned too
- **WHEN** the daily plan runs and `main`'s head is the App's state commit after an apply
- **THEN** the run plans `main` rather than skipping

#### Scenario: No drift asks nothing
- **WHEN** the daily plan finds the declaration and the org in agreement
- **THEN** the run ends after the plan, with no approval requested

### Requirement: A scheduled or manual plan of main waits for green CI
Before a scheduled or manual run plans `main`, it SHALL check CI on the commit CI runs on for `main`'s head: the newest
commit on `main` that changes more than `tofu/terraform.tfstate`, or one after it that CI ran on. It SHALL plan only
once that CI has passed, waiting while CI is pending or running, up to a time limit. No input SHALL let a run skip
this check. A run after CI on a merge SHALL be unchanged.

#### Scenario: Green CI is planned as before
- **WHEN** a scheduled or manual run starts and CI passed on `main`'s newest commit that CI runs on
- **THEN** the run plans `main`'s head, as it did before this requirement

#### Scenario: The App's state commit is looked past
- **WHEN** a scheduled run starts and `main`'s head is the App's state commit after an apply
- **THEN** the run checks CI on the commit before it, the one that was applied, and plans `main`'s head once that
  CI has passed

#### Scenario: Running CI is waited for
- **WHEN** a scheduled or manual run starts while CI on that commit is queued or running
- **THEN** the run waits, and plans once CI passes, or fails as for red CI if CI fails

#### Scenario: A manual run can't skip the check
- **WHEN** the owner starts the run by hand while CI on `main` is red
- **THEN** it fails as a scheduled run does, and the run takes no input that skips the check

#### Scenario: A run after CI on a merge is unchanged
- **WHEN** CI passes on a merge to `main` and its run starts
- **THEN** that run plans as before this requirement, without checking CI again

### Requirement: A red main fails a scheduled or manual plan, saying how to recover
When CI on that commit concluded anything but success, or didn't finish within the time limit, a scheduled or manual
run SHALL fail before planning or asking for approval. Its summary SHALL name the commit, link the CI run, and say how
to recover: a fix pull request, a re-run of the failed CI job, or a break-glass apply from the owner's machine.

#### Scenario: Red CI fails the run before planning
- **WHEN** a scheduled or manual run starts and CI failed on `main`'s newest commit that CI runs on
- **THEN** the plan job fails without planning or asking for approval, and its summary names the commit, links the
  failed CI run, and lists the three ways to recover

#### Scenario: A cancelled CI run isn't green
- **WHEN** CI on that commit was cancelled, timed out, or concluded anything else but success
- **THEN** the run fails as for red CI

#### Scenario: CI that doesn't finish in time fails the run
- **WHEN** CI on that commit hasn't finished within the time limit
- **THEN** the plan job fails without planning, saying CI didn't finish and naming the commit

#### Scenario: A red main fails every daily run until it's green
- **WHEN** CI on `main` stays red across several days
- **THEN** each daily run fails the same way, and the first daily run after CI passes plans as usual

### Requirement: A pull request merges only after its plan succeeds
On this repository, a pull request's plan SHALL be a required check. A pull request that is planned SHALL NOT be
mergeable until the owner has approved its plan run and the plan has succeeded. When unsure whether a file is read
by OpenTofu, it SHALL count as read, so a mistake costs an approval rather than a missing plan.

#### Scenario: A pull request waits for its plan
- **WHEN** a pull request changes what is declared and the owner hasn't approved its plan run
- **THEN** GitHub refuses to merge it, naming the plan check

#### Scenario: A failed plan blocks the merge
- **WHEN** a pull request's plan fails, for example because the configuration doesn't plan
- **THEN** GitHub refuses to merge it

#### Scenario: A file not known to be ignored is planned
- **WHEN** a pull request changes a file outside the paths known to be ignored by OpenTofu, such as a new top-level
  directory
- **THEN** the pull request is planned

### Requirement: CI tests each pull request once, and main after every push
This repository's tests (the `check` and `guard tests` jobs) SHALL run once for each update to a pull request, on the
pull request merged onto `main`, and once for every push to `main` that changes more than the state file. A push to
any other branch, and the App's state commit after an apply, SHALL NOT run them again. On `main` they SHALL run in
full. The `guard` check's triggers are set by "The rules are re-checked on GitHub" (development-workflow).

#### Scenario: A pull request is tested once
- **WHEN** a commit is pushed to a branch that has an open pull request into `main`
- **THEN** each of the `check` and `guard tests` checks reports once on that commit, from the pull request's run

#### Scenario: A merge to main is tested, and then planned
- **WHEN** a pull request is merged into `main`
- **THEN** CI runs the full check and every guard-tests leg on `main`'s new head, whatever paths the merge changed,
  and the plan of `main` follows that run once it passes

#### Scenario: The state commit isn't tested again
- **WHEN** the App commits the state to `main` after an apply, changing only the state file
- **THEN** CI doesn't run its tests on that commit, and the `guard` check still runs on the push

#### Scenario: A branch with no pull request
- **WHEN** a branch other than `main` is pushed and no pull request is open for it
- **THEN** CI doesn't run its tests, and the `guard` check still runs on the push

### Requirement: A change runs the checks its paths need
This repository SHALL declare a scope, in its check-paths declaration, for each of its declarations that only some
tests read: DNS records, milestones, labels, the OpenTofu configuration and the docs. A commit, and a pull request's
`check` job, SHALL run what the guard's check-scope answer gives for the changed paths: nothing, those scopes, or the
full check. Every non-test gate runs in a scoped check.

#### Scenario: A DNS-only pull request
- **WHEN** a pull request changes only `tofu/dns.json` and files under `openspec/`
- **THEN** its `check` job runs `scripts/check.py --scope dns`: ruff, mypy, `tofu fmt` and `tofu validate`, and only
  the tests tagged `dns`, and the job reports success when they pass

#### Scenario: A DNS-only commit
- **WHEN** a commit stages only `tofu/dns.json` and its change's `tasks.md`
- **THEN** the pre-commit check runs `scripts/check.py --scope dns`, and the guard says so

#### Scenario: Two declarations change
- **WHEN** a pull request changes `tofu/milestones.json` and a file under `tofu/labels/`
- **THEN** its `check` job runs `scripts/check.py --scope labels --scope milestones`

#### Scenario: Only skipped paths change
- **WHEN** a pull request changes only files under `openspec/`
- **THEN** its `check` job runs no gate and reports success

#### Scenario: Any other path changes
- **WHEN** a pull request changes a path in no scope and not skipped, such as `scripts/tofu.py`, a new top-level file
  or `scripts/check-paths.toml` itself
- **THEN** its `check` job runs the full check

#### Scenario: The changed paths can't be listed
- **WHEN** the `check` job can't list the pull request's changed paths, or the list is empty
- **THEN** it runs the full check

#### Scenario: A malformed declaration in a pull request
- **WHEN** a pull request's `scripts/check-paths.toml` is malformed
- **THEN** its `check` job fails, naming the file, what's wrong and the fix

#### Scenario: Every test that reads a changed declaration is selected
- **WHEN** a test reads a file in one of this repository's scopes
- **THEN** it carries that scope's tag, or every run of the tests fails it, naming the test, the file and the tag

### Requirement: The guard's tests run on every OS only when what they test changes
On a pull request, the guard's tests on each supported OS and Python version SHALL run when it changes a path they
depend on: a file the guard delivers, the guard's tests and their shared fixtures, the check-paths declaration, the
Python project's files, or the CI workflow. Otherwise they SHALL be skipped. One required `guard tests` check SHALL
report their result either way.

#### Scenario: A pull request that changes the guard
- **WHEN** a pull request changes `scripts/guard.py`, a file under `.githooks/`, or a `test_guard_*.py` test
- **THEN** every guard-tests leg runs, and `guard tests` passes only if every leg passed

#### Scenario: A pull request that doesn't
- **WHEN** a pull request changes only `tofu/dns.json`, `scripts/tofu.py` and files under `openspec/`
- **THEN** no guard-tests leg runs, and `guard tests` reports success

#### Scenario: A failing or cancelled leg
- **WHEN** a guard-tests leg fails or is cancelled on a pull request that needs them
- **THEN** `guard tests` fails, naming the result

#### Scenario: The decision itself fails
- **WHEN** the job that decides whether the guard's tests are needed fails
- **THEN** every leg runs, as if they were needed

#### Scenario: A delivered guard file isn't in the list
- **WHEN** the guard delivers a file that the list of paths the guard's tests depend on doesn't cover
- **THEN** this repository's tests fail, naming the file

### Requirement: What OpenTofu can't manage is checked whenever main is planned
Whenever CI plans `main` (daily, after CI passes on a merge, or on a manual run), it SHALL also run the drift check
for what OpenTofu can't manage, in a job that doesn't depend on the plan. The job SHALL run only on `main`, and SHALL
read GitHub with a token that can only read.

#### Scenario: The daily run checks what OpenTofu can't manage
- **WHEN** the daily run of `main`'s plan starts
- **THEN** the drift job runs too, whatever the plan's result

#### Scenario: A failed plan doesn't hide drift
- **WHEN** the plan of `main` fails
- **THEN** the drift job still runs and reports its own result

#### Scenario: A red main doesn't stop the drift job
- **WHEN** a scheduled or manual run's plan fails because CI on `main` failed or is still running
- **THEN** the drift job still runs and reports its own result

#### Scenario: Drift outside OpenTofu doesn't stop the plan
- **WHEN** the drift job finds a difference in the same run as the daily plan
- **THEN** the plan still runs and, if it has changes, still waits for the owner's approval

#### Scenario: A branch can't get the drift job's credential
- **WHEN** a workflow run on any ref other than `main`, a pull request included, asks for the drift job's credential
- **THEN** GitHub refuses the deployment, and the run gets no secret from that environment

#### Scenario: The drift job can't write
- **WHEN** the drift job's token is used for any write to GitHub
- **THEN** GitHub refuses it, because the token holds only read permissions and the workflow token only
  `contents: read`

### Requirement: The drift job fails on a difference or an unreadable check, and says what it checked
The drift job SHALL run every check the drift check has, the same checks as a hand run. It SHALL fail when the check
finds a difference, and SHALL put each difference in the run's summary and annotations. A check that can't be read
SHALL fail the job, naming the check, and SHALL never count as "no difference". The run's summary SHALL list the
checks it ran.

#### Scenario: A difference fails the daily run
- **WHEN** the daily run finds that something in `oob/` differs from GitHub, such as a repository's dependency graph
  turned off by hand
- **THEN** the drift job fails, and its summary and an error annotation name the difference

#### Scenario: Nothing differs
- **WHEN** every check matches its declaration
- **THEN** the drift job succeeds, and its summary lists the checks that ran

#### Scenario: A check that can't be read fails the run
- **WHEN** one check's read fails, for example with a 403 or a network error
- **THEN** the drift job still runs every other check, then fails, naming the check that couldn't be read

#### Scenario: CI leaves no check out
- **WHEN** the drift job runs
- **THEN** it reads everything a hand run of the drift check reads, the org's App installations included

### Requirement: A plan too long to show is cut on purpose, never silently
Wherever CI shows a plan with a size limit, the pull request's plan comment and the run summary of `main`'s plan, the
plan SHALL be shown whole when it fits. When it doesn't, it SHALL be cut at a line boundary, below the limit, with a
note that it is truncated, how much is shown, and a link to the full plan. Every resource change line and the `Plan:`
line SHALL be listed in full above the cut. A plan SHALL never be cut without that note.

#### Scenario: A plan that fits is shown whole
- **WHEN** a pull request's plan fits within the comment's limit
- **THEN** the comment holds the whole plan and no truncation note

#### Scenario: A plan over the limit is cut at a line, with the summary kept
- **WHEN** a pull request's plan is longer than the comment's limit
- **THEN** the comment stays under GitHub's limit, lists every resource change and the `Plan:` line above the plan,
  shows the plan up to the end of a whole line, says it is truncated and how many of its lines and bytes are shown,
  and links to the full plan

#### Scenario: The full plan is reachable from the comment
- **WHEN** a reader follows the link in a truncated plan comment
- **THEN** they reach the whole plan made by that run

#### Scenario: The plan for approval is cut the same way
- **WHEN** the plan of `main` is longer than the run summary's limit
- **THEN** the run summary lists every resource change and the `Plan:` line, shows the plan cut at a line with the
  truncation note, and links to the full plan

#### Scenario: A summary that can't fit fails the step
- **WHEN** the resource change lines and the `Plan:` line alone don't fit within the limit
- **THEN** the step fails, naming the limit, and posts nothing with any of them left out

### Requirement: A plan identifies a file it writes by its content's hash, not its content
A plan SHALL NOT print the content of a file OpenTofu writes into a repository, such as the guard's delivered files
and the files of `troupe-run/.github`. It SHALL show that file's resource as changing, and the commit message it
plans SHALL carry the hash of the content it writes, so a reader can tell which content each change delivers. The
content is reviewed in the pull request's diff of its source.

#### Scenario: A changed source shows its hash, not its content
- **WHEN** a pull request changes the source of a delivered file
- **THEN** its plan shows each delivery of that file as an update, with the commit message's content hash going from
  old to new, and no line of the file's content

#### Scenario: A drifted file is shown being restored, without its content
- **WHEN** a delivered file is changed in a target repository outside OpenTofu
- **THEN** the next plan shows that file's resource as an update that restores it, and prints neither the target's
  content nor the source's

#### Scenario: Hiding the content is a one-off update that prints no content
- **WHEN** the plan that first hides file content runs, and no source has changed
- **THEN** it shows each file resource as an in-place update whose only change is `content` becoming
  `(sensitive value)`, with OpenTofu's note that the value is unchanged; it prints no file's content, and no
  `commit_message` changes

### Requirement: A Python tooling dependency update isn't planned
A pull request that changes only the Python tooling's dependency files at the repository root (`pyproject.toml` and
`uv.lock`), with or without other files OpenTofu never reads, SHALL NOT be planned and SHALL NOT ask the owner for an
approval. This SHALL hold only while no step of the plan or apply runs in the Python project's environment. The
provider lockfile SHALL be planned, since it changes what OpenTofu runs.

#### Scenario: A Python tooling bump isn't planned
- **WHEN** a pull request changes only `uv.lock`, or `uv.lock` and `pyproject.toml`
- **THEN** its plan job is skipped, no approval is requested, and the skipped job counts as passed

#### Scenario: A provider lockfile bump is planned
- **WHEN** a pull request changes `tofu/.terraform.lock.hcl`, alone or with `uv.lock`
- **THEN** it is planned like any other, and needs the owner's approval of its plan run

#### Scenario: Only the root files are skipped
- **WHEN** a pull request changes a `pyproject.toml` or `uv.lock` anywhere but the repository root
- **THEN** it is planned

#### Scenario: A plan step that uses the project's environment
- **WHEN** a step of the `tofu` workflow runs a script in the Python project's environment rather than without it
- **THEN** the repository's tests fail, naming the step, until the step runs without the project or the Python files
  stop being skipped

### Requirement: CI tests the merge queue's commit in full
This repository's tests (the `check` and `guard tests` jobs) SHALL run once for each commit the merge queue tests,
in full, whatever paths the queued pull requests changed, as they do on a push to `main`.

#### Scenario: A queued pull request is tested on top of main
- **WHEN** a pull request that changes only documentation joins this repository's merge queue
- **THEN** CI runs the full check and every guard-tests leg on the queue's commit, and each reports there

### Requirement: A pull request's plan isn't run again in the merge queue
On this repository, the `plan (pull request)` check SHALL report as skipped on a merge queue's commit, asking for no
approval and holding no credential. The plan of `main` that follows the merge SHALL still be made and approved
before anything applies. A queue's run SHALL NOT wait for, or hold up, a plan or apply of `main`.

#### Scenario: A queued pull request needs no second approval
- **WHEN** a pull request whose plan the owner approved joins the merge queue
- **THEN** `plan (pull request)` reports as skipped on the queue's commit without the owner approving anything, and
  the pull request can land once the other required checks pass

#### Scenario: Main is still planned after the queue lands
- **WHEN** the queue lands a pull request that changes what is declared
- **THEN** CI on `main` is followed by `plan (main)`, and nothing applies until the owner approves it

#### Scenario: A queue run while main is being applied
- **WHEN** a pull request joins the queue while an apply of `main` is waiting for approval
- **THEN** the queue's runs proceed without waiting for that apply, and the apply isn't cancelled
