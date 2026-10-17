"""The tofu wrapper: secrets from the environment, from 1Password, or a refusal.

Spec: state-and-apply. End-to-end tests put a fake `tofu` and `op` on the PATH; each records
how it was called.
"""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "scripts" / "tofu.py"
SECRETS = {
    "TF_VAR_github_app_pem": "pem",
    "TF_VAR_state_passphrase": "pass",
    "TF_VAR_billing_email": "a@b.c",
    "TF_VAR_cloudflare_api_token": "cf",
}

# A fake tool: records its name, arguments and the App/secret environment to $CALLS, then
# runs the rest of its arguments after "--" (so a fake `op run -- tofu` reaches the fake tofu).
FAKE = """#!{python}
import json, os, subprocess, sys
name = os.path.basename(sys.argv[0])
keys = ["OP_ACCOUNT", "TF_VAR_github_app_pem", "TF_VAR_state_passphrase", "TF_VAR_billing_email",
        "TF_VAR_cloudflare_api_token"]
with open(os.environ["CALLS"], "a") as f:
    f.write(json.dumps({{"tool": name, "args": sys.argv[1:],
                        "env": {{k: os.environ.get(k) for k in keys}}}}) + "\\n")
if "--" in sys.argv:
    rest = sys.argv[sys.argv.index("--") + 1:]
    sys.exit(subprocess.run(rest).returncode)
"""


# The wrapper only runs on the owner's machine and Linux CI; the fakes are shebang scripts.
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="fake tools are shebang scripts")


def install_fake(bin_dir: Path, name: str) -> None:
    path = bin_dir / name
    path.write_text(FAKE.format(python=sys.executable))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def run(
    tmp_path: Path, tools: list[str], secrets: dict[str, str]
) -> tuple[int, str, list[dict[str, Any]]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in tools:
        install_fake(bin_dir, tool)
    calls = tmp_path / "calls.jsonl"
    env = {k: v for k, v in os.environ.items() if k not in SECRETS and k != "OP_ACCOUNT"}
    env.update(secrets)
    env["PATH"] = str(bin_dir)
    env["CALLS"] = str(calls)
    result = subprocess.run(
        [sys.executable, str(WRAPPER), "plan"], env=env, capture_output=True, text=True, check=False
    )
    lines = calls.read_text().splitlines() if calls.exists() else []
    return result.returncode, result.stderr, [json.loads(line) for line in lines]


def test_secrets_in_the_environment_run_tofu_without_op(tmp_path: Path) -> None:
    code, _, calls = run(tmp_path, ["tofu", "op"], SECRETS)
    assert code == 0
    assert [c["tool"] for c in calls] == ["tofu"]
    assert calls[0]["args"] == [f"-chdir={ROOT / 'tofu'}", "plan"]
    assert calls[0]["env"]["TF_VAR_github_app_pem"] == "pem"


def test_missing_secrets_run_tofu_under_op_run_with_the_references_file(tmp_path: Path) -> None:
    code, _, calls = run(tmp_path, ["tofu", "op"], {})
    assert code == 0
    assert [c["tool"] for c in calls] == ["op", "tofu"]
    assert calls[0]["args"][:3] == ["run", f"--env-file={ROOT / 'tofu' / 'secrets.env'}", "--"]
    assert calls[1]["args"] == [f"-chdir={ROOT / 'tofu'}", "plan"]


def test_one_missing_secret_is_enough_to_use_op(tmp_path: Path) -> None:
    partial = {k: v for k, v in SECRETS.items() if k != "TF_VAR_state_passphrase"}
    _, _, calls = run(tmp_path, ["tofu", "op"], partial)
    assert calls[0]["tool"] == "op"


def test_missing_secret_without_op_stops_before_tofu_and_names_it(tmp_path: Path) -> None:
    partial = {k: v for k, v in SECRETS.items() if k != "TF_VAR_github_app_pem"}
    code, stderr, calls = run(tmp_path, ["tofu"], partial)
    assert code != 0
    assert calls == []
    assert "TF_VAR_github_app_pem" in stderr
    assert "TF_VAR_state_passphrase" not in stderr


def test_op_runs_in_the_configured_account(tmp_path: Path) -> None:
    _, _, calls = run(tmp_path, ["tofu", "op"], {})
    assert calls[0]["env"]["OP_ACCOUNT"] == "l-a-u.1password.com"


def test_no_tofu_on_the_path_is_refused(tmp_path: Path) -> None:
    code, stderr, calls = run(tmp_path, ["op"], SECRETS)
    assert code != 0
    assert calls == []
    assert "tofu is not on the PATH" in stderr


def test_missing_cloudflare_token_without_op_stops_before_tofu_and_names_it(tmp_path: Path) -> None:
    partial = {k: v for k, v in SECRETS.items() if k != "TF_VAR_cloudflare_api_token"}
    code, stderr, calls = run(tmp_path, ["tofu"], partial)
    assert code != 0
    assert calls == []
    assert "TF_VAR_cloudflare_api_token" in stderr


def test_the_references_file_names_every_secret_the_wrapper_needs() -> None:
    names = {
        line.split("=", 1)[0]
        for line in (ROOT / "tofu" / "secrets.env").read_text().splitlines()
        if line and not line.startswith("#")
    }
    assert names == set(SECRETS)
