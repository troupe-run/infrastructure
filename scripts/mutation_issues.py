"""Keeps one test-quality issue per module under its threshold or baseline (spec: mutation-testing;
lint-mutation design D5, D7, D8).

Usage: uv run scripts/mutation_issues.py REPORT_DIR [--dry-run]

REPORT_DIR holds report-<repository>.json for each repository the run tested
(scripts/mutation_report.py) and quality-gates-<repository>.toml, that repository's quality-gates
file at the commit it tested. For each repository, each judged module (enough mutants, all of them
run within the budget) is under when its score is below the threshold, or below its baseline by
more than the tolerance (the ratchet, design D7). An under module keeps exactly one open
issue in its repository, labelled `test-quality`, found by the marker on its first line in an issue
the test-quality App opened: opened if there's none (at most `max_new_issues` a run), rewritten if
there is, with a comment when the score or the number of survivors changed. A module no longer under
gets a comment and its issue closed. A survivor new since the last run (design D8) names the merged
pull request that added it, "added in #n", which GitHub cross-references on that pull request: the
test-quality App writes issues only. Which pull request a commit came from is read with READ_TOKEN
(the workflow's own, read-only), since an issues-only token can't read pull requests.

The run never writes a baseline: its summary, and each module's issue, name the baselines it would
raise, for a person or agent to raise by pull request (design D10).

It exits 1 when it couldn't handle a repository, after handling the others, and 2 when it couldn't
start. Outside GitHub Actions, or with --dry-run, it only reads, and prints what it would do.
Its outputs, in GitHub Actions: `issue-urls`, a JSON list of the issues it opened, for the board
job; and the run's summary.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mutation_report as mr
import mutation_settings as ms

ORG = "troupe-run"
APP = "troupe-run-test-quality[bot]"
CREATOR = APP.replace("[", "%5B").replace("]", "%5D")
"""The App's login in a query string, its brackets encoded as dependabot_issues.py does."""
LABEL = "test-quality"
ISSUE_TYPE = "Task"
SETTINGS = Path(__file__).resolve().parent / "mutation.json"
SETTINGS_URL = "https://github.com/troupe-run/infrastructure/blob/main/scripts/mutation.json"
SHOWN = 30
"""How many survivors an issue lists before saying how many more there are."""
NO_TESTS_NOTE = {
    "mutmut": " in the test process (mutmut doesn't see code a test runs in a subprocess, so a "
    "function tested only that way counts here)",
    "stryker": "",
}
MARKER = re.compile(r"<!-- mutation-testing: (?P<repository>[\w.-]+):(?P<module>\S+) -->")
STATE = re.compile(
    r"<!-- mutation-testing-state: score=(?P<score>[\d.]+) survived=(?P<survived>\d+) -->"
)


# Judging (design D7)


@dataclass(frozen=True)
class Judgement:
    module: str
    score: float
    counted: int
    judged: bool  # enough mutants, all run within the budget
    under_threshold: bool
    below_baseline: bool  # fell below its baseline by more than the tolerance
    baseline: float | None
    raise_to: float | None  # the baseline a pull request should record, when it moves up

    @property
    def under(self) -> bool:
        return self.judged and (self.under_threshold or self.below_baseline)


def judge(
    name: str, module: mr.Module, baseline: ms.Baseline | None, settings: ms.Settings
) -> Judgement:
    judged = module.finished and module.counted >= settings.min_mutants
    score = module.score
    previous = baseline.score if baseline is not None else None
    # Both hold at once: a module first measured at 40% has an issue for being under 60%, and it
    # says so again, with its baseline, if it falls to 35% (design D7).
    under_threshold = judged and score < settings.threshold
    below_baseline = judged and previous is not None and score < previous - settings.tolerance
    raise_to = score if judged and (previous is None or score > previous) else None
    return Judgement(
        name, score, module.counted, judged, under_threshold, below_baseline, previous, raise_to
    )


# The issue's text (design D5)


def marker(repository: str, module: str) -> str:
    return f"<!-- mutation-testing: {repository}:{module} -->"


def title(judgement: Judgement, settings: ms.Settings) -> str:
    if judgement.below_baseline:
        why = f"below its {judgement.baseline:g}% baseline"
    else:
        why = f"under {settings.threshold:g}%"
    return f"Mutation score {judgement.score:g}% in {judgement.module} ({why})"


def code(text: str) -> str:
    """Text for inside a code span: a report's strings come from a run of other code, so a
    backtick can't end the span and let the rest render as Markdown."""
    return text.replace("`", "'")


def survivor_line(survivor: mr.Survivor, pulls: Mapping[str, int]) -> str:
    where = f"`{code(survivor.path)}:{survivor.line}`"
    added = ""
    if survivor.new and survivor.commit:
        pull = pulls.get(survivor.commit)
        added = f", added in #{pull}" if pull else f", added in {survivor.commit[:12]}"
    change = code(survivor.change.replace("\n", " / "))
    return f"- {where} `{code(survivor.name)}`{added}: `{change}`"


def body(
    repository: str,
    judgement: Judgement,
    module: mr.Module,
    settings: ms.Settings,
    run_url: str,
    tool: str,
    pulls: Mapping[str, int],
) -> str:
    survivors = sorted(module.survivors, key=lambda s: (not s.new, s.path, s.line))
    new = [s for s in survivors if s.new]
    lines = [
        marker(repository, judgement.module),
        f"<!-- mutation-testing-state: score={judgement.score:g} survived={module.survived} -->",
        "",
        f"`{judgement.module}` scored **{judgement.score:g}%** in the weekly mutation run "
        f"([run]({run_url})): {module.caught} caught of {module.counted} "
        f"({module.killed} killed, {module.timeout} timed out, {module.crashed} crashed), "
        f"{module.survived} survived, {module.no_tests} reached by no test"
        + (NO_TESTS_NOTE[tool] if module.no_tests else "")
        + ".",
        "",
    ]
    if judgement.below_baseline:
        lines.append(
            f"It fell below its recorded baseline of **{judgement.baseline:g}%** "
            f"(tolerance {settings.tolerance:g} points), which may only move up."
        )
    if judgement.under_threshold:
        lines.append(f"It's under the threshold of **{settings.threshold:g}%**.")
    lines += [
        "",
        f"Settings: [scripts/mutation.json]({SETTINGS_URL}). Baselines: `quality-gates.toml`'s "
        "`[mutation]` table in this repository, raised by pull request.",
        "",
    ]
    if new:
        lines += ["### New since the last run", "", *(survivor_line(s, pulls) for s in new), ""]
    rest = [s for s in survivors if not s.new]
    shown = rest[: max(0, SHOWN - len(new))]
    if rest:
        lines += ["### Surviving mutants", "", *(survivor_line(s, pulls) for s in shown)]
        more = len(rest) - len(shown)
        if more:
            how = (
                "`mutmut results` in a checkout of this repository"
                if tool == "mutmut"
                else "the Stryker HTML report in the run's artifacts"
            )
            lines.append(f"- and {more} more: {how} lists them all")
        lines.append("")
    lines.append(
        "A test that fails for a mutant kills it. Close this by raising the score: the weekly run "
        "closes it when the module is back at or over its threshold and baseline."
    )
    return "\n".join(lines) + "\n"


# Planning (design D5)


class Issue(NamedTuple):
    number: int
    url: str
    module: str
    score: float | None  # from the state line, when it has one
    survived: int | None


def was(value: float | int | None) -> str:
    return "?" if value is None else f"{value:g}"


class Action(NamedTuple):
    kind: str  # open, update, comment, close
    module: str
    issue: Issue | None
    title: str = ""
    body: str = ""
    comment: str = ""


@dataclass
class Plan:
    actions: list[Action] = field(default_factory=list)
    deferred: list[str] = field(default_factory=list)  # under, but past the cap on new issues
    not_judged: list[str] = field(default_factory=list)
    raises: dict[str, float] = field(default_factory=dict)


def plan_repository(
    report: mr.Report,
    baselines: Mapping[str, ms.Baseline],
    issues: Sequence[Issue],
    settings: ms.Settings,
    run_url: str,
    tool: str,
    pulls: Mapping[str, int],
) -> Plan:
    plan = Plan()
    open_issues = {issue.module: issue for issue in issues}
    opened = 0
    for name in sorted(report.modules):
        module = report.modules[name]
        judgement = judge(name, module, baselines.get(name), settings)
        issue = open_issues.get(name)
        if not judgement.judged:
            plan.not_judged.append(name)
            continue
        if judgement.raise_to is not None:
            plan.raises[name] = judgement.raise_to
        if judgement.under:
            text = body(report.repository, judgement, module, settings, run_url, tool, pulls)
            heading = title(judgement, settings)
            if issue is None:
                if opened >= settings.max_new_issues:
                    plan.deferred.append(name)
                    continue
                opened += 1
                plan.actions.append(Action("open", name, None, heading, text))
                continue
            plan.actions.append(Action("update", name, issue, heading, text))
            if issue.score != judgement.score or issue.survived != module.survived:
                plan.actions.append(
                    Action(
                        "comment",
                        name,
                        issue,
                        comment=f"This week: {judgement.score:g}% with {module.survived} surviving "
                        f"(was {was(issue.score)}% with {was(issue.survived)}). [Run]({run_url}).",
                    )
                )
        elif issue is not None:
            plan.actions.append(
                Action(
                    "close",
                    name,
                    issue,
                    comment=f"Back to {judgement.score:g}%, at or over its threshold and baseline "
                    f"([run]({run_url})). Closing.",
                )
            )
    return plan


def read_issue(found: Mapping[str, object], repository: str) -> Issue | None:
    """One of the App's issues, if its first line is a marker for this repository."""
    text = str(found.get("body") or "")
    first = MARKER.match(text.split("\n", 1)[0])
    if first is None or first["repository"] != repository:
        return None
    state = STATE.search(text)
    number = found.get("number")
    if not isinstance(number, int):
        return None
    return Issue(
        number=number,
        url=str(found.get("html_url") or found.get("url") or ""),
        module=first["module"],
        score=float(state["score"]) if state else None,
        survived=int(state["survived"]) if state else None,
    )


# GitHub


class GhResult(NamedTuple):
    code: int
    stdout: str
    stderr: str


Gh = Callable[[list[str]], GhResult]


def run_gh(args: list[str]) -> GhResult:
    done = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    return GhResult(done.returncode, done.stdout, done.stderr)


class GitHubError(Exception):
    """A read or write GitHub refused."""


def gh_json(gh: Gh, args: list[str]) -> object:
    result = gh(args)
    if result.code != 0:
        raise GitHubError(f"gh {' '.join(args[:3])} failed: {result.stderr.strip()}")
    return json.loads(result.stdout or "null")


def list_issues(gh: Gh, repository: str) -> list[Issue]:
    """The App's open issues labelled test-quality in `repository`, by their markers."""
    found = gh_json(
        gh,
        [
            "api",
            "--paginate",
            "--slurp",
            f"repos/{ORG}/{repository}/issues?state=open&labels={LABEL}&creator={CREATOR}&per_page=100",
        ],
    )
    pages = found if isinstance(found, list) else []
    issues = []
    for page in pages:
        for item in page if isinstance(page, list) else []:
            if isinstance(item, dict) and str(item.get("user", {}).get("login")) == APP:
                issue = read_issue(item, repository)
                if issue is not None:
                    issues.append(issue)
    return issues


def pulls_for(gh: Gh, repository: str, commits: set[str]) -> dict[str, int]:
    """The merged pull request each commit came from, where GitHub knows one (design D8)."""
    pulls = {}
    for commit in sorted(commits):
        found = gh_json(gh, ["api", f"repos/{ORG}/{repository}/commits/{commit}/pulls"])
        merged = (
            [p for p in found if isinstance(p, dict) and p.get("merged_at")]
            if isinstance(found, list)
            else []
        )
        if merged and isinstance(merged[0].get("number"), int):
            pulls[commit] = merged[0]["number"]
    return pulls


def apply(gh: Gh, repository: str, plan: Plan, opened: list[str]) -> None:
    """Make the plan's writes, adding each issue's URL to `opened` as soon as it's opened, so an
    issue opened before a later write fails still reaches the board (spec: mutation-testing)."""
    base = f"repos/{ORG}/{repository}/issues"
    for action in plan.actions:
        if action.kind == "open":
            made = gh_json(
                gh,
                [
                    "api",
                    base,
                    "-f",
                    f"title={action.title}",
                    "-f",
                    f"body={action.body}",
                    "-f",
                    f"labels[]={LABEL}",
                    "-f",
                    f"type={ISSUE_TYPE}",
                ],
            )
            if isinstance(made, dict):
                opened.append(str(made.get("html_url")))
        elif action.issue is not None and action.kind == "update":
            gh_json(
                gh,
                [
                    "api",
                    "-X",
                    "PATCH",
                    f"{base}/{action.issue.number}",
                    "-f",
                    f"title={action.title}",
                    "-f",
                    f"body={action.body}",
                ],
            )
        elif action.issue is not None and action.kind == "comment":
            gh_json(
                gh,
                ["api", f"{base}/{action.issue.number}/comments", "-f", f"body={action.comment}"],
            )
        elif action.issue is not None and action.kind == "close":
            gh_json(
                gh,
                ["api", f"{base}/{action.issue.number}/comments", "-f", f"body={action.comment}"],
            )
            gh_json(
                gh,
                [
                    "api",
                    "-X",
                    "PATCH",
                    f"{base}/{action.issue.number}",
                    "-f",
                    "state=closed",
                    "-f",
                    "state_reason=completed",
                ],
            )


# The run


def unattributed_section(report: mr.Report) -> list[str]:
    """Every survivor whose `git blame` failed, named rather than lost (#377)."""
    lost = mr.unattributed(report)
    if not lost:
        return []
    lines = [
        "",
        "Unattributed survivors: their `git blame` failed, so who last changed their line isn't "
        "known; the run's log says why.",
        "",
    ]
    lines += [f"- `{code(s.name)}` at `{code(s.path)}:{s.line}`" for s in lost]
    return lines


def crashed_section(report: mr.Report) -> list[str]:
    """Every crashed mutant the report names, for the owner to decide on exclusions (#361). A
    crash the report names ended only its own test process; one that ended the run never reaches
    the report: the step says how the run ended instead."""
    crashes = [c for _, m in sorted(report.modules.items()) for c in m.crashed_mutants]
    if not crashes:
        return []
    lines = [
        "",
        "Crashed mutants: each ended only its own test process, and the tool recorded it and went "
        "on. Excluding any (`# pragma: no mutate`) is the owner's decision.",
        "",
    ]
    for crash in crashes:
        status = "no exit code" if crash.exit_code is None else f"exit {crash.exit_code}"
        where = f"`{code(crash.path)}:{crash.line}`"
        change = code(crash.change.replace("\n", " / "))
        lines.append(f"- `{code(crash.name)}` at {where} ({status}): `{change}`")
    return lines


def summary(
    repository: str, report: mr.Report, plan: Plan, settings: ms.Settings, dry: bool
) -> str:
    verb = "would " if dry else ""
    lines = [f"## {repository} at {report.commit[:12]}", ""]
    lines += ["| Module | Score | Mutants | Judged |", "|---|---|---|---|"]
    for name, module in sorted(report.modules.items()):
        judged = "yes" if name not in plan.not_judged else "no"
        lines.append(f"| `{name}` | {module.score:g}% | {module.counted} | {judged} |")
    lines.append("")
    for action in plan.actions:
        lines.append(
            f"- {verb}{action.kind} `{action.module}`"
            + (f" (#{action.issue.number})" if action.issue else "")
        )
    if plan.deferred:
        lines.append(
            f"- under, but past the cap of {settings.max_new_issues} new issues: "
            + ", ".join(f"`{name}`" for name in plan.deferred)
            + " (raised by a later run)"
        )
    lines += crashed_section(report)
    lines += unattributed_section(report)
    if plan.raises:
        lines += [
            "",
            "Baselines to raise in this repository's `quality-gates.toml`, by pull request:",
            "",
            "```toml",
        ]
        for name, score in sorted(plan.raises.items()):
            module = report.modules[name]
            lines += [
                f'[mutation.baselines."{name}"]',
                f"score = {score:g}",
                f"mutants = {module.counted}",
                f'judged_at = "{report.commit}"',
                "",
            ]
        lines.append("```")
    return "\n".join(lines) + "\n"


def handle(
    repository: str,
    directory: Path,
    settings: ms.Settings,
    gh: Gh,
    run_url: str,
    dry: bool,
    opened: list[str],
    read_gh: Gh | None = None,
) -> str:
    """One repository's issues; the URLs of those it opens are added to `opened` as it goes."""
    report = mr.load_report(
        (directory / f"report-{repository}.json").read_text(encoding="utf-8"), repository
    )
    gates = directory / f"quality-gates-{repository}.toml"
    path = f"troupe-run/{repository}/quality-gates.toml"
    table = (
        ms.read_mutation_table(gates.read_text(encoding="utf-8"), path) if gates.exists() else {}
    )
    baselines = ms.load_baselines(table, path)
    issues = list_issues(gh, repository)
    commits = {s.commit for m in report.modules.values() for s in m.survivors if s.new and s.commit}
    reader = read_gh or gh
    pulls = pulls_for(reader, repository, commits) if commits else {}
    tool = settings.repositories[repository].tool
    plan = plan_repository(report, baselines, issues, settings, run_url, tool, pulls)
    if not dry:
        apply(gh, repository, plan, opened)
    return summary(repository, report, plan, settings, dry)


def reading_gh(token: str) -> Gh:
    """gh with another token, for the reads the App's issues-only token can't make."""

    def gh(args: list[str]) -> GhResult:
        done = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "GH_TOKEN": token},
        )
        return GhResult(done.returncode, done.stdout, done.stderr)

    return gh


def main(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] = os.environ,
    gh: Gh = run_gh,
    read_gh: Gh | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("reports", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    dry = args.dry_run or env.get("GITHUB_ACTIONS") != "true"
    try:
        settings = ms.load_settings(SETTINGS.read_text(encoding="utf-8"))
    except ms.SettingsError as error:
        print(f"mutation_issues: {SETTINGS.name}: {error}", file=sys.stderr)
        return 2
    run_url = (
        f"{env.get('GITHUB_SERVER_URL', 'https://github.com')}/{env.get('GITHUB_REPOSITORY', '')}"
        f"/actions/runs/{env.get('GITHUB_RUN_ID', '')}"
    )
    if read_gh is None and env.get("READ_TOKEN"):
        read_gh = reading_gh(env["READ_TOKEN"])
    failed: list[str] = []
    opened: list[str] = []
    text: list[str] = []
    for repository in sorted(settings.repositories):
        if not (args.reports / f"report-{repository}.json").exists():
            if (args.reports / f"skipped-{repository}").exists():
                continue  # a dispatch that named another repository
            failed.append(f"{repository}: no report (its job failed or timed out)")
            continue
        try:
            part = handle(repository, args.reports, settings, gh, run_url, dry, opened, read_gh)
        except (mr.ReportError, ms.SettingsError, GitHubError) as error:
            failed.append(f"{repository}: {error}")
            continue
        text.append(part)
    report = "\n".join(text) + "".join(f"\n**Not handled:** {problem}\n" for problem in failed)
    print(report)
    if summary_path := env.get("GITHUB_STEP_SUMMARY"):
        with open(summary_path, "a", encoding="utf-8") as out:
            out.write(report)
    if output := env.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as out:
            out.write(f"issue-urls={json.dumps(opened)}\n")
    for problem in failed:
        print(f"mutation_issues: {problem}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
