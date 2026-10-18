## Why

The guard's `pr-closes-issue` check refuses a `gh pr create` whose `--body` is built by command substitution, such as
`--body "$(cat <<'EOF' ... EOF)"`, and says the description has no closing line even when it does (#90, seen on
troupe-run/website#17). `split_command` drops heredoc bodies before splitting, so the check sees only
`$(cat <<'EOF'\n)`. Refusing is the safe direction, but the message is wrong and its fix ("Add a line like
'Closes #22'") can't help, because the line is already there. Agents build descriptions this way often, so the
wrong message will keep sending them in circles.

Planning found three more misreads of the same kind, and the owner asked for all of them to be fixed here:

- `--body "$BODY"` (a variable) gets the same untrue "doesn't close an issue".
- A short flag whose value is in the same word isn't read at all. `-b'Closes #1'`, `-Fpr.md` and grouped flags such as
  `-db 'Closes #1'` are refused with "has no description", though gh reads each of them as a description. The same
  gap means a grouped `-R` naming another repository isn't seen as one.
- `gh pr create --help` is refused as a PR with no description. A sweep of the guard found the same for about 130
  help requests: every gh group's help (`gh pr --help`) is refused as not on the allow-list, and every owner-only
  command's help (`gh repo edit --help`) as owner-only. An agent can't read the help it needs, and the refusal
  misleads it about why. Only `gh help <command>` works, and nothing points to it.

While applying, gh's source showed one more gap, live on `main` and more serious, which the owner asked to fix here
too. gh's `--attach <file>` (on `gh pr` and `gh issue` `create`, `comment` and `edit`) uploads a local file to GitHub,
but the guard's list of flags that read local files predates it. So `gh issue comment 1 --body x --attach /etc/hosts`
is **granted**: it runs with no prompt and no auto-mode check, which is what "A grant is only for a plain gh
command" exists to prevent for `--body-file`.

## What Changes

- When `pr-closes-issue` refuses a `gh pr create` whose `--body`/`-b` value holds a shell expansion (command
  substitution `$(...)` or backticks, or a variable `$NAME`/`${...}`), it says why: a description built by the shell
  can't be checked before it's sent. The fix is to write the description to a file and pass it with `--body-file`
  and a literal path. That matches how the check already treats `--body-file -` (stdin) and `--fill`.
- For expansions, which commands are refused doesn't change. A body whose literal text already holds a closing line
  (`--body "Closes #16 $(cat notes)"`) still goes ahead. The heredoc parser doesn't change (the issue's option 2 is
  not taken).
- The check reads `gh pr create`'s flags as gh does: a short flag's value may follow in the same word (`-bTEXT`,
  `-b=TEXT`), boolean short flags may be grouped in front of it (`-db TEXT`), and every flag's value is skipped
  rather than read as a flag. One reader serves both the description and the target (`-R`), so the two can't
  disagree. This does change what's refused: a description or target given in one of these forms is now read, so a
  PR that closes an issue that way goes ahead, and one into another repository named that way isn't checked.
- A request for a built-in gh command's help goes ahead, whatever the command would be refused for. It's one narrow
  shape: `gh`, a built-in group, words that aren't flags, and `--help` or `-h` last. The shape leaves no room for a
  command that does something: `--help` as another flag's value (`--description --help`), an extension and an alias
  are judged as today. Help requests aren't granted, and help for `guard.py override` stays refused.
- A granted command's `--attach` counts as a file read, like `--body-file`: the guard grants it only when every file
  gh could read for it (gh tries the whole value, then each part before a `#`) is inside the repository or the
  system temp directory. `--attach` is also read as a value-taking flag of `gh pr create`.
- No other check reads a description, so the description changes are in `pr-closes-issue` only. `gh issue create`
  isn't checked, as today. The help rule sits in front of `pr-closes-issue`, `gh-allow-list` and `owner-only`.
- The rules' rows in `docs/development-workflow.md` name the new cases.
- `scripts/guard.py` is delivered to troupe and website.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: "Pull requests close an issue" gains scenarios. A description built by a shell expansion
  is refused with a message saying it can't be checked before it's sent and to pass it with `--body-file`. A
  description or target given in any short-flag form gh accepts is read as gh reads it. `gh pr create --help` goes
  ahead.
- `development-workflow`: "Agents' gh commands are allow-listed" adds a request for a built-in command's help to
  the list, with scenarios for asking for help, a help flag that is another flag's value, and an extension or alias.
- `development-workflow`: "Agents don't act as the owner" gains a scenario: help for an owner-only command goes
  ahead.
- `development-workflow`: "A grant is only for a plain gh command" gains scenarios: an attachment from outside the
  repository isn't granted; one from inside may be.

## Impact

- `scripts/guard.py`: `pr_closes_issue` and `pr_target`, through one reader of `gh pr create`'s flags; a help-request
  test in `shell_decisions`, with a table of gh's built-in groups.
- `scripts/tests/test_guard_claude.py` and `scripts/tests/test_guard_gh.py`: regression tests for the issue's
  command, each new form and help requests, and tests for what must not change. `scripts/tests/test_guard_grants.py`
  for `--attach`.
- `docs/development-workflow.md`: the `pr-closes-issue`, `gh-allow-list` and `owner-only` rows, and "What the guard
  grants".
- Delivery: `scripts/guard.py` changes in place in **troupe and website** (`guard_targets` in
  `tofu/guard_delivery.tf`), after the owner approves the plan. Neither repository's declaration or hooks change.
