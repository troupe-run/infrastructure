<!-- Source: troupe-run/infrastructure (org-profile/CONTRIBUTING.md). Change it there; this copy is written by the App. -->
# Contributing to troupe

Thanks for helping. This guide applies to every troupe-run repository that doesn't have a `CONTRIBUTING.md` of
its own. The [website](https://github.com/troupe-run/website) has its own.

## Licence and sign-off

Contributions are accepted under the repository's licence (Apache-2.0 for troupe itself), with a sign-off under
the [Developer Certificate of Origin](https://developercertificate.org/) (DCO). The sign-off is one line in each
commit, which `git commit -s` adds for you:

```
Signed-off-by: Your Name <you@example.com>
```

It certifies that you wrote the change, or otherwise have the right to submit it under the repository's licence.
You keep the copyright in your work. There's no separate agreement to sign.

Forgot it? `git commit --amend -s` fixes the last commit, and `git rebase --signoff main` fixes every commit on
your branch.

Members of the troupe-run organisation don't need the sign-off on commits they author and sign
cryptographically. Their work already belongs to the project's owner, HPS.GD PTY LTD.

## How work flows

troupe is built with [OpenSpec](https://github.com/Fission-AI/OpenSpec). GitHub holds what we want and its
status; OpenSpec holds what the system does and how each change will do it.

1. **An issue says what and why.** Use the Feature, Bug or Decision form. A Decision issue is an open question,
   with the research done: options, evidence and a recommendation.
2. **An OpenSpec change says how.** It lives under `openspec/changes/<name>/`, on a branch named `<name>`, with a
   proposal, spec deltas, a design and tasks. Its proposal cites the issue.
3. **A pull request delivers it.** It names the change and closes the issue (`Closes #12`). Specs, code and tests
   change together.
4. **Before the merge,** the change is archived on its branch, which updates `openspec/specs/`, so the pull
   request lands code, tests and specs together. It's merged by rebase.
5. **After the merge,** the issue gets a comment linking the PR and the change, and is closed.

Small fixes follow the same path. A bug fix adds the scenario that reproduces the bug to the spec.

## Milestones

Each milestone is a planned troupe release, and its description says what a user gets from it. Every repository
has the same milestones, so an issue anywhere is filed under the troupe release it's needed for. When a milestone's
last issue is closed, that version is released.

- **Planned work** goes in the release it's needed for.
- **Completed work** always has a milestone: the one of the work it arose from or, when nothing fits, the release
  that was in progress when it was done. That includes development process, org upkeep and flaky tests.
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
