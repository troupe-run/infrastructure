"""A saved plan holds no key (spec: state-and-apply; ephemeral-state-passphrase D2, D3).

The declaration tests read both roots' `.tf` files, so a key that stops being ephemeral fails
here, before any plan is made.
"""

import re
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
