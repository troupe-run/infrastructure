"""The org-default issue forms and PR template (specs: development-workflow, org-profile, labels;
pr-templates design D5).

A form whose issue type the org doesn't have, or whose label a repository lacks, still renders on
GitHub; the type or label is just dropped. So each form is checked here against what the org
declares: issue types in oob/issue-types.json (which oob.py compares with GitHub) and the
workflow's labels in tofu/labels/workflow.json (which every managed repository gets).

The contributing guide's licence and sign-off table is checked the same way, against what the
rulesets require (tofu/required-checks.json) and the licence pyproject.toml declares.
"""

import json
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO

ORG_PROFILE = REPO / "org-profile"
FORMS = ORG_PROFILE / ".github" / "ISSUE_TEMPLATE"
ISSUE_TYPES = REPO / "oob" / "issue-types.json"
WORKFLOW_LABELS = REPO / "tofu" / "labels" / "workflow.json"

# The chooser's settings, not a form.
NOT_A_FORM = {"config.yml"}


def enabled_types(path: Path) -> set[str]:
    return {t["name"] for t in json.loads(path.read_text(encoding="utf-8")) if t["is_enabled"]}


def label_names(path: Path) -> set[str]:
    return {label["name"] for label in json.loads(path.read_text(encoding="utf-8"))}


def form_problems(form: Path, types: set[str], labels: set[str]) -> list[str]:
    """What's wrong with one issue form, each naming the form. Empty when it's sound."""
    try:
        loaded: Any = yaml.safe_load(form.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        return [f"{form.name}: doesn't parse as YAML ({error})"]
    if not isinstance(loaded, dict):
        return [f"{form.name}: isn't a YAML mapping"]
    problems = []
    kind = loaded.get("type")
    if kind is None:
        problems.append(f"{form.name}: has no type:")
    elif kind not in types:
        problems.append(
            f"{form.name}: type {kind!r} isn't an enabled issue type in oob/issue-types.json"
        )
    for label in loaded.get("labels") or []:
        if label not in labels:
            problems.append(f"{form.name}: label {label!r} isn't in tofu/labels/workflow.json")
    return problems


def note(relative: str) -> str:
    return (
        f"Source: troupe-run/infrastructure (org-profile/{relative}). "
        "Change it there; this copy is written by the App."
    )


def note_problem(root: Path, path: Path) -> str | None:
    """The file's first line must be the source note naming its own path (spec: org-profile)."""
    relative = path.relative_to(root).as_posix()
    lines = path.read_text(encoding="utf-8").splitlines()
    first = lines[0] if lines else ""
    expected = (f"<!-- {note(relative)} -->", f"# {note(relative)}")
    return None if first in expected else f"{relative}: first line isn't the source note: {first!r}"


def real_forms() -> list[Path]:
    return sorted(p for p in FORMS.glob("*.yml") if p.name not in NOT_A_FORM)


def test_the_org_profile_has_the_bug_feature_and_decision_forms() -> None:
    assert [p.name for p in real_forms()] == ["bug.yml", "decision.yml", "feature.yml"]


@pytest.mark.labels
@pytest.mark.parametrize("form", real_forms(), ids=lambda p: p.name)
def test_each_forms_type_and_labels_are_declared_by_the_org(form: Path) -> None:
    assert form_problems(form, enabled_types(ISSUE_TYPES), label_names(WORKFLOW_LABELS)) == []


def test_the_decision_form_applies_needs_owner() -> None:
    decision = yaml.safe_load((FORMS / "decision.yml").read_text(encoding="utf-8"))
    assert decision["labels"] == ["needs:owner"]


@pytest.mark.parametrize(
    "path",
    # Every file tofu/org_profile.tf publishes, which leaves out macOS's .DS_Store (design D1).
    sorted(p for p in ORG_PROFILE.rglob("*") if p.is_file() and p.name != ".DS_Store"),
    ids=lambda p: p.relative_to(ORG_PROFILE).as_posix(),
)
def test_every_org_profile_file_starts_with_its_source_note(path: Path) -> None:
    assert note_problem(ORG_PROFILE, path) is None


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_form_with_no_type_fails_naming_the_form(tmp_path: Path) -> None:
    form = write(tmp_path / "idea.yml", "name: Idea\nbody: []\n")
    assert form_problems(form, {"Bug"}, set()) == ["idea.yml: has no type:"]


def test_a_form_that_doesnt_parse_fails_naming_the_form(tmp_path: Path) -> None:
    form = write(tmp_path / "broken.yml", "name: [unclosed\n")
    [problem] = form_problems(form, {"Bug"}, set())
    assert problem.startswith("broken.yml: doesn't parse as YAML")


def test_a_form_naming_an_undeclared_type_fails_naming_the_form_and_type(tmp_path: Path) -> None:
    form = write(tmp_path / "chore.yml", "name: Chore\ntype: Chore\n")
    assert form_problems(form, {"Bug"}, set()) == [
        "chore.yml: type 'Chore' isn't an enabled issue type in oob/issue-types.json"
    ]


def test_a_form_naming_an_undeclared_label_fails_naming_the_form_and_label(tmp_path: Path) -> None:
    form = write(tmp_path / "ask.yml", "name: Ask\ntype: Bug\nlabels: [needs:owner, triage]\n")
    assert form_problems(form, {"Bug"}, {"needs:owner"}) == [
        "ask.yml: label 'triage' isn't in tofu/labels/workflow.json"
    ]


def test_a_disabled_issue_type_doesnt_count(tmp_path: Path) -> None:
    types = write(
        tmp_path / "issue-types.json",
        json.dumps([{"name": "Bug", "is_enabled": True}, {"name": "Epic", "is_enabled": False}]),
    )
    assert enabled_types(types) == {"Bug"}


def test_a_file_without_its_source_note_fails_naming_it(tmp_path: Path) -> None:
    write(tmp_path / ".github" / "x.yml", "name: X\n")
    assert note_problem(tmp_path, tmp_path / ".github" / "x.yml") == (
        ".github/x.yml: first line isn't the source note: 'name: X'"
    )


def test_a_source_note_naming_another_path_fails(tmp_path: Path) -> None:
    write(tmp_path / "a.md", f"<!-- {note('b.md')} -->\n")
    assert note_problem(tmp_path, tmp_path / "a.md") is not None


CHOOSER_CONFIG = FORMS / "config.yml"


def security_link_problems(config: Path) -> list[str]:
    """The chooser config mustn't link to the security policy (drop-security-contact-link).

    GitHub already shows its own "Report a security vulnerability" entry wherever the org has a
    security policy, so a contact link to it is a second, duplicate entry.
    """
    loaded: Any = yaml.safe_load(config.read_text(encoding="utf-8"))
    links = loaded.get("contact_links") or [] if isinstance(loaded, dict) else []
    return [
        f"{config.name}: contact link {link.get('name')!r} points to the security policy, which "
        "GitHub already shows as its own 'Report a security vulnerability' entry"
        for link in links
        if isinstance(link, dict)
        and (
            str(link.get("url", "")).lower().endswith("security.md")
            or "/security" in str(link.get("url", "")).lower()
        )
    ]


def test_the_chooser_config_doesnt_duplicate_githubs_security_entry() -> None:
    assert security_link_problems(CHOOSER_CONFIG) == []


def test_a_contact_link_to_the_security_policy_fails_saying_github_shows_it(
    tmp_path: Path,
) -> None:
    config = write(
        tmp_path / "config.yml",
        "blank_issues_enabled: true\n"
        "contact_links:\n"
        "  - name: Report a vulnerability\n"
        "    url: https://github.com/troupe-run/.github/blob/main/SECURITY.md\n"
        "    about: Privately.\n"
        "  - name: Discussions\n"
        "    url: https://github.com/orgs/troupe-run/discussions\n"
        "    about: Questions.\n",
    )
    assert security_link_problems(config) == [
        "config.yml: contact link 'Report a vulnerability' points to the security policy, which "
        "GitHub already shows as its own 'Report a security vulnerability' entry"
    ]


def test_a_security_advisories_link_counts_as_the_security_policy(tmp_path: Path) -> None:
    config = write(
        tmp_path / "config.yml",
        "contact_links:\n"
        "  - name: Report\n"
        "    url: https://github.com/troupe-run/troupe/security/advisories/new\n",
    )
    assert len(security_link_problems(config)) == 1


# Where questions go: troupe's Q&A discussions (spec: org-profile; repository-features design D7).
QUESTIONS_URL = "https://github.com/troupe-run/troupe/discussions/categories/q-a"


def test_the_chooser_offers_a_question_link_to_troupes_q_and_a() -> None:
    loaded: Any = yaml.safe_load(CHOOSER_CONFIG.read_text(encoding="utf-8"))
    links = [(link["name"], link["url"]) for link in loaded["contact_links"]]
    assert ("Ask a question", QUESTIONS_URL) in links


GUIDE = ORG_PROFILE / "CONTRIBUTING.md"
REQUIRED_CHECKS = REPO / "tofu" / "required-checks.json"
PYPROJECT = REPO / "pyproject.toml"

# A row of the guide's licence and sign-off table: | [repo](link) | licence | sign-off |
TABLE_ROW = re.compile(r"^\|\s*\[([^\]]+)\]\([^)]*\)\s*\|([^|]*)\|([^|]*)\|\s*$")


def requires_dco(checks: list[dict[str, str]]) -> bool:
    return any(c["context"] == "DCO" and c["app"] == "dco" for c in checks)


def guide_table_problems(
    guide: str, required_checks: dict[str, list[dict[str, str]]], licence: str
) -> list[str]:
    """What the guide's licence and sign-off table gets wrong, each naming the repository (specs:
    org-profile, licensing; org-contributing-covers-website design D3).

    Every repository in tofu/required-checks.json is governed, so each needs one row. Its sign-off
    is DCO exactly when its pull requests require the DCO App's check, and infrastructure's licence
    is the one pyproject.toml declares.
    """
    rows: dict[str, list[tuple[str, str]]] = {}
    for line in guide.splitlines():
        if match := TABLE_ROW.match(line):
            name, row_licence, sign_off = (part.strip() for part in match.groups())
            rows.setdefault(name, []).append((row_licence, sign_off))
    problems = []
    for repo, checks in sorted(required_checks.items()):
        found = rows.get(repo, [])
        if len(found) != 1:
            problems.append(
                f"{repo}: the guide's licence and sign-off table has {len(found)} rows for it, "
                "not one"
            )
            continue
        [(row_licence, sign_off)] = found
        if requires_dco(checks) and not sign_off.startswith("DCO"):
            problems.append(
                f"{repo}: its pull requests require the DCO check, but the guide says {sign_off!r}"
            )
        if not requires_dco(checks) and not sign_off.startswith("None"):
            problems.append(
                f"{repo}: the guide says {sign_off!r}, but its pull requests don't require the "
                "DCO check"
            )
        if repo == "infrastructure" and row_licence != licence:
            problems.append(
                f"infrastructure: the guide says {row_licence!r}, but pyproject.toml declares "
                f"{licence!r}"
            )
    return problems


@pytest.mark.tofu
def test_the_guides_table_matches_the_rulesets_and_this_repositorys_licence() -> None:
    required_checks = json.loads(REQUIRED_CHECKS.read_text(encoding="utf-8"))
    licence = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["license"]
    assert guide_table_problems(GUIDE.read_text(encoding="utf-8"), required_checks, licence) == []


DCO = {"context": "DCO", "app": "dco"}
GUARD = {"context": "guard (workflow rules)", "app": "github-actions"}
CHECKS = {"infrastructure": [GUARD, DCO], "website": [GUARD]}
SOUND_GUIDE = (
    "| Repository | Licence | Sign-off |\n"
    "|---|---|---|\n"
    "| [infrastructure](https://github.com/troupe-run/infrastructure) | Apache-2.0 | DCO |\n"
    "| [website](https://github.com/troupe-run/website) | MIT | None: no DCO, no CLA |\n"
)


def test_a_table_matching_the_checks_and_licence_has_no_problems() -> None:
    assert guide_table_problems(SOUND_GUIDE, CHECKS, "Apache-2.0") == []


def test_a_governed_repository_with_no_row_fails_naming_it() -> None:
    guide = SOUND_GUIDE.replace("| [website](https://github.com/troupe-run/website) |", "| x |")
    assert guide_table_problems(guide, CHECKS, "Apache-2.0") == [
        "website: the guide's licence and sign-off table has 0 rows for it, not one"
    ]


def test_dco_for_a_repository_that_doesnt_require_it_fails_naming_it() -> None:
    guide = SOUND_GUIDE.replace("None: no DCO, no CLA", "DCO")
    assert guide_table_problems(guide, CHECKS, "Apache-2.0") == [
        "website: the guide says 'DCO', but its pull requests don't require the DCO check"
    ]


def test_no_sign_off_for_a_repository_that_requires_dco_fails_naming_it() -> None:
    guide = SOUND_GUIDE.replace("| Apache-2.0 | DCO |", "| Apache-2.0 | None |")
    assert guide_table_problems(guide, CHECKS, "Apache-2.0") == [
        "infrastructure: its pull requests require the DCO check, but the guide says 'None'"
    ]


def test_a_dco_check_from_another_app_doesnt_count() -> None:
    checks = {**CHECKS, "website": [GUARD, {"context": "DCO", "app": "github-actions"}]}
    assert guide_table_problems(SOUND_GUIDE, checks, "Apache-2.0") == []


def test_a_licence_other_than_pyprojects_fails_naming_both() -> None:
    assert guide_table_problems(SOUND_GUIDE, CHECKS, "MIT") == [
        "infrastructure: the guide says 'Apache-2.0', but pyproject.toml declares 'MIT'"
    ]


# The guide's sentence listing the issue types, up to its full stop (issue-relationships-rule
# design D2).
TYPES_SENTENCE = re.compile(r"^Every issue has a type: ([^.]*)\.", re.MULTILINE)
NO_TYPES_LIST = (
    "the guide's list of issue types wasn't found: no line starts 'Every issue has a type:'"
)


def guide_type_problems(guide: str, types: set[str]) -> list[str]:
    """What the guide's list of issue types gets wrong against the org's enabled types, each naming
    the type (spec: org-profile; issue-relationships-rule design D2)."""
    match = TYPES_SENTENCE.search(guide)
    if match is None:
        return [NO_TYPES_LIST]
    listed = {name.strip() for name in re.split(r",|\bor\b", match.group(1)) if name.strip()}
    problems = [
        f"{name}: the guide lists it, but it isn't an enabled issue type in oob/issue-types.json"
        for name in sorted(listed - types)
    ]
    problems += [
        f"{name}: it's an enabled issue type in oob/issue-types.json, but the guide doesn't list it"
        for name in sorted(types - listed)
    ]
    return problems


def test_the_guides_issue_types_are_the_orgs_enabled_types() -> None:
    assert guide_type_problems(GUIDE.read_text(encoding="utf-8"), enabled_types(ISSUE_TYPES)) == []


ORG_TYPES = {"Epic", "Feature", "Bug", "Task", "Decision"}
TYPES_GUIDE = (
    "## How issues are related\n\nEvery issue has a type: Epic, Feature, Bug, Task or Decision.\n"
)


def test_a_list_matching_the_enabled_types_has_no_problems() -> None:
    assert guide_type_problems(TYPES_GUIDE, ORG_TYPES) == []


def test_a_type_the_org_doesnt_have_fails_naming_it() -> None:
    guide = TYPES_GUIDE.replace("Task or Decision", "Task, Chore or Decision")
    assert guide_type_problems(guide, ORG_TYPES) == [
        "Chore: the guide lists it, but it isn't an enabled issue type in oob/issue-types.json"
    ]


def test_a_type_the_guide_leaves_out_fails_naming_it() -> None:
    guide = TYPES_GUIDE.replace("Bug, Task or", "Bug or")
    assert guide_type_problems(guide, ORG_TYPES) == [
        "Task: it's an enabled issue type in oob/issue-types.json, but the guide doesn't list it"
    ]


def test_a_guide_with_no_list_of_types_fails_saying_so() -> None:
    assert guide_type_problems("## How issues are related\n", ORG_TYPES) == [NO_TYPES_LIST]


def test_the_guide_sends_questions_to_troupes_discussions() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    section = guide.split("## Questions\n", 1)[1].split("\n## ", 1)[0]
    assert QUESTIONS_URL in section
    assert "not in an\nissue" in section
