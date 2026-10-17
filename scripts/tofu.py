"""Run OpenTofu against the org, with the App's identity and the secrets supplied at run time.

Usage: uv run scripts/tofu.py <tofu arguments>     e.g. uv run scripts/tofu.py plan

This is the only documented way to run `tofu` here (design D3, D4):
- when the secrets are already in the environment (CI), it runs `tofu` as is;
- otherwise it runs `tofu` under `op run`, which resolves the `op://` references in
  tofu/secrets.env for that one process and masks them in its output;
- with neither, it stops before contacting GitHub and says what's missing.
"""

import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOFU_DIR = ROOT / "tofu"
SECRETS_ENV = TOFU_DIR / "secrets.env"

# Supplied at run time, never committed. The billing email isn't secret, but it is personal
# data in a public repo, so it travels the same way (design D4). The Cloudflare token edits only
# troupe.run's DNS records (manage-dns-as-code design D4).
SECRETS = (
    "TF_VAR_github_app_pem",
    "TF_VAR_state_passphrase",
    "TF_VAR_billing_email",
    "TF_VAR_cloudflare_api_token",
)

# The secrets that grant something: acting as the App, editing DNS, decrypting the state. A saved
# plan, and every rendering of it, holds none of them, so each is an ephemeral variable in both
# roots and CI checks each plan for them (scripts/plan_secrets.py; ephemeral-state-passphrase D2).
# The billing email isn't one: the org resource stores it, so it can't be ephemeral.
KEYS = (
    "TF_VAR_github_app_pem",
    "TF_VAR_state_passphrase",
    "TF_VAR_cloudflare_api_token",
)

# The 1Password account holding the items in tofu/secrets.env. An OP_ACCOUNT already in the
# environment wins.
OP_ACCOUNT = "l-a-u.1password.com"


@dataclass(frozen=True)
class Refusal:
    message: str


def plan_command(
    args: list[str],
    env: Mapping[str, str],
    which: Callable[[str], str | None],
) -> list[str] | Refusal:
    """Decide how to run tofu: as is, under `op run`, or not at all."""
    tofu = which("tofu")
    if tofu is None:
        return Refusal("tofu is not on the PATH. Fix: install OpenTofu (brew install opentofu).")
    command = [tofu, f"-chdir={TOFU_DIR}", *args]
    missing = [name for name in SECRETS if not env.get(name)]
    if not missing:
        return command
    op = which("op")
    if op is None:
        names = ", ".join(missing)
        return Refusal(
            f"missing {names}, and the 1Password CLI (op) is not on the PATH. "
            f"Fix: install op and sign in (references are in {SECRETS_ENV.relative_to(ROOT)}), "
            f"or export {names}."
        )
    return [op, "run", f"--env-file={SECRETS_ENV}", "--", *command]


def main(argv: list[str]) -> int:
    env = dict(os.environ)
    env.setdefault("OP_ACCOUNT", OP_ACCOUNT)
    decision = plan_command(argv, env, shutil.which)
    if isinstance(decision, Refusal):
        print(f"tofu.py: {decision.message}", file=sys.stderr)
        return 2
    return subprocess.run(decision, env=env, check=False).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
