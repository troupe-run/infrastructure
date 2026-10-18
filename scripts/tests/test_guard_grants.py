"""What the guard's hook grants: plain gh reads and everyday writes, only from the reviewed guard
(spec: development-workflow; guard-grants-gh design D1-D4)."""

import os
import tempfile
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import Repo, git

import guard

# What is granted (D1)


def test_every_granted_command_is_on_the_allow_list() -> None:
    assert guard.GH_GRANTED <= guard.GH_READS | guard.GH_WORKFLOW_WRITES


def test_merging_checking_out_and_running_workflows_are_not_granted() -> None:
    not_granted = {
        ("pr", "merge"),
        ("pr", "checkout"),
        ("workflow", "run"),
        ("run", "rerun"),
        ("run", "cancel"),
    }
    assert guard.GH_GRANTED & not_granted == set()


def test_the_everyday_housekeeping_writes_are_granted() -> None:
    assert {("pr", "ready"), ("issue", "edit"), ("issue", "comment")} <= guard.GH_GRANTED


def test_reads_that_write_local_files_anywhere_are_not_granted() -> None:
    assert guard.GH_GRANTED & {("run", "download"), ("repo", "clone")} == set()


# Only plain commands are granted (D2)


@pytest.mark.parametrize(
    "command",
    [
        "gh pr ready 74",
        "gh issue edit 29 --type Feature",
        "gh issue edit 29 --add-blocked-by 63",
        'gh issue comment 1 --body "Fix #3, see https://example.com/?q=a"',
        "gh pr view 17 --json comments --jq '.comments[] | .body'",
        "gh issue list -R troupe-run/troupe --search 'is:open label:cap:runs'",
        "gh pr ready 74 -R troupe-run/infrastructure",
    ],
)
def test_a_plain_granted_gh_command_is_granted(command: str, tmp_path: Path) -> None:
    assert guard.grantable(command, tmp_path, tmp_path)


@pytest.mark.parametrize(
    "command",
    [
        "gh pr merge 32 --rebase",
        "gh pr checkout 32",
        "gh workflow run tofu.yml",
        "gh run rerun 123",
        "gh run download 123 -D out",
        "gh repo clone troupe-run/troupe",
        "gh api repos/troupe-run/troupe",
        "gh repo delete troupe-run/infra-probe-x --yes",
        "gh label create x -R troupe-run/infra-probe-x",
        "gh auth status --show-token",
        "gh pr create --title t --body 'no closing reference'",
        "gh my-extension run",
        "gh",
        "gh pr",
    ],
)
def test_a_command_outside_the_grant_or_refused_is_not_granted(
    command: str, tmp_path: Path
) -> None:
    assert not guard.grantable(command, tmp_path, tmp_path)


@pytest.mark.parametrize(
    "command",
    [
        "gh pr ready 74 && rm -rf build",
        "gh pr ready 74; ls",
        "gh pr ready 74 | cat",
        "gh pr ready 74 &",
        "gh pr ready 74\nrm -rf build",
        'gh issue comment 1 --body "$(cat notes)"',
        'gh issue comment 1 --body "`id`"',
        'gh issue comment 1 --body "$HOME"',
        "gh issue comment 1 --body $HOME",
        "GH_TOKEN=x gh pr ready 74",
        "/usr/local/bin/gh pr ready 74",
        "command gh pr ready 74",
        "gh pr ready 74 > out",
        "gh pr ready 74 2>/dev/null",
        "gh issue comment 1 --body-file - <<'EOF'\nbody\nEOF",
        "gh issue comment 1 --body-file notes*",
        "gh issue comment 1 --body-file ~/notes.md",
        "gh pr ready 74 # comment",
        "(gh pr ready 74)",
        "gh pr ready \\74",
        "gh issue comment 1 --body 'unbalanced",
    ],
)
def test_a_gh_command_with_shell_syntax_is_not_granted(command: str, tmp_path: Path) -> None:
    assert not guard.grantable(command, tmp_path, tmp_path)


def test_a_body_file_inside_the_repository_is_granted(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "notes").mkdir(parents=True)
    (repo / "notes" / "body.md").write_text("Closes #1\n", encoding="utf-8")
    assert guard.grantable("gh issue comment 1 --body-file notes/body.md", repo, repo)
    assert guard.grantable("gh issue comment 1 -F notes/body.md", repo, repo)


def test_a_body_file_under_the_temp_directory_is_granted(tmp_path: Path) -> None:
    body = Path(tempfile.gettempdir()) / f"grant-test-{os.getpid()}.md"
    body.write_text("text\n", encoding="utf-8")
    try:
        # Quoted, as a Windows path must be: an unquoted backslash is a shell escape.
        command = f'gh issue comment 1 --body-file "{body}"'
        assert guard.grantable(command, tmp_path / "elsewhere", tmp_path / "elsewhere")
    finally:
        body.unlink()


def test_an_unquoted_windows_path_is_not_granted(tmp_path: Path) -> None:
    command = "gh issue comment 1 --body-file C:\\Users\\me\\body.md"
    assert not guard.grantable(command, tmp_path, tmp_path)


@pytest.mark.parametrize(
    "flag",
    ["--body-file /etc/hosts", "-F /etc/hosts", "--body-file=/etc/hosts", "--body-file -"],
)
def test_a_body_file_outside_the_repository_and_temp_directory_is_not_granted(
    flag: str, tmp_path: Path
) -> None:
    assert not guard.grantable(f"gh issue comment 1 {flag}", tmp_path, tmp_path)


def test_a_body_file_under_the_home_directory_is_not_granted(tmp_path: Path) -> None:
    secret = Path.home() / ".ssh" / "id_ed25519"
    assert not guard.grantable(f"gh issue comment 1 --body-file {secret}", tmp_path, tmp_path)


def test_a_symlink_inside_the_repository_to_a_file_outside_is_not_granted(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "body.md").symlink_to("/etc/hosts")
    assert not guard.grantable("gh issue comment 1 --body-file body.md", repo, repo)


# An attachment is a file read (refuse-substituted-pr-body design D6): gh uploads it, and reads the
# whole value or a part before a '#', whichever exists when it runs.

ATTACHING_COMMANDS = [
    "gh issue comment 1",
    "gh pr comment 1",
    "gh issue create --title t",
    "gh pr create --title t",
    "gh issue edit 1",
    "gh pr edit 1",
]


@pytest.mark.parametrize("command", ATTACHING_COMMANDS)
def test_an_attachment_from_outside_the_repository_is_not_granted(
    command: str, tmp_path: Path
) -> None:
    full = f"{command} --body 'Closes #1' --attach /etc/hosts"
    assert not guard.grantable(full, tmp_path, tmp_path)


UP = "../" * 40  # out of the test's repository and the temp directory it sits in, to /


@pytest.mark.parametrize(
    "flag",
    [
        "--attach=/etc/hosts",
        f"--attach '{UP}etc/hosts#alt'",
        f"--attach 'shot.png#x/{UP}etc/hosts'",  # the part before '#' is inside; the whole isn't
        "--attach ''",
    ],
)
def test_an_attachment_any_reading_of_which_is_outside_is_not_granted(
    flag: str, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert not guard.grantable(f"gh issue comment 1 --body x {flag}", repo, repo)


@pytest.mark.parametrize("flag", ["--attach shot.png", "--attach 'docs/shot.png#The new page'"])
def test_an_attachment_inside_the_repository_is_granted(flag: str, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert guard.grantable(f"gh issue comment 1 --body x {flag}", repo, repo)


def test_an_attachment_under_the_temp_directory_is_granted(tmp_path: Path) -> None:
    shot = Path(tempfile.gettempdir()) / f"grant-test-{os.getpid()}.png"
    command = f'gh issue comment 1 --body x --attach "{shot}#A screenshot"'
    assert guard.grantable(command, tmp_path / "elsewhere", tmp_path / "elsewhere")


# Only the reviewed guard grants (D3)


def with_origin_main(repo: Repo, guard_text: str | None) -> Path:
    """Commit a scripts/guard.py (or none) and point origin/main at that commit."""
    if guard_text is not None:
        repo.write("scripts/guard.py", guard_text)
        git(repo.path, "add", "-A")
        git(repo.path, "commit", "-q", "-m", "chore: add the guard")
    git(repo.path, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repo.path / "scripts" / "guard.py"


def test_a_guard_identical_to_origin_main_is_reviewed(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    running = with_origin_main(repo, "print('guard')\n")
    assert guard.guard_is_reviewed(repo.path, running)


def test_a_guard_edited_since_origin_main_is_not_reviewed(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    running = with_origin_main(repo, "print('guard')\n")
    running.write_text("print('edited')\n", encoding="utf-8")
    assert not guard.guard_is_reviewed(repo.path, running)


def test_no_origin_main_means_not_reviewed(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    running = repo.write("scripts/guard.py", "print('guard')\n")
    assert not guard.guard_is_reviewed(repo.path, running)


def test_origin_main_without_the_guard_means_not_reviewed(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    with_origin_main(repo, None)
    running = repo.write("scripts/guard.py", "print('guard')\n")
    assert not guard.guard_is_reviewed(repo.path, running)
