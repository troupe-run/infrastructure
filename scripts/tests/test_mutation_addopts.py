"""The pytest options a mutation run gives mutmut: the repository's own `addopts`, without those
mutmut's copy can't honour (#332, #398). Moved from test_mutation_run.py at the size gate (#399)."""

from pathlib import Path

import pytest
from test_mutation_run import package_checkout

import mutation_run as run

pytestmark = pytest.mark.mutation


def write_addopts(tmp_path: Path, addopts: str) -> None:
    text = f"[tool.pytest.ini_options]\naddopts = {addopts}\n"
    (tmp_path / "pyproject.toml").write_text(text, encoding="utf-8")


def test_a_run_keeps_the_repositorys_pytest_options_but_those_the_copy_cant_honour(
    tmp_path: Path,
) -> None:
    """troupe's own plugins load; strict markers and the guard's tag plugin, which finds its
    declarations from the repository's root, don't (#332)."""
    unit = package_checkout(tmp_path)
    write_addopts(
        tmp_path,
        '["-ra", "--strict-markers", "--strict-config", "-p", "protocol_guard", '
        '"-p", "guard_pytest", "-p", "gitrepo"]',
    )
    config = run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=2)
    assert "\n    addopts=-ra --strict-config -p protocol_guard -p gitrepo\n" in config


def test_troupes_kinds_plugin_is_left_out_of_the_copy(tmp_path: Path) -> None:
    """In mutmut's copy kinds_pytest finds no suite and refuses every test (#398)."""
    unit = package_checkout(tmp_path)
    write_addopts(
        tmp_path,
        '["-ra", "--strict-markers", "-p", "protocol_guard", "-p", "guard_pytest", '
        '"-p", "kinds_pytest", "-pkinds_pytest", "-p", "hypothesis_profiles", "-p", "gitrepo"]',
    )
    config = run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=2)
    assert "\n    addopts=-ra -p protocol_guard -p hypothesis_profiles -p gitrepo\n" in config


def test_addopts_as_one_string_is_split_as_pytest_splits_it(tmp_path: Path) -> None:
    unit = package_checkout(tmp_path)
    write_addopts(tmp_path, "\"-ra --strict-markers -p guard_pytest -k 'a or b'\"")
    config = run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=2)
    assert "\n    addopts=-ra -k 'a or b'\n" in config


def test_the_joined_plugin_form_is_left_out_too(tmp_path: Path) -> None:
    unit = package_checkout(tmp_path)
    write_addopts(tmp_path, '["-ra", "-pguard_pytest", "-pgitrepo"]')
    config = run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=2)
    assert "\n    addopts=-ra -pgitrepo\n" in config


def test_no_addopts_gives_ra(tmp_path: Path) -> None:
    unit = package_checkout(tmp_path)
    config = run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=2)
    assert "\n    addopts=-ra\n" in config


def test_a_pyproject_that_isnt_toml_is_refused_naming_it(tmp_path: Path) -> None:
    unit = package_checkout(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[tool.pytest\n", encoding="utf-8")
    with pytest.raises(run.RunError, match=r"pyproject.toml isn't valid TOML"):
        run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=2)


def test_addopts_of_another_type_is_refused_naming_it(tmp_path: Path) -> None:
    unit = package_checkout(tmp_path)
    write_addopts(tmp_path, "3")
    with pytest.raises(run.RunError, match=r"pyproject.toml's addopts is 3; it must be"):
        run.mutmut_config(tmp_path / "packages" / "troupe", tmp_path, unit, children=2)
