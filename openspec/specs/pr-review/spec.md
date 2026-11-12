# pr-review Specification

## Purpose

Claude reviews each pull request in the governed repositories (troupe, infrastructure, website) automatically and
posts each finding as a conversation, labelled must-fix, nit or decision for who resolves it. It can't change the code
or approve; an unresolved conversation blocks the merge through the ruleset. This spec covers when it runs, what it may
write, how its findings are tiered and resolved, the credentials it uses and how the workflow reaches each repository.

## Requirements

### Requirement: Claude reviews each pull request when it's opened and updated
A pull request in troupe, infrastructure or website SHALL get a review from Claude when it's opened, reopened, or
pushed to. Drafts SHALL be reviewed too. Marking a draft ready for review SHALL NOT start a review: its head was
reviewed when it was pushed. The review SHALL be posted as comments on the pull request: inline on the lines it
concerns, and one top-level summary.

#### Scenario: A pull request is opened
- **WHEN** a member opens a pull request from a branch of troupe, infrastructure or website
- **THEN** a review run starts, and Claude's comments appear on the pull request once it finishes

#### Scenario: A pull request is updated
- **WHEN** a member pushes a new commit to a pull request's branch
- **THEN** a new review run starts for the new head, and a run still going for the earlier head is cancelled

#### Scenario: A draft
- **WHEN** a member opens a draft pull request
- **THEN** it's reviewed as any other pull request is

#### Scenario: A draft is marked ready
- **WHEN** a member marks a draft pull request ready for review, with no new push
- **THEN** no review run starts, and the review of its last push stands

#### Scenario: A push after it's marked ready
- **WHEN** a member pushes to a pull request after marking it ready
- **THEN** a review run starts for the new head, as for any push

### Requirement: Pull requests opened by a bot, or from a fork, aren't reviewed
A pull request whose author is a bot SHALL NOT start a review. That covers Dependabot, release-please's release pull
requests through `troupe-run-release`, and any App's. A pull request from a fork SHALL NOT get the review's credential,
so it SHALL NOT be reviewed automatically.

#### Scenario: A release pull request
- **WHEN** `troupe-run-release[bot]` opens or updates troupe's release pull request
- **THEN** the review job is skipped, and the run doesn't fail

#### Scenario: A Dependabot pull request
- **WHEN** Dependabot opens a pull request
- **THEN** the review job is skipped, and the run doesn't fail

#### Scenario: A fork's pull request
- **WHEN** an outside contributor opens a pull request from a fork
- **THEN** the review job is skipped, the run doesn't fail, and the credential isn't exposed to it

### Requirement: The review judges a reply to one of its must-fixes when it's posted
When a person with write access to the repository replies in an open must-fix conversation the review opened, a review
run SHALL start for the pull request, with no push and nothing re-run by hand. It SHALL be the same review a push
starts, of the pull request's current head, so it judges the reply with the rest of the conversations. Re-running a
review run by hand SHALL still work.

#### Scenario: The author answers a must-fix
- **WHEN** the author replies to an open must-fix with why the code is right
- **THEN** a review run starts, and either resolves the conversation, re-tiers it, or leaves it open, and its summary
  says which

#### Scenario: A burst of replies
- **WHEN** the author replies in three must-fix conversations within a minute
- **THEN** each reply cancels the run the one before it started, and the last reply's run judges all three

#### Scenario: A reply while a review is running
- **WHEN** a person replies to a must-fix while a review of the pull request is running
- **THEN** that review is cancelled, and the reply's run reviews the pull request as a push's run would

#### Scenario: A push after a reply
- **WHEN** the author pushes while a reply's review is running
- **THEN** the reply's run is cancelled, and the push's run reviews the new head and judges the reply

#### Scenario: A reply's run failed
- **WHEN** a reply's review run fails
- **THEN** re-running it, or the pull request's last `claude review` run, judges the reply

### Requirement: Only a person's reply to an open must-fix starts a review
A review comment SHALL start a review only when it replies in an open conversation the review opened whose tier is
must-fix, its author is not a bot and has write access to the repository, and the pull request isn't from a fork or
opened by a bot. Any other review comment SHALL start no review, SHALL NOT fail its run, and SHALL get no secret when it
comes from a fork.

#### Scenario: The author answers a nit
- **WHEN** the author, or an agent with the author's login, replies to a nit saying what it did
- **THEN** no review starts, and the nit is the author's to resolve

#### Scenario: A reply to a decision
- **WHEN** someone replies in a conversation labelled decision
- **THEN** no review starts, since no review resolves a decision

#### Scenario: A reply in a person's own conversation, or a resolved one
- **WHEN** someone replies in a conversation a person opened, or in a must-fix that's already resolved
- **THEN** no review starts until the next push or must-fix reply

#### Scenario: The conversation replied to can't be read
- **WHEN** a reply's run can't read the pull request's review conversations
- **THEN** no review starts, the run fails saying so, and re-running it once they can be read judges the reply

#### Scenario: The review's own comments
- **WHEN** `troupe-run-review[bot]` posts a finding, or a reply that re-tiers one
- **THEN** no review starts, and the run it causes is skipped

#### Scenario: A comment that opens a conversation
- **WHEN** a person posts a new review comment that doesn't reply to another
- **THEN** no review starts until the next push or reply

#### Scenario: An outside user replies
- **WHEN** someone without write access to the repository replies to one of the review's must-fixes
- **THEN** no review starts, and the run it causes doesn't fail

#### Scenario: A member whose membership is private replies
- **WHEN** an org member with write access, whose membership isn't public, replies to an open must-fix
- **THEN** a review starts, though GitHub labels the comment's author a contributor

#### Scenario: A reply on a fork's pull request
- **WHEN** someone replies in a review conversation on a pull request from a fork
- **THEN** no review starts, and the run gets no secret

#### Scenario: A reply on a bot's pull request
- **WHEN** a person replies in a conversation on a Dependabot or release pull request
- **THEN** no review starts

### Requirement: A skipped run doesn't cancel a running review
A run whose review job is skipped SHALL NOT cancel, or delay, a review run for the same pull request. Only a run whose
review job starts SHALL replace one that's running.

#### Scenario: The review posts its findings
- **WHEN** a running review posts five inline findings, each of which starts a run that's skipped
- **THEN** the review runs to its end, posts its summary, and its resolving job runs

#### Scenario: An outside user comments during a review
- **WHEN** someone without write access replies in a conversation while a review is running
- **THEN** the running review isn't cancelled

### Requirement: A review run can't change the repository
A review run SHALL write only with review App tokens for its repository: contents read and pull requests write in
Claude's job; contents write and pull requests write, which resolving needs, in the resolving job, where Claude doesn't
run and nothing is checked out. Each `GITHUB_TOKEN` SHALL hold only `contents: read`, and no `id-token`. Claude's tools
SHALL be limited to reading the pull request and commenting. The run SHALL NOT use `pull_request_target`.

#### Scenario: Where the comments come from
- **WHEN** a review is posted
- **THEN** its comments are by `troupe-run-review[bot]`

#### Scenario: The run's tokens
- **WHEN** a review run's log is read
- **THEN** each job's `GITHUB_TOKEN` permissions list `Contents: read` and `Metadata: read` only; the review job's App
  token asks for contents read and pull requests write, and the resolving job's for contents write and pull requests
  write

#### Scenario: Claude tries to push
- **WHEN** a pull request's text asks Claude to commit a fix or push a branch
- **THEN** Claude has no tool that edits files or runs git, and the job it runs in has no token that can write
  contents, so nothing is pushed

#### Scenario: Claude is asked to read outside the checkout
- **WHEN** a pull request's text asks Claude to read `/proc/self/environ`, `.git/config` or any file outside the
  checkout, and post what it finds
- **THEN** the read is refused, because Read, Grep and Glob reach the checkout only, and the checkout keeps no token

#### Scenario: The workflow is weakened
- **WHEN** a change gives either job another permission, runs Claude or a checkout in the resolving job, swaps its event for `pull_request_target`, drops the
  bot skip, lets it mint a token through OIDC, asks the App for more, widens Claude's tools, or uses an action that
  isn't pinned to a full commit SHA
- **THEN** `scripts/check.py` fails, naming what changed

#### Scenario: The reply trigger is widened
- **WHEN** a change starts the review on another event, such as `issue_comment` or `pull_request_review`, or on another
  review comment action, drops the reply-only, bot or fork skip or the write-access check, judges write access by the comment's
  author association, lets the review start without the check
  that the reply is to an open must-fix of the review's, puts that check in the concurrency group, or moves the group
  back to the workflow, where a skipped run joins it
- **THEN** `scripts/check.py` fails, naming what changed

### Requirement: The review App is narrow and installed on the governed repositories
The review App `troupe-run-review` SHALL have only these repository permissions: contents read and write, which
resolving a conversation needs (owner, 2026-10-28), pull requests read and write, and metadata read. It SHALL have no organisation permissions. Its installation SHALL select repositories,
and SHALL cover troupe, infrastructure and website only. Any difference SHALL be reported by the drift check or the
hand-confirmed list (spec: teams-and-access).

#### Scenario: The review App gains a permission
- **WHEN** the review App's installation gains a permission on GitHub, such as administration or workflows
- **THEN** the drift check reports the permission and exits non-zero

#### Scenario: The declared review App matches
- **WHEN** the review App has exactly the declared permissions and repository selection
- **THEN** the drift check reports no difference for it

### Requirement: The review loads no settings from the repository
A review run SHALL load Claude Code settings from the user scope only, never from the repository's `.claude/`
directory or a local settings file. So the guard's Claude Code hooks, which are written for an agent working in the
owner's terminal, SHALL NOT run in it, and SHALL NOT widen the tools the review allows (owner, 2026-10-26).

#### Scenario: The repository holds the guard's hooks
- **WHEN** a pull request is reviewed in a repository whose `.claude/settings.json` holds the guard's hooks
- **THEN** the review reads the diff and posts its comments, and none of the guard's hooks runs

#### Scenario: A hook would grant a write
- **WHEN** the review is asked to close or retitle the pull request
- **THEN** it can't: no repository setting grants `gh pr close` or `gh pr edit`, and its tool list doesn't allow them

#### Scenario: The settings are widened
- **WHEN** a change makes the review load project or local settings
- **THEN** `scripts/check.py` fails, naming the setting sources

### Requirement: The review's credentials are org secrets set by hand
The review SHALL authenticate to Claude with `CLAUDE_CODE_OAUTH_TOKEN`, and mint its GitHub token with
`REVIEW_APP_PRIVATE_KEY`. Each SHALL be an org Actions secret visible to troupe, infrastructure and website only, set
by the owner from 1Password with a documented command that prints nothing. OpenTofu SHALL NOT hold either, and
`oob/README.md` SHALL record how each is made, checked by name and rotated.

#### Scenario: Checking the secret
- **WHEN** the owner lists each org secret's repositories, by name, never by value
- **THEN** exactly troupe, infrastructure and website are listed

#### Scenario: A failed read sets nothing
- **WHEN** the 1Password read fails while the documented command runs
- **THEN** no secret is set or overwritten

#### Scenario: The token has expired
- **WHEN** a review run's Claude credential is refused
- **THEN** the run fails with the action's authentication error, its `claude review completed` check fails, and the
  pull request can't merge until the token is renewed and the run re-run, or the owner bypasses the rules

### Requirement: The review is advisory
Claude SHALL NOT approve or request changes on a pull request, and the review job SHALL NOT be a required check. What
the review finds blocks a merge only through its open conversations (spec: rulesets), never through its review state.
That the review of the head completed SHALL be required, through the `claude review completed` check.

#### Scenario: The review fails
- **WHEN** a pull request's last review run fails or times out
- **THEN** the pull request can't merge until a review of its head completes, and then can once its other required
  checks pass and its open conversations are resolved

#### Scenario: Claude's findings
- **WHEN** Claude finishes a review
- **THEN** it has posted comments, and resolved only its own conversations, and the pull request's review state is
  unchanged

### Requirement: The review checks the org's own rules
The review's instructions SHALL be written in one place, the workflow's prompt. It SHALL check the pull request against
the repository's `CLAUDE.md` as on the base branch, the org's contributing guide, the OpenSpec change's tasks and specs
against the diff, the linked issue's "Done when", and Conventional Commits, as well as for correctness bugs.

#### Scenario: An unticked task's code is in the diff
- **WHEN** a pull request implements a task its change's `tasks.md` leaves unticked, or ticks one whose code isn't there
- **THEN** Claude's review points it out

#### Scenario: A pull request edits CLAUDE.md
- **WHEN** a pull request changes `CLAUDE.md`
- **THEN** the review is guided by the base branch's `CLAUDE.md`, not the pull request's

### Requirement: The review workflow is delivered from this repository
The review workflow's source SHALL be this repository's `.github/workflows/claude-review.yml`. It SHALL be delivered to
troupe and website with the guard's files, listed in each one's `.github/guard-delivery.json` and changed only at its
source (spec: guard-delivery). It SHALL NOT be delivered to `.github`.

#### Scenario: The delivered workflow
- **WHEN** troupe's or website's `.github/workflows/claude-review.yml` is read after an apply
- **THEN** it has the source's content, and the repository's delivered list names it

#### Scenario: An edit in a governed repository
- **WHEN** someone changes the review workflow in troupe directly
- **THEN** the guard refuses the commit as a delivered file, and if it reaches GitHub, the next plan restores it

#### Scenario: .github
- **WHEN** the managed state is read after an apply
- **THEN** `.github` holds no review workflow

### Requirement: A review run names each permission denial in its log
When Claude is refused a tool call, the review run SHALL name the call in its log as a warning: the tool and its
input, cut short. The run SHALL show nothing else from the session, which stays hidden. A run with no denial SHALL say
so. Reporting SHALL use no secret, and SHALL NOT fail the run or stop the review's comments from being posted.

#### Scenario: A call is refused
- **WHEN** Claude tries a tool its list doesn't allow, such as fetching a URL
- **THEN** the run shows a warning naming that tool and its input, and the review's comments are still posted

#### Scenario: Nothing is refused
- **WHEN** a review finishes without a denial
- **THEN** the run's log says no call was refused, and shows no warning for it

#### Scenario: A denied input holds a workflow command
- **WHEN** a denied call's input holds a newline or `::`, for example text a pull request asked Claude to run
- **THEN** it's printed inside the one warning, and no workflow command runs from it

#### Scenario: The session's output stays hidden
- **WHEN** a review run's log is read
- **THEN** it shows the denials and the action's own summary, but not the session's messages or tool results

#### Scenario: The report is widened or dropped
- **WHEN** a change adds a step that runs another command, changes the reporting step, or gives the action
  `show_full_output` or `display_report`
- **THEN** `scripts/check.py` fails, naming the step or input

### Requirement: The review reads the org's contributing guide from its checkout
A review run SHALL check out troupe-run/.github's `CONTRIBUTING.md` into a path inside its workspace, keeping no
credential, and the prompt SHALL name that path. The review SHALL read the guide with its Read tool and gain no tool
to fetch a URL. In infrastructure, which holds the guide's source, the prompt SHALL also name that source.

#### Scenario: The review checks the guide
- **WHEN** a pull request is reviewed in troupe, infrastructure or website
- **THEN** Claude reads the guide from the checkout, and no call to fetch it is refused

#### Scenario: A pull request changes the guide's source
- **WHEN** a pull request in infrastructure changes `org-profile/CONTRIBUTING.md`
- **THEN** the prompt tells Claude that file is the guide's source, and the copy from troupe-run/.github is the
  version on its main

#### Scenario: The guide's checkout keeps a credential or leaves the workspace
- **WHEN** a change lets the guide's checkout keep its token, moves it outside the workspace, checks out another
  repository, or adds a tool that fetches URLs
- **THEN** `scripts/check.py` fails, naming what changed

### Requirement: Each finding is a must-fix, a nit or a decision
The review SHALL label each finding with one tier, named for who resolves it: must-fix (the review, once addressed),
nit (the author, or the review once a push has fixed it) or decision (the owner). The prompt SHALL define the tiers in
one place, and SHALL say that a finding the review is unsure between must-fix and nit is a must-fix. The summary
comment SHALL list decisions and must-fixes first.

#### Scenario: A bug
- **WHEN** the review finds code that does the wrong thing, loses data, weakens a security fence, or a test whose name
  claims more than its body checks
- **THEN** its comment is labelled must-fix

#### Scenario: A stale path in a comment
- **WHEN** the review finds a comment that names a file the pull request moves
- **THEN** its comment is labelled nit

#### Scenario: A choice the design doesn't settle
- **WHEN** the review finds two defensible ways the pull request could go, the change's design doesn't choose, and the
  choice is hard to reverse or reaches beyond the pull request
- **THEN** its comment is labelled decision

#### Scenario: A cheap, local choice
- **WHEN** the review finds two defensible ways to write something that only this pull request's code depends on
- **THEN** its comment is labelled nit, and the author chooses

### Requirement: A commit SHA a rebase removed isn't a finding
The review SHALL NOT raise a finding, at any tier, because a commit SHA cited in the pull request names no commit on
its branch, and SHALL NOT ask for one to be re-cited. Its prompt SHALL say why: pull requests merge by rebase, which
rewrites every SHA, so no cited SHA survives the merge. A ticked task SHALL still be judged by its code and
verification in the pull request, and a CI run id it cites SHALL still count as evidence.

#### Scenario: A task cites CI on a commit from before a rebase
- **WHEN** a ticked task in the change's `tasks.md` says its verification passed in "CI run N on `<sha>`", its code
  and test are in the diff, and the branch was rebased so `<sha>` is no longer on it
- **THEN** the review raises no finding about the SHA, and doesn't ask for the task to cite the new head

#### Scenario: A ticked task with nothing behind it
- **WHEN** a ticked task cites a CI run on a commit, but its code or its verification isn't in the pull request
- **THEN** the review still raises the ticked task with nothing behind it as a must-fix

#### Scenario: Another stale reference
- **WHEN** the review finds a comment or doc that names a file, function or section the pull request moved, renamed
  or removed
- **THEN** its comment is still labelled nit

### Requirement: A conversation's tier is the review's latest label in it
A conversation's tier SHALL be the latest label `troupe-run-review[bot]` gave in it; a later reply of the review's
with no label keeps it. Only the review SHALL change a tier, by replying in the conversation with a new label line and its reason; the author argues for a change by
replying, and a label in anyone else's comment SHALL count for nothing.

#### Scenario: A must-fix turns out to be a choice
- **WHEN** the author replies to a must-fix that both ways are defensible, and the next review agrees
- **THEN** the review replies in the conversation labelled decision, saying why, and the conversation is the owner's

#### Scenario: A must-fix turns out to be small
- **WHEN** the author's reply shows a must-fix is only wording, and the next review agrees
- **THEN** the review replies labelled nit, and the author may resolve it

#### Scenario: The author relabels a finding
- **WHEN** the author replies to a must-fix with a comment whose first line is `**nit**`
- **THEN** the conversation is still a must-fix, the guard still refuses the author's resolve, and the next review
  decides

### Requirement: Every finding is a conversation on the pull request
The review SHALL post each finding as an inline comment, which opens a conversation, on the lines it's about. A
finding that isn't about particular lines SHALL go on the line closest to what it concerns, so that every finding,
whatever its tier, is a conversation that must be resolved before the merge.

#### Scenario: A finding about the change as a whole
- **WHEN** the review finds that a ticked task has nothing behind it in the diff
- **THEN** it posts the finding as a conversation on the task's line in `tasks.md`

#### Scenario: Nothing found
- **WHEN** the review finds nothing
- **THEN** it opens no conversation, and its summary says so

### Requirement: The review reads its earlier conversations on each run
Before Claude starts, a review run SHALL write the pull request's review conversations to a file in the workspace:
each one's state, its comments and their authors. Claude SHALL read it, SHALL NOT post again a finding an open
conversation already holds, and SHALL say in its summary what became of each earlier finding.

#### Scenario: A finding that's still there
- **WHEN** the review runs again after a push that didn't address an open finding
- **THEN** it doesn't post that finding a second time, and its summary lists it as still open

#### Scenario: A nit resolved without a fix
- **WHEN** the author resolved a nit, and the review now sees it's a real problem
- **THEN** it posts a new must-fix on the same lines, saying why

#### Scenario: The conversations can't be read
- **WHEN** reading the pull request's conversations fails
- **THEN** the run fails before Claude starts, saying so, and no conversation is resolved

### Requirement: The review resolves its own must-fixes once addressed, and its nits once fixed
A review run SHALL resolve an open conversation only when Claude names it, and only when the review App opened it and
its tier is must-fix or nit. Claude SHALL name a must-fix whose problem is gone from the diff or whose author's reply
settles it, and a nit only when its problem is gone from the diff. A fixed step, in a job of its own after the review,
SHALL resolve them. Claude's tools SHALL NOT grow.

#### Scenario: A must-fix is fixed
- **WHEN** the author pushes a fix for a must-fix and the next review no longer sees the problem
- **THEN** that run resolves the conversation, and the summary says it was fixed

#### Scenario: A nit is fixed
- **WHEN** the author pushes a fix for a nit the review opened, leaves the conversation open, and the review of that
  push no longer sees the problem
- **THEN** that run resolves the conversation, and the summary says it was fixed

#### Scenario: A nit answered without a fix
- **WHEN** the author replies to a nit that it isn't worth fixing, and pushes nothing that fixes it
- **THEN** no review run resolves it, and the conversation stays open for the author to resolve

#### Scenario: The author resolves a nit first
- **WHEN** the author resolves a nit before the next review runs
- **THEN** the review leaves it resolved, and the summary says the author resolved it

#### Scenario: The author disagrees
- **WHEN** the author replies to a must-fix with a reason, and the next review still sees a problem
- **THEN** the conversation stays open, and the summary says it's disputed and needs the owner

#### Scenario: A decision
- **WHEN** a conversation is labelled decision
- **THEN** no review run resolves it, whatever the replies say or the diff shows

#### Scenario: Claude names a conversation it may not resolve
- **WHEN** Claude names a decision, an unlabelled conversation, a person's conversation, or one that doesn't exist on
  the pull request
- **THEN** the step resolves none of those, and names each one it skipped in the run's log

#### Scenario: The resolving step is widened
- **WHEN** a change lets the step resolve another author's conversation, a decision or an unlabelled conversation,
  gives Claude a tool that sends GraphQL, or asks the App for more than it holds
- **THEN** `scripts/check.py` fails, naming what changed

### Requirement: A check reports whether the review of a pull request's head completed
Each run of the review workflow started by a pull request event SHALL report a check named `claude review completed`
on the pull request's head. It SHALL wait for the review and its resolving job, and pass only if both succeeded. If
either, or the gate before them, failed or was cancelled, it SHALL fail, and its message SHALL name the run to re-run
with `gh run rerun <id>`.

#### Scenario: The review completes
- **WHEN** a push starts a review, and the review and its resolving job succeed
- **THEN** `claude review completed` passes on that head

#### Scenario: The review is still running
- **WHEN** a review of the head is running
- **THEN** `claude review completed` hasn't passed yet, and the pull request can't merge

#### Scenario: The last review is cancelled
- **WHEN** the last run to review a head is cancelled, with no run after it
- **THEN** `claude review completed` fails on the head, naming the run to re-run, and the pull request can't merge

#### Scenario: The review fails
- **WHEN** the review job fails
- **THEN** `claude review completed` fails, and its message says `gh run rerun <id>` with that run's ID

#### Scenario: The gate fails
- **WHEN** the gate job of a pull request event's run fails or is cancelled
- **THEN** `claude review completed` fails in that run, naming the run to re-run

### Requirement: The newest pull request event's run decides the check
The `claude review completed` that counts for a pull request SHALL be the one from the newest run started by a pull
request event on its head. A cancelled or failed review followed by such a run, or a re-run, that completes SHALL
pass.

#### Scenario: A re-run completes
- **WHEN** a cancelled review run is re-run with `gh run rerun <id>` and its review completes
- **THEN** the pull request's `claude review completed` passes, though the cancelled attempt's failure is still listed

#### Scenario: A newer run on the same head
- **WHEN** the pull request is reopened while its last review on the same head had failed, and the new run's review
  completes
- **THEN** the pull request's `claude review completed` passes

### Requirement: A comment's run doesn't change the check
A run started by a review comment SHALL NOT report `claude review completed`, and SHALL NOT change whether it passes:
the check stays as the newest pull request event's run left it. A reply's review that completes SHALL NOT pass a check
whose last pull request review was cancelled; that run is re-run instead.

#### Scenario: The review's own comments after a cancelled review
- **WHEN** the last review of a head was cancelled, and a bot's comment then starts a run that reviews nothing
- **THEN** `claude review completed` still fails, naming the cancelled run

#### Scenario: A reply cancels a push's review
- **WHEN** a reply to a must-fix starts a review that cancels the push's review still running, and the reply's
  review completes
- **THEN** `claude review completed` still fails, naming the push's run, and re-running that run, which judges the
  reply too, passes it

#### Scenario: A reply after a completed review
- **WHEN** the last review of a head completed, and a person then replies to a nit or a must-fix
- **THEN** `claude review completed` still passes

### Requirement: A pull request that isn't reviewed by design isn't held by the check
`claude review completed` SHALL pass on a pull request that isn't reviewed by design: one opened by a bot, including
Dependabot's and release-please's, or from a fork. It SHALL be skipped on a merge group, which counts as passed, so the
merge queue isn't held up.

#### Scenario: A Dependabot pull request
- **WHEN** Dependabot opens a pull request
- **THEN** the review is skipped and `claude review completed` passes

#### Scenario: A release pull request
- **WHEN** `troupe-run-release[bot]` opens or updates troupe's release pull request
- **THEN** the review is skipped and `claude review completed` passes

#### Scenario: A fork's pull request
- **WHEN** an outside contributor opens a pull request from a fork
- **THEN** the review is skipped, no secret is used, and `claude review completed` passes

#### Scenario: The merge queue
- **WHEN** the merge queue builds a merge group
- **THEN** `claude review completed` reports as skipped on the group's commit, and the queue isn't held up waiting
  for it

### Requirement: The changed files and their diffs are listed before the review starts
Before Claude starts, a review run SHALL write each changed file's diff into the workspace, made from the checked-out
commit, and a list of what must be read: an added file whole; a modified or renamed file whole, as it is now, and its
diff; a deleted file's diff. A path the review's action restores from the base SHALL be read as its copy of the pull
request's version. Each target SHALL list the Reads that cover it. Binary files and a declared skip list need nothing.

#### Scenario: A large pull request
- **WHEN** a pull request adds 9,000 lines across 114 files
- **THEN** each of its changed text files has its whole diff in the workspace, none cut short, and the list names
  each file and diff to read

#### Scenario: A modified file
- **WHEN** a pull request changes one function in a 600-line module
- **THEN** the list names the whole module and its diff

#### Scenario: A pull request that grows CLAUDE.md
- **WHEN** a pull request adds two lines to `CLAUDE.md`, which the action puts back from the base before Claude starts
- **THEN** the list names the action's copy of the pull request's `CLAUDE.md` and counts the pull request's lines

#### Scenario: A long file
- **WHEN** a pull request adds a 60 KB file
- **THEN** its target lists consecutive Reads that cover every line, each small enough that Read returns it whole

#### Scenario: A deleted file
- **WHEN** a pull request deletes a module
- **THEN** the list names its diff, which holds every line that was removed

#### Scenario: A lockfile
- **WHEN** a pull request changes `uv.lock`
- **THEN** the list needs nothing read for it, and says it's on the skip list

#### Scenario: Attributes that mark code binary
- **WHEN** a pull request adds a `.gitattributes` with `*.py -diff` and changes a `.py` file
- **THEN** that file's targets are listed as for any text file

#### Scenario: The diff can't be made
- **WHEN** the diff can't be made from the checkout
- **THEN** the run fails before Claude starts, saying so

### Requirement: The review reads everything listed, and the uses of what changed
The prompt SHALL tell each session to read everything on its own list in full with Read before it gives its summary,
and SHALL say that a review that hasn't is not a clean one. It SHALL tell the session to search for the uses of each
changed or removed name and read them. The session's summary SHALL say what it read, and name each file on its list
it didn't read in full. Claude's tools SHALL NOT grow.

#### Scenario: The prompt
- **WHEN** this repository's tests read the review's prompt
- **THEN** they fail if it doesn't name the session's list, doesn't tell the session to read everything on it,
  doesn't ask for the uses of changed names to be read, or doesn't ask the summary to name each file on the list not
  read in full

#### Scenario: A part's prompt
- **WHEN** the second of three parts' sessions starts
- **THEN** its prompt names its own list, says other sessions read the rest, and doesn't ask it to do the
  whole-pull-request checks

#### Scenario: A follow-up's prompt
- **WHEN** a follow-up session starts
- **THEN** its prompt names only the files left unread, and says an earlier session didn't read them

### Requirement: The review's coverage is measured from its tool calls
After each session, a step SHALL work out what the session read, from the action's record of its tool calls, never
from anything Claude wrote. A listed file SHALL count as read in full only when Read calls that succeeded, in one or
more of the review's sessions, together cover every line of everything listed for it. It SHALL count as read in part
when they cover some, and as not read otherwise. The run's summary SHALL list each file's coverage.

#### Scenario: Everything read
- **WHEN** the session's Read calls cover every line of every listed file and diff
- **THEN** the run's summary lists every file as read in full

#### Scenario: Part of a file read
- **WHEN** an added file is 3,000 lines and the session read lines 1 to 2,000 of it
- **THEN** the run's summary lists that file as read in part

#### Scenario: The diff read, but not the file
- **WHEN** the session read a modified file's whole diff but none of the file itself
- **THEN** the run's summary lists that file as read in part

#### Scenario: A file read across two sessions
- **WHEN** a part's session read a modified file's diff, and the follow-up session read the file itself
- **THEN** the run's summary lists that file as read in full

#### Scenario: The summary claims more than was read
- **WHEN** Claude's summary says it read every file, but the session made no Read call on one of them
- **THEN** that file is listed as not read

#### Scenario: A Read that failed
- **WHEN** a Read call on a listed file returned an error
- **THEN** it counts for nothing

#### Scenario: The record can't be read
- **WHEN** the action left no record of a session's tool calls, or one that can't be parsed
- **THEN** every file on that session's list counts as not read by it, so the follow-up rounds read its source and
  test files again

### Requirement: Call sites are reported, not gated
The run's summary SHALL also list, from the same record, the searches the session made and the files it read that
weren't changed, so a reader can see whether it looked at the uses of what changed. Whether it did SHALL NOT change
whether `claude review completed` passes.

#### Scenario: A review that looked at callers
- **WHEN** the session searched for a changed function's name and read two unchanged files that call it
- **THEN** the run's summary lists the search and the two files

#### Scenario: A review that didn't
- **WHEN** the session read everything listed but searched for nothing
- **THEN** the run's summary says it made no search and read no unchanged file, and the check doesn't fail for that

### Requirement: The review's turn budget scales with the reading needed
Each session's turn limit SHALL be a base plus an amount for each Read call its own list needs, at the Read tool's
measured size per call, up to a declared cap. The review jobs' timeout SHALL be long enough for the cap. A session
that runs out of turns or time SHALL leave its unread source and test files to the follow-up rounds, and SHALL fail
`claude review completed` if they're still unread after it.

#### Scenario: A small pull request
- **WHEN** a pull request lists one modified 300-line file
- **THEN** the session's turn limit is the base plus two Reads' worth: the file and its diff

#### Scenario: A part
- **WHEN** a part's list needs 40 Reads, and the whole pull request needs 130
- **THEN** that session's turn limit is the base plus 40 Reads' worth

#### Scenario: A pull request past the cap
- **WHEN** a part's list needs more Reads than the cap allows turns for, and its session doesn't read them all
- **THEN** the follow-up rounds take the source and test files it left, and `claude review completed` fails, naming
  any still unread after them

#### Scenario: A session that runs out of turns
- **WHEN** a part's session runs out of turns with two source files unread
- **THEN** the follow-up session reads them, and the check passes if it does

### Requirement: The review's model is a declared variable
The review SHALL run on the model named by the Actions variable `CLAUDE_REVIEW_MODEL`. OpenTofu SHALL set it on
troupe, infrastructure and website from one declared value. A run where it's unset, or isn't a Claude model name,
SHALL fail before Claude starts, naming the variable.

#### Scenario: The model is changed
- **WHEN** the declared value is changed and the plan applied
- **THEN** the next review in each of the three repositories runs on the new model, with no change to the workflow

#### Scenario: The variable is unset
- **WHEN** a review runs in a repository without `CLAUDE_REVIEW_MODEL`
- **THEN** the review fails before Claude starts, naming the variable, and `claude review completed` fails

#### Scenario: The variable holds something else
- **WHEN** `CLAUDE_REVIEW_MODEL` holds a value with a space or a `--` flag
- **THEN** the review fails before Claude starts, naming the variable, and the value never reaches Claude's arguments

### Requirement: One declared list decides which changed files are source and test
Before any session starts, the plan step SHALL sort each listed file with a line to read into source and test, prose
or data, from one declared list. Prose is Markdown, plain text, SVG, licence files and anything under `openspec/`.
Data is JSON, recorded streams and tables, and files with no suffix in a `fixtures/` folder, except declared
configuration. Every other file counts as source and test, kinds the list doesn't name included. The run's summary
SHALL show each file's kind.

#### Scenario: A module and its tests
- **WHEN** a pull request changes `src/troupe_runner_ollama/conversation.py` and `tests/test_ollama_conversation.py`
- **THEN** both count as source and test

#### Scenario: Fixtures and recorded streams
- **WHEN** a pull request changes `fixtures/ollama/thinking/events.json`, a `.jsonl` recording elsewhere, and
  `fixtures/claude/stream-error`, a recorded stream with no suffix, and test code names each of them or its folder
- **THEN** each is data

#### Scenario: JSON that configures something
- **WHEN** a pull request changes `package.json`, `tsconfig.base.json`, `tofu/required-checks.json` and
  `.github/dependabot.json`
- **THEN** each counts as source and test

#### Scenario: Code in a fixtures folder
- **WHEN** a pull request changes `tests/fixtures/conftest.py`
- **THEN** it counts as source and test

#### Scenario: Prose and licences
- **WHEN** a pull request changes `README.md`, `contributing/runners.md`, `LICENSE` and
  `openspec/changes/x/.openspec.yaml`
- **THEN** each is prose

#### Scenario: A workflow or a kind the list doesn't name
- **WHEN** a pull request changes `.github/workflows/ci.yml` or a `.astro` page
- **THEN** each counts as source and test

#### Scenario: An empty file
- **WHEN** a pull request adds an empty `__init__.py`, which has no line to read
- **THEN** it has no kind, so reading it doesn't count towards the check

#### Scenario: Skip-listed and binary files
- **WHEN** a pull request changes `uv.lock` and a PNG
- **THEN** neither has a kind, since neither needs anything read

#### Scenario: The run's summary
- **WHEN** a review run finishes
- **THEN** its summary's table says, for each file, its kind and how it was read, and how many source and test files
  were read in full

#### Scenario: The list is changed
- **WHEN** a change edits the declared list, or the step's script, without moving the test's pin
- **THEN** `scripts/check.py` fails, naming the step whose script isn't the one pinned

### Requirement: Source and test files are split into parts, each read by its own session
Before any session starts, a review run SHALL split the changed source and test files into parts of at most a declared
number of Reads, keeping each file's targets in one part and files of one folder together, up to a declared number of
parts. Each part SHALL be reviewed by its own session. The first part SHALL also carry the prose and the
whole-pull-request checks. A pull request whose source and test files fit in one part SHALL get one session.

#### Scenario: A small pull request
- **WHEN** a pull request changes three Python files and a Markdown file, needing 8 Reads
- **THEN** one session reviews it, reading the three files and the Markdown file, and doing every check

#### Scenario: A runner pull request
- **WHEN** a pull request's source and test files need three times the declared Reads per part
- **THEN** three sessions run, each with its own list, and together the lists hold every source and test file once

#### Scenario: More than the parts allow
- **WHEN** a pull request's source and test files need more Reads than the declared parts times the Reads per part
- **THEN** the declared number of sessions runs, each part larger than the declared Reads, and no file is left off

#### Scenario: Nothing but prose and data
- **WHEN** a pull request changes only Markdown, files under `openspec/` and fixtures
- **THEN** one session reviews it, with the prose to read and no source or test file

#### Scenario: A newer push
- **WHEN** a member pushes while a review's parts are running
- **THEN** every session of the earlier review that shares a part number with the new review is cancelled

### Requirement: Source and test files left unread are read by a follow-up session
After the parts' sessions finish, the run SHALL measure what they read together. If any changed source or test file
wasn't read in full, the run SHALL start a round of follow-up sessions, split as the parts are, over only those
files, each told that an earlier session left them unread. It SHALL do so again after that round, and SHALL start
no more than two follow-up rounds.

#### Scenario: A session that stopped early
- **WHEN** a review's only session reads 7 of 39 files in full and none of its 16 source and test files, then ends
  by itself, as on troupe#325
- **THEN** a follow-up session starts over the 16 source and test files, and the check judges what both read

#### Scenario: Every source and test file read
- **WHEN** the parts' sessions read every source and test file in full
- **THEN** no follow-up session starts

#### Scenario: Prose left unread
- **WHEN** the parts' sessions read every source and test file but left a Markdown file unread
- **THEN** no follow-up session starts, and the check warns, naming the Markdown file

#### Scenario: The first follow-up stops early too
- **WHEN** the first follow-up session leaves two source files unread
- **THEN** a second follow-up session starts over those two files

#### Scenario: The second follow-up stops early too
- **WHEN** the second follow-up session leaves a source file unread
- **THEN** no third follow-up round starts, and `claude review completed` fails, naming that file

### Requirement: A review's sessions report as one review
Each session SHALL post its findings as inline comments, and SHALL give back a summary of its part in its structured
output, never as a comment of its own. After every session, the resolving job SHALL post one top-level comment that
holds every session's summary and the measured coverage. Claude's tools SHALL NOT include posting a top-level comment.

#### Scenario: Three parts
- **WHEN** a review runs three sessions and a follow-up session
- **THEN** the pull request gets one top-level comment from the review App, with each session's summary and what was
  read, and each finding as its own inline conversation

#### Scenario: A session's summary is missing
- **WHEN** one session's structured output has no summary
- **THEN** the comment says that part's summary is missing, and the check still judges coverage from its tool calls

#### Scenario: The tools are widened
- **WHEN** a change gives Claude `gh pr comment` again, or a tool that posts a top-level comment
- **THEN** `scripts/check.py` fails, naming the tool

### Requirement: A session resolves or re-tiers only the conversations of its part
A session's request to resolve or re-tier a conversation SHALL be carried out only when the conversation is on a file
in that session's list. Conversations on a file in no session's list, or on no file, SHALL be the first part's. The
check SHALL be made against the conversations read before the sessions started, never against what Claude says.

#### Scenario: A finding on another part's file
- **WHEN** the second part's session names a must-fix on a file in the first part's list
- **THEN** the resolving job leaves it open, and names it in the run's log as outside that session's part

#### Scenario: A finding on prose
- **WHEN** the first part's session names a nit on `README.md`, whose problem a push fixed
- **THEN** the resolving job resolves it

### Requirement: The check fails unless every changed source and test file was read in full
`claude review completed` SHALL fail when a changed source or test file wasn't read in full by any of the review's
sessions, naming each one, or when coverage is unknown, missing or malformed. Prose left unread SHALL NOT fail it: the
check SHALL pass with one warning naming each. Data files SHALL be named as left to their tests. A failure SHALL say
how to get a review that reads the code.

#### Scenario: troupe#325's runs
- **WHEN** the sessions together read 10 of 16 changed source and test files in full
- **THEN** `claude review completed` fails, naming the 6 files

#### Scenario: A review that read no code
- **WHEN** a review's sessions read only the task list and the Markdown files
- **THEN** `claude review completed` fails, naming every changed source and test file

#### Scenario: Every source and test file read, prose skipped
- **WHEN** the sessions read every source and test file in full and left two Markdown files unread
- **THEN** `claude review completed` passes, with one warning naming the two Markdown files

#### Scenario: Data left to its tests
- **WHEN** a pull request adds 40 fixture files that tests name, and the sessions read every source and test file
- **THEN** `claude review completed` passes, and the run's summary lists the 40 files as data left to its tests

#### Scenario: No source or test file changed
- **WHEN** a pull request changes only Markdown and files under `openspec/`
- **THEN** `claude review completed` passes once the review completes, with a warning naming any file not read

#### Scenario: Coverage unknown
- **WHEN** a part's record of its tool calls is missing or can't be read, and a source or test file it was to read is
  still not read in full after the follow-up rounds
- **THEN** `claude review completed` fails, saying coverage couldn't be measured, and naming the part

#### Scenario: A missing record that the follow-ups made up for
- **WHEN** the second part's record is missing, and a follow-up session reads every source and test file on its list
- **THEN** `claude review completed` passes

#### Scenario: The lead session died
- **WHEN** a pull request changes only Markdown, and its one session fails having read none of the changed files and
  diffs listed, only `CLAUDE.md` or nothing at all, for example because the Claude token expired, so its action step
  fails without failing its job
- **THEN** `claude review completed` fails, saying coverage couldn't be measured and naming round 1 part 1

#### Scenario: The check is weakened
- **WHEN** a change lets the check pass with a source or test file unread, drops a part's record from the union, or
  reads Claude's structured output or summary to decide coverage
- **THEN** `scripts/check.py` fails, naming what changed

### Requirement: Data that nothing names is read as source and test
A file the list makes data SHALL stay data only when a tracked file that isn't data, outside the change's own
`openspec/` folder, names the data file's name or the name of the folder that holds it. Otherwise the plan step SHALL
count it as source and test, so it must be read in full. The run's summary SHALL say why.

#### Scenario: A fixture its test loads
- **WHEN** a pull request adds `fixtures/responses/refusal/replies.json`, and a test names `replies.json`
- **THEN** it's data, left to its tests

#### Scenario: A stray data file
- **WHEN** a pull request adds `notes/old-export.json`, and no tracked file that isn't data names `old-export.json`
  or `notes`
- **THEN** it counts as source and test, and the run's summary says nothing names it

#### Scenario: Named only by other data
- **WHEN** a JSON file's name appears only in another JSON file and in the change's proposal
- **THEN** it counts as source and test
