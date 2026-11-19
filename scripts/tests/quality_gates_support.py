"""What the quality gates' tests share: the config they start from, the captured tool output, and
scratch git repositories (spec: quality-gates). Imported by test_guard_quality_gates.py and
test_guard_quality_audit.py, which import the fixtures too so pytest finds them.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "quality-gates"
LIZARD = shutil.which("lizard", path=str(Path(sys.executable).parent)) or "lizard"

CONFIG = """\
version = 1

[coverage]
floor = 80.0
tolerance = 0.5

[coverage.packages.core]
paths = ["packages/core/src"]
baseline = 90.0

[coverage.packages.plugin]
paths = ["plugins/plugin"]

[complexity]
block_above = 5
languages = ["python", "typescript"]
exclude = ["**/tests/**"]

[audit]
lock_files = ["uv.lock"]
block = ["high", "critical"]
"""


def fixture(name: str) -> dict[str, object]:
    data: dict[str, object] = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return data


@pytest.fixture(autouse=True)
def no_inherited_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tests may run inside a real pre-commit hook, whose GIT_* variables name this repo."""
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "commit.gpgsign", "false")
    (tmp_path / "quality-gates.toml").write_text(CONFIG, encoding="utf-8")
    return tmp_path


def commit(repo: Path, files: dict[str, str], message: str = "change") -> str:
    for path, text in files.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", message)
    return git(repo, "rev-parse", "HEAD")
