"""scripts/dependabot_config.py generates each repository's .github/dependabot.yml from one policy
(spec: dependency-updates; deliver-dependabot design D1 to D3)."""

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

import dependabot_config
import tofu_text

POLICY: dict[str, Any] = {
    "schedule": {"interval": "weekly", "day": "monday", "time": "00:00", "timezone": "UTC"},
    "cooldown": {
        "default-days": 7,
        "semver-patch-days": 3,
        "semver-minor-days": 7,
        "semver-major-days": 14,
    },
    "semver_cooldown": ["npm", "uv"],
    "commit-message": {"prefix": "chore", "include": "scope"},
    "directories": {"github-actions": "/", "npm": "/", "uv": "/"},
}

LABELS: dict[str, Any] = {
    "dependencies": {"name": "dependencies"},
    "ecosystems": {
        "github-actions": {"name": "github_actions"},
        "npm": {"name": "javascript"},
        "uv": {"name": "python:uv"},
    },
    "repositories": {
        ".github": [],
        "infrastructure": ["github-actions", "uv"],
        "troupe": ["github-actions", "uv"],
        "website": ["github-actions", "npm"],
    },
}

GUARD_FILES = [
    "scripts/guard.py",
    ".github/workflows/guard.yml",
    ".github/workflows/claude-review.yml",
]
TARGETS = ["troupe", "website"]


def generate(guard_files: list[str] = GUARD_FILES) -> dict[str, dict[str, Any]]:
    return dependabot_config.configs(POLICY, LABELS, guard_files, TARGETS)


def updates(repo: str, guard_files: list[str] = GUARD_FILES) -> dict[str, dict[str, Any]]:
    """The repository's update entries, keyed by ecosystem."""
    return {u["package-ecosystem"]: u for u in generate(guard_files)[repo]["updates"]}


# Each repository's ecosystems


def test_each_repository_gets_its_ecosystems_at_their_directories() -> None:
    configs = generate()
    ecosystems = {r: [u["package-ecosystem"] for u in c["updates"]] for r, c in configs.items()}
    assert ecosystems == {
        "infrastructure": ["github-actions", "uv"],
        "troupe": ["github-actions", "uv"],
        "website": ["github-actions", "npm"],
    }
    for config in configs.values():
        assert config["version"] == 2
        for update in config["updates"]:
            assert update["directory"] == POLICY["directories"][update["package-ecosystem"]]


def test_a_repository_with_no_ecosystems_gets_no_file() -> None:
    assert ".github" not in generate()


def test_an_ecosystem_with_no_directory_is_named_with_its_repository() -> None:
    labels = copy.deepcopy(LABELS)
    labels["repositories"]["website"].append("cargo")
    assert dependabot_config.undirected_ecosystems(POLICY, labels) == [
        "website: ecosystem 'cargo' has no directory in tofu/dependabot.json"
    ]


@pytest.mark.dependabot
@pytest.mark.labels
def test_every_declared_ecosystem_has_a_directory() -> None:
    policy = json.loads(dependabot_config.POLICY.read_text(encoding="utf-8"))
    labels = json.loads(dependabot_config.LABELS.read_text(encoding="utf-8"))
    assert dependabot_config.undirected_ecosystems(policy, labels) == []


# What ships in a release (security-updates-release design D4)


def test_a_release_naming_an_ecosystem_the_repository_lacks_is_named() -> None:
    policy = copy.deepcopy(POLICY) | {"releases": {"troupe": ["uv", "npm"]}}
    assert dependabot_config.unknown_releases(policy, LABELS) == [
        "troupe: ecosystem 'npm' in tofu/dependabot.json's releases isn't one of its Dependabot "
        "ecosystems in tofu/labels/dependabot.json"
    ]


def test_a_release_naming_an_undeclared_repository_is_named() -> None:
    policy = copy.deepcopy(POLICY) | {"releases": {"troupe-docs": ["uv"]}}
    assert dependabot_config.unknown_releases(policy, LABELS) == [
        "troupe-docs: in tofu/dependabot.json's releases, but not a repository in "
        "tofu/labels/dependabot.json"
    ]


def test_a_policy_with_no_releases_has_none_to_check() -> None:
    assert dependabot_config.unknown_releases(POLICY, LABELS) == []


def test_releases_change_no_generated_configuration() -> None:
    policy = copy.deepcopy(POLICY) | {"releases": {"troupe": ["uv"]}}
    assert dependabot_config.configs(policy, LABELS, GUARD_FILES, TARGETS) == generate()


@pytest.mark.dependabot
@pytest.mark.labels
def test_only_troupes_uv_dependencies_ship_and_the_declaration_is_valid() -> None:
    policy = json.loads(dependabot_config.POLICY.read_text(encoding="utf-8"))
    labels = json.loads(dependabot_config.LABELS.read_text(encoding="utf-8"))
    assert policy["releases"] == {"troupe": ["uv"]}
    assert dependabot_config.unknown_releases(policy, labels) == []


# Schedule and cooldown


def test_every_entry_runs_weekly_on_the_policys_schedule_with_no_grouping_or_limit() -> None:
    for config in generate().values():
        for update in config["updates"]:
            assert update["schedule"] == POLICY["schedule"]
            assert "groups" not in update
            assert "open-pull-requests-limit" not in update


@pytest.mark.parametrize(("repo", "ecosystem"), [("website", "npm"), ("troupe", "uv")])
def test_npm_and_uv_wait_by_kind_of_release_the_major_longest(repo: str, ecosystem: str) -> None:
    cooldown = updates(repo)[ecosystem]["cooldown"]
    assert cooldown == POLICY["cooldown"]
    assert cooldown["semver-major-days"] > cooldown["semver-minor-days"]
    assert cooldown["semver-major-days"] > cooldown["semver-patch-days"]


def test_github_actions_waits_the_default_days_only() -> None:
    assert updates("troupe")["github-actions"]["cooldown"] == {"default-days": 7}


# Commit messages and labels


def test_every_entry_commits_as_chore_with_its_scope() -> None:
    for config in generate().values():
        for update in config["updates"]:
            assert update["commit-message"] == {"prefix": "chore", "include": "scope"}


def test_troupes_github_actions_labels_are_dependencies_and_github_actions() -> None:
    assert updates("troupe")["github-actions"]["labels"] == ["dependencies", "github_actions"]


@pytest.mark.dependabot
@pytest.mark.labels
@pytest.mark.tofu
def test_every_label_in_the_real_configurations_is_declared_for_that_repository() -> None:
    labels = json.loads(dependabot_config.LABELS.read_text(encoding="utf-8"))
    for name, content in dependabot_config.generated().items():
        repo = name.removesuffix(".yml")
        declared = {labels["dependencies"]["name"]} | {
            labels["ecosystems"][ecosystem]["name"] for ecosystem in labels["repositories"][repo]
        }
        for update in yaml.safe_load(content)["updates"]:
            assert set(update["labels"]) <= declared, (name, update["labels"])


@pytest.mark.dependabot
@pytest.mark.labels
@pytest.mark.tofu
def test_no_real_configuration_moves_dependabots_branches_out_of_the_reserved_name() -> None:
    # The ruleset reserves Dependabot's default dependabot/ prefix and / separator
    # (dependabot-exemption design D2), so no entry may change either.
    for name, content in dependabot_config.generated().items():
        for update in yaml.safe_load(content)["updates"]:
            assert "pull-request-branch-name" not in update, name


# Delivered workflows


def test_guard_targets_leave_out_the_delivered_workflows() -> None:
    for repo in TARGETS:
        assert updates(repo)["github-actions"]["exclude-paths"] == [
            ".github/workflows/claude-review.yml",
            ".github/workflows/guard.yml",
        ]


def test_infrastructure_leaves_out_nothing() -> None:
    for update in updates("infrastructure").values():
        assert "exclude-paths" not in update


def test_only_the_github_actions_entry_leaves_anything_out() -> None:
    assert "exclude-paths" not in updates("troupe")["uv"]
    assert "exclude-paths" not in updates("website")["npm"]


def test_a_newly_delivered_workflow_is_left_out_too() -> None:
    files = [*GUARD_FILES, ".github/workflows/issues.yml"]
    excluded = updates("troupe", files)["github-actions"]["exclude-paths"]
    assert ".github/workflows/issues.yml" in excluded


# The rendered file


def test_the_file_opens_by_saying_where_it_comes_from() -> None:
    text = dependabot_config.render(generate()["troupe"])
    assert text.startswith("# Generated in troupe-run/infrastructure")
    assert "Change it there" in text.split("version:", 1)[0]


def test_the_rendered_file_reads_back_as_the_configuration() -> None:
    config = generate()["troupe"]
    assert yaml.safe_load(dependabot_config.render(config)) == config


def test_the_time_is_quoted_so_no_reader_takes_it_for_a_number() -> None:
    text = dependabot_config.render(generate()["troupe"])
    assert 'time: "00:00"' in text


# The checked-in files


@pytest.mark.dependabot
@pytest.mark.labels
@pytest.mark.tofu
def test_the_generated_files_are_up_to_date() -> None:
    assert dependabot_config.stale(dependabot_config.OUT, dependabot_config.generated()) == []


def test_a_stale_file_is_named_with_the_command(tmp_path: Path) -> None:
    files = {"troupe.yml": "new\n", "website.yml": "same\n"}
    (tmp_path / "troupe.yml").write_text("old\n", encoding="utf-8")
    (tmp_path / "website.yml").write_text("same\n", encoding="utf-8")
    (tmp_path / "gone.yml").write_text("x\n", encoding="utf-8")
    run = "run `uv run scripts/dependabot_config.py`"
    assert dependabot_config.stale(tmp_path, files) == [
        f"tofu/dependabot/troupe.yml is out of date: {run}",
        f"tofu/dependabot/gone.yml is no longer generated: {run}",
    ]


def test_a_missing_file_is_named(tmp_path: Path) -> None:
    assert dependabot_config.stale(tmp_path, {"troupe.yml": "x\n"}) == [
        "tofu/dependabot/troupe.yml is out of date: run `uv run scripts/dependabot_config.py`"
    ]


def test_writing_removes_a_file_no_longer_generated(tmp_path: Path) -> None:
    (tmp_path / "gone.yml").write_text("x\n", encoding="utf-8")
    dependabot_config.write(tmp_path, {"troupe.yml": "x\n"})
    assert sorted(p.name for p in tmp_path.iterdir()) == ["troupe.yml"]


# The delivery (tofu/dependabot.tf, tofu/guard_delivery.tf; design D4)

DEPENDABOT_TF = dependabot_config.REPO / "tofu" / "dependabot.tf"


@pytest.mark.tofu
def test_opentofu_delivers_each_generated_file_to_dependabot_yml() -> None:
    tf = DEPENDABOT_TF.read_text(encoding="utf-8")
    assert 'dependabot_path = ".github/dependabot.yml"' in tf
    assert 'fileset("${path.module}/dependabot", "*.yml")' in tf
    assert dependabot_config.OUT == dependabot_config.REPO / "tofu" / "dependabot"
    assert "overwrite_on_create = false" in tf


@pytest.mark.tofu
def test_the_guard_targets_delivered_list_names_the_dependabot_config() -> None:
    tf = tofu_text.GUARD_DELIVERY_TF.read_text(encoding="utf-8")
    listed = re.search(r"files\s+= sort\(concat\((.*?)\)\)\n", tf)
    assert listed is not None, "guard_list's files isn't sort(concat(...)); update this test"
    assert "local.dependabot_path" in listed.group(1)


@pytest.mark.dependabot
@pytest.mark.labels
@pytest.mark.tofu
def test_every_guard_target_has_a_generated_file() -> None:
    targets = tofu_text.guard_targets(
        tofu_text.GUARD_DELIVERY_TF.read_text(encoding="utf-8"),
        tofu_text.REPOSITORIES_TF.read_text(encoding="utf-8"),
    )
    assert {f"{repo}.yml" for repo in targets} <= set(dependabot_config.generated())
