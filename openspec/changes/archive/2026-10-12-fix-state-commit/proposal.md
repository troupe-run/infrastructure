# Proposal

Issue: #11 (follows #6, part of #1).

## Why

The first CI apply after `ci-apply` merged
([run 38200444558](https://github.com/troupe-run/infrastructure/actions/runs/38200444558)) applied correctly, then
failed to commit the new state:

```
/usr/bin/jq: Argument list too long
```

`tofu.yml` passes the base64-encoded state to `jq` as one command-line argument. The state is 159 KB, about 213 KB
encoded, and Linux refuses a single argument over 128 KB. So every apply leaves `main`'s state behind. The run kept
the new state (serial 7) as its `state-after-apply` artifact, as designed, and `main` still holds serial 6. That has
to be recovered before the next apply. The `ci-apply` probe never exercised the state commit with a real-sized
state, which is how this got through.

## What Changes

- **The state commit moves out of inline shell into `scripts/commit_state.py`:**
  - standard library only;
  - it sends the request body to GitHub's contents API directly, so no value ever goes through a command line;
  - it keeps the behaviour of design D4 of `ci-apply`:
    - skip when the state is unchanged;
    - send the planned blob's `sha`, so a changed file on `main` gets a 409 instead of being overwritten;
    - the same commit message.
- **It has tests:** a state far over 128 KB, the unchanged-state skip, the 409, and the request it builds. The `check`
  job runs them.
- **`tofu.yml` calls the script** in place of the shell step.
- **Recovery:** this change's pull request commits the artifact's state (serial 7) on its branch, through the README's
  break-glass path, so `main` catches up when it merges.
- **The script is proven against GitHub** on a throwaway repository: a real-sized file through the contents API, the
  409, and the skip.

Out of scope: any other change to the workflow, or to what is applied.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci-apply`: "The new state reaches main after every apply" gains a scenario for a state of any size, which is what
  failed.

## Impact

- **New:** `scripts/commit_state.py` and `scripts/tests/test_commit_state.py`.
- **Changed:**
  - `.github/workflows/tofu.yml`: one step;
  - `tofu/terraform.tfstate`: the recovered serial 7.
- **GitHub:** a throwaway repository, created and deleted for the proof.
- **The owner:** reviews the PR plan, which should report no changes, then merges.
