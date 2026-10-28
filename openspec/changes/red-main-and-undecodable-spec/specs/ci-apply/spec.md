## MODIFIED Requirements

### Requirement: A red main fails a scheduled or manual plan, saying how to recover
When CI on that commit concluded anything but success, or didn't finish within the time limit, a scheduled or manual
run SHALL fail before planning or asking for approval, unless a newer merge superseded it. Its summary SHALL name the
commit, link the CI run, and say how to recover: a fix pull request, a re-run of the failed CI job, or a break-glass
apply from the owner's machine.

#### Scenario: Red CI fails the run before planning
- **WHEN** a scheduled or manual run starts and CI failed on `main`'s newest commit that CI runs on
- **THEN** the plan job fails without planning or asking for approval, and its summary names the commit, links the
  failed CI run, and lists the three ways to recover

#### Scenario: A cancelled CI run isn't green
- **WHEN** CI on that commit was cancelled and `main` on GitHub hasn't moved past it with a commit CI runs on, or CI
  timed out or concluded anything else but success
- **THEN** the run fails as for red CI

#### Scenario: CI that doesn't finish in time fails the run
- **WHEN** CI on that commit hasn't finished within the time limit
- **THEN** the plan job fails without planning, saying CI didn't finish and naming the commit

#### Scenario: A red main fails every daily run until it's green
- **WHEN** CI on `main` stays red across several days
- **THEN** each daily run fails the same way, and the first daily run after CI passes plans as usual

## ADDED Requirements

### Requirement: A scheduled or manual plan superseded by a newer merge plans nothing
When CI on the commit a scheduled or manual run checked was cancelled, the run SHALL check whether `main` on GitHub
has since moved past that commit with a commit CI runs on. If it has, the run SHALL plan nothing, ask for no approval
and not fail, and its summary SHALL name the commit checked and `main`'s newer head, whose own run plans it. A check
that can't be read, or answers anything else, SHALL fail the run as for red CI.

#### Scenario: A merge during the wait cancels the CI it waited for
- **WHEN** a manual run is waiting for CI on `main`'s head, and a newer merge lands and CI's concurrency cancels that
  CI run
- **THEN** the run doesn't plan, ask for approval or fail, its summary names both commits and says the newer one's run
  plans it, and the drift job still runs

#### Scenario: A cancel with main unmoved still fails
- **WHEN** CI on the commit checked was cancelled and `main` on GitHub is still at that commit
- **THEN** the run fails as for red CI

#### Scenario: Only state commits since the cancel
- **WHEN** CI on the commit checked was cancelled and the only commits on `main` since change nothing but
  `tofu/terraform.tfstate`
- **THEN** the run fails as for red CI, since no newer CI run will plan it

#### Scenario: The check of main can't be read
- **WHEN** CI on the commit checked was cancelled and GitHub can't be asked whether `main` has moved, or answers that
  the two have diverged or with anything else this doesn't know
- **THEN** the run fails, naming what it couldn't read, and plans nothing
