"""What each guard target receives, from tofu/guard_delivery.tf's own locals evaluated by OpenTofu
(spec: mutation-testing, "The repositories that get coverage and mutation testing are named in one
place"; quality-scope design D3).

`tofu console` on tofu/ reads the encrypted state, so the locals block is evaluated in a scratch
module instead: the same text, with the targets' module references replaced by their names, and the
repository's delivered files linked beside it so its file() calls read the real sources.
"""

import json
import re
import shutil
import subprocess
from typing import Any

import pytest
from conftest import REPO

import tofu_text

pytestmark = [pytest.mark.tofu, pytest.mark.mutation]

TARGETS = {"module.repo_troupe.name": "troupe", "module.repo_website.name": "website"}
LIST = ".github/guard-delivery.json"


def locals_block(text: str) -> str:
    start = text.index("locals {")
    end = text.index("\n}\n", start) + 3
    block = text[start:end]
    for reference, name in TARGETS.items():
        assert reference in block, f"guard_targets no longer names {reference}: update this test"
        block = block.replace(reference, json.dumps(name))
    return block


@pytest.fixture(scope="module")
def deliveries(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    tofu = shutil.which("tofu")
    assert tofu is not None, "tofu isn't on the PATH: the check needs it (scripts/check.py)"
    root = tmp_path_factory.mktemp("delivery")
    (root / "tofu").mkdir()
    for entry in ("scripts", ".githooks", ".claude", ".github"):
        (root / entry).symlink_to(REPO / entry, target_is_directory=True)
    dependabot = re.search(
        r'dependabot_path = "([^"]+)"', (REPO / "tofu" / "dependabot.tf").read_text("utf-8")
    )
    assert dependabot is not None
    (root / "tofu" / "main.tf").write_text(
        locals_block(tofu_text.GUARD_DELIVERY_TF.read_text(encoding="utf-8"))
        + f'\nlocals {{\n  dependabot_path = "{dependabot.group(1)}"\n}}\n',
        encoding="utf-8",
    )
    expression = (
        "jsonencode({deliveries = {for k, v in local.guard_deliveries : k => "
        "{repository = v.repository, file = v.file, content = v.content}}, "
        "lists = local.guard_lists})\n"
    )
    done = subprocess.run(
        [tofu, "console"],
        cwd=root / "tofu",
        input=expression,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    evaluated: dict[str, Any] = json.loads(json.loads(done.stdout.strip()))
    return evaluated


def files(deliveries: dict[str, Any], repository: str) -> set[str]:
    return {d["file"] for d in deliveries["deliveries"].values() if d["repository"] == repository}


def report_files() -> set[str]:
    return set(tofu_text.mutation_report_files(tofu_text.GUARD_DELIVERY_TF.read_text("utf-8")))


def listed() -> set[str]:
    return set(json.loads((REPO / "scripts" / "mutation.json").read_text("utf-8"))["repositories"])


def test_every_target_gets_the_guards_files_and_its_list(deliveries: dict[str, Any]) -> None:
    common = set(tofu_text.guard_files(tofu_text.GUARD_DELIVERY_TF.read_text("utf-8")))
    assert "scripts/quality_gates.py" in common
    for repository in TARGETS.values():
        assert common | {LIST} <= files(deliveries, repository), repository


def test_only_the_listed_targets_get_the_pull_request_report(deliveries: dict[str, Any]) -> None:
    """troupe is listed and website isn't (#332), so only troupe receives the report's files."""
    for repository in TARGETS.values():
        received = files(deliveries, repository) & report_files()
        assert received == (report_files() if repository in listed() else set()), repository
    assert "troupe" in listed()
    assert "website" not in listed()


def test_each_targets_list_names_exactly_what_it_receives(deliveries: dict[str, Any]) -> None:
    for repository in TARGETS.values():
        written = json.loads(deliveries["lists"][repository])
        assert written["source"] == "troupe-run/infrastructure"
        assert written["files"] == sorted(
            files(deliveries, repository) | {".github/dependabot.yml"}
        )
        [delivered] = [
            d["content"]
            for d in deliveries["deliveries"].values()
            if (d["repository"], d["file"]) == (repository, LIST)
        ]
        assert delivered == deliveries["lists"][repository]


def test_each_delivery_is_keyed_by_repository_and_file_and_carries_its_source(
    deliveries: dict[str, Any],
) -> None:
    for key, delivery in deliveries["deliveries"].items():
        assert key == f"{delivery['repository']}:{delivery['file']}"
        if delivery["file"] != LIST:
            source = (REPO / delivery["file"]).read_text(encoding="utf-8")
            assert delivery["content"] == source, key
