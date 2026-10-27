## ADDED Requirements

### Requirement: A merge group is re-checked as main is
For a merge group, the GitHub check SHALL judge the commits between the group's base on `main` and its head, as it
judges a push to `main`: commit messages, schema commit types, archived tasks, delivered files, strict OpenSpec
validation of every main spec and active change, and troupe's capability labels. The branch and description rules
SHALL NOT apply: each pull request in the group passed them.

#### Scenario: A queued pull request whose branch has a change
- **WHEN** a pull request from a branch with a matching OpenSpec change joins the merge queue, and its commits pass
  the git-level rules
- **THEN** the `guard` check passes on the queue's commit, although the queue's `gh-readonly-queue/main/...` branch
  matches no change

#### Scenario: A combination that fails strict validation
- **WHEN** two queued pull requests each pass alone, but together leave a main spec failing strict validation
- **THEN** the `guard` check fails under `openspec-strict` on the second one's queue commit, naming that spec

#### Scenario: A merge group the check can't read
- **WHEN** the check runs for a merge group whose event payload has no base or head commit
- **THEN** the check fails, naming the merge group, and says to re-run it and, if it fails again, to tell the owner

### Requirement: A merge queue's branch push isn't judged as a branch
A push to a merge queue's branch (`gh-readonly-queue/<base>/...`) SHALL NOT start the `guard` check: it is the one
push that "The rules are re-checked on GitHub" doesn't reach. Its commits are judged on the merge group instead, so
the check can't fail them for having no matching change.

#### Scenario: The queue creates its branch
- **WHEN** the merge queue pushes its `gh-readonly-queue/main/pr-<n>-<sha>` branch
- **THEN** no `guard` run starts for that push, and the merge group's own `guard` run reports on the commit
