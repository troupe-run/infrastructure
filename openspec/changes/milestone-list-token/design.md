# Design

## Context

See proposal.md for why. The list is made by `scripts/milestone_review.py` (needed-for-milestones design D4), run
by the "Issues with no milestone" step in two jobs of `.github/workflows/tofu.yml`:

- `pr-plan` (`contents: read`, `pull-requests: write`), guarded by `steps.secrets.outputs.available`, so it runs
  only where the secrets are, never on a fork's pull request.
- `plan` (workflow `contents: read` only), the plan of `main` the owner approves from.

The script reads `repos/troupe-run/<repo>` (for `has_issues`), then
`repos/troupe-run/<repo>/issues?milestone=none&state=open`, every page, and drops pull requests.

**What GitHub does (probe, 2026-11-02, recorded on #247).** In a throwaway public repository, jobs read
`issues?state=open` for troupe, website and infrastructure with their own `GITHUB_TOKEN`:

- With `contents: read` only, the list held every open issue and pull request, matching `open_issues_count` and the
  owner's login: troupe 67 of 67.
- With `contents: read` and `pull-requests: write`, the list held only the pull requests: troupe 10 of 67, no issues.

So `pr-plan`'s pull-requests permission is what narrowed #245's list, and the `plan` job had no gap. The pattern
suggests a token holding one of the two permissions sees only that kind, so an issues-only token would likely list
no pull requests.

Both jobs already hold the troupe-run-infrastructure App's key (`secrets.TF_VAR_github_app_pem`, App id 5272634) for
the plan itself. The App is installed on troupe, .github, infrastructure and website with `issues: write`, and no
pull-requests permission (`oob/app-installations.json`). `create-github-app-token` gives a token only the
`permission-*` inputs it lists (#238).

## Goals / Non-Goals

**Goals:**

- The list sees every open issue with no milestone in each repository, on a pull request's plan and on `main`'s.
- A token that can't see everything fails the step, whatever token that turns out to be.
- Neither job depends on the repositories being public to read the list.

**Non-Goals:**

- Changing what the list shows, where it's shown, or which plans show it.
- Changing any job's `GITHUB_TOKEN` permissions.

## Decisions

### D1. Both plan jobs read with an App token that can read issues and pull requests (owner, 2026-11-02)

A step "Token to read the issues" before each "Issues with no milestone" step, with the same guard (`if:`) as the step
it serves:

```yaml
uses: actions/create-github-app-token@<same pin as the file's other uses>
with:
  app-id: 5272634
  private-key: ${{ secrets.TF_VAR_github_app_pem }}
  owner: troupe-run
  repositories: troupe,.github,infrastructure,website
  permission-issues: read
  permission-pull-requests: read
```

The list step's `GH_TOKEN` becomes that token's output. "Post the plan on the pull request" keeps `${{ github.token }}`:
the comment is written by the job, and the App token can't write pull requests.

Pull requests are read so the token sees what `open_issues_count` counts (D2). The App gains `pull_requests: read` for
this: the owner grants it in the App's settings and accepts it on the installation, and `oob/app-installations.json`
declares it, so the drift check (spec: teams-and-access) agrees.

The repositories are listed by hand, matching `tofu/milestones.json`'s `repositories`. The workflow test derives the
expected list from that file, so a repository added there and not here fails `check.py` (the gap #238 showed with
lists pinned by hand). `metadata: read` comes with every App token, and gives `repos/troupe-run/<repo>`.

The `plan` job gets the token too, though its own token reads correctly today: that works only while the
repositories are public, and one token for both jobs keeps the two steps the same.

**Alternatives (owner chose D1):**

- *A separate job with a `contents: read` token*: no App change, but `pr-plan` would hand it the plan's JSON and wait
  for its section before posting, and it works only while the repositories are public.
- *An issues-only App token, checked against the search API's count of open issues*: no App change, but search
  lags, so a correct read could fail now and then.
- *`issues: read` on the job's `GITHUB_TOKEN`*: the probe suggests it would narrow the list to issues, and a
  `GITHUB_TOKEN` can't be given permissions on other repositories.

### D2. The script checks what it read against the repository's count

GitHub's repository object has `open_issues_count`: open issues plus open pull requests. A token that can't see one
kind lists fewer items than that, as #245's did (10 against 67 in troupe).

So the script lists **all** open items (`issues?state=open&per_page=100`, every page, no milestone filter), counts
them, and fails when the count is below `open_issues_count`, naming the repository and both numbers. It then keeps
the issues (not pull requests) whose `milestone` is `null`.

Reading at least as many as the count is accepted: an item opened between the two reads is the race, and the list is
then correct as of its own read.

**Alternatives:**

- *Keep `milestone=none` and compare a filtered count*: no repository-level count of issues with no milestone exists
  without search.
- *Probe the token's permissions*: that checks the token, not the answer. Comparing the answer catches any cause.

The cost is reading open items that have a milestone, and pull requests: a page or so per repository, once per
milestone-closing plan.

## Risks / Trade-offs

- [`open_issues_count` lags behind a close or transfer] → a lag makes it read high, which fails the step loud rather
  than short. Re-running the plan clears it.
- [A repository added to `tofu/milestones.json` but not to the token step] → the App token can't read it, and the
  read fails. The workflow test derives the list from the declaration, so `check.py` catches it first.
- [The App gains a permission] → read-only, on the four repositories it's already installed on. The drift check
  reports it if the declaration and GitHub ever disagree.
- [Shown only by a real milestone-closing plan] → the first proof in CI is the next release's closing plan. Until
  then the probe, a local run with a token minted as D1 mints it (tasks 3.3), and the unit tests are the evidence.
