"""guard.yml takes Node from the repository's .nvmrc, so its delivered copy passes website's rule
(spec: guard-delivery; guard-node-version-file design D1-D3, #155).

`node_version_problems` is a copy of website's `tests/unit/workflow-node-version.test.ts` for the
steps guard.yml can have (troupe-run/website#4). Like that test, it reads only each step's `uses`
and `with`, so it ignores `if:`. website's test is the authority: the change's tasks ran it
against guard.yml."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO

GUARD = REPO / ".github" / "workflows" / "guard.yml"


def node_version_problems(file: str, workflow: dict[str, Any]) -> list[str]:
    problems = []
    for job, body in (workflow.get("jobs") or {}).items():
        for i, step in enumerate(body.get("steps") or []):
            where = (
                f'{file}, job "{job}", step {i + 1} ({step.get("uses") or step.get("id") or "run"})'
            )
            inputs = step.get("with") or {}
            action = str(step.get("uses", "")).split("@")[0]
            if action == "actions/setup-node":
                if inputs.get("node-version-file") != ".nvmrc":
                    problems.append(f"{where}: setup-node must have node-version-file: .nvmrc")
                if "node-version" in inputs:
                    problems.append(
                        f"{where}: setup-node must not have node-version "
                        f"(found {inputs['node-version']!r})"
                    )
            elif "node-version" in inputs:
                problems.append(
                    f"{where}: names its own node-version (found {inputs['node-version']!r})"
                )
    return problems


def check(text: str) -> list[str]:
    return node_version_problems("fixture.yml", yaml.safe_load(text))


def test_guard_yml_sets_up_node_only_from_nvmrc() -> None:
    workflow = yaml.safe_load(GUARD.read_text(encoding="utf-8"))
    assert node_version_problems("guard.yml", workflow) == []


def test_the_rule_accepts_setup_node_reading_nvmrc() -> None:
    assert (
        check(
            "jobs:\n  t:\n    steps:\n      - uses: actions/setup-node@v7\n"
            "        with:\n          node-version-file: .nvmrc\n"
        )
        == []
    )


def test_the_rule_refuses_a_pinned_setup_node_naming_the_job_and_step() -> None:
    assert check(
        "jobs:\n  t:\n    steps:\n      - uses: actions/checkout@v7\n"
        "      - uses: actions/setup-node@v7\n        with:\n          node-version: 22\n"
    ) == [
        'fixture.yml, job "t", step 2 (actions/setup-node@v7): setup-node must have '
        "node-version-file: .nvmrc",
        'fixture.yml, job "t", step 2 (actions/setup-node@v7): setup-node must not have '
        "node-version (found 22)",
    ]


def test_the_rule_refuses_a_pinned_setup_node_behind_an_if() -> None:
    assert check(
        "jobs:\n  t:\n    steps:\n      - uses: actions/setup-node@v7\n"
        "        if: hashFiles('.nvmrc') == ''\n        with:\n          node-version: 22\n"
    ) == [
        'fixture.yml, job "t", step 1 (actions/setup-node@v7): setup-node must have '
        "node-version-file: .nvmrc",
        'fixture.yml, job "t", step 1 (actions/setup-node@v7): setup-node must not have '
        "node-version (found 22)",
    ]


def test_the_rule_refuses_a_node_version_input_on_another_step() -> None:
    assert check(
        "jobs:\n  t:\n    steps:\n      - uses: some/other-action@v1\n"
        "        with:\n          node-version: '24'\n"
    ) == [
        'fixture.yml, job "t", step 1 (some/other-action@v1): names its own node-version '
        "(found '24')"
    ]


def guard_steps() -> list[dict[str, Any]]:
    workflow = yaml.safe_load(GUARD.read_text(encoding="utf-8"))
    steps: list[dict[str, Any]] = workflow["jobs"]["guard"]["steps"]
    return steps


def choose_step() -> tuple[int, dict[str, Any]]:
    for i, step in enumerate(guard_steps()):
        if step.get("name") == "Choose the Node version":
            return i, step
    raise AssertionError("guard.yml has no 'Choose the Node version' step")


def test_the_node_version_is_chosen_before_node_is_set_up() -> None:
    chosen, _ = choose_step()
    setups = [
        i
        for i, step in enumerate(guard_steps())
        if str(step.get("uses", "")).startswith("actions/setup-node@")
    ]
    assert setups
    assert chosen < setups[0]


def pinned_node_version() -> str:
    workflow = yaml.safe_load(GUARD.read_text(encoding="utf-8"))
    return str(workflow["jobs"]["guard"]["env"]["NODE_VERSION"])


def run_choose_step(directory: Path) -> subprocess.CompletedProcess[str]:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash isn't on PATH")
    _, step = choose_step()
    return subprocess.run(
        [bash, "-e", "-c", step["run"]],
        cwd=directory,
        env={**os.environ, "NODE_VERSION": pinned_node_version()},
        capture_output=True,
        text=True,
        check=True,
    )


def test_with_no_nvmrc_the_pin_is_written_to_nvmrc(tmp_path: Path) -> None:
    result = run_choose_step(tmp_path)
    assert (tmp_path / ".nvmrc").read_bytes() == f"{pinned_node_version()}\n".encode()
    assert "the guard's pin" in result.stdout


def test_a_repository_s_nvmrc_is_left_byte_for_byte_unchanged(tmp_path: Path) -> None:
    (tmp_path / ".nvmrc").write_bytes(b"22\r\n")
    result = run_choose_step(tmp_path)
    assert (tmp_path / ".nvmrc").read_bytes() == b"22\r\n"
    assert "from the repository's .nvmrc" in result.stdout
