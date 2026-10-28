"""The capability-label rule: a troupe spec's Capability: line, checked on GitHub against the
labels troupe-run/infrastructure declares on main (guard-capability-label-at-proposal)."""

import email.message
import http.client
import io
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import Repo
from test_guard_openspec import captured, stub_openspec

import guard


def spec(first_line: str) -> str:
    return f"# x Specification\n\n## Purpose\n\n{first_line}\n\nWhat x is for.\n\n## Requirements\n"


# Design D6: the line's one reading, now in the delivered guard.


@pytest.mark.parametrize(
    ("spec_md", "labels"),
    [
        (spec("Capability: `cap:stages`"), ["cap:stages"]),
        (spec("Capability: `cap:stages`, `cap:vcs`"), ["cap:stages", "cap:vcs"]),
        ("# x\n\n## Requirements\n\nCapability: `cap:stages`\n", []),
        (spec("Defines where a run works, as `cap:stages` says."), []),
    ],
    ids=["one", "two", "no-purpose", "prose-first"],
)
def test_capability_labels_reads_the_labels_the_line_names(spec_md: str, labels: list[str]) -> None:
    assert guard.capability_labels(spec_md) == labels


@pytest.mark.parametrize(
    "line",
    [
        "Capabilities: `cap:stages`",
        "capability: `cap:stages`",
        "Capability:",
        "Capability: cap:stages",
        "Capability: `cap:vcs`, `cap:vcs`",
        "Capability: `cap:vcs` (and git)",
    ],
    ids=["plural", "lower-case", "empty", "no-backticks", "repeated", "trailing-prose"],
)
def test_capability_labels_refuses_a_malformed_line_rather_than_reading_part_of_it(
    line: str,
) -> None:
    with pytest.raises(guard.MalformedCapabilityLineError) as raised:
        guard.capability_labels(spec(line))
    assert str(raised.value) == line


# The rule: a tree under tmp_path shaped like troupe's, judged with the labels injected.

TROUPE = "troupe-run/troupe"
DECLARED = frozenset({"cap:stages", "cap:vcs"})


def declared() -> frozenset[str]:
    return DECLARED


def never() -> frozenset[str]:
    raise AssertionError("the labels were read")


def write(root: Path, relative: str, text: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def main_spec(root: Path, name: str, first_line: str) -> None:
    write(root, f"openspec/specs/{name}/spec.md", spec(first_line))


def proposed_spec(root: Path, change: str, name: str, text: str) -> None:
    write(root, f"openspec/changes/{change}/specs/{name}/spec.md", text)


def judged(
    root: Path,
    scope: guard.OpenSpecScope,
    repository: str | None = TROUPE,
    read_labels: Callable[[], frozenset[str]] = declared,
) -> tuple[guard.Decision, list[str]]:
    notes: list[str] = []
    decision = guard.capability_label(root, scope, repository, read_labels, notes=notes)
    return decision, notes


def touching(*paths: str, branch: str = "x", pull_request: bool = True) -> guard.OpenSpecScope:
    return guard.openspec_scope(paths, branch, pull_request, lambda path: True)


def test_a_proposed_spec_naming_a_declared_label_passes(tmp_path: Path) -> None:
    proposed_spec(tmp_path, "x", "run-workspaces", spec("Capability: `cap:stages`"))
    decision, notes = judged(tmp_path, touching("openspec/changes/x/proposal.md"))
    assert decision == guard.ALLOW
    assert notes == [
        "guard: capability-label: judged 1 spec(s), what the range touches, against 2 declared "
        "label(s)."
    ]


def test_a_proposed_spec_naming_an_undeclared_label_fails_pointing_at_the_standard_change(
    tmp_path: Path,
) -> None:
    proposed_spec(tmp_path, "x", "run-workspaces", spec("Capability: `cap:workspaces`"))
    decision, _ = judged(tmp_path, touching("openspec/changes/x/proposal.md"))
    assert decision.rule == "capability-label"
    assert decision.problem == (
        "1 problem(s) with the capability labels specs name: change `x`: spec `run-workspaces` "
        "names `cap:workspaces`, which troupe-run/infrastructure doesn't declare on main."
    )
    assert (
        "open the label's sub-issue from https://github.com/troupe-run/infrastructure/blob/main/"
        "docs/standard-changes.md#a-capability-label under the needing issue's Epic, so it "
        "blocks that issue" in decision.fix
    )
    assert decision.fix.endswith("Or name a declared label.")


def test_an_edit_to_an_existing_spec_s_line_is_judged_naming_the_spec(tmp_path: Path) -> None:
    main_spec(tmp_path, "stages", "Capability: `cap:stages`, `cap:gates`")
    decision, _ = judged(tmp_path, touching("openspec/specs/stages/spec.md"))
    assert decision.rule == "capability-label"
    assert "spec `stages` names `cap:gates`, which troupe-run/infrastructure" in decision.problem
    assert "change `" not in decision.problem
    assert "`cap:stages`" not in decision.problem


@pytest.mark.parametrize(
    "text",
    [
        "# run-workspaces\n\n## ADDED Requirements\n",
        spec("Defines where a run works."),
    ],
    ids=["no-purpose", "prose-first"],
)
def test_a_proposed_spec_with_no_line_fails_saying_where_the_line_goes(
    tmp_path: Path, text: str
) -> None:
    proposed_spec(tmp_path, "x", "run-workspaces", text)
    decision, _ = judged(tmp_path, touching("openspec/changes/x/tasks.md"))
    assert decision.rule == "capability-label"
    assert (
        "change `x`: spec `run-workspaces` names no capability label: its Purpose doesn't start "
        "with a Capability: line" in decision.problem
    )
    assert "at the top of the delta's `## Purpose`" in decision.fix
    assert "standard-changes.md" not in decision.fix


def test_a_malformed_line_fails_naming_the_spec_the_line_and_its_shape(tmp_path: Path) -> None:
    main_spec(tmp_path, "stages", "Capability: cap:stages")
    decision, _ = judged(tmp_path, touching("openspec/specs/stages/spec.md"))
    assert decision.rule == "capability-label"
    assert (
        "spec `stages`: its Capability: line is malformed: 'Capability: cap:stages'"
        in decision.problem
    )
    assert f"Make the first line of the spec's Purpose {guard.CAPABILITY_SHAPE}." in decision.fix
    assert "delta" not in decision.fix


def test_every_finding_is_listed_sorted_by_spec_with_a_fix_for_each_kind(tmp_path: Path) -> None:
    main_spec(tmp_path, "stages", "Capability: `cap:gates`")
    main_spec(tmp_path, "config", "Defines the config.")
    decision, _ = judged(tmp_path, guard.OpenSpecScope(everything=True))
    assert decision.problem.startswith(
        "2 problem(s) with the capability labels specs name: spec `config` names no"
    )
    assert "; spec `stages` names `cap:gates`" in decision.problem
    assert "standard-changes.md" in decision.fix
    assert guard.CAPABILITY_SHAPE in decision.fix


@pytest.mark.parametrize("repository", ["troupe-run/infrastructure", "troupe-run/website", None])
def test_another_repository_isn_t_judged_and_its_labels_aren_t_read(
    tmp_path: Path, repository: str | None
) -> None:
    main_spec(tmp_path, "stages", "no line here")
    decision, notes = judged(tmp_path, guard.OpenSpecScope(everything=True), repository, never)
    assert decision == guard.ALLOW
    assert notes[0].endswith("names no capability labels, so it wasn't checked.")


# The scope (design D2)


def test_a_pull_request_that_touches_no_spec_doesn_t_read_the_labels(tmp_path: Path) -> None:
    main_spec(tmp_path, "stages", "Capability: `cap:nope`")
    decision, notes = judged(tmp_path, touching("README.md"), read_labels=never)
    assert decision == guard.ALLOW
    assert notes == ["guard: capability-label: no spec in scope, so the labels weren't read."]


def test_a_delta_for_a_spec_that_exists_isn_t_judged(tmp_path: Path) -> None:
    main_spec(tmp_path, "stages", "Capability: `cap:stages`")
    proposed_spec(tmp_path, "x", "stages", spec("Capability: `cap:nope`"))
    specs = guard.capability_specs(tmp_path, touching("openspec/changes/x/specs/stages/spec.md"))
    assert specs == []
    decision, notes = judged(tmp_path, touching("openspec/changes/x/specs/stages/spec.md"))
    assert decision == guard.ALLOW
    assert notes == ["guard: capability-label: no spec in scope, so the labels weren't read."]


@pytest.mark.parametrize(
    ("paths", "branch", "pull_request"),
    [
        (("README.md",), "main", False),
        (("scripts/guard.py",), "x", True),
        ((".github/workflows/guard.yml",), "x", False),
    ],
    ids=["push-to-main", "guard-changed", "workflow-changed"],
)
def test_everything_is_judged_on_a_push_to_main_and_when_the_guard_changes(
    tmp_path: Path, paths: tuple[str, ...], branch: str, pull_request: bool
) -> None:
    main_spec(tmp_path, "stages", "Capability: `cap:stages`")
    main_spec(tmp_path, "vcs", "Capability: `cap:vcs`")
    proposed_spec(tmp_path, "y", "run-workspaces", spec("Capability: `cap:stages`"))
    write(tmp_path, "openspec/changes/archive/2026-01-01-z/specs/old/spec.md", spec("none"))
    scope = touching(*paths, branch=branch, pull_request=pull_request)
    found = [(s.name, s.change) for s in guard.capability_specs(tmp_path, scope)]
    assert found == [("run-workspaces", "y"), ("stages", None), ("vcs", None)]


def test_an_archive_commit_judges_the_main_spec_it_creates(tmp_path: Path) -> None:
    main_spec(tmp_path, "run-workspaces", "Capability: `cap:stages`")
    write(
        tmp_path,
        "openspec/changes/archive/2026-10-26-x/specs/run-workspaces/spec.md",
        spec("Capability: `cap:stages`"),
    )
    scope = guard.openspec_scope(
        [
            "openspec/specs/run-workspaces/spec.md",
            "openspec/changes/archive/2026-10-26-x/specs/run-workspaces/spec.md",
            "openspec/changes/x/specs/run-workspaces/spec.md",
        ],
        "x",
        True,
        lambda path: (tmp_path / path).is_dir(),
    )
    found = [(s.name, s.change) for s in guard.capability_specs(tmp_path, scope)]
    assert found == [("run-workspaces", None)]
    assert judged(tmp_path, scope)[0] == guard.ALLOW


# The CI entry: after openspec-strict, for the repository the run is in (design D1).


def ci_branch(
    make_repo: Callable[[], Repo], first_line: str, change: str = "x"
) -> tuple[Repo, str]:
    """A branch proposing the new spec run-workspaces, whose Purpose starts with first_line."""
    repo = make_repo()
    base = repo.head()
    repo.switch(change)
    repo.change(change, tasks="- [ ] 1.1 build it\n")
    proposed_spec(repo.path, change, "run-workspaces", spec(first_line))
    made = repo.commit(f"docs(openspec): propose {change}")
    assert made.returncode == 0, made.stderr
    return repo, base


def test_a_fork_s_pull_request_into_troupe_is_judged_against_troupe_s_labels(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base = ci_branch(make_repo, "Capability: `cap:workspaces`")
    bin_dir = stub_openspec(tmp_path / "bin", captured("pass"))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GITHUB_REPOSITORY", TROUPE)
    status = guard.run_ci_entry(
        repo.path, base, repo.head(), "x", "docs: propose x", "someone/troupe", declared
    )
    assert status == 1
    err = capsys.readouterr().err
    assert "guard: capability-label: 1 problem(s)" in err
    assert "change `x`: spec `run-workspaces` names `cap:workspaces`" in err


def test_both_refusals_print_when_both_rules_fail(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The captured failing report fails the active change add-thing.
    repo, base = ci_branch(make_repo, "Capability: `cap:workspaces`", "add-thing")
    bin_dir = stub_openspec(tmp_path / "bin", captured("fail"))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GITHUB_REPOSITORY", TROUPE)
    status = guard.run_ci_entry(
        repo.path, base, repo.head(), "add-thing", "docs: propose add-thing", None, declared
    )
    assert status == 1
    err = capsys.readouterr().err
    assert "guard: openspec-strict:" in err
    assert "guard: capability-label:" in err


def test_a_passing_run_logs_what_capability_label_judged(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base = ci_branch(make_repo, "Capability: `cap:stages`")
    bin_dir = stub_openspec(tmp_path / "bin", captured("pass"))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GITHUB_REPOSITORY", TROUPE)
    status = guard.run_ci_entry(
        repo.path, base, repo.head(), "x", "docs: propose x", None, declared
    )
    out = capsys.readouterr().out
    assert status == 0, out
    assert "guard: capability-label: judged 1 spec(s), what the range touches" in out


# Reading the declared labels (design D3), the request injected.

Send = Callable[[urllib.request.Request, float], bytes]


def answering(body: bytes, sent: list[urllib.request.Request] | None = None) -> Send:
    def send(request: urllib.request.Request, timeout: float) -> bytes:
        assert timeout == guard.CAPABILITY_LABELS_TIMEOUT_SECONDS
        if sent is not None:
            sent.append(request)
        return body

    return send


def failing(error: Exception) -> Send:
    def send(request: urllib.request.Request, timeout: float) -> bytes:
        raise error

    return send


def test_the_labels_are_read_from_infrastructure_s_main_as_raw_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    sent: list[urllib.request.Request] = []
    body = b'[{"name": "cap:stages", "color": "1D76DB"}, {"name": "cap:vcs"}]'
    assert guard.declared_labels(answering(body, sent)) == DECLARED
    (request,) = sent
    assert request.full_url == (
        "https://api.github.com/repos/troupe-run/infrastructure/contents/"
        "tofu/labels/troupe.json?ref=main"
    )
    assert request.get_header("Accept") == "application/vnd.github.raw+json"
    assert not request.has_header("Authorization")


def test_the_run_s_token_is_sent_when_there_is_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "t0ken")
    sent: list[urllib.request.Request] = []
    guard.declared_labels(answering(b"[]", sent))
    assert sent[0].get_header("Authorization") == "Bearer t0ken"


def test_a_redirect_s_request_to_another_host_carries_no_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # urlopen follows a redirect with the request redirect_request makes, which copies the
    # first request's headers (#206).
    monkeypatch.setenv("GITHUB_TOKEN", "t0ken")
    redirected: list[urllib.request.Request] = []

    def redirecting(request: urllib.request.Request, timeout: float) -> bytes:
        new = urllib.request.HTTPRedirectHandler().redirect_request(
            request,
            io.BytesIO(),
            302,
            "Found",
            http.client.HTTPMessage(),
            "https://elsewhere.example/",
        )
        assert new is not None
        redirected.append(new)
        return b"[]"

    guard.declared_labels(redirecting)
    (request,) = redirected
    assert request.full_url == "https://elsewhere.example/"
    assert not request.has_header("Authorization")


@pytest.mark.parametrize(
    ("send", "reason"),
    [
        (
            failing(
                urllib.error.HTTPError(
                    guard.CAPABILITY_LABELS_URL, 404, "Not Found", email.message.Message(), None
                )
            ),
            "GitHub answered 404 Not Found",
        ),
        (failing(TimeoutError("timed out")), "the request failed: timed out"),
        (failing(urllib.error.URLError("no route")), "the request failed: <urlopen error"),
        (answering(b"not json"), "it isn't JSON"),
        (answering(b'{"name": "cap:stages"}'), "it isn't a list of labels"),
        (answering(b'[{"name": "cap:stages"}, {"color": "1D76DB"}]'), "it isn't a list of labels"),
    ],
    ids=["http-error", "timeout", "no-connection", "not-json", "not-a-list", "entry-without-name"],
)
def test_labels_that_can_t_be_read_are_an_error_never_no_labels(send: Send, reason: str) -> None:
    with pytest.raises(guard.UnreadableLabelsError) as raised:
        guard.declared_labels(send)
    assert str(raised.value).startswith(reason)


def test_an_unreadable_labels_file_fails_the_rule_saying_to_re_run(tmp_path: Path) -> None:
    proposed_spec(tmp_path, "x", "run-workspaces", spec("Capability: `cap:stages`"))

    def unreadable() -> frozenset[str]:
        return guard.declared_labels(failing(TimeoutError("timed out")))

    decision, _ = judged(tmp_path, touching("openspec/changes/x/tasks.md"), read_labels=unreadable)
    assert decision.rule == "capability-label"
    assert decision.problem == (
        "couldn't read the declared labels, tofu/labels/troupe.json on troupe-run/infrastructure's "
        "main: the request failed: timed out."
    )
    assert decision.fix.startswith("Re-run the check.")
