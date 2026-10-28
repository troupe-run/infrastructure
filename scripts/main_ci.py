"""Wait for CI on main before a scheduled or manual run plans it, and fail when CI isn't green.

Usage (in .github/workflows/tofu.yml's `plan` job, after a checkout of main with full history):
    python3 scripts/main_ci.py --main origin/main --repository "$GITHUB_REPOSITORY" \
        --summary "$GITHUB_STEP_SUMMARY"

Prints `superseded=true` or `superseded=false` on stdout, for "$GITHUB_OUTPUT". Exits 0 once CI
has passed, adding one line to the summary, or when a newer merge superseded the run (below), saying
so. Otherwise exits 1 with an error annotation, and the summary names the commit, links the CI run
and says how to recover. Spec: ci-apply ("A scheduled or manual plan of main waits for green CI",
"A scheduled or manual plan superseded by a newer merge plans nothing"); plans-wait-for-ci design
D1-D4; red-main-and-undecodable-spec design D1, D2.

Which commit's CI: the one CI runs on for main's head. CI's push trigger ignores a push that changes
only the state file (ci.yml's paths-ignore), so, walking main's first-parent history from its head:
- a commit with a CI push run is the one;
- otherwise one that changes only the state file is one CI skips, whoever made it: look past it;
- otherwise CI hasn't started on this commit yet: wait for it.
The walk runs again at every poll, so a run appearing on a later commit of the same push is found.

The newest run on that commit decides: success passes; any other conclusion fails; a status this
doesn't know fails, never counting as "still running". It waits up to LIMIT_SECONDS.

A cancelled run is the one exception. CI on main cancels an older run when a newer push lands, and
the walk reads main as fetched when this run started, so a merge during the wait isn't seen (#202).
So on a cancel it asks GitHub to compare the commit with main now. Ahead by a commit that changes
more than the state file: superseded, and the newer merge's own run plans main; the summary names
the newest such commit, read from GitHub. Identical, ahead only by state commits, any other answer,
or a read that fails: red, as for any other conclusion.

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
    superseded: bool = False


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


def compare(gh_: Gh, repository: str | None, sha: str) -> dict[str, Any]:
    """GitHub's comparison of this commit with main now: its status, how many commits main has
    since, the newest it lists, and the files they change. A shape this doesn't expect is a failed
    read, never "moved" or "not moved"."""
    where = repository or "{owner}/{repo}"
    found = gh_(
        [
            "api", f"repos/{where}/compare/{sha}...main", "--jq",
            "{status, total_commits, commits: [.commits[].sha], files: [.files[]?.filename]}",
        ]
    )  # fmt: skip
    if not (
        isinstance(found, dict)
        and isinstance(found.get("status"), str)
        and isinstance(found.get("total_commits"), int)
        and isinstance(found.get("commits"), list)
        and all(isinstance(commit, str) for commit in found["commits"])
        and isinstance(found.get("files"), list)
        and all(isinstance(name, str) for name in found["files"])
    ):
        raise ReadError(f"GitHub's compare of {short(sha)} with main isn't the shape expected")
    return found


def newest_ci_commit(gh_: Gh, repository: str | None, commits: list[str]) -> str:
    """The newest of these that changes more than the state file: main's head may be the App's
    state commit after the newer merge's apply, and CI never runs on that."""
    where = repository or "{owner}/{repo}"
    for sha in reversed(commits):
        files = gh_(["api", f"repos/{where}/commits/{sha}", "--jq", "[.files[]?.filename]"])
        if not (isinstance(files, list) and all(isinstance(name, str) for name in files)):
            raise ReadError(f"GitHub's files for {short(sha)} aren't the shape expected")
        if any(name != STATE_PATH for name in files):
            return sha
    raise ReadError(f"no commit since changes more than {STATE_PATH}, though the comparison does")


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


def after_cancel(
    repo: Path, sha: str, found: dict[str, Any], gh_: Gh, repository: str | None
) -> Result:
    """Superseded when main has moved past the cancelled commit by one CI runs on; red otherwise."""
    cancelled = "concluded **cancelled**"
    try:
        moved = compare(gh_, repository, sha)
    except ReadError as error:
        return red(
            repo,
            sha,
            found,
            f"{cancelled}, and whether `main` has moved past it couldn't be read: {error}",
        )
    status = moved["status"]
    if status == "identical":
        return red(repo, sha, found, cancelled)
    if status != "ahead":
        return red(
            repo, sha, found, f"{cancelled}, and GitHub compares `main` with it as **{status}**"
        )
    if all(name == STATE_PATH for name in moved["files"]):
        return red(
            repo,
            sha,
            found,
            f"{cancelled}, and `main` has moved past it only by commits that change {STATE_PATH},"
            " which CI doesn't run on",
        )
    commits = moved["commits"]
    if moved["total_commits"] == len(commits):
        try:
            newer = f"`{short(newest_ci_commit(gh_, repository, commits))}`"
        except ReadError as error:
            return red(
                repo,
                sha,
                found,
                f"{cancelled}, and which newer merge plans `main` couldn't be read: {error}",
            )
    else:  # the compare lists only the oldest commits since: none of them is the newest merge
        newer = "the newest merge on `main`"
    summary = (
        "### A newer merge superseded this run, so nothing was planned\n\n"
        f"CI on {describe(repo, sha)} was cancelled, and `main` has since moved on to {newer}."
        f" [The cancelled run]({found['url']}).\n\n"
        f"The run that starts when CI passes on {newer} plans `main`. This run planned nothing and"
        " asks for no approval.\n\n"
    )
    return Result(True, sha, summary, superseded=True)


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
            if found["conclusion"] == "cancelled":
                return after_cancel(repo, sha, found, gh_, repository)
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
    # Only name=value lines on stdout: the workflow appends it to $GITHUB_OUTPUT.
    print(f"superseded={'true' if result.superseded else 'false'}")
    if not result.passed:
        print(f"::error::main_ci.py: {result.error}", file=sys.stderr)
        return 1
    if result.superseded:
        print(
            f"CI on {result.sha} was cancelled and main has moved past it; not planning",
            file=sys.stderr,
        )
    else:
        print(f"CI passed on {result.sha}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
