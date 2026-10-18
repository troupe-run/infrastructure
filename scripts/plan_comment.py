"""Show a plan within a size limit: whole when it fits, otherwise cut on purpose, never silently.

Usage (in .github/workflows/tofu.yml):
    uv run --no-project scripts/plan_comment.py --target comment --head head.md \
        --plan plan.txt --plan-url "$PLAN_URL" --out comment.md

Spec: ci-apply ("A plan too long to show is cut on purpose, never silently"); design:
truncate-long-plans D1-D4. `--head` is the body the workflow writes before the plan; this adds the
plan and writes the whole body, so it can measure all of it. A plan that fits is shown as the
workflow showed it before. One that doesn't is cut at a line, below the limit, after a list of
every resource change and the `Plan:` line, with a note saying how much is shown and a link to the
full plan. If that list alone doesn't fit, it's an error, and nothing is written.
"""

import argparse
import re
import sys
from pathlib import Path

# GitHub allows 65,536 characters in a comment and 1 MiB in a step's summary. Bytes are never fewer
# than characters, so a byte limit under each holds whatever the plan contains (design D2).
COMMENT_LIMIT = 65_000
SUMMARY_LIMIT = 1_000_000
LIMITS = {"comment": COMMENT_LIMIT, "summary": SUMMARY_LIMIT}

# A resource's header in `tofu show -no-color`: indented by exactly two spaces (design D3).
RESOURCE = re.compile(r"  # \S.* (will be|must be|has moved to) ")


class TooLongError(ValueError):
    """The resource list and `Plan:` line alone are over the limit."""


def size(text: str) -> int:
    return len(text.encode("utf-8"))


def resource_lines(plan: str) -> list[str]:
    """Each resource change's header, in plan order, then the first `Plan:` line."""
    lines = plan.splitlines()
    found = [line for line in lines if RESOURCE.match(line)]
    found += [line for line in lines if line.startswith("Plan:")][:1]
    return found


def fence(plan: str) -> str:
    """Longer than any run of backticks in the plan, so the plan can't close it (design D4)."""
    longest = max((len(run) for run in re.findall(r"`+", plan)), default=0)
    return "`" * max(3, longest + 1)


def block(text: str, f: str, target: str, summary: str) -> str:
    """The plan in a code block: in <details> for a comment, bare for a run summary."""
    code = f"{f}\n{text}{f}\n"
    if target == "comment":
        return f"<details><summary>{summary}</summary>\n\n{code}</details>\n"
    return code


def note(lines: int, total_lines: int, shown: int, total: int, url: str) -> str:
    return (
        f"\nTruncated: showing the first {lines:,} of {total_lines:,} lines "
        f"({shown:,} of {total:,} bytes). The full plan: [plan.txt]({url}).\n"
    )


def render(head: str, plan: str, plan_url: str, target: str, limit: int | None = None) -> str:
    """The whole body: `head`, then the plan, within the target's limit (or `limit`)."""
    limit = LIMITS[target] if limit is None else limit
    if plan and not plan.endswith("\n"):
        plan += "\n"
    f = fence(plan)
    whole = head + block(plan, f, target, "Full plan")
    if size(whole) <= limit:
        return whole

    listed = resource_lines(plan)
    count = sum(1 for line in listed if RESOURCE.match(line))
    listing = "".join(f"{line}\n" for line in listed)
    before = f"{head}**Resource changes** ({count}):\n\n{f}\n{listing}{f}\n\n"
    lines = plan.splitlines(keepends=True)
    total = size(plan)
    # A count shown never has more digits than its total, so this reserves enough for the note.
    fixed = size(before) + size(block("", f, target, "Plan (truncated)"))
    fixed += size(note(len(lines), len(lines), total, total, plan_url))
    room = limit - fixed
    if room < 0:
        raise TooLongError(
            f"the resource list and Plan: line take {fixed:,} bytes, over the {target} limit of "
            f"{limit:,} bytes. Fix: plan the change locally, or split it into smaller changes."
        )
    shown: list[str] = []
    used = 0
    for line in lines:
        if used + size(line) > room:
            break
        shown.append(line)
        used += size(line)
    text = "".join(shown)
    return (
        before
        + block(text, f, target, "Plan (truncated)")
        + note(len(shown), len(lines), used, total, plan_url)
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", choices=sorted(LIMITS), required=True)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-url", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.plan_url.startswith("https://"):
        print(
            f"plan_comment.py: --plan-url must be an https:// URL, got {args.plan_url!r}. "
            "Fix: pass the upload step's artifact-url output.",
            file=sys.stderr,
        )
        return 2
    head = args.head.read_text(encoding="utf-8")
    plan = args.plan.read_text(encoding="utf-8")
    try:
        body = render(head, plan, args.plan_url, args.target)
    except TooLongError as error:
        print(f"plan_comment.py: {error}", file=sys.stderr)
        return 2
    args.out.write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
