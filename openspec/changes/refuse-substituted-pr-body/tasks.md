# Tasks

## 1. Pin what must not change

- [ ] 1.1 Before changing the guard, add a hypothesis property test to `scripts/tests/test_guard_claude.py` (design
  D5): for generated bodies (plain text, with or without a closing line, with and without `$(...)`, backticks, a
  `$(cat <<'EOF' ... EOF)` heredoc and `$VAR`/`${VAR}`, passed as `--body`, `--body=` and `-b` with a space),
  `gh pr create` is refused under `pr-closes-issue` exactly when the body word `split_command` gives has no closing
  line. Name it for that. Also pin the messages that stay: `--body "no closing line"` and `--body "costs $5"` are
  refused with today's problem and fix, and `--body-file <file>` holding `Closes #16` goes ahead. Verify they pass
  on the current code, before 2.2 and 3.2.

## 2. Read gh pr create's flags as gh does

- [ ] 2.1 Check pflag's rule against real gh (design D5): create `troupe-run/infra-probe-pr-flags` (public, with a
  pushed branch), run `gh pr create --dry-run` with `-b'Closes #1'`, `-b='Closes #1'`, `-db 'Closes #1'`,
  `-Fpr.md`, `--title -b --body x`, `--title --fill --body x` and `-- -b x`, and record which description and title
  gh reads for each, here. Delete the repository afterwards and verify it's gone (`gh repo view` fails).
- [ ] 2.2 Write the reader's table of tests (design D3), one row per case, matching 2.1's results: long `=` and
  space forms, a short flag with its value attached, after `=`, and in the next word, grouped boolean flags before a
  value flag, a dash-leading value of a long and a short flag, an unknown letter, and `--`. Add the spec's
  short-flag scenarios through `shell_decisions`: `-b'Closes #22'`, `-b='Closes #22'`, `-db 'Closes #22'` and
  `-F<file>` holding `Closes #22` go ahead, and `-b'no close'` is refused with "doesn't close an issue";
  `--title --fill --body 'Closes #22'` goes ahead; `-dR troupe-run/.github` with no closing line goes ahead from a
  troupe clone. Verify the decision tests fail on the current code.
- [ ] 2.3 Implement `pr_create_flags` (D3) in `scripts/guard.py`, and move `pr_closes_issue` and `pr_target` onto it.
  Verify 1.1, 2.2 and every existing test in `scripts/tests/` pass, and `uv run mypy` and `uv run ruff check` are
  clean.

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
  `gh auth token --help`, `GH_REPO=x gh pr create --help` and `gh pr create -h` go ahead; refused as today:
  `gh label create x --description --help` (owner-only), `gh co --help`, `gh myext --help`, `gh pr create --help x`
  (no closing description), `gh pr create --title --help` (no closing description), and `guard.py override --help`
  (`guard-tamper`). No help request is granted (`grantable` is false). Verify the go-ahead tests fail on the current
  code.
- [ ] 4.3 Implement D4 in `scripts/guard.py`: `GH_BUILTIN_GROUPS` (gh 2.102.0's CORE, GITHUB ACTIONS and ADDITIONAL
  COMMANDS, with a comment naming the version and that ALIAS COMMANDS are left out), `gh_help_request`, and its use in
  `shell_decisions`. Verify 4.1, 4.2 and every test in `scripts/tests/` pass, and `uv run mypy` and
  `uv run ruff check` are clean.
- [ ] 4.4 Check D4 against gh (design D5): repeat the sweep of `--help` and `-h` over every built-in group and every
  command in the guard's tables, and record which decisions changed (expected: exactly the help shapes, refused to
  allowed; `guard-tamper` and `skip-hooks` unchanged). Then run real gh, now that the guard allows it, on
  `gh repo create --help`, `gh auth token --help`, `gh auth token -h`, `gh secret set -h`, `gh config get -h` and
  `gh codespace --help`, and verify each prints help or stops with "flag needs an argument", and changes nothing.
  Cite the lines of gh 2.102.0's source where `gh alias set` and `gh extension install` refuse a built-in's name.
  Record all of it here.
- [ ] 4.5 In `docs/development-workflow.md`, the `gh-allow-list` and `owner-only` rows say a request for a built-in
  command's help goes ahead, in the narrow shape (D4), and isn't granted; the `pr-closes-issue` row says the same for
  `gh pr create --help`. Verify `uv run scripts/check.py` passes.

## 5. Integration

- [ ] 5.1 Run `uv run scripts/tofu.py plan` after fast-forwarding onto `origin/main`, and verify it shows
  `scripts/guard.py` updated in place in troupe and website, and nothing else. Keep it for the pull request.
- [ ] 5.2 Run `openspec validate refuse-substituted-pr-body --strict` and verify it passes.

## Workflow follow-up

- Open the pull request with a Conventional title and `Closes #90`, the evidence from 2.1, 3.3 and 4.4 and the plan
  from 5.1, with the description passed by `--body-file`. CI must be green on all three OSes before the delivery is
  planned.
- Archive the change on the branch before merging. The owner merges by rebase and approves the `apply` job, which
  delivers `scripts/guard.py` to troupe and website.
- After the apply, confirm both repositories' delivered `scripts/guard.py` match `main` here.
- Comment on #90 with the pull request and the archived change, noting the three cases added in planning, check it's
  closed, and check its roadmap card says Done.
