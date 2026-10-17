"""A saved plan holds no key (spec: state-and-apply; ephemeral-state-passphrase D2, D3).

The declaration tests read both roots' `.tf` files, so a key that stops being ephemeral fails
here, before any plan is made.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tofu import KEYS, SECRETS

ROOT = Path(__file__).resolve().parents[2]
ROOTS = {
    "tofu": sorted((ROOT / "tofu").glob("*.tf")),
    "tofu/probe": [ROOT / "tofu" / "probe" / "main.tf"],
}


def variable_block(files: list[Path], name: str) -> str | None:
    """The body of `variable "<name>" { ... }` in any of the files, or None."""
    pattern = re.compile(rf'^variable "{re.escape(name)}" \{{\n(.*?)^\}}', re.MULTILINE | re.DOTALL)
    for path in files:
        found = pattern.search(path.read_text(encoding="utf-8"))
        if found:
            return found.group(1)
    return None


def test_every_key_is_a_secret_the_wrapper_supplies() -> None:
    assert set(KEYS) <= set(SECRETS)


# Reads the `tofu` scope's files (scripts/check-paths.toml); the probe root is in no scope.
@pytest.mark.tofu
@pytest.mark.parametrize("root", sorted(ROOTS))
@pytest.mark.parametrize("key", KEYS)
def test_every_key_is_an_ephemeral_sensitive_variable_in_each_root(root: str, key: str) -> None:
    name = key.removeprefix("TF_VAR_")
    body = variable_block(ROOTS[root], name)
    assert body is not None, f"{root}: no variable {name!r}"
    assert re.search(r"^\s*ephemeral\s*=\s*true\s*$", body, re.MULTILINE), (
        f"{root}: variable {name!r} isn't ephemeral, so a saved plan would record it"
    )
    assert re.search(r"^\s*sensitive\s*=\s*true\s*$", body, re.MULTILINE), (
        f"{root}: variable {name!r} isn't sensitive"
    )


# The script, run as CI runs it, with made-up keys in the environment.
SCRIPT = ROOT / "scripts" / "plan_secrets.py"
PEM = (
    "-----BEGIN RSA PRIVATE KEY-----\nMIIEfakefakefake\nmorefakelines\n"
    "-----END RSA PRIVATE KEY-----\n"
)
VALUES = {
    "TF_VAR_github_app_pem": PEM,
    "TF_VAR_state_passphrase": "correct-horse-battery-staple-test",
    "TF_VAR_cloudflare_api_token": "cf-token-made-up-for-the-test",
}


def run(files: list[Path], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    full = {k: v for k, v in os.environ.items() if k not in VALUES}
    full.update(VALUES if env is None else env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, files)],
        env=full,
        capture_output=True,
        text=True,
        check=False,
    )


def write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def clean_plan() -> str:
    return json.dumps({"variables": {"note": {"value": "a"}}, "resource_changes": []})


def test_a_plan_without_keys_passes(tmp_path: Path) -> None:
    text = write(tmp_path, "plan.txt", "No changes. Your infrastructure matches the configuration.")
    result = run([text, write(tmp_path, "plan.json", clean_plan())])
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("key", sorted(VALUES))
def test_a_plan_holding_a_key_fails_naming_the_file_and_key(tmp_path: Path, key: str) -> None:
    plan = write(tmp_path, "plan.txt", f"  + value = {VALUES[key]}\n")
    result = run([plan])
    assert result.returncode == 1
    assert str(plan) in result.stdout
    assert key in result.stdout
    assert VALUES[key] not in result.stdout + result.stderr


def test_a_key_is_found_json_escaped(tmp_path: Path) -> None:
    plan = write(tmp_path, "plan.json", json.dumps({"variables": {"pem": {"value": PEM}}}))
    assert PEM not in plan.read_text(encoding="utf-8")  # the newlines are escaped
    result = run([plan])
    assert result.returncode == 1
    assert "TF_VAR_github_app_pem" in result.stdout
    for line in PEM.splitlines():
        if line:
            assert line not in result.stdout + result.stderr


def test_the_passphrase_among_the_variables_fails(tmp_path: Path) -> None:
    passphrase = VALUES["TF_VAR_state_passphrase"]
    plan = write(
        tmp_path,
        "plan.json",
        json.dumps({"variables": {"state_passphrase": {"value": passphrase}}}),
    )
    result = run([plan])
    assert result.returncode == 1
    assert "TF_VAR_state_passphrase" in result.stdout


@pytest.mark.parametrize("value", [None, ""])
def test_an_unset_or_empty_key_is_an_error_naming_it(tmp_path: Path, value: str | None) -> None:
    env = {k: v for k, v in VALUES.items() if k != "TF_VAR_cloudflare_api_token"}
    if value is not None:
        env["TF_VAR_cloudflare_api_token"] = value
    result = run([write(tmp_path, "plan.json", clean_plan())], env)
    assert result.returncode == 2
    assert "TF_VAR_cloudflare_api_token" in result.stderr


def test_a_missing_file_is_an_error_naming_it(tmp_path: Path) -> None:
    missing = tmp_path / "plan.json"
    result = run([missing])
    assert result.returncode == 2
    assert str(missing) in result.stderr


def test_no_file_is_a_usage_error() -> None:
    result = run([])
    assert result.returncode == 2
    assert "required: files" in result.stderr
