<!-- Source: troupe-run/infrastructure (org-profile/CONTRIBUTING.md). Change it there; this copy is written by the App. -->
# Contributing to troupe

Thanks for helping. This guide applies to every troupe-run repository. Setting up and running a repository is in
its README.

## Licence and sign-off

Contributions are accepted under the repository's licence. Some repositories also ask for a sign-off on each
commit:

| Repository | Licence | Sign-off |
|---|---|---|
| [troupe](https://github.com/troupe-run/troupe) | Apache-2.0 | DCO |
| [infrastructure](https://github.com/troupe-run/infrastructure) | Apache-2.0 | DCO |
| [website](https://github.com/troupe-run/website) | MIT for code, CC BY 4.0 for content | None: no DCO, no CLA |

You keep the copyright in your work. There's no separate agreement to sign.

The troupe name, logo, mark and characters are trademarks of HPS.GD PTY LTD and aren't covered by any of these
licences.

### The DCO sign-off

Where a repository asks for it, the sign-off is under the
[Developer Certificate of Origin](https://developercertificate.org/) (DCO). It's one line in each commit, which
`git commit -s` adds for you:

```
Signed-off-by: Your Name <you@example.com>
```

It certifies that you wrote the change, or otherwise have the right to submit it under the repository's licence.

Forgot it? `git commit --amend -s` fixes the last commit, and `git rebase --signoff main` fixes every commit on
your branch.

Members of the troupe-run organisation don't need the sign-off on commits they author and sign
cryptographically. Their work already belongs to the project's owner, HPS.GD PTY LTD.

## How work flows

troupe is built with [OpenSpec](https://github.com/Fission-AI/OpenSpec). GitHub holds what we want and its
status; OpenSpec holds what the system does and how each change will do it.

1. **An issue says what and why.** Use the Feature, Bug or Decision form. A Task or an Epic has no form: a
   maintainer sets its type. A Decision issue is an open question, with the research done: options, evidence and a
   recommendation.
2. **An OpenSpec change says how.** It lives under `openspec/changes/<name>/`, on a branch named `<name>`, with a
   proposal, spec deltas, a design and tasks. Its proposal cites the issue.
3. **A pull request delivers it.** It names the change and closes the issue (`Closes #12`). Specs, code and tests
   change together, and the repository's check passes before every commit (its README says how to run it).
4. **Claude's review is acted on.** It reviews each push, and posts every finding as a conversation on the lines
   it's about, labelled for who resolves it. A **must-fix** is fixed, or answered with a reason, and the review
   resolves it on its next run once it's addressed. A **nit** is fixed, or answered (a follow-up issue, or why it
   isn't worth it), and the author resolves it. A **decision** is the maintainer's, and so is a must-fix still in
   dispute after the re-review. The review runs again on each push; a must-fix answered with a reply alone is
   judged once the last `claude review` run is re-run. The pull request can't merge while any conversation is open.
5. **Before the merge,** the change is archived on its branch, which updates `openspec/specs/`, so the pull
   request lands code, tests and specs together. It's merged once every conversation is resolved, by rebase, through
   the repository's merge queue where it has one: the queue tests it on top of `main` and whatever is queued ahead of
   it, then lands what it tested.
6. **After the merge,** the issue gets a comment linking the PR and the change, and is closed.

Small fixes follow the same path. A bug fix adds the scenario that reproduces the bug to the spec.

Commit messages are [Conventional Commits](https://www.conventionalcommits.org/), for example `feat(cli): ...`,
`fix(docs): ...` or `ci: ...`.

## A fix from outside

A pull request made outside this workflow, for example in GitHub's editor, fails its `guard` check, because it isn't
on an OpenSpec change's branch. That's expected. A maintainer carries your fix through the workflow instead: they
put it on a change branch of their own, credit you as its co-author with a `Co-authored-by:` line, link your pull
request from theirs, and close yours when theirs merges. You don't need to do anything else.

## How issues are related

Work often grows while it's being done. Relate issues so that it still reads as one piece of work, whichever
repositories it's in. Each relationship answers one question:

- **Sub-issue of an Epic:** the parts of one outcome, in any repository. It answers "is the outcome done?" An issue
  with sub-issues is an Epic, and it's done when every sub-issue is.
- **Blocked by:** a real prerequisite, a Decision included. It answers "can this start?"
- **"Arose from" in the body:** where a follow-up came from, as a line such as
  `Arose from troupe-run/troupe#139.` The milestone rule below reads it.

Work found while doing a change becomes a sub-issue of the Epic its origin belongs to, so the Epic isn't done until
that work is, and it gets the "arose from" line too. When the origin has no Epic, or the follow-up isn't needed for
the outcome (it's parked, optional, or a new outcome of its own), it gets only the "arose from" line.

Every issue has a type: Epic, Feature, Bug, Task or Decision.

## Milestones

Each milestone is a planned troupe release, and its description says what a user gets from it. Every repository
has the same milestones, so an issue anywhere is filed under the troupe release it's needed for. When a milestone's
last issue is closed, that version is released.

- **Planned work** goes in the release it's needed for.
- **Completed work** always has a milestone: the one of the work it [arose from](#how-issues-are-related) or, when
  nothing fits, the release that was in progress when it was done. That includes development process, org upkeep and
  flaky tests.
- **Open work that isn't planned** has no milestone. 1.0.0 holds only the stability promise.
- **A Decision** goes in the milestone of the earliest work it blocks or, when it blocks nothing, of the work it
  shaped.

Milestones may be renumbered, reordered or re-described as plans change. They're declared in
[`tofu/milestones.json`](https://github.com/troupe-run/infrastructure/blob/main/tofu/milestones.json), and
[troupe#139](https://github.com/troupe-run/troupe/issues/139) records why.

## Guardrails

Each repository that builds with this workflow enforces it with git hooks, Claude Code hooks and a GitHub check.
They refuse a shortcut with the rule's name and the fix. The rules, and how an override works, are in
[development-workflow.md](https://github.com/troupe-run/infrastructure/blob/main/docs/development-workflow.md).

## Before you open a pull request

Run the repository's checks. Each repository's README says how. A pull request needs every check to pass.

## Security

Please don't report security problems in public issues. See the [security policy](SECURITY.md).
