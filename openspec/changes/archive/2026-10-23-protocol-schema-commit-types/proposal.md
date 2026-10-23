# Proposal

## Why

Since troupe-run/troupe#140 (`protocol-own-release`), troupe's protocol is released on its own. The troupe package
records which protocol release its copy of the schemas is (`packages/troupe/src/troupe/protocol/version.json`), and
that record moves only when the protocol releases. release-please releases a component only for a commit whose type
is `feat`, `fix`, `perf` or `revert`, or that is a breaking change (`src/util/filter-commits.ts`,
`DEFAULT_CHANGELOG_SECTIONS`; troupe's config sets no `changelog-sections`). So a `docs:`, `refactor:`, `test:` or
`chore:` commit that changes a schema releases nothing, and the next troupe release ships the changed schemas under
the old protocol version.

troupe's `contributing/releasing.md` asks for a releasing type in words. Nothing checks it (#122).

## What Changes

- **A new guard rule, `schema-commit-type`.** A commit that changes a file under `protocol/schemas/` is refused unless
  its type releases something: `feat`, `fix`, `perf` or `revert`, or any type marked breaking (`!` before the colon,
  or a `BREAKING CHANGE:` or `BREAKING-CHANGE:` footer). The refusal names the schema files and the types that are
  allowed. It's overridable by the owner, like the other git rules.
- **Checked where commit messages already are:** by the `commit-msg` hook against what the commit will contain, by
  the `pre-push` hook and by the `guard` check on GitHub against each commit's own changes. So a commit that skipped
  the hooks, or was amended or reworded afterwards, is still caught before it merges.
- **Inert where there's no `protocol/schemas/`.** The rule keys on the path, which today exists only in troupe.
  infrastructure and website are unaffected. A commit that changes only `protocol/README.md`, `protocol/CHANGELOG.md`
  or anything else outside `protocol/schemas/` is unaffected too, and so is release-please's own release commit, which
  changes `version.json` and the changelog but no schema.
- **`docs/development-workflow.md` lists the rule**, and the `development-workflow` spec gains a requirement for it.
- **Delivered to troupe and website** in the usual way, once CI is green on all three OSes and the owner approves the
  plan.

Not changing: which commit types are accepted at all (`commit-message`), how release-please is configured, and
troupe's generated copy of the schemas (troupe's `scripts/package_schemas.py` already fails a copy that differs from
`protocol/schemas/`, so a schema change always starts at the source).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: a new requirement, "Schema changes use a commit type that releases", with its scenarios;
  "Commit messages are checked before a push" and "The rules are re-checked on GitHub" name the new rule among the
  ones they apply.

## Impact

- `scripts/guard.py`: the rule, its rule id, and calls from `run_commit_msg`, `run_pre_push` and `run_ci`.
- `scripts/tests/test_guard_commit_rules.py`, `scripts/tests/test_guard_push_and_ci.py`, and the docs test that
  checks every rule is listed.
- `docs/development-workflow.md`.
- The delivered copies in troupe-run/troupe and troupe-run/website (an apply after merge). In troupe, the next commit
  that touches a schema needs a releasing type; troupe's `contributing/releasing.md` can then point at the rule
  rather than ask for it (troupe's own follow-up, not this change).
