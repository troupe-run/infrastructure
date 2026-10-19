"""The rules reach every git and gh command a shell line runs (spec: development-workflow, "The
rules reach every command a shell line runs"; read-nested-commands design D1-D6).

The reader is checked against real shells, not only against itself (design D6): stub `gh` and
`git` programs, first on PATH, record each run's arguments and do nothing else, so no real git or
gh command runs."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import guard

SHELL_NAMES = ("bash", "zsh")
PROGRAMS = ("gh", "git")
SEPARATOR = "\x1f"
STUB = """#!/bin/sh
{{
  printf '%s' "{name}"
  for a in "$@"; do printf '\\037%s' "$a"; done
  printf '\\n'
}} >> "$STUB_LOG"
"""


def _shell(name: str) -> str | None:
    found = shutil.which(name)
    # On Windows, System32's bash.exe starts WSL, not Git Bash: a different machine's programs.
    if found is None or "system32" in found.lower():
        return None
    return found


SHELLS = [name for name in SHELL_NAMES if _shell(name)]
needs_bash = pytest.mark.skipif(_shell("bash") is None, reason="no bash on this machine")


class Stubs:
    """A directory of stub gh and git programs, and the log they write."""

    def __init__(self, root: Path) -> None:
        self.bin = root / "bin"
        self.bin.mkdir()
        self.log = root / "ran.log"
        self.cwd = root / "work"
        self.cwd.mkdir()
        for name in PROGRAMS:
            stub = self.bin / name
            stub.write_text(STUB.format(name=name), encoding="utf-8", newline="\n")
            stub.chmod(0o755)

    def run(self, command: str, shell: str) -> list[list[str]]:
        """The git and gh commands `shell` ran for `command`, in order, as argument lists."""
        self.log.write_text("", encoding="utf-8")
        executable = _shell(shell)
        assert executable is not None
        env = dict(os.environ)
        env["PATH"] = f"{self.bin}{os.pathsep}{env.get('PATH', '')}"
        env["STUB_LOG"] = str(self.log)
        # zsh -f skips the user's startup files, which could put the real programs first on PATH.
        flags = ["-f"] if shell == "zsh" else []
        subprocess.run(
            [executable, *flags, "-c", command],
            cwd=self.cwd,
            env=env,
            capture_output=True,
            timeout=30,
            check=False,
        )
        lines = self.log.read_text(encoding="utf-8").splitlines()
        return [line.split(SEPARATOR) for line in lines]


@pytest.fixture
def stubs(tmp_path: Path) -> Stubs:
    return Stubs(tmp_path)


# Task 2.1: the harness runs the stubs, and only the stubs


@needs_bash
@pytest.mark.parametrize("shell", SHELLS)
def test_the_stubs_record_each_git_and_gh_command_the_shell_runs(stubs: Stubs, shell: str) -> None:
    ran = stubs.run("gh auth token; git status --short 'a b'", shell)
    assert ran == [["gh", "auth", "token"], ["git", "status", "--short", "a b"]]


# Task 2.2: every rule reaches a git or gh command wherever it sits in the line

ALL = tuple(SHELL_NAMES)
NONE: tuple[str, ...] = ()


def _refusals(command: str, cwd: Path | None = None) -> set[tuple[str | None, str, str]]:
    decisions = guard.shell_decisions(command, cwd or Path.cwd())
    return {(d.rule, d.problem, d.fix) for d in decisions if d.refused}


def _judged(command: str) -> list[list[str]]:
    """The git and gh commands the guard reads in `command`, as the stubs would log them. The
    rules see a trailing redirection such as `2>/dev/null` as a word, as they always have; the
    program never does."""
    found = []
    for words in guard.commands_run(command):
        program, args = guard._program(words)
        if program in PROGRAMS:
            kept = [a for a in args if not (m := guard.REDIRECTION.match(a)) or not m.group(1)]
            found.append([program, *kept])
    return found


# (command, the command it runs that a rule refuses, the shells that can check the reading). A
# shell checks the reading only when every git and gh word in the line is literal and runs once.
NESTED = [
    # An owner-only command in a command substitution (#94's four)
    ("out=$(gh repo delete troupe-run/x --yes)", "gh repo delete troupe-run/x --yes", ALL),
    ('echo "$(gh repo delete troupe-run/x --yes)"', "gh repo delete troupe-run/x --yes", ALL),
    ("x=`gh auth token`", "gh auth token", ALL),
    ("echo $(gh pr merge 1 --admin)", "gh pr merge 1 --admin", ALL),
    # Nested substitutions
    ('echo "$(echo $(gh auth token))"', "gh auth token", ALL),
    ("echo $(echo `gh auth token`)", "gh auth token", ALL),
    ("echo `echo $(gh auth token)`", "gh auth token", ALL),
    ("echo `echo \\`gh auth token\\``", "gh auth token", ALL),
    # Process substitution and parameter defaults
    ("cat <(gh auth token)", "gh auth token", ALL),
    ('echo "${T:-$(gh auth token)}"', "gh auth token", ALL),
    ("cat =(gh auth token)", "gh auth token", ("zsh",)),
    # A heredoc the shell expands
    ("cat <<EOF\n$(gh auth token)\nEOF", "gh auth token", ALL),
    ("cat <<-EOF\n\t`gh auth token`\n\tEOF", "gh auth token", ALL),
    # Subshells, groups, loops and conditions
    ("(gh auth token)", "gh auth token", ALL),
    ("(cd . && gh auth token)", "gh auth token", ALL),
    ("{ gh auth token; }", "gh auth token", ALL),
    ("if gh auth token; then :; fi", "gh auth token", ALL),
    ("if true; then gh auth token; fi", "gh auth token", ALL),
    ("if false; then :; elif true; then gh auth token; fi", "gh auth token", ALL),
    ("if false; then :; else gh auth token; fi", "gh auth token", ALL),
    ("while gh auth token; do break; done", "gh auth token", ALL),
    ("until gh auth token; do :; done", "gh auth token", ALL),
    ("for i in 1; do gh auth token; done", "gh auth token", ALL),
    ("! gh auth token", "gh auth token", ALL),
    ("f(){ gh auth token; }; f", "gh auth token", ALL),
    ("f() { gh auth token; }\nf", "gh auth token", ALL),
    ("function f { gh auth token; }; f", "gh auth token", ALL),
    ("2>/dev/null gh auth token", "gh auth token", ALL),
    # Wrappers that run the command as written
    ("time gh auth token", "gh auth token", ALL),
    ("time -p gh auth token", "gh auth token", ("bash",)),
    ("command gh auth token", "gh auth token", ALL),
    ("command -p gh auth token", "gh auth token", NONE),  # -p searches the default PATH
    ("exec gh auth token", "gh auth token", ALL),
    ("env GH_REPO=troupe-run/x gh auth token", "gh auth token", ALL),
    ("env -u GH_REPO -- gh auth token", "gh auth token", ALL),
    ("nice -n 5 gh auth token", "gh auth token", ALL),
    ("nohup gh auth token", "gh auth token", ALL),
    ("timeout 5 gh auth token", "gh auth token", NONE),  # macOS has no timeout
    ("timeout -k 1 --foreground 5s gh auth token", "gh auth token", NONE),
    ("noglob gh auth token", "gh auth token", ("zsh",)),
    ("nocorrect gh auth token", "gh auth token", ("zsh",)),
    # A shell's command string
    ('bash -c "gh auth token"', "gh auth token", ALL),
    ("sh -c 'gh auth token'", "gh auth token", ALL),
    ("bash -ec 'gh auth token'", "gh auth token", ALL),
    ('zsh -f -c "gh auth token"', "gh auth token", ALL),
    ('eval "gh auth token"', "gh auth token", ALL),
    ("eval gh auth token", "gh auth token", ALL),
    # A script fed to a shell by a heredoc
    ("bash <<'EOF'\ngh auth token\nEOF", "gh auth token", ALL),
    ("bash <<EOF\ngh auth token\nEOF", "gh auth token", ALL),
    ("sh -s <<\\EOF\ngh auth token\nEOF", "gh auth token", ALL),
    # Git's hooks skipped from inside another command
    ("(git commit --no-verify -m 'fix: x')", "git commit --no-verify -m 'fix: x'", ALL),
    ("x=$(git commit --no-verify -m 'fix: x')", "git commit --no-verify -m 'fix: x'", ALL),
    # A pull request opened inside a substitution
    (
        "url=$(gh pr create --title t --body 'no closing line')",
        "gh pr create --title t --body 'no closing line'",
        ALL,
    ),
]


@pytest.mark.parametrize(("command", "inner", "shells"), NESTED)
def test_a_nested_command_is_refused_as_it_is_on_its_own(
    command: str, inner: str, shells: tuple[str, ...]
) -> None:
    alone = _refusals(inner)
    assert alone, f"{inner!r} should be refused on its own"
    assert _refusals(command) == alone


@needs_bash
@pytest.mark.parametrize(
    ("command", "shell"),
    [(command, shell) for command, _, shells in NESTED for shell in shells if shell in SHELLS],
)
def test_the_guard_reads_the_git_and_gh_commands_the_shell_runs(
    stubs: Stubs, command: str, shell: str
) -> None:
    assert sorted(_judged(command)) == sorted(stubs.run(command, shell))


@pytest.mark.parametrize(
    "command",
    [
        "git log $(git merge-base main HEAD)..HEAD",
        'cd "$(git rev-parse --show-toplevel)"',
        "for n in 1 2; do gh issue view $n; done",
        "n=$(gh issue view 1 --json title -q .title) && echo $n",
        "(git status && gh pr list)",
    ],
)
def test_reads_inside_other_commands_go_ahead(command: str) -> None:
    assert not _refusals(command)


def test_the_cat_in_a_body_built_by_the_shell_is_not_refused() -> None:
    command = "gh pr create --title t --body \"$(cat <<'EOF'\nDoes the thing.\nEOF\n)\""
    [refusal] = _refusals(command)
    rule, problem, _ = refusal
    assert rule == "pr-closes-issue"
    assert "built by the shell" in problem
    assert "cat" in [guard._program(words)[0] for words in guard.commands_run(command)]


@pytest.mark.parametrize(
    "command", ["n=$(gh issue view 1)", "(gh issue view 1)", "{ gh pr ready 74; }"]
)
def test_a_nested_command_is_never_granted(command: str) -> None:
    assert not guard.grantable(command, Path.cwd(), Path.cwd())


# Task 2.4: composed nestings, read as bash runs them

# Each form wraps one command ({c}, or {q} for it as one quoted word). The forms that end in a
# heredoc's closing line only go outermost, since nothing may follow that line on it.
FORMS = [
    "x=$({c})",
    'echo "$({c})"',
    "echo $({c})",
    "cat <({c})",
    "({c})",
    "{{ {c}; }}",
    "if {c}; then :; fi",
    "if true; then {c}; fi",
    "for i in 1; do {c}; done",
    "! {c}",
    "time {c}",
    "command {c}",
    "env A=1 {c}",
    "nice -n 1 {c}",
    "nohup {c}",
    "f(){{ {c}; }}; f",
    'echo "${{T:-$({c})}}"',
    "bash -c {q}",
    "bash -ec {q}",
    "eval {q}",
    "A=1 {c} 2>/dev/null",
]
SIMPLE_ONLY = {"command {c}", "env A=1 {c}", "nice -n 1 {c}", "nohup {c}", "A=1 {c} 2>/dev/null"}
"""Forms that wrap a simple command: around a subshell or group they're a syntax error."""
EXTERNAL = {"env A=1 {c}", "nice -n 1 {c}", "nohup {c}"}
"""Programs, not shell words: they can't run a builtin such as eval."""
WRAPPERS = EXTERNAL | {"command {c}"}
"""Each takes the first word after it as the program, so an assignment there is a program's name."""
BACKTICK_FORM = "x=`{c}`"
OUTERMOST_FORMS = ["cat <<EOF\n$({c})\nEOF", "bash <<'EOF'\n{c}\nEOF", "bash <<EOF\n{c}\nEOF"]
ARGUMENT = st.one_of(
    st.sampled_from(
        ["status", "auth", "token", "-x", "--json", "a b", "it's", "x;y", "a|b", "(z)"]
    ),
    st.text(alphabet=st.sampled_from("abz09-_./=:"), min_size=1, max_size=6),
)


@st.composite
def nested_command(draw: st.DrawFn) -> str:
    program = draw(st.sampled_from(PROGRAMS))
    args = draw(st.lists(ARGUMENT, max_size=3))
    command = shlex.join([program, *args])
    simple = program_first = True
    assigns_first = False
    for _ in range(draw(st.integers(min_value=1, max_value=3))):
        forms = [f for f in FORMS if simple or f not in SIMPLE_ONLY]
        forms = [f for f in forms if program_first or f not in EXTERNAL]
        forms = [f for f in forms if assigns_first is False or f not in WRAPPERS]
        forms += [] if "`" in command else [BACKTICK_FORM]
        form = draw(st.sampled_from(forms))
        command = form.format(c=command, q=shlex.quote(command))
        simple = not form.startswith(("(", "{", "if ", "for ", "! ", "time ", "f()"))
        assigns_first = form.startswith("A=1")
        program_first = simple and not assigns_first and not form.startswith(("eval", "command"))
    if draw(st.booleans()):
        command = draw(st.sampled_from(OUTERMOST_FORMS)).format(c=command)
    return command


@pytest.fixture(scope="module")
def shared_stubs(tmp_path_factory: pytest.TempPathFactory) -> Stubs:
    return Stubs(tmp_path_factory.mktemp("stubs"))


@needs_bash
@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(command=nested_command())
def test_composed_nestings_are_read_as_bash_runs_them_or_refused_as_unreadable(
    shared_stubs: Stubs, command: str
) -> None:
    try:
        judged = _judged(command)
    except ValueError:
        assert "command-unparseable" in {rule for rule, _, _ in _refusals(command)}
        return
    assert sorted(judged) == sorted(shared_stubs.run(command, "bash"))


def test_an_unparseable_command_whose_gh_is_only_in_a_heredoc_is_refused() -> None:
    """Found by the composed test: the git-or-gh test looked at the text without heredoc bodies,
    so a script fed to bash that only it mentioned gh in was allowed."""
    command = "bash <<EOF\necho $(gh auth token 'it\nEOF"
    assert {rule for rule, _, _ in _refusals(command)} == {"command-unparseable"}
