# Tasks

## 1. Pin what must not change

- [x] 1.1 Before changing the guard, add a hypothesis property test to `scripts/tests/test_guard_claude.py` (design
  D5): for generated bodies (plain text, with or without a closing line, with and without `$(...)`, backticks, a
  `$(cat <<'EOF' ... EOF)` heredoc and `$VAR`/`${VAR}`, passed as `--body`, `--body=` and `-b` with a space),
  `gh pr create` is refused under `pr-closes-issue` exactly when the body word `split_command` gives has no closing
  line. Name it for that. Also pin the messages that stay: `--body "no closing line"` and `--body "costs $5"` are
  refused with today's problem and fix, and `--body-file <file>` holding `Closes #16` goes ahead. Verify they pass
  on the current code, before 2.2 and 3.2.
  - 2026-10-18: 5 tests, all passing on `b4bda71`'s guard. Over 500 generated commands the property test saw every
    case: heredoc bodies (217, all refused), inline bodies with an expansion (76 refused, 42 going ahead because
    their literal text closes an issue) and plain ones (95 refused, 70 going ahead).

## 2. Read gh pr create's flags as gh does

- [x] 2.1 Check pflag's rule against real gh (design D5): create `troupe-run/infra-probe-pr-flags` (public, with a
  pushed branch), run `gh pr create --dry-run` with `-b'Closes #1'`, `-b='Closes #1'`, `-db 'Closes #1'`,
  `-Fpr.md`, `--title -b --body x`, `--title --fill --body x` and `-- -b x`, and record which description and title
  gh reads for each, here. Delete the repository afterwards and verify it's gone (`gh repo view` fails).
  - 2026-10-18, gh 2.102.0, `gh pr create --repo troupe-run/infra-probe-pr-flags --head probe --dry-run`, run from
    this worktree (a PR into another repository isn't checked, so each form reached gh as written). gh read:
    `-b'Closes #1'` and `-b='Closes #1'` → body `Closes #1`; `-db 'Closes #1'` → draft, body `Closes #1`;
    `-dbClose` → draft, body `Close`; `-F<path>` and `-F=<path>` → the file's text; `--title -b --body x` → title
    `-b`; `--title --fill --body x` → title `--fill`; `-b -x` → body `-x`; `--body --fill` → body `--fill`;
    `-b 'Closes #1' --body 'last wins'` → `last wins`; `--body base -- -b x` → error `unknown arguments ["-b" "x"]`;
    `-zb x` → error `unknown shorthand flag: 'z' in -zb`. All as D3 describes. The repository was then deleted, and
    `gh repo view` reports it can't be resolved.
- [x] 2.2 Write the reader's table of tests (design D3), one row per case, matching 2.1's results: long `=` and
  space forms, a short flag with its value attached, after `=`, and in the next word, grouped boolean flags before a
  value flag, a dash-leading value of a long and a short flag, an unknown letter, and `--`. Add the spec's
  short-flag scenarios through `shell_decisions`: `-b'Closes #22'`, `-b='Closes #22'`, `-db 'Closes #22'` and
  `-F<file>` holding `Closes #22` go ahead, and `-b'no close'` is refused with "doesn't close an issue";
  `--title --fill --body 'Closes #22'` goes ahead; `-dR troupe-run/.github` with no closing line goes ahead from a
  troupe clone. Verify the decision tests fail on the current code.
  - 2026-10-18: 23 reader rows and 8 decision tests. On `ebbef19`'s guard 30 fail (`pr_create_flags` doesn't
    exist; the short-flag, grouped-target and `--title --fill` cases are refused) and 1 passes:
    `-b='Closes #22'`, which the old check already read. It stays, since the spec names it.
- [x] 2.3 Implement `pr_create_flags` (D3) in `scripts/guard.py`, with `--attach` added to `GH_PR_CREATE_VALUE_FLAGS`
  (design D6), and move `pr_closes_issue` and `pr_target` onto it.
  Verify 1.1, 2.2 and every existing test in `scripts/tests/` pass, and `uv run mypy` and `uv run ruff check` are
  clean.
  - 2026-10-18: `pr_create_flags` with `GH_PR_CREATE_BOOLEAN_SHORT_FLAGS`; `pr_target` and `pr_closes_issue` read
    from it. 1071 tests pass; ruff and mypy clean.

## 3. Say what's wrong with a body built by the shell

- [ ] 3.1 Write the regression tests (spec: "A description built by the shell", "An expanded description whose own
  text closes an issue"): the issue's command verbatim, `--body "$(cat notes)"`, `` --body "`cat notes`" ``,
  `--body="$(x)"`, `--body "$BODY"` and `--body "${BODY}"` are refused with a problem saying a description built by
  the shell can't be checked before it's sent, a fix naming `--body-file`, and a problem that doesn't say the
  description doesn't close an issue; the issue's command through the PreToolUse entry gives a denial starting
  `guard: pr-closes-issue:` with the new problem; `--body "Closes #16 $(cat notes)"` goes ahead; an expanded
  `--body` followed by `--body-file good.md` that closes an issue goes ahead. Verify the refusal tests fail on the
  current code and the go-ahead ones pass.
- [ ] 3.2 Implement D1 and D2 in `pr_closes_issue`. Verify 1.1, 3.1 and every existing test pass, and `uv run mypy`
  and `uv run ruff check` are clean.
- [ ] 3.3 Run the one-off comparison (design D5): a scratchpad script runs `main`'s `pr_closes_issue`
  (`git show main:scripts/guard.py`) and this branch's over at least 5,000 generated commands mixing every body,
  body-file, fill, title and repo form above. Verify every difference is one the spec allows: a new message only
  where the body holds an expansion, and a new decision only where the command uses an attached or grouped short
  flag or a flag-like value. Record the counts here.
- [ ] 3.4 In `docs/development-workflow.md`, the `pr-closes-issue` row names a `--body` built by the shell as a case
  that can't be checked, its fix (`--body-file` with a literal path), that literal text in single quotes that looks
  like an expansion gets the same message (design D2), and that flags are read as gh reads them. Verify
  `uv run scripts/check.py` passes.

## 4. Help requests go ahead

- [ ] 4.1 Before changing the guard, add to `scripts/tests/test_guard_gh.py` a hypothesis property test (design D5):
  for generated gh commands that aren't in D4's help shape (groups from the guard's tables and unknown ones, flags
  and values, `--help`/`-h` as a flag's value or not last), `shell_decisions` gives the same decisions as it does
  with the help test switched off. Name it for that. Verify it and every existing gh test pass on the current code
  (the property holds trivially there, which is the baseline).
- [ ] 4.2 Write the help tests (spec: "Asking for help", "A help flag that is another flag's value", "Help for an
  extension or an alias", "Help for an owner-only command", "Help for gh pr create"): `gh pr --help`,
  `gh codespace -h`, `gh repo create myrepo --help`, `gh repo edit --help`, `gh label create -h`,
  `gh auth token --help`, `gh copilot --help`, `GH_REPO=x gh pr create --help` and `gh pr create -h` go ahead;
  refused as today: `gh label create x --description --help` (owner-only), `gh co --help`, `gh myext --help`,
  `gh extension exec myext --help`, `gh ext exec myext --help`, `gh pr create --help x`
  (no closing description), `gh pr create --title --help` (no closing description), and `guard.py override --help`
  (`guard-tamper`). No help request is granted (`grantable` is false). Verify the go-ahead tests fail on the current
  code.
- [ ] 4.3 Implement D4 in `scripts/guard.py`: `GH_BUILTIN_GROUPS` (gh 2.102.0's CORE, GITHUB ACTIONS and ADDITIONAL
  COMMANDS, with a comment naming the version, that ALIAS COMMANDS are left out, and to check new commands for
  `DisableFlagParsing`), `GH_HELP_FORWARDED`, `gh_help_request`, and its use in
  `shell_decisions`. Verify 4.1, 4.2 and every test in `scripts/tests/` pass, and `uv run mypy` and
  `uv run ruff check` are clean.
- [ ] 4.4 Check D4 against gh (design D5): repeat the sweep of `--help` and `-h` over every built-in group and every
  command in the guard's tables, and record which decisions changed (expected: exactly the help shapes, refused to
  allowed; `guard-tamper` and `skip-hooks` unchanged). Then run real gh, now that the guard allows it, on
  `gh repo create --help`, `gh auth token --help`, `gh auth token -h`, `gh secret set -h`, `gh config get -h` and
  `gh codespace --help`, and verify each prints help or stops with "flag needs an argument", and changes nothing.
  Record all of it here.
  - 2026-10-18, before any code (raised by a side agent): gh 2.102.0's source, read in the scratchpad, gives the
    facts now in the design's Context. An extension or alias can't take a built-in's name
    (`pkg/cmd/root/root.go:193-201`, `root.go:205-209`, `pkg/cmd/alias/set/set.go:122-126`; `gh extension install`
    itself doesn't refuse one, so the design's first wording was wrong). `gh extension exec` forwards `--help` to
    the extension (`pkg/cmd/extension/command.go:541-557`), so D4 now excludes it; `gh copilot` handles help itself
    (`pkg/cmd/copilot/copilot.go:83-104`). `-h` is help through pflag v1.0.10's `ErrHelp` (`flag.go:1050-1056`).
- [ ] 4.5 In `docs/development-workflow.md`, the `gh-allow-list` and `owner-only` rows say a request for a built-in
  command's help goes ahead, in the narrow shape (D4), and isn't granted; the `pr-closes-issue` row says the same for
  `gh pr create --help`. Verify `uv run scripts/check.py` passes.

## 5. An attachment is a file read

- [ ] 5.1 Write the grant tests in `scripts/tests/test_guard_grants.py` (spec: "An attachment from outside the
  repository", "An attachment from inside the repository"): not granted: `gh issue comment 1 --body x --attach
  /etc/hosts`, the same on `gh pr comment`, `gh issue create`, `gh pr create`, `gh issue edit` and `gh pr edit`,
  `--attach=/etc/hosts`, `--attach '../outside.png#alt'`, `--attach 'shot.png#x/../../../etc/hosts'` (a prefix is
  inside, the whole value isn't), and an empty `--attach ''`; granted: `--attach shot.png`,
  `--attach 'docs/shot.png#The new page'` and a file in the system temp directory, each on `gh issue comment`. Verify
  the not-granted tests fail on the current code and the granted ones pass.
- [ ] 5.2 Implement D6 in `_files_read` and `GH_FILE_FLAGS` (with the comment the design's risks name). Verify 5.1
  and every test in `scripts/tests/` pass, and `uv run mypy` and `uv run ruff check` are clean.
- [ ] 5.3 In `docs/development-workflow.md`, "What the guard grants" says every `--body-file`/`-F`/`--input` and
  `--attach` (each reading of `<file>#<alt>`) must be inside the repository or the temp directory. Verify
  `uv run scripts/check.py` passes.

## 6. Integration

- [ ] 6.1 Run `uv run scripts/tofu.py plan` after fast-forwarding onto `origin/main`, and verify it shows
  `scripts/guard.py` updated in place in troupe and website, and nothing else. Keep it for the pull request.
- [ ] 6.2 Run `openspec validate refuse-substituted-pr-body --strict` and verify it passes.

## Workflow follow-up

- Open the pull request with a Conventional title and `Closes #90`, the evidence from 2.1, 3.3 and 4.4 and the plan
  from 6.1, with the description passed by `--body-file`. CI must be green on all three OSes before the delivery is
  planned.
- Archive the change on the branch before merging. The owner merges by rebase and approves the `apply` job, which
  delivers `scripts/guard.py` to troupe and website.
- After the apply, confirm both repositories' delivered `scripts/guard.py` match `main` here.
- Comment on #90 with the pull request and the archived change, noting the three cases added in planning and the `--attach` grant found while applying, check it's
  closed, and check its roadmap card says Done.
