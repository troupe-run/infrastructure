"""The board's Capability options get their labels' descriptions (spec: labels;
board-capability-descriptions design).

Every GitHub call is injected: these tests never touch the network.
"""

import copy
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

import board_options
from board_options import BoardError, Change

FIELD_ID = "PVTSSF_field"
LABELS = {"runs": "Running a play", "cues": "Open requests addressed to a role"}


def option(id: str, name: str, description: str = "", color: str = "GRAY") -> dict[str, str]:
    return {"id": id, "name": name, "color": color, "description": description}


OPTIONS = [
    option("a1", "runs"),
    option("b2", "cues", "Open requests addressed to a role"),
    option("c3", "lifecycle", "kept as it is", color="RED"),
]


def field_data(options: list[dict[str, str]], typename: str = "ProjectV2SingleSelectField") -> Any:  # noqa: ANN401
    field: dict[str, Any] = {"__typename": typename}
    if typename == "ProjectV2SingleSelectField":
        field |= {"id": FIELD_ID, "options": options}
    return {"organization": {"projectV2": {"field": field}}}


class FakeBoard:
    """A field GitHub holds, read by the field query and replaced by the mutation."""

    def __init__(self, options: list[dict[str, str]], *, after_send: Any = None) -> None:  # noqa: ANN401
        self.options = copy.deepcopy(options)
        self.sent: list[list[dict[str, str]]] = []
        self.after_send = after_send

    def __call__(self, request: dict[str, Any]) -> Any:  # noqa: ANN401
        if request["query"] == board_options.FIELD_QUERY:
            return field_data(self.options)
        assert request["query"] == board_options.UPDATE_MUTATION
        assert request["variables"]["field"] == FIELD_ID
        self.sent.append(request["variables"]["options"])
        self.options = copy.deepcopy(self.after_send or request["variables"]["options"])
        return {"updateProjectV2Field": {"projectV2Field": {"id": FIELD_ID}}}


def plan_for(options: list[dict[str, str]], project: int = 7) -> dict[str, Any]:
    return board_options.make_plan(FakeBoard(options), project, LABELS)


def apply(plan: dict[str, Any], board: FakeBoard, *, in_ci: bool = False) -> int:
    return board_options.apply_plan(plan, board, in_ci=in_ci, out=lambda _: None)


# --- planning ----------------------------------------------------------------------------------


def test_an_option_whose_description_differs_from_its_label_s_is_listed_with_from_and_to() -> None:
    assert board_options.description_changes(OPTIONS, LABELS) == [
        Change(id="a1", name="runs", before="", after="Running a play")
    ]


def test_a_matching_option_and_an_option_with_no_label_aren_t_listed() -> None:
    names = [change.name for change in board_options.description_changes(OPTIONS, LABELS)]
    assert "cues" not in names
    assert "lifecycle" not in names


def test_the_plan_records_the_field_as_read_and_its_changes() -> None:
    plan = plan_for(OPTIONS)
    assert plan["field_id"] == FIELD_ID
    assert plan["before"] == OPTIONS
    assert plan["changes"] == [
        {"id": "a1", "name": "runs", "before": "", "after": "Running a play"}
    ]


def test_a_plan_with_no_changes_writes_empty_changes_and_a_summary_saying_so(
    tmp_path: Path,
) -> None:
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps([{"name": "cap:cues", "description": LABELS["cues"]}]))
    out, summary = tmp_path / "plan.json", tmp_path / "board.md"
    argv = ["plan", "--out", str(out), "--summary", str(summary), "--labels", str(labels)]
    assert board_options.main(argv, FakeBoard(OPTIONS)) == 0
    assert json.loads(out.read_text())["changes"] == []
    assert "None to set" in summary.read_text()


def test_the_summary_names_each_option_with_its_description_now_and_after() -> None:
    text = board_options.summary(plan_for(OPTIONS))
    assert "| `runs` | *(none)* | Running a play |" in text
    assert "1 to set" in text


def test_a_pipe_in_a_description_doesn_t_split_the_summary_s_table() -> None:
    assert board_options.cell("a | b") == "a \\| b"


def test_only_cap_labels_are_read_and_without_the_prefix(tmp_path: Path) -> None:
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps([{"name": "cap:runs", "description": "R"}, {"name": "bug", "description": "B"}])
    )
    assert board_options.label_descriptions(labels) == {"runs": "R"}


@pytest.mark.labels
def test_the_declared_labels_file_reads() -> None:
    assert "infrastructure" in board_options.label_descriptions(board_options.LABELS)


def test_a_missing_field_refuses_naming_it() -> None:
    def missing(_: dict[str, Any]) -> Any:  # noqa: ANN401
        stderr = "gh: Could not resolve to a Unions::ProjectV2FieldConfiguration with the name X"
        raise subprocess.CalledProcessError(1, ["gh"], "", stderr)

    with pytest.raises(BoardError, match="project 7 has no 'Capability' field"):
        board_options.make_plan(missing, 7, LABELS)


def test_a_field_that_isn_t_a_single_select_refuses_naming_its_type() -> None:
    with pytest.raises(BoardError, match="is a ProjectV2Field, not a single select"):
        board_options.make_plan(lambda _: field_data([], "ProjectV2Field"), 7, LABELS)


# --- applying ----------------------------------------------------------------------------------


def test_apply_sends_every_option_in_order_changing_only_the_planned_descriptions() -> None:
    board = FakeBoard(OPTIONS)
    assert apply(plan_for(OPTIONS), board) == 0
    assert board.sent == [
        [
            option("a1", "runs", "Running a play"),
            option("b2", "cues", "Open requests addressed to a role"),
            option("c3", "lifecycle", "kept as it is", color="RED"),
        ]
    ]


@pytest.mark.parametrize("missing", [None, ""])
def test_an_option_with_no_id_refuses_naming_it_and_nothing_is_sent(missing: str | None) -> None:
    options = copy.deepcopy(OPTIONS)
    if missing is None:
        del options[1]["id"]
    else:
        options[1]["id"] = missing
    with pytest.raises(BoardError, match="option 'cues' has no id"):
        board_options.options_to_send(options, [])

    # Through apply too: a field read with an id-less option is never sent.
    board = FakeBoard(options)
    plan = plan_for(options)
    with pytest.raises(BoardError, match="option 'cues' has no id"):
        apply(plan, board)
    assert board.sent == []


def edited(change: str) -> list[dict[str, str]]:
    options = copy.deepcopy(OPTIONS)
    if change == "added":
        options.append(option("d4", "effects"))
    elif change == "removed":
        options.pop()
    elif change == "renamed":
        options[2]["name"] = "lifecycles"
    elif change == "recoloured":
        options[2]["color"] = "BLUE"
    elif change == "reordered":
        options.reverse()
    elif change == "described":
        options[0]["description"] = "typed by hand"
    return options


@pytest.mark.parametrize(
    ("change", "named"),
    [
        ("added", "'effects' was added"),
        ("removed", "'lifecycle' was removed"),
        ("renamed", "'lifecycle' name was 'lifecycle', now 'lifecycles'"),
        ("recoloured", "'lifecycle' color was 'RED', now 'BLUE'"),
        ("reordered", "the options were reordered"),
        ("described", "'runs' description was '', now 'typed by hand'"),
    ],
)
def test_a_field_changed_since_the_plan_refuses_naming_the_change_and_nothing_is_sent(
    change: str, named: str
) -> None:
    plan = plan_for(OPTIONS)
    board = FakeBoard(edited(change))
    with pytest.raises(BoardError, match="changed since the plan") as refused:
        apply(plan, board)
    assert named in str(refused.value)
    assert board.sent == []


def test_a_read_back_that_differs_from_what_was_sent_fails() -> None:
    board = FakeBoard(OPTIONS, after_send=[option("a1", "runs"), *OPTIONS[1:]])
    with pytest.raises(BoardError, match="read back after the update isn't what was sent"):
        apply(plan_for(OPTIONS), board)
    assert len(board.sent) == 1


def test_apply_on_the_live_board_refuses_outside_ci_and_sends_nothing() -> None:
    board = FakeBoard(OPTIONS)
    plan = plan_for(OPTIONS, project=board_options.PROJECT)
    with pytest.raises(BoardError, match="not by a local run"):
        apply(plan, board)
    assert board.sent == []
    assert apply(plan, board, in_ci=True) == 0
    assert len(board.sent) == 1


def test_apply_with_no_changes_sends_nothing() -> None:
    options = [option("b2", "cues", LABELS["cues"])]
    board = FakeBoard(options)
    assert apply(plan_for(options), board) == 0
    assert board.sent == []


def test_a_file_that_isn_t_a_board_plan_refuses(tmp_path: Path) -> None:
    path = tmp_path / "plan.json"
    path.write_text(json.dumps({"version": 1, "entries": []}))
    with pytest.raises(BoardError, match="isn't a version 1 board plan"):
        board_options.read_plan(path)


def test_main_reports_a_refusal_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan_for(OPTIONS, project=board_options.PROJECT)))
    assert board_options.main(["apply", "--board-plan", str(path)], FakeBoard(OPTIONS)) == 1
    assert "board_options: " in capsys.readouterr().err


# --- a board that can't be read (design D9) ----------------------------------------------------


def unreadable(_: dict[str, Any]) -> Any:  # noqa: ANN401
    raise subprocess.CalledProcessError(1, ["gh"], "", "gh: Resource not accessible by integration")


def plan_argv(tmp_path: Path, *extra: str) -> list[str]:
    out, summary = tmp_path / "plan.json", tmp_path / "board.md"
    labels = tmp_path / "labels.json"
    if not labels.exists():
        labels.write_text(json.dumps([{"name": "cap:runs", "description": LABELS["runs"]}]))
    return ["plan", "--out", str(out), "--summary", str(summary), "--labels", str(labels), *extra]


def test_in_ci_a_board_that_can_t_be_read_is_reported_and_writes_no_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stale = tmp_path / "plan.json"
    stale.write_text("{}")
    assert board_options.main(plan_argv(tmp_path, "--ci"), unreadable) == 0
    assert not stale.exists()
    summary = (tmp_path / "board.md").read_text()
    assert "Couldn't be read, so none are planned" in summary
    assert "Resource not accessible by integration" in summary
    printed = capsys.readouterr().out
    assert printed.startswith("::error title=board descriptions::couldn't read the troupe roadmap")


def test_outside_ci_a_board_that_can_t_be_read_exits_1_naming_why(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert board_options.main(plan_argv(tmp_path), unreadable) == 1
    assert "Resource not accessible by integration" in capsys.readouterr().err
    assert not (tmp_path / "plan.json").exists()


def test_in_ci_a_broken_labels_file_is_still_an_error(tmp_path: Path) -> None:
    labels = tmp_path / "labels.json"
    labels.write_text("not json")
    with pytest.raises(json.JSONDecodeError):
        board_options.main(plan_argv(tmp_path, "--ci", "--labels", str(labels)), FakeBoard(OPTIONS))


def test_an_annotation_can_t_be_split_by_a_newline_in_the_reason() -> None:
    assert board_options.annotation("a\nb") == "::error title=board descriptions::a%0Ab"
