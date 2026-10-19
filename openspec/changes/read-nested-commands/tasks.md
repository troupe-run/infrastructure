# Tasks

## 1. Pin what must not change

- [ ] 1.1 Before changing the guard, add to `scripts/tests/test_guard_claude.py` the hypothesis property test of
  design D6 ("Pin first"): commands built from plain pieces (git and gh commands from the rules' existing tests,
  `echo`, `ls`, quoted words holding operators, heredocs with quoted delimiters) joined by `&&`, `||`, `;`, `|` and
  newlines, with no nesting, get from `shell_decisions` the refusals their pieces get one at a time. Name it for that.
  Also pin, as plain tests, the spec's "must not change" cases: the reads in "Reads inside other commands", the words
  in "Words that only name git or gh", `cat <<'EOF'` with `$(gh auth token)` in its body, and #90's
  `--body "$(cat <<'EOF' … EOF)"` message. Verify they pass on `main`'s guard (`82efe9f`) before 2.2. Record the
  counts here.

## 2. Read every command a shell line runs

- [ ] 2.1 Write the stub-shell harness of design D6 ("Compare with real shells") in a new
  `scripts/tests/test_guard_nested.py`: stub `gh` and `git` programs, first on `PATH` in a temporary directory, that
  only append their arguments to a log; a helper that runs a command under `bash` (and `zsh` when installed) from that
  directory and returns the git and gh commands that ran. Skip when no `bash` is found. Verify by a test that a plain
  `gh auth token` and `git status` run the stubs and are logged, on this Mac under both shells.
- [ ] 2.2 Write the tests of the requirement "The rules reach every command a shell line runs", one per scenario:
  the issue's four commands refused as `owner-only` with the message the command gets on its own; nesting,
  backticks in `$(...)` and `$(...)` in backticks; `<(...)`, `${T:-$(…)}` and zsh's `=(…)`; the heredoc pair; each
  grouping, keyword and function form; each wrapper in `SHELL_WRAPPERS`; `bash -c`, `sh -c`, `zsh -c` and `eval`; a
  heredoc fed to `bash`; `skip-hooks` in a subshell and a substitution; `pr-closes-issue` in a substitution. For each
  command the stubs can run, also assert, with 2.1's harness, that the commands the guard judged are the ones the
  shell ran. Verify the new decision tests fail on `main`'s guard and 1.1 still passes.
- [ ] 2.3 Implement design D1 to D4 in `scripts/guard.py`: the D2 scanner, `commands_run`, `split_command`'s new
  operators, `_program`'s skipping, `SHELL_WRAPPERS`, `DATA_PROGRAMS` (with the comment saying what earns a place),
  shells' `-c` and `eval`, and `strip_heredocs` keeping each body and its quoting, with `<<\WORD` and `<<E"OF"` read
  as quoted. `shell_decisions` judges every command `commands_run` returns, `guard_tamper` included. Verify 1.1, 2.2
  and every existing test pass, and `uv run mypy` and `uv run ruff check` are clean.
- [ ] 2.4 Add the hypothesis variant of 2.1's harness (design D6): compose nestings from D2's and D3's forms around
  generated `gh` and `git` commands, and assert the commands the guard finds are the ones bash ran, or that the guard
  refuses the command as `command-unparseable`. Verify it passes over at least 500 examples locally, and record any
  disagreement it found and how it was resolved, here.

## 3. Refuse what can't be read

- [ ] 3.1 Write the tests of the requirement "A git or gh command the guard can't read is refused", one per scenario:
  `xargs`, `sudo`, `find -exec` and `docker` running git or gh; `G=gh; $G auth token`; a pipe and a here-string into
  `bash`; `alias g=gh`; `$(case x in a) gh auth token;; esac)` and an unclosed `$(`; `env -S 'gh auth token'`; the
  depth cap. Each is refused as `command-unparseable` with D5's message, and the same shapes without git or gh go
  ahead. Verify they fail on the code from 2.3.
- [ ] 3.2 Implement design D5: the reader's unreadable marks, the git-or-gh word test, and the
  `command-unparseable` message and fix. Unbalanced quotes keep today's message. Verify 1.1, 2.2, 2.4, 3.1 and every
  existing test pass, and `uv run mypy` and `uv run ruff check` are clean.
- [ ] 3.3 Run the one-off comparison of design D6 ("Compare with main over the survey"): a scratchpad script runs
  `main`'s `shell_decisions` and this branch's over the surveyed Bash commands and lists each command whose decisions
  differ. Classify every difference as meant (a nested command now read or refused, by which scenario) or a
  regression, fix each regression with a test, and record the counts here (not the commands: they are session
  history). Verify no difference is left unclassified.

## 4. PowerShell

- [ ] 4.1 Write the PowerShell scenario tests (spec: "PowerShell subexpressions and script blocks", "PowerShell command
  strings", "PowerShell's backtick is an escape", "PowerShell that can't be read"), judged as the PowerShell tool's
  commands, and extend 2.1's harness to run them under `pwsh` (stub `gh.cmd`/`git.cmd` on Windows, stub scripts
  elsewhere), skipped where `pwsh` is missing. Include an `-EncodedCommand` built the way PowerShell encodes it.
  Verify the decision tests fail on `main`'s guard.
- [ ] 4.2 Implement design D7 in `scripts/guard.py`: `shell_decisions` takes the tool, and the reader's PowerShell
  dialect (quoting, here-strings, subexpressions, script blocks, call operators, command strings, `cmd /c`, and the
  PowerShell entries of `DATA_PROGRAMS`). Verify 1.1, 2.2, 2.4, 3.1, 4.1 and every existing test pass, the existing
  PowerShell hook tests in `test_guard_claude.py` included, and `uv run mypy` and `uv run ruff check` are clean.
- [ ] 4.3 After pushing, verify from CI's logs that the `pwsh` tests ran, not skipped, on Linux, macOS and Windows,
  and record the counts here. If a runner has no `pwsh`, stop and raise it with the owner rather than leaving them
  skipped.

## 5. Document it

- [ ] 5.1 In `docs/development-workflow.md`, the `command-unparseable` row says what can't be read and the fix (run
  the git or gh command on its own), and a short paragraph under the rules table says that every rule reaches the git
  and gh commands a Bash or PowerShell command runs, wherever they sit, lists the forms read in each, the data programs and the wrappers by
  their table names, and says what is out of reach (scripts and programs that run git or gh themselves, `source`,
  obfuscated names). Verify each example command in the new text gets the decision the text says, by running it
  through `shell_decisions` in a scratchpad script.

## 6. Integration

- [ ] 6.1 Verify the delivery plan shows `scripts/guard.py` updated in place in troupe and website, and nothing else,
  and keep it for the pull request. The evidence is CI's pull-request plan (`tofu.yml`'s `plan (pull request)` job),
  not a local one.
- [ ] 6.2 Run `openspec validate read-nested-commands --strict` and verify it passes.

## Workflow follow-up

- Open the pull request with a Conventional title and `Closes #94`, the evidence from 1.1, 2.4, 3.3 and 4.3 and the
  plan from 6.1, with the description passed by `--body-file`. CI must be green on all three OSes before the delivery is
  planned.
- Archive the change on the branch before merging. The owner merges by rebase and approves the `apply` job, which
  delivers `scripts/guard.py` to troupe and website.
- After the apply, confirm both repositories' delivered `scripts/guard.py` match `main` here.
- Comment on #94 with the pull request and the archived change, noting the forms beyond substitutions that the owner
  asked to include, check it's closed, and check its roadmap card says Done.
