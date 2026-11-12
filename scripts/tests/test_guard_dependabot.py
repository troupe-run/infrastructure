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

FIXTURES = Path(__file__).parent / "fixtures" / "dependabot-issues"

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


# guard-requirement-range task 3.5: a requirement update read from its manifest line, as the
# guard reads it, and from its title, as the issue reads it, is the same kind (design D4).
# Dependabot keeps the file's order of bounds but reorders the old range in the title, so the
# title's is shuffled.
DIGITS = st.lists(st.integers(0, 12), min_size=1, max_size=4).map(lambda p: ".".join(map(str, p)))
MOVES = st.lists(
    st.tuples(st.sampled_from(["<", "<=", ">", ">=", "==", "!=", "~=", "^", "~"]), DIGITS, DIGITS),
    min_size=1,
    max_size=3,
    unique_by=lambda move: move[0],
)


@given(moves=MOVES, data=st.data())
def test_a_requirement_s_manifest_line_and_title_are_the_same_kind(
    moves: list[tuple[str, str, str]], data: st.DataObject
) -> None:
    old = [operator + version for operator, version, _ in moves]
    new = ",".join(operator + version for operator, _, version in moves)
    titled = ",".join(data.draw(st.permutations(old)))
    kind, _ = guard.dependabot_line_kind("dep", f'    "dep{",".join(old)}",', f'    "dep{new}",')
    assert kind == dependabot_issues.range_kind(titled, new)


def test_troupe_181_s_line_and_title_are_both_a_patch() -> None:
    title = json.loads((FIXTURES / "pull-troupe-181.json").read_text(encoding="utf-8"))["title"]
    match = dependabot_issues.REQUIREMENT.fullmatch(title)
    assert match is not None
    line = 'requires = ["uv_build>=0.13.0,<0.14"]'
    moved = guard.dependabot_line_kind("uv-build", line, line.replace("0.13.0", "0.13.5"))
    assert moved == ("patch", None)
    assert dependabot_issues.range_kind(match.group("old"), match.group("new")) == "patch"


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


# guard-requirement-range: a requirement update, read from its manifest lines (design D3, D5).

UV_BUILD_BRANCH = "dependabot/uv/uv-build-gte-0.13.3-and-lt-0.14"
# troupe #181's commit a9fe317 (2026-10-29), trimmed as the others are. Its subject gives no
# versions, and its metadata's 0.13.3 is stale: the diff writes 0.13.5 (design Context).
UV_BUILD_181 = message(
    "chore(deps-dev): Update uv-build requirement",
    "Updates the requirements on [uv-build](https://github.com/astral-sh/uv) to permit the latest"
    " version.",
    "- dependency-name: uv-build\n  dependency-version: 0.13.3\n"
    "  dependency-type: direct:development\n",
)
# The nine packages #181 changed, each with troupe's build-system table.
UV_BUILD_PACKAGES = [
    *(
        f"packages/{name}/pyproject.toml"
        for name in (
            "troupe-artifacts-local",
            "troupe-identity-local",
            "troupe-stage-local",
            "troupe-store-text",
            "troupe-vcs-files",
            "troupe-vcs-git",
            "troupe",
        )
    ),
    "plugins/runner-claude-code/pyproject.toml",
    "plugins/runner-scripted/pyproject.toml",
]
UV_BUILD_RANGE = 'requires = ["uv_build>=0.13.0,<0.14"]'
# packages/troupe/pyproject.toml's ranges on troupe's main, 2026-10-29, trimmed to them.
TROUPE_PYPROJECT = """[project]
name = "troupe"
requires-python = ">=3.12,<3.16"
dependencies = [
    "eventsourcing>=9.5.6,<9.6",
    "jsonschema>=4.26,<5",
    "pydantic>=2.14,<3",
    "ruamel.yaml>=0.19.1,<0.20",
]

[build-system]
requires = ["uv_build>=0.13.0,<0.14"]
build-backend = "uv_build"
"""


def requirement_repo(make_repo: Callable[[], Repo], tmp_path: Path) -> tuple[Repo, str]:
    """A troupe-like repository: the dependency files, and #181's nine packages on main, with
    packages/troupe/pyproject.toml holding troupe's real ranges."""
    repo, _ = dependabot_repo(make_repo, tmp_path)
    for path in UV_BUILD_PACKAGES:
        repo.write(path, f'[project]\nname = "x"\n\n[build-system]\n{UV_BUILD_RANGE}\n')
    repo.write("packages/troupe/pyproject.toml", TROUPE_PYPROJECT)
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "--no-verify", "-m", "chore: add the packages")
    git(repo.path, "push", "-q", "origin", "main")
    return repo, repo.head()


def test_troupe_181_s_requirement_update_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = requirement_repo(make_repo, tmp_path)
    repo.switch(UV_BUILD_BRANCH)
    for path in UV_BUILD_PACKAGES:
        edit(repo, path, "uv_build>=0.13.0,<0.14", "uv_build>=0.13.5,<0.14")
    commit(repo, UV_BUILD_181)
    assert ci(repo, base, UV_BUILD_BRANCH, "troupe-run/troupe") == []


TROUPE = "packages/troupe/pyproject.toml"


def requirement_commit(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    subject: str,
    edits: list[tuple[str, str, str]],
) -> tuple[Repo, str]:
    """A requirement commit with ``subject`` on #181's branch, making each (path, old, new)
    edit to troupe-like files."""
    repo, base = requirement_repo(make_repo, tmp_path)
    repo.switch(UV_BUILD_BRANCH)
    for path, old, new in edits:
        edit(repo, path, old, new)
    commit(repo, UV_BUILD_181.replace("chore(deps-dev): Update uv-build requirement", subject, 1))
    return repo, base


def requirement_refusal(repo: Repo, base: str) -> str:
    return refused_for(ci(repo, base, UV_BUILD_BRANCH, "troupe-run/troupe")).problem


def test_an_upper_bound_raised_a_minor_step_with_its_lockfile_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = requirement_commit(
        make_repo,
        tmp_path,
        "chore(deps): Update eventsourcing requirement",
        [
            (TROUPE, '"eventsourcing>=9.5.6,<9.6"', '"eventsourcing>=9.6.0,<9.7"'),
            ("uv.lock", 'version = "9.5.5"', 'version = "9.6.0"'),
        ],
    )
    assert ci(repo, base, UV_BUILD_BRANCH, "troupe-run/troupe") == []


def test_a_commit_s_kind_is_its_largest_line_s(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    subject = "chore(deps-dev): Update uv-build requirement"
    repo, base = requirement_commit(
        make_repo,
        tmp_path,
        subject,
        [
            (UV_BUILD_PACKAGES[0], "uv_build>=0.13.0,<0.14", "uv_build>=0.13.5,<0.14"),
            (UV_BUILD_PACKAGES[1], "uv_build>=0.13.0,<0.14", "uv_build>=0.13.0,<1.0"),
        ],
    )
    assert f"{repo.head()[:7]} ('{subject}') is a major update" in requirement_refusal(repo, base)


def test_a_range_that_admits_a_new_major_fails_saying_so(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    subject = "chore(deps): Update jsonschema requirement"
    repo, base = requirement_commit(
        make_repo, tmp_path, subject, [(TROUPE, '"jsonschema>=4.26,<5"', '"jsonschema>=4.26,<6"')]
    )
    assert f"{repo.head()[:7]} ('{subject}') is a major update" in requirement_refusal(repo, base)


@pytest.mark.parametrize(
    ("subject", "edits", "why"),
    [
        pytest.param(
            "chore(deps-dev): Update uv-build requirement",
            [(TROUPE, "uv_build>=0.13.0,<0.14", "uv_build>=0.12.9,<0.14")],
            f"{TROUPE} 'requires = [\"uv_build>=0.13.0,<0.14\"]' to "
            "'requires = [\"uv_build>=0.12.9,<0.14\"]' lowers a version",
            id="a-bound-that-goes-down",
        ),
        pytest.param(
            "chore(deps-dev): Update uv-build requirement",
            [(TROUPE, "uv_build>=0.13.0,<0.14", "uv_build~=0.13.5")],
            "changes more than version numbers",
            id="more-than-versions",
        ),
        pytest.param(
            "chore(deps-dev): Update uv-build requirement",
            [
                (TROUPE, "uv_build>=0.13.0,<0.14", "uv_build>=0.13.5,<0.14"),
                (TROUPE, '"pydantic>=2.14,<3"', '"pydantic>=2.15,<3"'),
            ],
            "'\"pydantic>=2.14,<3\",' to '\"pydantic>=2.15,<3\",' doesn't name uv-build",
            id="another-dependency",
        ),
        pytest.param(
            "chore(deps-dev): Update uv-build requirement",
            [("uv.lock", 'version = "9.5.5"', 'version = "9.6.0"')],
            "it changes no manifest line",
            id="only-the-lockfile",
        ),
    ],
)
def test_a_requirement_whose_lines_can_t_be_read_fails_naming_why(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    subject: str,
    edits: list[tuple[str, str, str]],
    why: str,
) -> None:
    repo, base = requirement_commit(make_repo, tmp_path, subject, edits)
    problem = requirement_refusal(repo, base)
    assert f"{repo.head()[:7]}'s requirement versions can't be read as a minor or patch" in problem
    assert why in problem


LONG_UV_BUILD = "chore(deps-dev): Update uv-build requirement from <0.14,>=0.13.0 to >=0.13.5,<0.14"


def test_a_subject_whose_ranges_agree_with_the_diff_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = requirement_commit(
        make_repo,
        tmp_path,
        LONG_UV_BUILD,
        [(TROUPE, "uv_build>=0.13.0,<0.14", "uv_build>=0.13.5,<0.14")],
    )
    assert ci(repo, base, UV_BUILD_BRANCH, "troupe-run/troupe") == []


def test_a_subject_whose_ranges_disagree_with_the_diff_fails_naming_both(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    # The subject says a patch; the diff moves the upper bound a minor step too.
    repo, base = requirement_commit(
        make_repo,
        tmp_path,
        LONG_UV_BUILD,
        [(TROUPE, "uv_build>=0.13.0,<0.14", "uv_build>=0.13.5,<0.15")],
    )
    problem = requirement_refusal(repo, base)
    assert (
        f"{repo.head()[:7]}'s subject and diff disagree: the subject's ranges are patch, its diff "
        "minor" in problem
    )


@pytest.mark.parametrize(
    ("dependency", "line", "named"),
    [
        ("zod", '    "zod": "^3.0.0",', True),
        ("@axe-core/playwright", '    "@axe-core/playwright": "^4.13.0",', True),
        ("ruamel.yaml", '    "ruamel_yaml>=0.19.1,<0.20",', True),
        ("zod", '    "@evil/zod": "^3.0.0",', False),  # a scoped lookalike (review on #221)
        ("zod", '    "evil/zod": "^3.0.0",', False),
        ("zod", '    "zod/extra": "^3.0.0",', False),
        ("uv-build", '    "uv-build-extra>=1.0,<2",', False),
        ("uv-build", '    "my-uv-build>=1.0,<2",', False),
    ],
)
def test_a_line_names_the_dependency_only_as_a_whole_name(
    dependency: str, line: str, named: bool
) -> None:
    moved = re.sub(r"(\d+)\.0(?=\D*$)", r"\1.1", line, count=1)
    _, why = guard.dependabot_line_kind(dependency, line, moved)
    assert (why != f"doesn't name {dependency}") is named


def test_a_line_for_a_dependency_whose_name_only_starts_alike_fails(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, _ = requirement_repo(make_repo, tmp_path)
    repo.write(
        "plugins/extra/pyproject.toml", '[project]\ndependencies = ["uv-build-extra>=1.0,<2"]\n'
    )
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "--no-verify", "-m", "chore: add a near name")
    git(repo.path, "push", "-q", "origin", "main")
    base = repo.head()
    repo.switch(UV_BUILD_BRANCH)
    edit(repo, "plugins/extra/pyproject.toml", "uv-build-extra>=1.0", "uv-build-extra>=1.1")
    commit(repo, UV_BUILD_181)
    assert "doesn't name uv-build" in requirement_refusal(repo, base)


def test_a_manifest_whose_lines_don_t_pair_fails_saying_so(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = requirement_commit(
        make_repo,
        tmp_path,
        "chore(deps-dev): Update uv-build requirement",
        [(TROUPE, '    "pydantic>=2.14,<3",\n', "")],
    )
    assert f"{TROUPE} doesn't pair line for line" in requirement_refusal(repo, base)


def test_a_requirement_commit_changing_another_file_fails_naming_it(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = requirement_commit(
        make_repo,
        tmp_path,
        "chore(deps-dev): Update uv-build requirement",
        [
            (TROUPE, "uv_build>=0.13.0,<0.14", "uv_build>=0.13.5,<0.14"),
            ("src/index.ts", "export {};", "export { x };"),
        ],
    )
    problem = requirement_refusal(repo, base)
    assert "src/index.ts isn't a manifest or lock file" in problem
    assert "aren't dependency files: src/index.ts" in problem


def test_a_requirement_commit_reports_its_first_problem_in_path_order(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    # packages/... sorts before src/..., so the unreadable line is reported, not the other file.
    # Found by guard-dependabot-short-subject's differential run against main.
    repo, base = requirement_commit(
        make_repo,
        tmp_path,
        "chore(deps-dev): Update uv-build requirement",
        [
            (TROUPE, "uv_build>=0.13.0,<0.14", "uv_build~=0.13.5"),
            ("src/index.ts", "export {};", "export { x };"),
        ],
    )
    problem = requirement_refusal(repo, base)
    assert "changes more than version numbers" in problem
    assert "src/index.ts isn't a manifest or lock file" not in problem


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


# guard-dependabot-short-subject: a "Bump X" subject that leaves out its versions (#301)

PR_285 = FIXTURES.parent / "dependabot-285"
PR_285_BRANCH = "dependabot/uv/types-pyyaml-6.0.12.20261030"


def pr_285_repo(make_repo: Callable[[], Repo], tmp_path: Path) -> tuple[Repo, str]:
    """infrastructure at #285's parent, 0b0f7d9: its real pyproject.toml and uv.lock on main."""
    repo, _ = release_repo(make_repo, tmp_path)
    repo.write("pyproject.toml", (PR_285 / "pyproject.toml.txt").read_text(encoding="utf-8"))
    repo.write("uv.lock", (PR_285 / "uv.lock.txt").read_text(encoding="utf-8"))
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "--no-verify", "-m", "chore: infrastructure at 0b0f7d9")
    git(repo.path, "push", "-q", "origin", "main")
    return repo, repo.head()


def pr_285_message() -> str:
    """b25fc2f's whole message, from the patch: it ends where format-patch's diffstat begins
    ("---" then " pyproject.toml | ...")."""
    patch = (PR_285 / "b25fc2f.patch").read_text(encoding="utf-8")
    return patch.split("Subject: [PATCH] ", 1)[1].split("\n---\n ", 1)[0] + "\n"


def apply_285(repo: Repo) -> None:
    """b25fc2f as Dependabot made it: its message, its author and its diff (git format-patch).
    git am cuts a message at its first "---" line, which drops the updated-dependencies block
    and the sign-off, so the whole message is put back (review on #302)."""
    repo.switch(PR_285_BRANCH)
    git(repo.path, "am", "-q", "--no-verify", "--keep-cr", str(PR_285 / "b25fc2f.patch"))
    message = repo.path.parent / "b25fc2f-message.txt"
    message.write_text(pr_285_message(), encoding="utf-8")
    git(repo.path, "commit", "-q", "--amend", "--no-verify", "-F", str(message))


def test_pr_285_s_real_commit_passes(make_repo: Callable[[], Repo], tmp_path: Path) -> None:
    repo, base = pr_285_repo(make_repo, tmp_path)
    apply_285(repo)
    subject = git(repo.path, "log", "-1", "--format=%s").stdout.strip()
    assert subject == "chore(deps-dev): Bump types-pyyaml"
    message = git(repo.path, "log", "-1", "--format=%B").stdout
    assert "  update-type: version-update:semver-patch\n" in message
    assert message.rstrip().endswith("Signed-off-by: dependabot[bot] <support@github.com>")
    author = git(repo.path, "log", "-1", "--format=%an").stdout.strip()
    assert author == "dependabot[bot]"
    # Before #301: "b25fc2f's subject 'chore(deps-dev): Bump types-pyyaml' doesn't give one
    # dependency's versions, so its kind of update can't be read."
    assert [d.problem for d in ci(repo, base, PR_285_BRANCH, "troupe-run/infrastructure")] == []


def test_pr_285_s_title_and_bumps_line_are_both_a_patch() -> None:
    # The issue reads the title; this checks the guard's Bumps reading of the real message. Its
    # lock and manifest readings are checked by test_pr_285_s_real_commit_passes.
    title = "chore(deps-dev): Bump types-pyyaml from 6.0.12.20260906 to 6.0.12.20261030"
    pull = {"title": title, "head": {"ref": PR_285_BRANCH}}
    assert dependabot_issues.read_update(pull).kind == "patch"
    message = pr_285_message()
    assert message.rstrip().endswith("Signed-off-by: dependabot[bot] <support@github.com>")
    versions = guard.bumps_line_versions(message, "types-pyyaml")
    assert versions == ("6.0.12.20260906", "6.0.12.20261030")
    assert guard.dependabot_update_kind(*versions) == "patch"


@pytest.mark.parametrize(
    ("old", "new", "kind"),
    [
        ("6.0.12.20260906", "6.0.12.20261030", "patch"),  # the fourth part, a date
        ("6.0.12.20261030", "6.0.13.20261101", "patch"),
        ("6.0.12.20261030", "6.1.0.20261101", "minor"),
        ("6.0.12.20261030", "7.0.0.20261101", "major"),
        ("6.0", "6.0.0.1", "patch"),  # missing parts count as zero
    ],
)
def test_four_part_versions_count_by_their_first_differing_part_in_both_readers(
    old: str, new: str, kind: str
) -> None:
    assert guard.dependabot_update_kind(old, new) == kind
    assert dependabot_issues.update_type(old, new) == kind


SUBJECT_PREFIX = st.sampled_from(["", "chore(deps): ", "chore(deps-dev): ", "build(deps): "])
NAME = st.from_regex(r"@?[a-z][a-z0-9._/-]{0,15}", fullmatch=True)
WORD = st.from_regex(r"[!-~]{1,12}", fullmatch=True)


@given(
    prefix=SUBJECT_PREFIX,
    verb=st.sampled_from(["Bump", "bump", "Update", "update"]),
    dependency=NAME,
    old=WORD,
    new=WORD,
    directory=st.none() | WORD,
    requirement=st.booleans(),
)
def test_a_subject_that_gives_its_versions_never_takes_the_short_reading(
    prefix: str,
    verb: str,
    dependency: str,
    old: str,
    new: str,
    directory: str | None,
    requirement: bool,
) -> None:
    subject = (
        f"{prefix}{verb} {dependency}{' requirement' if requirement else ''} from {old} to {new}"
    )
    if directory is not None:
        subject += f" in {directory}"
    assert guard.DEPENDABOT_SUBJECT.fullmatch(subject) or guard.DEPENDABOT_REQUIREMENT.fullmatch(
        subject
    )
    assert guard.dependabot_short_subject(subject) is None


@given(prefix=SUBJECT_PREFIX, dependency=NAME)
def test_a_requirement_subject_never_takes_the_short_reading(prefix: str, dependency: str) -> None:
    subject = f"{prefix}Update {dependency} requirement"
    assert guard.dependabot_short_subject(subject) is None


@given(prefix=SUBJECT_PREFIX, dependency=NAME)
def test_a_bump_subject_without_versions_names_its_dependency(prefix: str, dependency: str) -> None:
    assert guard.dependabot_short_subject(f"{prefix}Bump {dependency}") == dependency
    assert guard.dependabot_short_subject(f"{prefix}Bump {dependency} in /web") == dependency


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Bumps [zod](https://github.com/colinhacks/zod) from 4.6.5 to 4.6.7.", ("4.6.5", "4.6.7")),
        ("Bumps zod from v4.6.5 to v4.6.7.", ("4.6.5", "4.6.7")),
        ("Bumps [Zod](https://x) from 4.6.5 to 4.6.7", ("4.6.5", "4.6.7")),
        (
            "Bumps [vite](https://github.com/vitejs/vite) from 7.0.0 to 7.0.1.",
            "names vite, not zod",
        ),
        ("Updates the requirements on [zod](https://x) to permit the latest version.", None),
        ("", None),
        # Only the first body line is read: a changelog's line further down isn't.
        ("Release notes\n\nBumps [zod](https://x) from 4.6.5 to 4.6.7.", None),
    ],
    ids=["linked", "plain-v", "case", "other", "requirement", "empty", "changelog"],
)
def test_the_bumps_line_is_the_message_s_first_body_line(
    body: str, expected: tuple[str, str] | str | None
) -> None:
    got = guard.bumps_line_versions(f"chore(deps): Bump zod\n\n{body}\n", "zod")
    if isinstance(expected, str):
        assert isinstance(got, str)
        assert expected in got
    else:
        assert got == expected


def test_a_uv_lock_s_versions_are_its_packages_of_that_name() -> None:
    lock = (PR_285 / "uv.lock.txt").read_text(encoding="utf-8")
    assert guard.lock_versions("uv.lock", lock, "types-pyyaml") == ["6.0.12.20260906"]
    assert guard.lock_versions("uv.lock", lock, "types_PyYAML") == ["6.0.12.20260906"]
    assert guard.lock_versions("uv.lock", lock, "types-pyyaml-extra") == []


def test_a_package_lock_s_versions_include_nested_entries_but_not_near_names() -> None:
    lock = json.dumps(
        {
            "packages": {
                "": {"name": "site"},
                "node_modules/zod": {"version": "4.6.5"},
                "node_modules/a/node_modules/zod": {"version": "3.0.0"},
                "node_modules/zod-extra": {"version": "1.0.0"},
                "node_modules/@scope/zod": {"version": "2.0.0"},
            }
        }
    )
    assert guard.lock_versions("package-lock.json", lock, "zod") == ["4.6.5", "3.0.0"]
    assert guard.lock_versions("package-lock.json", lock, "@scope/zod") == ["2.0.0"]


@pytest.mark.parametrize(
    ("name", "text", "why"),
    [
        ("uv.lock", "[[package]\n", "can't be parsed"),
        ("uv.lock", 'package = "x"\n', "has no [[package]] list"),
        ("package-lock.json", "{", "can't be parsed"),
        ("package-lock.json", '{"dependencies": {}}', "has no packages"),
        ("package-lock.json", "[]", "can't be parsed"),
    ],
)
def test_a_lock_file_that_can_t_be_read_says_why(name: str, text: str, why: str) -> None:
    got = guard.lock_versions(name, text, "zod")
    assert isinstance(got, str)
    assert why in got


# Git-level: the readings of a short subject on a reserved branch (spec: "A Dependabot bump whose
# subject leaves out its versions is read from two agreeing sources").

ZOD_SHORT_BRANCH = "dependabot/npm_and_yarn/zod-4.6.7"


def short_message(subject: str, bumps: str | None, metadata: str = "") -> str:
    body = f"{bumps}\n- [Commits](https://github.com/colinhacks/zod/commits)\n" if bumps else ""
    meta = f"---\nupdated-dependencies:\n{metadata}...\n\n" if metadata else ""
    return f"{subject}\n\n{body}\n{meta}Signed-off-by: dependabot[bot] <support@github.com>\n"


def zod_bumps(old: str, new: str) -> str:
    return f"Bumps [zod](https://github.com/colinhacks/zod) from {old} to {new}."


def short_zod(
    make_repo: Callable[[], Repo],
    tmp_path: Path,
    message: str,
    lock_to: str | None = "4.6.7",
    manifest_to: str | None = None,
) -> list[guard.Decision]:
    repo, base = dependabot_repo(make_repo, tmp_path)
    repo.switch(ZOD_SHORT_BRANCH)
    if lock_to is not None:
        edit(repo, "package-lock.json", '"version": "4.6.5"', f'"version": "{lock_to}"')
    if manifest_to is not None:
        edit(repo, "package.json", '"zod": "4.6.5"', f'"zod": "{manifest_to}"')
    commit(repo, message)
    return ci(repo, base, ZOD_SHORT_BRANCH)


def test_a_short_subject_whose_bumps_line_lock_and_manifest_agree_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    message = short_message("chore(deps): Bump zod", zod_bumps("4.6.5", "4.6.7"))
    assert short_zod(make_repo, tmp_path, message, manifest_to="4.6.7") == []


def test_a_short_subject_whose_bumps_line_and_lock_agree_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    message = short_message("chore(deps): Bump zod", zod_bumps("4.6.5", "4.6.7"))
    assert short_zod(make_repo, tmp_path, message) == []


def test_a_short_subject_whose_lock_and_manifest_agree_without_a_bumps_line_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    message = short_message("chore(deps): Bump zod", None)
    assert short_zod(make_repo, tmp_path, message, manifest_to="4.6.7") == []


def test_a_short_subject_whose_bumps_line_and_lock_disagree_fails_naming_both(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    message = short_message("chore(deps): Bump zod", zod_bumps("4.6.5", "4.6.7"))
    problem = refused_for(short_zod(make_repo, tmp_path, message, lock_to="4.7.0")).problem
    assert "readings of zod's versions disagree" in problem
    assert "its Bumps line says 4.6.5 to 4.6.7" in problem
    assert "package-lock.json says 4.6.5 to 4.7.0" in problem


def test_a_short_subject_with_one_reading_fails_saying_two_must_agree(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    message = short_message("chore(deps): Bump zod", None)
    problem = refused_for(short_zod(make_repo, tmp_path, message)).problem
    assert "gives no versions" in problem
    assert "1 reading(s) of zod's, where two must agree (found: package-lock.json)" in problem


def test_a_short_subject_s_metadata_alone_isn_t_a_reading(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    metadata = (
        "- dependency-name: zod\n  dependency-version: 4.6.7\n"
        "  dependency-type: direct:production\n  update-type: version-update:semver-patch\n"
    )
    message = short_message("chore(deps): Bump zod", None, metadata)
    problem = refused_for(short_zod(make_repo, tmp_path, message)).problem
    assert "1 reading(s) of zod's, where two must agree" in problem


def test_a_short_subject_read_as_major_from_two_sources_fails_saying_so(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    message = short_message("chore(deps): Bump zod", zod_bumps("4.6.5", "5.0.0"))
    problem = refused_for(short_zod(make_repo, tmp_path, message, lock_to="5.0.0")).problem
    assert "zod 4.6.5 to 5.0.0) is a major update" in problem


def test_a_short_subject_whose_versions_go_down_fails(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    message = short_message("chore(deps): Bump zod", zod_bumps("4.6.5", "4.6.4"))
    problem = refused_for(short_zod(make_repo, tmp_path, message, lock_to="4.6.4")).problem
    assert "4.6.5 to 4.6.4, can't be read as a minor or patch update" in problem


def test_a_short_subject_whose_bumps_line_names_another_dependency_fails(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    message = short_message("chore(deps): Bump zod", "Bumps [vite](https://x) from 4.6.5 to 4.6.7.")
    problem = refused_for(short_zod(make_repo, tmp_path, message)).problem
    assert "its Bumps line names vite, not zod" in problem


def test_a_short_subject_whose_manifest_moves_by_another_step_fails_naming_both(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, _ = dependabot_repo(make_repo, tmp_path)
    edit(repo, "pyproject.toml", "eventsourcing==9.5.5", "eventsourcing>=9.5,<9.6")
    git(repo.path, "commit", "-q", "--no-verify", "-am", "chore: a range")
    git(repo.path, "push", "-q", "origin", "main")
    base = repo.head()
    branch = "dependabot/uv/eventsourcing-9.5.6"
    repo.switch(branch)
    edit(repo, "uv.lock", 'version = "9.5.5"', 'version = "9.5.6"')
    edit(repo, "pyproject.toml", "eventsourcing>=9.5,<9.6", "eventsourcing>=9.6,<9.7")
    bumps = "Bumps [eventsourcing](https://x) from 9.5.5 to 9.5.6."
    commit(repo, short_message("chore(deps): Bump eventsourcing", bumps))
    problem = refused_for(ci(repo, base, branch, "troupe-run/troupe")).problem
    assert "manifest lines move eventsourcing by a minor step" in problem
    assert "its versions 9.5.5 to 9.5.6 are a patch" in problem


def test_a_short_subject_whose_manifest_line_can_t_be_read_fails_naming_it(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    message = short_message("chore(deps): Bump zod", zod_bumps("4.6.5", "4.6.7"))
    problem = refused_for(short_zod(make_repo, tmp_path, message, manifest_to="^4.6.7")).problem
    assert "manifest lines can't be read for zod" in problem
    assert "package.json" in problem


def test_a_short_subject_whose_lock_moves_two_versions_fails_naming_the_file(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, _ = dependabot_repo(make_repo, tmp_path)
    nested = '"node_modules/a/node_modules/zod": {"version": "4.6.4"},\n    "node_modules/zod"'
    edit(repo, "package-lock.json", '"node_modules/zod"', nested)
    git(repo.path, "commit", "-q", "--no-verify", "-am", "chore: two zods")
    git(repo.path, "push", "-q", "origin", "main")
    base = repo.head()
    repo.switch(ZOD_SHORT_BRANCH)
    edit(repo, "package-lock.json", '"version": "4.6.4"', '"version": "4.6.7"')
    edit(repo, "package-lock.json", '"version": "4.6.5"', '"version": "4.6.7"')
    commit(repo, short_message("chore(deps): Bump zod", zod_bumps("4.6.5", "4.6.7")))
    problem = refused_for(ci(repo, base, ZOD_SHORT_BRANCH)).problem
    assert "package-lock.json doesn't move one version of zod to one other" in problem


def test_a_short_subject_whose_lock_doesn_t_move_the_dependency_fails_naming_the_file(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, base = dependabot_repo(make_repo, tmp_path)
    repo.switch(ZOD_SHORT_BRANCH)
    other = '"node_modules/other": {"version": "1.0.0"},\n    "node_modules/zod"'
    edit(repo, "package-lock.json", '"node_modules/zod"', other)
    edit(repo, "package.json", '"zod": "4.6.5"', '"zod": "4.6.7"')
    commit(repo, short_message("chore(deps): Bump zod", zod_bumps("4.6.5", "4.6.7")))
    problem = refused_for(ci(repo, base, ZOD_SHORT_BRANCH)).problem
    assert "package-lock.json doesn't move one version of zod to one other" in problem
    assert "(from none to none)" in problem


def test_a_short_subject_whose_lock_moves_two_copies_of_one_version_passes(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo, _ = dependabot_repo(make_repo, tmp_path)
    nested = '"node_modules/a/node_modules/zod": {"version": "4.6.5"},\n    "node_modules/zod"'
    edit(repo, "package-lock.json", '"node_modules/zod"', nested)
    git(repo.path, "commit", "-q", "--no-verify", "-am", "chore: a hoisted and a nested zod")
    git(repo.path, "push", "-q", "origin", "main")
    base = repo.head()
    repo.switch(ZOD_SHORT_BRANCH)
    edit(repo, "package-lock.json", '"version": "4.6.5"', '"version": "4.6.7"')
    commit(repo, short_message("chore(deps): Bump zod", zod_bumps("4.6.5", "4.6.7")))
    assert ci(repo, base, ZOD_SHORT_BRANCH) == []


def test_a_short_subject_whose_lock_can_t_be_parsed_fails_naming_the_file(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    message = short_message("chore(deps): Bump zod", zod_bumps("4.6.5", "4.6.7"))
    problem = refused_for(short_zod(make_repo, tmp_path, message, lock_to='4.6.7",')).problem
    assert "package-lock.json can't be parsed" in problem


def test_a_subject_that_gives_its_versions_is_read_from_it_whatever_its_body_and_lock_say(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    # As before #301: the subject's patch counts, though the Bumps line and the lock say major.
    message = short_message(
        "chore(deps): Bump zod from 4.6.5 to 4.6.7", zod_bumps("4.6.5", "9.0.0")
    )
    assert short_zod(make_repo, tmp_path, message, lock_to="9.0.0") == []
