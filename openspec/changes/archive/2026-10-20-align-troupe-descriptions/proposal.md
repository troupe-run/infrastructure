# Proposal

## Why

Every place that introduces troupe says it a little differently (#108). The hero, org profile and troupe README agree
on the tagline and paragraph. The repository descriptions, page title and meta description each have their own
one-liner, the status lines vary ("Pre-alpha, building in the open", "there's nothing to install yet"), the org has no
description, and only infrastructure has topics. The owner settled the canonical text on 2026-10-20. This change sets
it on GitHub's side and raises the matching changes in troupe and website.

## What Changes

- **The canonical text (owner, 2026-10-20):**
  - Tagline: "Your agents need a director."
  - Sentence: "troupe runs your development process with a team of agents, asking only when it needs you."
  - Paragraph: the sentence, then the existing "Work branches and loops, decisions go to whoever owns them, and every
    decision records who made it." This replaces "…with agents and people in named roles", which the owner found weak.
  - Status line: "Pre-alpha: there's nothing to install yet."
  - One-line description: the tagline and the sentence together (119 characters, inside the org description's
    160-character limit).
  - Page title: "troupe: your agents need a director".
  - Deliberate variants: the landing page's "Install: coming" button (brand guide §7). The README's longer status
    paragraph ("what exists so far is…") follows the status line.
- **One source here:** the tagline, sentence and status line go in `tofu/descriptions.json`. OpenTofu reads it for
  the org's description and troupe's repository description. A test checks that the org profile says the same.
- **The org's description** goes from empty to the one-line description.
- **troupe's repository description** goes from "troupe: run your development process with agents and people in
  named roles" to the one-line description.
- **website's repository description** goes from "troupe.run — website and landing page" to "The troupe.run website
  and landing page", without the em dash. infrastructure's and `.github`'s descriptions say what those repositories
  are, not what troupe is, so they stay as they are.
- **Topics:** troupe gets `ai-agents`, `developer-tools`, `human-in-the-loop`, `workflow` and `python`. website gets
  `astro` and `website`. infrastructure keeps its three.
- **The org profile** (`org-profile/profile/README.md`) gets the new paragraph and keeps its status line. The App
  delivers it to `.github` as usual.
- **Raised in the other repositories, each through its own process:**
  - website: record the canonical text in the brand guide, which is "the reference for anything that carries the
    troupe brand", including GitHub. Then the new paragraph in the hero, the page title and the meta description (the
    one-line description plus the status line).
  - troupe: the new paragraph in the README.

  Each is its own issue, opened on the board as a sub-issue of #108.
- **Not in this change:**
  - Checking across repositories that troupe's README and website's copy match this repository. #120 settled how
    troupe and its docs stay in step, and it covered `/docs`, not the landing page or the README. A check across
    repositories would need network access, which the guard's offline checks don't have. The brand guide is the
    reference that both read from.
  - The `docs/status.md` wording ("Nothing is installable yet"). #120 moves status out of `/docs` to a page of the
    website's own, so that change words it.

## Capabilities

### New Capabilities
- `descriptions`: how the org describes troupe on GitHub. One source for the tagline, sentence and status line, used
  by the org's description, troupe's repository description and the org profile, plus the repositories' topics.

### Modified Capabilities
- None. The `repositories` and `org-settings` specs already require declared settings to show drift in the plan. This
  change sets new values through those declarations.

## Impact

- `tofu/descriptions.json` (new). `tofu/org.tf`: `description`. `tofu/repositories.tf`: troupe's and website's
  `description` and `topics`.
- `org-profile/profile/README.md`: the paragraph.
- `scripts/tests/test_org_profile.py` (or a new `test_descriptions.py`): the profile carries the canonical text, and
  the tofu files take the descriptions from `descriptions.json`.
- The apply PATCHes the org settings and two repositories. The plan has to show only `description` and `topics`
  changing, plus one commit of the profile to `.github`.
- Two new issues, troupe and website, on the board as sub-issues of #108.
