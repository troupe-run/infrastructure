"""Give the troupe roadmap board's Capability options their cap: labels' descriptions.

Usage (in .github/workflows/tofu.yml):
    # GH_TOKEN: any token that can read the org's projects
    uv run --no-project scripts/board_options.py plan --out board-plan.json --summary board.md
    # GH_TOKEN: the troupe-run-board App's, with Projects: write
    uv run --no-project scripts/board_options.py apply --board-plan board-plan.json

Spec: labels ("An approved apply gives the board's options their labels' descriptions", "The board's
options are never sent without their identity"); design: board-capability-descriptions.
- OpenTofu can't manage a Projects v2 field, so this is a plan and an apply of its own, shown and
  approved with the OpenTofu plan (D1).
- `plan` reads the field and `tofu/labels/troupe.json`, and lists each option whose description
  isn't its `cap:<option>` label's. An option with no label is left alone (D4). It only reads.
- `apply` re-reads the field and refuses if it isn't the one the plan read (D3).
  `updateProjectV2Field` replaces the whole option list, and an option sent without its id loses
  every card's value for it, so it sends every option read, in order, with its id, name and colour,
  and refuses an option with no id (D2). It then reads the field back. It never creates or removes
  an option (D5), and runs on the live board only in CI (D7).

Recovery: a refused or failed `apply` leaves the field as it was, or as the read-back names; the
next plan of `main` (daily at the latest) reads it again.
"""

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ORG = "troupe-run"
BOARD = "troupe roadmap"
PROJECT = 1
FIELD = "Capability"
LABELS = ROOT / "tofu" / "labels" / "troupe.json"
VERSION = 1

FIELD_QUERY = (
    "query($org: String!, $number: Int!, $field: String!) {"
    " organization(login: $org) { projectV2(number: $number) { field(name: $field) {"
    " __typename ... on ProjectV2SingleSelectField { id options { id name color description } }"
    " } } } }"
)
UPDATE_MUTATION = (
    "mutation($field: ID!, $options: [ProjectV2SingleSelectFieldOptionInput!]) {"
    " updateProjectV2Field(input: {fieldId: $field, singleSelectOptions: $options}) {"
    " projectV2Field { ... on ProjectV2SingleSelectField { id } } } }"
)
# What gh prints when the project has no field of that name: a GraphQL NOT_FOUND, so gh exits 1.
NO_SUCH_FIELD = "Could not resolve to a Unions::ProjectV2FieldConfiguration"

Option = dict[str, str]
# A GraphQL request body ({query, variables}) -> its `data`. Injected so tests don't touch GitHub.
GraphQL = Callable[[dict[str, Any]], Any]


class BoardError(Exception):
    """A refusal: the field can't be read as expected, or moved, or GitHub said no. The message
    says which, and nothing was sent unless it says so."""


@dataclass(frozen=True)
class Change:
    """Option `name` (id `id`) has description `before`, and its label's is `after`."""

    id: str
    name: str
    before: str
    after: str


# --- reading -----------------------------------------------------------------------------------


def label_descriptions(path: Path) -> dict[str, str]:
    """Each declared cap: label's description, by its name without the prefix."""
    labels = json.loads(path.read_text(encoding="utf-8"))
    return {
        label["name"].removeprefix("cap:"): label["description"]
        for label in labels
        if label["name"].startswith("cap:")
    }


def description_changes(options: list[Option], labels: dict[str, str]) -> list[Change]:
    """Each option whose description isn't its label's, in the field's order. An option with no
    label isn't one (D4). The drift check uses this too, so it passes exactly when a plan would
    list nothing."""
    return [
        Change(
            id=option.get("id", ""),
            name=option["name"],
            before=option.get("description", ""),
            after=labels[option["name"]],
        )
        for option in options
        if option["name"] in labels and option.get("description", "") != labels[option["name"]]
    ]


def read_field(graphql: GraphQL, project: int, field: str = FIELD) -> tuple[str, list[Option]]:
    """The field's id and its options as GitHub holds them, in order."""
    request = {
        "query": FIELD_QUERY,
        "variables": {"org": ORG, "number": project, "field": field},
    }
    try:
        data = graphql(request)
    except subprocess.CalledProcessError as error:
        if NO_SUCH_FIELD in str(error.stderr):
            raise BoardError(f"project {project} has no {field!r} field") from None
        raise
    found = (((data or {}).get("organization") or {}).get("projectV2") or {}).get("field")
    if not found:
        raise BoardError(f"project {project} has no {field!r} field, or it can't be read")
    if found.get("__typename") != "ProjectV2SingleSelectField":
        raise BoardError(
            f"project {project}'s {field!r} field is a {found.get('__typename')}, "
            "not a single select"
        )
    options = [
        {key: option.get(key) or "" for key in ("id", "name", "color", "description")}
        for option in found["options"]
    ]
    return found["id"], options


# --- planning ----------------------------------------------------------------------------------


def make_plan(graphql: GraphQL, project: int, labels: dict[str, str]) -> dict[str, Any]:
    field_id, options = read_field(graphql, project)
    return {
        "version": VERSION,
        "project": project,
        "field": FIELD,
        "field_id": field_id,
        "before": options,
        "changes": [asdict(change) for change in description_changes(options, labels)],
    }


def cell(text: str) -> str:
    """A Markdown table cell: pipes escaped, newlines flattened, empty shown as such."""
    return text.replace("|", "\\|").replace("\n", " ") if text else "*(none)*"


def summary(plan: dict[str, Any]) -> str:
    """Markdown for the run summary, under the OpenTofu plan."""
    changes = plan["changes"]
    title = f"#### The {BOARD} board's {plan['field']} descriptions"
    if not changes:
        return f"{title}\n\nNone to set: every option with a label has its description.\n"
    lines = [
        title,
        "",
        f"{len(changes)} to set from `tofu/labels/troupe.json` after the apply "
        "(spec: labels). Each option keeps its id, name and colour.",
        "",
        "| Option | Now | After |",
        "| --- | --- | --- |",
    ]
    lines += [
        f"| `{change['name']}` | {cell(change['before'])} | {cell(change['after'])} |"
        for change in changes
    ]
    return "\n".join(lines) + "\n"


# --- applying ----------------------------------------------------------------------------------


def field_differences(before: list[Option], now: list[Option]) -> list[str]:
    """How the field read now differs from the one the plan read, option by option."""
    was = {option["id"]: option for option in before}
    found: list[str] = []
    for option in now:
        old = was.get(option["id"])
        if old is None:
            found.append(f"{option['name']!r} was added")
            continue
        for key in ("name", "color", "description"):
            if old[key] != option[key]:
                found.append(f"{old['name']!r} {key} was {old[key]!r}, now {option[key]!r}")
    ids = {option["id"] for option in now}
    found += [f"{option['name']!r} was removed" for option in before if option["id"] not in ids]
    if not found and [o["id"] for o in before] != [o["id"] for o in now]:
        found.append("the options were reordered")
    return found


def options_to_send(options: list[Option], changes: list[dict[str, str]]) -> list[Option]:
    """Every option, in order, with its id, name and colour, and the planned descriptions. Refuses
    an option with no id: sent without one, it would lose every card's value for it (D2)."""
    for option in options:
        if not option.get("id"):
            raise BoardError(
                f"option {option.get('name')!r} has no id; sending it without one would clear "
                "every card's value for it, so nothing was sent"
            )
    after = {change["id"]: change["after"] for change in changes}
    return [
        {
            "id": option["id"],
            "name": option["name"],
            "color": option["color"],
            "description": after.get(option["id"], option["description"]),
        }
        for option in options
    ]


def apply_plan(
    plan: dict[str, Any], graphql: GraphQL, *, in_ci: bool, out: Callable[[str], None]
) -> int:
    """Set the planned descriptions. Returns the exit code."""
    project = plan["project"]
    if project == PROJECT and not in_ci:
        raise BoardError(
            f"the {BOARD} board's descriptions are set by the tofu workflow's board job after an "
            "approved apply, not by a local run (design D7); nothing was sent"
        )
    if not plan["changes"]:
        out("board_options: no descriptions to set.")
        return 0
    field_id, now = read_field(graphql, project, plan["field"])
    moved = field_differences(plan["before"], now)
    if field_id != plan["field_id"]:
        moved.insert(0, f"the field's id is {field_id!r}, planned {plan['field_id']!r}")
    if moved:
        raise BoardError(
            f"the {plan['field']} field changed since the plan ({'; '.join(moved)}); nothing was "
            "sent. The next plan reads it again"
        )
    sent = options_to_send(now, plan["changes"])
    graphql({"query": UPDATE_MUTATION, "variables": {"field": field_id, "options": sent}})
    _, back = read_field(graphql, project, plan["field"])
    if back != sent:
        raise BoardError(
            f"the {plan['field']} field read back after the update isn't what was sent "
            f"({'; '.join(field_differences(sent, back)) or 'it differs'})"
        )
    out(f"board_options: set {len(plan['changes'])} description(s) on project {project}.")
    return 0


# --- the command line --------------------------------------------------------------------------


def graphql_with_gh(request: dict[str, Any]) -> Any:  # noqa: ANN401 (JSON)
    """The request's `data`, through `gh api graphql` with GH_TOKEN or gh's login."""
    result = subprocess.run(
        ["gh", "api", "graphql", "--input", "-"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, ["gh", "api", "graphql"], result.stdout, result.stderr
        )
    body = json.loads(result.stdout)
    if body.get("errors"):
        raise BoardError(f"GitHub refused the request: {body['errors']}")
    return body.get("data")


def read_plan(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    keys = {"version", "project", "field", "field_id", "before", "changes"}
    if not isinstance(data, dict) or data.get("version") != VERSION or not keys <= data.keys():
        raise BoardError(f"{path} isn't a version {VERSION} board plan")
    return data


def main(argv: list[str], graphql: GraphQL = graphql_with_gh) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="list the descriptions to set (only reads)")
    plan.add_argument("--out", required=True, type=Path, help="where to write the board plan")
    plan.add_argument("--summary", required=True, type=Path, help="where to write its Markdown")
    plan.add_argument("--project", default=PROJECT, type=int, help=f"default: {PROJECT}")
    plan.add_argument(
        "--labels", default=LABELS, type=Path, help="default: tofu/labels/troupe.json"
    )
    apply = sub.add_parser("apply", help="set the descriptions a board plan lists")
    apply.add_argument("--board-plan", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            made = make_plan(graphql, args.project, label_descriptions(args.labels))
            args.out.write_text(json.dumps(made, indent=2) + "\n", encoding="utf-8")
            args.summary.write_text(summary(made), encoding="utf-8")
            print(summary(made), end="")
            return 0
        in_ci = os.environ.get("GITHUB_ACTIONS") == "true"
        return apply_plan(read_plan(args.board_plan), graphql, in_ci=in_ci, out=print)
    except BoardError as error:
        print(f"board_options: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
