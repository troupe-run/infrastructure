"""commit-check-paths tasks 1.1-1.2: the check-paths declaration, read and decided (D1-D5)."""

import pytest
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
