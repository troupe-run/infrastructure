"""The out-of-band drift checks (spec: org-settings): report differences, never write."""

import base64
import json
import re
import subprocess
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
# As troupe's specs carry it on main (troupe#170 design D2).
CLI_SPEC = (
    "# cli Specification\n\n## Purpose\n\nCapability: `cap:cli`\n\nThe command line, a thin\n"
    "client over the core.\n\n## Requirements\n"
)
PURPOSES = {"cli": "The command line, a thin client over the core."}
BASELINE = {"name": "baseline", "enforcement": "unenforced", "dependency_graph": "enabled"}
DEFAULTS = [{"name": "baseline", "default_for_new_repos": "public"}]
ATTACHED = {"status": "attached", "configuration": "baseline"}
CODE_SECURITY = {
    "configurations": [BASELINE],
    "defaults": DEFAULTS,
    "repositories": [
        {
            "repository": r,
            "configuration": "baseline",
            "status": "attached",
            "dependency_graph": "on",
        }
        for r in ("troupe", "website")
    ],
}
MILESTONES = {
    "repositories": ["troupe", "website"],
    "milestones": [
        {"key": "0.1.0", "title": "0.1.0", "state": "open", "description": "now"},
        {"key": "0.2.0", "title": "0.2.0", "state": "closed", "description": "next"},
    ],
}
DECLARED_MILESTONES = ["0.1.0", "0.2.0"]
BOARD: dict[str, Any] = {
    "__typename": "ProjectV2SingleSelectField",
    "options": [{"name": "cli"}, {"name": "cues"}],
}


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
    (tmp_path / "troupe-spec-purposes.json").write_text(json.dumps(PURPOSES))
    (tmp_path / "code-security.json").write_text(json.dumps(CODE_SECURITY))
    (tmp_path / "tofu" / "milestones.json").write_text(json.dumps(MILESTONES))
    return tmp_path


def fake_github(
    types: list[Any],
    projects: list[Any],
    calls: list[list[str]],
    settings: list[Any] = SETTINGS,
    profile: list[Any] = PROFILE,
    apps: list[Any] = APPS,
    specs: list[str] = SPECS,
    spec_docs: dict[str, str] | None = None,
    configurations: list[Any] | None = None,
    defaults: list[Any] = DEFAULTS,
    attachments: dict[str, Any] | None = None,
    graphs: dict[str, BaseException] | None = None,
    milestones: dict[str, Any] | None = None,
    failures: dict[str, BaseException] | None = None,
    board: dict[str, Any] | BaseException = BOARD,
) -> oob.Fetch:
    """GitHub as declared. attachments maps a repository to its attachment (None: 204, nothing
    attached); graphs maps a repository to what reading its dependency graph raises; failures
    maps a piece of a read's path (or "graphql") to what that read raises."""
    docs = {"cli": CLI_SPEC} if spec_docs is None else spec_docs
    configs = [BASELINE] if configurations is None else configurations
    attached = attachments or {}
    graph_errors = graphs or {}
    milestone_titles = milestones or {}

    def fetch(args: list[str]) -> Any:  # noqa: ANN401 (JSON)
        calls.append(args)
        for piece, failure in (failures or {}).items():
            if piece in args[1]:
                raise failure
        if args[1] == "graphql" and "projectV2(number:" in " ".join(args):
            if isinstance(board, BaseException):
                raise board
            return board
        if "/milestones?" in args[1]:
            found = milestone_titles.get(args[1].split("/")[2], DECLARED_MILESTONES)
            if isinstance(found, BaseException):
                raise found
            return found
        if args[1].endswith("/code-security/configurations"):
            return configs
        if args[1].endswith("/code-security/configurations/defaults"):
            return defaults
        if args[1].endswith("/code-security-configuration"):
            return attached.get(args[1].split("/")[2], ATTACHED)
        if args[1].endswith("/dependency-graph/sbom"):
            error = graph_errors.get(args[1].split("/")[2])
            if error is not None:
                raise error
            return 3
        if args[1].endswith("/spec.md"):
            name = args[1].split("/")[-2]
            return {"content": base64.b64encode(docs[name].encode()).decode()}
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
    report = oob.run(fetch, oob_dir, root=oob_dir)
    assert report.unreadable == [], report.unreadable
    return report.differences


def REPORT(fetch: oob.Fetch, oob_dir: Path) -> oob.Report:  # noqa: N802
    """The whole report, unreadable checks included."""
    return oob.run(fetch, oob_dir, root=oob_dir)


def refused(stderr: str) -> subprocess.CalledProcessError:
    """What oob.gh raises when gh exits non-zero for anything but a 404."""
    return subprocess.CalledProcessError(1, ["gh", "api"], "", stderr)


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


def test_a_project_unlinked_from_a_declared_repository_is_reported(oob_dir: Path) -> None:
    """govern-website design D4: OpenTofu can't link a project, so the links are declared."""
    linked = [{**PROJECTS[0], "repositories": ["troupe", "website"]}]
    (oob_dir / "projects.json").write_text(json.dumps(linked))
    unlinked = [{**PROJECTS[0], "repositories": ["troupe"]}]
    found = RUN(fake_github(TYPES, unlinked, []), oob_dir)
    assert found == [
        "projects: 1 repositories is ['troupe'] on GitHub, declared ['troupe', 'website']"
    ]


def test_the_projects_query_reads_each_project_s_linked_repositories_sorted_by_name() -> None:
    """Checks the query's text only: the fake above stands in for what gh returns."""
    (projects,) = [c for c in oob.CHECKS if c.name == "projects"]
    query = next(a for a in projects.gh_args if a.startswith("query="))
    jq = projects.gh_args[projects.gh_args.index("--jq") + 1]
    assert "repositories(first:100){nodes{name}}" in query
    assert ".repositories = ([.repositories.nodes[].name] | sort)" in jq


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


# spec-capability-label-check design D1, D2: each spec names its labels in its Capability: line.


def spec(*capability: str, purpose: str = "The command line, a thin client over the core.") -> str:
    """A spec.md whose Purpose starts with the given lines, then the Purpose text."""
    lines = "\n".join(capability)
    return f"# x Specification\n\n## Purpose\n\n{lines}\n\n{purpose}\n\n## Requirements\n"


def test_a_spec_without_a_label_is_reported(oob_dir: Path) -> None:
    docs = {"cli": spec()}
    assert RUN(fake_github(TYPES, PROJECTS, [], spec_docs=docs), oob_dir) == [
        "troupe specs: 'cli' names no capability label; add a Capability: line as the first "
        "line of its Purpose in troupe-run/troupe",
    ]


def test_a_spec_naming_an_undeclared_label_is_reported(oob_dir: Path) -> None:
    docs = {"cli": spec("Capability: `cap:cli`, `cap:development`")}
    assert RUN(fake_github(TYPES, PROJECTS, [], spec_docs=docs), oob_dir) == [
        "troupe specs: 'cli' names 'cap:development', which isn't declared; add it to "
        "tofu/labels/troupe.json by pull request, or correct the spec in troupe-run/troupe"
    ]


def test_a_spec_naming_two_declared_labels_reports_nothing(oob_dir: Path) -> None:
    docs = {"cli": spec("Capability: `cap:cli`, `cap:cues`")}
    assert RUN(fake_github(TYPES, PROJECTS, [], spec_docs=docs), oob_dir) == []


def test_a_cap_label_ahead_of_its_spec_is_not_reported(oob_dir: Path) -> None:
    """cap:cues is declared and no spec names it: a label can come before its spec."""
    assert RUN(fake_github(TYPES, PROJECTS, []), oob_dir) == []


def test_a_folder_without_a_label_of_its_own_name_reports_nothing(oob_dir: Path) -> None:
    (oob_dir / "troupe-spec-purposes.json").write_text(
        json.dumps({**PURPOSES, "artifact-store": "Run artifacts."})
    )
    docs = {
        "cli": CLI_SPEC,
        "artifact-store": spec("Capability: `cap:cues`", purpose="Run artifacts."),
    }
    fetch = fake_github(TYPES, PROJECTS, [], specs=["cli", "artifact-store"], spec_docs=docs)
    assert RUN(fetch, oob_dir) == []


@pytest.mark.parametrize(
    "line",
    [
        "Capability: cap:cli",
        "Capability: `cap:cli` (and the server)",
        "Capability: `cap:cli`; `cap:cues`",
        "Capability: `cap:cli`, `cap:cli`",
        "Capabilities: `cap:cli`",
        "capability: `cap:cli`",
        "Capability:",
    ],
)
def test_a_malformed_capability_line_is_reported_quoting_it(oob_dir: Path, line: str) -> None:
    docs = {"cli": spec(line)}
    assert RUN(fake_github(TYPES, PROJECTS, [], spec_docs=docs), oob_dir) == [
        f"troupe specs: 'cli' Capability: line is malformed: {line!r}; "
        "write it as Capability: `cap:<name>`, `cap:<name>`"
    ]


def test_a_malformed_line_s_labels_are_not_checked(oob_dir: Path) -> None:
    """`cap:nope` isn't declared, but the line is malformed, so it isn't read as naming it."""
    docs = {"cli": spec("Capability: `cap:nope` (and git)")}
    found = RUN(fake_github(TYPES, PROJECTS, [], spec_docs=docs), oob_dir)
    assert len(found) == 1
    assert "malformed" in found[0]


def test_a_failed_spec_read_is_unreadable_naming_the_spec(oob_dir: Path) -> None:
    failures: dict[str, BaseException] = {"cli/spec.md": refused("gh: Bad Gateway (HTTP 502)")}
    report = REPORT(fake_github(TYPES, PROJECTS, [], failures=failures), oob_dir)
    assert report.differences == []
    assert report.unreadable == [
        "troupe specs: couldn't read 'cli''s spec.md (gh: Bad Gateway (HTTP 502))",
        "troupe label descriptions: not checked, since troupe's specs couldn't be read",
    ]


def test_each_spec_md_is_read_once_for_both_checks(oob_dir: Path) -> None:
    (oob_dir / "troupe-spec-purposes.json").write_text(
        json.dumps({**PURPOSES, "cues": "Open requests."})
    )
    calls: list[list[str]] = []
    docs = {"cli": CLI_SPEC, "cues": spec("Capability: `cap:cues`", purpose="Open requests.")}
    assert (
        RUN(fake_github(TYPES, PROJECTS, calls, specs=["cli", "cues"], spec_docs=docs), oob_dir)
        == []
    )
    read = [c[1].split("/")[-2] for c in calls if c[1].endswith("/spec.md")]
    assert read == ["cli", "cues"]


@pytest.mark.parametrize(
    ("spec_md", "labels"),
    [
        (CLI_SPEC, ["cap:cli"]),
        (
            spec("Capability: `cap:actor-runners`, `cap:protocol`"),
            ["cap:actor-runners", "cap:protocol"],
        ),
        ("## Purpose\nCapability: `cap:cli`\nThe command line.\n", ["cap:cli"]),
        ("## Purpose\n\n\n  Capability: `cap:cli`  \n", ["cap:cli"]),
        ("# cli\n\n## Requirements\n\nCapability: `cap:cli`\n", []),
        (spec("The command line names `cap:cli` in prose."), []),
    ],
    ids=["one", "two", "no-blank-line", "blank-lines-and-spaces", "no-purpose", "prose-first"],
)
def test_capability_labels_reads_the_first_non_blank_purpose_line(
    spec_md: str, labels: list[str]
) -> None:
    assert oob.capability_labels(spec_md) == labels


# spec-capability-label-check design D3: the Purpose record is keyed by spec, without the line.


def test_every_spec_recorded_and_unchanged_reports_nothing(oob_dir: Path) -> None:
    assert RUN(fake_github(TYPES, PROJECTS, []), oob_dir) == []


def test_a_labelled_spec_with_no_recorded_purpose_is_reported(oob_dir: Path) -> None:
    (oob_dir / "troupe-spec-purposes.json").write_text("{}")
    assert RUN(fake_github(TYPES, PROJECTS, []), oob_dir) == [
        "troupe labels: 'cli' spec's Purpose isn't recorded; check the descriptions of 'cap:cli' "
        "against it and record it in oob/troupe-spec-purposes.json"
    ]


def test_a_changed_purpose_is_reported_naming_every_label_it_names(oob_dir: Path) -> None:
    docs = {"cli": spec("Capability: `cap:cli`, `cap:cues`", purpose="And a server too.")}
    assert RUN(fake_github(TYPES, PROJECTS, [], spec_docs=docs), oob_dir) == [
        "troupe labels: 'cli' spec's Purpose has changed; review the descriptions of 'cap:cli', "
        "'cap:cues' in tofu/labels/troupe.json and update oob/troupe-spec-purposes.json"
    ]


def test_a_purpose_only_rewrapped_or_respaced_is_not_reported(oob_dir: Path) -> None:
    docs = {
        "cli": "## Purpose\nCapability: `cap:cli`\n  The command\nline,   a thin client\n\n"
        "over the core.  \n## Other\n"
    }
    assert RUN(fake_github(TYPES, PROJECTS, [], spec_docs=docs), oob_dir) == []


def test_a_change_to_the_capability_line_alone_is_not_a_changed_purpose(oob_dir: Path) -> None:
    docs = {"cli": spec("Capability: `cap:cues`, `cap:cli`")}
    assert RUN(fake_github(TYPES, PROJECTS, [], spec_docs=docs), oob_dir) == []


def test_a_spec_with_no_purpose_section_is_reported_as_changed_and_unlabelled(
    oob_dir: Path,
) -> None:
    docs = {"cli": "# cli Specification\n\n## Requirements\n\nThe command line.\n"}
    found = RUN(fake_github(TYPES, PROJECTS, [], spec_docs=docs), oob_dir)
    assert found == [
        "troupe specs: 'cli' names no capability label; add a Capability: line as the first "
        "line of its Purpose in troupe-run/troupe",
        "troupe labels: 'cli' spec's Purpose has changed; review the descriptions of the labels "
        "it names in tofu/labels/troupe.json and update oob/troupe-spec-purposes.json",
    ]


def test_a_recorded_purpose_with_no_spec_is_reported(oob_dir: Path) -> None:
    (oob_dir / "troupe-spec-purposes.json").write_text(
        json.dumps({**PURPOSES, "cues": "Open requests."})
    )
    assert RUN(fake_github(TYPES, PROJECTS, []), oob_dir) == [
        "troupe labels: 'cues' has a recorded Purpose but troupe has no cues spec; "
        "remove it from oob/troupe-spec-purposes.json"
    ]


def test_main_exits_non_zero_on_a_difference(
    oob_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(oob, "OOB", oob_dir)
    monkeypatch.setattr(oob, "ROOT", oob_dir)
    monkeypatch.setattr(oob, "gh", fake_github(TYPES[:1], PROJECTS, []))
    assert oob.main([]) == 1
    assert "1 difference(s)" in capsys.readouterr().out


def test_main_exits_zero_when_nothing_differs(
    oob_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(oob, "OOB", oob_dir)
    monkeypatch.setattr(oob, "ROOT", oob_dir)
    monkeypatch.setattr(oob, "gh", fake_github(TYPES, PROJECTS, []))
    assert oob.main([]) == 0


def test_every_github_call_is_a_read() -> None:
    """REST calls carry no method or body flags; the GraphQL call is a query, not a mutation."""
    write_flags = {"-X", "--method", "-F", "--field", "--input", "-H"}
    for name, args in [
        *((c.name, c.gh_args) for c in oob.CHECKS),
        ("specs", oob.SPECS_GH_ARGS),
        ("spec.md", oob.spec_md_gh_args("runs")),
        ("configurations", oob.CONFIGURATIONS_GH_ARGS),
        ("defaults", oob.DEFAULTS_GH_ARGS),
        ("attachment", oob.attachment_gh_args("troupe")),
        ("sbom", oob.sbom_gh_args("troupe")),
        ("milestones", oob.milestones_gh_args("troupe")),
        ("board", oob.BOARD_GH_ARGS),
    ]:
        assert args[0] == "api"
        assert not write_flags & set(args), name
        fields = [args[i + 1] for i, a in enumerate(args) if a in {"-f", "--raw-field"}]
        if args[1] == "graphql":
            assert all(f.startswith("query={") for f in fields), name
        else:
            assert fields == [], name


# security-scanning design D7: the code security configuration, its default, and each declared
# repository's attachment and dependency graph.


def test_a_configuration_setting_changed_on_github_is_reported(oob_dir: Path) -> None:
    changed = {**BASELINE, "dependency_graph": "not_set"}
    found = RUN(fake_github(TYPES, PROJECTS, [], configurations=[changed]), oob_dir)
    assert found == [
        "code security configurations: 'baseline' dependency_graph is 'not_set' on GitHub, "
        "declared 'enabled'"
    ]


def test_an_undeclared_configuration_on_github_is_reported(oob_dir: Path) -> None:
    extra = {"name": "by hand", "enforcement": "enforced"}
    found = RUN(fake_github(TYPES, PROJECTS, [], configurations=[BASELINE, extra]), oob_dir)
    assert found == ["code security configurations: 'by hand' is on GitHub but not declared"]


def test_the_configuration_no_longer_the_default_is_reported(oob_dir: Path) -> None:
    found = RUN(fake_github(TYPES, PROJECTS, [], defaults=[]), oob_dir)
    assert found == ["code security defaults: 'baseline' is declared but missing on GitHub"]


def test_a_repository_with_no_configuration_attached_is_reported(oob_dir: Path) -> None:
    found = RUN(fake_github(TYPES, PROJECTS, [], attachments={"website": None}), oob_dir)
    assert found == [
        "code security repositories: 'website' configuration is None on GitHub, "
        "declared 'baseline'",
        "code security repositories: 'website' status is 'none' on GitHub, declared 'attached'",
    ]


def test_a_dependency_graph_github_says_is_missing_is_reported_as_off(oob_dir: Path) -> None:
    graphs: dict[str, BaseException] = {"troupe": oob.NotFoundError("sbom")}
    found = RUN(fake_github(TYPES, PROJECTS, [], graphs=graphs), oob_dir)
    assert found == [
        "code security repositories: 'troupe' dependency_graph is 'off' on GitHub, declared 'on'"
    ]


def test_a_dependency_graph_that_can_t_be_read_is_an_error_never_off(oob_dir: Path) -> None:
    graphs: dict[str, BaseException] = {"troupe": RuntimeError("HTTP 502")}
    report = REPORT(fake_github(TYPES, PROJECTS, [], graphs=graphs), oob_dir)
    assert report.differences == []
    assert len(report.unreadable) == 1
    assert re.search(r"'troupe'.*dependency graph.*HTTP 502", report.unreadable[0])


def test_main_exits_non_zero_naming_the_repository_when_a_graph_can_t_be_read(
    oob_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    graphs: dict[str, BaseException] = {"website": RuntimeError("HTTP 403")}
    monkeypatch.setattr(oob, "OOB", oob_dir)
    monkeypatch.setattr(oob, "ROOT", oob_dir)
    monkeypatch.setattr(oob, "gh", fake_github(TYPES, PROJECTS, [], graphs=graphs))
    assert oob.main([]) == 1
    out = capsys.readouterr().out
    assert "'website'" in out
    assert "HTTP 403" in out
    assert "no differences" not in out


def test_gh_reports_a_404_as_not_found_and_other_failures_as_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(stderr: str, returncode: int, stdout: str = "") -> Any:  # noqa: ANN401
        return lambda *_a, **_k: subprocess.CompletedProcess([], returncode, stdout, stderr)

    monkeypatch.setattr(subprocess, "run", fake_run("gh: Not Found (HTTP 404)", 1))
    with pytest.raises(oob.NotFoundError):
        oob.gh(["api", "repos/x/y/dependency-graph/sbom"])
    monkeypatch.setattr(subprocess, "run", fake_run("gh: Server Error (HTTP 502)", 1))
    with pytest.raises(subprocess.CalledProcessError):
        oob.gh(["api", "repos/x/y/dependency-graph/sbom"])
    monkeypatch.setattr(subprocess, "run", fake_run("", 0))
    assert oob.gh(["api", "repos/x/y/code-security-configuration"]) is None


# release-milestones design D5: a milestone made by hand on a listed repository.


def test_a_milestone_made_by_hand_is_reported_naming_the_repository_and_the_file(
    oob_dir: Path,
) -> None:
    made = {"website": [*DECLARED_MILESTONES, "0.3.0"]}
    found = RUN(fake_github(TYPES, PROJECTS, [], milestones=made), oob_dir)
    assert found == [
        "milestones: website: '0.3.0' is on GitHub but not declared; "
        "declare it in tofu/milestones.json"
    ]


def test_a_closed_milestone_made_by_hand_is_reported_too(oob_dir: Path) -> None:
    calls: list[list[str]] = []
    made = {"troupe": ["alpha-0", *DECLARED_MILESTONES]}
    found = RUN(fake_github(TYPES, PROJECTS, calls, milestones=made), oob_dir)
    assert found == [
        "milestones: troupe: 'alpha-0' is on GitHub but not declared; "
        "declare it in tofu/milestones.json"
    ]
    assert any("milestones?state=all" in c[1] for c in calls)


def test_every_declared_milestone_on_every_listed_repository_reports_nothing(
    oob_dir: Path,
) -> None:
    calls: list[list[str]] = []
    assert RUN(fake_github(TYPES, PROJECTS, calls), oob_dir) == []
    read = sorted(c[1].split("/")[2] for c in calls if "/milestones?" in c[1])
    assert read == ["troupe", "website"]


def test_a_declared_milestone_missing_on_github_is_left_to_the_plan(oob_dir: Path) -> None:
    found = RUN(fake_github(TYPES, PROJECTS, [], milestones={"troupe": ["0.1.0"]}), oob_dir)
    assert found == []


# milestone-interim-titles design D4: a milestone's title and its interim title both count as
# declared, so neither the old title before the apply nor the interim title after it is reported.
SWAPPED = {
    "repositories": ["troupe", "website"],
    "milestones": [
        {
            "key": "0.1.0",
            "title": "0.2.0",
            "interim_title": "0.2.0 (renumbering)",
            "state": "open",
            "description": "now",
        },
        {
            "key": "0.2.0",
            "title": "0.1.0",
            "interim_title": "0.1.0 (renumbering)",
            "state": "closed",
            "description": "next",
        },
    ],
}


def test_a_milestone_under_its_interim_title_reports_nothing(oob_dir: Path) -> None:
    (oob_dir / "tofu" / "milestones.json").write_text(json.dumps(SWAPPED))
    on_github = ["0.2.0 (renumbering)", "0.1.0 (renumbering)"]
    made = {"troupe": on_github, "website": on_github}
    assert RUN(fake_github(TYPES, PROJECTS, [], milestones=made), oob_dir) == []


def test_a_milestone_under_its_title_while_it_has_an_interim_title_reports_nothing(
    oob_dir: Path,
) -> None:
    (oob_dir / "tofu" / "milestones.json").write_text(json.dumps(SWAPPED))
    assert RUN(fake_github(TYPES, PROJECTS, []), oob_dir) == []


def test_an_undeclared_title_is_still_reported_beside_interim_titles(oob_dir: Path) -> None:
    (oob_dir / "tofu" / "milestones.json").write_text(json.dumps(SWAPPED))
    made = {"website": ["0.2.0 (renumbering)", "someday"]}
    found = RUN(fake_github(TYPES, PROJECTS, [], milestones=made), oob_dir)
    assert found == [
        "milestones: website: 'someday' is on GitHub but not declared; "
        "declare it in tofu/milestones.json"
    ]


def test_milestones_that_can_t_be_read_are_an_error_naming_the_repository(oob_dir: Path) -> None:
    errors = {"website": RuntimeError("HTTP 502")}
    report = REPORT(fake_github(TYPES, PROJECTS, [], milestones=errors), oob_dir)
    assert report.differences == []
    assert len(report.unreadable) == 1
    assert re.search(r"'website'.*milestones.*HTTP 502", report.unreadable[0])


# run-oob-check-daily design D3: anything that can't be read is unreadable, named, and never a
# difference or "no difference".


def test_a_refused_issue_types_read_is_unreadable_naming_the_check(oob_dir: Path) -> None:
    failures: dict[str, BaseException] = {"issue-types": refused("gh: Forbidden (HTTP 403)")}
    report = REPORT(fake_github(TYPES, PROJECTS, [], failures=failures), oob_dir)
    assert report.differences == []
    assert len(report.unreadable) == 1
    assert "issue types" in report.unreadable[0]
    assert "HTTP 403" in report.unreadable[0]


def test_a_projects_read_gh_fails_for_a_graphql_error_is_unreadable(oob_dir: Path) -> None:
    # gh api graphql exits 1 when the answer carries `errors` (design D3).
    error = refused("gh: Resource not accessible by integration")
    report = REPORT(fake_github(TYPES, PROJECTS, [], failures={"graphql": error}), oob_dir)
    assert report.differences == []
    # The board's Capability field is read through GraphQL too, so it is unreadable alongside.
    assert [line.split(":")[0] for line in report.unreadable] == ["projects", "board capabilities"]
    assert all("Resource not accessible by integration" in line for line in report.unreadable)


def test_two_factor_hidden_from_the_token_is_unreadable_not_a_difference(oob_dir: Path) -> None:
    hidden = [{"name": "two_factor_requirement_enabled", "value": None}]
    report = REPORT(fake_github(TYPES, PROJECTS, [], settings=hidden), oob_dir)
    assert report.differences == []
    assert len(report.unreadable) == 1
    assert "org settings" in report.unreadable[0]
    assert "two_factor_requirement_enabled" in report.unreadable[0]
    assert "value" in report.unreadable[0]


def test_a_failed_spec_list_read_is_unreadable_and_purposes_not_checked(oob_dir: Path) -> None:
    github = fake_github(TYPES, PROJECTS, [])

    def fetch(args: list[str]) -> Any:  # noqa: ANN401 (JSON)
        if args[1].endswith("/contents/openspec/specs"):
            raise refused("gh: Bad Gateway (HTTP 502)")
        return github(args)

    report = REPORT(fetch, oob_dir)
    assert report.differences == []
    assert report.unreadable == [
        "troupe specs: couldn't read it (gh: Bad Gateway (HTTP 502))",
        "troupe label descriptions: not checked, since troupe's specs couldn't be read",
    ]


def test_a_project_short_description_declared_null_and_read_null_matches(oob_dir: Path) -> None:
    # null is a real value outside the checks GitHub hides fields from (design D3).
    projects = [{**PROJECTS[0], "shortDescription": None}]
    (oob_dir / "projects.json").write_text(json.dumps(projects))
    assert RUN(fake_github(TYPES, projects, []), oob_dir) == []


def test_a_short_description_cleared_on_github_is_a_difference_not_unreadable(
    oob_dir: Path,
) -> None:
    (oob_dir / "projects.json").write_text(
        json.dumps([{**PROJECTS[0], "shortDescription": "Where troupe is going"}])
    )
    cleared = [{**PROJECTS[0], "shortDescription": None}]
    assert RUN(fake_github(TYPES, cleared, []), oob_dir) == [
        "projects: 1 shortDescription is None on GitHub, declared 'Where troupe is going'"
    ]


def test_main_reports_every_unreadable_check_and_every_difference(
    oob_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    failures: dict[str, BaseException] = {
        "issue-types": refused("gh: Forbidden (HTTP 403)"),
        "graphql": refused("gh: Resource not accessible by integration"),
    }
    hand_made = {"website": [*DECLARED_MILESTONES, "0.3.0"]}
    monkeypatch.setattr(oob, "OOB", oob_dir)
    monkeypatch.setattr(oob, "ROOT", oob_dir)
    monkeypatch.setattr(
        oob, "gh", fake_github(TYPES, PROJECTS, [], failures=failures, milestones=hand_made)
    )
    assert oob.main([]) == 1
    out = capsys.readouterr().out
    assert "oob: issue types: couldn't read it (gh: Forbidden (HTTP 403))" in out
    assert "oob: projects: couldn't read it (gh: Resource not accessible by integration)" in out
    assert "milestones: website: '0.3.0' is on GitHub but not declared" in out
    assert "1 difference(s)" in out
    assert "no differences" not in out


# run-oob-check-daily design D4: --ci runs every check a hand run does; only its output differs.

EVERY_CHECK = [
    ".github files",
    "org settings",
    "App installations",
    "issue types",
    "projects",
    "troupe specs",
    "troupe label descriptions",
    "code security",
    "milestones",
    "board capabilities",
]


def test_ci_reads_the_org_s_installations_and_lists_every_check(
    oob_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []
    summary = oob_dir / "summary.md"
    monkeypatch.setattr(oob, "OOB", oob_dir)
    monkeypatch.setattr(oob, "ROOT", oob_dir)
    monkeypatch.setattr(oob, "gh", fake_github(TYPES, PROJECTS, calls))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert oob.main(["--ci"]) == 0
    assert any(c[1] == "orgs/troupe-run/installations" for c in calls)
    assert f"Checked: {', '.join(EVERY_CHECK)}." in summary.read_text()
    assert f"oob: no differences ({', '.join(EVERY_CHECK)})" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [["--skip", "projects"], ["ci"], ["--ci", "extra"], ["--CI"]])
def test_any_other_argument_exits_2_before_reading_anything(
    argv: list[str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(oob, "gh", fake_github(TYPES, PROJECTS, calls))
    assert oob.main(argv) == 2
    assert calls == []
    assert "usage: uv run scripts/oob.py [--ci]" in capsys.readouterr().err


# run-oob-check-daily design D5: under --ci, each difference and unreadable check is an error
# annotation, and the run's summary lists what was found, what ran and what was left to a person.


def ci_main(
    oob_dir: Path, monkeypatch: pytest.MonkeyPatch, fetch: oob.Fetch, argv: list[str] | None = None
) -> tuple[int, Path]:
    summary = oob_dir / "summary.md"
    monkeypatch.setattr(oob, "OOB", oob_dir)
    monkeypatch.setattr(oob, "ROOT", oob_dir)
    monkeypatch.setattr(oob, "gh", fetch)
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    return oob.main(["--ci"] if argv is None else argv), summary


def test_ci_annotates_each_difference_and_each_unreadable_check(
    oob_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    failures: dict[str, BaseException] = {"issue-types": refused("gh: Forbidden (HTTP 403)")}
    fetch = fake_github(TYPES, PROJECTS, [], failures=failures, settings=[
        {"name": "two_factor_requirement_enabled", "value": True}
    ])  # fmt: skip
    code, _ = ci_main(oob_dir, monkeypatch, fetch)
    assert code == 1
    errors = [line for line in capsys.readouterr().out.splitlines() if line.startswith("::error")]
    assert errors == [
        "::error title=oob difference::org settings: 'two_factor_requirement_enabled' value is "
        "True on GitHub, declared False",
        "::error title=oob unreadable::issue types: couldn't read it (gh: Forbidden (HTTP 403))",
    ]


def test_an_annotation_escapes_what_would_end_or_split_it() -> None:
    assert oob.annotation("difference", "50% done\r\nnext") == (
        "::error title=oob difference::50%25 done%0D%0Anext"
    )


def test_the_summary_lists_differences_unreadable_checks_what_ran_and_what_was_left(
    oob_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failures: dict[str, BaseException] = {"issue-types": refused("gh: Forbidden (HTTP 403)")}
    made = {"website": [*DECLARED_MILESTONES, "0.3.0"]}
    fetch = fake_github(TYPES, PROJECTS, [], failures=failures, milestones=made)
    _, summary = ci_main(oob_dir, monkeypatch, fetch)
    text = summary.read_text()
    assert text.startswith("### Out-of-band drift check\n")
    assert "**1 difference, 1 check couldn't be read.**" in text
    assert "- milestones: website: '0.3.0' is on GitHub but not declared" in text
    assert "- issue types: couldn't read it (gh: Forbidden (HTTP 403))" in text
    ran = [n for n in EVERY_CHECK if n != "issue types"]
    assert f"Checked: {', '.join(ran)}." in text


def test_the_summary_says_no_differences_when_there_are_none(
    oob_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    code, summary = ci_main(oob_dir, monkeypatch, fake_github(TYPES, PROJECTS, []))
    assert code == 0
    assert "**No differences.**" in summary.read_text()


def test_a_hand_run_writes_no_annotations_and_no_summary(
    oob_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fetch = fake_github(TYPES[:1], PROJECTS, [])
    code, summary = ci_main(oob_dir, monkeypatch, fetch, argv=[])
    assert code == 1
    assert "::error" not in capsys.readouterr().out
    assert not summary.exists()


# capability-label-standard-change design D4: the board's Capability options, both ways against
# the declared cap: labels, which the owner changes in the field's settings.


def board(*names: str) -> dict[str, Any]:
    return {**BOARD, "options": [{"name": n} for n in names]}


def test_a_declared_label_with_no_board_option_is_reported(oob_dir: Path) -> None:
    assert RUN(fake_github(TYPES, PROJECTS, [], board=board("cli")), oob_dir) == [
        "board capabilities: cap:cues has no 'cues' option in the troupe roadmap board's "
        "Capability field; the owner adds it in the field's settings"
    ]


def test_a_board_option_with_no_declared_label_is_reported(oob_dir: Path) -> None:
    found = RUN(fake_github(TYPES, PROJECTS, [], board=board("cli", "cues", "lifecycle")), oob_dir)
    assert found == [
        "board capabilities: the troupe roadmap board's Capability field has a 'lifecycle' "
        "option, but no cap:lifecycle is declared in tofu/labels/troupe.json; the owner removes "
        "it in the field's settings, or the label is declared"
    ]


def test_board_options_matching_the_labels_report_nothing(oob_dir: Path) -> None:
    calls: list[list[str]] = []
    assert RUN(fake_github(TYPES, PROJECTS, calls, board=board("cues", "cli")), oob_dir) == []
    assert oob.BOARD_GH_ARGS in calls


def test_a_board_with_no_capability_field_is_a_difference_naming_it(oob_dir: Path) -> None:
    # What gh prints when the board has no field of that name (checked on 2026-10-26).
    missing = refused(
        "gh: Could not resolve to a Unions::ProjectV2FieldConfiguration with the name Capability"
    )
    assert RUN(fake_github(TYPES, PROJECTS, [], board=missing), oob_dir) == [
        "board capabilities: the troupe roadmap board has no 'Capability' field; "
        "the owner adds it as a single select whose options are the cap: labels' names"
    ]


def test_a_capability_field_that_isn_t_a_single_select_is_a_difference(oob_dir: Path) -> None:
    text = {"__typename": "ProjectV2Field"}
    assert RUN(fake_github(TYPES, PROJECTS, [], board=text), oob_dir) == [
        "board capabilities: the troupe roadmap board's 'Capability' field is a ProjectV2Field, "
        "not a single select"
    ]


def test_a_board_that_can_t_be_read_is_unreadable_not_a_difference(oob_dir: Path) -> None:
    error = refused("gh: Resource not accessible by integration")
    report = REPORT(fake_github(TYPES, PROJECTS, [], board=error), oob_dir)
    assert report.differences == []
    assert len(report.unreadable) == 1
    assert report.unreadable[0].startswith("board capabilities:")
    assert "Resource not accessible by integration" in report.unreadable[0]
