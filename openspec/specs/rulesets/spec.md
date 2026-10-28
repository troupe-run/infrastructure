# rulesets Specification

## Purpose
The rules GitHub enforces on the org's branches, declared here: which repositories and branches they cover, what they
refuse, who may bypass them, and how the owner keeps the ability to change them.

## Requirements

### Requirement: Main is protected on every managed repository except .github
`main` SHALL be covered by a ruleset on `troupe`, `infrastructure` and `website`, and on every repository brought
under management later unless its declaration says otherwise. `troupe-run/.github` SHALL be covered by its own
ruleset instead, under which only the infrastructure App changes `main`.

#### Scenario: Every protected repository has the ruleset
- **WHEN** the managed repositories' rulesets are read from GitHub
- **THEN** `troupe`, `infrastructure` and `website` each have an active ruleset on `main`, `.github` has its own
  active ruleset on `main`, and the plan shows no difference from the declaration

### Requirement: Changes reach main only through a pull request
A push directly to `main` SHALL be refused for everyone, the owner included (`.github` excepted: see below). A
pull request SHALL be mergeable without an approving review, because the org has one maintainer. The infrastructure
App is excepted:
- in a repository that receives the guard, it MAY push its deliveries straight to `main`;
- in this repository, it MAY push the encrypted state straight to `main` after an apply.

#### Scenario: A direct push is refused
- **WHEN** anyone, the owner included, pushes a commit directly to `main`
- **THEN** GitHub refuses the push, naming the ruleset

#### Scenario: A pull request merges without a review
- **WHEN** a pull request into `main` has no reviews, its required checks have passed, and it is merged by rebase
- **THEN** the merge succeeds

#### Scenario: The App delivers to a governed repository
- **WHEN** the infrastructure App commits a delivered file to `main` in a repository that receives the guard
- **THEN** GitHub accepts the commit, although the commit has no checks of its own

#### Scenario: The App commits state to this repository
- **WHEN** the infrastructure App commits `tofu/terraform.tfstate` to `main` in this repository
- **THEN** GitHub accepts the commit, although the commit has no checks of its own

#### Scenario: The App's exception is limited to governed repositories
- **WHEN** the managed rulesets are read
- **THEN** only this repository's ruleset, `.github`'s ruleset and the rulesets of repositories that receive the
  guard name the App as a bypass actor, and no other App is named by any

### Requirement: Pull requests merge by rebase only
A pull request into `main` SHALL be mergeable only by rebase. Merging with a merge commit or by squashing SHALL be
refused, so `main` keeps a linear history that carries each commit.

#### Scenario: A merge commit is refused
- **WHEN** a pull request into `main` is merged with the merge method
- **THEN** GitHub refuses it

#### Scenario: A squash is refused
- **WHEN** a pull request into `main` is merged with the squash method
- **THEN** GitHub refuses it

### Requirement: Main's history can't be rewritten or deleted
A force-push to `main` and the deletion of `main` SHALL be refused, and a merge commit SHALL NOT be pushed to it.

#### Scenario: A force-push is refused
- **WHEN** anyone force-pushes to `main`
- **THEN** GitHub refuses it

#### Scenario: Deleting main is refused
- **WHEN** anyone deletes the `main` branch
- **THEN** GitHub refuses it

### Requirement: The owner bypasses rules only through a pull request
An org owner SHALL be able to merge a pull request that a rule would otherwise block, including one whose required
checks have failed or not reported. That bypass SHALL NOT extend to pushing to `main` directly. On `.github`, the
owner has no bypass: the break-glass there is changing the ruleset.

#### Scenario: The owner's direct push is refused
- **WHEN** an org owner pushes directly to `main`
- **THEN** GitHub refuses the push

#### Scenario: The owner merges past a failing check
- **WHEN** a required check on a pull request has failed and an org owner merges it, choosing to bypass the rules
- **THEN** the merge succeeds

### Requirement: The owner can't be locked out
An org owner SHALL always be able to change or disable a ruleset on GitHub as a break-glass. Any such change SHALL
appear in the next plan, and an apply SHALL restore the declared ruleset.

#### Scenario: A ruleset disabled on GitHub shows as drift and is restored
- **WHEN** an owner disables a declared ruleset on GitHub
- **THEN** the next plan shows it returning to `active`, and applying that plan restores it

### Requirement: Pull requests merge only when their required checks pass
A pull request into `main` SHALL NOT be mergeable until every check its repository requires has passed on the pull
request's latest commit. Each required check SHALL be accepted only from the App that is meant to post it, so a check
of the same name posted by anything else doesn't count. A check that is skipped SHALL count as passed.

#### Scenario: A failing check blocks the merge
- **WHEN** one of a repository's required checks has failed on a pull request
- **THEN** GitHub refuses to merge it, naming the check

#### Scenario: A missing check blocks the merge
- **WHEN** a required check hasn't reported on a pull request's latest commit
- **THEN** GitHub refuses to merge it until the check passes

#### Scenario: A check from the wrong source doesn't count
- **WHEN** a status with a required check's name is posted on a pull request by something other than that check's App
- **THEN** the check is still missing, and the pull request can't be merged

### Requirement: Each repository requires its own checks
Each repository with a `main` ruleset SHALL require the checks that run on its pull requests:
- `infrastructure`: its CI check, its `guard tests` check, the `guard` check, DCO, and its pull request's plan;
- `troupe`: its CI `check`, not its legs, the `guard` check and DCO;
- `website`: its CI test and the `guard` check. It SHALL NOT require DCO: its contributions are accepted under its
  own licences, with no sign-off (owner, 2026-10-16).

The required names SHALL be declared in one place.

#### Scenario: The declared names match this repository's workflows
- **WHEN** this repository's tests run
- **THEN** they fail if `infrastructure`'s required checks name a job its workflows don't define, or leave out a job
  the list above says is required

#### Scenario: troupe's legs aren't required, their result is
- **WHEN** this repository's tests run
- **THEN** they fail if troupe's required checks leave out `check`, or name any `check (<os>, Python <version>)` leg:
  a skipped matrix job reports under its unexpanded name, so a required leg would never report on a push that skips
  them

#### Scenario: A renamed job can't be merged past
- **WHEN** a pull request renames a required job, so the old name never reports
- **THEN** the pull request can't be merged until the required checks are changed to match, or the owner bypasses
  the rules

#### Scenario: A website pull request needs the guard check
- **WHEN** a pull request into the website's `main` has passed its CI test but its `guard` check has failed or not
  reported
- **THEN** GitHub refuses to merge it, naming the `guard` check

#### Scenario: A website pull request needs no sign-off
- **WHEN** a pull request into the website's `main` has unsigned-off commits and its CI test and `guard` check have
  passed
- **THEN** the merge succeeds

#### Scenario: A skipped guard-tests matrix doesn't block a merge
- **WHEN** a pull request into `infrastructure` changes nothing the guard's tests depend on, so every guard-tests leg
  is skipped
- **THEN** its required checks can all pass, and it can be merged once they do

#### Scenario: A troupe pull request whose legs were skipped can merge
- **WHEN** the latest push to a troupe pull request skips every check leg, and its `check`, `guard` and DCO checks
  have passed
- **THEN** GitHub shows the pull request as mergeable

#### Scenario: A failed troupe leg blocks the merge
- **WHEN** any check leg on a troupe pull request's latest commit has failed
- **THEN** its `check` fails, and GitHub refuses to merge it, naming `check`

### Requirement: Only the App changes .github's main
In `troupe-run/.github`, every change to `main` SHALL be refused unless the infrastructure App makes it. That
includes pushes, merges of pull requests, force-pushes and deleting the branch, by anyone, org owners included.

#### Scenario: The App syncs a file
- **WHEN** the infrastructure App commits a file to `.github`'s `main`
- **THEN** GitHub accepts the commit

#### Scenario: The owner's push is refused
- **WHEN** an org owner pushes a commit to `.github`'s `main`
- **THEN** GitHub refuses it, naming the ruleset

#### Scenario: A pull request can't merge
- **WHEN** anyone, an org owner included, tries to merge a pull request into `.github`'s `main`
- **THEN** GitHub refuses the merge

### Requirement: Pull requests reach main through a merge queue
In a repository whose queue is turned on, a pull request into `main` SHALL merge only through a merge queue that
merges by rebase. The queue SHALL land exactly the commits it tested, so `main` stays linear and carries each commit.
The infrastructure App's direct pushes to `main` and the owner's pull-request bypass SHALL work as before.

#### Scenario: The owner's merge adds the pull request to the queue
- **WHEN** the owner merges a pull request into `main` whose required checks have passed, in a repository whose
  queue is on
- **THEN** the pull request joins the merge queue, and lands on `main` by rebase only after the queue's checks pass

#### Scenario: What lands is what was tested
- **WHEN** the queue lands a pull request
- **THEN** `main`'s new head is the commit the queue's checks ran on, and `main`'s history has no merge commit

#### Scenario: The App still delivers straight to main
- **WHEN** the infrastructure App pushes a delivery or a state commit to `main` in a repository whose queue is on
- **THEN** GitHub accepts the push without the queue

#### Scenario: The owner still merges past a failing check
- **WHEN** a pull request's required check has failed and an org owner merges it, choosing to bypass the rules
- **THEN** the merge succeeds without the queue

### Requirement: The queue lands only a combination whose required checks passed
A queued pull request SHALL land only when every check its repository requires has passed on the queue's commit:
`main` with the pull requests ahead of it in the queue and its own commits applied. A check that fails, or doesn't
report before the queue's timeout, SHALL remove the pull request from the queue and leave `main` unchanged.

#### Scenario: Two pull requests that break main together
- **WHEN** two pull requests each pass their checks alone, are queued one after the other, and the second fails a
  required check on top of the first
- **THEN** the first lands, the second is removed from the queue, and `main` never holds the failing combination

#### Scenario: A check that never reports
- **WHEN** a required check doesn't report on a queued commit within the queue's timeout
- **THEN** the pull request is removed from the queue and `main` is unchanged

### Requirement: A repository's queue is on only when its required checks report on the queue
Whether a repository's `main` merges through a queue SHALL be declared once per repository. A queue SHALL be turned
on only when every check that repository requires runs on merge groups, so the queue never waits on a check that
can't report.

#### Scenario: A required workflow without the queue's trigger
- **WHEN** this repository's tests run and infrastructure's queue is declared on while a workflow defining one of
  its required checks doesn't run on merge groups
- **THEN** the tests fail, naming the check and its workflow

#### Scenario: A repository with its queue off
- **WHEN** a repository's queue is declared off
- **THEN** its `main` ruleset has no merge queue rule, and its pull requests merge by rebase as before

### Requirement: troupe, infrastructure and website merge through the queue
Each repository whose `main` takes pull requests (troupe, infrastructure and website) SHALL have its merge queue
turned on. A product repository's switch SHALL go on only once every check it requires runs on merge groups on its
`main`, since its CI workflows live in that repository and this one's tests can't read them.

#### Scenario: Each repository's ruleset has the queue
- **WHEN** the `protect main` ruleset of troupe, infrastructure or website is read from GitHub
- **THEN** it has the merge queue rule, merging by rebase, and the plan shows no difference

#### Scenario: A product repository's next pull request lands through its queue
- **WHEN** the owner merges a pull request in troupe or website after its queue is turned on
- **THEN** the pull request joins the queue, every check that repository requires reports on the merge group, and
  `main`'s new head is the commit the queue tested

#### Scenario: A product repository's CI doesn't run on merge groups
- **WHEN** the workflow defining one of troupe's or website's required checks, on that repository's `main`, isn't
  triggered by `merge_group` or narrows what it runs there
- **THEN** that repository's switch stays off until a pull request there fixes the workflow

### Requirement: Pull requests merge only when every review conversation is resolved
On troupe, infrastructure and website, a pull request into `main` SHALL NOT be mergeable, or join the merge queue,
while any review conversation on it is unresolved, whoever opened it. The owner's pull-request bypass SHALL still
merge past it. The setting SHALL be declared once, in the repository module.

#### Scenario: An open finding
- **WHEN** a pull request's required checks have passed but a conversation the review opened is unresolved
- **THEN** GitHub refuses to merge it or add it to the merge queue

#### Scenario: Every conversation resolved
- **WHEN** every conversation on a pull request is resolved and its required checks have passed
- **THEN** it can be merged, through the queue where the repository has one

#### Scenario: The owner bypasses
- **WHEN** an org owner merges a pull request with an open conversation, choosing to bypass the rules
- **THEN** the merge succeeds

#### Scenario: The setting is turned off on GitHub
- **WHEN** someone turns off conversation resolution in a repository's `main` ruleset on GitHub
- **THEN** the next plan shows the difference, and an apply restores it
