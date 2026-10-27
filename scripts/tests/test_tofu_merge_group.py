"""tofu.yml on a merge queue's commit (spec: ci-apply; merge-queue design D5): `plan (pull request)`
reports as skipped, so the queue needs no second approval, nothing else runs, and the run never
shares main's concurrency group, where it would wait behind an apply awaiting approval.

GitHub evaluates the conditions, so the tests evaluate them the same way, for the context a
merge_group run has: the expressions here use only &&, ||, ==, !=, !cancelled(), format() and
context references, and the evaluator refuses anything else rather than guess."""

import re
from typing import Any

import pytest
import yaml
from conftest import REPO

TOFU = REPO / ".github" / "workflows" / "tofu.yml"
QUEUE_REF = "refs/heads/gh-readonly-queue/main/pr-7-0123456789abcdef0123456789abcdef01234567"
QUEUE_HEAD = "89abcdef0123456789abcdef0123456789abcdef"
REFERENCE = re.compile(r"\b(?:github|needs)(?:\.[A-Za-z_][\w-]*)+")


def tofu() -> dict[Any, Any]:
    loaded = yaml.safe_load(TOFU.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def evaluate(expression: str, context: dict[str, str]) -> object:
    """``expression`` as GitHub evaluates it for a run that isn't cancelled: && and || return an
    operand, as Python's and/or do; a reference to anything ``context`` doesn't hold is ''."""
    text = str(expression).strip()
    if text.startswith("${{") and text.endswith("}}"):
        text = text[3:-2]
    values: list[str] = []

    def lookup(match: re.Match[str]) -> str:
        values.append(context.get(match.group(0), ""))
        return f"_v[{len(values) - 1}]"

    text = REFERENCE.sub(lookup, text)
    text = text.replace("!cancelled()", "True").replace("&&", " and ").replace("||", " or ")
    text = text.replace("format(", "_f(")
    strings: list[str] = re.findall(r"'[^']*'", text)
    bare = re.sub(r"'[^']*'|_v\[\d+\]", " ", text)
    for token in re.split(r"\s+", bare.replace("(", " ").replace(")", " ").replace(",", " ")):
        assert token in ("", "and", "or", "==", "!=", "True", "False", "_f"), (token, expression)
    assert all("{" not in s or "{0}" in s for s in strings)

    def fmt(template: str, *args: object) -> str:
        return template.format(*args)

    return eval(text, {"__builtins__": {}}, {"_v": values, "_f": fmt})  # noqa: S307


def merge_group_context() -> dict[str, str]:
    return {
        "github.event_name": "merge_group",
        "github.ref": QUEUE_REF,
        "github.event.merge_group.head_sha": QUEUE_HEAD,
    }


def runs_on_merge_group(job: dict[str, Any], jobs: dict[str, Any]) -> bool:
    """Whether a job runs on a merge group: its own condition holds, and the jobs it needs ran (a
    job whose needs were skipped is skipped unless its condition is always())."""
    needs = job.get("needs", [])
    needs = [needs] if isinstance(needs, str) else list(needs)
    condition = job.get("if", "success()")
    if "always()" in str(condition):
        return True
    if any(not runs_on_merge_group(jobs[name], jobs) for name in needs):
        return False
    if condition == "success()":
        return True
    context = merge_group_context()
    for name in needs:
        context[f"needs.{name}.result"] = "success"
    return bool(evaluate(condition, context))


def test_tofu_runs_on_every_commit_a_merge_queue_tests() -> None:
    assert "merge_group" in tofu()[True]  # YAML 1.1 reads the key `on` as true


def test_on_a_merge_group_no_job_runs_and_pr_plan_reports_as_skipped() -> None:
    jobs = tofu()["jobs"]
    assert jobs["pr-plan"]["name"] == "plan (pull request)"
    running = [name for name, job in jobs.items() if runs_on_merge_group(job, jobs)]
    assert running == []


def test_the_evaluation_runs_pr_plan_on_a_pull_request_that_needs_a_plan() -> None:
    """The evaluation can say yes: a pull request that changes what OpenTofu reads is planned."""
    jobs = tofu()["jobs"]
    context = {
        "github.event_name": "pull_request",
        "needs.changes.result": "success",
        "needs.changes.outputs.plan": "true",
    }
    assert evaluate(jobs["pr-plan"]["if"], context) is True


def test_a_merge_group_s_concurrency_group_is_its_own() -> None:
    group = evaluate(tofu()["concurrency"]["group"].removeprefix("tofu-"), merge_group_context())
    assert group == f"mq-{QUEUE_HEAD}"


@pytest.mark.parametrize(
    ("context", "expected"),
    [
        ({"github.event_name": "pull_request", "github.event.pull_request.number": "7"}, "pr-7"),
        ({"github.event_name": "workflow_run"}, "main"),
        ({"github.event_name": "schedule"}, "main"),
        ({"github.event_name": "workflow_dispatch"}, "main"),
    ],
)
def test_every_other_run_keeps_its_concurrency_group(
    context: dict[str, str], expected: str
) -> None:
    assert evaluate(tofu()["concurrency"]["group"].removeprefix("tofu-"), context) == expected


def test_a_merge_group_s_run_is_never_cancelled_by_another() -> None:
    cancel = tofu()["concurrency"]["cancel-in-progress"]
    assert evaluate(cancel, merge_group_context()) is False
