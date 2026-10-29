"""commit-branch-change on GitHub for Dependabot's branches: a minor or patch update of dependency
files only is exempt where a ruleset reserves the dependabot/ name for Dependabot
(dependabot-exemption design D2-D6). The messages are Dependabot's own, copied from its pull
requests on 2026-10-27."""

import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import Repo, git
from hypothesis import given
from hypothesis import strategies as st
from test_guard_push_and_ci import TOFU, _blocks, commit_as, release_repo

import dependabot_issues
import guard

DEPENDABOT_BOT = "dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>"
WEBSITE = "troupe-run/website"

ZOD_BRANCH = "dependabot/npm_and_yarn/zod-4.6.7"
# website #44: a security update, so no update-type.
ZOD = """chore(deps): Bump zod from 4.6.5 to 4.6.7

Bumps [zod](https://github.com/colinhacks/zod) from 4.6.5 to 4.6.7.
- [Release notes](https://github.com/colinhacks/zod/releases)
- [Commits](https://github.com/colinhacks/zod/compare/v4.6.5...v4.6.7)

---
updated-dependencies:
- dependency-name: zod
  dependency-version: 4.6.7
  dependency-type: indirect
...

Signed-off-by: dependabot[bot] <support@github.com>
"""

# Each dependency file before Dependabot's bump, as the base of every test repository.
BASE_FILES = {
    "package.json": '{\n  "dependencies": {\n    "zod": "4.6.5"\n  }\n}\n',
    "package-lock.json": (
        '{\n  "packages": {\n    "node_modules/zod": {"version": "4.6.5"}\n  }\n}\n'
    ),
    "pyproject.toml": '[project]\ndependencies = ["eventsourcing==9.5.5"]\n',
    "packages/troupe/pyproject.toml": '[project]\ndependencies = ["eventsourcing==9.5.5"]\n',
    "uv.lock": '[[package]]\nname = "eventsourcing"\nversion = "9.5.5"\n',
    ".github/workflows/tofu.yml": (
        "jobs:\n  plan:\n    steps:\n"
        "      - uses: actions/download-artifact@v8.0.1\n"
        "      - run: tofu plan\n"
    ),
    "src/index.ts": "export {};\n",
}


def dependabot_repo(make_repo: Callable[[], Repo], tmp_path: Path) -> tuple[Repo, str]:
    """A repository whose main, on its remote, holds every dependency file a test bumps."""
    repo, _ = release_repo(make_repo, tmp_path)
    for path, text in BASE_FILES.items():
        repo.write(path, text)
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "--no-verify", "-m", "chore: add the dependency files")
    git(repo.path, "push", "-q", "origin", "main")
    return repo, repo.head()


def bump(repo: Repo, message: str, *paths: str, author: str = DEPENDABOT_BOT) -> str:
    """A commit, as ``author``, that changes each of ``paths`` by a version-like line."""
    for path in paths:
        target = repo.path / path
        target.write_text(target.read_text(encoding="utf-8") + "# bumped\n", encoding="utf-8")
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "--no-verify", f"--author={author}", "-m", message)
    return repo.head()


def zod_branch(make_repo: Callable[[], Repo], tmp_path: Path) -> tuple[Repo, str]:
    """website #44's branch: a patch update of package-lock.json only."""
    repo, base = dependabot_repo(make_repo, tmp_path)
    repo.switch(ZOD_BRANCH)
    bump(repo, ZOD, "package-lock.json")
    return repo, base


# Pinned before the exemption (task 2.1): the cases it must leave refused.


def test_a_qualifying_dependabot_branch_in_a_repository_without_the_ruleset_fails(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = zod_branch(make_repo, tmp_path)
    [refusal] = guard.run_ci(
        repo.path, base, repo.head(), ZOD_BRANCH, repository="troupe-run/.github"
    )
    assert refusal.rule == "commit-branch-change"


def test_a_qualifying_dependabot_branch_with_no_repository_named_fails(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = zod_branch(make_repo, tmp_path)
    [refusal] = guard.run_ci(repo.path, base, repo.head(), ZOD_BRANCH, repository=None)
    assert refusal.rule == "commit-branch-change"


def test_a_qualifying_dependabot_branch_from_a_fork_fails(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = zod_branch(make_repo, tmp_path)
    [refusal] = guard.run_ci(repo.path, base, repo.head(), ZOD_BRANCH, repository="someone/website")
    assert refusal.rule == "commit-branch-change"


def test_a_local_commit_on_a_dependabot_branch_is_refused(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, _ = zod_branch(make_repo, tmp_path)
    assert guard.commit_branch_change(repo.path, ZOD_BRANCH).rule == "commit-branch-change"


def test_a_release_branch_in_troupe_still_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    repo.switch(guard.RELEASE_BRANCH_PREFIX + "branches--main")
    commit_as(repo, DEPENDABOT_BOT, "chore: release main", "CHANGELOG.md")
    branch = guard.RELEASE_BRANCH_PREFIX + "branches--main"
    assert guard.run_ci(repo.path, base, repo.head(), branch, repository="troupe-run/troupe") == []


# The ruleset that makes the name proof (design D2): every repository the guard exempts has it.

RULESET_PATTERN = '"refs/heads/dependabot/**/*"'


def dependabot_ruleset_repositories(dependabot_tf: str, generated: list[str]) -> set[str]:
    """The repositories the Dependabot branch ruleset is declared for, by full name: one per
    generated configuration (tofu/dependabot/<repository>.yml), when the ruleset covers exactly
    the probed pattern, refuses creation and update, and lets only Dependabot through. A text
    reading of tofu/dependabot.tf, not an HCL parser, as for the release ruleset."""
    owner = guard.SOURCE_REPOSITORY.split("/")[0]
    app = re.search(r"^\s*dependabot_app_id\s*=\s*(\d+)\s*$", dependabot_tf, re.MULTILINE)
    for block in _blocks(dependabot_tf, r'^resource "github_repository_ruleset" "\w+" \{'):
        reserves = all(
            re.search(rf"^\s*{rule}\s*=\s*true\s*$", block, re.MULTILINE)
            for rule in ("creation", "update")
        )
        actors = re.findall(r"actor_id\s*=\s*(\S+)", block)
        only_dependabot = actors == ["local.dependabot_app_id"] and app and app.group(1) == "29110"
        per_configuration = re.search(r"for_each\s*=\s*local\.dependabot_files\s*$", block, re.M)
        if RULESET_PATTERN in block and reserves and only_dependabot and per_configuration:
            return {f"{owner}/{name.removesuffix('.yml')}" for name in generated}
    return set()


def real_coverage(dependabot_tf: str | None = None) -> set[str]:
    text = dependabot_tf or (TOFU / "dependabot.tf").read_text(encoding="utf-8")
    generated = sorted(path.name for path in (TOFU / "dependabot").glob("*.yml"))
    return dependabot_ruleset_repositories(text, generated)


@pytest.mark.tofu
@pytest.mark.dependabot
def test_every_repository_the_guard_exempts_has_the_dependabot_ruleset_declared() -> None:
    assert real_coverage() >= guard.DEPENDABOT_REPOSITORIES


@pytest.mark.tofu
@pytest.mark.dependabot
def test_removing_the_dependabot_ruleset_leaves_its_repositories_uncovered() -> None:
    text = (TOFU / "dependabot.tf").read_text(encoding="utf-8")
    [ruleset] = _blocks(text, r'^resource "github_repository_ruleset" "\w+" \{')
    assert not real_coverage(text.replace(ruleset, "")) >= guard.DEPENDABOT_REPOSITORIES


@pytest.mark.tofu
@pytest.mark.dependabot
@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("creation                      = true", "creation                      = false"),
        ("update                        = true", "update                        = false"),
        # The pattern the probe showed matches no Dependabot branch (task 1.3).
        ('"refs/heads/dependabot/**/*"', '"refs/heads/dependabot/**"'),
        ("dependabot_app_id = 29110", "dependabot_app_id = 5300488"),
        (
            '    bypass_mode = "always"\n  }\n\n  depends_on',
            '    bypass_mode = "always"\n  }\n\n  bypass_actors {\n'
            '    actor_type  = "Integration"\n'
            '    actor_id    = 5300488\n    bypass_mode = "always"\n  }\n\n  depends_on',
        ),
    ],
    ids=["creation", "update", "pattern", "app", "second-bypass"],
)
def test_a_dependabot_ruleset_that_stops_reserving_the_name_leaves_them_uncovered(
    old: str, new: str
) -> None:
    text = (TOFU / "dependabot.tf").read_text(encoding="utf-8")
    assert text.count(old) == 1
    assert not real_coverage(text.replace(old, new)) >= guard.DEPENDABOT_REPOSITORIES


# Dependabot's own messages for the other pull requests in design's table (2026-10-27), trimmed to
# the subject, the Bumps line and the metadata block.


def message(subject: str, bumps: str, metadata: str) -> str:
    return (
        f"{subject}\n\n{bumps}\n\n---\nupdated-dependencies:\n{metadata}...\n\n"
        "Signed-off-by: dependabot[bot] <support@github.com>\n"
    )


POSTCSS = message(  # website #54, a security update: no update-type, and a build prefix
    "build(deps): Bump postcss-selector-parser from 6.1.4 to 6.1.5",
    "Bumps [postcss-selector-parser](https://github.com/postcss/postcss-selector-parser) from 6.1.4"
    " to 6.1.5.",
    "- dependency-name: postcss-selector-parser\n  dependency-version: 6.1.5\n"
    "  dependency-type: indirect\n",
)
AXE = message(  # website #58
    "chore(deps-dev): Bump @axe-core/playwright from 4.13.0 to 4.14.0",
    "Bumps [@axe-core/playwright](https://github.com/dequelabs/axe-core-npm) from 4.13.0 to"
    " 4.14.0.",
    '- dependency-name: "@axe-core/playwright"\n  dependency-version: 4.14.0\n'
    "  dependency-type: direct:development\n  update-type: version-update:semver-minor\n",
)
TYPESCRIPT = message(  # website #55
    "chore(deps-dev): Bump typescript from 6.0.3 to 7.0.2",
    "Bumps [typescript](https://github.com/microsoft/TypeScript) from 6.0.3 to 7.0.2.",
    "- dependency-name: typescript\n  dependency-version: 7.0.2\n"
    "  dependency-type: direct:development\n  update-type: version-update:semver-major\n",
)
EVENTSOURCING = message(  # troupe #174
    "chore(deps): Bump eventsourcing from 9.5.5 to 9.5.6",
    "Bumps [eventsourcing](https://github.com/pyeventsourcing/eventsourcing) from 9.5.5 to 9.5.6.",
    "- dependency-name: eventsourcing\n  dependency-version: 9.5.6\n"
    "  dependency-type: direct:production\n  update-type: version-update:semver-patch\n",
)
UV_BUILD = message(  # troupe #175: a requirement range, whose subject gives no versions
    "chore(deps-dev): Update uv-build requirement",
    "Updates the requirements on [uv-build](https://github.com/astral-sh/uv) to permit the latest"
    " version.",
    "- dependency-name: uv-build\n  dependency-version: 0.13.2\n"
    "  dependency-type: direct:development\n",
)
DOWNLOAD_ARTIFACT = message(  # infrastructure #184
    "chore(deps): Bump actions/download-artifact from 8.0.1 to 8.0.2",
    "Bumps [actions/download-artifact](https://github.com/actions/download-artifact) from 8.0.1 to"
    " 8.0.2.",
    "- dependency-name: actions/download-artifact\n  dependency-version: 8.0.2\n"
    "  dependency-type: direct:production\n  update-type: version-update:semver-patch\n",
)

REAL_SUBJECTS = [
    ZOD.splitlines()[0],
    POSTCSS.splitlines()[0],
    AXE.splitlines()[0],
    TYPESCRIPT.splitlines()[0],
    EVENTSOURCING.splitlines()[0],
    UV_BUILD.splitlines()[0],
    # The pull request's title for #175, which keeps the range the commit's subject drops.
    "chore(deps-dev): Update uv-build requirement from <0.14,>=0.13.0 to >=0.13.2,<0.14",
    DOWNLOAD_ARTIFACT.splitlines()[0],
]


# Task 4.1: the guard counts an update as the issue does (design D5)


def issue_kind(subject: str) -> str:
    pull = {"title": subject, "head": {"ref": "dependabot/npm_and_yarn/x"}}
    return dependabot_issues.read_update(pull).kind


def test_the_guard_s_copies_are_the_issue_workflow_s_patterns() -> None:
    assert guard.DEPENDABOT_SUBJECT.pattern == dependabot_issues.TITLE.pattern
    assert guard.DEPENDABOT_VERSION.pattern == dependabot_issues.VERSION.pattern
    assert guard.DEPENDABOT_REQUIREMENT.pattern == dependabot_issues.REQUIREMENT.pattern
    assert guard.DEPENDABOT_SPECIFIER.pattern == dependabot_issues.SPECIFIER.pattern


@pytest.mark.parametrize("subject", REAL_SUBJECTS)
def test_each_real_subject_is_the_same_kind_of_update_for_the_guard_and_the_issue(
    subject: str,
) -> None:
    assert guard.dependabot_subject_kind(subject) == issue_kind(subject)


def test_the_real_subjects_kinds() -> None:
    kinds = [guard.dependabot_subject_kind(subject) for subject in REAL_SUBJECTS]
    # The commit's subject gives no versions; the pull request's title gives ranges, a patch apart.
    assert kinds == ["patch", "patch", "minor", "major", "patch", "unknown", "patch", "patch"]


VERSIONS = st.one_of(
    st.lists(st.integers(0, 12), min_size=1, max_size=4).map(lambda p: ".".join(map(str, p))),
    st.text(max_size=8),
).flatmap(lambda v: st.sampled_from([v, f"v{v}"]))


@given(old=VERSIONS, new=VERSIONS)
def test_any_pair_of_versions_is_the_same_kind_for_the_guard_and_the_issue(
    old: str, new: str
) -> None:
    assert guard.dependabot_update_kind(old, new) == dependabot_issues.update_type(old, new)


@given(dependency=st.from_regex(r"[@a-z][a-z/-]{0,12}", fullmatch=True), old=VERSIONS, new=VERSIONS)
def test_any_bump_subject_is_the_same_kind_for_the_guard_and_the_issue(
    dependency: str, old: str, new: str
) -> None:
    subject = f"chore(deps): Bump {dependency} from {old} to {new}"
    assert guard.dependabot_subject_kind(subject) == issue_kind(subject)


# guard-requirement-range task 2.3: the guard counts a range as the issue does (design D4)

OPERATORS = ["", "<", "<=", ">", ">=", "==", "!=", "~=", "^", "~", "=", "=>"]
RANGES = st.lists(st.tuples(st.sampled_from(OPERATORS), VERSIONS), min_size=1, max_size=3).map(
    lambda bounds: ",".join(operator + version for operator, version in bounds)
)


@given(old=VERSIONS, new=VERSIONS)
def test_any_pair_of_moves_is_the_same_kind_for_the_guard_and_the_issue(old: str, new: str) -> None:
    pairs = [(old, new), (new, old)]
    assert guard.dependabot_pairs_kind(pairs[:1]) == dependabot_issues.pairs_kind(pairs[:1])
    assert guard.dependabot_pairs_kind(pairs) == dependabot_issues.pairs_kind(pairs)


@given(old=RANGES, new=RANGES)
def test_any_pair_of_ranges_is_the_same_kind_for_the_guard_and_the_issue(
    old: str, new: str
) -> None:
    assert guard.dependabot_range_kind(old, new) == dependabot_issues.range_kind(old, new)


# Task 4.2: dependency files only (design D4)


def edit(repo: Repo, path: str, old: str, new: str) -> None:
    target = repo.path / path
    text = target.read_text(encoding="utf-8")
    assert old in text
    target.write_text(text.replace(old, new), encoding="utf-8")


def commit(repo: Repo, message: str, author: str = DEPENDABOT_BOT) -> str:
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "--no-verify", f"--author={author}", "-m", message)
    return repo.head()


def ci(repo: Repo, base: str, branch: str, repository: str = WEBSITE) -> list[guard.Decision]:
    """A push's check, which has no title or description: only the git-level rules."""
    return guard.run_ci(repo.path, base, repo.head(), branch, repository=repository)


def refused_for(decisions: list[guard.Decision]) -> guard.Decision:
    [refusal] = decisions
    assert refusal.rule == "commit-branch-change"
    assert (
        "A Dependabot branch is exempt only when it is a minor or patch update" in refusal.problem
    )
    assert "OpenSpec change" in refusal.fix
    assert guard.DEPENDABOT_DOCS in refusal.fix
    return refusal


def test_a_patch_update_of_the_lockfile_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = zod_branch(make_repo, tmp_path)
    assert ci(repo, base, ZOD_BRANCH) == []


def test_a_minor_update_of_the_manifest_and_lockfile_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    branch = "dependabot/npm_and_yarn/axe-core/playwright-4.14.0"
    repo.switch(branch)
    bump(repo, AXE, "package.json", "package-lock.json")
    assert ci(repo, base, branch) == []


def test_manifests_in_several_packages_and_the_lockfile_pass(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    branch = "dependabot/uv/eventsourcing-9.5.6"
    repo.switch(branch)
    bump(repo, EVENTSOURCING, "pyproject.toml", "packages/troupe/pyproject.toml", "uv.lock")
    assert ci(repo, base, branch, "troupe-run/troupe") == []


def test_an_action_bump_of_a_workflow_s_uses_line_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    branch = "dependabot/github_actions/actions/download-artifact-8.0.2"
    repo.switch(branch)
    edit(repo, ".github/workflows/tofu.yml", "download-artifact@v8.0.1", "download-artifact@v8.0.2")
    commit(repo, DOWNLOAD_ARTIFACT)
    assert ci(repo, base, branch, "troupe-run/infrastructure") == []


def test_another_file_fails_naming_it(make_repo: Callable[[], Repo], tmp_path: Path) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    repo.switch(ZOD_BRANCH)
    bump(repo, ZOD, "package-lock.json", "src/index.ts")
    refusal = refused_for(ci(repo, base, ZOD_BRANCH))
    assert "aren't dependency files: src/index.ts." in refusal.problem


def test_a_file_dependabot_s_ecosystems_here_don_t_use_fails(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    # security-scanning's probe: pip's requirements.txt, which no declared ecosystem uses.
    repo, base = dependabot_repo(make_repo, tmp_path)
    branch = "dependabot/pip/requests-2.33.0"
    repo.switch(branch)
    commit_as(
        repo, DEPENDABOT_BOT, "build(deps): Bump requests from 2.32.0 to 2.33.0", "requirements.txt"
    )
    refusal = refused_for(ci(repo, base, branch, "troupe-run/troupe"))
    assert "requirements.txt" in refusal.problem


def test_a_deleted_lockfile_fails_naming_it(make_repo: Callable[[], Repo], tmp_path: Path) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    branch = "dependabot/uv/eventsourcing-9.5.6"
    repo.switch(branch)
    (repo.path / "uv.lock").unlink()
    commit(repo, EVENTSOURCING)
    refusal = refused_for(ci(repo, base, branch, "troupe-run/troupe"))
    assert "aren't dependency files: uv.lock." in refusal.problem


def test_a_renamed_manifest_fails_naming_it(make_repo: Callable[[], Repo], tmp_path: Path) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    repo.switch(ZOD_BRANCH)
    (repo.path / "web").mkdir()
    git(repo.path, "mv", "package.json", "web/package.json")
    commit(repo, ZOD)
    refusal = refused_for(ci(repo, base, ZOD_BRANCH))
    assert "web/package.json" in refusal.problem


def test_a_workflow_line_that_isn_t_uses_fails_naming_the_workflow(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    branch = "dependabot/github_actions/actions/download-artifact-8.0.2"
    repo.switch(branch)
    edit(repo, ".github/workflows/tofu.yml", "download-artifact@v8.0.1", "download-artifact@v8.0.2")
    edit(repo, ".github/workflows/tofu.yml", "run: tofu plan", "run: tofu apply -auto-approve")
    commit(repo, DOWNLOAD_ARTIFACT)
    refusal = refused_for(ci(repo, base, branch, "troupe-run/infrastructure"))
    assert "aren't dependency files: .github/workflows/tofu.yml." in refusal.problem


# A diff prints a removed "---" as "----" and an added "++x" as "+++x", like its file headers
# (#204).
LEADING_DASHES_WORKFLOW = (
    "---\njobs:\n  plan:\n    steps:\n"
    "      - uses: actions/download-artifact@v8.0.1\n"
    "      - run: >\n          tofu plan\n--force\n"
)


def leading_dashes_bump(
    make_repo: Callable[[], Repo], tmp_path: Path, old: str = "", new: str = ""
) -> tuple[Repo, str, str]:
    """An action bump of LEADING_DASHES_WORKFLOW's uses: line that also replaces ``old`` with
    ``new``, on main's remote and a Dependabot branch."""
    repo, _ = dependabot_repo(make_repo, tmp_path)
    repo.write(".github/workflows/tofu.yml", LEADING_DASHES_WORKFLOW)
    git(repo.path, "commit", "-q", "--no-verify", "-am", "chore: start the workflow with ---")
    git(repo.path, "push", "-q", "origin", "main")
    base = repo.head()
    branch = "dependabot/github_actions/actions/download-artifact-8.0.2"
    repo.switch(branch)
    edit(repo, ".github/workflows/tofu.yml", "download-artifact@v8.0.1", "download-artifact@v8.0.2")
    if old:
        edit(repo, ".github/workflows/tofu.yml", old, new)
    commit(repo, DOWNLOAD_ARTIFACT)
    return repo, base, branch


def test_an_action_bump_of_a_workflow_with_lines_that_begin_with_dashes_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base, branch = leading_dashes_bump(make_repo, tmp_path)
    assert ci(repo, base, branch, "troupe-run/infrastructure") == []


@pytest.mark.parametrize(
    ("old", "new"),
    [("---\njobs:", "jobs:"), ("--force\n", ""), ("--force\n", "--force\n++x\n")],
    ids=["removed-document-marker", "removed-flag", "added-plus-plus"],
)
def test_a_workflow_line_that_begins_like_a_diff_header_fails_naming_the_workflow(
    make_repo: Callable[[], Repo], tmp_path: Path, old: str, new: str
) -> None:
    repo, base, branch = leading_dashes_bump(make_repo, tmp_path, old, new)
    refusal = refused_for(ci(repo, base, branch, "troupe-run/infrastructure"))
    assert "aren't dependency files: .github/workflows/tofu.yml." in refusal.problem


def test_a_merge_commit_fails_naming_it_whatever_its_subject(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    # A merge's paths aren't listed by diff-tree, so one that also changes src/index.ts, with a
    # Dependabot subject, passed as dependency files only (#205).
    repo, base = dependabot_repo(make_repo, tmp_path)
    branch = "dependabot/npm_and_yarn/x"
    repo.switch(branch)
    bump(repo, ZOD, "package-lock.json")
    git(repo.path, "switch", "-q", "-c", "side", base)
    bump(repo, ZOD, "package.json")
    git(repo.path, "switch", "-q", branch)
    git(repo.path, "merge", "-q", "--no-ff", "--no-commit", "side")
    repo.write("src/index.ts", "export const evil = 1;\n")
    merge = commit(repo, ZOD)
    assert len(git(repo.path, "log", "-1", "--format=%P", merge).stdout.split()) == 2
    refusal = refused_for(ci(repo, base, branch))
    assert f"{merge[:7]} is a merge commit, and Dependabot doesn't make merge commits" in (
        refusal.problem
    )


ECOSYSTEM_FILES = {
    "npm": {"package.json", "package-lock.json"},
    "uv": {"pyproject.toml", "uv.lock"},
    "github-actions": set(),  # its workflows' uses: lines
}


@pytest.mark.labels
def test_every_declared_ecosystem_s_files_are_dependency_files() -> None:
    declared = json.loads((TOFU / "labels" / "dependabot.json").read_text(encoding="utf-8"))
    ecosystems = {e for repo in declared["repositories"].values() for e in repo}
    assert ecosystems <= ECOSYSTEM_FILES.keys(), "add the new ecosystem's files to DEPENDENCY_FILES"
    assert set().union(*ECOSYSTEM_FILES.values()) == guard.DEPENDENCY_FILES


# Task 4.3: a single minor or patch update, read from each commit (design D5)


@pytest.mark.parametrize("text", [ZOD, POSTCSS], ids=["zod", "postcss-no-update-type"])
def test_a_patch_update_with_no_update_type_passes(
    make_repo: Callable[[], Repo], tmp_path: Path, text: str
) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    repo.switch(ZOD_BRANCH)
    bump(repo, text, "package-lock.json")
    assert ci(repo, base, ZOD_BRANCH) == []


def test_a_major_update_fails_saying_so(make_repo: Callable[[], Repo], tmp_path: Path) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    branch = "dependabot/npm_and_yarn/typescript-7.0.2"
    repo.switch(branch)
    sha = bump(repo, TYPESCRIPT, "package.json", "package-lock.json")
    refusal = refused_for(ci(repo, base, branch))
    assert f"{sha[:7]} ('chore(deps-dev): Bump typescript from 6.0.3 to 7.0.2') is a major" in (
        refusal.problem
    )
    assert "update-type: version-update:semver-major" in refusal.problem


def test_a_requirement_range_fails_saying_its_versions_can_t_be_read(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    branch = "dependabot/uv/uv-build-gte-0.13.2-and-lt-0.14"
    repo.switch(branch)
    bump(repo, UV_BUILD, "pyproject.toml", "packages/troupe/pyproject.toml")
    refusal = refused_for(ci(repo, base, branch, "troupe-run/troupe"))
    assert "doesn't give one dependency's versions" in refusal.problem


def test_an_update_type_that_disagrees_with_the_versions_fails(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    repo.switch(ZOD_BRANCH)
    text = ZOD.replace("4.6.5 to 4.6.7", "1.2.3 to 1.2.4").replace(
        "  dependency-type: indirect\n",
        "  dependency-type: indirect\n  update-type: version-update:semver-major\n",
    )
    bump(repo, text, "package-lock.json")
    refusal = refused_for(ci(repo, base, ZOD_BRANCH))
    assert "says update-type: version-update:semver-major" in refusal.problem
    assert "is a major" not in refusal.problem


def test_a_branch_with_one_major_commit_among_patches_fails(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = zod_branch(make_repo, tmp_path)
    bump(repo, TYPESCRIPT, "package.json")
    refusal = refused_for(ci(repo, base, ZOD_BRANCH))
    assert "is a major update" in refusal.problem


# guard-requirement-range task 1.1: reading requirement updates leaves every bump's result as it
# was (design D2). Each real bump, with the files its pull request changed, and its outcome on main.
BUMP_OUTCOMES = [
    (ZOD, ZOD_BRANCH, WEBSITE, ("package-lock.json",), None),
    (POSTCSS, ZOD_BRANCH, WEBSITE, ("package-lock.json",), None),
    (AXE, "dependabot/npm_and_yarn/axe-core/playwright-4.14.0", WEBSITE,
     ("package.json", "package-lock.json"), None),
    (TYPESCRIPT, "dependabot/npm_and_yarn/typescript-7.0.2", WEBSITE,
     ("package.json", "package-lock.json"), "is a major update"),
    (EVENTSOURCING, "dependabot/uv/eventsourcing-9.5.6", "troupe-run/troupe",
     ("pyproject.toml", "packages/troupe/pyproject.toml", "uv.lock"), None),
]  # fmt: skip


@pytest.mark.parametrize(
    ("text", "branch", "repository", "paths", "refused"),
    BUMP_OUTCOMES,
    ids=["zod", "postcss", "axe", "typescript", "eventsourcing"],
)
def test_each_real_bump_keeps_its_outcome(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    text: str,
    branch: str,
    repository: str,
    paths: tuple[str, ...],
    refused: str | None,
) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    repo.switch(branch)
    bump(repo, text, *paths)
    decisions = ci(repo, base, branch, repository)
    if refused is None:
        assert decisions == []
    else:
        assert refused in refused_for(decisions).problem


def test_the_real_action_bump_keeps_its_outcome(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    branch = "dependabot/github_actions/actions/download-artifact-8.0.2"
    repo.switch(branch)
    edit(repo, ".github/workflows/tofu.yml", "download-artifact@v8.0.1", "download-artifact@v8.0.2")
    commit(repo, DOWNLOAD_ARTIFACT)
    assert ci(repo, base, branch, "troupe-run/infrastructure") == []


# Task 4.4: the exemption in run_ci (design D3, D6)


@pytest.mark.parametrize("repository", sorted(guard.DEPENDABOT_REPOSITORIES))
def test_a_qualifying_branch_passes_in_each_repository_that_reserves_the_name(
    make_repo: Callable[[], Repo], tmp_path: Path, repository: str
) -> None:
    repo, base = zod_branch(make_repo, tmp_path)
    assert ci(repo, base, ZOD_BRANCH, repository) == []


def test_a_qualifying_pull_request_that_closes_its_issue_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = zod_branch(make_repo, tmp_path)
    title = ZOD.splitlines()[0]
    body = "Bumps zod.\n\nCloses #60"
    assert guard.run_ci(repo.path, base, repo.head(), ZOD_BRANCH, title, WEBSITE, body) == []


def test_a_qualifying_branch_passes_whoever_authored_its_commits(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    repo.switch(ZOD_BRANCH)
    bump(repo, ZOD, "package-lock.json", author="Someone <someone@example.com>")
    assert ci(repo, base, ZOD_BRANCH) == []


def test_a_qualifying_pull_request_with_no_closing_line_fails_only_that(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = zod_branch(make_repo, tmp_path)
    title = ZOD.splitlines()[0]
    decisions = guard.run_ci(repo.path, base, repo.head(), ZOD_BRANCH, title, WEBSITE, "Bumps zod.")
    assert [d.rule for d in decisions] == ["pr-closes-issue"]


def test_a_non_conventional_dependabot_commit_fails_the_commit_message_rule_only(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    repo.switch(ZOD_BRANCH)
    bump(repo, ZOD.removeprefix("chore(deps): "), "package-lock.json")
    assert [d.rule for d in ci(repo, base, ZOD_BRANCH)] == ["commit-message"]


def test_a_branch_outside_dependabot_s_name_is_refused_as_ever(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    repo.switch("bump-zod")
    bump(repo, ZOD, "package-lock.json")
    [refusal] = ci(repo, base, "bump-zod")
    assert refusal.rule == "commit-branch-change"
    assert "Dependabot" not in refusal.problem


@pytest.mark.parametrize(
    "branch", ["dependabot/zod-4.6.7", "dependabot/npm_and_yarn/", "dependabot/"]
)
def test_a_name_not_shaped_like_dependabot_s_isn_t_trusted(
    make_repo: Callable[[], Repo], tmp_path: Path, branch: str
) -> None:
    # The probe showed the ruleset reserves dependabot/<ecosystem>/<name>, not other shapes.
    repo, base = dependabot_repo(make_repo, tmp_path)
    repo.switch("qualifying")
    bump(repo, ZOD, "package-lock.json")
    [refusal] = ci(repo, base, branch)
    assert refusal.rule == "commit-branch-change"
    assert "Dependabot" not in refusal.problem
