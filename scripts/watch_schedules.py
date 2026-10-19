"""Notices when a watched scheduled workflow in the org stops running (spec: schedule-watch; #60).

Usage: uv run scripts/watch_schedules.py [--extra-workflow troupe-run/<repository>/<file>]

GitHub turns a public repository's scheduled workflows off after 60 days without activity in it,
and then nothing runs, fails or opens an issue. For each workflow in scripts/watched-schedules.json
this reads its state and its latest run started by the schedule, and keeps one tracking issue in
the repository it runs in: opened when a workflow has stopped, commented on when what's stopped
changes, closed by a clean run (watch-website-link-check design D3, D4). It exits 1 when it found a
problem, after updating the issue, and 2 when it couldn't read something, touching no issue.

Outside GitHub Actions it only reads, and prints what it would do to the issue.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple

ROOT = Path(__file__).resolve().parent.parent
DECLARATION = ROOT / "scripts" / "watched-schedules.json"
ORG = "troupe-run"
TITLE = "Scheduled workflows stopped running"
# How the workflow's own token is named: `gh issue list` and `gh issue view` name it differently
# (fixtures/schedule-watch/README.md).
LISTED_AUTHOR = "app/github-actions"
COMMENT_AUTHOR = "github-actions"
EXTRA_MAX_AGE_DAYS = 8
MARKER = re.compile(r"<!-- schedule-watch: (.*?) -->")

REPOSITORY = re.compile(r"[A-Za-z0-9._-]+")
WORKFLOW = re.compile(r"[A-Za-z0-9._-]+\.ya?ml")
EXTRA = re.compile(r"troupe-run/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+\.ya?ml)")
FIELDS = {"repository", "workflow", "max_age_days"}


class DeclarationError(Exception):
    """The declaration, or a hand-started run's extra workflow, isn't well formed."""


class ReadError(Exception):
    """A watched workflow couldn't be read, so nothing is known about it."""


class GhResult(NamedTuple):
    code: int
    stdout: str
    stderr: str


Gh = Callable[[list[str]], GhResult]


@dataclass(frozen=True)
class Watched:
    repository: str  # inside troupe-run
    workflow: str  # the file name under .github/workflows/
    max_age_days: int

    @property
    def name(self) -> str:
        return f"{self.repository}/{self.workflow}"


@dataclass(frozen=True)
class Problem:
    repository: str
    workflow: str
    kind: str  # not-found, not-active, never-ran or too-old (design D3)
    detail: str
    fix: str


def load_declaration(text: str) -> list[Watched]:
    """Every entry, or DeclarationError naming the first one that's wrong: none is skipped."""
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as error:
        raise DeclarationError(f"the declaration isn't JSON: {error}") from None
    if not isinstance(loaded, list) or not loaded:
        raise DeclarationError("the declaration must be a non-empty list of entries")
    watched = []
    for number, entry in enumerate(loaded, start=1):
        where = f"entry {number}"
        if not isinstance(entry, dict):
            raise DeclarationError(f"{where} isn't an object")
        for field in sorted(set(entry) - FIELDS):
            raise DeclarationError(
                f"{where} has the field {field!r}, which isn't one of {sorted(FIELDS)}"
            )
        for field in sorted(FIELDS - set(entry)):
            raise DeclarationError(f"{where} has no {field!r}")
        repository, workflow, age = entry["repository"], entry["workflow"], entry["max_age_days"]
        if not isinstance(repository, str) or not REPOSITORY.fullmatch(repository):
            raise DeclarationError(f"{where}'s repository {repository!r} isn't a name in {ORG}")
        if not isinstance(workflow, str) or not WORKFLOW.fullmatch(workflow):
            raise DeclarationError(
                f"{where}'s workflow {workflow!r} isn't a .yml or .yaml file name"
            )
        if isinstance(age, bool) or not isinstance(age, int) or age < 1:
            raise DeclarationError(f"{where}'s max_age_days {age!r} isn't a positive whole number")
        watched.append(Watched(repository, workflow, age))
    return watched


def parse_extra(value: str) -> Watched | None:
    """A hand-started run's one extra workflow (design D7), or None when there isn't one."""
    if not value:
        return None
    match = EXTRA.fullmatch(value)
    if not match:
        raise DeclarationError(
            f"extra-workflow {value!r} isn't troupe-run/<repository>/<workflow file>.yml"
        )
    return Watched(match.group(1), match.group(2), EXTRA_MAX_AGE_DAYS)


def gh_json(watched: Watched, gh: Gh, path: str) -> Any:  # noqa: ANN401 (JSON)
    result = gh(["api", path])
    if result.code != 0:
        raise ReadError(f"{watched.name}: {result.stderr.strip() or f'gh exited {result.code}'}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise ReadError(f"{watched.name}: GitHub's answer isn't JSON") from None


def read(watched: Watched, gh: Gh) -> tuple[Any, Any]:
    """The workflow and its latest scheduled run's page, or (None, None) when it isn't found."""
    path = f"repos/{ORG}/{watched.repository}/actions/workflows/{watched.workflow}"
    try:
        found = gh_json(watched, gh, path)
    except ReadError as error:
        if "(HTTP 404)" in str(error):
            return None, None
        raise
    return found, gh_json(watched, gh, f"{path}/runs?event=schedule&per_page=1")


def problem_for(watched: Watched, found: Any, page: Any, now: datetime) -> Problem | None:  # noqa: ANN401
    """What's wrong with one workflow, if anything (design D3). An answer of a shape this doesn't
    know is a ReadError, never all clear."""
    enable = f"`gh workflow enable {watched.workflow} -R {ORG}/{watched.repository}`"
    if found is None:
        return Problem(
            watched.repository,
            watched.workflow,
            "not-found",
            "GitHub has no such workflow",
            "It was renamed or deleted: update `scripts/watched-schedules.json` in "
            "troupe-run/infrastructure.",
        )
    state = found.get("state") if isinstance(found, dict) else None
    if not isinstance(state, str):
        raise ReadError(f"{watched.name}: the workflow has no state")
    if state != "active":
        return Problem(
            watched.repository,
            watched.workflow,
            "not-active",
            f"its state is `{state}`",
            f"Turn it back on with {enable}.",
        )
    if not isinstance(page, dict) or not isinstance(page.get("workflow_runs"), list):
        raise ReadError(f"{watched.name}: the runs page has no workflow_runs")
    if not page["workflow_runs"]:
        return Problem(
            watched.repository,
            watched.workflow,
            "never-ran",
            "it has never run on its schedule",
            "Check its `schedule:` trigger is on its default branch.",
        )
    latest = page["workflow_runs"][0]
    if not isinstance(latest, dict) or latest.get("event") != "schedule":
        event = latest.get("event") if isinstance(latest, dict) else latest
        raise ReadError(f"{watched.name}: asked for scheduled runs, got a {event} run")
    try:
        began = datetime.strptime(latest["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (KeyError, TypeError, ValueError):
        raise ReadError(f"{watched.name}: the latest run's created_at isn't a time") from None
    if now - began > timedelta(days=watched.max_age_days):
        return Problem(
            watched.repository,
            watched.workflow,
            "too-old",
            f"it's active, but its latest scheduled run began {began:%Y-%m-%d %H:%M} UTC, more "
            f"than {watched.max_age_days} days ago",
            "Check its `schedule:` trigger and GitHub's status. Turning it off and on again "
            f"(`gh workflow disable`, then {enable}) restarts the schedule.",
        )
    return None


def fingerprint(problems: list[Problem]) -> str:
    """Which workflows have which kind of problem: ages and wording aren't in it (design D4)."""
    return ",".join(sorted(f"{p.repository}/{p.workflow}:{p.kind}" for p in problems))


def report(problems: list[Problem], run_url: str) -> str:
    lines = [f"{len(problems)} watched scheduled workflow(s) stopped running.", ""]
    for p in problems:
        lines += [f"- **{ORG}/{p.repository}** `{p.workflow}`: {p.detail}. {p.fix}"]
    lines += [
        "",
        f"Run: {run_url}",
        "",
        "This issue is kept by the schedule watch (`.github/workflows/schedules.yml` in "
        "troupe-run/infrastructure, #60). It's commented on when what's stopped changes, and "
        "closes itself after a clean run.",
        "",
        f"<!-- schedule-watch: {fingerprint(problems)} -->",
    ]
    return "\n".join(lines)


def tracking_issues(listed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Open issues with the tracking title opened by the workflow's token, oldest first."""
    found = [
        issue
        for issue in listed
        if issue.get("title") == TITLE
        and issue.get("state") == "OPEN"
        and (issue.get("author") or {}).get("login") == LISTED_AUTHOR
    ]
    return sorted(found, key=lambda issue: str(issue.get("createdAt")))


def last_fingerprint(view: dict[str, Any]) -> str | None:
    """The fingerprint in the newest of the issue's body and comments the watch posted."""
    posted = [str(view.get("body") or "")] + [
        str(comment.get("body") or "")
        for comment in view.get("comments") or []
        if (comment.get("author") or {}).get("login") == COMMENT_AUTHOR
    ]
    for body in reversed(posted):
        if match := MARKER.search(body):
            return match.group(1)
    return None


def decide(problems: list[Problem], issue: Mapping[str, Any] | None, last: str | None) -> str:
    """open, comment, close or none (design D4's table)."""
    if problems and issue is None:
        return "open"
    if problems:
        return "none" if last == fingerprint(problems) else "comment"
    return "close" if issue is not None else "none"


def run_gh(args: list[str]) -> GhResult:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    return GhResult(result.returncode, result.stdout, result.stderr)


def run(
    declaration: Path, extra: str, env: Mapping[str, str], gh: Gh, now: datetime | None = None
) -> int:
    now = now or datetime.now(UTC)
    try:
        watched = load_declaration(declaration.read_text(encoding="utf-8"))
        if more := parse_extra(extra):
            watched.append(more)
    except DeclarationError as error:
        print(f"watch: {error}. Fix it; nothing was read.", file=sys.stderr)
        return 2
    problems = []
    try:
        for each in watched:
            found, page = read(each, gh)
            problem = problem_for(each, found, page, now)
            print(f"{each.name}: {problem.detail if problem else 'running on its schedule'}")
            if problem:
                problems.append(problem)
    except ReadError as error:
        print(
            f"watch: couldn't read {error}. Nothing is known about it, so the tracking issue is "
            "left as it is; run again.",
            file=sys.stderr,
        )
        return 2

    in_actions = env.get("GITHUB_ACTIONS") == "true"
    repository = env.get("GITHUB_REPOSITORY", f"{ORG}/infrastructure")
    listed = gh(
        [
            "issue",
            "list",
            "-R",
            repository,
            "--state",
            "open",
            "--limit",
            "1000",
            "--json",
            "number,title,author,createdAt,state,url",
        ]
    )
    if listed.code != 0:
        print(
            f"watch: couldn't list {repository}'s issues: {listed.stderr.strip()}", file=sys.stderr
        )
        return 2
    issues = tracking_issues(json.loads(listed.stdout))
    if len(issues) > 1:
        others = ", ".join(f"#{issue['number']}" for issue in issues[1:])
        oldest = issues[0]["number"]
        print(f"watch: {len(issues)} open tracking issues; updating #{oldest}, not {others}")
    issue = issues[0] if issues else None
    last = None
    if issue is not None and problems:
        viewed = gh(
            ["issue", "view", str(issue["number"]), "-R", repository, "--json", "body,comments"]
        )
        if viewed.code != 0:
            print(
                f"watch: couldn't read #{issue['number']}: {viewed.stderr.strip()}", file=sys.stderr
            )
            return 2
        last = last_fingerprint(json.loads(viewed.stdout))
    action = decide(problems, issue, last)

    if not in_actions:
        if action == "none":
            print("Not in GitHub Actions: the tracking issue would be left as it is")
        else:
            target = f" #{issue['number']}" if issue else ""
            print(f"Not in GitHub Actions: would {action} the tracking issue{target}")
        return 1 if problems else 0

    run_url = f"{env.get('GITHUB_SERVER_URL')}/{repository}/actions/runs/{env.get('GITHUB_RUN_ID')}"
    issue_url = ""
    if action == "open":
        result = gh(
            [
                "issue",
                "create",
                "-R",
                repository,
                "--title",
                TITLE,
                "--label",
                "bug",
                "--body",
                report(problems, run_url),
            ]
        )
        issue_url = result.stdout.strip()
    elif action == "comment" and issue is not None:
        result = gh(
            [
                "issue",
                "comment",
                str(issue["number"]),
                "-R",
                repository,
                "--body",
                report(problems, run_url),
            ]
        )
        issue_url = str(issue["url"])
    elif action == "close" and issue is not None:
        result = gh(
            [
                "issue",
                "close",
                str(issue["number"]),
                "-R",
                repository,
                "--comment",
                f"Every watched scheduled workflow is running on its schedule: {run_url}",
            ]
        )
    else:
        result = GhResult(0, "", "")
    if result.code != 0:
        print(
            f"watch: couldn't {action} the tracking issue: {result.stderr.strip()}", file=sys.stderr
        )
        return 2
    print(f"Tracking issue: {action}{f' {issue_url}' if issue_url else ''}")
    # The board job (schedules.yml) adds the issue to the roadmap board when this is set.
    if issue_url and (output := env.get("GITHUB_OUTPUT")):
        with Path(output).open("a", encoding="utf-8") as out:
            out.write(f"issue-url={issue_url}\n")
    return 1 if problems else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--extra-workflow", default="", help="troupe-run/<repository>/<file>.yml")
    args = parser.parse_args(argv)
    return run(DECLARATION, args.extra_workflow, os.environ, run_gh)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
