"""Wait for CI on main before a scheduled or manual run plans it, and fail when CI isn't green.

Usage (in .github/workflows/tofu.yml's `plan` job, after a checkout of main with full history):
    python3 scripts/main_ci.py --main origin/main --repository "$GITHUB_REPOSITORY" \
        --summary "$GITHUB_STEP_SUMMARY"

Exits 0 once CI has passed, adding one line to the summary. Otherwise exits 1 with an error
annotation, and the summary names the commit, links the CI run and says how to recover. Spec:
ci-apply ("A scheduled or manual plan of main waits for green CI"); plans-wait-for-ci design D1-D4.

Which commit's CI: the one CI runs on for main's head. CI's push trigger ignores a push that changes
only the state file (ci.yml's paths-ignore), so, walking main's first-parent history from its head:
- a commit with a CI push run is the one;
- otherwise one that changes only the state file is one CI skips, whoever made it: look past it;
- otherwise CI hasn't started on this commit yet: wait for it.
The walk runs again at every poll, so a run appearing on a later commit of the same push is found.

The newest run on that commit decides: success passes; any other conclusion fails; a status this
doesn't know fails, never counting as "still running". It waits up to LIMIT_SECONDS.

Standard library, git and gh only: the job runs it with the runner's python3, before uv is set up.
"""

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from plan_target import STATE_PATH, RefusedError, git, short

LIMIT_SECONDS = 25 * 60
POLL_SECONDS = 15
WAITING = frozenset({"queued", "in_progress", "waiting", "requested", "pending"})
RECOVER = """A red `main` holds scheduled and manual plans until CI passes on it. To recover:

- **Broken code:** merge a fix pull request. Its own run plans and applies once CI passes.
- **A flaky failure:** re-run the failed jobs ({rerun}). When they pass, the merge's own run starts.
- **Something urgent:** a break-glass apply from the owner's machine (README, "Break-glass: applying
  from your machine").
"""

Gh = Callable[[list[str]], Any]


class ReadError(Exception):
    """A read of GitHub that failed, in gh's words."""


@dataclass(frozen=True)
class Result:
    passed: bool
    sha: str | None
    summary: str
    error: str = ""


def gh(args: list[str]) -> Any:  # noqa: ANN401 (JSON)
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ReadError(result.stderr.strip() or f"gh exited {result.returncode}")
    return json.loads(result.stdout)


def ci_run(gh_: Gh, repository: str | None, sha: str) -> dict[str, Any] | None:
    """The newest CI push run on main for this commit, or None."""
    args = ["run", "list"]
    if repository:
        args += ["--repo", repository]
    args += [
        "--workflow", "ci.yml", "--commit", sha, "--event", "push", "--branch", "main",
        "--json", "databaseId,status,conclusion,url", "--limit", "1",
    ]  # fmt: skip
    found = gh_(args)
    if not isinstance(found, list):
        raise ReadError(f"gh run list printed {type(found).__name__}, not a list")
    return found[0] if found else None


def state_only(repo: Path, sha: str) -> bool:
    return git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", sha) == STATE_PATH


def find(
    repo: Path, main: str, gh_: Gh, repository: str | None
) -> tuple[str, dict[str, Any] | None]:
    """The commit CI runs on for main's head, and its newest run if it has one (D2)."""
    for sha in git(repo, "rev-list", "--first-parent", main).split():
        found = ci_run(gh_, repository, sha)
        if found is not None or not state_only(repo, sha):
            return sha, found
    raise RefusedError(f"{main} has no commit that changes more than {STATE_PATH}")


def describe(repo: Path, sha: str) -> str:
    return f"`{short(sha)}` ({git(repo, 'log', '-1', '--format=%s', sha)})"


def red(repo: Path, sha: str, found: dict[str, Any] | None, why: str) -> Result:
    link = f" [The CI run]({found['url']})." if found else ""
    rerun = (
        f"`gh run rerun {found['databaseId']} --failed`"
        if found
        else "`gh run rerun <id> --failed`"
    )
    summary = (
        f"### `main`'s CI isn't green, so nothing was planned\n\n"
        f"CI on {describe(repo, sha)} {why}.{link}\n\n{RECOVER.format(rerun=rerun)}\n"
    )
    return Result(False, sha, summary, f"CI on {sha} {why}; not planning.")


def wait_for_ci(
    repo: Path,
    main: str,
    gh_: Gh,
    *,
    repository: str | None = None,
    now: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> Result:
    start = now()
    while True:
        try:
            sha, found = find(repo, main, gh_, repository)
        except (ReadError, RefusedError) as error:
            return Result(
                False,
                None,
                f"Couldn't read CI on `main`, so nothing was planned: {error}\n\n",
                str(error),
            )
        if found is not None and found["status"] == "completed":
            if found["conclusion"] == "success":
                return Result(
                    True, sha, f"CI passed on {describe(repo, sha)}: [run]({found['url']}).\n\n"
                )
            return red(repo, sha, found, f"concluded **{found['conclusion']}**")
        if found is not None and found["status"] not in WAITING:
            return red(repo, sha, found, f"has a status this doesn't know: **{found['status']}**")
        if now() - start >= LIMIT_SECONDS:
            started = "" if found else " (no CI run has started on it)"
            return red(
                repo, sha, found, f"didn't finish within {LIMIT_SECONDS // 60} minutes{started}"
            )
        sleep(POLL_SECONDS)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--main", default="origin/main", help="main as fetched for this run")
    parser.add_argument("--repository", required=True, help="owner/name, for gh")
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args(argv)
    result = wait_for_ci(args.repo, args.main, gh, repository=args.repository)
    with args.summary.open("a", encoding="utf-8") as summary:
        summary.write(result.summary)
    if not result.passed:
        print(f"::error::main_ci.py: {result.error}", file=sys.stderr)
        return 1
    print(f"CI passed on {result.sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
