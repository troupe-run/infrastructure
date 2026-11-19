# Tasks

Load rule for every full check below: ask the orchestrator first (one heavy run at a time), check `uptime`, and start
only when the 1-minute load is under 40. Every commit is signed off (`git commit -s`).

## 0. Owner decisions

- [x] 0.1 Send the draft design to the owner and record the answers in design.md. Verify: Q1–Q4 and the four
      additions are quoted with their date in design.md's "Owner's decisions" (2026-11-19)

## 1. Probes (throwaway repositories only)

- [ ] 1.1 On a public `troupe-run/infra-probe-*` repository, run a workflow whose `GITHUB_TOKEN` has `issues: read`
      and `pull-requests: read`. It reads `dependencies/blocked_by` for an issue in that repository and for
      troupe-run/troupe and troupe-run/infrastructure issues, and `GET pulls/<n>` from a merge group run. Verify:
      every read returns 200 with the expected blockers, recorded in design D7. If one fails, stop and ask the owner
      (D7's fallback)
- [ ] 1.2 Once the owner has created `troupe-run-merge` (D10), install it on an `infra-probe-*` repository with a merge
      queue and probe the smallest permissions. Probe `enqueuePullRequest` with `expectedHeadOid` (right and stale
      head), `dequeuePullRequest`, a label and a comment, reading the variable and a run's artifact, and a push and a
      variable write, which must be refused. Verify: each result recorded in design D10, and the App's permissions
      trimmed to what's needed (the owner trims them on GitHub)

## 2. The rule's config (design D4)

- [ ] 2.1 Tests first, in `scripts/tests/test_auto_merge_config.py`. These must pass: the delivered `auto-merge.toml`
      gives each repository 800/30/15/40, and a repository's `protected` adds to the defaults. Each of these must
      fail, naming the key: an unknown key, a wrong type, a negative limit, a repository missing from the config, an
      unknown repository. Verify they fail before 2.2
- [ ] 2.2 Write `auto-merge.toml` and the strict reader in `scripts/auto_merge.py`. Verify 2.1 passes, and
      `mypy --strict` and `ruff` are clean

## 3. The conditions (design D2, D3, D5, D6)

Each condition is a function over a recorded pull-request shape. Fixtures are copied from real API responses of
troupe, infrastructure and website pull requests, not written by hand
([[learned--a-test-name-that-overclaims-is-worse-than-no-test]]).

- [ ] 3.1 Record fixtures in `scripts/tests/fixtures/auto_merge/`, with `gh api` as the owner's login (reads only):
      - a qualifying merged troupe pull request: its pull request, check runs, rules, threads, commits, closing
        issues and their blocked_by;
      - one each with an open thread, a Decision closed, a `needs:owner` close, a blocked close, a draft and a fork.
      Verify each fixture names its source URL in a `provenance.json`
- [ ] 3.2 Tests first, one or more per scenario of the `auto-merge` spec's requirements:
      - "Only a ready pull request…", "Every required check…", "No conversation…", "Every commit is signed off…",
        "The issues it closes…", "Nothing protected changes…";
      - the review result, with the `openspec/`-only carve-out and its stop on a code commit.
      Verify they fail before 3.3
- [ ] 3.3 Implement the conditions and the ordered judging (D3), with one summary line per pull request. Verify 3.2
      passes
- [ ] 3.4 Tests first, then implement size and complexity on a scratch git repository, reusing `quality_gates`' diff
      and lizard functions:
      - lines leave out generated files and prose;
      - files leave out only generated files;
      - one function of complexity 18 fails;
      - 40 one-line files fail on files and pass on complexity.
      Then replay the evaluator's size and complexity over 10 calibration pull requests. Verify the replay matches
      the calibration script's numbers for each (recorded in this task)
- [ ] 3.5 Tests first, then implement the switch (unset, `off`, `dry-run`, `on`, a bad value) and the markers:
      - queued once per head;
      - dry-run once per head, and again for a new head;
      - only `troupe-run-merge[bot]`'s comments count as markers;
      - `hold` dequeues only a pull request the App queued.
      Verify with a fake GitHub client that records every write, and that no write happens in `off` or on a bad
      value
- [ ] 3.6 Tests first, then implement the comment's content (spec: "A queued pull request records why"). Verify a
      golden comment for the qualifying fixture

## 4. The workflow and its credentials (design D1, D10, D11)

- [ ] 4.1 Write `.github/workflows/auto-merge.yml`:
      - triggers per D1;
      - the `auto-merge` environment;
      - checkout of main only;
      - token minted with exactly the permissions from 1.2;
      - no expression reading the event.
      Add a workflow test pinning those, like `test_dependabot_dispatch_workflow.py`. Verify the test passes and
      fails when a trigger or permission is changed
- [ ] 4.2 `tofu/auto_merge.tf`: the `auto-merge` environment (main only, no admin bypass), `MERGE_APP_CLIENT_ID`, and
      `AUTO_MERGE = "dry-run"` in the three repositories. Add `auto-merge` to `test_main_only_environments.py`.
      Verify `tofu fmt`, `validate` and the test pass
- [ ] 4.3 `hold` and `auto-merged` in `tofu/labels/workflow.json`. Verify the labels test passes and, at the PR's plan,
      the plan creates them in each managed repository
- [ ] 4.4 Declare the App in `oob/app-installations.json`, and its by-hand set-up in `oob/README.md`. Verify
      `uv run scripts/oob.py` reports no difference once the owner has created it

## 5. The review result and the dispatcher (design D6, D8)

- [ ] 5.1 Make `claude-review.yml`'s `completed` job write and upload `review-result`. Verify the workflow's tests
      pass, and on this pull request's own review run (memory: review-change-tests-itself) the artifact has this head
      and its coverage
- [ ] 5.2 Add the auto-merge job to `dependabot-dispatch.yml` per D8. Extend `test_dependabot_dispatch_workflow.py`:
      - each job starts only its workflow;
      - no event data is passed;
      - both are skipped in infrastructure.
      Verify the tests pass

## 6. The guard (design D7, D9)

- [ ] 6.1 Tests first for `blocked-by`, in the guard's tests, with a fake reader:
      - an open blocker in another repository;
      - a closed blocker;
      - the same repository;
      - an Epic blocker;
      - no blockers;
      - a release pull request;
      - a merge group's pull request read from its head_ref;
      - a head_ref of another shape;
      - a 403;
      - a closed issue that doesn't exist.
      Verify they fail before 6.2
- [ ] 6.2 Implement `blocked-by` in `guard.py ci`, and add `issues: read` and `pull-requests: read` to `guard.yml`.
      Verify 6.1 passes and the guard's tests pass on the three OSes in CI
- [ ] 6.3 Tests first, then refuse removing `hold` (D9): `gh pr edit` and `gh issue edit`, alone and in a comma list,
      any case. Adding `hold`, and removing another label, stay allowed. Verify the tests pass
- [ ] 6.4 `docs/development-workflow.md`: list `blocked-by` and the hold rule, and a new "Auto-merge" section with the
      rule, the switch, `hold` and what the comment means. `README.md`'s layout table gets the new files. Verify the
      docs' link check, and that each rule id in `guard.py` appears in the doc (the existing test)

## 7. Integration

- [ ] 7.1 A dry run of the evaluator from a local checkout, against the live open pull requests, with the owner's
      read-only login and `AUTO_MERGE` treated as `dry-run`. Writes go to a recorder, never GitHub. Verify the summary
      has one line per open pull request, and each verdict is checked by hand against two of them
- [ ] 7.2 The full check (`uv run scripts/check.py`), after asking the orchestrator. Verify it passes

## Workflow follow-up

- Draft PR (`Closes #275`, "Part of #320"), Claude's review acted on, marked ready, the plan approved by the owner,
  archived, merged by the owner.
- Owner: approve the apply, then the delivery to troupe and website. Comment on #275 with the PR and archived change.
- After a dry-run week, a follow-up change sets `AUTO_MERGE=on` and closes #320. The week's tally is posted on #320.
