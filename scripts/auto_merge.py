"""Auto-merge: queue the pull requests that pass the safe-PR rule (spec: auto-merge; #319, #320).

Usage:
    auto_merge.py run [--recorder PATH]

It judges every open pull request of the governed repositories against the rule, and, where the
repository's AUTO_MERGE variable says so, queues it or comments that it would have (design D1-D5).
It runs on infrastructure's main only, as the troupe-run-merge App, and executes nothing from a
pull request: it reads them through GitHub's API and as git data.

The rule's settings come from auto-merge.toml at this repository's root, read strictly (design D4):
an unknown key, a wrong type or a missing repository is an error, and the run then queues nothing.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Protocol

from quality_gates import LANGUAGES, Function, GateError, excluded, lizard_functions

CONFIG_NAME = "auto-merge.toml"
OWNER = "troupe-run"
REPOSITORIES = ("troupe", "infrastructure", "website")
"""The governed repositories auto-merge judges, each needing its own table in the config."""

LIMIT_KEYS = ("max_lines", "max_files", "max_function_complexity", "max_complexity_increase")
LIST_KEYS = ("generated", "prose", "complexity_exclude", "languages", "protected")


class AutoMergeError(Exception):
    """The run couldn't judge: a bad config, an unreadable read, a malformed variable."""


# --- Config (design D4) ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Limits:
    max_lines: int
    max_files: int
    max_function_complexity: int
    max_complexity_increase: int


@dataclass(frozen=True)
class Rules:
    """One repository's rule settings: the defaults, with its own table applied."""

    limits: Limits
    generated: tuple[str, ...]
    prose: tuple[str, ...]
    complexity_exclude: tuple[str, ...]
    languages: tuple[str, ...]
    protected: tuple[str, ...]

    def is_generated(self, path: str) -> bool:
        return excluded(path, self.generated)

    def is_prose(self, path: str) -> bool:
        return excluded(path, self.prose)

    def is_protected(self, path: str) -> bool:
        return excluded(path, self.protected)


@dataclass(frozen=True)
class Config:
    repositories: Mapping[str, Rules]


def _where(table: str, key: str) -> str:
    return f"{table}.{key}" if table else key


def _keys(
    table: Mapping[str, object], where: str, allowed: Sequence[str], required: Iterable[str]
) -> None:
    unknown = sorted(set(table) - set(allowed))
    if unknown:
        raise AutoMergeError(
            f"{CONFIG_NAME}: unknown key `{_where(where, unknown[0])}`. "
            f"`[{where or 'top level'}]` takes: {', '.join(allowed)}."
        )
    for key in required:
        if key not in table:
            raise AutoMergeError(f"{CONFIG_NAME}: `{_where(where, key)}` is required.")


def _limit(table: Mapping[str, object], where: str, key: str) -> int:
    value = table[key]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AutoMergeError(
            f"{CONFIG_NAME}: `{_where(where, key)}` must be a whole number, 0 or more, "
            f"not {value!r}."
        )
    return value


def _strings(
    table: Mapping[str, object], where: str, key: str, choices: Sequence[str] | None = None
) -> tuple[str, ...]:
    value = table[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AutoMergeError(f"{CONFIG_NAME}: `{_where(where, key)}` must be a list of strings.")
    for item in value:
        if choices is not None and item not in choices:
            raise AutoMergeError(
                f"{CONFIG_NAME}: `{_where(where, key)}` can't hold {item!r}. "
                f"Valid: {', '.join(choices)}."
            )
    return tuple(value)


def _table(table: Mapping[str, object], where: str, key: str) -> Mapping[str, object]:
    value = table[key]
    if not isinstance(value, dict):
        raise AutoMergeError(f"{CONFIG_NAME}: `{_where(where, key)}` must be a table.")
    return value


def parse_config(text: str) -> Config:
    """The config, from the text of auto-merge.toml."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise AutoMergeError(f"{CONFIG_NAME} isn't valid TOML: {error}.") from error
    _keys(
        data, "", ("version", "defaults", "repositories"), ("version", "defaults", "repositories")
    )
    if data["version"] != 1:
        raise AutoMergeError(f"{CONFIG_NAME}: `version` must be 1, not {data['version']!r}.")

    defaults = _table(data, "", "defaults")
    _keys(defaults, "defaults", (*LIMIT_KEYS, *LIST_KEYS), (*LIMIT_KEYS, *LIST_KEYS))
    base_limits = {key: _limit(defaults, "defaults", key) for key in LIMIT_KEYS}
    languages = _strings(defaults, "defaults", "languages", tuple(LANGUAGES))

    repositories = _table(data, "", "repositories")
    unknown = sorted(set(repositories) - set(REPOSITORIES))
    if unknown:
        raise AutoMergeError(
            f"{CONFIG_NAME}: unknown repository `repositories.{unknown[0]}`. "
            f"The governed repositories are: {', '.join(REPOSITORIES)}."
        )
    rules: dict[str, Rules] = {}
    for name in REPOSITORIES:
        if name not in repositories:
            raise AutoMergeError(
                f"{CONFIG_NAME}: `repositories.{name}` is missing. Every governed repository needs "
                f"its table, even an empty `[repositories.{name}]`, so none is judged by accident."
            )
        where = f"repositories.{name}"
        own = _table(repositories, "repositories", name)
        _keys(own, where, (*LIMIT_KEYS, "protected"), ())
        limits = {
            key: _limit(own, where, key) if key in own else base_limits[key] for key in LIMIT_KEYS
        }
        extra = _strings(own, where, "protected") if "protected" in own else ()
        rules[name] = Rules(
            limits=Limits(**limits),
            generated=_strings(defaults, "defaults", "generated"),
            prose=_strings(defaults, "defaults", "prose"),
            complexity_exclude=_strings(defaults, "defaults", "complexity_exclude"),
            languages=languages,
            protected=(*_strings(defaults, "defaults", "protected"), *extra),
        )
    return Config(rules)


def read_config(root: Path) -> Config:
    """The config at the repository's root; a missing file is an error, never "no rules"."""
    try:
        text = (root / CONFIG_NAME).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise AutoMergeError(f"{CONFIG_NAME} is missing at {root}.") from None
    return parse_config(text)


# --- GitHub (design D2) ---------------------------------------------------------------------------

APP_LOGIN = "troupe-run-merge[bot]"
"""The App whose comments carry the markers: only its comments count (design D5)."""
RULE = "safe-PR rule v1 (#319)"
HOLD = "hold"
AUTO_MERGED = "auto-merged"
NEEDS_OWNER = "needs:owner"
DECISION = "Decision"
SWITCH = "AUTO_MERGE"
SWITCH_VALUES = ("off", "dry-run", "on")
REVIEW_WORKFLOW = "claude-review.yml"
REVIEW_ARTIFACT = "review-result"
DELIVERY_LIST = ".github/guard-delivery.json"
MARKER = re.compile(r"<!-- auto-merge:(?P<kind>queued|dry-run) (?P<head>[0-9a-f]{40}) -->")
SIGNED_OFF = re.compile(r"^Signed-off-by: \S.* <[^>]+>\s*$", re.MULTILINE)
BOT_EMAIL = re.compile(r"\[bot\]@users\.noreply\.github\.com\Z")
COMPONENT = re.compile(
    r"(?:\A|/)(?:pyproject\.toml|package\.json)\Z|\Aopenspec/specs/[^/]+/spec\.md\Z"
)
"""A file whose deletion deletes a component (spec: "Nothing protected changes")."""
PASSING = frozenset({"success", "skipped", "neutral"})
"""Check-run conclusions GitHub counts as passing a required check."""


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


# --- One pull request's facts, read when a condition first needs them (design D2, D3) -------------

PULL_REQUEST_QUERY = """
query($owner: String!, $name: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      id number title body state isDraft baseRefName headRefName headRefOid changedFiles mergeable
      reviewDecision
      author { login }
      headRepository { nameWithOwner }
      mergeQueueEntry { id }
      labels(first: 100) { nodes { name } }
      closingIssuesReferences(first: 50) { nodes { number repository { nameWithOwner } } }
      reviewThreads(first: 100, after: $after) {
        nodes { isResolved }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""


@dataclass(frozen=True)
class Check:
    """One condition's result: whether it holds, and what it saw."""

    name: str
    ok: bool
    saw: str


class PullRequest:
    """One open pull request in a governed repository, read lazily through the API."""

    def __init__(
        self,
        gh: GitHub,
        repository: str,
        number: int,
        rules: Rules,
        measure: Callable[[PullRequest], tuple[int, int]] | None = None,
    ) -> None:
        self.gh = gh
        self.repository = repository
        self.full = f"{OWNER}/{repository}"
        self.number = number
        self.rules = rules
        self.measure = measure

    # The pull request itself ------------------------------------------------------------------

    @cached_property
    def data(self) -> Mapping[str, object]:
        threads: list[object] = []
        after: str | None = None
        first: Mapping[str, object] | None = None
        while True:
            answer = self.gh.graphql(
                PULL_REQUEST_QUERY,
                {"owner": OWNER, "name": self.repository, "number": self.number, "after": after},
            )
            pull = _dict(_dict(_dict(answer, "the answer").get("repository"), "repository").get(
                "pullRequest"), "pullRequest")  # fmt: skip
            first = first or pull
            page = _dict(pull.get("reviewThreads"), "reviewThreads")
            threads.extend(_list(page.get("nodes"), "reviewThreads.nodes"))
            info = _dict(page.get("pageInfo"), "pageInfo")
            if not info.get("hasNextPage"):
                break
            after = _text(info.get("endCursor"), "endCursor")
        return {**first, "threads": threads}

    @property
    def head(self) -> str:
        return _text(self.data.get("headRefOid"), "headRefOid")

    @property
    def author(self) -> str:
        return _text(_dict(self.data.get("author"), "author").get("login"), "author.login")

    @property
    def labels(self) -> set[str]:
        nodes = _list(_dict(self.data.get("labels"), "labels").get("nodes"), "labels.nodes")
        return {_text(_dict(node, "label").get("name"), "label.name") for node in nodes}

    @property
    def queued(self) -> bool:
        return self.data.get("mergeQueueEntry") is not None

    @cached_property
    def comments(self) -> list[Mapping[str, object]]:
        listing = get_all(self.gh, f"repos/{self.full}/issues/{self.number}/comments")
        return [_dict(comment, "comment") for comment in listing]

    def markers(self, kind: str) -> set[str]:
        """The heads the App's comments mark with ``kind`` (design D5): only its own count."""
        heads = set()
        for comment in self.comments:
            user = comment.get("user")
            if not isinstance(user, dict) or user.get("login") != APP_LOGIN:
                continue
            for match in MARKER.finditer(str(comment.get("body") or "")):
                if match.group("kind") == kind:
                    heads.add(match.group("head"))
        return heads

    @cached_property
    def files(self) -> list[Mapping[str, object]]:
        listing = [
            _dict(item, "file")
            for item in get_all(self.gh, f"repos/{self.full}/pulls/{self.number}/files")
        ]
        expected = self.data.get("changedFiles")
        if not isinstance(expected, int) or len(listing) != expected:
            raise AutoMergeError(
                f"GitHub listed {len(listing)} changed files of {expected}: the listing stops at "
                "3,000, so the change can't be judged"
            )
        return listing

    @cached_property
    def commits(self) -> list[Mapping[str, object]]:
        return [
            _dict(item, "commit")
            for item in get_all(self.gh, f"repos/{self.full}/pulls/{self.number}/commits")
        ]


# --- The conditions, cheapest first (design D3) ---------------------------------------------------


def ready(pr: PullRequest) -> Check:
    data = pr.data
    head_repository = data.get("headRepository")
    head_name = head_repository.get("nameWithOwner") if isinstance(head_repository, dict) else None
    problems = []
    if data.get("state") != "OPEN":
        problems.append(f"it's {str(data.get('state')).lower()}")
    if data.get("isDraft") is not False:
        problems.append("it's a draft")
    if data.get("baseRefName") != "main":
        problems.append(f"it targets {data.get('baseRefName')}, not main")
    if head_name != pr.full:
        problems.append(f"its branch is in {head_name or 'a deleted fork'}, not {pr.full}")
    if HOLD in pr.labels:
        problems.append("it has the `hold` label")
    if data.get("mergeable") == "CONFLICTING":
        problems.append("it conflicts with main")
    elif data.get("mergeable") != "MERGEABLE":
        problems.append("GitHub hasn't worked out yet whether it conflicts with main")
    if problems:
        return Check("ready", False, "; ".join(problems))
    return Check(
        "ready", True, "open, not a draft, on main, from this repository, no hold, no conflict"
    )


def not_queued_before(pr: PullRequest) -> Check:
    if pr.head in pr.markers("queued"):
        return Check(
            "queued once per head",
            False,
            f"the App queued {pr.head[:7]} before, and it left the queue unmerged: re-queueing it "
            "is the owner's",
        )
    return Check("queued once per head", True, f"{pr.head[:7]} not queued by the App before")


def required_checks(pr: PullRequest) -> Check:
    rules = _list(pr.gh.get(f"repos/{pr.full}/rules/branches/main"), "the branch's rules")
    required: list[tuple[str, int | None]] = []
    for rule in rules:
        rule = _dict(rule, "rule")
        if rule.get("type") != "required_status_checks":
            continue
        parameters = _dict(rule.get("parameters"), "required_status_checks.parameters")
        for item in _list(parameters.get("required_status_checks"), "required_status_checks"):
            item = _dict(item, "required check")
            integration = item.get("integration_id")
            required.append(
                (
                    _text(item.get("context"), "context"),
                    integration if isinstance(integration, int) else None,
                )
            )
    if not required:
        return Check(
            "required checks",
            False,
            "main's rules name no required check, so nothing can be judged green",
        )
    runs = [
        _dict(run, "check run")
        for run in get_all(pr.gh, f"repos/{pr.full}/commits/{pr.head}/check-runs", "check_runs")
    ]
    statuses = _list(
        _dict(pr.gh.get(f"repos/{pr.full}/commits/{pr.head}/status"), "status").get("statuses"),
        "statuses",
    )
    failing, seen = [], []
    for context, integration in required:
        problem, url = _required_check(context, integration, runs, statuses)
        if problem is not None:
            failing.append(problem)
        seen.append(f"[{context}]({url})" if url else context)
    if failing:
        return Check("required checks", False, "; ".join(failing))
    return Check(
        "required checks", True, f"all {len(required)} green on {pr.head[:7]}: " + ", ".join(seen)
    )


def _required_check(
    context: str,
    integration: int | None,
    runs: Sequence[Mapping[str, object]],
    statuses: Sequence[object],
) -> tuple[str | None, str | None]:
    """Whether one required check passed on the head (None, or what's wrong), and the link to the
    run that decided it, for the record (spec: "A queued pull request records why")."""
    mine = [
        run for run in runs
        if run.get("name") == context
        and (integration is None or _dict(run.get("app") or {}, "app").get("id") == integration)
    ]  # fmt: skip
    if mine:
        latest = max(mine, key=lambda run: int(str(run.get("id", 0))))
        url = latest.get("html_url")
        link = url if isinstance(url, str) else None
        if latest.get("status") != "completed":
            return f"{context} is still {latest.get('status')}", link
        if latest.get("conclusion") not in PASSING:
            return f"{context} {latest.get('conclusion')}", link
        return None, link
    status = [_dict(s, "status") for s in statuses if _dict(s, "status").get("context") == context]
    if status and status[0].get("state") == "success":
        url = status[0].get("target_url")
        return None, url if isinstance(url, str) else None
    return f"{context} hasn't reported", None


def conversations(pr: PullRequest) -> Check:
    threads = _list(pr.data.get("threads"), "threads")
    unresolved = sum(1 for thread in threads if not _dict(thread, "thread").get("isResolved"))
    problems = []
    if unresolved:
        problems.append(f"{unresolved} conversation(s) open")
    if pr.data.get("reviewDecision") == "CHANGES_REQUESTED":
        problems.append("a review requests changes")
    if problems:
        return Check("conversations", False, "; ".join(problems))
    return Check("conversations", True, f"all {len(threads)} resolved, no changes requested")


def _is_bot(user: object, email: object) -> bool | None:
    """Whether a commit's author or committer is a bot; None when neither identity can be read."""
    if isinstance(user, dict) and user.get("type") == "Bot":
        return True
    if isinstance(email, str) and BOT_EMAIL.search(email):
        return True
    if not isinstance(user, dict) and not isinstance(email, str):
        return None
    return False


def commits(pr: PullRequest) -> Check:
    problems = []
    for item in pr.commits:
        sha = str(item.get("sha", "?"))[:7]
        commit = _dict(item.get("commit"), "commit.commit")
        if not SIGNED_OFF.search(str(commit.get("message") or "")):
            problems.append(f"{sha} has no Signed-off-by")
        for role in ("author", "committer"):
            git_identity = commit.get(role)
            email = git_identity.get("email") if isinstance(git_identity, dict) else None
            bot = _is_bot(item.get(role), email)
            if bot is None:
                problems.append(f"{sha}'s {role} can't be read")
            elif bot:
                who = item.get(role)
                name = who.get("login") if isinstance(who, dict) else email
                problems.append(f"{sha}'s {role} is a bot ({name})")
    if not pr.commits:
        problems.append("it has no commits")
    if problems:
        return Check("commits", False, "; ".join(problems))
    return Check("commits", True, f"{len(pr.commits)} commit(s), each a person's and signed off")


def pushed_by_author(pr: PullRequest) -> Check:
    """Every pull_request run for the head was started by the author (design D12)."""
    runs = get_all(
        pr.gh,
        f"repos/{pr.full}/actions/runs?head_sha={pr.head}&event=pull_request",
        "workflow_runs",
    )
    if not runs:
        return Check(
            "pushed by the author",
            False,
            f"no workflow ran for {pr.head[:7]} from a pull request event, so who pushed it "
            "can't be read",
        )
    others = set()
    for run in runs:
        run = _dict(run, "workflow run")
        for role in ("actor", "triggering_actor"):
            who = run.get(role)
            login = who.get("login") if isinstance(who, dict) else None
            if login != pr.author:
                others.add(str(login))
    if others:
        return Check(
            "pushed by the author",
            False,
            f"runs for {pr.head[:7]} were started by {', '.join(sorted(others))}, not the "
            f"author {pr.author}",
        )
    return Check(
        "pushed by the author",
        True,
        f"all {len(runs)} run(s) for {pr.head[:7]} started by {pr.author}",
    )


def archived(pr: PullRequest) -> Check:
    branch = _text(pr.data.get("headRefName"), "headRefName")
    try:
        pr.gh.get(f"repos/{pr.full}/contents/openspec/changes/{branch}?ref={pr.head}")
    except NotFoundError:
        return Check("archived", True, f"no active change `{branch}` at {pr.head[:7]}")
    return Check(
        "archived", False, f"openspec/changes/{branch}/ is still there: archive the change"
    )


def closed_issues(pr: PullRequest) -> list[tuple[str, int]]:
    import guard  # the closing lines are read as pr-closes-issue reads them

    found = guard.closed_issues(str(pr.data.get("body") or ""), pr.full)
    references = _dict(pr.data.get("closingIssuesReferences"), "closingIssuesReferences")
    for node in _list(references.get("nodes"), "closingIssuesReferences.nodes"):
        node = _dict(node, "closing reference")
        repository = _text(
            _dict(node.get("repository"), "repository").get("nameWithOwner"), "nameWithOwner"
        )
        issue = (repository, int(str(node.get("number"))))
        if issue not in found:
            found.append(issue)
    return found


def issues(pr: PullRequest) -> Check:
    import guard

    def read(path: str) -> object:
        try:
            return pr.gh.get(path)
        except AutoMergeError as error:
            raise guard.UnreadableGitHubError(str(error)) from error

    closing = closed_issues(pr)
    problems = []
    for repository, number in closing:
        name = f"{repository}#{number}"
        issue = _dict(pr.gh.get(f"repos/{repository}/issues/{number}"), name)
        kind = issue.get("type")
        if isinstance(kind, dict) and kind.get("name") == DECISION:
            problems.append(f"{name} is a Decision")
        labels = {
            str(_dict(label, "label").get("name")) for label in _list(issue.get("labels"), "labels")
        }
        if NEEDS_OWNER in labels:
            problems.append(f"{name} is labelled {NEEDS_OWNER}")
        try:
            blockers = guard.open_blockers(repository, number, read)
        except guard.UnreadableGitHubError as error:
            raise AutoMergeError(f"couldn't read what blocks {name}: {error}") from error
        problems.extend(f"{name} is blocked by {blocker}, still open" for blocker in blockers)
    if problems:
        return Check("closed issues", False, "; ".join(problems))
    named = ", ".join(f"{r}#{n}" for r, n in closing) or "none"
    return Check("closed issues", True, f"no Decision, no {NEEDS_OWNER}, nothing blocked: {named}")


def delivered(pr: PullRequest) -> frozenset[str]:
    """The repository's delivered files on main, which are protected (spec)."""
    try:
        answer = _dict(
            pr.gh.get(f"repos/{pr.full}/contents/{DELIVERY_LIST}?ref=main"), DELIVERY_LIST
        )
    except NotFoundError:
        return frozenset()
    listing = _dict(
        json.loads(base64.b64decode(_text(answer.get("content"), "content"))), DELIVERY_LIST
    )
    return frozenset(
        _text(path, "a delivered path") for path in _list(listing.get("files"), "files")
    )


def protected(pr: PullRequest) -> Check:
    shipped = delivered(pr)
    hits = []
    for file in pr.files:
        paths = [_text(file.get("filename"), "filename")]
        if isinstance(file.get("previous_filename"), str):
            paths.append(str(file["previous_filename"]))
        for path in paths:
            if pr.rules.is_protected(path) or path in shipped:
                hits.append(path)
            elif file.get("status") == "removed" and COMPONENT.search(path):
                hits.append(f"{path} (deletes a component)")
    if hits:
        return Check("protected", False, "changes " + ", ".join(sorted(set(hits))[:10]))
    return Check("protected", True, f"none of its {len(pr.files)} files is protected")


def size(pr: PullRequest) -> Check:
    limits = pr.rules.limits
    counted = [
        f for f in pr.files if not pr.rules.is_generated(_text(f.get("filename"), "filename"))
    ]
    lines = sum(
        int(str(f.get("additions", 0))) + int(str(f.get("deletions", 0)))
        for f in counted
        if not pr.rules.is_prose(_text(f.get("filename"), "filename"))
    )
    problems = []
    if lines > limits.max_lines:
        problems.append(f"lines {lines} > {limits.max_lines}")
    if len(counted) > limits.max_files:
        problems.append(f"files {len(counted)} > {limits.max_files}")
    saw = f"lines {lines}/{limits.max_lines}, files {len(counted)}/{limits.max_files}"
    if pr.measure is None:
        raise AutoMergeError("no way to measure complexity was given")
    highest, increase = pr.measure(pr)
    if highest > limits.max_function_complexity:
        problems.append(f"max complexity {highest} > {limits.max_function_complexity}")
    if increase > limits.max_complexity_increase:
        problems.append(f"complexity increase {increase} > {limits.max_complexity_increase}")
    saw += (
        f", max complexity {highest}/{limits.max_function_complexity}, "
        f"increase {increase}/{limits.max_complexity_increase}"
    )
    if problems:
        return Check("size", False, "; ".join(problems))
    return Check("size", True, saw)


def review_result(pr: PullRequest, sha: str) -> Mapping[str, object] | None:
    """The newest pull_request review run's recorded result for ``sha``, or None if there's none."""
    runs = get_all(
        pr.gh,
        f"repos/{pr.full}/actions/workflows/{REVIEW_WORKFLOW}/runs?head_sha={sha}&event=pull_request",
        "workflow_runs",
    )
    if not runs:
        return None
    newest = max((_dict(run, "run") for run in runs), key=lambda run: int(str(run.get("id", 0))))
    artifacts = _list(
        _dict(
            pr.gh.get(f"repos/{pr.full}/actions/runs/{newest.get('id')}/artifacts"), "artifacts"
        ).get("artifacts"),
        "artifacts",
    )
    named = [
        _dict(a, "artifact")
        for a in artifacts
        if _dict(a, "artifact").get("name") == REVIEW_ARTIFACT
    ]
    if not named:
        return None
    body = pr.gh.raw(f"repos/{pr.full}/actions/artifacts/{named[0].get('id')}/zip")
    try:
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            result = json.loads(archive.read("review-result.json"))
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as error:
        raise AutoMergeError(f"the review result for {sha[:7]} can't be read: {error}") from error
    return _dict(result, "review result")


def _only_openspec(pr: PullRequest, sha: str) -> bool:
    commit = _dict(pr.gh.get(f"repos/{pr.full}/commits/{sha}"), f"commit {sha[:7]}")
    files = _list(commit.get("files"), "files")
    return bool(files) and all(
        _text(_dict(f, "file").get("filename"), "filename").startswith("openspec/") for f in files
    )


def review(pr: PullRequest) -> Check:
    """The head's review read everything, or, past commits that change only openspec/, an earlier
    commit's did (#319's carve-out; design D6)."""
    shas = [_text(item.get("sha"), "sha") for item in pr.commits]
    if not shas or shas[-1] != pr.head:
        return Check("review", False, "the commit list doesn't end at the head")
    for index in range(len(shas) - 1, -1, -1):
        sha = shas[index]
        result = review_result(pr, sha)
        if (
            result is not None
            and result.get("head") == sha
            and result.get("coverage") == "complete"
        ):
            via = (
                "" if sha == pr.head else f", carried past openspec/-only commits to {pr.head[:7]}"
            )
            return Check("review", True, f"coverage complete on {sha[:7]}{via}")
        if not _only_openspec(pr, sha):
            coverage = result.get("coverage") if result is not None else "no result recorded"
            return Check(
                "review", False, f"the review of {sha[:7]}: coverage {coverage}, not complete"
            )
    return Check("review", False, "no commit's review read everything")


CONDITIONS: tuple[Callable[[PullRequest], Check], ...] = (
    ready,
    not_queued_before,
    required_checks,
    conversations,
    commits,
    pushed_by_author,
    archived,
    issues,
    protected,
    size,
    review,
)
"""In order, cheapest first (design D3): the first that fails ends the judging."""


@dataclass
class Verdict:
    qualified: bool
    checks: list[Check] = field(default_factory=list)
    error: str | None = None

    def line(self) -> str:
        if self.error is not None:
            return f"error: {self.error}"
        if self.qualified:
            return "qualifies"
        failed = self.checks[-1]
        return f"{failed.name}: {failed.saw}"


def judge_every(pr: PullRequest) -> Verdict:
    """Every condition's result, failures and errors included: for reading a pull request, never
    for deciding (the run uses judge)."""
    verdict = Verdict(True)
    for condition in CONDITIONS:
        try:
            check = condition(pr)
        except AutoMergeError as error:
            check = Check(condition.__name__, False, f"error: {error}")
        verdict.checks.append(check)
        verdict.qualified = verdict.qualified and check.ok
    return verdict


def judge(pr: PullRequest) -> Verdict:
    verdict = Verdict(False)
    try:
        for condition in CONDITIONS:
            check = condition(pr)
            verdict.checks.append(check)
            if not check.ok:
                return verdict
    except AutoMergeError as error:
        verdict.error = str(error)
        return verdict
    verdict.qualified = True
    return verdict


# --- Complexity, from git data: nothing of the pull request's is run (design D2) ------------------

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", re.MULTILINE)


def _git(where: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(where), *args], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        raise AutoMergeError(f"git {' '.join(args[:2])} failed: {done.stderr.strip()[-300:]}")
    return done.stdout


def changed_lines(clone: Path, base: str, head: str) -> dict[str, set[int]]:
    """Each file there at ``head`` that changed since ``base``, with its new or edited lines."""
    diff = _git(
        clone, "diff", "-U0", "--no-renames", "--no-ext-diff", "--no-color", base, head, "--"
    )
    changed: dict[str, set[int]] = {}
    for section in re.split(r"^diff --git ", diff, flags=re.MULTILINE)[1:]:
        target = re.search(r"^\+\+\+ b/(.+)$", section, re.MULTILINE)
        if target is None:
            continue  # deleted, or binary
        lines: set[int] = set()
        for start, length in HUNK.findall(section):
            count = int(length) if length else 1
            lines.update(range(int(start), int(start) + count))
        changed[target.group(1)] = lines
    return changed


def _copies(clone: Path, revision: str, paths: Iterable[str], into: Path) -> list[str]:
    present = []
    for path in paths:
        shown = subprocess.run(
            ["git", "-C", str(clone), "show", f"{revision}:{path}"],
            capture_output=True,
            check=False,
        )
        if shown.returncode != 0:
            continue  # not there at this revision
        target = into / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(shown.stdout)
        present.append(path)
    return present


def _by_name(functions: Iterable[Function]) -> dict[tuple[str, str], int]:
    """Each function's complexity, keyed by its file and name, not its signature: a function whose
    parameters change is edited, not new. Two of one name in a file count as their highest."""
    found: dict[tuple[str, str], int] = {}
    for function in functions:
        key = (function.path, function.name)
        found[key] = max(found.get(key, 0), function.complexity)
    return found


def complexity(clone: Path, base: str, head: str, rules: Rules, lizard: str) -> tuple[int, int]:
    """Over the functions that are new, or whose cyclomatic complexity rose (owner, 2026-11-19: the
    calibration's measure), the highest complexity and the sum of the rises, a new function
    counting whole. Measured with lizard on copies of the changed files at the base and the head;
    functions are matched by file and name. A refactor that lowers complexity, or an edit that adds
    no branching, counts for nothing."""
    extensions = tuple(ext for language in rules.languages for ext in LANGUAGES[language])
    changes = [
        path
        for path in changed_lines(clone, base, head)
        if path.endswith(extensions) and not excluded(path, rules.complexity_exclude)
    ]
    if not changes:
        return 0, 0
    with tempfile.TemporaryDirectory() as scratch:
        before_dir, after_dir = Path(scratch, "base"), Path(scratch, "head")
        try:
            before = _by_name(
                lizard_functions(lizard, before_dir, _copies(clone, base, changes, before_dir))
            )
            after = _by_name(
                lizard_functions(lizard, after_dir, _copies(clone, head, changes, after_dir))
            )
        except GateError as error:
            raise AutoMergeError(str(error)) from error
    rose = [
        (value, before.get(key, 0)) for key, value in after.items() if value > before.get(key, 0)
    ]
    highest = max((value for value, _ in rose), default=0)
    return highest, sum(value - old for value, old in rose)


class Clones:
    """One blobless bare clone per repository, fetched per pull request (design D2)."""

    def __init__(self, root: Path, lizard: str) -> None:
        self.root = root
        self.lizard = lizard

    def clone(self, repository: str) -> Path:
        where = self.root / f"{repository}.git"
        if not where.exists():
            done = subprocess.run(
                ["git", "clone", "-q", "--bare", "--filter=blob:none", "--no-tags",
                 f"https://github.com/{OWNER}/{repository}.git", str(where)],
                capture_output=True, text=True, check=False,
            )  # fmt: skip
            if done.returncode != 0:
                raise AutoMergeError(f"couldn't clone {repository}: {done.stderr.strip()[-300:]}")
        return where

    def measure(self, pr: PullRequest) -> tuple[int, int]:
        where = self.clone(pr.repository)
        pull = f"+refs/pull/{pr.number}/head:refs/pr/{pr.number}"
        _git(where, "fetch", "-q", "--no-tags", "origin", pull, "+refs/heads/main:refs/heads/main")
        base = _git(where, "merge-base", "main", pr.head).strip()
        return complexity(where, base, pr.head, pr.rules, self.lizard)


# --- Acting on the verdict (design D5) ------------------------------------------------------------

ENQUEUE = """mutation($id: ID!, $head: GitObjectID!) {
  enqueuePullRequest(input: {pullRequestId: $id, expectedHeadOid: $head}) { mergeQueueEntry { id } }
}"""
DEQUEUE = """mutation($id: ID!) {
  dequeuePullRequest(input: {id: $id}) { mergeQueueEntry { id } }
}"""
DOCS = (
    "https://github.com/troupe-run/infrastructure/blob/main/docs/development-workflow.md#auto-merge"
)


def comment_body(pr: PullRequest, verdict: Verdict, kind: str) -> str:
    """The record of what each condition saw (spec: "A queued pull request records why")."""
    if kind == "queued":
        title = f"**Queued by auto-merge** at `{pr.head}`, under the {RULE}."
        after = "To stop it, add the `hold` label: the App takes it out of the queue."
    else:
        title = (
            f"**Auto-merge would have queued this** at `{pr.head}`, under the {RULE}. "
            "It's in dry-run here, so nothing was queued."
        )
        after = "This is a record for the dry-run week; queue it by hand as usual."
    rows = "\n".join(f"| {check.name} | {check.saw} |" for check in verdict.checks)
    return (
        f"<!-- auto-merge:{kind} {pr.head} -->\n{title}\n\n| Condition | What it saw |\n|---|---|\n"
        f"{rows}\n\n{after} How this works: {DOCS}"
    )


def act(pr: PullRequest, mode: str) -> str:
    """Judge one pull request and do what its repository's switch says. Returns its summary line."""
    if pr.queued:
        if HOLD in pr.labels and pr.head in pr.markers("queued"):
            pr.gh.graphql(DEQUEUE, {"id": _text(pr.data.get("id"), "id")})
            return "held: taken out of the queue the App put it in"
        return "already in the queue"
    verdict = judge(pr)
    if not verdict.qualified:
        return verdict.line()
    if mode == "dry-run":
        if pr.head in pr.markers("dry-run"):
            return "qualifies (dry-run; already commented on this head)"
        pr.gh.write(
            "POST",
            f"repos/{pr.full}/issues/{pr.number}/comments",
            {"body": comment_body(pr, verdict, "dry-run")},
        )
        return "qualifies (dry-run): commented"
    # The record goes first, so a head is never queued twice even if what follows fails (D5).
    pr.gh.write(
        "POST",
        f"repos/{pr.full}/issues/{pr.number}/comments",
        {"body": comment_body(pr, verdict, "queued")},
    )
    pr.gh.graphql(ENQUEUE, {"id": _text(pr.data.get("id"), "id"), "head": pr.head})
    pr.gh.write("POST", f"repos/{pr.full}/issues/{pr.number}/labels", {"labels": [AUTO_MERGED]})
    return "queued"


def switch(gh: GitHub, repository: str) -> str:
    """The repository's AUTO_MERGE: unset is off; any value but off, dry-run and on is an error."""
    try:
        answer = _dict(gh.get(f"repos/{OWNER}/{repository}/actions/variables/{SWITCH}"), SWITCH)
    except NotFoundError:
        return "off"
    value = answer.get("value")
    if value not in SWITCH_VALUES:
        raise AutoMergeError(
            f"{OWNER}/{repository}'s {SWITCH} is {value!r}: it must be one of "
            f"{', '.join(SWITCH_VALUES)}, so nothing is done there"
        )
    return str(value)


def run(
    gh: GitHub,
    config: Config,
    measure: Callable[[PullRequest], tuple[int, int]],
    say: Callable[[str], None] = print,
    as_if: str | None = None,
) -> int:
    """Judge every open pull request of the governed repositories. 1 if anything couldn't be
    judged or done, so the run shows red; 0 otherwise."""
    status = 0
    for repository in REPOSITORIES:
        full = f"{OWNER}/{repository}"
        try:
            mode = as_if or switch(gh, repository)
        except AutoMergeError as error:
            say(f"- {full}: error: {error}")
            status = 1
            continue
        if mode == "off":
            say(f"- {full}: {SWITCH} is off, so nothing is judged")
            continue
        try:
            open_prs = get_all(gh, f"repos/{full}/pulls?state=open")
        except AutoMergeError as error:
            say(f"- {full}: error: couldn't list open pull requests: {error}")
            status = 1
            continue
        say(f"- {full} ({mode}): {len(open_prs)} open pull request(s)")
        for item in open_prs:
            number = int(str(_dict(item, "pull request").get("number")))
            pr = PullRequest(gh, repository, number, config.repositories[repository], measure)
            try:
                line = act(pr, mode)
            except AutoMergeError as error:
                line = f"error: {error}"
            if line.startswith("error"):
                status = 1
            say(f"  - #{number}: {line}")
    return status


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    go = sub.add_parser("run", help="judge every open pull request, and act as each switch says")
    go.add_argument(
        "--recorder", type=Path, help="record writes to this file instead of sending them"
    )
    go.add_argument(
        "--clones", type=Path, help="where to keep the clones (default: a temporary directory)"
    )
    go.add_argument(
        "--as-if",
        choices=SWITCH_VALUES,
        help="judge every repository as if its switch said this; only with --recorder",
    )
    one = sub.add_parser("judge", help="judge one pull request and print what each condition saw")
    one.add_argument("repository", choices=REPOSITORIES)
    one.add_argument("number", type=int)
    one.add_argument("--tape", type=Path, help="write every read's answer to this file")
    one.add_argument(
        "--every",
        action="store_true",
        help="run every condition, not stopping at the first failure",
    )
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    lizard = shutil.which("lizard", path=str(Path(sys.executable).parent)) or shutil.which("lizard")
    if lizard is None:
        print("auto-merge: lizard isn't installed (uv sync installs it).", file=sys.stderr)
        return 1
    try:
        config = read_config(root)
    except AutoMergeError as error:
        print(f"auto-merge: {error}", file=sys.stderr)
        return 1
    gh: GitHub = GhCli()
    if args.command == "judge":
        tape = Tape(gh)
        with tempfile.TemporaryDirectory() as scratch:
            pr = PullRequest(
                tape,
                args.repository,
                args.number,
                config.repositories[args.repository],
                Clones(Path(scratch), lizard).measure,
            )
            verdict = judge_every(pr) if args.every else judge(pr)
        for check in verdict.checks:
            print(f"{'ok  ' if check.ok else 'FAIL'} {check.name}: {check.saw}")
        print(verdict.line())
        if args.tape:
            args.tape.write_text(
                json.dumps(tape.reads, indent=1, sort_keys=True) + "\n", encoding="utf-8"
            )
        return 0
    if args.as_if and not args.recorder:
        parser.error("--as-if only with --recorder: it must never act on GitHub")
    recorder = Recorder(gh) if args.recorder else None
    lines: list[str] = []

    def say(line: str) -> None:
        lines.append(line)
        print(line)

    with tempfile.TemporaryDirectory() as scratch:
        clones = Clones(args.clones or Path(scratch), lizard)
        status = run(recorder or gh, config, clones.measure, say, as_if=args.as_if)
    if recorder is not None:
        args.recorder.write_text(json.dumps(recorder.writes, indent=2) + "\n", encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write("## Auto-merge\n\n" + "\n".join(lines) + "\n")
    return status


if __name__ == "__main__":
    sys.exit(main())
