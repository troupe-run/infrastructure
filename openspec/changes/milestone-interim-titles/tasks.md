# Tasks

## 1. Prove the collision on a throwaway repository

- [x] 1.1 Create `troupe-run/infra-probe-milestones` (`gh repo create --public --add-readme`) and ask the owner to add it
  to the App's installation. Verify with a probe plan that can read the repository.
- [x] 1.2 Add `probe_milestones` to `tofu/probe/main.tf` (design D6), with the live title expression of design D1 and a
  comment naming the copy. Verify with `tofu fmt -check` and `tofu validate` in `tofu/probe`.
- [x] 1.3 Step 1: apply keys `a`, `b`, `c` titled `0.2.0`, `0.3.0` and `0.4.0`, file one issue in each, and record each
  issue's milestone number. Verify with `gh api repos/troupe-run/infra-probe-milestones/milestones`.
- [x] 1.4 Step 2: plan and apply the rotation with no interim titles. Record GitHub's error, and what the next plan
  shows. Verify it failed on the duplicate title. If it applied, stop and report on #128 and #129 (design, risks).
- [x] 1.5 Step 3: restore step 1, then apply the rotation with interim titles, then without them. Verify both plans
  show only updates in place, both apply, and each issue's milestone number matches 1.3.
- [x] 1.6 Delete the repository and the probe's state, `terraform.tfvars` and anything else 1.1 to 1.5 left. Verify
  `gh repo view troupe-run/infra-probe-milestones` fails and `git status` in `tofu/probe` shows nothing
  untracked. Put the results from 1.4 and 1.5 in a comment on #129.

## 2. Interim titles in the declaration's readers

- [x] 2.1 In `scripts/tests/test_milestones.py`, write tests for design D3 first: an interim title equal to another
  milestone's title, equal to its own title, equal to another interim title, empty, and not a string, each named in
  the message. A milestone with a unique interim title is valid. Verify they fail before 2.2.
- [x] 2.2 Extend `declaration_problems` for D3, and verify 2.1's tests pass.
- [x] 2.3 In `scripts/tests/test_oob.py`, write tests for design D4: a declared milestone on GitHub under its interim
  title, and under its title, reports nothing, and an undeclared title is still reported. Verify the first fails
  before 2.4.
- [x] 2.4 Make `undeclared_milestones` count interim titles as declared, update its comment, and verify 2.3's tests
  pass.
- [x] 2.5 Make `tofu/milestones.tf` apply the interim title (design D1). Update its header comment. Verify with `tofu fmt -check`, `tofu validate`, and a local plan against current state
  (fast-forward onto `origin/main` first) that shows no changes while the declaration has no interim titles.
- [x] 2.6 Update README's milestones row: a key and title can differ, the title is the version, and an interim title
  (design D2's format) lets titles move between milestones in two applies. Verify `uv run scripts/check.py` passes.

## 3. The declaration

- [x] 3.1 Write #128's titles, interim titles and new description into `tofu/milestones.json` (design D5). Verify
  `uv run scripts/check.py` passes.
- [x] 3.2 Check the website reads it: in a website checkout on `main`, with `TROUPE_MILESTONES` set to this worktree,
  call `readMilestones` and `readRoadmap` from `scripts/roadmap-lib.mjs`, the functions the build uses, without
  writing anything there. Verify the releases list 0.1.0, then 0.2.0 "Other runners", then 0.3.0 "Config by hand", up
  to 0.14.0 "Contained", then 0.15.0 to 1.0.0 unchanged. (Done this way, not with `npm run build`, so the website
  checkout stays untouched. The page itself is checked after #128, in its design D3.)
- [x] 3.3 Run a local plan against current state. Verify it shows 52 updates in place, 13 in each of troupe,
  infrastructure, website and `.github`, the 4 of key `0.14.0` with the new description too, and nothing created,
  destroyed or replaced.

## 4. Pull request and apply

- [ ] 4.1 Open the pull request with `Closes #129` and a link to #128, using `--body-file`. Verify the CI plan comment
  shows the same counts as 3.3.

## Workflow follow-up

- Archive the change on the branch, in the same push as ticking 4.1, and rebase onto `main`'s latest state commit
  before asking for the plan approval (memory: archive before plan approval).
- After the owner merges and approves the apply, verify with `gh api` that every managed repository has the 13
  interim titles and no other title changed, and that troupe's milestone 20 still holds #56 and #162. Comment on #129
  with the PR and archived change, close it, and set its card to Done.
- Start #128's change (`milestones-other-runners`): rebase it onto `main` after the state commit.
