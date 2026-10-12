"""The state commit after a CI apply (spec: ci-apply; fix-state-commit design D2).

Unit tests inject the HTTP call. The end-to-end test runs the script as CI does, against a local
stand-in for GitHub's contents API, with a state far over the 128 KB that Linux allows in one
command-line argument: the limit the shell version hit.
"""

import base64
import http.server
import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar

import pytest

import commit_state
from commit_state import Response

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "commit_state.py"
PLANNED_SHA = "0123456789abcdef0123456789abcdef01234567"
RUN_URL = "https://github.com/troupe-run/infrastructure/actions/runs/1"
TOKEN = "fake-token"  # noqa: S105 (a stand-in, never sent to GitHub)


class Recorder:
    def __init__(self, response: Response) -> None:
        self.response = response
        self.calls: list[tuple[str, str, str, dict[str, Any]]] = []

    def __call__(self, method: str, url: str, token: str, body: dict[str, Any]) -> Response:
        self.calls.append((method, url, token, body))
        return self.response


def run(content: bytes, planned_blob: str, send: Recorder, out: list[str]) -> int:
    return commit_state.commit_state(
        content=content,
        planned_blob=planned_blob,
        repo="troupe-run/infrastructure",
        branch="main",
        path="tofu/terraform.tfstate",
        message=commit_state.commit_message(PLANNED_SHA, RUN_URL),
        token=TOKEN,
        api="https://api.example",
        send=send,
        out=out.append,
    )


def test_the_blob_id_matches_git_hash_object(tmp_path: Path) -> None:
    content = os.urandom(5000)
    path = tmp_path / "state"
    path.write_bytes(content)
    expected = subprocess.run(
        ["git", "hash-object", str(path)], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert commit_state.git_blob_sha(content) == expected


def test_an_unchanged_state_sends_nothing() -> None:
    content = b'{"serial": 6}'
    send = Recorder(Response(200, {}))
    out: list[str] = []
    assert run(content, commit_state.git_blob_sha(content), send, out) == 0
    assert send.calls == []
    assert "unchanged" in out[0]


def test_a_changed_state_is_one_put_on_the_planned_blob() -> None:
    old, new = b'{"serial": 6}', b'{"serial": 7}'
    send = Recorder(Response(201, {"commit": {"sha": "abc123"}}))
    out: list[str] = []
    assert run(new, commit_state.git_blob_sha(old), send, out) == 0
    [(method, url, token, body)] = send.calls
    assert method == "PUT"
    assert (
        url == "https://api.example/repos/troupe-run/infrastructure/contents/tofu/terraform.tfstate"
    )
    assert token == TOKEN
    assert body["sha"] == commit_state.git_blob_sha(old)
    assert body["branch"] == "main"
    assert base64.b64decode(body["content"]) == new
    assert out == ["committed abc123 to main"]


def test_the_message_names_the_applied_commit_and_the_run() -> None:
    message = commit_state.commit_message(PLANNED_SHA, RUN_URL)
    assert (
        message == f"chore(tofu): commit the state after applying 0123456\n\nApplied by {RUN_URL}"
    )


def test_a_conflict_fails_and_points_at_the_artifact() -> None:
    send = Recorder(Response(409, {"message": "is at abc but expected def"}))
    out: list[str] = []
    assert run(b"new", commit_state.git_blob_sha(b"old"), send, out) == 1
    assert "HTTP 409" in out[0]
    assert "changed since the plan was made" in out[0]
    assert "state-after-apply" in out[0]


def test_any_other_refusal_fails_too() -> None:
    send = Recorder(Response(422, {"message": "Invalid request"}))
    out: list[str] = []
    assert run(b"new", commit_state.git_blob_sha(b"old"), send, out) == 1
    assert "HTTP 422" in out[0]


# --- end to end ----------------------------------------------------------------------------


class FakeContentsApi(http.server.BaseHTTPRequestHandler):
    received: ClassVar[list[dict[str, Any]]] = []

    def do_PUT(self) -> None:
        length = int(self.headers["Content-Length"])
        FakeContentsApi.received.append(
            {
                "path": self.path,
                "auth": self.headers["Authorization"],
                "body": json.loads(self.rfile.read(length)),
            }
        )
        reply = json.dumps({"commit": {"sha": "f00d"}}).encode()
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(reply)))
        self.end_headers()
        self.wfile.write(reply)

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def fake_api() -> Iterator[str]:
    FakeContentsApi.received = []
    server = http.server.HTTPServer(("127.0.0.1", 0), FakeContentsApi)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def git(cwd: Path, *args: str) -> str:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True, env=env
    ).stdout.strip()


def test_a_300_kb_state_is_committed_end_to_end(tmp_path: Path, fake_api: str) -> None:
    git(tmp_path, "init", "-q", "-b", "main")
    state = tmp_path / "tofu" / "terraform.tfstate"
    state.parent.mkdir()
    state.write_bytes(b'{"serial": 6}')
    git(tmp_path, "add", "-A")
    git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "s6")
    planned = git(tmp_path, "rev-parse", "HEAD")
    planned_blob = git(tmp_path, "rev-parse", "HEAD:tofu/terraform.tfstate")
    big = os.urandom(300 * 1024)  # ~400 KB in base64: three times the argument limit
    state.write_bytes(big)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            "troupe-run/infrastructure",
            "--branch",
            "main",
            "--path",
            "tofu/terraform.tfstate",
            "--planned",
            planned,
            "--run-url",
            RUN_URL,
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "GH_TOKEN": TOKEN, "GITHUB_API_URL": fake_api},
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "committed f00d to main" in result.stdout
    [request] = FakeContentsApi.received
    assert request["path"] == "/repos/troupe-run/infrastructure/contents/tofu/terraform.tfstate"
    assert request["auth"] == f"Bearer {TOKEN}"
    assert request["body"]["sha"] == planned_blob
    assert request["body"]["branch"] == "main"
    assert base64.b64decode(request["body"]["content"]) == big
    assert request["body"]["message"].startswith(
        f"chore(tofu): commit the state after applying {planned[:7]}"
    )


def test_without_a_token_it_stops_before_contacting_github(tmp_path: Path) -> None:
    env = {k: v for k, v in os.environ.items() if k != "GH_TOKEN"}
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            "r/r",
            "--branch",
            "main",
            "--path",
            "p",
            "--planned",
            "x",
            "--run-url",
            "u",
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 2
    assert "GH_TOKEN is not set" in result.stderr
