## ADDED Requirements

### Requirement: The rules reach every command a shell line runs
In a Claude Code session, every rule for git and gh commands SHALL apply to each git or gh command a Bash command
would run, wherever it sits in that command, and SHALL decide it as it decides the same command run on its own: the
same rule, message and fix. A command that holds no nested command SHALL get the decision it got before.

#### Scenario: An owner-only command in a command substitution
- **WHEN** an agent runs any of `out=$(gh repo delete troupe-run/x --yes)`, `echo "$(gh repo delete troupe-run/x
  --yes)"`, ``x=`gh auth token` `` or `echo $(gh pr merge 1 --admin)`
- **THEN** the command is refused as `owner-only`, with the message `gh repo delete troupe-run/x --yes`,
  `gh auth token` or `gh pr merge 1 --admin` gets on its own

#### Scenario: Nested substitutions
- **WHEN** an agent runs a git or gh command that a rule refuses inside a substitution inside another substitution,
  such as `echo "$(echo $(gh auth token))"` or ``echo $(echo `gh auth token`)``
- **THEN** the command is refused, as the innermost command is on its own

#### Scenario: Process substitution and parameter defaults
- **WHEN** an agent runs `cat <(gh auth token)` or `echo "${T:-$(gh auth token)}"`
- **THEN** the command is refused as `owner-only`

#### Scenario: A heredoc the shell expands
- **WHEN** an agent runs `cat <<EOF` with a body line `$(gh auth token)`, its delimiter unquoted
- **THEN** the command is refused as `owner-only`

#### Scenario: A heredoc the shell leaves alone
- **WHEN** an agent runs `cat <<'EOF'` with a body line `$(gh auth token)`
- **THEN** the command goes ahead, since the shell doesn't run the body

#### Scenario: Subshells, groups, loops and conditions
- **WHEN** an agent runs a refused gh command inside `( … )`, `{ …; }`, after `if`, `then`, `else`, `while`,
  `until`, `do` or `!`, or in a function's body (`f(){ gh auth token; }`)
- **THEN** the command is refused, as the gh command is on its own

#### Scenario: Wrappers that run the command as written
- **WHEN** an agent runs a refused gh command after `time`, `command`, `exec`, `env` (with its assignments and
  options), `nice`, `nohup`, `timeout` with a duration, or zsh's `noglob` or `nocorrect`
- **THEN** the command is refused, as the gh command is on its own

#### Scenario: A shell's command string
- **WHEN** an agent runs `bash -c "gh auth token"`, `sh -c 'gh auth token'`, `zsh -c "gh auth token"` or
  `eval "gh auth token"`
- **THEN** the command is refused as `owner-only`

#### Scenario: A script fed to a shell by a heredoc
- **WHEN** an agent runs `bash <<'EOF'` with a body line `gh auth token`
- **THEN** the command is refused as `owner-only`, whatever the delimiter's quoting

#### Scenario: Git's hooks skipped from inside another command
- **WHEN** an agent runs `(git commit --no-verify -m 'fix: x')` or `x=$(git commit --no-verify -m 'fix: x')`
- **THEN** the command is refused as `skip-hooks`

#### Scenario: A pull request opened inside a substitution
- **WHEN** an agent runs `url=$(gh pr create --title t --body 'no closing line')` in the session's repository
- **THEN** the command is refused as `pr-closes-issue`

#### Scenario: Reads inside other commands
- **WHEN** an agent runs a command whose nested git and gh commands are all allowed, such as
  `git log $(git merge-base main HEAD)..HEAD`, `cd "$(git rev-parse --show-toplevel)"` or
  `for n in 1 2; do gh issue view $n; done`
- **THEN** the command goes ahead

#### Scenario: A description built by the shell
- **WHEN** an agent opens a pull request with `--body "$(cat <<'EOF' … EOF)"` whose text outside the substitution
  closes no issue
- **THEN** the request is refused as `pr-closes-issue` with the message for a description built by the shell, as
  before, and the `cat` inside it isn't refused

#### Scenario: Words that only name git or gh
- **WHEN** an agent runs a command that names git or gh only as data, such as `which gh git`, `command -v gh`,
  `type gh`, `echo gh`, `grep -n "git" notes.md` or `for c in gh git; do echo $c; done`
- **THEN** the command goes ahead

#### Scenario: A nested command is never granted
- **WHEN** an agent runs a granted gh command inside a substitution or a group, such as `n=$(gh issue view 1)`
- **THEN** the guard doesn't grant it, and Claude Code decides as it would without the guard

### Requirement: A git or gh command the guard can't read is refused
In a Claude Code session, a Bash command that would run git or gh in a way the guard can't read SHALL be refused,
never allowed, with a message that says the guardrails can't read it there and to run the git or gh command on its
own. A command the guard can't read that never mentions git or gh SHALL go ahead.

#### Scenario: Run by another program
- **WHEN** an agent runs git or gh through a program that isn't known to run its arguments as written, such as
  `echo 1 | xargs gh issue view`, `sudo gh auth status`, `find . -name x -exec git add {} \;` or
  `docker run img git status`
- **THEN** the command is refused as `command-unparseable`, and the message says to run the git or gh command on its
  own

#### Scenario: A program named by an expansion
- **WHEN** an agent runs a command whose program is a shell expansion and that mentions git or gh, such as
  `G=gh; $G auth token`
- **THEN** the command is refused as `command-unparseable`

#### Scenario: A shell reading its commands from a pipe
- **WHEN** an agent runs `echo 'gh auth token' | bash`, or `bash <<< 'gh auth token'`
- **THEN** the command is refused as `command-unparseable`

#### Scenario: An alias for git or gh
- **WHEN** an agent runs `alias g=gh` in a command
- **THEN** the command is refused as `command-unparseable`

#### Scenario: A substitution the guard can't follow
- **WHEN** an agent runs a substitution whose end the guard can't find for certain, such as one holding a `case`
  statement (`echo $(case x in a) gh auth token;; esac)`), or one with no end
- **THEN** the command is refused as `command-unparseable` if it mentions git or gh, and goes ahead if it doesn't

#### Scenario: A wrapper option the guard doesn't know
- **WHEN** an agent runs gh after a known wrapper with an option the guard doesn't know, such as `env -S 'gh auth
  token'`
- **THEN** the command is refused as `command-unparseable`
