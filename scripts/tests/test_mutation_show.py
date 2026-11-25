"""Survivors' diffs come from one render per unit by mutmut's own interpreter, not a `mutmut show`
per mutant (#404, mutation-survivor-diffs design D1, D2). mutmut isn't installed here: the render
is faked, and mutation_locator_check.py's `show-equal` checks it against real `mutmut show`."""

import io
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

import mutation_locator_check as lc
import mutation_report as mr
import mutation_run as run
import mutation_show as ms_

pytestmark = pytest.mark.mutation


def meta(root: Path, path: str, codes: dict[str, int | None]) -> None:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / path).write_text("def f():\n    return 1\n", encoding="utf-8")
    file = root / "mutants" / f"{path}.meta"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps({"exit_code_by_key": codes}), encoding="utf-8")


def test_only_survivors_and_crashes_are_shown_file_by_file_and_never_the_tests(
    tmp_path: Path,
) -> None:
    meta(tmp_path, "src/a.py", {"a.x_f__mutmut_1": 0, "a.x_f__mutmut_2": 1, "a.x_f__mutmut_3": -11})
    meta(
        tmp_path,
        "src/b.py",
        {"b.x_f__mutmut_1": None, "b.x_f__mutmut_2": 33, "b.x_f__mutmut_3": 36},
    )
    meta(tmp_path, "src/tests/t.py", {"t.x_f__mutmut_1": 0})
    assert mr.to_show(tmp_path, "src", skip=("src/tests/",)) == {
        "src/a.py": ["a.x_f__mutmut_1", "a.x_f__mutmut_3"]
    }


class Done:
    def __init__(self, code: int, stdout: str) -> None:
        self.returncode, self.stdout, self.stderr = code, stdout, "a traceback"


def rendering(monkeypatch: pytest.MonkeyPatch, result: Done | Exception) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_run(args: list[str], **kwargs: Any) -> Done:  # noqa: ANN401
        calls.append({"args": args, **kwargs})
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


WANTED = {"src/a.py": ["a.x_f__mutmut_1", "a.x_f__mutmut_3"]}


def test_one_render_by_the_interpreter_beside_mutmut_shows_every_wanted_mutant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = {"a.x_f__mutmut_1": "# a.x_f__mutmut_1: survived\n-x\n+y\n", "a.x_f__mutmut_3": "z\n"}
    calls = rendering(monkeypatch, Done(0, json.dumps(out)))
    assert run.shown(tmp_path, "/venv/bin/mutmut", WANTED) == out
    [call] = calls
    assert call["args"] == ["/venv/bin/python", str(run.SHOW)]
    assert (call["cwd"], json.loads(call["input"])) == (tmp_path, WANTED)


def test_nothing_to_show_starts_no_render(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = rendering(monkeypatch, Done(0, "{}"))
    assert run.shown(tmp_path, "/venv/bin/mutmut", {}) == {}
    assert calls == []


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (Done(1, "Traceback"), r"mutation_show\.py failed \(exit 1\)"),
        (Done(0, "not json"), r"mutation_show\.py's output isn't JSON"),
        (Done(0, "[]"), r"mutation_show\.py's output isn't an object"),
        (Done(0, json.dumps({"a.x_f__mutmut_1": "d"})), r"left out a\.x_f__mutmut_3"),
        (FileNotFoundError("python"), r"/venv/bin/python can't run mutation_show\.py"),
    ],
)
def test_a_render_that_fails_or_leaves_one_out_is_an_error_never_a_blank_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, result: Done | Exception, message: str
) -> None:
    rendering(monkeypatch, result)
    with pytest.raises(run.RunError, match=message):
        run.shown(tmp_path, "/venv/bin/mutmut", WANTED)


@pytest.mark.parametrize("given", ["[]", '{"src/a.py": "a.x_f__mutmut_1"}', '{"src/a.py": [1]}'])
def test_the_renderer_refuses_a_request_that_isnt_paths_to_names(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], given: str
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(given))
    assert ms_.main() == 2
    assert "stdin must be an object of path to a list of mutant names" in capsys.readouterr().out


def test_the_equality_check_takes_the_survivors_from_a_ci_report_by_mutmuts_paths(
    tmp_path: Path,
) -> None:
    """show-equal marks only what a CI run reported, so no mutant is ever run to get results."""
    report = tmp_path / "report-troupe.json"
    survivor = {"line": 1, "change": "-a\n+b"}
    modules = {
        "troupe.cli": {"survivors": [
            {**survivor, "name": "troupe.cli.x_main__mutmut_1",
             "path": "packages/troupe/src/troupe/cli/__init__.py"},
        ]},
        "troupe_vcs_git": {"survivors": [
            {**survivor, "name": "troupe_vcs_git.x_f__mutmut_2",
             "path": "packages/troupe-vcs-git/src/troupe_vcs_git/__init__.py"},
        ]},
    }  # fmt: skip
    report.write_text(json.dumps({"modules": modules}), encoding="utf-8")
    assert lc.survivors_of(report, "packages/troupe/src") == {
        "src/troupe/cli/__init__.py": ["troupe.cli.x_main__mutmut_1"]
    }
