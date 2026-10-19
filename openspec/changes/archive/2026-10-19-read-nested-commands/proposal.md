## Why

The guard takes each simple command's first word as its program, so a git or gh command anywhere else in a Bash
command reaches none of its rules (#94). On `main` (`82efe9f`) every one of these is allowed, while
`gh auth token` or `gh repo delete troupe-run/x --yes` on its own is refused as owner-only:

- command substitution: `out=$(gh repo delete troupe-run/x --yes)`, `echo "$(gh …)"`, `` x=`gh auth token` ``,
  `echo $(gh pr merge 1 --admin)`, nested `$(echo $(gh auth token))`, and process substitution `<(gh auth token)`;
- grouping and keywords: `(gh auth token)`, `{ gh auth token; }`, `if gh auth token; then …`, `for …; do gh …; done`,
  `until ! gh …`, `! gh …`, a function body `f(){ gh …; }`;
- wrappers: `time`, `env`, `command`, `nohup`, `timeout`, `xargs`, `sudo`;
- a shell inside the command: `bash -c "gh auth token"`, `eval "gh auth token"`;
- git too: `(git commit --no-verify -m 'fix: x')` and `x=$(git commit --no-verify …)` pass `skip-hooks`.

The hooks aren't a security boundary, but this is exactly the shortcut they exist to stop: an agent can run any
owner-only gh command, print the login's token into its context, or skip git's hooks, by wrapping the command. It was
found by accident (#90, task 4.4), when a loop's `out=$(gh $c ...)` went through. These forms are everyday agent
shapes, not tricks: of 20,612 Bash commands in earlier sessions, 1,135 hold a substitution that mentions git or gh,
1,646 run a command after `do`, 393 after `until`, and 96 inside `{ … }`.

The hook also covers the PowerShell tool, but reads its text as bash, so PowerShell's own forms go through:
`Invoke-Expression "gh auth token"`, `iex "gh auth token"`, `$t = $(gh auth token)`, `pwsh -Command "gh auth token"`,
`cmd /c gh auth token`, `Start-Process gh -ArgumentList "auth","token"` and `1..2 | ForEach-Object { gh auth token }`
are all allowed on `main`. The owner asked (2026-10-19) for PowerShell to be included.

The owner chose (2026-10-19) to fix all the forms in this one change, by reading what can be read and refusing the
rest: a git or gh command the guard finds but can't read is refused, never allowed.

## What Changes

- The guard reads every command a Bash command runs, not only each piece's first word: inside `$(...)`, backticks
  (in or out of double quotes, nested to any depth), `<(...)`/`>(...)`, `${…}` defaults, an expanding heredoc's body,
  subshells, `{ … }` groups, loop, conditional and function bodies, after `!`, `time` and the plain wrappers
  (`command`, `exec`, `env`, `nice`, `nohup`, `timeout`, zsh's `noglob` and `nocorrect`), in the string of
  `bash -c`/`sh -c`/`zsh -c` and `eval`, and in a script fed to a shell by a heredoc. Each command it finds is judged
  by every rule, with the same rule and message as when it's run on its own.
- A git or gh command the guard finds but can't read is refused under `command-unparseable`, with a message saying
  where it was and to run it on its own: one run by another program (`xargs`, `sudo`, `find -exec`, `docker`, or any
  program the guard doesn't know to treat it as data), a program named by an expansion (`$G auth token`) in a command
  that mentions git or gh, a shell reading its commands from a pipe or here-string, an alias for git or gh, and a
  substitution the reader can't follow (a `case` inside `$(...)`, or one nested too deep).
- A command run through the PowerShell tool is read with PowerShell's rules, not bash's: `$( )`, `@( )` and script
  blocks `{ }` are read, the backtick is an escape, the `&` and `.` call operators are skipped, and
  `Invoke-Expression`/`iex`, `pwsh`/`powershell -Command` (and `-EncodedCommand`, decoded) and `cmd /c` have their
  command strings read. What it can't read (`Start-Process`, `Start-Job`, a call operator on a variable) is refused as
  for bash.
- What stays the same: a command with no nesting gets the decision it gets today; a word that only names git or gh
  as data (`which gh`, `grep -n git x`, `echo gh`, `command -v gh`, `for c in gh git`) isn't refused; the inner `cat`
  of `--body "$(cat <<'EOF' … EOF)"` goes ahead and the outer `gh pr create` keeps #90's message; a quoted heredoc's
  body is still data; no nested command is ever granted.
- `docs/development-workflow.md`: the `command-unparseable` row, and a paragraph on which commands the guard reads.
- `scripts/guard.py` is delivered to troupe and website.

Out of scope, and said so in the docs: programs and scripts that run git or gh themselves (`bash script.sh`,
`uv run scripts/check.py`, `make`, Python's `subprocess`, a git alias starting with `!`), `source`/`.`, and deliberate
obfuscation that hides the program's name (`$'\x67h'`).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: two new requirements. "The rules reach every command a shell line runs" has scenarios for
  each form above and for what must not change. "A git or gh command the guard can't read is refused" covers the
  rest.

## Impact

- `scripts/guard.py`: one reader of a Bash command's text that returns every simple command it would run, replacing
  the first-word view `split_command` gives `shell_decisions`; `strip_heredocs` keeps each body and whether it
  expands; `_program` skips redirections, reserved words and the plain wrappers through one table; a table of
  programs that take git or gh as data; the `command-unparseable` message for what can't be read.
- `scripts/tests/test_guard_claude.py` (or a new `scripts/tests/test_guard_nested.py`): the issue's four commands and
  every form above, tests that pin today's decisions for commands without nesting (written and passing before the
  change), and a differential test against real bash, and zsh where it's installed, using stub `gh` and `git`
  programs that only record their arguments, and under `pwsh` where it's installed (CI's runners have it on all three
  OSes; this Mac doesn't). `shell_decisions` is told which tool ran the command.
- `docs/development-workflow.md`: the `command-unparseable` row and what the guard reads.
- Delivery: `scripts/guard.py` changes in place in **troupe and website** (`guard_targets` in
  `tofu/guard_delivery.tf`), after the owner approves the plan. Neither repository's declaration or hooks change.
- Agents: 13 earlier `xargs gh`/`xargs git` commands, one `docker run … git` and about 19 commands that name their
  program with a variable while mentioning git or gh would now be refused, and need rewriting as a plain git or gh
  command.
