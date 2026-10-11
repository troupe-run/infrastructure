# Contributing to troupe

Thanks for helping. This guide applies to every troupe-run repository that doesn't have a `CONTRIBUTING.md` of
its own. The website ([troupe-run.github.io](https://github.com/troupe-run/troupe-run.github.io)) has its own.

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
2. **An OpenSpec change says how.** It lives under `openspec/changes/<name>/`, with a proposal, spec deltas, a
   design and tasks. Its proposal cites the issue.
3. **A pull request delivers it.** It names the change and closes the issue (`Closes #12`). Specs, code and tests
   change together.
4. **After the merge,** the change is archived, which updates `openspec/specs/`. Then the issue gets a comment
   linking the PR and the change, and is closed.

Small fixes follow the same path. A bug fix adds the scenario that reproduces the bug to the spec.

## Before you open a pull request

Run the repository's checks. Each repository's README says how. A pull request needs every check to pass.

## Security

Please don't report security problems in public issues. See the [security policy](SECURITY.md).
