# Spec Delta

## ADDED Requirements

### Requirement: Commit rules judge what the commit contains
The rules checked before a commit SHALL judge what that commit will contain: the checks-pass rule, including its
unstaged-changes test and the paths and declaration it reads; the archived-changes rule; and the delivered-file rule.
This holds when the contributor runs `git commit -a` or `git commit <path>`, as well as a plain commit of what's
staged.

#### Scenario: Committing all tracked edits
- **WHEN** a tracked file has an unstaged edit and the contributor runs `git commit -a`
- **THEN** the commit isn't refused for unstaged changes, and the check runs on what `-a` commits

#### Scenario: Committing named paths with other edits left out
- **WHEN** the contributor runs `git commit <path>` while another tracked file has an edit that commit leaves out
- **THEN** the commit is refused under `commit-checks` for that file's unstaged changes, as for a plain commit

#### Scenario: A declaration edit committed with -a
- **WHEN** `scripts/check-paths.toml` has an unstaged edit, and the contributor commits it with `git commit -a`
- **THEN** the full check runs, because the declaration is part of the commit

#### Scenario: An unticked archived change committed with -a
- **WHEN** an archived change's `tasks.md` is edited to leave a task unticked, and the edit is committed with
  `git commit -a`
- **THEN** the commit is refused, naming the change and the unticked task

#### Scenario: A delivered file committed with -a
- **WHEN** in a repository that receives the guard, a delivered file has an unstaged edit committed with
  `git commit -a`
- **THEN** the commit is refused under `delivered-file`, naming the file

### Requirement: A force-pushed branch is still judged on GitHub
When a push replaces a branch's tip with commits that don't descend from it, the GitHub check for that push SHALL
judge the branch's commits since it left `main`, as for a branch's first push, and say that it did so. It SHALL NOT
pass by judging no commits.

#### Scenario: A rebased branch is force-pushed
- **WHEN** a branch with commits on it is rebased onto a newer `main` and force-pushed, and one of its commits has a
  message that isn't a Conventional Commit
- **THEN** the GitHub check for that push fails under `commit-message`, naming the commit

#### Scenario: The run says where its range starts
- **WHEN** the GitHub check runs for a push whose replaced tip isn't in its clone
- **THEN** its output says the range starts where the branch left `main`, and why

#### Scenario: An ordinary push is unchanged
- **WHEN** a branch is pushed with new commits on top of its previous tip
- **THEN** the GitHub check judges only the commits after that tip
