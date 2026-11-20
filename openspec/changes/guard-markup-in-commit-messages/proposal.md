# Proposal

## Why

troupe-run/troupe's 0.2.0 release left two components unreleased (troupe-run/troupe#484). One commit subject,
`fix(runtimes): the actor's model beats TROUPE_RUNTIME_<NAME>_MODEL`, reached the release pull request's notes as
`&lt;NAME&gt;`. After the merge, release-please 17.6.0 parses that body, writes it back out and parses it again, and
the first parse decodes the entity. The second sees an unclosed `<NAME>` element, which swallowed the blocks after
it: troupe-runner-ollama and protocol got no release, and troupe-v0.2.0's notes took in every later block. Nothing
stops the next such subject (#364).

Checked with release-please 17.6.0's own changelog writer and round trip:

- Text node-html-parser reads as markup loses text or components: `<!--`, or `<`, an optional `/` and a letter.
- `` `<NAME>` `` in backticks is no different, because the parse is HTML, not Markdown.
- `<details>` crashes release-please.
- `a < b`, `<=`, `1<2`, `<3` and `->` are untouched.

## What Changes

- The `commit-message` rule also refuses a message whose subject, or `BREAKING CHANGE:` note, contains text that
  node-html-parser reads as markup. That's the text release-please writes into release notes. The refusal quotes the
  text and says to write it without angle brackets, for example `TROUPE_RUNTIME_{NAME}_MODEL`, and that backticks
  don't help.
- It applies wherever `commit-message` does: the `commit-msg` hook, the `pre-push` hook, the `guard` check on GitHub
  and a pull request's title. Every governed repository gets it by delivery.
- `docs/development-workflow.md`'s rule table says so.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `development-workflow`: a new requirement that commit text release notes would parse as markup is refused.

## Impact

- `scripts/guard.py`: `commit_message` and `pr_title`. It has about 4 KB of room under its size ceiling (#350).
- `scripts/tests/test_guard_commit_rules.py`, and the pull-request title tests.
- `docs/development-workflow.md`.
- A delivery to troupe and website after the merge, as for any guard change.
