"""Commit the state to a branch through GitHub's contents API, after a CI apply.

Usage (in .github/workflows/tofu.yml, with the App's token in GH_TOKEN):
    uv run --no-project scripts/commit_state.py --repo troupe-run/infrastructure --branch main \
        --path tofu/terraform.tfstate --planned <sha> --run-url <url>

Spec: ci-apply ("The new state reaches main after every apply"); design D1 of fix-state-commit.
- If the state file is the blob the plan was made from, nothing was written: no commit.
- Otherwise one PUT, with `sha` set to that planned blob, so a file changed on the branch since
  gets a 409 instead of being overwritten.
- The request body is built and sent in memory. The state is far bigger than an operating system
  allows in one command-line argument (128 KB on Linux), which is what broke the shell version.
"""

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

API = "https://api.github.com"
RECOVERY = (
    "The state is kept as the run's state-after-apply artifact; "
    "README, 'Break-glass: applying from your machine', says how to recover it."
)


@dataclass(frozen=True)
class Response:
    status: int
    body: dict[str, Any]


# (method, url, token, body) -> response. Injected so tests don't touch GitHub.
Send = Callable[[str, str, str, dict[str, Any]], Response]


def git_blob_sha(content: bytes) -> str:
    """The ID git gives `content` as a blob, as `git hash-object` computes it."""
    return hashlib.sha1(b"blob %d\0" % len(content) + content, usedforsecurity=False).hexdigest()


def commit_message(planned: str, run_url: str) -> str:
    return f"chore(tofu): commit the state after applying {planned[:7]}\n\nApplied by {run_url}"


def request_body(content: bytes, planned_blob: str, branch: str, message: str) -> dict[str, Any]:
    return {
        "message": message,
        "content": base64.b64encode(content).decode("ascii"),
        "sha": planned_blob,
        "branch": branch,
    }


def send_with_urllib(method: str, url: str, token: str, body: dict[str, Any]) -> Response:
    # HTTPS only, except a local stand-in (the tests'): never a file: or other scheme.
    if not (url.startswith("https://") or url.startswith("http://127.0.0.1:")):
        raise ValueError(f"refusing to send the state to {url}")
    request = urllib.request.Request(  # noqa: S310 (scheme checked above)
        url,
        data=json.dumps(body).encode("utf-8"),
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 (as above)
            return Response(response.status, json.loads(response.read() or b"{}"))
    except urllib.error.HTTPError as error:
        try:
            detail = json.loads(error.read() or b"{}")
        except json.JSONDecodeError:
            detail = {}
        return Response(error.code, detail if isinstance(detail, dict) else {})


def commit_state(
    *,
    content: bytes,
    planned_blob: str,
    repo: str,
    branch: str,
    path: str,
    message: str,
    token: str,
    api: str,
    send: Send,
    out: Callable[[str], None],
) -> int:
    """Commit `content` at `path` unless it is the planned blob. Returns the exit code."""
    if git_blob_sha(content) == planned_blob:
        out(f"The state is unchanged (the apply wrote nothing); no commit to {branch}.")
        return 0
    url = f"{api.rstrip('/')}/repos/{repo}/contents/{path}"
    response = send("PUT", url, token, request_body(content, planned_blob, branch, message))
    if response.status in (200, 201):
        commit = response.body.get("commit", {}).get("sha", "?")
        out(f"committed {commit} to {branch}")
        return 0
    reason = response.body.get("message", "no message")
    if response.status == 409:
        reason += f" ({path} on {branch} changed since the plan was made)"
    out(f"commit_state: GitHub refused the commit: HTTP {response.status}: {reason}. {RECOVERY}")
    return 1


def planned_blob_id(root: Path, planned: str, path: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"{planned}:{path}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, help="owner/name, e.g. troupe-run/infrastructure")
    parser.add_argument("--branch", required=True, help="the branch to commit to, e.g. main")
    parser.add_argument("--path", required=True, help="the state file, relative to the repo root")
    parser.add_argument(
        "--planned", required=True, help="the commit the applied plan was made from"
    )
    parser.add_argument("--run-url", required=True, help="the workflow run, named in the message")
    parser.add_argument("--root", default=".", help="the checkout (default: the current directory)")
    args = parser.parse_args(argv)

    token = os.environ.get("GH_TOKEN", "")
    if not token:
        print("commit_state: GH_TOKEN is not set.", file=sys.stderr)
        return 2
    root = Path(args.root)
    return commit_state(
        content=(root / args.path).read_bytes(),
        planned_blob=planned_blob_id(root, args.planned, args.path),
        repo=args.repo,
        branch=args.branch,
        path=args.path,
        message=commit_message(args.planned, args.run_url),
        token=token,
        api=os.environ.get("GITHUB_API_URL") or API,
        send=send_with_urllib,
        out=print,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
