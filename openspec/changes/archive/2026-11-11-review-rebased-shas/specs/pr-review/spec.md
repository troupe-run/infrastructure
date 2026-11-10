## ADDED Requirements

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
