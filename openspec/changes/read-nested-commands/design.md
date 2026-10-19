## Context

See proposal.md for why. The current state of `scripts/guard.py` (`82efe9f`):

- `shell_decisions` calls `split_command`, then runs `guard_tamper`, `skip_hooks`, `pr_closes_issue` and
  `gh_decision` on each simple command it returns. Every rule but `guard_tamper` starts with `_program(words)` and
  returns ALLOW unless the program is `git` or `gh`.
- `split_command` drops heredoc bodies (`strip_heredocs`), splits on `&& || ; | & \n` outside quotes, and gives each
  piece to `shlex.split(posix=True)`. It doesn't look inside `$(...)` or backticks: their text stays in an outer word
  (`out=$(gh`, `"$(gh … )"` as one word), and an operator inside `$(...)` splits the outer command in the wrong place.
  `(`, `)`, `{` and `}` aren't operators, so `(gh` is a program.
- `_program` skips leading `VAR=value` words and takes the next word's last path component, lowercased, without
  `.exe`. It doesn't skip redirections, reserved words or wrappers.
- `strip_heredocs` recognises `<<WORD`, `<<'WORD'` and `<<"WORD"` (and `<<-`), not `<<\WORD`, and keeps no record of
  a body or of whether it expands.
- `command-unparseable` is used only when `split_command` raises (unbalanced quotes) and the text matches
  `\b(git|gh)\b`. Unparseable text that never mentions git or gh is allowed.
- `pr_closes_issue` needs the outer `--body` word to keep its `$(...)` text, so that `SHELL_EXPANSION` can give
  #90's message (refuse-substituted-pr-body D1, D2). `grantable` grants only text with no shell syntax at all
  (`_plain_shell_text`), so nothing nested is granted today.
- The Bash tool runs the user's shell: zsh on this Mac, bash on Linux, Git Bash on Windows. All three read `$(...)`,
  backticks, `<(...)`, subshells, groups and the reserved words the same way. zsh adds `=(...)`, `noglob`,
  `nocorrect` and `repeat N`.
- Survey (2026-10-19) of the 20,612 Bash commands in this machine's earlier troupe sessions: 1,135 hold a
  substitution or backticks and mention git or gh; leading `do` 1,646, `for` 1,185, `until` 393, `bash` 341 (330 of
  them run a script file, 7 `-c`, 4 a heredoc), `xargs` 109 (11 `xargs gh`, 2 `xargs git`), `env` 100, `{` 96,
  `time` 82, `if`/`then`/`else` 139, `( … )` about 200, `nohup` 36, `!` 21, `eval` 4, `timeout` 2. A git or gh word
  among another program's arguments, once the reserved words and plain wrappers are read: `xargs` 13, `which` 2,
  `docker` 1, `gitleaks` 1, `grep` 1. A program given by an expansion in a command that mentions git or gh: 19.
  The survey script is in this session's scratchpad. It's evidence, not part of the change.

## Goals / Non-Goals

**Goals:**

- One reader that turns a Bash command's text into every simple command it would run, which `shell_decisions` judges
  with the rules unchanged.
- Fail closed: whatever the reader can't follow, it says so, and a command that mentions git or gh is then refused.
- Pin today's decisions for commands without nesting before changing anything, and check the reader against real
  shells, not just against itself.

**Non-Goals:**

- Commands run by programs and scripts (`bash script.sh`, `uv run scripts/check.py`, `make`, `subprocess`, a git
  alias starting with `!`, `source`/`.`): the guard reads the command line, not what the programs it names do. These
  were out of reach before and stay out of reach.
- Deliberate obfuscation of the program's name, such as `$'\x67h'`. (`g\h` and `g""h` are read already, since quotes
  and escapes are removed.) The hooks aren't a security boundary, and the survey found no command like this.
- A full shell grammar. The reader knows the constructs listed in D2 and D3 and treats anything else that could
  hide a command as unreadable (D5).
- Changing any rule's own logic or message, or what is granted.

## Decisions

### D1. One reader returns every command; outer words stay as written

A new `commands_run(command) -> list[list[str]]` returns the simple commands in the order the text holds them: each
outer command first, then the commands nested in it, recursively. `shell_decisions` runs the rules over that list
instead of `split_command`'s. An outer command keeps each substitution's text in its word (`x=$(gh auth token)` is
still one word), so `pr_closes_issue` still sees `$(...)` in a `--body` and gives #90's message, while the commands
inside are judged as commands of their own.

`split_command` stays as the outer split (its tests keep their meaning), changed only so that an operator inside a
substitution, or inside `( … )`, no longer splits the outer command, and `(`, `)` become operators (D3).

Alternative: refuse every nested git or gh command (issue #94's option 2). Rejected by the owner: it refuses
everyday reads such as `cd "$(git rev-parse --show-toplevel)"`, 1,135 commands in the survey. Alternative: read
everything and refuse nothing new (option 1). Rejected: any gap in the reader would then fail open.

### D2. Finding nested commands: a scanner that tracks quotes and nesting

One character scanner over the text (after heredoc bodies are set aside, D4) tracks the quoting it is in and finds
each nested command's text:

| Opens | Where | Ends | Inside is |
|---|---|---|---|
| `$(` (not `$((`) | unquoted, or in `"…"` | the matching `)`, quotes and nesting tracked | a command, read recursively |
| `` ` `` | unquoted, or in `"…"` | the next unescaped `` ` `` | a command, after `` \` ``, `\\` and `\$` are unescaped |
| `<(`, `>(` | unquoted | the matching `)` | a command |
| `=(` at a word's start | unquoted (zsh) | the matching `)` | a command |
| `$((` | unquoted, or in `"…"` | the matching `))` | arithmetic: scanned for substitutions, not a command |
| `${` | unquoted, or in `"…"` | the matching `}` | a parameter expansion: scanned for substitutions |
| `'…'` | unquoted | the next `'` | nothing (literal) |

A nested command's end is found by the same scanner run over its text, so a `)` in quotes doesn't end it. If the
text runs out before the end, the scanner raises, which is unreadable (D5). A `case` statement inside `$(...)` makes
the end uncertain (a pattern's `)` ends the substitution for this scanner, though not for the shell), so a `case` at
command position inside a substitution is unreadable too. Recursion is capped at 16 levels, beyond which the text is
unreadable.

### D3. Finding the program: operators, reserved words, wrappers and data

- **Operators.** Outside quotes and outside substitutions, `( )` join `&& || ; | & \n` as places to split, except
  `(` straight after `$`, `<`, `>` or a word-start `=` (D2), and `NAME=(…)`, an array assignment whose words are data
  (scanned for substitutions only).
- **Before the program**, `_program` skips: `VAR=value` words (as now); redirections (`>f`, `2>f`, `<f`, `>>f`,
  `&>f`, `>&2`, and a bare operator followed by its target word); the reserved words `!`, `{`, `}`, `if`, `then`,
  `elif`, `else`, `while`, `until`, `do`, `time` (with `-p`), and `function NAME`; and the plain wrappers below.
- **Plain wrappers** run the rest of their words as a command, as written. They live in one table,
  `SHELL_WRAPPERS`, mapping each to the options it accepts and which of them take a value:

  | Wrapper | Accepted options |
  |---|---|
  | `command`, `builtin` | `-p`; `-v` or `-V` make it data (it only prints) |
  | `exec` | `-c`, `-l`, `-a NAME` |
  | `env` | `-i`, `-`, `-u NAME`, `-C DIR`, `--`, then `VAR=value` words |
  | `nice` | `-n N`, `-N` |
  | `nohup`, `noglob`, `nocorrect` | none |
  | `timeout` | `-s SIG`, `-k DUR`, `--foreground`, `--preserve-status`, `-v`, then a duration |

  An option the table doesn't list (`env -S`, `nice --adjustment=…`) makes the command unreadable (D5), so a wrong
  guess about a wrapper's options can't skip past a git or gh word.
- **Shells and `eval`.** `bash`, `sh`, `zsh`, `dash` and `ksh` with `-c`: the word after `-c` (after any other
  single-letter options, or `-o NAME`) is read as a command, recursively. `eval`'s words, joined by spaces, are read
  as a command. A shell given a script file runs code the guard can't see, a non-goal, so it's left alone. A shell
  with no operand, or with `-s`, reads its commands from stdin: if the same piece has a heredoc, that body is read as
  commands whatever its quoting (D4); a pipe or a here-string (`<<<`) is unreadable (D5).
- **Data.** Words after these programs only name things: `echo`, `printf`, `which`, `type`, `whereis`, `man`,
  `grep`, `egrep`, `fgrep`, `rg`, `command -v`/`-V`, and the headers `for NAME in …`, `select NAME in …` and
  `case … in`, and the closers `done`, `fi`, `esac`. One table, `DATA_PROGRAMS`, holds them, with a comment that
  says what earns a place (the program never runs a word it's given). The list is from the survey; anything else is
  added by pull request, as for the gh allow-list.

Alternative: skip every unknown leading word until one is `git` or `gh`. Rejected: it would read `sudo gh x` or
`xargs gh x` as `gh x`, which isn't what runs (`xargs` adds words; `sudo` runs as another user).

### D4. Heredocs: keep the body and whether it expands

`strip_heredocs` still takes bodies out before splitting, so a body is never read as shell words. It now also
returns each body with its piece and whether its delimiter was quoted, and recognises `<<\WORD` and a partly quoted
`<<E"OF"` as quoted (both turn expansion off, as in bash and zsh). A body whose delimiter isn't quoted is scanned
for substitutions as if in double quotes (D2), and each one is read. A quoted body is data, unless its piece runs a
shell that reads stdin (D3), where the body is read as commands.

### D5. What can't be read is refused under `command-unparseable`

The reader marks a piece unreadable when: D2's scanner can't find an end or meets a `case` in a substitution or the
depth cap; a wrapper has an option the table doesn't know; a shell reads a pipe or a here-string; the program is an
expansion (a word starting with `$` or holding a backtick, after quotes are removed); or `alias` defines a name.
A piece is also unreadable when a word naming git or gh (its last path component, lowercased, without `.exe`, is
`git` or `gh`) is among the arguments of a program that isn't `git`, `gh`, a data program or a wrapper the reader
followed. That last case is the fail-closed default for every program the guard doesn't know: `xargs`, `sudo`,
`doas`, `find -exec`, `watch`, `parallel`, `docker`, zsh's `repeat`, and so on.

An unreadable piece is refused only when the whole command's text matches `\b(git|gh)\b`, the test unbalanced quotes
already use, so an odd command that has nothing to do with git or gh still goes ahead. The rule stays
`command-unparseable` (one rule for "the guardrails can't check this", rather than a new name), with a message that
names what it couldn't read: "this command runs git or gh where the guardrails can't read it (<reason>)." and the
fix "Run the git or gh command on its own, as a separate Bash command, not through another program, a variable or a
pipe into a shell." Unbalanced quotes keep today's message.

`guard_tamper` runs over every command the reader finds, nested ones included, and over the raw text when the text
can't be read, as now.

### D6. Evidence: pin, compare with main, compare with real shells

- **Pin first.** Before the reader changes, a hypothesis property test generates commands from plain pieces (git and
  gh commands from the rules' own tests, `echo`, `ls`, quoted words with operators inside, heredocs with quoted
  delimiters) joined by operators, with no nesting, and asserts `shell_decisions` gives what it gives on `main`
  (the expected decisions come from the pieces judged one at a time). It must pass on `main` before the change, and
  after. This is the learned rule on differential tests: what must stay the same is checked, not assumed.
- **Compare with main over the survey.** A one-off script in the scratchpad runs `main`'s `shell_decisions` and this
  branch's over the 20,612 surveyed commands and lists every command whose decisions differ. Each difference is
  either one this design meant (a nested command now read or refused) or a regression to fix. The counts go into
  tasks.md. The commands themselves stay in the scratchpad (they are session history).
- **Compare with real shells.** A test puts stub `gh` and `git` programs first on `PATH` that only append their
  arguments to a log, runs a table of commands under `bash` (and `zsh` where it's installed), and asserts that the
  git and gh commands the reader finds are the ones the shell ran. A hypothesis variant composes nestings from D2's
  and D3's forms. The commands only run stubs, in a temporary directory; no real git or gh runs. It is skipped on a
  platform with no `bash`, and runs in CI on Linux, macOS and Windows (Git Bash). Forms where the shell runs more than
  the reader can know (a function called later, `xargs`) are unreadable by D5, so the test asserts those are
  refused instead.

## Risks / Trade-offs

- [A form the reader gets wrong fails open] → D5's fail-closed default covers any program the reader doesn't know;
  D6's real-shell test checks the reader's boundaries against bash and zsh rather than against itself.
- [New refusals for working commands: `xargs gh …`, `$PY …` with git in the same command, `docker run … git`] →
  about 33 of 20,612 surveyed commands. Each gets a message saying how to rewrite it, and D6's comparison lists them
  so the owner sees the cost before merging.
- [The data list is too short and refuses an ordinary command] → it's one table, extended by pull request, as the gh
  allow-list is; the comparison over the survey finds the common cases now.
- [The outer split changes for text with `( )`] → D6's pinned decisions and the comparison with `main` catch a change
  for commands with no nesting.
- [Two Python versions or OSes read text differently] → the reader is plain string scanning plus `shlex`, which the
  guard already relies on; the guard's tests run on every OS and Python version in CI.

## Migration Plan

The change ships as `scripts/guard.py`, delivered to troupe and website after the owner approves the delivery plan.
Rollback is reverting the commit here and delivering again. Nothing is stored, so there's nothing to migrate.
