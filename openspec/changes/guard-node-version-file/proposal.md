# Proposal

## Why

website's `main` is red (#155). The delivered `.github/workflows/guard.yml` sets up Node with
`node-version: 22.23.4` to install the OpenSpec CLI. website keeps its Node version in one place, `.nvmrc`, and its
`tests/unit/workflow-node-version.test.ts` (troupe-run/website#4) fails on any workflow that names its own. While that
test fails, website's guard refuses every commit that isn't OpenSpec-only, so troupe-run/website#31 is blocked.

## What Changes

- **The delivered `guard` workflow takes Node from the repository's `.nvmrc` when it has one** (the issue's option 1).
  Its only `actions/setup-node` step reads `node-version-file: .nvmrc` and has no `node-version` input, which is what
  website's test asks of every `setup-node` step, whatever its `if:`.
- **Where a repository has no `.nvmrc`** (this repository and troupe today), an earlier `run` step writes the
  workflow's pinned version to `.nvmrc` in the job's checkout before `setup-node` reads it. Nothing is committed. The
  pin sits in the job's `env` as `NODE_VERSION`, next to `OPENSPEC_VERSION`, in one named place. A repository's own
  `.nvmrc` is never overwritten.
- **A test here checks `guard.yml` against website's rule**, so a later edit that brings back a `node-version` input
  fails in this repository before it's delivered.
- **Delivery**: `guard.yml` is a delivered file. After merge, the owner-approved apply delivers it to troupe and
  website, and website's `uv run scripts/check.py` then passes on `main`.

Not changed: website's test (the issue's option 2, which would weaken website's rule for the one workflow it doesn't
own), the OpenSpec version, and how the guard runs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `guard-delivery`: one added requirement. The delivered `guard` workflow takes its Node version from the
  repository's `.nvmrc` when there is one, and from its own pin only when there isn't. It never names a Node version
  as a step input.

## Impact

- `.github/workflows/guard.yml`: the `setup-node` step and a new step before it. Job `env` gains `NODE_VERSION`.
- `scripts/tests/`: a new `test_guard_workflow.py`, using pyyaml as the other workflow tests do.
- `docs/development-workflow.md`: "Where the guard comes from" says where the guard check's Node version comes from.
- **Delivery** to troupe and website (spec: `guard-delivery`), through a plan the owner approves after merge. website's
  `.nvmrc` says `22`, so its guard runs OpenSpec on Node 22, as it does today with `22.23.4`. troupe has no `.nvmrc`
  and keeps the pin.
- No OpenTofu resource changes beyond the delivered file's content.
