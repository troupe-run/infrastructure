# Design

## Context

See proposal.md, "Why". `commit_message(message)` in `scripts/guard.py` is the one decision behind the `commit-msg`
hook, the `pre-push` range check (`nonconforming_commits`) and the `guard` check on GitHub. `pr_title` applies it to
a pull request's title and writes its own reason and fix. guard.py may grow by about 4 KB before its size ceiling
(`quality-gates.toml`, #350).

Measured with release-please 17.6.0's changelog writer (`DefaultChangelogNotes`) on full messages:

- The subject goes into the notes HTML-escaped (`&lt;Old&gt;`). That's harmless until the post-merge round trip
  decodes it.
- A breaking note (`BREAKING CHANGE:` or `BREAKING-CHANGE:` footer, plus its continuation lines) goes in **raw**. With
  `!` and no footer, the subject is repeated raw as the note.
- A note ends at a blank line or at the next trailer (`Signed-off-by:`, `Co-Authored-By:`, …).
- The body and the trailers don't reach the notes.

node-html-parser (`kMarkupPattern`) reads `<!--…-->`, or `<`, an optional `/`, a letter then `[-.:0-9_a-zA-Z]*`,
followed by whitespace (attributes, up to any later `>`) or by `/>` or `>`. A release body always has a later `>`
(`</details>`).

## Goals / Non-Goals

**Goals:** refuse every subject or breaking note that release-please's round trip would turn into markup, with no
refusal of text it leaves alone, and the same answer in every place the rule runs.

**Non-Goals:**

- Fixing release-please. That's upstream; troupe's release workflow now notices a missing release
  (troupe-run/troupe#484).
- Judging the commit body or trailers, which never reach release notes.

## Decisions

### D1. Part of `commit-message`, not a new rule

The text is part of what a commit message may say, and every place that runs `commit-message` must also run this. A
separate rule would need wiring into the hook, the range check, the GitHub check and the title check, plus its
own docs row and override entry. guard.py has no room for that (#350). So `commit_message` checks the markup once
the message is a Conventional Commit, and returns its own reason and fix under the same rule name. `pr_title` passes
that decision through instead of rewriting it as a "not a Conventional Commit" refusal.

### D2. Copy the parser's rule, not "no `<`"

`MARKUP = re.compile(r"<!--|</?[A-Za-z][-.:0-9_A-Za-z]*(?:\s|/?>|$)")`. That is kMarkupPattern's opening, plus the
character that has to follow the tag name for a match. It refuses `<NAME>`, `Vec<u8>`, `a <b`, `</details>` and
`<!--`. It allows `a < b`, `<=`, `1<2`, `<3`, `->`, `<https://…>` and `<a@b.c>`. Those last two were measured: an
address isn't markup, since `@` can't follow a tag name.

An entity that decodes to `<` is markup too, once the round trip has decoded it (`&ltNAME`, `&amp;lt;`, `&#60;`).
Nobody needs entity text in a commit subject, so the rule also refuses `&lt`, `&#` and `&amp;` (case-insensitive)
rather than copying the parser's decoding. Plain `&` (`R&D`) is allowed.

Evidence: a differential run of 20,000 generated subjects through release-please 17.6.0's changelog writer and round
trip. The subjects mixed `<`, `>`, `/`, `!`, `-`, letters, digits, `@`, `:`, `` ` ``, `&`, `;`, `&#60;`, `&#x3C` and
`&amp;`. It found no subject that changes or drops notes that this rule allows. It over-refuses only entity text.

*Alternative:* refuse any `<`. Rejected: it refuses comparisons that release-please renders fine, so a person would
learn to work around a rule that's wrong.

### D3. Which text is judged

The subject (for a fixup, the subject it names, as `commit-message` already reads it). Then each line from a
`BREAKING CHANGE:` or `BREAKING-CHANGE:` footer up to the next blank line. That over-reaches by the trailers
after a note, but a trailer's `Name <address>` isn't markup (D2), so in practice it refuses nothing more.

*Alternative:* stop the note at the next trailer, as release-please does. Rejected: release-please's footer
boundary has exceptions (a `Refs:` line can continue the note), and copying them adds size and risk for no gain.

### D4. The fix says what works

The reason quotes the first piece of markup found. The fix says to write the text without angle brackets, for
example `{NAME}` or `NAME`, and that backticks don't protect it, because the parse is HTML, not Markdown.

## Risks / Trade-offs

- [release-please's parser changes] → The rule is named for the behaviour, and the tests list measured cases. A
  release-please upgrade that stops the round trip can relax it.
- [guard.py's size ceiling] → D1 keeps the change small. The size gate in `uv run scripts/check.py` shows the margin.
- [Existing commits on a branch] → The range check judges only the commits a push sends, so history on `main` is
  unaffected.
