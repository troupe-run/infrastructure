"""auto-merge.toml: the safe-PR rule's settings, read strictly (spec: auto-merge; design D4)."""

import re
from pathlib import Path

import pytest

import auto_merge as am

REPO = Path(__file__).resolve().parents[2]

MINIMAL = """\
version = 1

[defaults]
max_lines = 800
max_files = 30
max_function_complexity = 15
max_complexity_increase = 40
generated = ["**/uv.lock"]
prose = ["openspec/**"]
complexity_exclude = ["**/tests/**"]
languages = ["python"]
protected = [".github/**"]

[repositories.troupe]
protected = ["**/*masking*.py"]

[repositories.infrastructure]
max_lines = 100

[repositories.website]
"""


@pytest.mark.auto_merge
def test_the_committed_config_gives_every_repository_the_owners_limits() -> None:
    config = am.read_config(REPO)
    assert set(config.repositories) == {"troupe", "infrastructure", "website"}
    for rules in config.repositories.values():
        assert rules.limits == am.Limits(800, 30, 15, 40)


@pytest.mark.auto_merge
def test_the_committed_config_protects_the_rules_own_files_and_troupes_masking() -> None:
    config = am.read_config(REPO)
    infrastructure = config.repositories["infrastructure"]
    for path in ("auto-merge.toml", "scripts/auto_merge.py", "tofu/main.tf", "oob/README.md",
                 ".github/workflows/auto-merge.yml"):  # fmt: skip
        assert infrastructure.is_protected(path), path
    troupe = config.repositories["troupe"]
    assert troupe.is_protected("packages/troupe/src/troupe/core/masking.py")
    assert troupe.is_protected("packages/troupe-plugin-sdk/src/troupe_plugin_sdk/credential.py")
    assert not troupe.is_protected("packages/troupe/src/troupe/core/runner.py")
    assert not config.repositories["website"].is_protected("src/pages/index.astro")


def test_a_repositorys_protected_list_adds_to_the_defaults() -> None:
    troupe = am.parse_config(MINIMAL).repositories["troupe"]
    assert troupe.is_protected(".github/workflows/ci.yml")
    assert troupe.is_protected("plugins/x/src/x/masking.py")


def test_a_repositorys_limit_replaces_the_defaults_for_it_alone() -> None:
    config = am.parse_config(MINIMAL)
    assert config.repositories["infrastructure"].limits.max_lines == 100
    assert config.repositories["troupe"].limits.max_lines == 800


def test_generated_and_prose_paths_are_told_apart() -> None:
    rules = am.parse_config(MINIMAL).repositories["website"]
    assert rules.is_generated("uv.lock")
    assert rules.is_generated("packages/a/uv.lock")
    assert rules.is_prose("openspec/changes/x/design.md")
    assert not rules.is_generated("src/a.py")
    assert not rules.is_prose("src/a.py")


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (("max_lines = 800", "max_line = 800"), "defaults.max_line"),
        (("max_files = 30", 'max_files = "30"'), "defaults.max_files"),
        (
            ("max_function_complexity = 15", "max_function_complexity = -1"),
            "defaults.max_function_complexity",
        ),
        (
            ("max_complexity_increase = 40", "max_complexity_increase = true"),
            "defaults.max_complexity_increase",
        ),
        (('languages = ["python"]', 'languages = ["cobol"]'), "defaults.languages"),
        (('prose = ["openspec/**"]', 'prose = "openspec/**"'), "defaults.prose"),
        (("[repositories.website]\n", ""), "repositories.website"),
        (
            ("[repositories.website]\n", "[repositories.website]\n[repositories.dotgithub]\n"),
            "repositories.dotgithub",
        ),
        (("max_lines = 100", "max_lines = 1.5"), "repositories.infrastructure.max_lines"),
        (("max_lines = 100", "generated = []"), "repositories.infrastructure.generated"),
        (("version = 1", "version = 2"), "version"),
    ],
)
def test_a_bad_config_fails_naming_the_key(change: tuple[str, str], named: str) -> None:
    old, new = change
    assert old in MINIMAL
    with pytest.raises(am.AutoMergeError, match=re.escape(f"`{named}`")):
        am.parse_config(MINIMAL.replace(old, new, 1))


def test_a_missing_default_is_named() -> None:
    with pytest.raises(am.AutoMergeError, match=re.escape("`defaults.protected` is required")):
        am.parse_config(MINIMAL.replace('protected = [".github/**"]\n', "", 1))


def test_a_missing_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(am.AutoMergeError, match=re.escape("auto-merge.toml is missing")):
        am.read_config(tmp_path)


def test_invalid_toml_is_an_error() -> None:
    with pytest.raises(am.AutoMergeError, match="isn't valid TOML"):
        am.parse_config("version = ")
