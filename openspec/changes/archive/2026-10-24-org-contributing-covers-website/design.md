# Design

## Context

`org-profile/CONTRIBUTING.md` is delivered to `troupe-run/.github` by `github_repository_file.org_profile` in
`tofu/org_profile.tf`. A change to it is one in-place update in the plan and one App commit to `.github` on apply.
`scripts/tests/test_plan_needed.py` already makes a change to it need a plan.

Today the guide's sign-off rule is written for troupe only ("Apache-2.0 for troupe itself"). What the repositories
enforce is in `tofu/required-checks.json`, read 2026-10-24:

| Repository | Required checks | DCO? | Licence on GitHub |
|---|---|---|---|
| infrastructure | check, guard tests, guard (workflow rules), plan (pull request), DCO | yes | none |
| troupe | check, guard (workflow rules), DCO | yes | Apache-2.0 |
| website | test, guard (workflow rules) | no (owner, 2026-10-16; govern-website D3) | MIT, plus `LICENSE-CONTENT` (CC BY 4.0) |

The DCO App's config (`org-profile/.github/dco.yml`, `require: members: false`) is org-wide, so the members'
exception holds in every repository that requires DCO, not just troupe.

website's `CONTRIBUTING.md` (read 2026-10-24) is the source for the outside-fix text, the licence wording, the
trademark note and the Conventional Commits line. Each governed repository's check is `uv run scripts/check.py`
(troupe, infrastructure and website all have `scripts/check.py`).

## Goals / Non-Goals

**Goals:**
- One guide whose per-repository cases are checkable against the declared rulesets.

**Non-Goals:**
- Changing website's repository (troupe-run/website#31).
- A licence for `.github`. It holds only what GitHub expects (project context), and its files are this
  repository's, written by the App.
- Testing prose beyond the sign-off cases. The rest of the text is reviewed in the pull request.

## Decisions

### D1. The per-repository cases are one table

"Licence and sign-off" opens with a table, one row per governed repository:

```markdown
| Repository | Licence | Sign-off |
|---|---|---|
| [troupe](https://github.com/troupe-run/troupe) | Apache-2.0 | DCO |
| [infrastructure](https://github.com/troupe-run/infrastructure) | Apache-2.0 | DCO |
| [website](https://github.com/troupe-run/website) | MIT for code, CC BY 4.0 for content | None: no DCO, no CLA |
```

The DCO explanation, the `git commit -s` / `--amend -s` / `rebase --signoff` fixes and the members' exception
follow, unchanged in substance but worded for "a repository that takes the sign-off" instead of troupe. Then the
trademark note: the troupe name, logo, mark and characters are trademarks of HPS.GD PTY LTD and aren't covered by
the repository's licences.

A table, rather than prose per repository, gives the test (D3) a shape it can read without guessing at sentences.
The alternative, a section per repository, repeats the DCO explanation or makes readers jump between sections.

### D2. The rest of the text

- **Opening:** "This guide applies to every troupe-run repository." The sentence about website having its own goes.
  It doesn't mention website's own guide still existing. That guide is deleted by troupe-run/website#31, and a
  sentence about it would be undone by that ticket.
- **A fix from outside:** a new section after "How work flows", in website's wording made general: the `guard`
  check fails on a pull request made in GitHub's editor, because it isn't on a change's branch. That's expected. A
  maintainer puts the fix on a change branch of their own, credits the author with a `Co-authored-by:` line, links
  the pull request from theirs, and closes it when theirs merges. The author needn't do anything else.
- **How work flows:** step 3 gains "and the repository's check passes before every commit (each README says how to
  run it)". After the list: "Commit messages are [Conventional Commits](https://www.conventionalcommits.org/), for
  example `feat(cli): ...`, `fix(docs): ...`, `ci: ...`."
- **Milestones, Guardrails, Before you open a pull request, Security:** unchanged.
- The title stays "Contributing to troupe": troupe is the project every repository serves.

### D3. A test reads the table against `tofu/required-checks.json`

In `scripts/tests/test_org_profile.py`, a function returns the problems with the guide's sign-off table. It takes
the guide's text and the required checks, so fixtures can exercise it:

- Governed repositories are the keys of `required-checks.json`. Every one of them requires the guard's check, so
  the key set is the governed set. Deriving it means a newly governed repository fails until the guide has its row.
- Each governed repository needs exactly one row, found by its link text.
- A repository requiring a `DCO` check from the `dco` App needs a Sign-off cell starting `DCO`. One that doesn't
  needs a cell starting `None`.
- Each problem names the repository and which way it disagrees, for example
  `website: the guide says DCO, but its pull requests don't require the DCO check`.

Tests: the real guide passes; a fixture with a missing row, with DCO for a repository that doesn't require it, and
with None for one that does, each fail naming the repository. Each test is named for what it asserts.

- infrastructure's Licence cell must equal `pyproject.toml`'s `project.license` (spec: licensing). A difference
  names both, for example `infrastructure: the guide says MIT, but pyproject.toml declares Apache-2.0`.

Tests: the real guide passes; a fixture with a missing row, with DCO for a repository that doesn't require it, with
None for one that does, and with a licence other than the declared one, each fail naming the repository. Each test
is named for what it asserts.

The alternative, generating the table from `required-checks.json`, puts the guide's text in OpenTofu or a script,
which is more machinery than one table needs. The test keeps one source of truth for each fact (the rulesets for the
sign-off, `pyproject.toml` for the licence), and fails loudly when the guide doesn't follow it. troupe's and website's
licence cells aren't tested: their licences are in their own repositories, which this check can't read offline.

### D4. infrastructure's licence is set up the way troupe's is

The owner chose Apache-2.0 for infrastructure on 2026-10-24, to match troupe. troupe declares it in three places,
and infrastructure copies each one:

- **`LICENSE`:** byte-identical to troupe's, the standard Apache-2.0 text with its appendix left as a template. It's
  copied from `gh api repos/troupe-run/troupe/contents/LICENSE`, not typed out, so GitHub's licence detection matches
  it the way it matches troupe's. Copying exactly means a `diff` against troupe's file proves it.
- **`pyproject.toml`:** `license = "Apache-2.0"` and `license-files = ["LICENSE"]` (PEP 639), as troupe's does.
  `[tool.uv] package = false` means nothing is built from them, so they're metadata only. `uv lock --check` shows
  they leave the lock unchanged.
- **`README.md`:** a closing `## Licence` section in troupe's wording: `[Apache-2.0](LICENSE)`, then that the troupe
  name, logo, mark and characters are trademarks of HPS.GD PTY LTD and aren't covered by the licence. "mark" is added
  to troupe's wording, so it matches the guide's trademark note.

No copyright header goes in each file. troupe doesn't use them, and the `LICENSE` file covers the repository.

## Risks / Trade-offs

- [The two guides disagree until troupe-run/website#31 lands: website's still says the org's doesn't apply] → The
  order is #120's. website#31 waits on this, and its issue says so.
- [The guard's files are delivered from here into website, which is MIT. They're now Apache-2.0 files inside an MIT
  repository] → HPS.GD PTY LTD holds the copyright in both, so nothing conflicts. This was already unclear while
  infrastructure had no licence, and the change makes the delivered files' licence definite.
- [The test checks the table, not the prose around it] → The prose is reviewed in the pull request, and the table is
  the part that changes when a repository's rules do.

## Migration Plan

Merge, then the owner approves the `apply` of `main`'s plan. The plan should read `0 to add, 1 to change, 0 to
destroy`, the change being `github_repository_file.org_profile["CONTRIBUTING.md"]`. Rollback is a revert, applied
the same way. The licence files reach no other repository, so they add nothing to the plan. Once they're on `main`,
GitHub's licence API reports infrastructure as `Apache-2.0`.
