# Source: troupe-run/infrastructure. Change it there; copies in other repositories are delivered.
"""pytest plugin: each test's markers must cover what it reads (spec: development-workflow).

Load it from the repository's root conftest.py, with scripts/ on the path:

    pytest_plugins = ["guard_pytest"]

It reads scripts/check-paths.toml, registers each scope as a marker (so --strict-markers accepts
them and the declaration is the one list), and records every file inside the repository that a
test opens during its setup, call and teardown, through Python's `open` audit event. A test that
reads a skipped path, or a scope's path without that scope's marker, then fails at teardown with
the guard's message. The rule itself is guard.tag_violations, which takes plain data so another
runner's adapter can use it too (commit-check-paths design D9).

Reads made by a subprocess the test starts aren't seen: the hook watches this process only.
"""

from __future__ import annotations

import contextlib
import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard

_ROOT: str | None = None
_DECLARATION: guard.CheckPaths | None = None
_READS: set[str] | None = None
"""The current test's reads, or None between tests, when nothing is recorded."""


def _record(event: str, args: tuple[object, ...]) -> None:
    """The audit hook. It must never raise: an exception here would fail the open itself."""
    if event != "open" or _READS is None or _ROOT is None:
        return
    with contextlib.suppress(Exception):
        path = args[0]
        if not isinstance(path, str | os.PathLike):
            return  # a file descriptor, or bytes
        real = os.path.realpath(os.fspath(path))
        if real == _ROOT or not real.startswith(_ROOT + os.sep):
            return
        _READS.add(Path(os.path.relpath(real, _ROOT)).as_posix())


def pytest_configure(config: pytest.Config) -> None:
    global _ROOT, _DECLARATION
    root = Path(config.rootpath)
    text = guard.read_working_tree(root)(guard.CHECK_PATHS)
    if text is None:
        return
    try:
        _DECLARATION = guard.check_paths(text)
    except guard.CheckPathsError as error:
        raise pytest.UsageError(error.decision().text()) from None
    for name, entries in _DECLARATION.scopes:
        config.addinivalue_line(
            "markers", f"{name}: reads {', '.join(entries)} ({guard.CHECK_PATHS})"
        )
    _ROOT = os.path.realpath(root)
    sys.addaudithook(_record)  # one per process; it can't be removed, so it checks _READS


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    global _READS
    if _DECLARATION is not None:
        _READS = set()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    global _READS
    report = yield
    if call.when != "teardown" or _READS is None or _DECLARATION is None:
        return report
    reads, _READS = frozenset(_READS), None
    test = guard.TestReads(
        test=item.nodeid, tags=frozenset(mark.name for mark in item.iter_markers()), reads=reads
    )
    found = guard.tag_violations(test, _DECLARATION)
    if found and report.outcome != "failed":
        report.outcome = "failed"
        report.longrepr = "\n".join(f"guard: {violation}" for violation in found)
    return report
