"""Tasks 3.1-3.5: the Claude Code rules, and the PreToolUse entry point fed real-shaped JSON."""

import io
import itertools
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import SCRIPTS, Repo, clean_env, git
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import guard

# Task 3.1: splitting a command


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("git status && git commit -m 'a b'", [["git", "status"], ["git", "commit", "-m", "a b"]]),
        ("ls || echo no; pwd", [["ls"], ["echo", "no"], ["pwd"]]),
        ("cat x | grep 'a;b'", [["cat", "x"], ["grep", "a;b"]]),
        ("echo one\necho two", [["echo", "one"], ["echo", "two"]]),
        ('git commit -m "it\'s && fine"', [["git", "commit", "-m", "it's && fine"]]),
        ("sleep 1 & echo bg", [["sleep", "1"], ["echo", "bg"]]),
    ],
)
def test_a_command_splits_into_its_simple_commands(command: str, expected: list[list[str]]) -> None:
    assert guard.split_command(command) == expected


def test_heredoc_bodies_are_dropped_before_parsing() -> None:
    command = "git commit -q -F - <<'EOF'\nfix: it's Windows' quirk\n\nbody\nEOF\ngit log -1"
    assert guard.split_command(command) == [
        ["git", "commit", "-q", "-F", "-", "<<EOF"],
        ["git", "log", "-1"],
    ]


def test_unbalanced_quotes_are_reported_not_guessed() -> None:
    with pytest.raises(ValueError, match="unbalanced"):
        guard.split_command("git commit -m 'oops")


def test_an_unparseable_git_command_is_refused() -> None:
    [decision] = guard.shell_decisions("git commit -m 'oops", Path.cwd())
    assert decision.rule == "command-unparseable"


def test_a_command_without_git_or_gh_isn_t_parsed_at_all() -> None:
    assert guard.shell_decisions("echo 'unbalanced", Path.cwd()) == [guard.ALLOW]


# Task 3.2: skip-hooks


@pytest.mark.parametrize(
    "command",
    [
        "git commit --no-verify -m 'fix: x'",
        "git commit -n -m 'fix: x'",
        "git commit -anm 'fix: x'",
        "git push --no-verify",
        "git -c core.hooksPath=/dev/null commit -m 'fix: x'",
        "git -c core.hookspath= commit -m 'fix: x'",
        "git config core.hooksPath /tmp/nothing",
        "git config --unset core.hooksPath",
        "GIT_X=1 /usr/bin/git commit --no-verify",
        "cd x && git commit --no-verify",
    ],
)
def test_skipping_or_redirecting_the_git_hooks_is_refused(command: str) -> None:
    rules = {d.rule for d in guard.shell_decisions(command, Path.cwd())}
    assert "skip-hooks" in rules


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m 'fix: no -n here'",
        "git commit -m -n",
        "git commit -am 'fix: x'",
        "git config core.hooksPath .githooks",
        "git config --get core.hooksPath",
        "git log -n 3",
        "git -c core.hooksPath=.githooks commit -m 'fix: x'",
    ],
)
def test_ordinary_git_commands_are_allowed(command: str) -> None:
    assert not any(d.refused for d in guard.shell_decisions(command, Path.cwd()))


# Task 3.3: pr-closes-issue


@pytest.mark.parametrize("keyword", ["Closes", "closes", "Fixes", "fixed", "Resolves", "resolve"])
def test_a_pr_body_with_a_closing_keyword_is_allowed(keyword: str) -> None:
    command = f"gh pr create --title 't' --body 'Does x.\n\n{keyword} #22'"
    assert not any(d.refused for d in guard.shell_decisions(command, Path.cwd()))


def test_a_pr_body_referring_to_another_repository_s_issue_is_allowed() -> None:
    command = "gh pr create --body 'Closes troupe-run/infrastructure#1'"
    assert not any(d.refused for d in guard.shell_decisions(command, Path.cwd()))


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --title 't' --body 'Does x. Related to #22'",
        "gh pr create --fill",
        "gh pr create --title 't'",
        "gh pr create --body-file -",
    ],
)
def test_a_pr_that_closes_no_issue_is_refused(command: str) -> None:
    rules = {d.rule for d in guard.shell_decisions(command, Path.cwd())}
    assert "pr-closes-issue" in rules


def test_a_missing_body_file_says_so_and_how_to_fix_it(tmp_path: Path) -> None:
    """Found live: a body file written by the same command, named through $S, doesn't exist yet."""
    decisions = guard.shell_decisions("gh pr create --body-file $S/pr.md", tmp_path)
    [decision] = [d for d in decisions if d.rule == "pr-closes-issue"]
    assert "doesn't exist when the command starts" in decision.problem
    assert "shell variables aren't expanded" in decision.fix


def test_a_body_file_is_read_relative_to_the_working_directory(tmp_path: Path) -> None:
    (tmp_path / "good.md").write_text("Closes #22\n", encoding="utf-8")
    (tmp_path / "bad.md").write_text("Mentions #22\n", encoding="utf-8")
    good = guard.shell_decisions("gh pr create --body-file good.md", tmp_path)
    bad = guard.shell_decisions("gh pr create --body-file=bad.md", tmp_path)
    assert not any(d.refused for d in good)
    assert "pr-closes-issue" in {d.rule for d in bad}


# What refuse-substituted-pr-body must not change (its design D5): which bodies are refused

LITERAL = st.text(alphabet=st.sampled_from("abc XYZ019.,:#-"), max_size=20)
EXPANSION = st.sampled_from(["$(cat notes)", "`cat notes`", "$BODY", "${BODY}", "$((1+2))"])
BODY_PART = st.one_of(LITERAL, EXPANSION, st.just("Closes #16"), st.just("Mentions #16"))


@st.composite
def pr_create_with_a_body(draw: st.DrawFn) -> str:
    text = "".join(draw(st.lists(BODY_PART, max_size=4)))
    if draw(st.booleans()):  # the issue's form: the body is a heredoc read by cat
        value = f"\"$(cat <<'EOF'\n{text}\nEOF\n)\""
    elif draw(st.booleans()) and not any(c in text for c in "$`"):
        value = f"'{text}'"
    else:
        value = f'"{text}"'
    form = draw(st.sampled_from(["--body {}", "--body={}", "-b {}"]))
    return "gh pr create --title t " + form.format(value)


def _body_word(words: list[str]) -> str:
    for index, word in enumerate(words):
        if word.startswith("--body="):
            return word.removeprefix("--body=")
        if word in ("--body", "-b"):
            return words[index + 1]
    raise AssertionError(f"no body in {words}")


@given(pr_create_with_a_body())
def test_a_pr_body_is_refused_exactly_when_the_word_the_check_sees_has_no_closing_line(
    command: str,
) -> None:
    [words] = guard.split_command(command)
    closes = guard.CLOSING.search(_body_word(words)) is not None
    refused = "pr-closes-issue" in {d.rule for d in guard.shell_decisions(command, Path.cwd())}
    assert refused is not closes


@pytest.mark.parametrize("body", ["'no closing line'", "'costs $5'", '"costs $5 or $"'])
def test_a_plain_body_with_no_closing_line_keeps_its_message(body: str) -> None:
    [decision] = [
        d
        for d in guard.shell_decisions(f"gh pr create --body {body}", Path.cwd())
        if d.rule == "pr-closes-issue"
    ]
    assert decision.problem == "the pull request's description doesn't close an issue."
    assert decision.fix == (
        "Add a line like 'Closes #22' to the description (--body or --body-file)."
    )


def test_a_body_file_that_closes_an_issue_goes_ahead(tmp_path: Path) -> None:
    (tmp_path / "pr.md").write_text("Does x.\n\nCloses #16\n", encoding="utf-8")
    decisions = guard.shell_decisions("gh pr create --title t --body-file pr.md", tmp_path)
    assert not any(d.refused for d in decisions)


# gh pr create's flags, read as gh (pflag) reads them (refuse-substituted-pr-body design D3). Each
# row's reading was checked against gh 2.102.0's --dry-run (tasks.md 2.1).


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["--body=x y"], [("--body", "x y")]),
        (["--body", "x y"], [("--body", "x y")]),
        (["--body="], [("--body", "")]),
        (["--draft"], [("--draft", None)]),
        (["--draft=true"], [("--draft", "true")]),
        (["-bClose"], [("-b", "Close")]),
        (["-b=Closes #1"], [("-b", "Closes #1")]),
        (["-b", "Closes #1"], [("-b", "Closes #1")]),
        (["-db", "Closes #1"], [("-d", None), ("-b", "Closes #1")]),
        (["-dbClose"], [("-d", None), ("-b", "Close")]),
        (["-df"], [("-d", None), ("-f", None)]),
        (["-d=true", "-b", "x"], [("-d", "true"), ("-b", "x")]),
        (["-dR", "troupe-run/.github"], [("-d", None), ("-R", "troupe-run/.github")]),
        (["-F=pr.md"], [("-F", "pr.md")]),
        (["--title", "-b", "--body", "x"], [("--title", "-b"), ("--body", "x")]),
        (["--title", "--fill", "--body", "x"], [("--title", "--fill"), ("--body", "x")]),
        (["-b", "-x"], [("-b", "-x")]),
        (["--attach", "--body", "x"], [("--attach", "--body")]),
        (["-zb", "x"], []),
        (["--", "-b", "x"], []),
        (["-b"], [("-b", None)]),
        (["--body"], [("--body", None)]),
        (["stray", "--web"], [("--web", None)]),
    ],
)
def test_pr_create_flags_reads_each_form_as_gh_does(
    args: list[str], expected: list[tuple[str, str | None]]
) -> None:
    assert guard.pr_create_flags(args) == expected


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --title t -b'Closes #22'",
        "gh pr create --title t -b='Closes #22'",
        "gh pr create --title t -db 'Closes #22'",
        "gh pr create --title t -dbCloses\\ \\#22",
        "gh pr create --title --fill --body 'Closes #22'",
    ],
)
def test_a_description_given_in_any_short_flag_form_that_closes_an_issue_goes_ahead(
    command: str,
) -> None:
    assert not any(d.refused for d in guard.shell_decisions(command, Path.cwd()))


def test_an_attached_body_file_that_closes_an_issue_goes_ahead(tmp_path: Path) -> None:
    (tmp_path / "pr.md").write_text("Closes #22\n", encoding="utf-8")
    decisions = guard.shell_decisions("gh pr create --title t -Fpr.md", tmp_path)
    assert not any(d.refused for d in decisions)


def test_an_attached_body_that_closes_no_issue_says_so() -> None:
    [decision] = [
        d
        for d in guard.shell_decisions("gh pr create --title t -b'no close'", Path.cwd())
        if d.rule == "pr-closes-issue"
    ]
    assert decision.problem == "the pull request's description doesn't close an issue."


# A body built by the shell can't be checked (#90; refuse-substituted-pr-body design D1, D2)

ISSUE_90_COMMAND = """gh pr create --title t --body "$(cat <<'EOF'
Closes #16

Does the thing.
EOF
)\""""


@pytest.mark.parametrize(
    "command",
    [
        ISSUE_90_COMMAND,
        'gh pr create --title t --body "$(cat notes)"',
        'gh pr create --title t --body "`cat notes`"',
        'gh pr create --title t --body="$(x)"',
        'gh pr create --title t --body "$BODY"',
        'gh pr create --title t --body "${BODY}"',
        'gh pr create --title t -b"$BODY"',
    ],
)
def test_a_body_built_by_the_shell_is_refused_as_one_that_can_t_be_checked(command: str) -> None:
    [decision] = [
        d for d in guard.shell_decisions(command, Path.cwd()) if d.rule == "pr-closes-issue"
    ]
    assert "built by the shell" in decision.problem
    assert "can't be checked before it's sent" in decision.problem
    assert "doesn't close" not in decision.problem
    assert "--body-file" in decision.fix
    assert "literal path" in decision.fix


def test_the_issue_s_command_is_denied_with_the_new_message(make_repo: Callable[[], Repo]) -> None:
    output = pre_tool_use(make_repo().path, "Bash", {"command": ISSUE_90_COMMAND})
    reason = denial_reason(output)
    assert reason.startswith("guard: pr-closes-issue:")
    assert "built by the shell" in reason


@pytest.mark.parametrize(
    "command",
    [
        'gh pr create --title t --body "Closes #16 $(cat notes)"',
        'gh pr create --title t --body "$BODY Closes #16"',
    ],
)
def test_an_expanded_body_whose_own_text_closes_an_issue_goes_ahead(command: str) -> None:
    assert not any(d.refused for d in guard.shell_decisions(command, Path.cwd()))


def test_a_body_file_after_an_expanded_body_is_what_s_read(tmp_path: Path) -> None:
    (tmp_path / "good.md").write_text("Closes #16\n", encoding="utf-8")
    command = 'gh pr create --title t --body "$(cat notes)" --body-file good.md'
    assert not any(d.refused for d in guard.shell_decisions(command, tmp_path))


def test_a_target_after_grouped_flags_is_read(troupe_clone: Repo) -> None:
    command = "gh pr create -dR troupe-run/.github --title t --body 'Updates a link.'"
    assert "pr-closes-issue" not in pr_rules(command, troupe_clone.path)


# What read-nested-commands must not change (its design D6, "Pin first"): a command with no nested
# command is refused for exactly what main's guard refused its pieces for, one at a time. The
# expected refusals were recorded from main's guard at 82efe9f, before the reader changed, so a
# change in how a plain command is judged fails here.

SKIP_HOOKS = ("skip-hooks", "this would skip or disable the repository's git hooks.")
MAIN_REFUSALS: dict[str, set[tuple[str, str]]] = {
    "git status": set(),
    "git log -n 3": set(),
    "git commit -m 'fix: a && b; c | d'": set(),
    "git commit --no-verify -m 'fix: x'": {SKIP_HOOKS},
    "gh issue view 1": set(),
    "gh auth token": {("owner-only", "agents don't handle the login's credentials.")},
    "gh pr merge 17 --rebase --admin": {
        (
            "owner-only",
            "only the owner merges a pull request, queues it, turns on its auto-merge, or merges "
            "past its rules.",
        )
    },
    "gh repo edit --visibility public": {
        ("owner-only", "only the owner changes the org's or a repository's administration.")
    },
    "gh frobnicate": {("gh-allow-list", "gh frobnicate isn't on the guard's gh allow-list.")},
    "gh pr create --title t --body 'Closes #1'": set(),
    "gh pr create --title t --body 'no closing line'": {
        ("pr-closes-issue", "the pull request's description doesn't close an issue.")
    },
    "echo 'a | b'": set(),
    'echo "x; y && z"': set(),
    "ls -la": set(),
}
QUOTED_HEREDOCS: dict[str, set[tuple[str, str]]] = {
    "cat <<'EOF'\n$(gh auth token) && `git commit --no-verify`\nEOF": set(),
    "git commit -q -F - <<'EOF'\nfix: it's (one) thing; really\nEOF": set(),
}
PLAIN_PIECES = {**MAIN_REFUSALS, **QUOTED_HEREDOCS}


def _refusals(command: str) -> set[tuple[str | None, str]]:
    return {(d.rule, d.problem) for d in guard.shell_decisions(command, Path.cwd()) if d.refused}


@pytest.mark.parametrize(("piece", "expected"), PLAIN_PIECES.items())
def test_each_plain_piece_is_refused_for_what_main_s_guard_refused_it_for(
    piece: str, expected: set[tuple[str, str]]
) -> None:
    assert _refusals(piece) == expected


@st.composite
def plain_command(draw: st.DrawFn) -> tuple[str, list[str]]:
    pieces = draw(st.lists(st.sampled_from(list(PLAIN_PIECES)), min_size=1, max_size=5))
    text = pieces[0]
    for previous, piece in itertools.pairwise(pieces):
        # A heredoc's closing line must end its line, so whatever follows it starts a new one.
        joiner = (
            "\n"
            if previous in QUOTED_HEREDOCS
            else draw(st.sampled_from([" && ", " || ", "; ", " | ", "\n"]))
        )
        text += joiner + piece
    return text, pieces


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(plain_command())
def test_a_command_with_nothing_nested_is_refused_for_what_main_refused_its_pieces_for(
    case: tuple[str, list[str]],
) -> None:
    command, pieces = case
    expected: set[tuple[str | None, str]] = set().union(*(PLAIN_PIECES[p] for p in pieces))
    assert _refusals(command) == expected


@pytest.mark.parametrize(
    "command",
    [
        # Reads inside other commands
        "git log $(git merge-base main HEAD)..HEAD",
        'cd "$(git rev-parse --show-toplevel)"',
        "for n in 1 2; do gh issue view $n; done",
        # Words that only name git or gh
        "which gh git",
        "command -v gh",
        "type gh",
        "echo gh",
        'grep -n "git" notes.md',
        "for c in gh git; do echo $c; done",
        # A heredoc the shell leaves alone
        "cat <<'EOF'\n$(gh auth token)\nEOF",
    ],
)
def test_reads_data_words_and_a_literal_heredoc_go_ahead(command: str) -> None:
    assert not any(d.refused for d in guard.shell_decisions(command, Path.cwd()))


# pr-closes-issue covers PRs into this repository only (#28)

TROUPE_ORIGIN = "git@github.com:troupe-run/troupe.git"
NO_CLOSE = "--title t --body 'Updates a link.'"


@pytest.fixture(autouse=True)
def no_gh_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """GH_REPO in the developer's shell mustn't change what these tests check."""
    monkeypatch.delenv("GH_REPO", raising=False)


@pytest.fixture
def troupe_clone(make_repo: Callable[[], Repo]) -> Repo:
    repo = make_repo()
    git(repo.path, "remote", "add", "origin", TROUPE_ORIGIN)
    return repo


def pr_rules(command: str, cwd: Path) -> set[str | None]:
    return {d.rule for d in guard.shell_decisions(command, cwd)}


@pytest.mark.parametrize(
    "command",
    [
        f"gh pr create --repo troupe-run/.github {NO_CLOSE}",
        f"gh pr create -R troupe-run/website {NO_CLOSE}",
        f"gh pr create --repo=troupe-run/.github {NO_CLOSE}",
        f"GH_REPO=troupe-run/.github gh pr create {NO_CLOSE}",
    ],
)
def test_a_pr_into_another_repository_that_closes_no_issue_is_allowed(
    troupe_clone: Repo, command: str
) -> None:
    assert "pr-closes-issue" not in pr_rules(command, troupe_clone.path)


@pytest.mark.parametrize(
    "target",
    [
        "troupe-run/troupe",
        "TROUPE-RUN/Troupe",
        "github.com/troupe-run/troupe",
        "https://github.com/troupe-run/troupe.git",
    ],
)
def test_a_pr_naming_this_repository_that_closes_no_issue_is_refused(
    troupe_clone: Repo, target: str
) -> None:
    command = f"gh pr create --repo {target} {NO_CLOSE}"
    assert "pr-closes-issue" in pr_rules(command, troupe_clone.path)


@pytest.mark.parametrize("target", ["not a repo", "troupe", "a/b/c/d", "ftp://x/y/z", ""])
def test_a_pr_with_an_unrecognisable_target_is_refused(troupe_clone: Repo, target: str) -> None:
    command = f"gh pr create --repo '{target}' {NO_CLOSE}"
    assert "pr-closes-issue" in pr_rules(command, troupe_clone.path)


def test_a_pr_from_a_repository_with_no_remotes_is_refused(make_repo: Callable[[], Repo]) -> None:
    command = f"gh pr create --repo troupe-run/.github {NO_CLOSE}"
    assert "pr-closes-issue" in pr_rules(command, make_repo().path)


def test_gh_repo_in_the_environment_names_the_target(
    troupe_clone: Repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GH_REPO", "troupe-run/.github")
    assert "pr-closes-issue" not in pr_rules(f"gh pr create {NO_CLOSE}", troupe_clone.path)


def test_repo_flag_beats_gh_repo_in_the_environment(
    troupe_clone: Repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GH_REPO", "troupe-run/.github")
    command = f"gh pr create --repo troupe-run/troupe {NO_CLOSE}"
    assert "pr-closes-issue" in pr_rules(command, troupe_clone.path)


def test_repo_flag_beats_gh_repo_set_for_the_command(troupe_clone: Repo) -> None:
    command = f"GH_REPO=troupe-run/.github gh pr create -R troupe-run/troupe {NO_CLOSE}"
    assert "pr-closes-issue" in pr_rules(command, troupe_clone.path)


def test_gh_repo_set_for_the_command_beats_the_environment(
    troupe_clone: Repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GH_REPO", "troupe-run/.github")
    command = f"GH_REPO=troupe-run/troupe gh pr create {NO_CLOSE}"
    assert "pr-closes-issue" in pr_rules(command, troupe_clone.path)


def test_a_repo_flag_inside_the_body_isn_t_read_as_the_target(troupe_clone: Repo) -> None:
    command = "gh pr create --title t --body '--repo' --head x"
    assert "pr-closes-issue" in pr_rules(command, troupe_clone.path)
    command = "gh pr create --title '-Rtroupe-run/.github' --body 'Updates a link.'"
    assert "pr-closes-issue" in pr_rules(command, troupe_clone.path)


def test_a_pr_into_the_upstream_of_a_fork_s_clone_is_checked(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    git(repo.path, "remote", "add", "origin", "https://github.com/someone/troupe.git")
    git(repo.path, "remote", "add", "upstream", TROUPE_ORIGIN)
    for target in ("someone/troupe", "troupe-run/troupe"):
        command = f"gh pr create --repo {target} {NO_CLOSE}"
        assert "pr-closes-issue" in pr_rules(command, repo.path)
    assert "pr-closes-issue" not in pr_rules(
        f"gh pr create --repo troupe-run/.github {NO_CLOSE}", repo.path
    )


def test_a_pr_from_outside_any_repository_naming_a_target_is_refused(tmp_path: Path) -> None:
    command = f"gh pr create --repo troupe-run/.github {NO_CLOSE}"
    assert "pr-closes-issue" in pr_rules(command, tmp_path / "missing")


# Repository-name normalisation (design decision 3)

TROUPE = ("github.com", "troupe-run", "troupe")


@pytest.mark.parametrize(
    "name",
    [
        "troupe-run/troupe",
        "github.com/troupe-run/troupe",
        "https://github.com/troupe-run/troupe",
        "https://github.com/troupe-run/troupe.git",
        "https://github.com/troupe-run/troupe/",
        "git@github.com:troupe-run/troupe.git",
        "ssh://git@github.com/troupe-run/troupe.git",
        "ssh://git@github.com:22/troupe-run/troupe.git",
        "  Troupe-Run/TROUPE.git  ",
    ],
)
def test_each_accepted_form_normalises_to_host_owner_name(name: str) -> None:
    assert guard.normalise_repository(name) == TROUPE


def test_a_host_other_than_github_is_kept() -> None:
    assert guard.normalise_repository("ghe.example.com/a/b") == ("ghe.example.com", "a", "b")


@pytest.mark.parametrize(
    "name",
    [
        "",
        "troupe",
        "a/b/c/d",
        "not a repo",
        "ftp://github.com/a/b",
        "https://github.com/a/b/pull/3",
        "https://github.com/a",
        "../b",
        "a/..",
        "/a/b",
    ],
)
def test_an_unrecognisable_name_normalises_to_none(name: str) -> None:
    assert guard.normalise_repository(name) is None


REPO_NAME = st.text(alphabet=st.sampled_from("abcXYZ019_.-"), min_size=1, max_size=20).filter(
    lambda part: part not in (".", "..") and not part.lower().endswith(".git")
)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])  # no_gh_repo is harmless
@given(owner=REPO_NAME, name=REPO_NAME)
def test_any_owner_and_name_normalise_the_same_in_every_form(owner: str, name: str) -> None:
    forms = [
        f"{owner}/{name}",
        f"github.com/{owner}/{name}",
        f"GitHub.com/{owner}/{name}",
        f"https://github.com/{owner}/{name}",
        f"https://github.com/{owner}/{name}.git",
        f"git@github.com:{owner}/{name}.git",
        f"ssh://git@github.com/{owner}/{name}.git",
    ]
    expected = ("github.com", owner.lower(), name.lower())
    assert {guard.normalise_repository(form) for form in forms} == {expected}


# Task 3.4: edit-branch-change


def test_editing_on_main_is_refused(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    decision = guard.edit_decision(repo.path, "README.md", "main")
    assert decision.rule == "edit-branch-change"
    assert "main has none" in decision.problem


def test_editing_on_a_branch_without_its_change_is_refused(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    decision = guard.edit_decision(repo.path, str(repo.path / "README.md"), "add-thing")
    assert decision.rule == "edit-branch-change"


def test_editing_on_the_change_s_branch_is_allowed(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    repo.change("add-thing")
    assert guard.edit_decision(repo.path, "src/x.py", "add-thing") == guard.ALLOW


def test_editing_after_the_change_is_archived_on_the_branch_is_allowed(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    repo.change("add-thing", archived_on="2026-10-11")
    assert guard.edit_decision(repo.path, "src/x.py", "add-thing") == guard.ALLOW


def test_editing_outside_the_repository_is_allowed(
    make_repo: Callable[[], Repo], tmp_path: Path
) -> None:
    repo = make_repo()
    outside = tmp_path / "notes.md"
    assert guard.edit_decision(repo.path, str(outside), "main") == guard.ALLOW


def test_editing_under_dot_git_is_refused_as_tampering(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    repo.change("add-thing")
    decision = guard.edit_decision(repo.path, ".git/troupe-guard/override.json", "add-thing")
    assert decision.rule == guard.TAMPER_RULE


# Task 3.5: the PreToolUse entry point, with real-shaped hook input


def pre_tool_use(repo: Path, tool: str, tool_input: dict[str, str]) -> dict[str, object] | None:
    payload = {
        "session_id": "test",
        "transcript_path": str(repo / "transcript.jsonl"),
        "cwd": str(repo),
        "permission_mode": "default",
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
        "tool_use_id": "toolu_test",
    }
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "guard.py"), "claude-pre-tool-use"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
        env=clean_env(),
    )
    output: dict[str, object] | None = json.loads(result.stdout) if result.stdout.strip() else None
    return output


def denial_reason(output: dict[str, object] | None) -> str:
    assert output is not None, "expected a deny"
    specific = output["hookSpecificOutput"]
    assert isinstance(specific, dict)
    assert specific["hookEventName"] == "PreToolUse"
    assert specific["permissionDecision"] == "deny"
    return str(specific["permissionDecisionReason"])


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
def test_an_edit_tool_on_main_is_denied_with_the_rule_s_message(
    make_repo: Callable[[], Repo], tool: str
) -> None:
    repo = make_repo()
    reason = denial_reason(pre_tool_use(repo.path, tool, {"file_path": str(repo.path / "a.py")}))
    assert reason.startswith("guard: edit-branch-change:")
    assert "fix:" in reason


def test_a_notebook_edit_on_main_is_denied(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    output = pre_tool_use(repo.path, "NotebookEdit", {"notebook_path": str(repo.path / "n.ipynb")})
    assert "edit-branch-change" in denial_reason(output)


def test_an_edit_on_the_change_s_branch_produces_no_output(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    repo.change("add-thing")
    repo.switch("add-thing")
    assert pre_tool_use(repo.path, "Write", {"file_path": str(repo.path / "a.py")}) is None


def test_a_bash_no_verify_is_denied(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    output = pre_tool_use(repo.path, "Bash", {"command": "git commit --no-verify -m 'fix: x'"})
    assert "skip-hooks" in denial_reason(output)


def test_a_powershell_no_verify_is_denied(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    output = pre_tool_use(
        repo.path, "PowerShell", {"command": "git commit --no-verify -m 'fix: x'"}
    )
    assert "skip-hooks" in denial_reason(output)


def test_an_ordinary_bash_command_produces_no_output(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    assert pre_tool_use(repo.path, "Bash", {"command": "git status"}) is None


def test_a_bash_pr_into_another_repository_is_allowed_and_into_this_one_denied(
    troupe_clone: Repo,
) -> None:
    other = f"gh pr create --repo troupe-run/.github {NO_CLOSE}"
    ours = f"gh pr create {NO_CLOSE}"
    assert pre_tool_use(troupe_clone.path, "Bash", {"command": other}) is None
    reason = denial_reason(pre_tool_use(troupe_clone.path, "Bash", {"command": ours}))
    assert reason.startswith("guard: pr-closes-issue:")


def test_a_tool_outside_any_repository_is_left_alone(tmp_path: Path) -> None:
    assert pre_tool_use(tmp_path, "Write", {"file_path": str(tmp_path / "a.py")}) is None


def test_other_tools_are_left_alone(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    assert pre_tool_use(repo.path, "Read", {"file_path": str(repo.path / "README.md")}) is None


def test_the_entry_point_writes_to_a_given_stream(make_repo: Callable[[], Repo]) -> None:
    repo = make_repo()
    stream = io.StringIO()
    payload: dict[str, object] = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(repo.path / "a.py")},
        "cwd": str(repo.path),
    }
    assert guard.run_claude_pre_tool_use(payload, stdout=stream) == 0
    assert "edit-branch-change" in stream.getvalue()


# Grants (guard-grants-gh design D4)


def reviewed(repo: Repo) -> Repo:
    """Put this guard on the repository's origin/main, so the hook running it is reviewed."""
    # Bytes, not text: the reviewed check compares bytes, and text mode rewrites line endings
    # on Windows.
    (repo.path / "scripts").mkdir(exist_ok=True)
    (repo.path / "scripts" / "guard.py").write_bytes((SCRIPTS / "guard.py").read_bytes())
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "-m", "chore: add the guard")
    git(repo.path, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repo


def grant_reason(output: dict[str, object] | None) -> str:
    assert output is not None, "expected a grant"
    specific = output["hookSpecificOutput"]
    assert isinstance(specific, dict)
    assert specific["hookEventName"] == "PreToolUse"
    assert specific["permissionDecision"] == "allow"
    return str(specific["permissionDecisionReason"])


def test_a_granted_bash_command_is_allowed_with_the_guard_s_reason(
    make_repo: Callable[[], Repo],
) -> None:
    repo = reviewed(make_repo())
    output = pre_tool_use(repo.path, "Bash", {"command": "gh pr ready 74"})
    assert grant_reason(output).startswith("guard: gh pr ready")


def test_a_granted_command_through_powershell_gets_no_grant(
    make_repo: Callable[[], Repo],
) -> None:
    repo = reviewed(make_repo())
    assert pre_tool_use(repo.path, "PowerShell", {"command": "gh pr ready 74"}) is None


def test_a_guard_that_differs_from_origin_main_grants_nothing(
    make_repo: Callable[[], Repo],
) -> None:
    repo = make_repo()
    repo.write("scripts/guard.py", "print('an older guard')\n")
    git(repo.path, "add", "-A")
    git(repo.path, "commit", "-q", "-m", "chore: add the guard")
    git(repo.path, "update-ref", "refs/remotes/origin/main", "HEAD")
    assert pre_tool_use(repo.path, "Bash", {"command": "gh pr ready 74"}) is None


def test_a_refused_command_is_still_denied_by_the_reviewed_guard(
    make_repo: Callable[[], Repo],
) -> None:
    repo = reviewed(make_repo())
    output = pre_tool_use(repo.path, "Bash", {"command": "gh auth status --show-token"})
    assert "owner-only" in denial_reason(output)


def test_a_refusal_excused_by_an_override_gets_no_grant(make_repo: Callable[[], Repo]) -> None:
    repo = reviewed(make_repo())
    guard.grant_override(repo.path, "owner-only", "testing")
    assert pre_tool_use(repo.path, "Bash", {"command": "gh auth status --show-token"}) is None


def test_a_command_the_guard_allows_but_doesn_t_grant_gets_nothing(
    make_repo: Callable[[], Repo],
) -> None:
    repo = reviewed(make_repo())
    assert pre_tool_use(repo.path, "Bash", {"command": "gh pr checkout 32"}) is None


# read-nested-commands design D7: the hook reads the PowerShell tool's commands as PowerShell


def test_the_hook_denies_a_gh_command_in_a_powershell_command_string(
    make_repo: Callable[[], Repo],
) -> None:
    command = 'Invoke-Expression "gh auth token"'
    reason = denial_reason(pre_tool_use(make_repo().path, "PowerShell", {"command": command}))
    assert reason.startswith("guard: owner-only:")


def test_the_hook_reads_a_backtick_in_a_powershell_command_as_an_escape(
    make_repo: Callable[[], Repo],
) -> None:
    command = 'Write-Output "`$(gh auth token)"'
    assert pre_tool_use(make_repo().path, "PowerShell", {"command": command}) is None
