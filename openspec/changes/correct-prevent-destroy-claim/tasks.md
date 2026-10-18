# Tasks

## 1. The comment and the spec (D4, D5; spec: repositories)

- [x] 1.1 Rewrite the comment on `github_repository.this` in `tofu/modules/repository/main.tf` as D4 says:
      `prevent_destroy` refuses a destroy while this block is declared, and `archive_on_destroy` archives the
      repository when the block is deleted. Point at README.md. Verify `tofu fmt -check -recursive tofu` and
      `tofu validate` are clean, and `git diff` touches comment lines only
- [x] 1.2 Verify the delta spec agrees with D5: `openspec validate correct-prevent-destroy-claim --strict` passes, and
      the requirement no longer says a removed declaration fails the plan or that no repository is archived

## 2. The live state (D2)

- [ ] 2.1 Fast-forward onto `origin/main` if only the state commit is ahead, then read
      `uv run scripts/tofu.py state show module.repo_<name>.github_repository.this` for troupe, github, infrastructure
      and website. Verify each shows `archive_on_destroy = true`, and record the four lines. If any doesn't, stop and
      ask the owner

## 3. The probe (D1; needs the owner)

- [ ] 3.1 Create `troupe-run/infra-probe-<date>` with `gh repo create --public --add-readme`, and ask the owner to add
      it to the infrastructure App's installation. Open an issue on it labelled `bug` (ask the owner whether this
      throwaway issue goes on the roadmap board, which the board rule otherwise requires). Set `probe_repo` in
      `tofu/probe/terraform.tfvars`. Apply with `declared = true`. Verify: the repository and its labels are
      imported, and a second plan shows no changes
- [ ] 3.2 Plan with `-var declared=false`. Verify the plan fails on `prevent_destroy`, naming
      `module.probe[0].github_repository.this`, and record the output
- [ ] 3.3 Delete `module "probe"` and the two `import` blocks that target it, in the working tree only. Plan, then
      apply that plan. Verify: the plan lists the repository and the module's other resources as destroyed, with
      nothing refusing. Record the destroy list and the apply's output
- [ ] 3.4 Record the repository on GitHub: `gh repo view --json isArchived`, its labels, the issue's labels, its
      rulesets, and whether Dependabot alerts are on. Verify it's archived, not deleted. If it was deleted, or anything
      differs from D3's expectation, stop and take the result to the owner (design, Risks) before 4.1
- [ ] 3.5 `gh repo unarchive`, `git checkout tofu/probe/main.tf`, and apply with `declared = true`. Verify the apply
      re-imports the repository and recreates what 3.3 destroyed, and a second plan shows no changes. Record what
      didn't come back, such as the issue's label
- [ ] 3.6 Add the deleted-block probe to the header comment of `tofu/probe/main.tf`: the edit 3.3 makes and the
      recovery 3.5 runs. Verify `tofu fmt -check -recursive tofu` is clean and `git diff tofu/probe/main.tf` touches
      comment lines only
- [ ] 3.7 Delete the probe repository, then the probe's state and `terraform.tfvars`. Verify `gh repo view
      troupe-run/infra-probe-<date>` reports not found, and `git status --short --ignored tofu/probe` shows only the
      provider cache

## 4. README.md (D3)

- [ ] 4.1 Rewrite "An apply can't delete a repository" in README.md as D3 says, from what 3.2 to 3.5 showed: what
      `prevent_destroy` refuses, what a deleted block plans, what an approved apply then archives and loses, how to
      recover, and the `removed` block (its example kept). Verify each claim matches the recorded output, and that
      README.md no longer says removing a declaration makes the plan fail
- [ ] 4.2 Verify `uv run scripts/check.py` passes and a plan of the live root (`uv run scripts/tofu.py plan`) shows
      `No changes.`

## Workflow follow-up

- Commit each group as Conventional Commits, signed off, saying why. Check `git status` shows no probe edit first.
- Open the PR with `Closes #85`, quoting 2.1's state lines, 3.2's and 3.3's plan output, 3.4's and 3.5's findings,
  and 4.2's plan as evidence.
- Ask the owner whether they want a check-time test like #61's for repositories, as a follow-up issue (proposal:
  out of scope).
- Archive on the branch before the owner merges. After the merge, comment on #85 with the PR and the archived change,
  check it's closed and its card says Done, and remove the branch and worktree.
