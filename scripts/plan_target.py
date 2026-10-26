"""Decide which commit a run on main plans, so every plan reads main's current state.

Usage (in .github/workflows/tofu.yml's `plan` job, after a checkout of main with full history):
    python3 scripts/plan_target.py --event "$EVENT" --commit "$COMMIT" \
        --state-author "$STATE_AUTHOR" --main origin/main --summary "$GITHUB_STEP_SUMMARY" \
        >> "$GITHUB_OUTPUT"

Prints `sha=<commit>` and `plan=true`, or `sha=` and `plan=false`, and adds one line saying why to
the summary. Spec: ci-apply ("A plan of main reads main's current state"); plan-each-merge-once
design D1, D2.

The state is a file in the checkout, so a plan reads the state of the commit it checks out. A run
started for an older commit would read state from before any apply since, and plan that apply's
changes again (#167). So:
- A scheduled or manual run plans main's head as it is now, not when the run was triggered.
- A run after CI on a merge C plans P, the last of C and the App's state commits straight after
  it: P has C's declaration (a state commit changes only the state) and the newest state among
  them. If P's state is main's, it plans P. Otherwise state was committed after a later merge,
  and it plans nothing: that merge's run plans with the current state.
- The App's own state commit is never planned after CI; CI doesn't run on it anyway.
An unknown event, a commit that isn't a full sha, or one main doesn't contain, is refused.

Standard library and git only: the job runs it with the runner's python3, before uv is set up.
"""

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

STATE_PATH = "tofu/terraform.tfstate"
EVENTS = ("workflow_run", "schedule", "workflow_dispatch")
FULL_SHA = re.compile(r"[0-9a-f]{40}")
# Set by git while a hook runs; they would point every command here at that repository instead.
HOOK_VARIABLES = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX",
)


class RefusedError(Exception):
    """An input this can't decide on. The run fails rather than plan a guess."""


@dataclass(frozen=True)
class Target:
    sha: str | None
    reason: str


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {name: value for name, value in os.environ.items() if name not in HOOK_VARIABLES}
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False, env=env
    )


def git(repo: Path, *args: str) -> str:
    result = run_git(repo, *args)
    if result.returncode != 0:
        raise RefusedError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def short(sha: str) -> str:
    return sha[:7]


def is_state_commit(repo: Path, sha: str, state_author: str) -> bool:
    """The App's commit after an apply: by its bot, changing only the state file. A merge commit
    lists no files here, so it never counts."""
    author = git(repo, "log", "-1", "--format=%ae", sha)
    files = git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", sha)
    return author == state_author and files == STATE_PATH


def state_blob(repo: Path, sha: str) -> str:
    return git(repo, "rev-parse", f"{sha}:{STATE_PATH}")


def decide(repo: Path, event: str, commit: str, state_author: str, main: str) -> Target:
    if event not in EVENTS:
        raise RefusedError(f"unknown event {event!r}; this plans only on {', '.join(EVENTS)}")
    if not FULL_SHA.fullmatch(commit):
        raise RefusedError(f"{commit!r} isn't a full commit sha (40 lowercase hex characters)")
    if git(repo, "cat-file", "-t", commit) != "commit":
        raise RefusedError(f"{commit} isn't a commit")
    head = git(repo, "rev-parse", "--verify", f"{main}^{{commit}}")
    if run_git(repo, "merge-base", "--is-ancestor", commit, head).returncode != 0:
        raise RefusedError(f"{commit} isn't in {main}'s history ({short(head)}); not planning it")

    if event != "workflow_run":
        moved = (
            f" The run was started on {short(commit)}; {main} has moved since."
            if commit != head
            else ""
        )
        return Target(head, f"Planning {main}'s head, {short(head)}.{moved}")

    if is_state_commit(repo, commit, state_author):
        return Target(
            None, f"Nothing to plan: {short(commit)} is the App's state commit after an apply."
        )

    planned = commit
    later_merge = None
    for sha in git(repo, "rev-list", "--reverse", "--first-parent", f"{commit}..{head}").split():
        if not is_state_commit(repo, sha, state_author):
            later_merge = sha
            break
        planned = sha

    # With only state commits after it, `planned` is the head, so a different state means a later
    # merge came first.
    if later_merge is not None and state_blob(repo, planned) != state_blob(repo, head):
        return Target(
            None,
            f"Nothing to plan: state was committed after {short(later_merge)}, a later commit on "
            f"{main}, so {short(commit)}'s declaration has no commit with {main}'s current state. "
            "The run after CI on a later merge plans it with that state.",
        )
    if planned == commit:
        return Target(commit, f"Planning {short(commit)}: its state is {main}'s current state.")
    where = f"{main}'s head" if planned == head else "the last of the App's state commits"
    return Target(
        planned,
        f"Planning {short(planned)}, not {short(commit)}: {where}, after only the App's state "
        f"commits, so it has {short(commit)}'s declaration with {main}'s current state. If one of "
        f"those applies already applied {short(commit)}, this plan shows no changes.",
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--event", required=True)
    parser.add_argument("--commit", required=True, help="the commit the run was started for")
    parser.add_argument("--state-author", required=True, help="the App's bot's commit address")
    parser.add_argument("--main", default="origin/main", help="main as fetched for this run")
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        found = decide(args.repo, args.event, args.commit, args.state_author, args.main)
    except RefusedError as error:
        print(f"::error::plan_target.py: {error}", file=sys.stderr)
        return 1
    print(f"sha={found.sha or ''}")
    print(f"plan={'true' if found.sha else 'false'}")
    with args.summary.open("a", encoding="utf-8") as summary:
        summary.write(f"{found.reason}\n\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
