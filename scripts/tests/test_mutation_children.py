"""The mutmut plugin's per-mutant memory cap and peak records (#366, mutant-memory design D1-D3).

Each runs the plugin as mutmut's forked child loads it, in a process of its own where a cap is
set, so no cap ever lands on the test process.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import mutation_run as run

pytestmark = pytest.mark.mutation


CAPPED = """
import os, sys
sys.path.insert(0, sys.argv[1])
os.environ["MUTANT_UNDER_TEST"] = sys.argv[2]
import mutation_children
mutation_children.CONFIG = __import__("pathlib").Path(sys.argv[3])
mutation_children.pytest_configure(object())
try:
    import resource  # not on Windows, where the check's tests also run
except ImportError:
    print("limit", "none")
else:
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    print("limit", "none" if soft == resource.RLIM_INFINITY else soft // (1024 * 1024))
if len(sys.argv) > 4:
    try:
        held = bytearray(int(sys.argv[4]) * 1024 * 1024)
        print("allocated")
    except MemoryError:
        print("MemoryError")
"""


def capped(
    tmp_path: Path, mutant: str, config: object, allocate_mb: int | None = None
) -> subprocess.CompletedProcess[str]:
    """The plugin loaded in a process of its own, as mutmut's forked child loads it, so a cap
    never lands on this test process. `config` is written beside it, unless it's None."""
    path = tmp_path / "_mutation_children_plugin.json"
    if config is not None:
        path.write_text(config if isinstance(config, str) else json.dumps(config), encoding="utf-8")
    extra = [] if allocate_mb is None else [str(allocate_mb)]
    return subprocess.run(
        [sys.executable, "-c", CAPPED, str(Path(run.__file__).parent), mutant, str(path), *extra],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


LINUX_LIMITS = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="RLIMIT_AS is enforced on Linux, where CI runs"
)


@LINUX_LIMITS
def test_a_mutants_test_process_runs_under_the_cap(tmp_path: Path) -> None:
    """A runaway mutant then fails on its own instead of taking the run's cgroup down (#366, D1)."""
    done = capped(tmp_path, "troupe.core.x_f__mutmut_3", {"mutant_memory_mb": 2048, "peaks": None})
    assert done.stdout.split() == ["limit", "2048"], done.stderr


@pytest.mark.parametrize(
    ("mutant", "config"),
    [
        ("stats", {"mutant_memory_mb": 2048, "peaks": None}),
        ("none.none", {"mutant_memory_mb": 2048, "peaks": None}),
        ("", {"mutant_memory_mb": 2048, "peaks": None}),
        ("troupe.core.x_f__mutmut_3", {"mutant_memory_mb": None, "peaks": None}),
        ("troupe.core.x_f__mutmut_3", None),
    ],
)
def test_no_cap_outside_a_mutants_process_or_without_one_set(
    tmp_path: Path, mutant: str, config: object
) -> None:
    """mutmut's stats and clean passes run in its own process, which every mutant's is forked
    from: capping it would cap mutmut (D1). No file is no cap, as before this change."""
    done = capped(tmp_path, mutant, config)
    assert done.stdout.split() == ["limit", "none"], done.stderr


@pytest.mark.parametrize(
    ("config", "why"),
    [
        ("not json", "isn't JSON"),
        ("[]", "isn't an object"),
        ('{"mutant_memory_mb": "3G", "peaks": null}', "mutant_memory_mb is '3G'"),
        ('{"mutant_memory_mb": true, "peaks": null}', "mutant_memory_mb is True"),
        ('{"mutant_memory_mb": 2048}', "has no 'peaks'"),
        ('{"mutant_memory_mb": 2048, "peaks": null, "x": 1}', "has the key 'x'"),
        ('{"mutant_memory_mb": 2048, "peaks": 3}', "peaks is 3"),
    ],
)
def test_a_malformed_plugin_config_is_refused_naming_the_file(
    tmp_path: Path, config: str, why: str
) -> None:
    """A file that is there but wrong is an error, never read as no cap."""
    done = capped(tmp_path, "troupe.core.x_f__mutmut_3", config)
    assert done.returncode != 0
    assert "_mutation_children_plugin.json" in done.stderr
    assert why in done.stderr


@LINUX_LIMITS
def test_a_mutant_that_allocates_past_the_cap_gets_memory_error_and_its_parent_carries_on(
    tmp_path: Path,
) -> None:
    done = capped(
        tmp_path, "troupe.core.x_f__mutmut_3", {"mutant_memory_mb": 1024, "peaks": None}, 2048
    )
    assert done.stdout.split() == ["limit", "1024", "MemoryError"], done.stderr
    assert done.returncode == 0


STATUS = """Name:\tpython3
VmPeak:\t 1468004 kB
VmSize:\t 1400000 kB
VmHWM:\t  412300 kB
VmRSS:\t  400000 kB
"""


@pytest.mark.parametrize(
    ("mutant", "name"),
    [
        ("troupe.core.x_f__mutmut_3", "troupe.core.x_f__mutmut_3"),
        ("stats", "mutmut"),
        ("", "mutmut"),
    ],
)
def test_each_process_records_its_peaks_when_its_tests_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutant: str, name: str
) -> None:
    """mutmut's own passes are recorded as mutmut, a mutant's process by its mutant (#366, D3)."""
    import mutation_children as children

    status = tmp_path / "status"
    status.write_text(STATUS, encoding="utf-8")
    peaks = tmp_path / "peaks.log"
    (tmp_path / "config.json").write_text(
        json.dumps({"mutant_memory_mb": None, "peaks": str(peaks)}), encoding="utf-8"
    )
    monkeypatch.setattr(children, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(children, "STATUS", status)
    monkeypatch.setenv("MUTANT_UNDER_TEST", mutant)
    children.pytest_unconfigure(object())
    children.pytest_unconfigure(object())
    assert peaks.read_text(encoding="utf-8") == f"{name} 1468004 412300\n" * 2


@pytest.mark.parametrize("missing", ["status", "config", "peaks"])
def test_nothing_is_recorded_without_a_status_file_a_config_or_a_peaks_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    """Off Linux there's no /proc; loaded by hand there's no config (#366, D3)."""
    import mutation_children as children

    status = tmp_path / "status"
    if missing != "status":
        status.write_text(STATUS, encoding="utf-8")
    peaks = tmp_path / "peaks.log"
    config = {"mutant_memory_mb": None, "peaks": None if missing == "peaks" else str(peaks)}
    if missing != "config":
        (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(children, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(children, "STATUS", status)
    monkeypatch.setenv("MUTANT_UNDER_TEST", "troupe.core.x_f__mutmut_3")
    children.pytest_unconfigure(object())
    assert not peaks.exists()


def test_the_plugin_type_checks_as_windows_sees_it() -> None:
    """troupe's Windows legs run mypy --strict over the delivered plugin: a POSIX-only module used
    without narrowing on sys.platform failed all four of them (#369, mutation-win32 design D1)."""
    from mypy import api

    repo = Path(run.__file__).resolve().parent.parent
    out, err, code = api.run(
        [
            "--config-file",
            str(repo / "pyproject.toml"),
            "--platform",
            "win32",
            str(repo / "scripts" / "mutation_children.py"),
        ]
    )
    assert code == 0, out + err
