"""Delivered files keep their source's mode (spec: guard-delivery; executable-hooks design).

Every GitHub call is injected: these tests never touch the network.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

import guard
import hook_modes
from commit_state import git_blob_sha
from hook_modes import Delivered, Entry, ModeError, Response

API = "https://api.example"
TOKEN = "fake-token"  # noqa: S105 (a stand-in, never sent to GitHub)
HOOK = ".githooks/pre-push"
HOOK_CONTENT = "#!/bin/sh\nexec true\n"
HOOK_BLOB = git_blob_sha(HOOK_CONTENT.encode())


def plan_json(*files: tuple[str, str, str]) -> dict[str, Any]:
    """A `tofu show -json` plan holding these deliveries and one unrelated resource."""
    resources: list[dict[str, Any]] = [
        {"address": "github_repository.other", "values": {"name": "x"}},
    ]
    resources += [
        {
            "address": f'github_repository_file.guard["{repo}:{path}"]',
            "values": {"repository": repo, "file": path, "content": content},
        }
        for repo, path, content in files
    ]
    return {"planned_values": {"root_module": {"resources": resources}}}


def tree(**files: tuple[str, str]) -> dict[str, tuple[str, str]]:
    return dict(files)


def modes(
    delivered: list[Delivered],
    sources: dict[str, str],
    trees: dict[str, dict[str, tuple[str, str]]],
) -> list[Entry]:
    return hook_modes.mode_plan(delivered, sources.__getitem__, trees.__getitem__)


# --- plan -------------------------------------------------------------------------------------


def test_only_guard_deliveries_are_read_from_the_plan() -> None:
    plan = plan_json(("website", HOOK, HOOK_CONTENT), ("troupe", "scripts/guard.py", "x"))
    assert hook_modes.delivered_files(plan) == [
        Delivered("troupe", "scripts/guard.py", "x"),
        Delivered("website", HOOK, HOOK_CONTENT),
    ]


def test_a_delivery_with_unknown_content_in_the_plan_refuses() -> None:
    plan = plan_json(("website", HOOK, HOOK_CONTENT))
    plan["planned_values"]["root_module"]["resources"][1]["values"]["content"] = None
    with pytest.raises(ModeError, match="no known repository, file and content"):
        hook_modes.delivered_files(plan)


def test_a_delivery_whose_content_is_sensitive_is_still_read() -> None:
    # `content` is sensitive (truncate-long-plans D7). `tofu show -json` keeps the value and marks
    # it in sensitive_values, as OpenTofu 1.13.1 does (probe, 2026-10-18).
    plan = plan_json(("website", HOOK, HOOK_CONTENT))
    plan["planned_values"]["root_module"]["resources"][1]["sensitive_values"] = {"content": True}
    [delivered] = hook_modes.delivered_files(plan)
    assert delivered == Delivered("website", HOOK, HOOK_CONTENT)
    assert git_blob_sha(delivered.content.encode()) == HOOK_BLOB


def test_a_regular_target_with_an_executable_source_is_listed() -> None:
    entries = modes(
        [Delivered("website", HOOK, HOOK_CONTENT)],
        {HOOK: "100755"},
        {"website": tree(**{HOOK: ("100644", HOOK_BLOB)})},
    )
    assert entries == [Entry("website", HOOK, "100755", HOOK_BLOB)]


def test_a_matching_mode_is_not_listed() -> None:
    entries = modes(
        [Delivered("troupe", HOOK, HOOK_CONTENT)],
        {HOOK: "100755"},
        {"troupe": tree(**{HOOK: ("100755", HOOK_BLOB)})},
    )
    assert entries == []


def test_an_absent_file_with_an_executable_source_is_listed() -> None:
    entries = modes([Delivered("new", HOOK, HOOK_CONTENT)], {HOOK: "100755"}, {"new": tree()})
    assert entries == [Entry("new", HOOK, "100755", HOOK_BLOB)]


def test_a_regular_source_is_never_listed_absent_or_present() -> None:
    entries = modes(
        [Delivered("new", "scripts/guard.py", "x"), Delivered("old", "scripts/guard.py", "x")],
        {"scripts/guard.py": "100644"},
        {"new": tree(), "old": tree(**{"scripts/guard.py": ("100644", "b")})},
    )
    assert entries == []


def test_an_executable_target_with_a_regular_source_is_listed_back_to_regular() -> None:
    entries = modes(
        [Delivered("troupe", "scripts/guard.py", "x")],
        {"scripts/guard.py": "100644"},
        {"troupe": tree(**{"scripts/guard.py": ("100755", "b")})},
    )
    assert [e.mode for e in entries] == ["100644"]


def test_a_target_mode_that_is_neither_regular_nor_executable_refuses() -> None:
    with pytest.raises(ModeError, match="120000"):
        modes(
            [Delivered("website", HOOK, HOOK_CONTENT)],
            {HOOK: "100755"},
            {"website": tree(**{HOOK: ("120000", HOOK_BLOB)})},
        )


def test_each_target_tree_is_read_once() -> None:
    reads: list[str] = []

    def tree_of(repository: str) -> dict[str, tuple[str, str]]:
        reads.append(repository)
        return {}

    hook_modes.mode_plan(
        [Delivered("website", HOOK, "a"), Delivered("website", "x", "b")],
        lambda _: "100644",
        tree_of,
    )
    assert reads == ["website"]


def test_the_blob_is_what_git_hash_object_gives_the_content(tmp_path: Path) -> None:
    path = tmp_path / "hook"
    path.write_text(HOOK_CONTENT, encoding="utf-8", newline="\n")
    expected = subprocess.run(
        ["git", "hash-object", str(path)], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert expected == HOOK_BLOB


def test_a_truncated_tree_refuses_naming_the_repository() -> None:
    with pytest.raises(ModeError, match=r"troupe-run/website.*truncated"):
        hook_modes.tree_entries({"truncated": True, "tree": []}, "website")


def test_the_source_mode_is_the_index_mode_and_a_file_with_no_source_is_regular(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "hook").write_text("#!/bin/sh\n", encoding="utf-8")
    (tmp_path / "plain").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "hook", "plain"], cwd=tmp_path, check=True)
    subprocess.run(["git", "update-index", "--chmod=+x", "hook"], cwd=tmp_path, check=True)
    assert hook_modes.source_mode(tmp_path, "hook") == "100755"
    assert hook_modes.source_mode(tmp_path, "plain") == "100644"
    assert hook_modes.source_mode(tmp_path, ".github/guard-delivery.json") == "100644"


def test_this_repository_delivers_its_hooks_as_executable() -> None:
    root = Path(__file__).resolve().parents[2]
    for name in ("pre-commit", "commit-msg", "pre-push"):
        assert hook_modes.source_mode(root, f".githooks/{name}") == "100755"


def test_the_summary_lists_each_mode_or_says_there_are_none() -> None:
    assert "none" in hook_modes.summary([])
    text = hook_modes.summary([Entry("website", HOOK, "100755", HOOK_BLOB)])
    assert f"| website | `{HOOK}` | 100755 |" in text


def test_plan_writes_the_mode_plan_from_the_saved_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(plan_json(("website", HOOK, HOOK_CONTENT))), encoding="utf-8")
    calls: list[tuple[str, str]] = []

    def send(method: str, url: str, token: str, body: dict[str, Any] | None) -> Response:
        calls.append((method, url))
        return Response(
            200, {"tree": [{"path": HOOK, "mode": "100644", "type": "blob", "sha": HOOK_BLOB}]}
        )

    monkeypatch.setenv("GH_TOKEN", TOKEN)
    monkeypatch.setenv("GITHUB_API_URL", API)
    root = Path(__file__).resolve().parents[2]
    out, summary = tmp_path / "mode-plan.json", tmp_path / "modes.md"
    argv = ["plan", "--plan-json", str(plan), "--out", str(out), "--summary", str(summary)]
    assert hook_modes.main([*argv, "--root", str(root)], send=send) == 0
    assert calls == [("GET", f"{API}/repos/troupe-run/website/git/trees/main?recursive=1")]
    assert hook_modes.read_mode_plan(out) == [Entry("website", HOOK, "100755", HOOK_BLOB)]
    assert "website" in summary.read_text(encoding="utf-8")


def test_a_mode_plan_of_another_version_refuses(tmp_path: Path) -> None:
    path = tmp_path / "mode-plan.json"
    path.write_text('{"version": 2, "entries": []}', encoding="utf-8")
    with pytest.raises(ModeError, match="version 1"):
        hook_modes.read_mode_plan(path)


# --- apply ------------------------------------------------------------------------------------


class GitHub:
    """A stand-in for the Git Data API: one repository per name, with a head and one tree."""

    def __init__(self, files: dict[str, dict[str, tuple[str, str]]], ref_status: int = 200) -> None:
        self.files = files
        self.ref_status = ref_status
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def __call__(self, method: str, url: str, token: str, body: dict[str, Any] | None) -> Response:
        assert token == TOKEN
        self.calls.append((method, url, body))
        repo = url.removeprefix(f"{API}/repos/troupe-run/").split("/")[0]
        if method == "GET" and "/git/ref/heads/main" in url:
            return Response(200, {"object": {"sha": f"head-{repo}"}})
        if method == "GET" and "/git/commits/" in url:
            return Response(200, {"tree": {"sha": f"tree-{repo}"}})
        if method == "GET" and "/git/trees/" in url:
            items = [
                {"path": p, "mode": m, "type": "blob", "sha": s}
                for p, (m, s) in self.files[repo].items()
            ]
            return Response(200, {"tree": items, "truncated": False})
        if method == "POST" and url.endswith("/git/trees"):
            return Response(201, {"sha": f"newtree-{repo}"})
        if method == "POST" and url.endswith("/git/commits"):
            return Response(201, {"sha": f"commit-{repo}"})
        if method == "PATCH":
            return Response(self.ref_status, {"message": "Update is not a fast forward"})
        raise AssertionError(f"unexpected {method} {url}")

    def writes(self) -> list[tuple[str, str, dict[str, Any] | None]]:
        return [call for call in self.calls if call[0] != "GET"]


def apply(entries: list[Entry], github: GitHub, out: list[str]) -> int:
    return hook_modes.apply_modes(entries, token=TOKEN, api=API, send=github, out=out.append)


def test_one_commit_per_repository_sets_the_modes_and_keeps_each_blob() -> None:
    other = ".githooks/commit-msg"
    github = GitHub(
        {
            "website": {
                HOOK: ("100644", HOOK_BLOB),
                other: ("100644", "b2"),
                "README": ("100644", "r"),
            },
            "troupe": {HOOK: ("100644", HOOK_BLOB)},
        }
    )
    entries = [
        Entry("website", HOOK, "100755", HOOK_BLOB),
        Entry("website", other, "100755", "b2"),
        Entry("troupe", HOOK, "100755", HOOK_BLOB),
    ]
    assert apply(entries, github, []) == 0
    writes = github.writes()
    assert [(m, u.split("/repos/troupe-run/")[1]) for m, u, _ in writes] == [
        ("POST", "troupe/git/trees"),
        ("POST", "troupe/git/commits"),
        ("PATCH", "troupe/git/refs/heads/main"),
        ("POST", "website/git/trees"),
        ("POST", "website/git/commits"),
        ("PATCH", "website/git/refs/heads/main"),
    ]
    website_tree = writes[3][2]
    assert website_tree == {
        "base_tree": "tree-website",
        "tree": [
            {"path": HOOK, "mode": "100755", "type": "blob", "sha": HOOK_BLOB},
            {"path": other, "mode": "100755", "type": "blob", "sha": "b2"},
        ],
    }
    assert writes[4][2] == {
        "message": f"chore(guard): set the mode of {other}, {HOOK} from troupe-run/infrastructure",
        "tree": "newtree-website",
        "parents": ["head-website"],
    }
    assert writes[5][2] == {"sha": "commit-website", "force": False}


def test_a_changed_blob_refuses_before_any_write_naming_the_repository_and_file() -> None:
    github = GitHub(
        {"troupe": {HOOK: ("100644", HOOK_BLOB)}, "website": {HOOK: ("100644", "other")}}
    )
    entries = [
        Entry("troupe", HOOK, "100755", HOOK_BLOB),
        Entry("website", HOOK, "100755", HOOK_BLOB),
    ]
    with pytest.raises(
        ModeError, match=f"troupe-run/website:{HOOK} isn't the content the plan read"
    ):
        apply(entries, github, [])
    assert github.writes() == []


def test_a_listed_file_missing_at_apply_time_refuses_before_any_write() -> None:
    github = GitHub({"website": {}})
    with pytest.raises(ModeError, match="no file"):
        apply([Entry("website", HOOK, "100755", HOOK_BLOB)], github, [])
    assert github.writes() == []


def test_a_main_that_moved_gets_a_422_and_fails_the_run() -> None:
    github = GitHub({"website": {HOOK: ("100644", HOOK_BLOB)}}, ref_status=422)
    with pytest.raises(ModeError, match="main moved since it was read"):
        apply([Entry("website", HOOK, "100755", HOOK_BLOB)], github, [])


def test_an_empty_mode_plan_makes_no_request() -> None:
    github = GitHub({})
    out: list[str] = []
    assert apply([], github, out) == 0
    assert github.calls == []
    assert out == ["hook_modes: no modes to set."]


def test_the_commit_message_passes_the_guards_commit_message_rule() -> None:
    message = hook_modes.commit_message([HOOK, ".githooks/commit-msg", ".githooks/pre-commit"])
    assert not guard.commit_message(message).refused


def test_apply_reports_a_refusal_as_exit_code_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "mode-plan.json"
    entry = {"repository": "website", "path": HOOK, "mode": "100755", "blob": HOOK_BLOB}
    path.write_text(json.dumps({"version": 1, "entries": [entry]}), encoding="utf-8")
    monkeypatch.setenv("GH_TOKEN", TOKEN)
    monkeypatch.setenv("GITHUB_API_URL", API)
    github = GitHub({"website": {HOOK: ("100644", "changed")}})
    assert hook_modes.main(["apply", "--mode-plan", str(path)], send=github) == 1
    assert "isn't the content the plan read" in capsys.readouterr().err


def test_no_token_refuses_with_exit_code_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    assert hook_modes.main(["apply", "--mode-plan", str(tmp_path / "x.json")]) == 2
