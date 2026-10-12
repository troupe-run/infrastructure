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
SETTINGS = [{"name": "two_factor_requirement_enabled", "value": False}]
APPS = [
    {"app_slug": "dco", "repository_selection": "selected", "permissions": {"checks": "write"}},
]
PROFILE = [{"path": "CONTRIBUTING.md"}, {"path": "profile/README.md"}]
CAP_LABELS = [
    {"name": "cap:cli", "color": "1D76DB", "description": "Capability: cli"},
    {"name": "cap:cues", "color": "1D76DB", "description": "Capability: cues"},
]
SPECS = ["cli"]


@pytest.fixture
def oob_dir(tmp_path: Path) -> Path:
    (tmp_path / "issue-types.json").write_text(json.dumps(TYPES))
    (tmp_path / "projects.json").write_text(json.dumps(PROJECTS))
    (tmp_path / "org-settings.json").write_text(json.dumps(SETTINGS))
    (tmp_path / "app-installations.json").write_text(json.dumps(APPS))
    for f in PROFILE:
        source = tmp_path / "org-profile" / f["path"]
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("x")
    labels = tmp_path / "tofu" / "labels" / "troupe.json"
    labels.parent.mkdir(parents=True)
    labels.write_text(json.dumps(CAP_LABELS))
    return tmp_path


def fake_github(
    types: list[Any],
    projects: list[Any],
    calls: list[list[str]],
    settings: list[Any] = SETTINGS,
    profile: list[Any] = PROFILE,
    apps: list[Any] = APPS,
    specs: list[str] = SPECS,
) -> oob.Fetch:
    def fetch(args: list[str]) -> Any:  # noqa: ANN401 (JSON)
        calls.append(args)
        if args[1].endswith("/contents/openspec/specs"):
            return specs
        if args[1].endswith("/installations"):
            return apps
        if "git/trees" in args[1]:
            return profile
        if "issue-types" in args[1]:
            return types
        return projects if args[1] == "graphql" else settings

    return fetch


def RUN(fetch: oob.Fetch, oob_dir: Path) -> list[str]:  # noqa: N802 (reads as the call under test)
    """oob.run with the fixture directory as both the oob/ and the repo root."""
    return oob.run(fetch, oob_dir, root=oob_dir)


def test_matching_declarations_report_nothing(oob_dir: Path) -> None:
    assert RUN(fake_github(TYPES, PROJECTS, []), oob_dir) == []


def test_an_issue_type_added_on_github_is_reported(oob_dir: Path) -> None:
    extra = [*TYPES, {"name": "Spike", "description": "", "color": "gray", "is_enabled": True}]
    found = RUN(fake_github(extra, PROJECTS, []), oob_dir)
    assert found == ["issue types: 'Spike' is on GitHub but not declared"]


def test_a_declared_issue_type_missing_on_github_is_reported(oob_dir: Path) -> None:
    found = RUN(fake_github(TYPES[:1], PROJECTS, []), oob_dir)
    assert found == ["issue types: 'Bug' is declared but missing on GitHub"]


def test_a_changed_field_is_reported_with_both_values(oob_dir: Path) -> None:
    private = [{**PROJECTS[0], "public": False}]
    found = RUN(fake_github(TYPES, private, []), oob_dir)
    assert found == ["projects: 1 public is False on GitHub, declared True"]


def test_two_factor_turned_on_by_hand_is_reported(oob_dir: Path) -> None:
    on = [{"name": "two_factor_requirement_enabled", "value": True}]
    found = RUN(fake_github(TYPES, PROJECTS, [], settings=on), oob_dir)
    assert found == [
        "org settings: 'two_factor_requirement_enabled' value is True on GitHub, declared False"
    ]


def test_a_file_in_dot_github_with_no_source_is_reported(oob_dir: Path) -> None:
    extra = [*PROFILE, {"path": "FUNDING.yml"}]
    found = RUN(fake_github(TYPES, PROJECTS, [], profile=extra), oob_dir)
    assert found == [".github files: 'FUNDING.yml' is on GitHub but not declared"]


def test_a_source_missing_from_dot_github_is_reported(oob_dir: Path) -> None:
    found = RUN(fake_github(TYPES, PROJECTS, [], profile=PROFILE[:1]), oob_dir)
    assert found == [".github files: 'profile/README.md' is declared but missing on GitHub"]


def test_an_app_gaining_a_permission_is_reported(oob_dir: Path) -> None:
    wider = [{**APPS[0], "permissions": {"checks": "write", "workflows": "write"}}]
    found = RUN(fake_github(TYPES, PROJECTS, [], apps=wider), oob_dir)
    assert found == [
        "App installations: 'dco' permissions is {'checks': 'write', 'workflows': 'write'} "
        "on GitHub, declared {'checks': 'write'}"
    ]


def test_an_app_installed_on_all_repos_is_reported(oob_dir: Path) -> None:
    everywhere = [{**APPS[0], "repository_selection": "all"}]
    found = RUN(fake_github(TYPES, PROJECTS, [], apps=everywhere), oob_dir)
    assert found == [
        "App installations: 'dco' repository_selection is 'all' on GitHub, declared 'selected'"
    ]


def test_a_troupe_spec_with_no_cap_label_is_reported(oob_dir: Path) -> None:
    found = RUN(fake_github(TYPES, PROJECTS, [], specs=["cli", "artifact-store"]), oob_dir)
    assert found == [
        "troupe specs: 'artifact-store' has no cap:artifact-store label; "
        "add it to tofu/labels/troupe.json by pull request"
    ]


def test_a_cap_label_ahead_of_its_spec_is_not_reported(oob_dir: Path) -> None:
    """cap:cues is declared and troupe has no cues spec: a label can come before its spec."""
    assert RUN(fake_github(TYPES, PROJECTS, [], specs=["cli"]), oob_dir) == []


def test_troupe_specs_all_labelled_report_nothing(oob_dir: Path) -> None:
    assert RUN(fake_github(TYPES, PROJECTS, [], specs=["cli", "cues"]), oob_dir) == []


def test_main_exits_non_zero_on_a_difference(
    oob_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(oob, "OOB", oob_dir)
    monkeypatch.setattr(oob, "ROOT", oob_dir)
    monkeypatch.setattr(oob, "gh", fake_github(TYPES[:1], PROJECTS, []))
    assert oob.main() == 1
    assert "1 difference(s)" in capsys.readouterr().out


def test_main_exits_zero_when_nothing_differs(
    oob_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(oob, "OOB", oob_dir)
    monkeypatch.setattr(oob, "ROOT", oob_dir)
    monkeypatch.setattr(oob, "gh", fake_github(TYPES, PROJECTS, []))
    assert oob.main() == 0


def test_every_github_call_is_a_read() -> None:
    """REST calls carry no method or body flags; the GraphQL call is a query, not a mutation."""
    write_flags = {"-X", "--method", "-F", "--field", "--input", "-H"}
    for name, args in [*((c.name, c.gh_args) for c in oob.CHECKS), ("specs", oob.SPECS_GH_ARGS)]:
        assert args[0] == "api"
        assert not write_flags & set(args), name
        fields = [args[i + 1] for i, a in enumerate(args) if a in {"-f", "--raw-field"}]
        if args[1] == "graphql":
            assert all(f.startswith("query={") for f in fields), name
        else:
            assert fields == [], name
