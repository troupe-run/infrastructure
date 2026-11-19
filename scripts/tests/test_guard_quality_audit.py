"""The quality gates' dependency audit and weekly report (spec: quality-gates; quality-gates design
D7, D8). Split from test_guard_quality_gates.py with the code it tests (gate-files design D8).

Named test_guard_*: scripts/quality_audit.py is delivered with the guard and runs in troupe's check
on every OS, so the guard's legs run these tests on each OS and Python too.

Tool output is real: pip-audit, OSV and npm audit were captured on 2026-11-17
(fixtures/quality-gates).
"""

# ruff: noqa: F811 (each test's `repo` parameter is the fixture imported below, not a redefinition)

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from quality_gates_support import (  # noqa: F401 (pytest's fixtures, imported to be found)
    CONFIG,
    FIXTURES,
    LIZARD,
    commit,
    fixture,
    git,
    no_inherited_git,
    repo,
)

import quality_audit as qa
import quality_gates as qg

# --- Audit ----------------------------------------------------------------------------------------


def osv_fixtures(advisory_id: str) -> str | None:
    """The severity from the OSV records captured for the requests probe."""
    path = FIXTURES / f"osv-{advisory_id}.json"
    if not path.exists():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    severity: str = record["database_specific"]["severity"]
    return severity.lower()


AUDIT = qg.parse_config(CONFIG).audit


def test_pip_audit_advisories_read_severity_through_the_github_alias() -> None:
    looked_up: list[str] = []

    def lookup(advisory_id: str) -> str | None:
        looked_up.append(advisory_id)
        return osv_fixtures(advisory_id)

    advisories = qa.pip_audit_advisories(fixture("pip-audit-requests-2.19.0.json"), lookup)
    # pip-audit lists each of the five advisories twice; each is reported, and looked up, once.
    assert len(looked_up) == 5
    assert sorted((a.id, a.severity, a.fixed_in) for a in advisories) == [
        ("GHSA-9hjg-9r4m-mvj7", "moderate", "2.32.4"),
        ("GHSA-9wx4-h78v-vm56", "moderate", "2.32.0"),
        ("GHSA-gc5v-m9x4-r6x2", "moderate", "2.33.0"),
        ("GHSA-j8r2-6x86-q33q", "moderate", "2.31.0"),
        ("GHSA-x84v-xcm2-53pg", "high", "2.20.0"),
    ]


def test_a_fixable_high_advisory_blocks_and_moderates_dont() -> None:
    advisories = qa.pip_audit_advisories(fixture("pip-audit-requests-2.19.0.json"), osv_fixtures)
    assert [a.text() for a in qa.blocking(advisories, AUDIT)] == [
        "requests 2.19.0: GHSA-x84v-xcm2-53pg (high, fixed in 2.20.0)"
    ]


def test_a_high_advisory_with_no_fix_doesnt_block() -> None:
    advisory = qa.Advisory("p", "1.0", "GHSA-x", "critical", None)
    assert qa.blocking([advisory], AUDIT) == []


def test_an_advisory_with_no_known_severity_blocks() -> None:
    report = fixture("pip-audit-requests-2.19.0.json")
    advisories = qa.pip_audit_advisories(report, lambda _: None)
    assert {a.severity for a in advisories} == {"unknown"}
    assert len(qa.blocking(advisories, AUDIT)) == 5


def osv_records(advisory_id: str) -> dict[str, object] | None:
    """The OSV records captured on 2026-11-17 and 18, as OSV would answer, or None for a 404."""
    path = FIXTURES / f"osv-{advisory_id}.json"
    if not path.exists():
        return None
    record: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    return record


WEBSITE = "npm-audit-website-2026-11-18.json"
"""website's lock on 2026-11-18: picomatch's high advisory has no patched version, and npm marks it
fixable by downgrading astro from 7.4.7 to 5.3.0 (#330)."""


def test_npms_downgrade_of_a_dependent_isnt_a_fix() -> None:
    """Spec: quality-gates, "npm offers a downgrade of a dependent as the fix" (#330)."""
    advisories = qa.npm_audit_advisories(fixture(WEBSITE), osv_records)
    picomatch = next(a for a in advisories if a.package == "picomatch")
    assert (picomatch.id, picomatch.severity, picomatch.fixed_in) == (
        "GHSA-fc5q-39xc-vjpf",
        "high",
        None,
    )
    assert qa.blocking(advisories, AUDIT) == []


def test_each_root_advisory_is_listed_once_with_osvs_fixed_version() -> None:
    advisories = qa.npm_audit_advisories(fixture(WEBSITE), osv_records)
    # npm lists 30 vulnerable packages; four advisories are their roots.
    assert sorted((a.package, a.id, a.severity, a.fixed_in) for a in advisories) == [
        ("glob", "GHSA-3g3m-2fjr-6pw4", "moderate", "14.0.2"),
        ("minimatch", "GHSA-g3hv-75wg-m249", "moderate", "11.0.1"),
        ("picomatch", "GHSA-fc5q-39xc-vjpf", "high", None),
        ("postcss-selector-parser", "GHSA-rj75-hqrm-r3gf", "moderate", "6.1.5"),
    ]


def test_an_advisory_its_own_package_fixes_blocks() -> None:
    advisories = qa.npm_audit_advisories(fixture("npm-audit-lodash-minimist.json"), osv_records)
    failing = qa.blocking(advisories, AUDIT)
    assert {a.package for a in failing} == {"lodash", "minimist"}
    assert all(a.fixed_in is not None for a in failing)


def test_an_advisory_osv_doesnt_know_has_no_known_fix() -> None:
    advisories = qa.npm_audit_advisories(fixture(WEBSITE), lambda _: None)
    assert {a.fixed_in for a in advisories} == {None}
    assert qa.blocking(advisories, AUDIT) == []


def with_picomatch_fix(fix: object) -> dict[str, object]:
    """website's real report, with npm's fix for picomatch set to `fix`."""
    report = fixture(WEBSITE)
    vulnerabilities = report["vulnerabilities"]
    assert isinstance(vulnerabilities, dict)
    vulnerabilities["picomatch"] = {**vulnerabilities["picomatch"], "fixAvailable": fix}
    return report


def test_without_an_osv_record_npms_fix_counts_when_it_names_the_package_itself() -> None:
    """Spec: quality-gates, "OSV has no record, and npm's fix names the vulnerable package" (owner,
    2026-11-18, #331's review)."""
    fix = {"name": "picomatch", "version": "4.0.8", "isSemVerMajor": False}
    advisories = qa.npm_audit_advisories(with_picomatch_fix(fix), lambda _: None)
    picomatch = next(a for a in advisories if a.package == "picomatch")
    assert picomatch.fixed_in == "4.0.8"
    assert qa.blocking(advisories, AUDIT) == [picomatch]


def test_without_an_osv_record_npms_fix_doesnt_count_when_it_names_a_dependent() -> None:
    # The real report: npm's fix for picomatch names astro@5.3.0, a downgrade of a dependent.
    advisories = qa.npm_audit_advisories(fixture(WEBSITE), lambda _: None)
    assert next(a for a in advisories if a.package == "picomatch").fixed_in is None
    assert qa.blocking(advisories, AUDIT) == []


def test_an_osv_record_wins_over_npms_fix() -> None:
    fix = {"name": "picomatch", "version": "4.0.8", "isSemVerMajor": False}
    advisories = qa.npm_audit_advisories(with_picomatch_fix(fix), osv_records)
    assert next(a for a in advisories if a.package == "picomatch").fixed_in is None


def test_osvs_fixed_version_is_the_lowest_for_that_package() -> None:
    record = osv_records("GHSA-rj75-hqrm-r3gf")
    assert record is not None
    assert qa.osv_fixed_version(record, "postcss-selector-parser") == "6.1.5"
    assert qa.osv_fixed_version(record, "some-other-package") is None


def test_an_unreachable_osv_fails_the_npm_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> object:
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    with pytest.raises(qg.GateError, match="couldn't read GHSA-"):
        qa.npm_audit_advisories(fixture(WEBSITE), qa.osv_record)


def test_an_npm_error_is_an_error() -> None:
    with pytest.raises(qg.GateError, match="npm audit failed"):
        qa.npm_audit_advisories({"error": {"code": "ENOLOCK"}}, osv_records)


def test_only_a_changed_lock_file_is_audited(repo: Path) -> None:
    base = commit(repo, {"uv.lock": "version = 1\n"})
    assert qa.changed_lock_files(repo, base, ["uv.lock"]) == []
    (repo / "uv.lock").write_text("version = 2\n", encoding="utf-8")
    assert qa.changed_lock_files(repo, base, ["uv.lock"]) == ["uv.lock"]


def test_the_audit_command_skips_without_a_changed_lock_file(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = commit(repo, {"uv.lock": "version = 1\n"})
    assert (
        qg.main(["audit", "--base", base, "--uv", "false", "--pip-audit", "false"], root=repo) == 0
    )
    assert "no lock file changed" in capsys.readouterr().out


def test_a_failing_audit_tool_is_an_error_not_a_pass(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = commit(repo, {"uv.lock": "version = 1\n"})
    (repo / "uv.lock").write_text("version = 2\n", encoding="utf-8")
    assert (
        qg.main(["audit", "--base", base, "--uv", "false", "--pip-audit", "false"], root=repo) == 2
    )
    assert "uv export failed" in capsys.readouterr().err


def test_an_unreachable_osv_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> object:
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    with pytest.raises(qg.GateError, match="couldn't read GHSA-x from OSV"):
        qa.osv_severity("GHSA-x")


# --- Weekly report -------------------------------------------------------------------------------


class FakeIssues:
    """One repository's issues, in memory."""

    def __init__(self, open_number: int | None = None) -> None:
        self.open_number = open_number
        self.calls: list[tuple[str, ...]] = []

    def find_open(self) -> int | None:
        return self.open_number

    def create(self, body: str) -> str:
        self.calls.append(("create", body))
        self.open_number = 7
        return "https://github.com/troupe-run/infrastructure/issues/7"

    def edit(self, number: int, body: str) -> None:
        self.calls.append(("edit", str(number), body))

    def close(self, number: int, comment: str) -> None:
        self.calls.append(("close", str(number), comment))
        self.open_number = None


HIGH = qa.Advisory("requests", "2.19.0", "GHSA-x84v-xcm2-53pg", "high", "2.20.0")
MODERATE = qa.Advisory("glob", "9.0.0 - 14.0.1", "npm audit", "moderate", None)


def test_advisories_with_no_open_issue_open_one_and_return_its_url() -> None:
    issues = FakeIssues()
    url = qa.upkeep([HIGH, MODERATE], AUDIT, issues, ["uv.lock"])
    assert url == "https://github.com/troupe-run/infrastructure/issues/7"
    assert [call[0] for call in issues.calls] == ["create"]
    body = issues.calls[0][1]
    assert "| requests | 2.19.0 | GHSA-x84v-xcm2-53pg | high | 2.20.0 | yes |" in body
    assert "| glob | 9.0.0 - 14.0.1 | npm audit | moderate | no fix yet |  |" in body


def test_advisories_with_an_open_issue_update_it_and_open_no_other() -> None:
    issues = FakeIssues(open_number=3)
    assert qa.upkeep([MODERATE], AUDIT, issues, ["uv.lock"]) is None
    assert [call[:2] for call in issues.calls] == [("edit", "3")]


def test_no_advisories_close_the_open_issue() -> None:
    issues = FakeIssues(open_number=3)
    assert qa.upkeep([], AUDIT, issues, ["uv.lock"]) is None
    assert issues.calls == [("close", "3", "The weekly dependency audit found no advisories.")]


def test_no_advisories_and_no_issue_do_nothing() -> None:
    issues = FakeIssues()
    assert qa.upkeep([], AUDIT, issues, ["uv.lock"]) is None
    assert issues.calls == []


FAKE_GH = """\
import json, pathlib, sys
log = pathlib.Path(sys.argv[0]).with_suffix(".log")
args = sys.argv[1:]
with log.open("a") as out:
    stdin = "" if sys.stdin.isatty() else sys.stdin.read()
    out.write(json.dumps({"args": args, "stdin": stdin}) + "\\n")
if args[:2] == ["issue", "list"]:
    print(json.dumps([
        {"number": 12, "title": "Dependency advisories in website"},
        {"number": 9, "title": "Dependency advisories"},
    ]))
elif args[:2] == ["issue", "create"]:
    print("https://github.com/troupe-run/infrastructure/issues/40")
"""


def fake_gh(tmp_path: Path) -> tuple[str, Path]:
    script = tmp_path / "gh.py"
    script.write_text(FAKE_GH, encoding="utf-8")
    wrapper = tmp_path / "gh"
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
    wrapper.chmod(0o755)
    return str(wrapper), script.with_suffix(".log")


@pytest.mark.skipif(sys.platform == "win32", reason="the fake gh is a shell script")
def test_gh_issues_finds_its_issue_by_exact_title_and_label(tmp_path: Path) -> None:
    gh, log = fake_gh(tmp_path)
    issues = qa.GhIssues(gh, "troupe-run/infrastructure")
    assert issues.find_open() == 9
    issues.edit(9, "the body")
    issues.close(9, "clear")
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert calls[0]["args"][:7] == [
        "issue", "list", "--state", "open", "--label", "dependencies", "--search",
    ]  # fmt: skip
    assert calls[0]["args"][-2:] == ["-R", "troupe-run/infrastructure"]
    assert calls[1]["args"] == [
        "issue", "edit", "9", "--body-file", "-", "-R", "troupe-run/infrastructure",
    ]  # fmt: skip
    assert calls[1]["stdin"] == "the body"
    assert calls[2]["args"][:4] == ["issue", "close", "9", "--comment"]


@pytest.mark.skipif(sys.platform == "win32", reason="the fake gh is a shell script")
def test_gh_issues_creates_with_title_label_and_body(tmp_path: Path) -> None:
    gh, log = fake_gh(tmp_path)
    url = qa.GhIssues(gh, "troupe-run/infrastructure").create("the body")
    assert url == "https://github.com/troupe-run/infrastructure/issues/40"
    call = json.loads(log.read_text().splitlines()[0])
    assert call["args"][:6] == [
        "issue", "create", "--title", "Dependency advisories", "--label", "dependencies",
    ]  # fmt: skip
    assert call["stdin"] == "the body"


def test_a_failing_gh_is_an_error() -> None:
    with pytest.raises(qg.GateError, match="gh issue list failed"):
        qa.GhIssues("false", "troupe-run/infrastructure").find_open()


def test_an_audit_error_run_as_a_script_stops_the_gate_with_exit_2(tmp_path: Path) -> None:
    """Run as a file, the script must share one GateError with quality_audit, which imports
    `quality_gates`: two copies of the module would leave the audit's error uncaught."""
    (tmp_path / "quality-gates.toml").write_text(
        CONFIG, encoding="utf-8"
    )  # names a missing uv.lock
    script = Path(qg.__file__)
    result = subprocess.run(
        [sys.executable, str(script), "report", "--repository", "o/r"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode, result.stderr.strip()) == (
        2,
        "report: quality-gates.toml names uv.lock, which doesn't exist.",
    )
