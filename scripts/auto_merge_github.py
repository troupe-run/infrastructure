"""GitHub as auto-merge reads and writes it (spec: auto-merge; auto-merge design D2): through
`gh api`, a recorder that keeps writes back, a tape that keeps every read for test fixtures, and a
replay that answers from one. Split from auto_merge.py to keep each file one review's read.
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from typing import Protocol


class AutoMergeError(Exception):
    """The run couldn't judge: a bad config, an unreadable read, a malformed variable."""


class NotFoundError(AutoMergeError):
    """GitHub answered 404: for some reads (a variable, a file) that's an answer, not a failure."""


class GitHub(Protocol):
    """GitHub's API as auto-merge uses it. A failure raises AutoMergeError; a 404, NotFoundError."""

    def get(self, path: str) -> object: ...

    def raw(self, path: str) -> bytes: ...

    def graphql(self, query: str, variables: Mapping[str, object]) -> Mapping[str, object]: ...

    def write(self, method: str, path: str, body: Mapping[str, object]) -> object: ...


class GhCli:
    """GitHub through `gh api`, with whatever token gh has: GH_TOKEN in the workflow (the App's),
    the owner's login for a local read-only run."""

    def __init__(self, gh: str = "gh") -> None:
        self.gh = gh

    def _run(self, args: Sequence[str], body: object = None) -> bytes:
        stdin = None if body is None else json.dumps(body).encode()
        command = [self.gh, "api", *args] + (["--input", "-"] if body is not None else [])
        try:
            done = subprocess.run(command, input=stdin, capture_output=True, check=False)
        except OSError as error:
            raise AutoMergeError(f"couldn't run gh: {error}") from error
        if done.returncode != 0:
            said = (done.stderr or done.stdout).decode(errors="replace").strip()
            if "HTTP 404" in said:
                raise NotFoundError(f"{args[-1]}: not found")
            raise AutoMergeError(f"gh api {' '.join(args)} failed: {said[-500:]}")
        return done.stdout

    def get(self, path: str) -> object:
        out = self._run(["-H", "Accept: application/vnd.github+json", path])
        try:
            result: object = json.loads(out or b"null")
        except json.JSONDecodeError as error:
            raise AutoMergeError(f"{path}: the answer isn't JSON: {error}") from error
        return result

    def raw(self, path: str) -> bytes:
        return self._run([path])

    def graphql(self, query: str, variables: Mapping[str, object]) -> Mapping[str, object]:
        answer = json.loads(self._run(["graphql"], {"query": query, "variables": dict(variables)}))
        if (
            not isinstance(answer, dict)
            or answer.get("errors")
            or not isinstance(answer.get("data"), dict)
        ):
            raise AutoMergeError(f"GraphQL failed: {json.dumps(answer)[:500]}")
        data: Mapping[str, object] = answer["data"]
        return data

    def write(self, method: str, path: str, body: Mapping[str, object]) -> object:
        out = self._run(["-X", method, path], dict(body))
        return json.loads(out) if out.strip() else None


def _operation(query: str) -> str:
    """A GraphQL mutation's field, such as enqueuePullRequest, for the record of what was sent."""
    found = re.search(r"\{\s*(\w+)", query)
    return found.group(1) if found else "?"


class Recorder:
    """A GitHub whose reads go through and whose writes are only recorded (tasks 7.1): for a run
    that must change nothing."""

    def __init__(self, inner: GitHub) -> None:
        self.inner = inner
        self.writes: list[dict[str, object]] = []

    def get(self, path: str) -> object:
        return self.inner.get(path)

    def raw(self, path: str) -> bytes:
        return self.inner.raw(path)

    def graphql(self, query: str, variables: Mapping[str, object]) -> Mapping[str, object]:
        if query.lstrip().startswith("mutation"):
            self.writes.append({"graphql": _operation(query), "variables": dict(variables)})
            return {}
        return self.inner.graphql(query, variables)

    def write(self, method: str, path: str, body: Mapping[str, object]) -> object:
        self.writes.append({"method": method, "path": path, "body": dict(body)})
        return None


class Tape:
    """A GitHub that passes everything through and keeps every read's answer, for test fixtures
    copied from real responses (tasks 3.1). Writes aren't allowed through it."""

    def __init__(self, inner: GitHub) -> None:
        self.inner = inner
        self.reads: dict[str, object] = {}

    def get(self, path: str) -> object:
        try:
            answer = self.inner.get(path)
        except NotFoundError:
            self.reads[f"GET {path}"] = {"__status__": 404}
            raise
        self.reads[f"GET {path}"] = answer
        return answer

    def raw(self, path: str) -> bytes:
        answer = self.inner.raw(path)
        self.reads[f"RAW {path}"] = {"__base64__": base64.b64encode(answer).decode()}
        return answer

    def graphql(self, query: str, variables: Mapping[str, object]) -> Mapping[str, object]:
        answer = self.inner.graphql(query, variables)
        self.reads[f"GRAPHQL {json.dumps(dict(variables), sort_keys=True)}"] = answer
        return answer

    def write(self, method: str, path: str, body: Mapping[str, object]) -> object:
        raise AutoMergeError("a tape records reads only")


class Replay:
    """A GitHub answering from a tape (a dict of recorded reads), and recording writes. A read the
    tape doesn't hold fails, so a test can't quietly depend on something it didn't record."""

    def __init__(self, reads: Mapping[str, object]) -> None:
        self.reads = dict(reads)
        self.writes: list[dict[str, object]] = []

    def _answer(self, key: str) -> object:
        if key not in self.reads:
            raise AutoMergeError(f"the tape has no answer for {key}")
        answer = self.reads[key]
        if isinstance(answer, dict) and answer.get("__status__") == 404:
            raise NotFoundError(key)
        if isinstance(answer, dict) and "__error__" in answer:
            raise AutoMergeError(str(answer["__error__"]))
        return answer

    def get(self, path: str) -> object:
        return self._answer(f"GET {path}")

    def raw(self, path: str) -> bytes:
        answer = _dict(self._answer(f"RAW {path}"), path)
        return base64.b64decode(_text(answer.get("__base64__"), path))

    def graphql(self, query: str, variables: Mapping[str, object]) -> Mapping[str, object]:
        if query.lstrip().startswith("mutation"):
            self.writes.append({"graphql": _operation(query), "variables": dict(variables)})
            return {}
        return _dict(
            self._answer(f"GRAPHQL {json.dumps(dict(variables), sort_keys=True)}"), "graphql"
        )

    def write(self, method: str, path: str, body: Mapping[str, object]) -> object:
        self.writes.append({"method": method, "path": path, "body": dict(body)})
        return None


def _dict(value: object, what: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise AutoMergeError(f"{what} isn't an object")
    return value


def _list(value: object, what: str) -> list[object]:
    if not isinstance(value, list):
        raise AutoMergeError(f"{what} isn't a list")
    return value


def _text(value: object, what: str) -> str:
    if not isinstance(value, str):
        raise AutoMergeError(f"{what} isn't text")
    return value


def get_all(gh: GitHub, path: str, key: str | None = None) -> list[object]:
    """Every page of a REST listing, 100 at a time. ``key`` names the list in an object answer."""
    found: list[object] = []
    page = 1
    joiner = "&" if "?" in path else "?"
    while True:
        answer = gh.get(f"{path}{joiner}per_page=100&page={page}")
        items = _list(_dict(answer, path).get(key) if key else answer, path)
        found.extend(items)
        if len(items) < 100:
            return found
        page += 1
