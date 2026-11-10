## Context

See proposal.md, "Why". The review's prompt lives in one place, the `prompt` input of the `anthropics/claude-code-action`
step in `.github/workflows/claude-review.yml`. Its check list says, at step 2, that a ticked task in `tasks.md` is one
whose code and verification are in the pull request; its tier list calls "a stale reference" a nit. Nothing says that
a commit SHA is a different kind of reference from a path or a name.

What the review can see bears on how the rule is worded. It checks the pull request out with `fetch-depth: 1`, and its
tools are `gh pr comment`, `gh pr diff`, `gh pr view`, `gh issue view`, Read, Grep and Glob. It has no `git log` and
no `gh run view`, so it can't tell why a SHA isn't among the pull request's commits (`gh pr view --json commits`): a
rebase, a commit made in another checkout, or a typo all look the same. It can't look a CI run up either.

`scripts/tests/test_claude_review_workflow.py` pins sentences the prompt must say (`PROMPT_READS`, and single-purpose
tests such as `test_the_prompt_tells_the_review_to_resolve_a_nit_only_on_a_fix_and_never_a_decision`).

## Goals / Non-Goals

**Goals:**

- One sentence pair in the prompt, beside the rule it qualifies, that the review can apply without knowing why a SHA
  is missing.
- A test that fails when the sentences are removed.

**Non-Goals:**

- Resolving conversations already open for such a SHA. They're nits, and the author resolves them as now, with a
  reply that points at this rule. The prompt doesn't gain a "withdraw a finding" path for one kind of nit.
- Checking that a cited CI run belongs to the pull request. The review has no tool for it, and the issue asks only
  that a run id still counts as evidence, not that the review prove it.
- Telling agents to stop citing SHAs. A SHA in a task is still useful while the pull request is open; it's only not
  worth keeping current.

## Decisions

### D1. The rule covers every SHA that names no commit on the branch, not only ones a rebase removed

The issue's wording is "because the branch was rebased". The review can't see the cause (Context), so a rule that
depends on it would leave the review guessing, and a guess is the flag the issue is about. Every cause ends the same
way: merging by rebase rewrites the SHA, so none survives the merge, and re-citing buys nothing. The prompt therefore
says: a commit SHA that names no commit on the branch isn't a finding, at any tier, and don't ask for it to be
re-cited, because the pull request merges by rebase and every SHA is rewritten.

Alternative: tell the review to check the SHA against `gh pr view --json commits` and only let pass the ones that
look rebased. Rejected: there is no "looks rebased" test it can run, and it would cost a call for nothing.

### D2. The sentences sit in check 2, with the task rule they qualify

Check 2 is where the review judges ticked tasks, and a task's "CI run N on `<sha>`" is the case that keeps recurring.
The sentence after "A task in its `tasks.md` is ticked only if its code and its verification are in the pull request"
reads: a SHA the task cites that isn't on the branch neither counts against it nor is a finding (the reason), and a
CI run id it cites is still evidence. The nit tier's "a stale reference" stays as it is; the rule in check 2 is
specific and says "at any tier", so it isn't read as a nit either.

Alternative: qualify "a stale reference" in the nit tier. Rejected: it would leave the must-fix path (troupe#287 raised
it as "a ticked task with nothing behind it") open, which is where the costlier rounds came from.

### D3. A test pins the sentences

A new test, named for what it checks (the prompt says a SHA missing from the branch isn't a finding, and a run id is
still evidence), flattens the prompt's whitespace as the existing prompt tests do and asserts both phrases. Like the
others, it checks the prompt says it, not that a model obeys it; that is checked on this change's own review (tasks).

### D4. The docs say it where agents read about nits

`docs/development-workflow.md`, "Claude's review", gains a sentence after the tier table: the review doesn't flag a
cited commit SHA that a rebase removed, since merging by rebase rewrites every SHA, so there's no need to re-cite one
after a rebase. `CLAUDE.md` and the org guide don't list the tiers' contents, so they don't change.

## Risks / Trade-offs

- [A SHA that's simply wrong, say a typo in a design's evidence, goes unflagged] → It wouldn't survive the merge
  either, and the evidence that matters (the code, the test, a run id) is still checked. Accepted per the owner's
  2026-11-09 comment.
- [The model ignores the sentence] → This change's own review runs the new prompt (the workflow reviews itself); the
  task to read that run is the check. If it still flags, the wording is revisited on this pull request.
- [troupe and website keep the old prompt until delivery] → Delivery follows the merge with the owner's approval of
  the plan, as for every change to this file.

## Migration Plan

Merge, then the `tofu` workflow's plan on `main` shows `claude-review.yml` delivered to troupe and website; the owner
approves the apply. Open pull requests in those repositories pick up the new prompt on their next push or rebase.
Rollback is a revert through the same path.
