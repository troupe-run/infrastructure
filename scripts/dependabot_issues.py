"""Gives every Dependabot pull request its issue, and links the pull request to it (spec:
dependency-updates; #172; openspec/changes/dependabot-issues/design.md).

Usage: uv run scripts/dependabot_issues.py

For each repository with Dependabot ecosystems in tofu/labels/dependabot.json, this reads the open
pull requests by dependabot[bot] and the issues the troupe-run-dependabot App opened. Each open pull
request gets an issue (type Task, label `dependencies`, the release in progress as milestone), or
reuses the open one for the same dependency, and its description gets `Closes #<n>`. An issue whose
pull request merged, or closed with no successor after an hour, is closed (design D2, D3). It never
reads a pull request's files: only the API's metadata, and the description to find its own line.

It exits 1 when it couldn't handle a repository, after handling the others, and 2 when it couldn't
start at all. Outside GitHub Actions it only reads, and prints what it would do (design D8).
"""

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "tofu" / "labels" / "dependabot.json"
MILESTONES = ROOT / "tofu" / "milestones.json"
ORG = "troupe-run"
DEPENDABOT = "dependabot[bot]"
APP = "troupe-run-dependabot[bot]"
LABEL = "dependencies"
ISSUE_TYPE = "Task"
# How long a pull request closed without merging waits for a successor before its issue closes.
GRACE = timedelta(hours=1)
# Closed issues are read back this far, so a reopened pull request finds its issue again.
CLOSED_LOOKBACK = timedelta(days=30)
DOCS = (
    "https://github.com/troupe-run/infrastructure/blob/main/docs/development-workflow.md"
    "#dependabot-pull-requests"
)

# A Conventional prefix, then Dependabot's own words (design D3). Dependabot capitalises `Bump`.
TITLE = re.compile(
    r"(?:[a-z]+(?:\([^)]*\))?!?:\s*)?(?:[Bb]ump|[Uu]pdate)\s+(?P<dependency>.+?)"
    r"(?:\s+requirement)?\s+from\s+(?P<old>\S+)\s+to\s+(?P<new>\S+)(?:\s+in\s+(?P<directory>\S+))?"
)
PREFIX = re.compile(r"[a-z]+(?:\([^)]*\))?!?:\s*")
BRANCH = re.compile(r"dependabot/(?P<ecosystem>[a-z0-9_-]+)/.+")
VERSION = re.compile(r"v?(\d+(?:\.\d+)*)")
MILESTONE_TITLE = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
MARKER = re.compile(r"<!-- dependabot-issue: (\{.*?\}) -->")


class StartError(Exception):
    """Something every repository needs couldn't be read, so nothing is done anywhere."""


class ReadError(Exception):
    """Something a repository needs couldn't be read, so nothing is done in it."""


class GhResult(NamedTuple):
    code: int
    stdout: str
    stderr: str


# gh's arguments, and what to send on its stdin (a write's JSON body), if anything.
Gh = Callable[[list[str], str | None], GhResult]


@dataclass(frozen=True)
class Key:
    """Which dependency an update is for: the same key in the same repository is the same issue."""

    ecosystem: str
    directory: str
    dependency: str


@dataclass(frozen=True)
class Update:
    """What a Dependabot pull request's branch and title say (design D3, D4)."""

    key: Key | None
    old: str | None
    new: str | None
    kind: str  # patch, minor, major or unknown


@dataclass(frozen=True)
class Marker:
    key: Key | None
    pull: int


@dataclass
class Action:
    kind: str  # open, relink, reopen, line, close-completed, close-not-planned
    pull: dict[str, Any]
    issue: dict[str, Any] | None = None


@dataclass
class Plan:
    actions: list[Action] = field(default_factory=list)


# --- Reading a pull request ---


def update_type(old: str | None, new: str | None) -> str:
    """Dependabot's counting: the first part that differs is major, the second minor, any later
    one patch. Anything that isn't a run of dotted digits is unknown (design D4)."""
    if old is None or new is None:
        return "unknown"
    a, b = VERSION.fullmatch(old), VERSION.fullmatch(new)
    if not a or not b:
        return "unknown"
    left = [int(part) for part in a.group(1).split(".")]
    right = [int(part) for part in b.group(1).split(".")]
    width = max(len(left), len(right))
    left += [0] * (width - len(left))
    right += [0] * (width - len(right))
    for index, (x, y) in enumerate(zip(left, right, strict=True)):
        if x != y:
            return ("major", "minor")[index] if index < 2 else "patch"
    return "unknown"


def read_update(pull: Mapping[str, Any]) -> Update:
    title = str(pull.get("title") or "")
    branch = str((pull.get("head") or {}).get("ref") or "")
    match = TITLE.fullmatch(title.strip())
    ecosystem = BRANCH.fullmatch(branch)
    if not match:
        return Update(None, None, None, "unknown")
    old, new = match.group("old"), match.group("new")
    key = None
    if ecosystem:
        key = Key(
            ecosystem.group("ecosystem"), match.group("directory") or "/", match.group("dependency")
        )
    return Update(key, old, new, update_type(old, new))


def issue_title(pull: Mapping[str, Any], update: Update) -> str:
    if update.key is None or update.old is None or update.new is None:
        return PREFIX.sub("", str(pull.get("title") or ""), count=1).strip() or (
            f"Dependabot pull request #{pull.get('number')}"
        )
    title = f"Update {update.key.dependency} from {update.old} to {update.new}"
    if update.key.directory != "/":
        title += f" in {update.key.directory}"
    return title


def marker(update: Update, pull: int) -> str:
    key = update.key
    fields = {
        "ecosystem": key.ecosystem if key else None,
        "directory": key.directory if key else None,
        "dependency": key.dependency if key else None,
        "pull": pull,
    }
    return f"<!-- dependabot-issue: {json.dumps(fields, sort_keys=True)} -->"


def issue_body(pull: Mapping[str, Any], update: Update) -> str:
    number = pull["number"]
    where = f" ({update.key.ecosystem}, `{update.key.directory}`)" if update.key is not None else ""
    lines = [
        f"Dependabot's pull request #{number} updates a dependency{where}. Its description has "
        "the release notes.",
        "",
        f"Update type: **{update.kind}**.",
    ]
    if update.kind in ("major", "unknown"):
        lines += [
            "",
            "This update needs an OpenSpec change before it can merge: make the same update on "
            "a branch named after the change, with a pull request that closes this issue, and "
            f"close Dependabot's with a link ([Dependabot pull requests]({DOCS})).",
        ]
    lines += [
        "",
        "Opened by `dependabot-issues` in troupe-run/infrastructure (#172). It's relinked when "
        "Dependabot supersedes the update, and closed when the pull request merges or is closed.",
        "",
        marker(update, number),
    ]
    return "\n".join(lines)


def read_marker(issue: Mapping[str, Any]) -> Marker:
    """The marker the App wrote. A missing or malformed one is a ReadError: the App wrote it, so
    something is wrong, and guessing could close the wrong issue."""
    match = MARKER.search(str(issue.get("body") or ""))
    where = f"#{issue.get('number')}"
    if not match:
        raise ReadError(f"issue {where} has no dependabot-issue marker")
    try:
        fields = json.loads(match.group(1))
    except json.JSONDecodeError:
        raise ReadError(f"issue {where}'s marker isn't JSON") from None
    pull = fields.get("pull") if isinstance(fields, dict) else None
    if isinstance(pull, bool) or not isinstance(pull, int):
        raise ReadError(f"issue {where}'s marker has no pull request number")
    parts = [fields.get(name) for name in ("ecosystem", "directory", "dependency")]
    if all(isinstance(part, str) for part in parts):
        return Marker(Key(*parts), pull)
    if all(part is None for part in parts):
        return Marker(None, pull)
    raise ReadError(f"issue {where}'s marker has a partial key")


def closing_line(number: int) -> str:
    return f"Closes #{number}"


def has_closing_line(pull: Mapping[str, Any], number: int) -> bool:
    lines = str(pull.get("body") or "").splitlines()
    return any(line.strip() == closing_line(number) for line in lines)


def with_closing_line(pull: Mapping[str, Any], number: int) -> str:
    body = str(pull.get("body") or "").rstrip()
    return f"{body}\n\n{closing_line(number)}" if body else closing_line(number)


# --- Trust (design D6) ---


def is_dependabot(pull: Mapping[str, Any]) -> bool:
    user = pull.get("user") or {}
    return user.get("login") == DEPENDABOT and user.get("type") == "Bot"


def is_app_issue(issue: Mapping[str, Any]) -> bool:
    user = issue.get("user") or {}
    return (
        user.get("login") == APP
        and user.get("type") == "Bot"
        and "pull_request" not in issue
        and LABEL in labels_of(issue)
    )


def labels_of(issue: Mapping[str, Any]) -> list[str]:
    return [
        label if isinstance(label, str) else str((label or {}).get("name"))
        for label in issue.get("labels") or []
    ]


# --- Deciding (design D2) ---


def parse_time(value: object) -> datetime:
    try:
        return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        raise ReadError(f"{value!r} isn't a time") from None


def plan(
    open_pulls: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    linked: Mapping[int, dict[str, Any]],
    now: datetime,
) -> Plan:
    """What to do in one repository. open_pulls are Dependabot's open pull requests; issues are
    the App's, open and recently closed; linked holds each pull request an open issue names that
    isn't open."""
    result = Plan()
    pulls = sorted((p for p in open_pulls if is_dependabot(p)), key=lambda p: int(p["number"]))
    mine = sorted((i for i in issues if is_app_issue(i)), key=lambda i: int(i["number"]))
    markers = {int(i["number"]): read_marker(i) for i in mine}
    open_numbers = {int(p["number"]) for p in pulls}
    open_keys = {u.key for u in (read_update(p) for p in pulls) if u.key is not None}
    taken: set[int] = set()

    for pull in pulls:
        number = int(pull["number"])
        update = read_update(pull)
        issue = next(
            (
                i
                for i in mine
                if markers[int(i["number"])].pull == number and int(i["number"]) not in taken
            ),
            None,
        )
        if issue is not None:
            taken.add(int(issue["number"]))
            if issue.get("state") != "open":
                # Only the App closes an issue as not planned, when its pull request closed. One
                # closed as completed was done by a change that took the update over, and stays
                # closed until Dependabot closes its pull request as up to date.
                if issue.get("state_reason") != "not_planned":
                    continue
                result.actions.append(Action("reopen", pull, issue))
            if not has_closing_line(pull, int(issue["number"])):
                result.actions.append(Action("line", pull, issue))
            continue
        if update.key is not None:
            issue = next(
                (
                    i
                    for i in mine
                    if i.get("state") == "open"
                    and int(i["number"]) not in taken
                    and markers[int(i["number"])].key == update.key
                    and markers[int(i["number"])].pull not in open_numbers
                ),
                None,
            )
            if issue is not None:
                taken.add(int(issue["number"]))
                result.actions.append(Action("relink", pull, issue))
                if not has_closing_line(pull, int(issue["number"])):
                    result.actions.append(Action("line", pull, issue))
                continue
        result.actions.append(Action("open", pull))

    for issue in mine:
        number = int(issue["number"])
        if number in taken or issue.get("state") != "open":
            continue
        mark = markers[number]
        if mark.pull in open_numbers:
            continue  # its pull request is linked to an older issue of the App's
        closed = linked.get(mark.pull)
        if closed is None:
            raise ReadError(f"issue #{number}'s pull request #{mark.pull} wasn't read")
        if closed.get("state") == "open":
            continue  # not Dependabot's, which the App never links
        if closed.get("merged_at"):
            result.actions.append(Action("close-completed", closed, issue))
        elif now - parse_time(closed.get("closed_at")) >= GRACE and mark.key not in open_keys:
            result.actions.append(Action("close-not-planned", closed, issue))
    return result


# --- Reading GitHub ---


def gh_json(gh: Gh, path: str, paginate: bool = False) -> Any:  # noqa: ANN401 (JSON)
    args = ["api", *(["--paginate", "--slurp"] if paginate else []), path]
    result = gh(args, None)
    if result.code != 0:
        raise ReadError(f"{path}: {result.stderr.strip() or f'gh exited {result.code}'}")
    try:
        loaded = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise ReadError(f"{path}: GitHub's answer isn't JSON") from None
    if paginate:
        if not isinstance(loaded, list) or not all(isinstance(page, list) for page in loaded):
            raise ReadError(f"{path}: GitHub's pages aren't lists")
        return [item for page in loaded for item in page]
    return loaded


def repositories(text: str) -> list[str]:
    """The repositories with Dependabot ecosystems, in the labels file's order."""
    try:
        declared = json.loads(text)["repositories"]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise StartError("tofu/labels/dependabot.json has no repositories object") from None
    if not isinstance(declared, dict):
        raise StartError("tofu/labels/dependabot.json's repositories isn't an object")
    return [name for name, ecosystems in declared.items() if ecosystems]


def release_in_progress(text: str) -> str:
    """The open declared milestone with the lowest version (design D5)."""
    try:
        declared = json.loads(text)["milestones"]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise StartError("tofu/milestones.json has no milestones array") from None
    if not isinstance(declared, list):
        raise StartError("tofu/milestones.json's milestones isn't an array")
    versions = []
    for each in declared:
        if not isinstance(each, dict) or each.get("state") != "open":
            continue
        if match := MILESTONE_TITLE.fullmatch(str(each.get("title"))):
            versions.append((tuple(int(part) for part in match.groups()), match.group(0)))
    if not versions:
        raise StartError(
            "tofu/milestones.json has no open milestone, so there is no release in progress"
        )
    return min(versions)[1]


@dataclass
class Repository:
    name: str
    milestone: int
    open_pulls: list[dict[str, Any]]
    issues: list[dict[str, Any]]
    linked: dict[int, dict[str, Any]]


def read_repository(name: str, title: str, gh: Gh, now: datetime) -> Repository:
    base = f"repos/{ORG}/{name}"
    milestones = gh_json(gh, f"{base}/milestones?state=open&per_page=100", paginate=True)
    numbers = [
        m.get("number") for m in milestones if isinstance(m, dict) and m.get("title") == title
    ]
    if len(numbers) != 1 or not isinstance(numbers[0], int):
        raise ReadError(
            f"{ORG}/{name} has no open milestone titled {title}, the release in "
            "progress declared in tofu/milestones.json"
        )
    pulls = gh_json(gh, f"{base}/pulls?state=open&per_page=100", paginate=True)
    creator = APP.replace("[", "%5B").replace("]", "%5D")
    query = f"{base}/issues?creator={creator}&labels={LABEL}&per_page=100"
    since = (now - CLOSED_LOOKBACK).strftime("%Y-%m-%dT%H:%M:%SZ")
    issues = gh_json(gh, f"{query}&state=open", paginate=True) + gh_json(
        gh, f"{query}&state=closed&since={since}", paginate=True
    )
    open_numbers = {int(p["number"]) for p in pulls if is_dependabot(p)}
    linked: dict[int, dict[str, Any]] = {}
    for issue in issues:
        if not is_app_issue(issue) or issue.get("state") != "open":
            continue
        pull = read_marker(issue).pull
        if pull not in open_numbers and pull not in linked:
            linked[pull] = gh_json(gh, f"{base}/pulls/{pull}")
    return Repository(name, numbers[0], pulls, issues, linked)


# --- Writing (design D2): every field travels as JSON on stdin, never through a shell ---


def describe(action: Action) -> str:
    pull = f"#{action.pull['number']}"
    issue = f"#{action.issue['number']}" if action.issue else "a new issue"
    return {
        "open": f"open the issue “{issue_title(action.pull, read_update(action.pull))}” for "
        f"{pull} and add its closing line",
        "relink": f"relink {issue} to {pull}",
        "reopen": f"reopen {issue} for {pull}",
        "line": f"add `Closes {issue}` to {pull}",
        "close-completed": f"close {issue} as completed: {pull} merged",
        "close-not-planned": f"close {issue} as not planned: {pull} closed without merging",
    }[action.kind]


def write(gh: Gh, method: str, path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    result = gh(["api", "--method", method, path, "--input", "-"], json.dumps(payload))
    if result.code != 0:
        raise ReadError(f"{method} {path}: {result.stderr.strip() or f'gh exited {result.code}'}")
    try:
        answer = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise ReadError(f"{method} {path}: GitHub's answer isn't JSON") from None
    if not isinstance(answer, dict):
        raise ReadError(f"{method} {path}: GitHub's answer isn't an object")
    return answer


def comment(gh: Gh, base: str, issue: int, text: str) -> None:
    write(gh, "POST", f"{base}/issues/{issue}/comments", {"body": text})


def act(repo: Repository, action: Action, gh: Gh) -> dict[str, Any] | None:
    """Makes one action's writes. Returns the issue it opened or reopened, if any."""
    base = f"repos/{ORG}/{repo.name}"
    pull = action.pull
    number = int(pull["number"])
    update = read_update(pull)
    if action.kind == "open":
        issue = write(
            gh,
            "POST",
            f"{base}/issues",
            {
                "title": issue_title(pull, update),
                "body": issue_body(pull, update),
                "labels": [LABEL],
                "milestone": repo.milestone,
                "type": ISSUE_TYPE,
            },
        )
        write(
            gh,
            "PATCH",
            f"{base}/pulls/{number}",
            {"body": with_closing_line(pull, issue["number"])},
        )
        return issue
    if action.issue is None:
        raise ReadError(f"{action.kind} for #{number} names no issue")
    issue_number = int(action.issue["number"])
    if action.kind == "relink":
        old = read_marker(action.issue).pull
        write(
            gh,
            "PATCH",
            f"{base}/issues/{issue_number}",
            {"title": issue_title(pull, update), "body": issue_body(pull, update)},
        )
        comment(
            gh,
            base,
            issue_number,
            f"Dependabot superseded #{old} with #{number}, so this issue now tracks #{number}.",
        )
    elif action.kind == "reopen":
        write(gh, "PATCH", f"{base}/issues/{issue_number}", {"state": "open"})
        comment(gh, base, issue_number, f"#{number} was reopened, so this issue is too.")
        return action.issue
    elif action.kind == "line":
        write(
            gh, "PATCH", f"{base}/pulls/{number}", {"body": with_closing_line(pull, issue_number)}
        )
    elif action.kind == "close-completed":
        comment(gh, base, issue_number, f"#{number} merged.")
        write(
            gh,
            "PATCH",
            f"{base}/issues/{issue_number}",
            {"state": "closed", "state_reason": "completed"},
        )
    elif action.kind == "close-not-planned":
        comment(
            gh,
            base,
            issue_number,
            f"Dependabot's #{number} was closed without merging, and no pull request for the same "
            f"dependency opened within {int(GRACE.total_seconds() // 3600)} hour, so this update "
            "isn't planned.",
        )
        write(
            gh,
            "PATCH",
            f"{base}/issues/{issue_number}",
            {"state": "closed", "state_reason": "not_planned"},
        )
    return None


# --- The run ---


def run_gh(args: list[str], stdin: str | None) -> GhResult:
    result = subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True, check=False)
    return GhResult(result.returncode, result.stdout, result.stderr)


def run(
    labels: Path, milestones: Path, env: Mapping[str, str], gh: Gh, now: datetime | None = None
) -> int:
    now = now or datetime.now(UTC)
    try:
        names = repositories(labels.read_text(encoding="utf-8"))
        title = release_in_progress(milestones.read_text(encoding="utf-8"))
    except (OSError, StartError) as error:
        print(f"dependabot-issues: {error}. Nothing was read or changed.", file=sys.stderr)
        return 2
    in_actions = env.get("GITHUB_ACTIONS") == "true"
    failed: list[str] = []
    open_issues: list[str] = []
    for name in names:
        try:
            repo = read_repository(name, title, gh, now)
            decided = plan(repo.open_pulls, repo.issues, repo.linked, now)
        except ReadError as error:
            print(
                f"dependabot-issues: {ORG}/{name}: couldn't read {error}. Nothing was changed "
                "there.",
                file=sys.stderr,
            )
            failed.append(name)
            continue
        if not decided.actions:
            print(f"{ORG}/{name}: nothing to do")
        closing = {
            int(a.issue["number"])
            for a in decided.actions
            if a.issue and a.kind.startswith("close")
        }
        urls = [
            str(i["html_url"])
            for i in repo.issues
            if is_app_issue(i) and i.get("state") == "open" and int(i["number"]) not in closing
        ]
        for action in decided.actions:
            if not in_actions:
                print(f"{ORG}/{name}: not in GitHub Actions: would {describe(action)}")
                continue
            try:
                made = act(repo, action, gh)
            except ReadError as error:
                print(
                    f"dependabot-issues: {ORG}/{name}: couldn't {describe(action)}: {error}",
                    file=sys.stderr,
                )
                failed.append(name)
                break
            print(
                f"{ORG}/{name}: {describe(action)}"
                + (f": {made['html_url']}" if made and made.get("html_url") else "")
            )
            if made and made.get("html_url"):
                urls.append(str(made["html_url"]))
        open_issues += urls
    # The board job (dependabot-issues.yml) adds each one that isn't on the board yet.
    if in_actions and (output := env.get("GITHUB_OUTPUT")):
        with Path(output).open("a", encoding="utf-8") as out:
            out.write(f"issue-urls={json.dumps(sorted(set(open_issues)))}\n")
    if failed:
        print(
            f"dependabot-issues: couldn't handle {', '.join(sorted(set(failed)))}", file=sys.stderr
        )
        return 1
    return 0


def main() -> int:
    return run(LABELS, MILESTONES, os.environ, run_gh)


if __name__ == "__main__":
    sys.exit(main())
