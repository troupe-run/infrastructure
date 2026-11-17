"""scripts/mutation.json is mutation testing's one declaration, read strictly (spec:
mutation-testing; lint-mutation design D3, D6, D7)."""

import copy
import json
from typing import Any

import pytest
from conftest import REPO

import mutation_settings as ms

pytestmark = pytest.mark.mutation

DECLARED = REPO / "scripts" / "mutation.json"


def declared() -> dict[str, Any]:
    loaded = json.loads(DECLARED.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_the_declared_settings_load_with_the_owners_values() -> None:
    settings = ms.load_settings(DECLARED.read_text(encoding="utf-8"))
    assert settings.threshold == 60.0
    assert settings.tolerance == 0.0
    assert settings.min_mutants == 10
    assert settings.budget_minutes == 240
    assert settings.pr_budget_minutes == 45
    assert settings.max_new_issues == 5
    assert set(settings.repositories) == {"troupe", "infrastructure", "website"}


def test_each_repository_names_its_tool_and_what_it_mutates() -> None:
    settings = ms.load_settings(DECLARED.read_text(encoding="utf-8"))
    assert settings.repositories["website"].tool == "stryker"
    for name in ("troupe", "infrastructure"):
        repository = settings.repositories[name]
        assert repository.tool == "mutmut"
        assert repository.units, name
        for unit in repository.units:
            assert unit.source
            assert unit.tests


def text(changed: dict[str, Any]) -> str:
    return json.dumps(changed)


def with_change(path: list[str], value: object) -> str:
    changed = copy.deepcopy(declared())
    target: Any = changed
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return text(changed)


@pytest.mark.parametrize(
    ("path", "value", "named"),
    [
        (["threshold"], 101, "threshold"),
        (["threshold"], -1, "threshold"),
        (["threshold"], "60", "threshold"),
        (["tolerance"], -0.5, "tolerance"),
        (["min_mutants"], 0, "min_mutants"),
        (["min_mutants"], True, "min_mutants"),
        (["budget_minutes"], 331, "budget_minutes"),
        (["pr_budget_minutes"], 0, "pr_budget_minutes"),
        (["max_new_issues"], -1, "max_new_issues"),
        (["repositories", "website", "tool"], "pitest", "tool"),
    ],
)
def test_an_out_of_range_setting_fails_naming_it(
    path: list[str], value: object, named: str
) -> None:
    with pytest.raises(ms.SettingsError, match=named):
        ms.load_settings(with_change(path, value))


def test_an_unknown_key_fails_naming_it_and_the_valid_keys() -> None:
    changed = declared()
    changed["reopen_window_days"] = 90
    with pytest.raises(ms.SettingsError, match="reopen_window_days") as raised:
        ms.load_settings(text(changed))
    assert "threshold" in str(raised.value)


def test_an_unknown_key_in_a_repository_fails_naming_the_repository() -> None:
    changed = declared()
    changed["repositories"]["troupe"]["extra"] = 1
    with pytest.raises(ms.SettingsError, match=r"troupe.*extra"):
        ms.load_settings(text(changed))


def test_a_missing_key_fails_naming_it() -> None:
    changed = declared()
    del changed["min_mutants"]
    with pytest.raises(ms.SettingsError, match="min_mutants"):
        ms.load_settings(text(changed))


def test_not_json_fails() -> None:
    with pytest.raises(ms.SettingsError, match="JSON"):
        ms.load_settings("{")


# The [mutation] table of a repository's quality-gates.toml (design D7)


def test_no_table_means_no_baselines() -> None:
    assert ms.load_baselines({}, "quality-gates.toml") == {}


def test_a_baseline_is_read() -> None:
    table = {
        "baselines": {"troupe.store.events": {"score": 71.2, "mutants": 140, "judged_at": "a" * 40}}
    }
    baselines = ms.load_baselines(table, "quality-gates.toml")
    assert baselines["troupe.store.events"] == ms.Baseline(71.2, 140, "a" * 40)


@pytest.mark.parametrize(
    ("entry", "named"),
    [
        ({"score": "high", "mutants": 1, "judged_at": "a" * 40}, "score"),
        ({"score": 101, "mutants": 1, "judged_at": "a" * 40}, "score"),
        ({"score": 50, "mutants": 0, "judged_at": "a" * 40}, "mutants"),
        ({"score": 50, "mutants": 3, "judged_at": "main"}, "judged_at"),
        ({"score": 50, "mutants": 3}, "judged_at"),
        ({"score": 50, "mutants": 3, "judged_at": "a" * 40, "note": "x"}, "note"),
    ],
)
def test_a_malformed_baseline_fails_naming_the_file_module_and_key(
    entry: dict[str, Any], named: str
) -> None:
    with pytest.raises(ms.SettingsError, match=rf"quality-gates\.toml.*troupe\.x.*{named}"):
        ms.load_baselines({"baselines": {"troupe.x": entry}}, "quality-gates.toml")


def test_an_unknown_key_in_the_table_fails() -> None:
    with pytest.raises(ms.SettingsError, match=r"quality-gates\.toml.*floor"):
        ms.load_baselines({"floor": 50, "baselines": {}}, "quality-gates.toml")


def test_a_quality_gates_file_hands_over_its_mutation_table() -> None:
    source = (
        '[coverage]\nfloor = 80\n\n[mutation.baselines."troupe.store.events"]\n'
        f'score = 71.2\nmutants = 140\njudged_at = "{"b" * 40}"\n'
    )
    table = ms.read_mutation_table(source, "quality-gates.toml")
    assert ms.load_baselines(table, "quality-gates.toml") == {
        "troupe.store.events": ms.Baseline(71.2, 140, "b" * 40)
    }


def test_a_quality_gates_file_without_a_mutation_table_has_no_baselines() -> None:
    assert ms.read_mutation_table("[coverage]\nfloor = 80\n", "quality-gates.toml") == {}


def test_a_quality_gates_file_that_isnt_toml_fails_naming_it() -> None:
    with pytest.raises(ms.SettingsError, match=r"quality-gates\.toml isn't TOML"):
        ms.read_mutation_table("[mutation\n", "quality-gates.toml")


def with_deselect(entry: object) -> str:
    changed = declared()
    changed["repositories"]["infrastructure"]["units"][0]["deselect"] = [entry]
    return text(changed)


def test_a_deselected_test_carries_its_reason() -> None:
    entry = {"test": "scripts/tests/test_a.py::test_b", "why": "it pretends to be Windows"}
    settings = ms.load_settings(with_deselect(entry))
    unit = settings.repositories["infrastructure"].units[0]
    assert unit.deselect == (("scripts/tests/test_a.py::test_b", "it pretends to be Windows"),)


@pytest.mark.parametrize(
    ("entry", "named"),
    [
        ({"test": "scripts/tests/test_a.py::test_b"}, "why"),
        ({"test": "tests/test_a.py::test_b", "why": "x"}, "node id under scripts/tests"),
        ({"test": "scripts/tests/test_a.py", "why": "x"}, "node id"),
        ({"test": "scripts/tests/test_a.py::t", "why": ""}, "why"),
    ],
)
def test_a_deselection_without_a_reason_or_a_node_id_fails(entry: object, named: str) -> None:
    with pytest.raises(ms.SettingsError, match=named):
        ms.load_settings(with_deselect(entry))
