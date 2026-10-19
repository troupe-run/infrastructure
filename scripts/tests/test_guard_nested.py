"""The rules reach every git and gh command a shell line runs (spec: development-workflow, "The
rules reach every command a shell line runs"; read-nested-commands design D1-D6).

The reader is checked against real shells, not only against itself (design D6): stub `gh` and
`git` programs, first on PATH, record each run's arguments and do nothing else, so no real git or
gh command runs."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SHELL_NAMES = ("bash", "zsh")
PROGRAMS = ("gh", "git")
SEPARATOR = "\x1f"
STUB = """#!/bin/sh
{{
  printf '%s' "{name}"
  for a in "$@"; do printf '\\037%s' "$a"; done
  printf '\\n'
}} >> "$STUB_LOG"
"""


def _shell(name: str) -> str | None:
    found = shutil.which(name)
    # On Windows, System32's bash.exe starts WSL, not Git Bash: a different machine's programs.
    if found is None or "system32" in found.lower():
        return None
    return found


SHELLS = [name for name in SHELL_NAMES if _shell(name)]
needs_bash = pytest.mark.skipif(_shell("bash") is None, reason="no bash on this machine")


class Stubs:
    """A directory of stub gh and git programs, and the log they write."""

    def __init__(self, root: Path) -> None:
        self.bin = root / "bin"
        self.bin.mkdir()
        self.log = root / "ran.log"
        self.cwd = root / "work"
        self.cwd.mkdir()
        for name in PROGRAMS:
            stub = self.bin / name
            stub.write_text(STUB.format(name=name), encoding="utf-8", newline="\n")
            stub.chmod(0o755)

    def run(self, command: str, shell: str) -> list[list[str]]:
        """The git and gh commands `shell` ran for `command`, in order, as argument lists."""
        self.log.write_text("", encoding="utf-8")
        executable = _shell(shell)
        assert executable is not None
        env = dict(os.environ)
        env["PATH"] = f"{self.bin}{os.pathsep}{env.get('PATH', '')}"
        env["STUB_LOG"] = str(self.log)
        # zsh -f skips the user's startup files, which could put the real programs first on PATH.
        flags = ["-f"] if shell == "zsh" else []
        subprocess.run(
            [executable, *flags, "-c", command],
            cwd=self.cwd,
            env=env,
            capture_output=True,
            timeout=30,
            check=False,
        )
        lines = self.log.read_text(encoding="utf-8").splitlines()
        return [line.split(SEPARATOR) for line in lines]


@pytest.fixture
def stubs(tmp_path: Path) -> Stubs:
    return Stubs(tmp_path)


# Task 2.1: the harness runs the stubs, and only the stubs


@needs_bash
@pytest.mark.parametrize("shell", SHELLS)
def test_the_stubs_record_each_git_and_gh_command_the_shell_runs(stubs: Stubs, shell: str) -> None:
    ran = stubs.run("gh auth token; git status --short 'a b'", shell)
    assert ran == [["gh", "auth", "token"], ["git", "status", "--short", "a b"]]
