"""The out-of-band drift checks (spec: org-settings): report differences, never write."""

import json
from pathlib import Path
from typing import Any

import pytest

import oob

TYPES = [
    {"name": "Task", "description": "Work", "color": "yellow", "is_enabled": True},
    {"name": "Bug", "description": "Broken", "color": "red", "is_enabled": True},
]
PROJECTS = [{"number": 1, "title": "roadmap", "public": True, "closed": False}]


@pytest.fixture
def oob_dir(tmp_path: Path) -> Path:
    (tmp_path / "issue-types.json").write_text(json.dumps(TYPES))
    (tmp_path / "projects.json").write_text(json.dumps(PROJECTS))
    return tmp_path


def fake_github(types: list[Any], projects: list[Any], calls: list[list[str]]) -> oob.Fetch:
    def fetch(args: list[str]) -> Any:  # noqa: ANN401 (JSON)
        calls.append(args)
        return types if "issue-types" in args[1] else projects

    return fetch


def test_matching_declarations_report_nothing(oob_dir: Path) -> None:
    assert oob.run(fake_github(TYPES, PROJECTS, []), oob_dir) == []


def test_an_issue_type_added_on_github_is_reported(oob_dir: Path) -> None:
    extra = [*TYPES, {"name": "Spike", "description": "", "color": "gray", "is_enabled": True}]
    found = oob.run(fake_github(extra, PROJECTS, []), oob_dir)
    assert found == ["issue types: 'Spike' is on GitHub but not declared"]


def test_a_declared_issue_type_missing_on_github_is_reported(oob_dir: Path) -> None:
    found = oob.run(fake_github(TYPES[:1], PROJECTS, []), oob_dir)
    assert found == ["issue types: 'Bug' is declared but missing on GitHub"]


def test_a_changed_field_is_reported_with_both_values(oob_dir: Path) -> None:
    private = [{**PROJECTS[0], "public": False}]
    found = oob.run(fake_github(TYPES, private, []), oob_dir)
    assert found == ["projects: 1 public is False on GitHub, declared True"]


def test_main_exits_non_zero_on_a_difference(
    oob_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(oob, "OOB", oob_dir)
    monkeypatch.setattr(oob, "gh", fake_github(TYPES[:1], PROJECTS, []))
    assert oob.main() == 1
    assert "1 difference(s)" in capsys.readouterr().out


def test_main_exits_zero_when_nothing_differs(
    oob_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(oob, "OOB", oob_dir)
    monkeypatch.setattr(oob, "gh", fake_github(TYPES, PROJECTS, []))
    assert oob.main() == 0


def test_every_github_call_is_a_read() -> None:
    """REST calls carry no method or body flags; the GraphQL call is a query, not a mutation."""
    write_flags = {"-X", "--method", "-F", "--field", "--input", "-H"}
    for check in oob.CHECKS:
        args = check.gh_args
        assert args[0] == "api"
        assert not write_flags & set(args), check.name
        fields = [args[i + 1] for i, a in enumerate(args) if a in {"-f", "--raw-field"}]
        if args[1] == "graphql":
            assert all(f.startswith("query={") for f in fields), check.name
        else:
            assert fields == [], check.name
