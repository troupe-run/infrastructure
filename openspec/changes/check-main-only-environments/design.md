# Design

## Context

See proposal.md for why. The current declarations:

- `tofu/environments.tf` declares infrastructure's CI environments as one resource,
  `github_repository_environment.ci`, with `for_each = local.ci_environments`. That map gives each environment
  `approval` and `main_only`. Two `dynamic` blocks turn those into a reviewer (`users = [local.owner_user_id]`) and a
  `deployment_branch_policy` (`protected_branches = false`, `custom_branch_policies = true`).
  `github_repository_environment_deployment_policy.main_only` adds `branch_pattern = "main"` for each `main_only`
  entry. `can_admins_bypass = false` is set on all of them. `plan-main` and `apply` are main-only, and `plan-pr` isn't.
- The same file declares the website's `github_repository_environment.github_pages`, with a literal
  `deployment_branch_policy`, `can_admins_bypass = false`, `prevent_destroy`, and the policy
  `github_pages_main_only` (`branch_pattern = "main"`).
- `tofu/release.tf` declares troupe's `github_repository_environment.release` and `release_main_only` in the same
  literal shape, without `prevent_destroy`.
- `scripts/tests/test_required_checks.py` is the precedent. It reads `.tf` files as text with regular expressions,
  and fails with "update this test" when a declaration isn't in a shape it knows.
- `scripts/check-paths.toml` already puts both `.tf` files in the `tofu` scope, so a test that reads them is marked
  `tofu` and runs on any change to them.

What `prevent_destroy` does and doesn't cover was shown in the #52 session and adopt-org's probe. It refuses a plan
that would destroy an instance while the resource block is in the configuration (`count = 0`, a removed `for_each`
key, a forced replacement). It does nothing once the block itself is deleted.

## Goals / Non-Goals

**Goals:**

- `scripts/check.py` fails, before any plan exists, when a change removes or weakens any of the four main-only
  environments. The failure names the environment and what's wrong.
- The list of protected environments, and what each must hold, is in one named place.
- The comment on `github_pages` no longer says `prevent_destroy` catches the block's removal.

**Non-Goals:**

- Stopping a change made on GitHub by hand. The plan already shows that as drift and reverts it (existing scenarios).
- `plan-pr`'s approval, which isn't main-only.
- A guard in CI that inspects the plan for destroyed environments (owner's choice, #61 notes).
- Protecting against someone who edits the test and the declaration together. The test makes that removal visible in
  the diff the owner reviews. It can't forbid it, and isn't meant to.

## Decisions

### D1. Four environments, and what each must hold

The test holds one table, the single place that says which environments are main-only:

| Environment | Repository module | Owner as required reviewer |
|---|---|---|
| `plan-main` | `repo_infrastructure` | not checked |
| `apply` | `repo_infrastructure` | yes |
| `release` | `repo_troupe` | not checked |
| `github-pages` | `repo_website` | not checked |

For each, the declaration must:

1. exist, on that repository (moving it to another repository leaves the original undeclared);
2. set `can_admins_bypass = false`;
3. have a deployment branch policy with `custom_branch_policies = true` and `protected_branches = false`;
4. have exactly one `github_repository_environment_deployment_policy` naming it, with `branch_pattern = "main"`. A
   second policy, or a different pattern, would widen it;
5. for `apply` only, list `local.owner_user_id` as its reviewer. The test checks the reference, not the user id
   itself, so the id is still declared only in `locals`.

`plan-main` has no reviewer by design (ci-apply D2), so the test doesn't check that either way. Asserting it has none
would test a choice the issue isn't about.

**Alternative considered:** `github-pages` only, as #61's minimum. Rejected: `apply` and `release` carry the same
risk and worse (`apply` would come back without its reviewer, and `release` holds the release App's key). The issue
asks for them too.

### D2. Read the declarations as text, and refuse unknown shapes

OpenTofu has no offline command that prints the parsed configuration. `show` reads a plan or the state, and
`console` needs the encrypted state, so the passphrase. Checked against `tofu -help` on OpenTofu 1.13.1. So the
options were:

- **Text, as `test_required_checks.py` does (chosen).** Standard library only, offline, no secret, and fast enough
  to run on every commit. The test strips comments, finds each resource block by matching braces, and reads its
  attributes. For `ci` it reads `local.ci_environments` and resolves the two `dynamic` blocks' `for_each`
  conditions (`each.value.approval ? [1] : []`, `each.value.main_only ? [1] : []`) against each entry. The policy
  resource's `for_each` filter (`if env.main_only`) is resolved the same way. Anything it can't read in those shapes,
  such as a different condition, a computed `can_admins_bypass` or an environment it can't find, is a failure that
  says to update the test. It isn't skipped, so a refactor can't quietly turn the check into a pass.
- **`tofu test` with `mock_provider`.** It evaluates the real configuration, `for_each` and all. Rejected for now:
  the root has the encryption block with a required ephemeral variable, 35 `import` blocks and Cloudflare data
  sources, none of which have been run under mocks. It needs `tofu init` first, which `check.py` runs after the
  tests. Making it work is a probe of its own, for a check that text handles.
- **An HCL parser (`python-hcl2`) as a dev dependency.** It parses, but doesn't evaluate `for_each` or `dynamic`, so
  the test would still resolve them by hand. It's a new dependency for little gain.

### D3. Problems are named, and every one has a test that produces it

As in `ci_trigger_problems`, one function returns a list of problems for given file texts, such as
`"apply: can_admins_bypass isn't false"` or `"github-pages: not declared"`. The real files must give an empty list.
Each weakening in D1 then gets a test that edits the real text in memory and checks the exact problem named:

- the `github_pages` block deleted, and the `release` block deleted;
- `"apply"` removed from `ci_environments`, and `main_only = false` on `plan-main`;
- `can_admins_bypass = true` on one literal block and on `ci`;
- `protected_branches = true`, and `custom_branch_policies = false`;
- the main-only policy deleted, its pattern changed to `"*"`, and a second policy added for the same environment;
- `approval = false` on `apply`, and the reviewer's `users` emptied;
- `github_pages` moved to `module.repo_troupe`;
- an unknown shape (for example, a `dynamic` condition rewritten), refused with "update this test".

Each mutation test is seen to fail before the code that names it exists. The real-files test passes on today's
`main`, which is correct: the declarations are right now, and the test guards them from here on.

### D4. The comment on `github_pages`

The `lifecycle` comment changes from "Deleting it would let the next deploy recreate it with no branch rule (design
D5)" to say that `prevent_destroy` refuses a plan that would destroy it while this block exists, and that deleting the
block removes that guard too, which `scripts/tests/test_main_only_environments.py` catches. The pointer to a `removed`
block stays. The `ci` and `release` declarations get a one-line comment naming the test, so whoever edits them knows
it's there. Archived website-environment D5 isn't edited. Archived changes record what was decided at the time, and
this change records the correction.

## Risks / Trade-offs

- **The text reader is tied to today's shapes.** A refactor of `environments.tf` must update the test too. That's
  the intended cost: D2 makes it a loud failure, never a silent pass.
- **The test protects the declaration, not GitHub.** A change made on GitHub is still caught only by the next plan.
- **README.md's repository sentence is still wrong** until #85 is done. Repositories have
  `archive_on_destroy`, so the damage there is an archive, not a loss.

## Decided

- **README.md line 145** ("Removing a repository's declaration makes the plan fail on `prevent_destroy`") has the
  same flaw as website-environment D5. The owner chose a follow-up issue (2026-10-18): #85, on the roadmap. This
  change doesn't touch it.
- **No `prevent_destroy` on `ci` or `release`** (owner, 2026-10-18). On `ci` it would refuse a plan that drops
  `"apply"` from the map, because the block stays, but the test already catches that before a plan exists, and it
  would also stop `plan-pr` being dropped on purpose.
