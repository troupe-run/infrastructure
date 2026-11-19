"""Auto-merge's complexity measure: over the functions a change adds, or whose cyclomatic
complexity it raises, the highest complexity and the total rise (spec: auto-merge, "The change is
within the size and complexity limits"; design D2). lizard runs for real, on files taken from a
scratch git repository's commits, as the evaluator takes them from a pull request's: nothing is
checked out or run.
"""

import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

import auto_merge as am

LIZARD = shutil.which("lizard", path=str(Path(sys.executable).parent)) or "lizard"
RULES = am.Rules(
    limits=am.Limits(800, 30, 15, 40),
    generated=("**/uv.lock",),
    prose=("**/*.md",),
    complexity_exclude=("**/tests/**",),
    languages=("python", "typescript"),
    protected=(),
)


def branches(count: int, name: str = "f") -> str:
    """A function whose cyclomatic complexity is ``count`` + 1."""
    body = "".join(f"    if x == {index}:\n        return {index}\n" for index in range(count))
    return f"def {name}(x):\n{body}    return -1\n"


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def commit(repo: Path, files: Mapping[str, str | None]) -> str:
    for path, text in files.items():
        target = repo / path
        if text is None:
            target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "x")
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-q")
    return path


def measure(
    repo: Path, before: Mapping[str, str | None], after: Mapping[str, str | None]
) -> tuple[int, int]:
    base = commit(repo, before)
    head = commit(repo, after)
    return am.complexity(repo, base, head, RULES, LIZARD)


def test_a_new_function_counts_whole(repo: Path) -> None:
    assert measure(repo, {"a.py": "x = 1\n"}, {"b.py": branches(17)}) == (18, 18)


def test_an_edited_function_counts_its_rise(repo: Path) -> None:
    assert measure(repo, {"a.py": branches(2)}, {"a.py": branches(4)}) == (5, 2)


def test_an_edit_that_adds_no_branching_to_a_complex_function_counts_for_nothing(
    repo: Path,
) -> None:
    """troupe#410's shape: a line changed inside a function of complexity 25."""
    before = {"a.py": branches(24).replace("return -1", "return -1  # old")}
    after = {"a.py": branches(24).replace("return -1", "return -2  # new")}
    assert measure(repo, before, after) == (0, 0)


def test_a_function_made_simpler_counts_for_nothing(repo: Path) -> None:
    assert measure(repo, {"a.py": branches(19)}, {"a.py": branches(15)}) == (0, 0)


def test_a_function_whose_parameters_change_is_edited_not_new(repo: Path) -> None:
    before = {"a.py": branches(10)}
    after = {"a.py": branches(11).replace("def f(x):", "def f(x, y=0):")}
    assert measure(repo, before, after) == (12, 1)


def test_a_function_the_change_doesnt_touch_isnt_counted(repo: Path) -> None:
    before = {"a.py": branches(20, "old") + "\n\n" + branches(1, "small")}
    after = {"a.py": branches(20, "old") + "\n\n" + branches(2, "small")}
    assert measure(repo, before, after) == (3, 1)


def test_tests_are_left_out(repo: Path) -> None:
    assert measure(repo, {"a.py": "x = 1\n"}, {"pkg/tests/test_a.py": branches(30)}) == (0, 0)


def test_other_languages_are_left_out(repo: Path) -> None:
    assert measure(repo, {"a.py": "x = 1\n"}, {"a.go": "func f() {}\n"}) == (0, 0)


def test_typescript_is_measured(repo: Path) -> None:
    after = {"a.ts": "export function f(x: number) {\n  if (x) { return 1; }\n  return 0;\n}\n"}
    assert measure(repo, {"a.py": "x = 1\n"}, after) == (2, 2)


def test_a_similar_line_in_many_files_adds_no_branching(repo: Path) -> None:
    before = {f"m{index}.py": branches(1, f"f{index}") for index in range(40)}
    after = {f"m{index}.py": branches(1, f"f{index}") + "LIMIT = 3\n" for index in range(40)}
    assert measure(repo, before, after) == (0, 0)


def test_a_deleted_file_isnt_measured(repo: Path) -> None:
    assert measure(repo, {"a.py": branches(30)}, {"a.py": None, "b.py": "y = 2\n"}) == (0, 0)
