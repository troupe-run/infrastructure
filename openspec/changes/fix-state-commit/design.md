# Design

## Context

- **The failing step,** "Commit the state to main as the App" in `.github/workflows/tofu.yml`:
  - It builds the contents-API request with `jq -n --arg content "$(base64 -w0 tofu/terraform.tfstate)"`.
  - Linux limits a single argument to 128 KB (`MAX_ARG_STRLEN`), and the state is 159 KB, about 213 KB in base64. So
    `exec` fails with `Argument list too long` (exit 126).
  - The state only grows as the org does, so this fails on every apply from now on.
- **Everything around the step worked:**
  - the apply;
  - keeping the state as the `state-after-apply` artifact;
  - minting the App's installation token.

  `main` holds serial 6. The artifact, downloaded and checked, holds serial 7 of the same lineage, and is still
  encrypted.
- **Conventions:** helper scripts here are standard-library Python, run with `uv run --no-project` in workflows, and
  covered by `scripts/tests` (`check.py` runs them; CI's `check` job is on Linux).

## Goals / Non-Goals

**Goals:**
- The state commit works for a state of any size the contents API accepts (up to 100 MB).
- The behaviour of `ci-apply` design D4 is unchanged:
  - skip when the state is unchanged;
  - send the planned blob's `sha`, so a changed `main` gets a 409, not an overwrite;
  - the same message;
  - a failure fails the run.
- That behaviour has tests, and is proven once against GitHub.
- `main`'s state is recovered.

**Non-Goals:**
- **Changing who commits** (the App's token, minted as before) or anything else in the workflow.
- **A different state store.**

## Decisions

### D1. A small Python script instead of shell

`scripts/commit_state.py --repo R --branch main --path tofu/terraform.tfstate --planned SHA --run-url URL`, with the
token in `GH_TOKEN` and the API base in `GITHUB_API_URL` (default `https://api.github.com`, which Actions also sets):

1. It reads the state file and computes its git blob ID in Python (`sha1(b"blob <len>\0" + content)`).
2. It reads the planned blob ID with `git rev-parse SHA:path`. That argument is tiny.
3. If the two match, it prints that the state is unchanged and exits 0.
4. Otherwise it builds the JSON body in memory and sends it with `urllib`: `PUT /repos/R/contents/path` with
   `message`, base64 `content`, `sha` = the planned blob, and `branch`. It prints the new commit's SHA.
5. If GitHub refuses, for example with a 409 because `main`'s file changed or a 422, it prints the status and
   GitHub's message, and points at the `state-after-apply` artifact and the README's break-glass section. It then
   exits 1, so the run fails.

**Why Python and not `jq --rawfile`:**
- `--rawfile` would fix this one argument.
- But the step would still have no tests, and "no test" is how this got through.
- Python with injectable I/O can be tested on every OS, like the guard.

### D2. Tests (`scripts/tests/test_commit_state.py`)

- **Unit tests,** with the HTTP call injected:
  - the blob ID matches `git hash-object` for the same bytes;
  - an unchanged state sends nothing;
  - a changed state sends exactly one PUT with the planned `sha`, the right branch, and content that base64-decodes
    to the file;
  - the commit message is `chore(tofu): commit the state after applying <sha7>`, followed by the run URL;
  - a 409 exits 1, naming the artifact.
- **End to end:** the script runs as a subprocess, with `GITHUB_API_URL` pointing at a local `http.server` thread,
  against a temporary git repository holding a **300 KB** state. That's far over the 128 KB argument limit, so a
  regression to passing content on a command line would fail here on Linux CI. The server records the request, and
  the test checks it.

### D3. Prove it against GitHub on a throwaway repository

- **The setup:** a throwaway repository, `infra-probe-statecommit-<date>`, cloned to the scratchpad. In it, a small
  `tofu/terraform.tfstate` is committed and pushed.
- **Then three runs of the script:**
  1. with a 300 KB file in its place → GitHub has the new file, byte for byte, in one commit;
  2. again with the old planned SHA → 409, and exit 1;
  3. with the file unchanged since the new commit → "unchanged", and no new commit.
- **Credentials:** the runs use the owner's `gh` token (`GH_TOKEN="$(gh auth token)"`, never printed), because the
  App's key stays out of the session. The App's identity isn't what failed: its commits through the contents API were
  already proven by the guard deliveries, and the token step worked in the failed run.
- The repository is deleted afterwards.

### D4. Recover `main`'s state in this pull request

The README's break-glass path ("If CI applied but couldn't commit the state"):
- copy the artifact's `terraform.tfstate` over `tofu/terraform.tfstate` on this branch;
- commit it as `chore(tofu): recover the state from run 38200444558`.

The PR's CI plan then reads serial 7, and should report no changes: the bypass is in both the state and GitHub. That
plan is the evidence the recovered state is right. The merge's `main` plan should also report no changes, so it
asks for no approval and makes no state commit.

## Risks / Trade-offs

- **[The fix can't be exercised end to end by this PR's own merge]**
  - Nothing is applied, so the state-commit step doesn't run on `main`.
  - Mitigation: the throwaway proof (D3) covers the real API, and the tests cover the step's logic.
  - The next change that applies (`required-checks`) runs it for real. Its PR description will say to watch for it.
- **[The artifact expires]** → it's kept for 90 days, and a copy is in the scratchpad. The recovery lands in this PR,
  well inside that.
- **[A local plan before this merges]** → it refreshes from GitHub, so serial 6 on `main` causes no wrong plan. Only a
  CI apply before this merges would face the stale state: its saved plan would apply, then its state commit would fail
  in the same way. No apply is pending.
