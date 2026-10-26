"""scripts/tofu_text.py reads values from the OpenTofu configuration's text."""

import pytest

import tofu_text

REPOSITORIES = (
    'module "repo_troupe" {\n  source = "./x"\n  name   = "troupe"\n}\n'
    'module "repo_github" {\n  source = "./x"\n  name   = ".github"\n}\n'
)


def test_guard_files_reads_the_list_in_order() -> None:
    text = 'guard_files = toset([\n  "scripts/guard.py",\n  # a note\n  ".githooks/pre-commit",\n])'
    assert tofu_text.guard_files(text) == ["scripts/guard.py", ".githooks/pre-commit"]


def test_guard_files_in_another_shape_is_named() -> None:
    with pytest.raises(tofu_text.ShapeError, match="guard_files isn't toset"):
        tofu_text.guard_files('guard_files = ["scripts/guard.py"]')


def test_guard_targets_reads_each_module_by_its_repositorys_name() -> None:
    text = "guard_targets = toset([module.repo_troupe.name, module.repo_github.name])"
    assert tofu_text.guard_targets(text, REPOSITORIES) == [".github", "troupe"]


def test_a_guard_target_with_no_module_is_named() -> None:
    text = "guard_targets = toset([module.repo_website.name])"
    with pytest.raises(tofu_text.ShapeError, match="repo_website"):
        tofu_text.guard_targets(text, REPOSITORIES)


@pytest.mark.tofu
def test_the_configurations_guard_targets_are_troupe_and_website() -> None:
    targets = tofu_text.guard_targets(
        tofu_text.GUARD_DELIVERY_TF.read_text(encoding="utf-8"),
        tofu_text.REPOSITORIES_TF.read_text(encoding="utf-8"),
    )
    assert targets == ["troupe", "website"]
