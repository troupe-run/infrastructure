"""Fail if any rendering of a saved plan holds a key.

Usage (in .github/workflows/tofu.yml, with the keys in the environment):
    tofu show -json main.tfplan > plan.json
    uv run --no-project scripts/plan_secrets.py plan.txt plan.json

Spec: state-and-apply ("A saved plan holds no key"); design: ephemeral-state-passphrase D2. Each
key in tofu.KEYS is an ephemeral variable, so no plan should hold one. This checks each file for
each key's value, as written and as JSON escapes it, and names the file and the variable, never
the value. A key that's unset or empty can't be checked, so it's an error, not a pass.

Exit codes: 0 no key found; 1 a key found; 2 a key or file couldn't be read.
"""

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from tofu import KEYS


def forms(value: str) -> set[str]:
    """The value as written, and as it appears inside a JSON string."""
    return {value, json.dumps(value)[1:-1]}


def found(text: str, keys: Mapping[str, str]) -> list[str]:
    """The names of the keys whose value appears in the text."""
    return [name for name, value in keys.items() if any(form in text for form in forms(value))]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path, help="plan renderings to check")
    args = parser.parse_args(argv)

    missing = [name for name in KEYS if not os.environ.get(name)]
    if missing:
        print(
            f"plan_secrets.py: {', '.join(missing)} unset or empty, so the plan can't be checked "
            "for it. Fix: run with every key in the environment, as the plan step has them.",
            file=sys.stderr,
        )
        return 2
    keys = {name: os.environ[name] for name in KEYS}

    status = 0
    for path in args.files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            print(f"plan_secrets.py: can't read {path}: {error.strerror}", file=sys.stderr)
            return 2
        for name in found(text, keys):
            print(f"::error title=plan holds a key::{path} holds the value of {name}")
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
