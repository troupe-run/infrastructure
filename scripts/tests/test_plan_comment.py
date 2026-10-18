"""A plan too long to show is cut on purpose, never silently (spec: ci-apply; truncate-long-plans
design D1-D4, D6).

The fixtures are real. `comment-pr93.md` is #93's posted plan comment, whole (2,015 characters):
a plan under the limit must render exactly as the shell rendered it then. `plan-pr96.txt` is
#96's plan from run 39128121513's log (256,078 bytes, two resources), which the shell cut
silently at 60,000 bytes so that website's resource never appeared.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO
from hypothesis import given
from hypothesis import strategies as st

import plan_comment

SCRIPT = REPO / "scripts" / "plan_comment.py"
FIXTURES = Path(__file__).parent / "fixtures"
URL = "https://github.com/troupe-run/infrastructure/actions/runs/1/artifacts/2"

COMMENT_93 = (FIXTURES / "comment-pr93.md").read_text(encoding="utf-8")
PLAN_96 = (FIXTURES / "plan-pr96.txt").read_text(encoding="utf-8")
DETAILS = "<details><summary>Full plan</summary>\n\n```\n"
HEADERS_96 = [
    '  # github_repository_file.guard["troupe:scripts/guard.py"] will be updated in-place',
    '  # github_repository_file.guard["website:scripts/guard.py"] will be updated in-place',
]
PLAN_LINE_96 = "Plan: 0 to add, 2 to change, 0 to destroy."


def size(text: str) -> int:
    return len(text.encode("utf-8"))


def split_93() -> tuple[str, str]:
    """#93's comment as (what the workflow writes before the plan, the plan)."""
    head, rest = COMMENT_93.split(DETAILS)
    plan, tail = rest.rsplit("```\n", 1)
    assert tail == "</details>\n"
    return head, plan


def shown_plan(body: str) -> str:
    """The plan in a truncated body: the code block just before the note.

    No run of backticks in the plan is as long as its fence, so the line before the closing fence
    that equals it is the opening one.
    """
    before = body.split("\n\nTruncated: ")[0].removesuffix("\n</details>")
    fence = before.rsplit("\n", 1)[1]
    assert re.fullmatch(r"`{3,}", fence), f"no closing fence before the note: {fence!r}"
    inner = before[: -len(fence)]
    return inner[inner.rindex(f"{fence}\n") + len(fence) + 1 :]


def is_line_prefix(plan: str, shown: str) -> bool:
    return plan.startswith(shown) and (shown == "" or shown.endswith("\n"))


def test_a_plan_under_the_limit_renders_as_the_shell_did() -> None:
    head, plan = split_93()
    assert plan_comment.render(head, plan, URL, "comment") == COMMENT_93


def test_a_plan_under_the_limit_has_no_note_and_no_resource_list() -> None:
    head, plan = split_93()
    body = plan_comment.render(head, plan, URL, "comment")
    assert "Truncated" not in body
    assert "Resource changes" not in body
    assert URL not in body


def test_the_summary_target_shows_a_plan_that_fits_in_a_bare_code_block() -> None:
    head, plan = split_93()
    assert plan_comment.render(head, plan, URL, "summary") == f"{head}```\n{plan}```\n"


def test_a_plan_over_the_limit_stays_under_it() -> None:
    body = plan_comment.render("### head\n\n", PLAN_96, URL, "comment")
    assert size(body) <= plan_comment.COMMENT_LIMIT


def test_a_plan_over_the_limit_lists_every_resource_and_the_plan_line_above_the_plan() -> None:
    body = plan_comment.render("### head\n\n", PLAN_96, URL, "comment")
    above = body.split("<details>")[0]
    for line in [*HEADERS_96, PLAN_LINE_96]:
        assert f"{line}\n" in above
    assert "**Resource changes** (2):" in above


def test_a_plan_over_the_limit_is_cut_at_a_line_as_late_as_the_limit_allows() -> None:
    body = plan_comment.render("### head\n\n", PLAN_96, URL, "comment")
    shown = shown_plan(body)
    assert shown.endswith("\n")
    assert PLAN_96.startswith(shown)
    next_line = PLAN_96[len(shown) :].splitlines(keepends=True)[0]
    assert size(body) + size(next_line) > plan_comment.COMMENT_LIMIT


def test_a_plan_over_the_limit_says_how_much_is_shown_and_links_the_full_plan() -> None:
    body = plan_comment.render("### head\n\n", PLAN_96, URL, "comment")
    shown = shown_plan(body)
    lines = len(shown.splitlines())
    total_lines = len(PLAN_96.splitlines())
    assert (
        f"Truncated: showing the first {lines:,} of {total_lines:,} lines "
        f"({size(shown):,} of {size(PLAN_96):,} bytes). The full plan: [plan.txt]({URL})."
    ) in body


def test_a_truncated_comment_closes_its_code_block_and_details() -> None:
    body = plan_comment.render("### head\n\n", PLAN_96, URL, "comment")
    assert re.search(r"\n```\n</details>\n\nTruncated: ", body)
    assert body.count("<details>") == body.count("</details>") == 1


def test_the_summary_target_cuts_in_a_bare_code_block() -> None:
    body = plan_comment.render("### head\n\n", PLAN_96, URL, "summary", limit=60_000)
    assert "<details>" not in body
    assert size(body) <= 60_000
    assert PLAN_96.startswith(shown_plan(body))
    for line in [*HEADERS_96, PLAN_LINE_96]:
        assert f"{line}\n" in body.split("Truncated")[0]


def test_a_resource_list_that_cannot_fit_is_an_error_naming_the_limit() -> None:
    plan = "".join(f"  # null_resource.r{i} will be created\n" for i in range(100))
    plan += "Plan: 100 to add, 0 to change, 0 to destroy.\n"
    with pytest.raises(plan_comment.TooLongError, match=r"over the comment limit of 2,000 bytes"):
        plan_comment.render("### head\n\n", plan, URL, "comment", limit=2_000)


def test_a_backtick_run_inside_a_line_gets_a_longer_fence() -> None:
    plan = 'x = "a ```` b"\n'
    assert plan_comment.render("", plan, URL, "summary") == f"`````\n{plan}`````\n"


def test_a_backtick_run_at_a_line_start_gets_a_longer_fence() -> None:
    plan = "```python\nprint(1)\n```\n"
    assert plan_comment.render("", plan, URL, "summary") == f"````\n{plan}````\n"


def test_multibyte_characters_are_counted_in_bytes() -> None:
    # 50 lines of 40 two-byte characters: a cut that counted characters would go over in bytes.
    plan = "".join(f"  # r.é{i} will be created\n" for i in range(3)) + ("é" * 40 + "\n") * 50
    plan += "Plan: 3 to add, 0 to change, 0 to destroy.\n"
    body = plan_comment.render("", plan, URL, "comment", limit=2_500)
    assert "Truncated" in body
    assert size(body) <= 2_500


def test_resource_lines_are_the_plans_two_space_headers() -> None:
    plan = (
        "  # a.b will be created\n"
        '  # module.m.c["k"] must be replaced\n'
        "  # d.e has moved to d.f\n"
        "  # data.g.h will be read during apply\n"
        "        # (3 unchanged attributes hidden)\n"
        "   # not a header will be created\n"
        "Plan: 1 to add, 0 to change, 1 to destroy.\n"
        "Plan: a second Plan line isn't listed\n"
    )
    assert plan_comment.resource_lines(plan) == [
        "  # a.b will be created",
        '  # module.m.c["k"] must be replaced',
        "  # d.e has moved to d.f",
        "  # data.g.h will be read during apply",
        "Plan: 1 to add, 0 to change, 1 to destroy.",
    ]


LINE = st.one_of(
    st.from_regex(r"\A  # [a-z_.]{1,30} will be (created|destroyed)\Z", fullmatch=True),
    st.text(alphabet=st.characters(blacklist_categories=["Cs", "Cc"]), max_size=80),
)


@given(lines=st.lists(LINE, max_size=60), limit=st.integers(min_value=200, max_value=5_000))
def test_any_plan_is_shown_whole_or_cut_at_a_line_with_every_resource(
    lines: list[str], limit: int
) -> None:
    plan = "".join(f"{line}\n" for line in lines)
    try:
        body = plan_comment.render("# h\n\n", plan, URL, "comment", limit=limit)
    except plan_comment.TooLongError:
        return
    assert size(body) <= limit
    if "Truncated" not in body:
        assert plan in body
        return
    shown = shown_plan(body)
    assert is_line_prefix(plan, shown)
    above = body.split("<details>")[0]
    for line in plan_comment.resource_lines(plan):
        assert f"{line}\n" in above


def run(tmp_path: Path, plan: str, *extra: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    (tmp_path / "head.md").write_text("### head\n\n", encoding="utf-8")
    (tmp_path / "plan.txt").write_text(plan, encoding="utf-8")
    out = tmp_path / "comment.md"
    args = ["--head", "head.md", "--plan", "plan.txt", "--out", str(out), *extra]
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    return result, out


def test_the_script_writes_the_rendered_body(tmp_path: Path) -> None:
    result, out = run(tmp_path, PLAN_96, "--plan-url", URL, "--target", "comment")
    assert result.returncode == 0, result.stderr
    assert out.read_text(encoding="utf-8") == plan_comment.render(
        "### head\n\n", PLAN_96, URL, "comment"
    )


def test_the_script_refuses_a_link_that_is_not_a_url_and_writes_nothing(tmp_path: Path) -> None:
    result, out = run(tmp_path, "Plan: x\n", "--plan-url", "", "--target", "comment")
    assert result.returncode == 2
    assert "--plan-url" in result.stderr
    assert not out.exists()


def test_the_script_refuses_an_unknown_target(tmp_path: Path) -> None:
    result, out = run(tmp_path, "Plan: x\n", "--plan-url", URL, "--target", "issue")
    assert result.returncode == 2
    assert not out.exists()
