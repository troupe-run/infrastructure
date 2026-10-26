# Design

## Context

`.github/workflows/guard.yml` sets up Node only to install the OpenSpec CLI that `openspec-strict` runs. It's
delivered to troupe and website (spec: `guard-delivery`), and it's this repository's own `guard` check too. Today
its `actions/setup-node` step has `node-version: 22.23.4`.

website's `tests/unit/workflow-node-version.test.ts` reads every workflow in `.github/workflows/` and, for each step:

- an `actions/setup-node` step must have `node-version-file: .nvmrc` (that literal string) and no `node-version`;
- any other step must have no `node-version` input.

It reads only each step's `uses` and `with`. It ignores `if:`, `run:` and `env`. website's `.nvmrc` says `22`.
troupe and this repository have no `.nvmrc`.

## Goals / Non-Goals

**Goals:**
- The delivered `guard.yml` passes website's test as written.
- Repositories without an `.nvmrc` still get a pinned Node version, declared once.

**Non-Goals:**
- Giving troupe or this repository an `.nvmrc`. Neither runs Node apart from this step.
- Checking that a repository's `.nvmrc` names a Node version the OpenSpec CLI supports. That's the repository's
  choice, and `openspec-strict` already fails, naming the cause, when the CLI can't run.

## Decisions

### D1. The fallback writes `.nvmrc` in the checkout, in a `run` step before `setup-node`

```yaml
env:
  OPENSPEC_VERSION: 1.14.3
  # The Node the OpenSpec CLI runs on where the repository has no .nvmrc of its own. One exact
  # version, moved by pull request. A repository's .nvmrc wins, so its single source holds.
  NODE_VERSION: 22.23.4
steps:
  - uses: actions/checkout@…
  - uses: astral-sh/setup-uv@…
  - name: Choose the Node version
    run: |
      if [ -e .nvmrc ]; then
        echo "Node from the repository's .nvmrc: $(cat .nvmrc)"
      else
        printf '%s\n' "$NODE_VERSION" > .nvmrc
        echo "No .nvmrc here, so Node $NODE_VERSION, the guard's pin"
      fi
  - uses: actions/setup-node@…
    with:
      node-version-file: .nvmrc
```

The `.nvmrc` the step writes stays in the runner's checkout and is never committed. It doesn't change what the
guard's `ci` entry judges (checked in `scripts/guard.py` before apply, 2026-10-26):

- The git-level rules (`run_ci`) read only git objects: the range's commits, `git diff-tree` of each, and
  `git show <rev>:<path>` for the archived tasks and the delivered list.
- The working tree is read only under `openspec/`. That's `matching_change`'s `openspec/changes/` lookup,
  `openspec_scope`'s and `openspec_strict`'s `is_dir` checks, and `openspec validate --all --strict`, run at the
  root, which validates `openspec/`.
- Nothing in the `ci` path reads `git status`, untracked files, or a file at the root other than through those.

This repository's own `guard` run, which has no `.nvmrc`, shows it in practice.

The test is in the shell, not in an `if: hashFiles('.nvmrc') == ''`, so it's one mechanism and the log says which
version was used.

Alternatives considered:
- **Two `setup-node` steps behind `if:`**, one reading `.nvmrc` and one pinned. website's test ignores `if:` and
  fails on the pinned one (the side agent's note, 2026-10-26).
- **An expression in `node-version-file`**, such as `${{ hashFiles('.nvmrc') != '' && '.nvmrc' || … }}`. The test
  wants the literal `.nvmrc`, and the fallback would still need a file to point at.
- **An `.nvmrc` in troupe and this repository.** That spreads the guard's Node pin into files the guard doesn't own,
  in repositories that otherwise have no Node, and a change to troupe's would need a troupe pull request.
- **The runner's preinstalled Node.** It isn't pinned, so it moves when GitHub updates the image.
- **Exempt delivered files in website's test** (the issue's option 2). It weakens website's rule for the one workflow
  it doesn't own, and it's a change on website's side.

### D2. The pin is `NODE_VERSION` in the job's `env`

It sits next to `OPENSPEC_VERSION`, the other version the job pins, and both move by pull request here. website's test
doesn't read `env`, and the rule it enforces is about website's Node, which comes from website's `.nvmrc`.

### D3. A test here holds `guard.yml` to website's rule

`scripts/tests/test_guard_workflow.py` reads `guard.yml` with pyyaml, as `test_ci_workflow.py` does, and checks:

- every `actions/setup-node` step has `node-version-file: .nvmrc` and no `node-version`, and no other step has a
  `node-version` input, ignoring `if:`, as website's test does. Each problem names the job and the step;
- the step that writes `.nvmrc` comes before the first `setup-node` step;
- that step, run in a temporary directory with bash, writes `NODE_VERSION` when there's no `.nvmrc`, and leaves an
  existing `.nvmrc` byte for byte as it was. It's skipped where bash isn't found.

website's test remains the authority. Task 3.1 runs it, unchanged, against the old and the new `guard.yml`, so the
rule here is checked against the real one, not a copy of it alone.

## Risks / Trade-offs

- [website's `.nvmrc` moves to a Node line the OpenSpec CLI doesn't support] → `openspec-strict` fails, naming the
  CLI failure, on website's own pull request that moves it. That's the right place to find out.
- [website's test changes shape (it starts reading `run:` or `env`)] → that's a change website makes by pull
  request, whose own CI then fails on the delivered file. Task 3.1's comparison is the record of what passed.
- [The fallback leaves an untracked `.nvmrc` in the job's checkout] → nothing later in the job reads the working
  tree's status (D1). The file goes when the job ends.
- [Our copy of website's rule drifts from website's] → D3 calls it a copy. Task 3.1 checks the real test.

## Migration Plan

1. Merge this change. The `tofu` workflow's plan on `main` shows `guard.yml`'s new content for troupe and website.
2. The owner approves the apply, which delivers `guard.yml` to both.
3. Verify: website's `guard` and CI runs on `main` pass, and `uv run scripts/check.py` passes on a fresh website
   `main`. troupe's `guard` run on `main` passes and logs the pinned version.

Rollback: revert the commit here and deliver again. The old file only puts website's check back to red, as it is now.
