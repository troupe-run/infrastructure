"""Give each delivered file its source's mode in the repositories that receive the guard.

Usage (in .github/workflows/tofu.yml):
    tofu show -json main.tfplan > plan.json
    # GH_TOKEN: any token that can read the targets
    uv run --no-project scripts/hook_modes.py plan --plan-json plan.json \
        --out mode-plan.json --summary modes.md
    # GH_TOKEN: the App's, scoped to the repositories the mode plan names
    uv run --no-project scripts/hook_modes.py apply --mode-plan mode-plan.json

Spec: guard-delivery ("A delivered file has its source's mode"); design: executable-hooks.
- `github_repository_file` writes through the Contents API, which takes no mode: a file it creates
  is 100644, and an update keeps whatever mode the file has. So a hook that is executable here
  arrived non-executable in a new target, and git skipped it (#69).
- `plan` reads what is delivered from the saved plan itself (D1), so there is no second list of
  targets or files. Each source's mode is this checkout's (`git ls-files -s`). One tree read per
  target finds each file whose mode differs, or that this apply creates with an executable source
  (D2, D5). It only reads.
- `apply` runs after the approved apply. Per repository, it checks every listed file still holds
  the planned blob, then makes one commit that sets the modes, and moves `main` without force, so a
  `main` that moved since gets a 422 instead of being overwritten (D4). Nothing it does is
  retried: the next plan reads the targets again.

Recovery: a failed `apply` changes nothing in a repository whose ref update failed; the next plan
of `main` (daily at the latest) lists the modes again for approval.
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from commit_state import git_blob_sha

API = "https://api.github.com"
ORG = "troupe-run"
SOURCE = "troupe-run/infrastructure"
BRANCH = "main"
RESOURCE = "github_repository_file.guard"
REGULAR, EXECUTABLE = "100644", "100755"
MODES = frozenset({REGULAR, EXECUTABLE})
"""The modes a delivered file can have. Anything else (a symlink, a submodule) is an error."""
VERSION = 1


@dataclass(frozen=True)
class Response:
    status: int
    body: dict[str, Any]


# (method, url, token, body or None) -> response. Injected so tests don't touch GitHub.
Send = Callable[[str, str, str, dict[str, Any] | None], Response]


class ModeError(Exception):
    """A refusal: the input can't be read as expected, or GitHub said no. The message says which."""


@dataclass(frozen=True)
class Delivered:
    """One delivered file, as the saved plan will leave it."""

    repository: str
    path: str
    content: str


@dataclass(frozen=True)
class Entry:
    """A mode to set: `path` in `repository` holds blob `blob` and must have mode `mode`."""

    repository: str
    path: str
    mode: str
    blob: str


# --- reading the plan -------------------------------------------------------------------------


def delivered_files(plan: dict[str, Any]) -> list[Delivered]:
    """Every delivered file in a `tofu show -json` plan's planned values (design D1)."""
    try:
        resources = plan["planned_values"]["root_module"].get("resources", [])
    except (KeyError, AttributeError, TypeError) as error:
        raise ModeError(f"the plan JSON has no planned_values.root_module ({error!r})") from None
    found = []
    for resource in resources:
        if not str(resource.get("address", "")).startswith(f"{RESOURCE}["):
            continue
        values = resource.get("values") or {}
        repository, path, content = (values.get(k) for k in ("repository", "file", "content"))
        if not (isinstance(repository, str) and isinstance(path, str) and isinstance(content, str)):
            raise ModeError(
                f"{resource.get('address')} has no known repository, file and content in the plan"
            )
        found.append(Delivered(repository, path, content))
    return sorted(found, key=lambda d: (d.repository, d.path))


def source_mode(root: Path, path: str) -> str:
    """The mode of `path` in this checkout's index. A file with no source (the generated delivered
    list) is a regular file."""
    listed = subprocess.run(
        ["git", "ls-files", "-s", "--", path],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    if not listed:
        return REGULAR
    mode = listed[0]
    if mode not in MODES:
        raise ModeError(
            f"{path} has mode {mode} here; a delivered file is {REGULAR} or {EXECUTABLE}"
        )
    return mode


# --- reading GitHub ---------------------------------------------------------------------------


def _get(send: Send, api: str, token: str, path: str) -> dict[str, Any]:
    response = send("GET", f"{api.rstrip('/')}/{path}", token, None)
    if response.status != 200:
        reason = response.body.get("message", "no message")
        raise ModeError(f"GET {path}: HTTP {response.status}: {reason}")
    return response.body


def tree_entries(body: dict[str, Any], repository: str) -> dict[str, tuple[str, str]]:
    """path -> (mode, blob) for each blob in a recursive tree read."""
    if body.get("truncated"):
        raise ModeError(
            f"{ORG}/{repository}'s tree is too big for one read (truncated); its modes can't be "
            "checked, so nothing is planned for it"
        )
    return {
        item["path"]: (item["mode"], item["sha"])
        for item in body.get("tree", [])
        if item.get("type") == "blob"
    }


def mode_plan(
    delivered: Iterable[Delivered],
    source_mode_of: Callable[[str], str],
    tree_of: Callable[[str], dict[str, tuple[str, str]]],
) -> list[Entry]:
    """Each delivered file whose target mode will differ from its source's after the apply (D2)."""
    entries = []
    trees: dict[str, dict[str, tuple[str, str]]] = {}
    for file in delivered:
        wanted = source_mode_of(file.path)
        blob = git_blob_sha(file.content.encode("utf-8"))
        if file.repository not in trees:
            trees[file.repository] = tree_of(file.repository)
        current = trees[file.repository].get(file.path)
        if current is None:
            # The apply creates it through the Contents API, so as a regular file (design D5).
            if wanted != REGULAR:
                entries.append(Entry(file.repository, file.path, wanted, blob))
            continue
        mode, _ = current
        if mode not in MODES:
            raise ModeError(
                f"{ORG}/{file.repository}:{file.path} has mode {mode}; a delivered file is "
                f"{REGULAR} or {EXECUTABLE}"
            )
        if mode != wanted:
            entries.append(Entry(file.repository, file.path, wanted, blob))
    return entries


def summary(entries: list[Entry]) -> str:
    """Markdown for the run summary and the pull request's comment, under the OpenTofu plan."""
    if not entries:
        return (
            "**Modes to set after the apply:** none. Every delivered file has its source's mode.\n"
        )
    lines = [
        f"**Modes to set after the apply:** {len(entries)}. The App sets each one on `main` once "
        "the apply succeeds (spec: guard-delivery).",
        "",
        "| Repository | File | Mode |",
        "|---|---|---|",
    ]
    lines += [f"| {e.repository} | `{e.path}` | {e.mode} |" for e in entries]
    return "\n".join(lines) + "\n"


# --- setting modes ----------------------------------------------------------------------------


def commit_message(paths: Iterable[str]) -> str:
    return f"chore(guard): set the mode of {', '.join(sorted(paths))} from {SOURCE}"


def apply_modes(
    entries: list[Entry],
    *,
    token: str,
    api: str,
    send: Send,
    out: Callable[[str], None],
) -> int:
    """Set each entry's mode, one commit per repository. Returns the exit code."""
    if not entries:
        out("hook_modes: no modes to set.")
        return 0
    by_repo: dict[str, list[Entry]] = {}
    for entry in entries:
        by_repo.setdefault(entry.repository, []).append(entry)

    # Every check before any write: a file changed since the plan stops the whole run (D4).
    heads: dict[str, tuple[str, str]] = {}
    for repository, listed in sorted(by_repo.items()):
        base = f"repos/{ORG}/{repository}/git"
        head = _get(send, api, token, f"{base}/ref/heads/{BRANCH}")["object"]["sha"]
        tree = _get(send, api, token, f"{base}/commits/{head}")["tree"]["sha"]
        current = tree_entries(
            _get(send, api, token, f"{base}/trees/{tree}?recursive=1"), repository
        )
        for entry in listed:
            found = current.get(entry.path)
            if found is None or found[1] != entry.blob:
                raise ModeError(
                    f"{ORG}/{repository}:{entry.path} isn't the content the plan read (planned "
                    f"blob {entry.blob[:12]}, found {found[1][:12] if found else 'no file'}); no "
                    "mode was set. The next plan reads it again"
                )
        heads[repository] = (head, tree)

    for repository, listed in sorted(by_repo.items()):
        base = f"{api.rstrip('/')}/repos/{ORG}/{repository}/git"
        head, tree = heads[repository]
        made = send(
            "POST",
            f"{base}/trees",
            token,
            {
                "base_tree": tree,
                "tree": [
                    {"path": e.path, "mode": e.mode, "type": "blob", "sha": e.blob} for e in listed
                ],
            },
        )
        _expect(made, 201, f"{repository}: create the tree")
        commit = send(
            "POST",
            f"{base}/commits",
            token,
            {
                "message": commit_message(e.path for e in listed),
                "tree": made.body["sha"],
                "parents": [head],
            },
        )
        _expect(commit, 201, f"{repository}: create the commit")
        moved = send(
            "PATCH",
            f"{base}/refs/heads/{BRANCH}",
            token,
            {"sha": commit.body["sha"], "force": False},
        )
        if moved.status == 422:
            raise ModeError(
                f"{ORG}/{repository}: {BRANCH} moved since it was read, so it wasn't updated "
                f"({moved.body.get('message', 'no message')}). The next plan reads it again"
            )
        _expect(moved, 200, f"{repository}: update {BRANCH}")
        out(f"{ORG}/{repository}: set the mode of {len(listed)} file(s) in {commit.body['sha']}")
    return 0


def _expect(response: Response, status: int, what: str) -> None:
    if response.status != status:
        reason = response.body.get("message", "no message")
        raise ModeError(f"{what}: HTTP {response.status}: {reason}")


# --- the command line -------------------------------------------------------------------------


def send_with_urllib(method: str, url: str, token: str, body: dict[str, Any] | None) -> Response:
    # HTTPS only, except a local stand-in: never a file: or other scheme.
    if not (url.startswith("https://") or url.startswith("http://127.0.0.1:")):
        raise ValueError(f"refusing to send a request to {url}")
    request = urllib.request.Request(  # noqa: S310 (scheme checked above)
        url,
        data=None if body is None else json.dumps(body).encode("utf-8"),
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


def read_mode_plan(path: Path) -> list[Entry]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != VERSION:
        raise ModeError(f"{path} isn't a version {VERSION} mode plan")
    try:
        return [Entry(**entry) for entry in data["entries"]]
    except (KeyError, TypeError) as error:
        raise ModeError(f"{path} has a malformed entry ({error})") from None


def main(argv: list[str], send: Send = send_with_urllib) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="list the modes to set, from a saved plan (only reads)")
    plan.add_argument("--plan-json", required=True, type=Path, help="`tofu show -json` output")
    plan.add_argument("--out", required=True, type=Path, help="where to write the mode plan")
    plan.add_argument("--summary", required=True, type=Path, help="where to write its Markdown")
    plan.add_argument("--root", default=".", type=Path, help="this checkout (default: .)")
    apply = sub.add_parser("apply", help="set the modes a mode plan lists, as the App")
    apply.add_argument("--mode-plan", required=True, type=Path)
    args = parser.parse_args(argv)

    token = os.environ.get("GH_TOKEN", "")
    if not token:
        print("hook_modes: GH_TOKEN is not set.", file=sys.stderr)
        return 2
    api = os.environ.get("GITHUB_API_URL") or API
    try:
        if args.command == "plan":
            delivered = delivered_files(json.loads(args.plan_json.read_text(encoding="utf-8")))
            entries = mode_plan(
                delivered,
                lambda path: source_mode(args.root, path),
                lambda repository: tree_entries(
                    _get(
                        send, api, token, f"repos/{ORG}/{repository}/git/trees/{BRANCH}?recursive=1"
                    ),
                    repository,
                ),
            )
            args.out.write_text(
                json.dumps({"version": VERSION, "entries": [asdict(e) for e in entries]}, indent=2)
                + "\n",
                encoding="utf-8",
            )
            args.summary.write_text(summary(entries), encoding="utf-8")
            print(summary(entries), end="")
            return 0
        return apply_modes(
            read_mode_plan(args.mode_plan), token=token, api=api, send=send, out=print
        )
    except ModeError as error:
        print(f"hook_modes: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
