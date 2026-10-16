"""Running the check turns the git hooks on by default (spec: development-workflow)."""

import os
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import Repo, git

import check


def hooks_path(repo: Repo) -> str:
    return git(repo.path, "config", "--get", "core.hooksPath", check=False).stdout.strip()


def test_the_check_turns_the_hooks_on_in_a_fresh_clone_and_says_so(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    assert hooks_path(repo) == ""
    notice = check.activate_git_hooks(repo.path)
    assert hooks_path(repo) == ".githooks"
    assert notice is not None
    assert "Activated the repository's git hooks" in notice


def test_a_second_run_changes_nothing_and_says_nothing(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    check.activate_git_hooks(repo.path)
    assert check.activate_git_hooks(repo.path) is None
    assert hooks_path(repo) == ".githooks"


def test_a_directory_that_isn_t_a_git_checkout_is_left_alone(tmp_path: Path) -> None:
    assert check.activate_git_hooks(tmp_path) is None


@pytest.mark.skipif(os.name == "nt", reason="Git for Windows has no executable bit")
@pytest.mark.parametrize("gates_result", [0, 1])
def test_the_check_names_a_hook_git_skips_and_its_result_is_the_gates_alone(
    make_repo: Callable[[], Repo],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    gates_result: int,
) -> None:
    repo = make_repo()
    repo.write(".githooks/pre-push", "#!/bin/sh\nexit 0\n")
    (repo.path / ".githooks" / "pre-push").chmod(0o644)
    ran: list[Path] = []

    def run_gates(steps: object, cwd: Path, scopes: object = ()) -> int:
        ran.append(cwd)
        return gates_result

    monkeypatch.setattr(check, "ROOT", repo.path)
    monkeypatch.setattr(check, "run_gates", run_gates)
    assert check.main([]) == gates_result
    assert ran == [repo.path]
    assert "Git skips .githooks/pre-push: it isn't executable." in capsys.readouterr().out
