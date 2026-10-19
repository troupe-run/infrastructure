# Tasks

## 1. Pin what must not change

- [x] 1.1 Before changing the guard, add to `scripts/tests/test_guard_claude.py` the hypothesis property test of
  design D6 ("Pin first"): commands built from plain pieces (git and gh commands from the rules' existing tests,
  `echo`, `ls`, quoted words holding operators, heredocs with quoted delimiters) joined by `&&`, `||`, `;`, `|` and
  newlines, with no nesting, get from `shell_decisions` the refusals their pieces get one at a time. Name it for that.
  Also pin, as plain tests, the spec's "must not change" cases: the reads in "Reads inside other commands", the words
  in "Words that only name git or gh", `cat <<'EOF'` with `$(gh auth token)` in its body, and #90's
  `--body "$(cat <<'EOF' … EOF)"` message. Verify they pass on `main`'s guard (`82efe9f`) before 2.2. Record the
  counts here.
  - 2026-10-19: 11 tests, all passing on `82efe9f`'s guard: the property test (100 examples, from 14 plain pieces and
    2 quoted heredocs, joined by `&&`, `||`, `;`, `|` and newlines) and 10 pinned commands. #90's message was
    already pinned by `test_a_body_built_by_the_shell_is_refused_as_one_that_can_t_be_checked`, so no new test.
  - 2026-10-19, corrected during 2.4 (raised by a side agent): the property test worked out its expected
    refusals with whichever guard was running, so after the rewrite it would have compared the new guard with
    itself. The pieces' expected refusals are now a fixed table, `MAIN_REFUSALS`, recorded from `82efe9f`'s guard
    (read from `git show 82efe9f:scripts/guard.py` in the scratchpad). A parametrized test checks each piece alone
    against it, and the property test checks joined commands against the table's union. Both pass on the new
    reader.

## 2. Read every command a shell line runs

- [x] 2.1 Write the stub-shell harness of design D6 ("Compare with real shells") in a new
  `scripts/tests/test_guard_nested.py`: stub `gh` and `git` programs, first on `PATH` in a temporary directory, that
  only append their arguments to a log; a helper that runs a command under `bash` (and `zsh` when installed) from that
  directory and returns the git and gh commands that ran. Skip when no `bash` is found. Verify by a test that a plain
  `gh auth token` and `git status` run the stubs and are logged, on this Mac under both shells.
  - 2026-10-19: `test_the_stubs_record_each_git_and_gh_command_the_shell_runs` passes under bash (Homebrew) and
    zsh on this Mac. zsh runs with `-f`, so the user's startup files can't put the real programs ahead of the stubs.
- [x] 2.2 Write the tests of the requirement "The rules reach every command a shell line runs", one per scenario:
  the issue's four commands refused as `owner-only` with the message the command gets on its own; nesting,
  backticks in `$(...)` and `$(...)` in backticks; `<(...)`, `${T:-$(…)}` and zsh's `=(…)`; the heredoc pair; each
  grouping, keyword and function form; each wrapper in `SHELL_WRAPPERS`; `bash -c`, `sh -c`, `zsh -c` and `eval`; a
  heredoc fed to `bash`; `skip-hooks` in a subshell and a substitution; `pr-closes-issue` in a substitution. For each
  command the stubs can run, also assert, with 2.1's harness, that the commands the guard judged are the ones the
  shell ran. Verify the new decision tests fail on `main`'s guard and 1.1 still passes.
  - 2026-10-19: in `test_guard_nested.py`, 52 nested commands, each refused as its inner command is on its own,
    with the readings checked against bash and zsh. Each row's inner command was first confirmed to be the one
    command the shells run (0 mismatches). On `main`'s guard 150 of the 160 tests fail. Ten pass: the harness, 4 of
    the 5 reads and the never-granted tests, which `main` gets right too, and `sh -s <<\EOF`, which `main` refuses
    only because it doesn't see `<<\EOF` as a heredoc and reads the body as commands. 1.1 still passes. Committed
    with 2.3, since the commit check runs the tests.
- [x] 2.3 Implement design D1 to D4 in `scripts/guard.py`: the D2 scanner, `commands_run`, `split_command`'s new
  operators, `_program`'s skipping, `SHELL_WRAPPERS`, `DATA_PROGRAMS` (with the comment saying what earns a place),
  shells' `-c` and `eval`, and `strip_heredocs` keeping each body and its quoting, with `<<\WORD` and `<<E"OF"` read
  as quoted. `shell_decisions` judges every command `commands_run` returns, `guard_tamper` included. Verify 1.1, 2.2
  and every existing test pass, and `uv run mypy` and `uv run ruff check` are clean.
  - 2026-10-19: `read_shell` (`_ShellReader`) in `scripts/guard.py`; `split_command` and `strip_heredocs` now use it.
    All 1,360 tests pass, and mypy and ruff are clean. 1.1's property test also passes at 3,000 examples. Still
    allowed until 3.2, as planned: `xargs gh …` and `sudo gh …`.
- [x] 2.4 Add the hypothesis variant of 2.1's harness (design D6): compose nestings from D2's and D3's forms around
  generated `gh` and `git` commands, and assert the commands the guard finds are the ones bash ran, or that the guard
  refuses the command as `command-unparseable`. Verify it passes over at least 500 examples locally, and record any
  disagreement it found and how it was resolved, here.
  - 2026-10-19: `test_composed_nestings_are_read_as_bash_runs_them_or_refused_as_unreadable` passes over 3,000
    examples in each of seven runs under bash 5.3 (21,000 in all). Disagreements it found, and how each was resolved:
    - The guard's bugs, fixed in `scripts/guard.py`:
      - A shell reading an unquoted heredoc: the body's substitutions were read twice. The outer shell expands them
        first, so they're now read once, and the script is read with each expansion as a word of unknown value.
      - `((gh))` is an arithmetic command, not two subshells. `((` at a command's start, including after `{` and
        `time`, is now arithmetic. Arithmetic is scanned only for `$(`, backticks and `${`, since `<(` there is
        less-than and a bracket.
      - **A fail-open:** when the reader can't split a command, it was refused only if its text mentioned git or
        gh, and the text checked had its heredoc bodies taken out. So a script fed to bash, whose only `gh` was in
        the body, went through. The whole command is now checked
        (`test_an_unparseable_command_whose_gh_is_only_in_a_heredoc_is_refused`).
    - The generator's bugs, where the shell itself ran nothing: `command (gh)` and `env A=1 eval gh` are errors,
      `command A=1 gh` looks up a program named `A=1`, and `sh` on macOS has no `<(…)`. Wrappers now wrap only
      simple commands that start with a program, and the generated shell forms use bash.
    - Allowed by the test as task 2.4 says: deeply re-quoted words inside an unquoted heredoc that the reader can't
      split are refused as `command-unparseable`.
    - Not changed: the rules see a trailing redirection (`2>/dev/null`) as a word, as before, so the test leaves
      attached redirections out when comparing with what the shell ran.

## 3. Refuse what can't be read

- [x] 3.1 Write the tests of the requirement "A git or gh command the guard can't read is refused", one per scenario:
  `xargs`, `sudo`, `find -exec` and `docker` running git or gh; `G=gh; $G auth token`; a pipe and a here-string into
  `bash`; `alias g=gh`; `$(case x in a) gh auth token;; esac)` and an unclosed `$(`; `env -S 'gh auth token'`; the
  depth cap. Each is refused as `command-unparseable` with D5's message, and the same shapes without git or gh go
  ahead. Verify they fail on the code from 2.3.
  - 2026-10-19: 24 tests in `test_guard_nested.py`. On 2.3's code the 11 refusals fail, and the 11 look-alikes
    without git or gh pass, as they should. The two unclosed substitutions pass too, through the existing
    unbalanced-text refusal, which keeps its message.
- [x] 3.2 Implement design D5: the reader's unreadable marks, the git-or-gh word test, and the
  `command-unparseable` message and fix. Unbalanced quotes keep today's message. Verify 1.1, 2.2, 2.4, 3.1 and every
  existing test pass, and `uv run mypy` and `uv run ruff check` are clean.
  - 2026-10-19: all 1,402 tests pass, mypy and ruff are clean, and 2.4's test passes over 3,000 examples twice more.
    Found while implementing: shlex makes `<<<` a word of its own, so `bash <<< 'gh …'` read the here-string as a
    script file. A shell's redirections and here-strings, and their targets, are now set aside before its options
    are read. A shell's other arguments get the git-or-gh word test too: `bash -c '"$0" auth token' gh` runs gh.
- [x] 3.3 Run the one-off comparison of design D6 ("Compare with main over the survey"): a scratchpad script runs
  `main`'s `shell_decisions` and this branch's over the surveyed Bash commands and lists each command whose decisions
  differ. Classify every difference as meant (a nested command now read or refused, by which scenario) or a
  regression, fix each regression with a test, and record the counts here (not the commands: they are session
  history). Verify no difference is left unclassified.
  - 2026-10-19: 20,750 Bash commands from this machine's earlier troupe sessions (this session left out), judged by
    `82efe9f`'s guard and by this branch's. The first run differed on 54. Eight were a regression: `/usr/bin/time
    -p git commit …`, refused because the `time` program wasn't a wrapper, though the `time` keyword was. It's now
    in `SHELL_WRAPPERS`, with a test. The rerun differs on 46, every one meant:
    - newly `command-unparseable` (26): `xargs gh` 11, `xargs git` 2, an expansion as the program 10 (one of them,
      `$R/docs/…` with `R="gh api …"`, does run gh), `docker run … git` 1, `gitleaks git` 1 (gitleaks' own
      subcommand, refused through D5's default for programs the guard doesn't know), and 1 unparseable command
      that mentions git or gh only in what reads as a heredoc body (2.4's fail-open fix);
    - newly `owner-only` (9): `GITHUB_TOKEN=$(gh auth token) …` and `gh repo edit` in `for` loops over
      `troupe-run/$r`, a repository that can't be told to be a throwaway;
    - newly `gh-allow-list` (10): GraphQL mutations and API writes in substitutions, and `gh $c` in a loop;
    - a changed message (1): a `gh api -X DELETE …/$(gh api …)` refusal now names the whole path, not `$(gh`.
    No refusal `main` gave was lost.

## 4. PowerShell

- [x] 4.1 Write the PowerShell scenario tests (spec: "PowerShell subexpressions and script blocks", "PowerShell command
  strings", "PowerShell's backtick is an escape", "PowerShell that can't be read"), judged as the PowerShell tool's
  commands, and extend 2.1's harness to run them under `pwsh` (stub `gh.cmd`/`git.cmd` on Windows, stub scripts
  elsewhere), skipped where `pwsh` is missing. Include an `-EncodedCommand` built the way PowerShell encodes it.
  Verify the decision tests fail on `main`'s guard.
  - 2026-10-19: 49 tests in `test_guard_nested.py` and 2 hook tests in `test_guard_claude.py`. On 3.3's code,
    whose PowerShell reading is `main`'s (the bash reader), all of them fail, the 14 `pwsh` reading tests aside.
    Those skip here: this Mac has no `pwsh`, so they're checked in CI (4.3). Corrected while writing: the spec
    gave `Start-Job { gh auth token }` as unreadable, but D7 reads every script block, so it's refused as
    `owner-only`. It moved to the script-block scenario, and the design says so. An example of an expression
    program, `& ("g" + "h")`, never names gh in its text, which is the obfuscation the design leaves out of scope,
    so the test uses `& (Get-Command gh)` instead.
- [x] 4.2 Implement design D7 in `scripts/guard.py`: `shell_decisions` takes the tool, and the reader's PowerShell
  dialect (quoting, here-strings, subexpressions, script blocks, call operators, command strings, `cmd /c`, and the
  PowerShell entries of `DATA_PROGRAMS`). Verify 1.1, 2.2, 2.4, 3.1, 4.1 and every existing test pass, the existing
  PowerShell hook tests in `test_guard_claude.py` included, and `uv run mypy` and `uv run ruff check` are clean.
  - 2026-10-19: `_PowerShellReader` in `scripts/guard.py`, and `shell_decisions` takes the tool. 1,439 tests pass
    (the 14 `pwsh` ones skipped), mypy and ruff are clean, and 2.4's bash test passes over 1,000 more examples.
    A PowerShell statement runs a program only when it starts with a bare word or a call operator; one that starts
    with a variable, a string, a number or a bracket is an expression, whose substitutions and blocks are read.
- [x] 4.3 After pushing, verify from CI's logs that the `pwsh` tests ran, not skipped, on Linux, macOS and Windows,
  and record the counts here. If a runner has no `pwsh`, stop and raise it with the owner rather than leaving them
  skipped.
  - 2026-10-19, CI run 39199978774 on `4b58aa0`, all 11 jobs green: no job reports the `pwsh` tests skipped. The
    only skips anywhere are 3 existing Windows tests ("Git for Windows has no executable bit"), so the 14 `pwsh`
    tests ran and passed on ubuntu (Python 3.13, 3.14, 3.15, and the `check` job), macOS (3.12 to 3.15) and Windows
    (3.12 to 3.15). The first run, 39199136640 on `906e99e`, had found two harness bugs, fixed in `4b58aa0`. On
    Windows, Git Bash put its own directories first on PATH, so the real git ran in place of the stub, in an empty
    temporary directory. A `BASH_ENV` file now puts the stubs first. The `zsh -f -c` row needs zsh installed, so it
    now runs only under zsh.

## 5. Document it

- [x] 5.1 In `docs/development-workflow.md`, the `command-unparseable` row says what can't be read and the fix (run
  the git or gh command on its own), and a short paragraph under the rules table says that every rule reaches the git
  and gh commands a Bash or PowerShell command runs, wherever they sit, lists the forms read in each, the data programs and the wrappers by
  their table names, and says what is out of reach (scripts and programs that run git or gh themselves, `source`,
  obfuscated names). Verify each example command in the new text gets the decision the text says, by running it
  through `shell_decisions` in a scratchpad script.
  - 2026-10-19: a new section, "Which commands the guard reads"; the `command-unparseable` row; and the known gap on
    commands built at run time, rewritten to say what's read now and what isn't, pointing to #101. All 25 example
    commands in the new text, through the Bash or PowerShell tool as the text says, get the decision it says (0
    mismatches), and the doc tests pass.

## 6. Integration

- [x] 6.1 Verify the delivery plan shows `scripts/guard.py` updated in place in troupe and website, and nothing else,
  and keep it for the pull request. The evidence is CI's pull-request plan (`tofu.yml`'s `plan (pull request)` job),
  not a local one.
  *2026-10-19: run 39199978813 on `4b58aa0`, posted on PR #102: `Plan: 0 to add, 2 to change, 0 to destroy.` The two
  are `github_repository_file.guard["troupe:scripts/guard.py"]` and `["website:scripts/guard.py"]`, updated in place
  (content and commit message only). No modes to set after the apply.*
- [x] 6.2 Run `openspec validate read-nested-commands --strict` and verify it passes.
  - 2026-10-19: `Change 'read-nested-commands' is valid`.

## Workflow follow-up

- Open the pull request with a Conventional title and `Closes #94`, the evidence from 1.1, 2.4, 3.3 and 4.3 and the
  plan from 6.1, with the description passed by `--body-file`. CI must be green on all three OSes before the delivery is
  planned.
- Archive the change on the branch before merging. The owner merges by rebase and approves the `apply` job, which
  delivers `scripts/guard.py` to troupe and website.
- After the apply, confirm both repositories' delivered `scripts/guard.py` match `main` here.
- Comment on #94 with the pull request and the archived change, noting the forms beyond substitutions that the owner
  asked to include, check it's closed, and check its roadmap card says Done.
