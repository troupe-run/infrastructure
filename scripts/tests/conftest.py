"""Shared helpers for the guard tests: temporary git repositories shaped like this one."""

import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import plan_target  # noqa: E402 (after the path it's found on)

PASSING_CHECK = 'print("check: all gates passed")\n'
FAILING_CHECK = (
    'import sys\nprint("check: mypy --strict failed (exit 1) after 0.1s")\nsys.exit(1)\n'
)


def clean_env() -> dict[str, str]:
    """No inherited repository-location variables: tests may run inside a real pre-commit hook."""
    import guard

    return guard._git_env()


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=check, env=clean_env()
    )


class Repo:
    """A throwaway repository with this repo's guard script and git hooks copied in."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, relative: str, text: str) -> Path:
        target = self.path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def change(
        self, name: str, *, archived_on: str | None = None, tasks: str = "- [x] 1.1 done\n"
    ) -> Path:
        base = (
            f"openspec/changes/archive/{archived_on}-{name}"
            if archived_on
            else f"openspec/changes/{name}"
        )
        return self.write(f"{base}/tasks.md", tasks).parent

    def switch(self, branch: str) -> None:
        git(self.path, "switch", "-q", "-c", branch)

    def commit(self, message: str, *paths: str) -> subprocess.CompletedProcess[str]:
        git(self.path, "add", *(paths or ("-A",)))
        return git(self.path, "commit", "-q", "-m", message, check=False)

    def head(self) -> str:
        return git(self.path, "rev-parse", "HEAD").stdout.strip()

    def hooks_on(self, check_script: str = PASSING_CHECK) -> None:
        shutil.copytree(REPO / ".githooks", self.path / ".githooks")
        self.write("scripts/guard.py", (SCRIPTS / "guard.py").read_text(encoding="utf-8"))
        self.write("scripts/check.py", check_script)
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", "chore: add the guard")
        git(self.path, "config", "core.hooksPath", ".githooks")


@pytest.fixture
def make_repo(tmp_path: Path) -> Callable[[], Repo]:
    counter = iter(range(1000))

    def make() -> Repo:
        path = tmp_path / f"repo{next(counter)}"
        path.mkdir()
        git(path, "init", "-q", "-b", "main")
        git(path, "config", "user.email", "tester@example.com")
        git(path, "config", "user.name", "Tester")
        git(path, "config", "commit.gpgsign", "false")
        repo = Repo(path)
        repo.write("README.md", "test\n")
        git(path, "add", "-A")
        git(path, "commit", "-q", "-m", "chore: initial")
        return repo

    return make


STATE_PATH = plan_target.STATE_PATH
# The App's bot, which commits the state after each apply (tofu.yml's STATE_AUTHOR).
STATE_APP = "340938853+troupe-run-infrastructure[bot]@users.noreply.github.com"


class History:
    """A repository shaped like main's history: merges by a person, and the App's state commits,
    which change only the state file (plan_target.py, main_ci.py)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.mkdir()
        git(path, "init", "-q", "-b", "main")
        git(path, "config", "user.email", "tester@example.com")
        git(path, "config", "user.name", "Tester")
        git(path, "config", "commit.gpgsign", "false")
        self.state = 0
        self.declaration = 0
        self.write(STATE_PATH, "state 0")
        self.write("tofu/main.tf", "declaration 0")
        git(path, "add", "-A")
        git(path, "commit", "-q", "-m", "chore: start")

    def write(self, relative: str, text: str) -> None:
        target = self.path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")

    def head(self) -> str:
        return git(self.path, "rev-parse", "HEAD").stdout.strip()

    def merge(self, *, state: bool = False) -> str:
        """A merged pull request: the declaration changes, and with `state`, the state too
        (a break-glass apply)."""
        self.declaration += 1
        self.write("tofu/main.tf", f"declaration {self.declaration}")
        if state:
            self.state += 1
            self.write(STATE_PATH, f"state {self.state}")
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", f"feat: merge {self.declaration}")
        return self.head()

    def apply(self) -> str:
        """The App's state commit after an apply: only the state file, by the App's bot."""
        self.state += 1
        self.write(STATE_PATH, f"state {self.state}")
        git(self.path, "add", STATE_PATH)
        # --author, not user.email: under a commit hook, git's GIT_AUTHOR_* would win over config.
        git(
            self.path,
            "commit",
            "-q",
            f"--author=troupe-run-infrastructure[bot] <{STATE_APP}>",
            "-m",
            "chore(tofu): commit the state after applying x",
        )
        return self.head()

    def state_only(self) -> str:
        """A person's commit changing only the state file: a break-glass state merge."""
        self.state += 1
        self.write(STATE_PATH, f"state {self.state}")
        git(self.path, "add", STATE_PATH)
        git(self.path, "commit", "-q", "-m", "chore: hand-made state")
        return self.head()


@pytest.fixture
def history(tmp_path: Path) -> History:
    """main's history: merges by a person, and the App's state commits."""
    return History(tmp_path / "repo")
