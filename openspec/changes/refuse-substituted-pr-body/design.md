## Context

See proposal.md for why. The current state of `scripts/guard.py`:

- `split_command` calls `strip_heredocs` first, which drops every line after a `<<DELIM` up to the delimiter line,
  even when the heredoc sits inside a double-quoted `$(...)`. It then splits on operators outside quotes and gives
  each segment to `shlex.split(posix=True)`, which removes the quotes. So the issue's command reaches the check as
  `['gh', 'pr', 'create', '--title', 't', '--body', "$(cat <<'EOF'\n)"]`. Quoting is gone by then: the check can't
  tell `"$(x)"` (expanded by the shell) from `'$(x)'` (literal text).
- `pr_closes_issue` walks every word after `pr create`. It matches `-b`/`--body`/`--body=`, `-F`/`--body-file` and
  the `--fill` family by name, takes the next word as a value without skipping it, and doesn't skip other flags'
  values. It has three messages for descriptions it can't check (`--fill`, stdin, a body file that doesn't exist
  yet). Each stops the walk and refuses with its own problem and fix. Any other body without a closing line gets
  "the pull request's description doesn't close an issue."
- `pr_target` walks the same words for `-R`/`--repo`. It does skip the values of the flags in
  `GH_PR_CREATE_VALUE_FLAGS`, and reads `-Rvalue`, but not `-R` grouped after a boolean flag.
- gh parses flags with pflag (cobra). For a word starting with a single `-`, each letter is a short flag. A boolean
  letter is consumed and the next letter read; the first letter that takes a value takes the rest of the word as its
  value, dropping one leading `=`, or the next word when the rest is empty. A long flag without `=` takes the next
  word as its value whatever it looks like. `--` ends the flags. gh pr create's boolean short flags are `-d`
  (`--draft`), `-e` (`--editor`), `-f` (`--fill`) and `-w` (`--web`). The ones that take values are the short forms
  in `GH_PR_CREATE_VALUE_FLAGS`.
- Reproduced on this branch's base (`4b613da`):
  - refused with "doesn't close an issue": `--body "$(cat <<'EOF' ... EOF)"`, `--body "$(cat notes)"`,
    `` --body "`cat notes`" ``, `--body="$(x)"`, `--body "$BODY"`, `--body "${BODY}"`;
  - refused with "has no description": `-b'Closes #1'`, `-Fgood.md` (a file that closes an issue), `-dbClose`, `-df`;
  - goes ahead: `--body "Closes #16 $(cat notes)"`, `-b="Closes #1"`.
- No other check reads a description. `CLOSING` and the body flags are used only in `pr_closes_issue`.
- Help requests are judged as the command they ask about. On 2026-10-18 the guard was given `--help` and `-h` for
  122 commands (every gh command its tables name, every gh group, the git commands with hook rules, and the
  guard's `override`): about 130 were refused. Every gh group's help (`gh pr --help`) is refused as not on the
  allow-list; every owner-only command's help (`gh repo edit --help`, `gh auth token -h`) as owner-only;
  `gh pr create --help` as having no description. `gh --help`, `gh -h` and `gh help <anything>` are allowed (in
  `gh_decision`), as is help for an allowed command (`gh pr merge --help`). None of these help commands is granted.
  Also refused: `guard.py override --help` (`guard-tamper`) and `git -c core.hooksPath=x commit --help`
  (`skip-hooks`).
- gh 2.102.0 has 33 built-in command groups (its CORE, GITHUB ACTIONS and ADDITIONAL COMMANDS); the guard's tables
  name 12 of them. `gh help` also lists `co` under ALIAS COMMANDS: gh ships it as an alias for `pr checkout`.
- gh (cobra) prints a command's help and runs nothing when `--help` or `-h` is a flag, anywhere among the flags. But
  `--help` that follows a value-taking flag is that flag's value (`gh label create x --description --help` creates
  the label), and `gh <extension> --help` runs the extension's program, as `gh <alias> --help` runs the alias.
- 12 commands use `-h` for a value, not help: `--hostname` on the seven `gh auth` commands, `--homepage` on
  `gh repo create` and `gh repo edit`, `--host` on `gh config get`, `list` and `set` (from `gh help` on every
  command, gh 2.102.0). As the last word, that `-h` has no value, and pflag stops with "flag needs an argument"
  before the command runs.

## Goals / Non-Goals

**Goals:**
- A refused body built by the shell gets a message that's true and a fix that works first time.
- The check reads `gh pr create`'s flags as gh does, in one place, for both the description and the target.
- An agent can read any built-in gh command's help, with `--help` or `-h`, whatever the command would be refused
  for, and no command that does something can pass as a help request.
- Apart from the forms the reader newly understands and help requests, what's refused and what goes ahead stays
  exactly as it is.

**Non-Goals:**
- Reading the heredoc (the issue's option 2). See D1.
- Other expansions: arithmetic `$((...))` is caught by the `$(` test anyway; special parameters (`$1`, `$@`) and
  `$'...'` quoting aren't recognised, and keep today's message. Agents don't build descriptions with them.
- `gh issue create`, which no check reads.
- gh's long-flag prefixes. pflag doesn't accept abbreviated long flags, so there's nothing to copy.
- Granting help requests. They go ahead but get no grant, so Claude Code decides on them as it does for `gh help`
  today. Granting them would change "The guard grants the gh commands it allows".
- Help for `guard.py override` and for git with `core.hooksPath` changed. `guard-tamper` is deliberately
  unconditional, the override CLI is the owner's, and plain `git commit --help` is already allowed.
- Help forms other than the last word (`gh repo create --help x`). gh accepts them, but agents ask for help with a
  trailing flag, and the narrow shape is what makes D5 safe.

## Decisions

### D1. Name the case in the message; don't read the heredoc

When the body that's left after reading the flags has no closing line and holds a shell expansion (D2), the check
refuses with:

- problem: "a description built by the shell ($VAR, $(...) or backticks) can't be checked before it's sent."
- fix: "Write the description to a file in an earlier, separate command, and pass it with --body-file and a
  literal path, including 'Closes #<issue>'."

This is the issue's option 1, and it's how the check already treats stdin and `--fill`: it can't see what will be
sent, so it says so. The test is applied after all the flags are read, not while reading them like the others,
because the last `--body` wins and a later `--body-file` can replace it.

The fix carries the body-file lesson from #88 (the file must exist when the command starts, and the path must be
literal), so an agent following it doesn't walk into the missing-file refusal next.

*Alternative:* option 2, keep the heredoc text for `$(cat <<'X' ... X)` and check it. It accepts the common form,
but the parser would have to track a quoted delimiter inside a double-quoted substitution, and `cat` is only one of
the commands an agent might use (`$(printf ...)`, `$(sed ...)`). The check would still need option 1's message for
the rest, and for variables. More parser, for a form `--body-file` already covers.

*Alternative:* refuse every expanded body, even one whose own text closes an issue. Rejected: it would refuse
commands that go ahead today (`--body "Closes #16 $(cat notes)"`), where the closing line the check sees really is
in the description, and it would turn a message fix into a change in what's refused.

### D2. Detect expansions on the word the check already has

A body holds an expansion when it contains `$(`, a backtick, or `$` followed by a letter, `_` or `{` (regex
`` \$[A-Za-z_{(]|` ``). Nothing in `split_command` changes.

Because quoting is gone by then, literal text in single quotes (`'costs $HOME'`, or Markdown inline code in
backticks) also gets the new message when its body has no closing line. That's acceptable: the command is refused
either way, and the fix (`--body-file`) works for it too. `$5` and `$` alone don't match, so prices keep today's
message. Carrying quote information out of `split_command` would remove the false match, at the cost of changing
the parser every rule uses.

### D3. One reader of gh pr create's flags, copying pflag's rule

A new function, `pr_create_flags(args)`, turns the words after `pr create` into `(flag, value)` pairs, long names
for long flags and `-x` for short ones, by pflag's rule as described in Context:

- `--name=value` and `--name value` for a flag in `GH_PR_CREATE_VALUE_FLAGS`; `--name` alone for any other long
  flag;
- a word starting with one `-` is read letter by letter: `d`, `e`, `f`, `w` give `(-x, None)`; a value letter takes
  the rest of the word, minus one leading `=`, or the next word; any other letter ends the word with nothing more
  read (gh would refuse the command, so nothing is created);
- `--` ends the flags.

`pr_closes_issue` reads the description from these pairs in order (the last body flag still wins, and `--fill`,
stdin and a missing file still stop the reading with their own messages). `pr_target` reads `-R`/`--repo` from the
same pairs, then falls back to `GH_REPO` as today. Since the flag names and values come from one place, the
description and the target can't be read from different words.

This is why the change uses one reader rather than a fix in each check: a second hand-written walk is how the two
drifted apart in the first place (`pr_target` skips values; `pr_closes_issue` doesn't).

*Alternative:* add `-b<value>` handling to `pr_closes_issue` only, like `pr_target`'s `-R<value>`. Smaller, but it
leaves grouped flags and value-skipping wrong, and keeps two walks to drift.

### D4. A help request is one narrow shape, decided once, before the gh rules

`gh_help_request(words)` is true for exactly this shape, after any leading `VAR=value` words:

    gh <group> [<word> ...] (--help | -h)

- `<group>` is in a new table, `GH_BUILTIN_GROUPS`: gh's own command groups, copied from gh 2.102.0's `gh help`
  (CORE, GITHUB ACTIONS and ADDITIONAL COMMANDS, not ALIAS COMMANDS). An extension or alias can't take a built-in's
  name, so a built-in name always means gh's own command, and gh's own commands print help for `--help`.
- every word between the group and the help flag doesn't start with `-`, so none can be a flag that takes the help
  flag as its value;
- the help flag is the last word.

In `shell_decisions`, a help request skips `pr_closes_issue` and `gh_decision` for that simple command.
`guard_tamper` and `skip_hooks` still run, as for every command. Deciding it once, in front of the gh rules,
keeps the three rules from each growing their own idea of help.

Why it's safe: in this shape gh has no word to take `--help` as a value, so it prints help. For the 12 commands
whose `-h` takes a value, the trailing `-h` has none, so gh stops with an error and runs nothing. A group not in
the table (an extension, an alias, `co`, or a group a later gh adds) isn't a help request, and is judged as today.
When gh adds a group, its help is refused until the table gains it: the safe direction.

`gh --help`, `gh -h` and `gh help ...` stay allowed where they are now, in `gh_decision`.

*Alternative:* allow any gh command holding `--help` or `-h`. Rejected: `gh label create x --description --help`
would create a label through it. *Alternative:* take the built-in groups from the guard's existing tables. Rejected:
they name 12 of 33 groups, so `gh codespace --help` would stay refused, and an unlisted group is exactly where an
agent needs the help. *Alternative:* read `gh help` at run time. Rejected: the guard runs offline and must not
depend on what's installed; and `gh help` lists aliases, which aren't safe.

### D5. What changes and what doesn't is tested, not asserted

Following the differential-test rule, the behaviour that must not change gets tests that pass on the current code
before the guard is edited:

- a property test: for generated bodies (plain text, with or without a closing line, with and without `$(...)`,
  backticks, a heredoc substitution and `$VAR`/`${VAR}`, passed as `--body`, `--body=` and `-b` with a space), the
  command is refused exactly when the body word as the check sees it has no closing line;
- the existing pr-closes-issue tests, unchanged, and the messages that stay (a plain body with no closing line);
- for D4, every existing gh-allow-list and owner-only test, unchanged, and a property test: any gh command that
  isn't in D4's shape gets the same decision from `shell_decisions` with and without `gh_help_request` in front.

The reader gets its own table of tests, one per pflag case in D3, checked against what gh does. Before relying on
the table, a handful of its rows (attached, `=`, grouped, a dash-leading value, `--`) are run through real gh with
`gh pr create --dry-run` on a throwaway `troupe-run/infra-probe-*` repository, deleted afterwards, and gh's reading
recorded in tasks.md.

After the edit, a one-off script compares this branch's `pr_closes_issue` with `main`'s
(`git show main:scripts/guard.py`) over generated commands. Every difference must be one the spec allows: a new
message where the body holds an expansion, or a new decision only where the command uses a form D3 newly reads
(an attached or grouped short flag, or a value that looks like a flag). The result is recorded in tasks.md. A
lasting test can't do that comparison, because after the merge `main` is the new code.

For D4, a one-off sweep repeats the 2026-10-18 one above over every built-in group and every command in the
guard's tables, with `--help` and `-h`, recording which change from refused to allowed (expected: exactly the help
shapes) and checking that `guard-tamper` and `skip-hooks` still refuse theirs. Real gh is then run on a sample of the
newly allowed shapes, the owner-only ones included (`gh repo create --help`, `gh auth token --help`,
`gh auth token -h`, `gh secret set -h`), to confirm each prints help or stops with "flag needs an argument", and
does nothing else. That is safe to run once the guard allows it, and it's the guard's claim being checked, so it
runs after the edit. The claim that an extension or alias can't take a built-in's name is checked in gh's source
for the installed version (`gh alias set` and `gh extension install` both refuse a name that is already a gh
command), cited by file and line in tasks.md. It isn't checked by running them: the guard refuses `gh alias set`, and
both change this machine's gh config.

## Risks / Trade-offs

- [Single-quoted literal text that looks like an expansion gets the new message] → D2: the refusal and its fix are
  still right. Stated in the docs row.
- [The reader gets pflag's rule wrong, and the guard lets a PR through that closes no issue] → D5 checks the rule
  against real gh before the table is trusted, and a PR that slips through is still in front of the owner's review.
  The reader only ever reads flags gh reads, so it can't invent a closing line.
- [A grouped `-R` naming another repository is now allowed through without a closing line] → That's what the
  existing scenario "in any form gh accepts" already requires; the check was wrong before.
- [A help request lets a command through that does something] → D4's shape leaves gh no word to read `--help` as a
  value, extensions and aliases are excluded by the table, and the help-flag-as-value and extension cases are tests.
  The one-off sweep in tasks.md checks real gh: every allowed help shape prints help and changes nothing.
- [`GH_BUILTIN_GROUPS` falls behind gh] → A new group's help is refused, as today, with the allow-list message.
  Adding it is a one-line pull request.
- [The message names `--body-file` but the agent passes `$S/pr.md`] → D1's fix says "literal path", and the
  missing-file message covers it if they do.

## Migration Plan

1. Merge with CI green on all three OSes.
2. CI's plan shows `scripts/guard.py` updated in place in troupe and website (`guard_targets` in
   `tofu/guard_delivery.tf`), and nothing else. The owner approves the `apply` job.
3. Rollback: revert the commit here and deliver again. Neither target's declaration or hooks change, so there's
   nothing else to undo.

