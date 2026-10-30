"""List the open issues with no milestone when a plan closes a milestone.

Usage (in .github/workflows/tofu.yml):
    tofu show -json pr.tfplan > plan.json
    uv run --no-project scripts/milestone_review.py --plan-json plan.json --summary review.md

Spec: milestones ("A plan that closes a milestone lists the open issues with no milestone", "The
list of issues with no milestone is never silently short"); design: needed-for-milestones D4. When
a release closes, every open issue with no milestone needs an outcome (the org's CONTRIBUTING.md,
"Milestones"). The plan says whether the apply closes one: a milestone whose state goes from open to
closed. Then this reads each milestone repository's open issues with no milestone, through
`gh api`, and writes a Markdown section for the posted plan. A plan that closes none writes an
empty file and reads nothing. A repository it can't read fails the step, and nothing is written,
so the list is never shown short. It only lists: it never fails on what it finds.
"""

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

ROOT = Path(__file__).resolve().parent.parent
MILESTONES = ROOT / "tofu" / "milestones.json"
ORG = "troupe-run"
RESOURCE = "github_repository_milestone"
GUIDE = "https://github.com/troupe-run/.github/blob/main/CONTRIBUTING.md#milestones"


class GhResult(NamedTuple):
    code: int
    stdout: str
    stderr: str


# gh's arguments, and what to send on its stdin (never anything: this only reads).
Gh = Callable[[list[str], str | None], GhResult]


class PlanError(Exception):
    """The plan's milestone changes can't be read, so whether one closes isn't known."""


class ReadError(Exception):
    """A repository couldn't be read, so its list would be short."""


def repositories(declared: dict[str, Any]) -> list[str]:
    """The milestone repositories, in the declaration's order."""
    listed = declared.get("repositories")
    if not isinstance(listed, list) or not all(isinstance(r, str) for r in listed):
        raise PlanError("tofu/milestones.json has no repositories list")
    return list(listed)


def milestone_changes(plan: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    """(address, title, state before, state after) for each milestone in the plan.

    Every plan lists each milestone, unchanged ones as no-op, so a change this can't read is an
    error, never taken as "not closing"."""
    found = []
    for each in plan.get("resource_changes") or []:
        if each.get("type") != RESOURCE:
            continue
        address = str(each.get("address"))
        change = each.get("change") or {}
        before, after = change.get("before"), change.get("after")
        if before is None or after is None:
            continue  # created or destroyed, so not a close
        if not isinstance(before, dict) or not isinstance(after, dict):
            raise PlanError(f"{address}: the plan's before and after aren't objects")
        states = before.get("state"), after.get("state")
        title = after.get("title")
        if not all(isinstance(s, str) for s in states) or not isinstance(title, str):
            raise PlanError(f"{address}: the plan gives no state or title before and after")
        found.append((address, title, str(states[0]), str(states[1])))
    return found


def closing(changes: list[tuple[str, str, str, str]]) -> list[str]:
    """The titles that close, once each, in version order."""
    titles = {title for _, title, before, after in changes if (before, after) == ("open", "closed")}
    return sorted(titles, key=lambda t: [int(p) if p.isdigit() else 0 for p in t.split(".")])


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


def unmilestoned(repo: str, gh: Gh) -> list[dict[str, Any]] | None:
    """The repository's open issues with no milestone, or None when its issues are off."""
    about = gh_json(gh, f"repos/{ORG}/{repo}")
    if not isinstance(about, dict):
        raise ReadError(f"repos/{ORG}/{repo}: GitHub's answer isn't an object")
    if about.get("has_issues") is False:
        return None
    listed = gh_json(
        gh, f"repos/{ORG}/{repo}/issues?milestone=none&state=open&per_page=100", paginate=True
    )
    found = []
    for each in listed:
        if not isinstance(each, dict):
            raise ReadError(f"{ORG}/{repo}: an issue in GitHub's answer isn't an object")
        if "pull_request" in each:
            continue  # the issues API lists pull requests too
        if not isinstance(each.get("number"), int) or not isinstance(each.get("html_url"), str):
            raise ReadError(f"{ORG}/{repo}: an issue has no number or link")
        found.append(each)
    return sorted(found, key=lambda i: int(i["number"]))


def code_span(text: str) -> str:
    """Text as a code span, so a title's markup, mentions and references stay text."""
    text = " ".join(text.split())
    fence = "`"
    while fence in text:
        fence += "`"
    return f"{fence} {text} {fence}"


def section(titles: list[str], found: dict[str, list[dict[str, Any]] | None]) -> str:
    total = sum(len(issues) for issues in found.values() if issues is not None)
    named = " and ".join(titles)
    lines = [
        f"**Issues with no milestone.** This plan closes {named}. Before it merges, give each of "
        f"the {total} open issues with no milestone an outcome: move it into a milestone, label it "
        f"`parked` with a reason to come back, or close it as not planned "
        f"([contributing guide]({GUIDE})).",
        "",
    ]
    for repo, issues in found.items():
        if issues is None:
            lines.append(f"- `{repo}`: left out, its issues are off")
        elif not issues:
            lines.append(f"- {repo}: none")
        else:
            lines.append(f"- {repo}: {len(issues)}")
            lines += [
                f"  - [#{i['number']}]({i['html_url']}) {code_span(str(i.get('title') or ''))}"
                for i in issues
            ]
    return "\n".join(lines) + "\n"


def run_gh(args: list[str], stdin: str | None) -> GhResult:
    result = subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True, check=False)
    return GhResult(result.returncode, result.stdout, result.stderr)


def main(argv: list[str], gh: Gh = run_gh) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan-json", type=Path, required=True, help="`tofu show -json` output")
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--milestones", type=Path, default=MILESTONES)
    args = parser.parse_args(argv)
    try:
        changes = milestone_changes(json.loads(args.plan_json.read_text(encoding="utf-8")))
        names = repositories(json.loads(args.milestones.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, PlanError) as error:
        print(f"milestone_review.py: {error}", file=sys.stderr)
        return 2
    titles = closing(changes)
    if not titles:
        print(f"milestone_review.py: {len(changes)} milestone changes, none closes a milestone")
        args.summary.write_text("", encoding="utf-8")
        return 0
    found: dict[str, list[dict[str, Any]] | None] = {}
    for repo in names:
        try:
            found[repo] = unmilestoned(repo, gh)
        except ReadError as error:
            print(
                f"milestone_review.py: couldn't read {ORG}/{repo}'s issues, so no list is shown: "
                f"{error}",
                file=sys.stderr,
            )
            return 1
    print(
        f"milestone_review.py: {' and '.join(titles)} closes; listing the issues with no milestone"
    )
    args.summary.write_text(section(titles, found), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
