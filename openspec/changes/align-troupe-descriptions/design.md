# Design

## Context

The text is in proposal.md (What Changes), as the owner settled it on 2026-10-20. On GitHub's side it lives in three
places today:

- `tofu/org.tf`: `github_organization_settings.org.description`, declared as `""`.
- `tofu/repositories.tf`: each repository module's `description` and `topics`. The module already passes `topics`
  through, with a default of `[]`.
- `org-profile/profile/README.md`: hand-written Markdown, which `github_repository_file` delivers to `.github`
  byte for byte. The org-profile spec makes this file the source, and a plan shows any difference.

The repository already declares data as JSON that both OpenTofu and the Python tests read: `dns.json`,
`milestones.json` and `labels/*.json`.

## Goals / Non-Goals

**Goals:**
- One place in this repository holds the tagline, sentence and status line, and nothing else here restates them
  without a check.

**Non-Goals:**
- Generating the org profile from a template. It stays hand-written (D2).
- Any check that reads troupe's or website's files (D3).

## Decisions

### D1. The text is declared in `tofu/descriptions.json`

```json
{
  "tagline": "Your agents need a director.",
  "sentence": "troupe runs your development process with a team of agents, asking only when it needs you.",
  "status": "Pre-alpha: there's nothing to install yet."
}
```

`tofu/repositories.tf` decodes it into a local, and the org's description and `repo_troupe`'s description are both
`"${tagline} ${sentence}"`. `org.tf` uses the same local, so the joining rule is written once.

- *Why JSON:* OpenTofu reads it with `jsondecode(file(...))`, and a test reads it with the standard library, as
  `dns.json` and `milestones.json` already are. A tofu `locals` block would make the test parse HCL with a regex.
- *Alternative, an input variable:* the text isn't secret or per-environment, and a variable's value would live
  outside the reviewed diff.
- `status` isn't used by OpenTofu. It's here so that the one file holds all three strings the profile is checked
  against, and the brand guide's copy has a single counterpart here (D3).

### D2. The org profile stays hand-written and is checked against the JSON

A new test, `scripts/tests/test_descriptions.py`, reads `descriptions.json` and the profile. It fails, naming the
missing string, unless the profile carries the tagline (as the bold line under the heading), a paragraph that starts
with the sentence, and the status line. It also fails when the tagline plus the sentence come to more than 160
characters, giving the length. 160 is the limit GitHub's settings page sets on an org's description. The test checks
it before a plan, where an over-long description would fail only at apply.

- *Alternative, `templatefile()` for the profile:* the file in `org-profile/` would stop being the literal content
  delivered to `.github`, which the org-profile spec relies on ("the source of `.github`'s files is this repository",
  adopted byte for byte). The profile's other lines (links, roadmap) are prose that doesn't belong in a template's
  variables either.
- The paragraph's second sentence ("Work branches and loops…") isn't in the JSON. Only the profile and the README use
  it, and neither the org's description nor troupe's repository description does. The check pins the parts that have
  more than one copy here.

### D3. The brand guide is the reference across repositories, and nothing checks across them

The canonical set, including the paragraph and the page title, is recorded in website's brand guide, which already
calls itself "the reference for anything that carries the troupe brand: the site, the docs, GitHub". That's a website
change, raised as its own issue. troupe's README and website's hero, title and meta description change through their
own issues and pull requests (the constraint that a product repository's files change only through its own checks).

No check here reads those repositories. The guard's checks work offline, and #120 decided how troupe and its docs
stay in step for `/docs` only. `tofu/repositories.tf` carries a comment that the text follows the brand guide, so
anyone changing `descriptions.json` knows where else it's written.

- *Alternative, website reads `descriptions.json` at build time:* a build dependency from website on this
  repository's tree, for three strings. If drift recurs, that's the case for it, and it belongs to website.

### D4. The other repositories' work is two issues, sub-issues of #108, and this PR closes #108

`pr-closes-issue` needs `Closes #n` on every pull request, so #108 can't stay open as a standing ticket across PRs.
This change does #108's steps 1 and 2 (agree the text, list each repository's changes) and step 3 on GitHub's side.
Each of the other two repositories gets an issue that quotes the agreed text, is opened on the troupe roadmap board,
and is linked to #108 as a sub-issue. The after-merge comment on #108 names both.

- website's issue: record the canonical set in the brand guide (§7, or a section of its own as website decides), and
  apply it to `src/content/copy/hero.md` (subtitle) and `src/pages/index.astro` (title and description).
- troupe's issue: the README's paragraph.

### D5. The values chosen outside the owner's answers

- website's description: "The troupe.run website and landing page". The current wording without the em dash. The
  brand guide §1 says troupe.run names the site.
- Topics, owner-approved list: troupe `ai-agents`, `developer-tools`, `human-in-the-loop`, `workflow`, `python`;
  website `astro`, `website`. They're listed alphabetically, as infrastructure's are. The plan after the apply is
  checked for a reorder (tasks, Workflow follow-up).

## Risks / Trade-offs

- [An update PATCHes the whole repository, and once turned a null homepage into `""`] → troupe and website both
  declare `homepage_url`. The plan is read for any change beyond `description` and `topics`, and the PR's plan comment
  is the evidence.
- [Org settings PATCH sends every declared field] → it's been updated in place before (d930670) with no side effects.
  The plan has to show only `description`.
- [GitHub's limit for an org's description might not be 160 through the API] → the text is 119 characters, well
  inside it. If the API's limit turns out to differ, the test's constant changes and the text doesn't.
- [The README and the website lag behind GitHub until their issues land] → that's a short window of the same drift
  #108 describes, now tracked by two board items.

## Migration Plan

Merge, then the owner approves `apply` on main. The App commits the profile to `.github`. Check the org's page and
both repositories show the new text. Rollback is a revert PR and another apply. Nothing is deleted.
