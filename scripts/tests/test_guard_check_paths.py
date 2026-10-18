"""commit-check-paths tasks 1.1-1.2: the check-paths declaration, read and decided (D1-D5)."""

import subprocess
import sys
from collections.abc import Callable

import pytest
from conftest import SCRIPTS, Repo, clean_env
from hypothesis import given
from hypothesis import strategies as st

import guard

BOTH = """\
version = 1

[skip]
paths = ["openspec/**"]

[scopes.docs]
paths = ["docs/**", "plugins/runner-scripted/README.md"]

[scopes.api]
paths = ["api/**"]
"""


def declared(text: str = BOTH) -> guard.CheckPaths:
    return guard.check_paths(text)


def problem(text: str) -> str:
    with pytest.raises(guard.CheckPathsError) as error:
        guard.check_paths(text)
    assert error.value.fix, "every refusal gives a fix"
    return error.value.problem


# Reading the declaration


def test_a_declaration_with_only_a_version_has_no_groups() -> None:
    assert declared("version = 1\n") == guard.CheckPaths(skip=(), scopes=())


def test_a_declaration_with_only_skip_is_read() -> None:
    text = 'version = 1\n[skip]\npaths = ["openspec/**", "CHANGELOG.md"]\n'
    assert declared(text) == guard.CheckPaths(skip=("openspec/**", "CHANGELOG.md"), scopes=())


def test_a_declaration_with_only_scopes_is_read() -> None:
    text = 'version = 1\n[scopes.docs]\npaths = ["docs/**"]\n'
    assert declared(text) == guard.CheckPaths(skip=(), scopes=(("docs", ("docs/**",)),))


def test_a_declaration_with_skip_and_scopes_is_read() -> None:
    assert declared() == guard.CheckPaths(
        skip=("openspec/**",),
        scopes=(
            ("docs", ("docs/**", "plugins/runner-scripted/README.md")),
            ("api", ("api/**",)),
        ),
    )


def test_the_same_entry_twice_in_one_group_is_allowed() -> None:
    text = 'version = 1\n[skip]\npaths = ["openspec/**", "openspec/**"]\n'
    assert declared(text).skip == ("openspec/**", "openspec/**")


@pytest.mark.parametrize(
    ("text", "names"),
    [
        ("version = [", "TOML"),
        ('[skip]\npaths = ["a/**"]\n', "version"),
        ("version = 2\n", "version"),
        ('version = "1"\n', "version"),
        ("version = true\n", "version"),
        ("version = 1\nextra = 1\n", "extra"),
        ("version = 1\n[other]\npaths = []\n", "other"),
        ("version = 1\n[skip]\n", "skip.paths"),
        ('version = 1\n[skip]\npaths = "a/**"\n', "skip.paths"),
        ("version = 1\n[skip]\npaths = [1]\n", "skip.paths[0]"),
        ('version = 1\n[skip]\npaths = []\nwhy = "x"\n', "why"),
        ('version = 1\nskip = ["a/**"]\n', "skip"),
        ('version = 1\nscopes = ["a"]\n', "scopes"),
        ("version = 1\n[scopes]\ndocs = 1\n", "scopes.docs"),
        ("version = 1\n[scopes.docs]\n", "scopes.docs.paths"),
    ],
)
def test_a_malformed_declaration_is_refused_naming_what_is_wrong(text: str, names: str) -> None:
    assert names in problem(text)


@pytest.mark.parametrize("name", ["Docs", "1x", "a-b", "_a", "-a", "none", "full"])
def test_a_bad_or_reserved_scope_name_is_refused(name: str) -> None:
    assert f"`{name}`" in problem(f'version = 1\n[scopes."{name}"]\npaths = ["x/**"]\n')


@pytest.mark.parametrize("name", ["a_b", "docs2", "docs"])
def test_a_scope_name_that_is_a_tag_in_any_runner_is_accepted(name: str) -> None:
    text = f'version = 1\n[scopes."{name}"]\npaths = ["x/**"]\n'
    assert declared(text).scopes == ((name, ("x/**",)),)


def test_an_empty_scope_name_is_refused() -> None:
    assert "scope name" in problem('version = 1\n[scopes.""]\npaths = ["x/**"]\n')


@pytest.mark.parametrize(
    "entry",
    ["docs/*.md", "src/?.py", "[ab]/**", "**", "/abs/**", "a\\\\b", "a//b", "./a", "a/../b", ""],
)
def test_an_entry_that_is_neither_an_exact_path_nor_a_directory_is_refused(entry: str) -> None:
    text = f'version = 1\n[skip]\npaths = ["ok/**", "{entry}"]\n'
    assert "skip.paths[1]" in problem(text)


@pytest.mark.parametrize(
    ("first", "second"),
    [("a/**", "a/b/**"), ("a/b/**", "a/**"), ("a/**", "a/b.md"), ("x.md", "x.md")],
)
@pytest.mark.parametrize("skip_first", [True, False])
def test_a_skip_entry_that_overlaps_a_scope_entry_is_refused_naming_both(
    first: str, second: str, skip_first: bool
) -> None:
    tables = ["[skip]", "[scopes.docs]"] if skip_first else ["[scopes.docs]", "[skip]"]
    text = f'version = 1\n{tables[0]}\npaths = ["{first}"]\n{tables[1]}\npaths = ["{second}"]\n'
    found = problem(text)
    assert f"`{first}`" in found
    assert f"`{second}`" in found
    assert "skip" in found
    assert "scopes.docs" in found


@pytest.mark.parametrize(
    ("first", "second"),
    [("a/**", "a/b/**"), ("a/**", "a/b.md"), ("x.md", "x.md"), ("path1/**", "path1/**")],
)
def test_scopes_may_overlap_one_another(first: str, second: str) -> None:
    text = (
        f'version = 1\n[scopes.blah]\npaths = ["{first}"]\n[scopes.blech]\npaths = ["{second}"]\n'
    )
    assert declared(text).scopes == (("blah", (first,)), ("blech", (second,)))


def test_entries_with_a_shared_prefix_but_different_directories_do_not_overlap() -> None:
    text = 'version = 1\n[skip]\npaths = ["a/**"]\n[scopes.docs]\npaths = ["ab/**", "a.md"]\n'
    assert declared(text).skip == ("a/**",)


# Deciding what a change runs


def test_no_paths_run_the_full_check() -> None:
    assert guard.check_scope([], declared()).full


def test_no_declaration_runs_the_full_check() -> None:
    assert guard.check_scope(["openspec/a.md"], None).full


def test_a_path_in_no_group_runs_the_full_check() -> None:
    assert guard.check_scope(["openspec/a.md", "README.md"], declared()).full


def test_the_declaration_itself_runs_the_full_check_even_when_a_group_covers_it() -> None:
    covering = declared('version = 1\n[skip]\npaths = ["scripts/**"]\n')
    assert guard.check_scope([guard.CHECK_PATHS], covering).full


def test_only_skipped_paths_run_nothing() -> None:
    scope = guard.check_scope(
        ["openspec/changes/x/tasks.md", "openspec/changes/archive/2026-10-15-x/tasks.md"],
        declared(),
    )
    assert (scope.full, scope.names, scope.matched) == (False, (), ("openspec/**",))
    assert scope.label == "none"
    assert scope.args == ()


def test_scoped_and_skipped_paths_run_the_scopes_they_touch_sorted() -> None:
    scope = guard.check_scope(["docs/a.md", "openspec/b.md", "api/c.py"], declared())
    assert (scope.full, scope.names) == (False, ("api", "docs"))
    assert scope.label == "api,docs"
    assert scope.args == ("--scope", "api", "--scope", "docs")


OVERLAPPING = """\
version = 1

[scopes.blah]
paths = ["path1/**", "another/**"]

[scopes.blech]
paths = ["path1/**"]
"""


def test_a_path_in_two_overlapping_scopes_runs_both() -> None:
    scope = guard.check_scope(["path1/blah.py"], declared(OVERLAPPING))
    assert (scope.full, scope.names) == (False, ("blah", "blech"))
    assert scope.args == ("--scope", "blah", "--scope", "blech")


def test_a_path_in_one_of_two_overlapping_scopes_runs_that_one() -> None:
    assert guard.check_scope(["another/x"], declared(OVERLAPPING)).names == ("blah",)


def test_the_full_check_has_no_arguments() -> None:
    scope = guard.check_scope(["README.md"], declared())
    assert scope.label == "full"
    assert scope.args == ()


@pytest.mark.parametrize(
    ("path", "covered"),
    [
        ("openspec/a.md", True),
        ("openspec/deep/er/a.md", True),
        ("openspec", False),
        ("openspecx/a.md", False),
        ("plugins/runner-scripted/README.md", True),
        ("plugins/runner-scripted/README.md.bak", False),
        ("plugins/runner-scripted/other.md", False),
    ],
)
def test_a_directory_matches_at_any_depth_and_an_exact_entry_only_itself(
    path: str, covered: bool
) -> None:
    assert guard.check_scope([path], declared()).full is not covered


# A property: the decision is exactly the groups of the paths (design D4)

# Each top-level name is in no group (empty), the skip list, or one or more scopes.
MEMBERSHIP = st.one_of(
    st.just(frozenset[str]()),
    st.just(frozenset({"skip"})),
    st.frozensets(st.sampled_from(["a", "b", "c"]), min_size=1),
)


@given(
    layout=st.lists(st.tuples(MEMBERSHIP, st.booleans()), min_size=1, max_size=6),
    picks=st.lists(st.integers(min_value=0, max_value=6), max_size=8),
)
def test_the_decision_is_full_or_exactly_the_scopes_the_paths_are_in(
    layout: list[tuple[frozenset[str], bool]], picks: list[int]
) -> None:
    # Top-level names t0..tn, each a directory or a file; index len(layout) is a path under
    # `other/`, which no group names. A name in several scopes is listed in each of them.
    skip: list[str] = []
    scopes: dict[str, list[str]] = {}
    for index, (groups, is_dir) in enumerate(layout):
        entry = f"t{index}/**" if is_dir else f"t{index}.md"
        for group in sorted(groups):
            if group == "skip":
                skip.append(entry)
            else:
                scopes.setdefault(group, []).append(entry)
    declaration = guard.CheckPaths(
        skip=tuple(skip), scopes=tuple((name, tuple(entries)) for name, entries in scopes.items())
    )
    paths: list[str] = []
    memberships: list[frozenset[str]] = []
    for pick in picks:
        if pick >= len(layout):
            paths.append("other/x.py")
            memberships.append(frozenset())
        else:
            groups, is_dir = layout[pick]
            paths.append(f"t{pick}/x/y.py" if is_dir else f"t{pick}.md")
            memberships.append(groups)

    scope = guard.check_scope(paths, declaration)

    if not paths or frozenset() in memberships:
        assert scope.full
    else:
        assert not scope.full
        assert scope.names == tuple(sorted(set().union(*memberships) - {"skip"}))


# A property: a declaration of `paths` alone reads back as written (scope-test-directories 2.1)

ENTRY = st.sampled_from(["a/**", "a/b/**", "a.md", "b/c.md", "docs/**", "x/y/z.json"])
SCOPE_NAMES = st.sampled_from(["docs", "api", "blah", "b2", "x_y"])


def toml_list(entries: tuple[str, ...]) -> str:
    return "[" + ", ".join(f'"{entry}"' for entry in entries) + "]"


@given(
    skip=st.one_of(st.none(), st.lists(st.sampled_from(["openspec/**", "CHANGELOG.md"]))),
    scopes=st.dictionaries(SCOPE_NAMES, st.lists(ENTRY), max_size=4),
)
def test_a_declaration_of_paths_alone_reads_back_as_written(
    skip: list[str] | None, scopes: dict[str, list[str]]
) -> None:
    text = "version = 1\n"
    if skip is not None:
        text += f"[skip]\npaths = {toml_list(tuple(skip))}\n"
    for name, entries in scopes.items():
        text += f"[scopes.{name}]\npaths = {toml_list(tuple(entries))}\n"

    read = declared(text)

    assert read.skip == tuple(skip or ())
    assert read.scopes == tuple((name, tuple(entries)) for name, entries in scopes.items())


def test_this_repository_s_declaration_reads() -> None:
    assert declared((SCRIPTS / "check-paths.toml").read_text(encoding="utf-8")).scopes


# A scope's `tests` key (scope-test-directories 2.2, design D1-D3)

WITH_TESTS = """\
version = 1

[skip]
paths = ["openspec/**"]

[scopes.vcs_git]
paths = ["packages/vcs-git/**"]
tests = ["packages/vcs-git/tests/**", "packages/core/tests/**"]

[scopes.docs]
paths = ["docs/**"]

[scopes.blah]
paths = ["path1/**"]
tests = ["tests/shared/**", "tests/shared/**"]

[scopes.blech]
paths = ["path1/**"]
tests = ["tests/shared/**"]
"""


def test_a_scope_s_tests_are_read_in_file_order_and_its_paths_are_unchanged() -> None:
    read = declared(WITH_TESTS)
    assert read.scopes == (
        ("vcs_git", ("packages/vcs-git/**",)),
        ("docs", ("docs/**",)),
        ("blah", ("path1/**",)),
        ("blech", ("path1/**",)),
    )
    assert read.tests == (
        ("vcs_git", ("packages/vcs-git/tests/**", "packages/core/tests/**")),
        ("blah", ("tests/shared/**", "tests/shared/**")),
        ("blech", ("tests/shared/**",)),
    )


@given(
    scopes=st.dictionaries(SCOPE_NAMES, st.lists(ENTRY), max_size=4),
    tests=st.lists(st.sampled_from(["t/**", "u/v/**"]), min_size=1),
)
def test_adding_tests_to_a_scope_changes_nothing_else_it_reads(
    scopes: dict[str, list[str]], tests: list[str]
) -> None:
    plain = "version = 1\n" + "".join(
        f"[scopes.{name}]\npaths = {toml_list(tuple(entries))}\n"
        for name, entries in scopes.items()
    )
    with_tests = "version = 1\n" + "".join(
        f"[scopes.{name}]\npaths = {toml_list(tuple(entries))}\ntests = {toml_list(tuple(tests))}\n"
        for name, entries in scopes.items()
    )
    assert declared(with_tests).scopes == declared(plain).scopes
    assert declared(with_tests).skip == declared(plain).skip
    assert declared(with_tests).tests == tuple((name, tuple(tests)) for name in scopes)
    assert declared(plain).tests == ()


@pytest.mark.parametrize(
    ("tests", "names"),
    [
        ('"t/**"', "scopes.docs.tests is not a list"),
        ("[]", "scopes.docs.tests is empty"),
        ("[1]", "scopes.docs.tests[0]"),
        ('["t/**", "t/x.py"]', "scopes.docs.tests[1] `t/x.py`"),
        ('["**"]', "scopes.docs.tests[0] `**`"),
        ('["t/*/**"]', "scopes.docs.tests[0] `t/*/**`"),
        ('["t\\\\u/**"]', "scopes.docs.tests[0]"),
        ('["/t/**"]', "scopes.docs.tests[0] `/t/**`"),
        ('["t/../u/**"]', "scopes.docs.tests[0] `t/../u/**`"),
        ('["./t/**"]', "scopes.docs.tests[0] `./t/**`"),
        ('["t//u/**"]', "scopes.docs.tests[0] `t//u/**`"),
        ('[""]', "scopes.docs.tests[0]"),
    ],
)
def test_a_malformed_tests_entry_is_refused_naming_the_scope_and_entry(
    tests: str, names: str
) -> None:
    assert names in problem(f'version = 1\n[scopes.docs]\npaths = ["docs/**"]\ntests = {tests}\n')


def test_an_exact_file_in_tests_is_told_to_name_a_directory() -> None:
    found = problem('version = 1\n[scopes.docs]\npaths = ["docs/**"]\ntests = ["t/x.py"]\n')
    assert "`dir/**`" in found


def test_tests_under_skip_is_an_unknown_key() -> None:
    found = problem('version = 1\n[skip]\npaths = ["openspec/**"]\ntests = ["t/**"]\n')
    assert "skip has an unknown key `tests`" in found


def test_a_scope_s_other_keys_are_still_refused_naming_both_it_reads() -> None:
    found = problem('version = 1\n[scopes.docs]\npaths = ["docs/**"]\nwhy = "x"\n')
    assert "unknown key `why`" in found
    assert "`paths` and `tests`" in found


def test_the_fix_for_a_malformed_declaration_names_the_tests_key() -> None:
    with pytest.raises(guard.CheckPathsError) as error:
        guard.check_paths('version = 1\n[scopes.docs]\npaths = ["docs/**"]\ntests = []\n')
    assert "`tests`" in error.value.fix


# CI's entry: guard.py check-scope (commit-check-paths tasks 3.1-3.2, design D6)

CI_DECLARATION = """\
version = 1

[skip]
paths = ["openspec/**"]

[scopes.docs]
paths = ["docs/**"]

[scopes.api]
paths = ["api/**"]

[scopes.blah]
paths = ["path1/**", "another/**"]

[scopes.blech]
paths = ["path1/**"]
"""


def check_scope_cli(
    make_repo: Callable[[], Repo], stdin: str, declaration: str | None = CI_DECLARATION
) -> subprocess.CompletedProcess[str]:
    repo = make_repo()
    if declaration is not None:
        repo.write(guard.CHECK_PATHS, declaration)
    env = {key: value for key, value in clean_env().items() if key != "CLAUDE_PROJECT_DIR"}
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "guard.py"), "check-scope"],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        cwd=repo.path,
        env=env,
    )


@pytest.mark.parametrize(
    ("stdin", "scope", "args"),
    [
        ("openspec/a.md\n", "none", ""),
        ("docs/a.md\nopenspec/a.md\n", "docs", "--scope docs"),
        ("docs/a.md\napi/b.py\n", "api,docs", "--scope api --scope docs"),
        ("path1/blah.py\n", "blah,blech", "--scope blah --scope blech"),
        ("README.md\nopenspec/a.md\n", "full", ""),
        ("", "full", ""),
        ("\n\n", "full", ""),
    ],
)
def test_check_scope_prints_the_scope_and_the_check_s_arguments(
    make_repo: Callable[[], Repo], stdin: str, scope: str, args: str
) -> None:
    result = check_scope_cli(make_repo, stdin)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"scope={scope}\ncheck-args={args}\n"


def test_check_scope_without_a_declaration_answers_full(make_repo: Callable[[], Repo]) -> None:
    result = check_scope_cli(make_repo, "openspec/a.md\n", declaration=None)
    assert result.stdout == "scope=full\ncheck-args=\n"


def test_check_scope_with_a_malformed_declaration_fails_and_answers_nothing(
    make_repo: Callable[[], Repo],
) -> None:
    result = check_scope_cli(
        make_repo, "openspec/a.md\n", declaration='version = 1\n[skip]\npaths = ["docs/*.md"]\n'
    )
    assert result.returncode == 1
    assert result.stdout == ""
    with pytest.raises(guard.CheckPathsError) as error:
        guard.check_paths('version = 1\n[skip]\npaths = ["docs/*.md"]\n')
    assert error.value.decision().text() in result.stderr


# Scopes are test tags (commit-check-paths tasks 4.1-4.2, design D8, D9)

TAGGED = """\
version = 1

[skip]
paths = ["openspec/**"]

[scopes.docs]
paths = ["docs/**"]

[scopes.blah]
paths = ["path1/**"]

[scopes.blech]
paths = ["path1/**"]
"""


def violations(*reads: str, tags: frozenset[str] = frozenset()) -> list[str]:
    test = guard.TestReads(test="tests/test_x.py::test_y", tags=tags, reads=frozenset(reads))
    return guard.tag_violations(test, declared(TAGGED))


def test_the_marker_expression_joins_scopes_with_or() -> None:
    assert guard.marker_expression(("api", "docs")) == "api or docs"
    assert guard.marker_expression(("docs",)) == "docs"


def test_an_untagged_test_reading_a_scope_s_path_is_told_to_add_the_tag() -> None:
    found = violations("docs/runs.md")
    assert len(found) == 1
    assert "tests/test_x.py::test_y" in found[0]
    assert "docs/runs.md" in found[0]
    assert "`docs`" in found[0]


def test_a_test_reading_a_path_in_two_scopes_needs_both_tags() -> None:
    found = violations("path1/x.json", tags=frozenset({"blah"}))
    assert len(found) == 1
    assert "`blech`" in found[0]
    assert "`blah`" not in found[0]


@pytest.mark.parametrize("tags", [frozenset[str](), frozenset({"docs", "blah", "blech"})])
def test_a_test_reading_a_skipped_path_is_refused_whatever_its_tags(tags: frozenset[str]) -> None:
    found = violations("openspec/a.md", tags=tags)
    assert len(found) == 1
    assert "openspec/a.md" in found[0]
    assert "`openspec/**`" in found[0]


@pytest.mark.parametrize(
    ("reads", "tags"),
    [
        (("README.md",), frozenset[str]()),
        (("docs/runs.md",), frozenset({"docs"})),
        (("path1/x.json", "docs/a.md", "src/b.py"), frozenset({"blah", "blech", "docs"})),
        ((), frozenset[str]()),
    ],
)
def test_tags_that_cover_every_read_have_no_violations(
    reads: tuple[str, ...], tags: frozenset[str]
) -> None:
    assert violations(*reads, tags=tags) == []


# Which scopes a test file's directory tags it with, and which entries match nothing
# (scope-test-directories 2.4, design D4, D6)

DIRECTORIES = """\
version = 1

[scopes.vcs_git]
paths = ["packages/vcs-git/**"]
tests = ["packages/vcs-git/tests/**", "packages/core/tests/**"]

[scopes.blah]
paths = ["path1/**"]
tests = ["tests/a/**", "tests/shared/**"]

[scopes.blech]
paths = ["path1/**"]
tests = ["tests/shared/**"]

[scopes.docs]
paths = ["docs/**"]
"""


@pytest.mark.parametrize(
    ("path", "tags"),
    [
        ("packages/vcs-git/tests/test_x.py", {"vcs_git"}),
        ("packages/core/tests/deep/er/test_y.py", {"vcs_git"}),
        ("tests/a/test_z.py", {"blah"}),
        ("tests/ab/test_z.py", set()),
        ("tests/a", set()),
        ("tests/shared/test_s.py", {"blah", "blech"}),
        ("docs/test_d.py", set()),
        ("packages/vcs-git/src/x.py", set()),
    ],
)
def test_a_test_file_is_tagged_with_each_scope_whose_tests_cover_it(
    path: str, tags: set[str]
) -> None:
    assert guard.directory_tags(path, declared(DIRECTORIES)) == frozenset(tags)


def test_without_tests_keys_no_file_is_tagged() -> None:
    assert guard.directory_tags("docs/test_d.py", declared()) == frozenset()


def unmatched(files: list[str], roots: list[str]) -> list[tuple[str, str, str]]:
    found = guard.unmatched_tests(files, roots, declared(DIRECTORIES))
    return [(each.scope, each.entry, each.place) for each in found]


EVERY_SUITE = [
    "packages/vcs-git/tests/test_x.py",
    "packages/core/tests/test_y.py",
    "tests/a/test_z.py",
    "tests/shared/test_s.py",
]


def test_every_entry_matching_a_test_reports_nothing() -> None:
    assert unmatched(EVERY_SUITE, [""]) == []


def test_an_entry_with_no_test_under_it_is_reported_in_declaration_order() -> None:
    files = ["packages/vcs-git/tests/test_x.py", "tests/ab/test_z.py"]
    assert unmatched(files, [""]) == [
        ("vcs_git", "packages/core/tests/**", "scopes.vcs_git.tests[1]"),
        ("blah", "tests/a/**", "scopes.blah.tests[0]"),
        ("blah", "tests/shared/**", "scopes.blah.tests[1]"),
        ("blech", "tests/shared/**", "scopes.blech.tests[0]"),
    ]


def test_the_message_names_the_file_the_scope_the_entry_and_the_fix() -> None:
    (found,) = guard.unmatched_tests(
        [f for f in EVERY_SUITE if "core" not in f], [""], declared(DIRECTORIES)
    )
    assert "scripts/check-paths.toml" in found.message
    assert "scope `vcs_git`" in found.message
    assert "`packages/core/tests/**`" in found.message
    assert "scopes.vcs_git.tests[1]" in found.message
    assert "--scope vcs_git" in found.message
    assert "Correct the entry" in found.message


@pytest.mark.parametrize(
    ("roots", "reported"),
    [
        ([""], True),
        (["packages"], True),
        (["packages/core"], True),
        (["packages/core/tests"], True),
        (["packages/core/tests/test_y.py"], False),
        (["packages/core/tests/unit"], False),
        (["packages/vcs-git/tests"], False),
        (["packages/cor"], False),
        (["tests", "packages/vcs-git/tests/test_x.py"], False),
        ([], False),
    ],
)
def test_only_an_entry_inside_what_the_run_collects_is_checked(
    roots: list[str], reported: bool
) -> None:
    files = [f for f in EVERY_SUITE if "core" not in f]
    found = [entry for _, entry, _ in unmatched(files, roots)]
    assert ("packages/core/tests/**" in found) is reported
