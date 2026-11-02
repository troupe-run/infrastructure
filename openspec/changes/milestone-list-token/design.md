# Design

## Context

See proposal.md for why. The list is made by `scripts/milestone_review.py` (needed-for-milestones design D4), run
by the "Issues with no milestone" step in two jobs of `.github/workflows/tofu.yml`:

- `pr-plan` (`contents: read`, `pull-requests: write`), guarded by `steps.secrets.outputs.available`, so it runs
  only where the secrets are, never on a fork's pull request.
- `plan` (workflow `contents: read` only), the plan of `main` the owner approves from.

Both jobs already have `secrets.TF_VAR_github_app_pem`, the troupe-run-infrastructure App's key (App id 5272634),
for the plan itself. That App is installed on troupe, .github, infrastructure and website with `issues: write`
(`oob/app-installations.json`). The drift job already mints a token from it for the four repositories with
`permission-issues: read`, so the shape is known to work. `create-github-app-token` gives a token only the
`permission-*` inputs it lists (#238).

The script reads `repos/troupe-run/<repo>` (for `has_issues`), then
`repos/troupe-run/<repo>/issues?milestone=none&state=open`, every page, and drops pull requests.

## Goals / Non-Goals

**Goals:**

- The list sees every open issue with no milestone in each repository, on a pull request's plan and on `main`'s.
- A token that can't see issues fails the step, whatever token that turns out to be.

**Non-Goals:**

- Changing what the list shows, where it's shown, or which plans show it.
- Giving any job's `GITHUB_TOKEN` a new permission.
- Changing the troupe-run-infrastructure App's permissions or installations.

## Decisions

### D1. Mint an issues-read token from the infrastructure App in each plan job

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
```

The step's `GH_TOKEN` becomes that token's output. "Post the plan on the pull request" keeps `${{ github.token }}`:
the comment is written by the job, and the App token can't write pull requests.

The repositories are listed by hand, matching `tofu/milestones.json`'s `repositories`. The workflow test derives the
expected list from that file, so a repository added there and not here fails `check.py` (the gap #238 showed with
lists pinned by hand).

`metadata: read` comes with every App token, and gives `repos/troupe-run/<repo>` (`has_issues`, the count in D2).

**Alternatives:**

- *`issues: read` on the job's `GITHUB_TOKEN`*: covers infrastructure only. A `GITHUB_TOKEN` can't reach other
  repositories (#247).
- *A token from another App* (dependabot, release): each has its own purpose and spec, and its key isn't in these
  jobs. Adding one would be a new secret for no gain.
- *One token for the whole job, reused by the plan*: the plan's provider builds its own credentials from the key.
  A shared token would need the union of permissions. A token per purpose stays narrow.

### D2. The script checks what it read against the repository's count

GitHub's repository object has `open_issues_count`: open issues plus open pull requests, readable with `metadata`.
With a token that can't see issues, the issues list holds only the pull requests, so it comes up short of that
count. That's the case #245 hit.

So the script lists **all** open items (`issues?state=open&per_page=100`, every page, no milestone filter), counts
them, and fails when the count is below `open_issues_count`, naming the repository and both numbers. It then keeps
the issues (not pull requests) with no milestone, filtering locally (`milestone` is `null`).

Reading at least as many items as the count is accepted: an issue or pull request opened between the two reads is
the race, and the list is then correct as of its own read.

**Alternatives:**

- *The search API's count* (`is:issue is:open no:milestone`): the issue's suggestion. Search is a separate index
  that lags, so it can disagree on a correct read and fail the step for nothing, and its rate limit is lower. It
  also has to be shown to fail, rather than answer 0, under a token that can't see issues.
- *Keep `milestone=none` and compare a filtered count*: no repository-level count of issues with no milestone exists
  without search.
- *Probe the token's permissions*: App installation tokens don't describe themselves on a cheap endpoint, and that
  checks the token, not the answer. Comparing the answer catches any cause.

**Precondition, tested before D2 is built (owner, 2026-11-02).** The count includes pull requests, but D1's token
is `issues: read` only, and the App has no pull-requests permission (`oob/app-installations.json`). #245 showed the
issues list returns only what the token may see. If an issues-only token likewise lists no pull requests, every read
falls short of the count and the step always fails. So the first apply task mints an issues-only token locally and
checks whether the list includes pull requests:

- **It does:** D2 stands as written.
- **It doesn't:** stop and take the result to the owner, choosing between giving the App `pull_requests: read`
  (declared in `oob/app-installations.json`, granted by the owner in the App's settings, and added to D1's token),
  which keeps this check exact, and comparing the issues read with the search API's count of open issues, which
  needs no App change but can fail a correct read while search lags. The spec holds either way; the chosen one is
  recorded here before 2.x.

The cost is reading open issues that have a milestone too. That's a few pages at most per repository, once per
milestone-closing plan.

### D3. Prove both halves on a throwaway repository before relying on them

D2 rests on two GitHub behaviours, both seen only indirectly in #245's run: a `GITHUB_TOKEN` with no issues
permission gets only pull requests from the issues list, and still sees `open_issues_count` with issues counted. A
public `troupe-run/infra-probe-milestone-list` with one open issue and one open pull request, and a workflow that
reads both with `contents: read` only, for itself and for website, shows both. Then delete the repository. That the
App token does see the issues is shown locally, with a token minted as D1 mints it (tasks 3.3). If either behaviour isn't as expected, stop
and bring the finding back before writing D2's code.

## Risks / Trade-offs

- [`open_issues_count` lags behind a close or transfer] → a lag makes it read high, which fails the step loud rather
  than short. Re-running the plan clears it. The probe and the first real run show how often it happens.
- [A repository added to `tofu/milestones.json` but not to the token step] → the App token can't read it, and the
  read fails. The workflow test derives the list from the declaration, so `check.py` catches it first.
- [The App key is now used in one more step per plan job] → it's the same secret the job already holds for the plan,
  and the token is read-only and short-lived.
- [Shown only by a real milestone-closing plan] → the first proof of D1 in CI is the next release's closing plan.
  Until then the probe (D3) and the unit tests are the evidence, and the closing change's PR should check the list
  against a local run once.
