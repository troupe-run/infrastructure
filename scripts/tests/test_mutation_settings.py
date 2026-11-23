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
# The settings as they were with three repositories and both tools: the refusals are tested on
# them, so every tool's keys stay covered while the real list names troupe alone (#332).
THREE = REPO / "scripts" / "tests" / "fixtures" / "mutation" / "settings-three.json"


def declared() -> dict[str, Any]:
    loaded = json.loads(THREE.read_text(encoding="utf-8"))
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
    # Two mutants at once: four starved the hosted runner in both troupe dry runs (#337).
    assert settings.max_children == 2
    # Each mutant's process is capped at 2,048 MB (#366): dry run 44693481824 measured mutmut's own
    # VmPeak at 1,111 MB and the largest ordinary mutant's at 1,270 MB; plus half, rounded up to
    # 256 MB (mutant-memory design D4). The runaway it stops reached 5,289 MB.
    assert settings.mutant_memory_mb == 2048
    # Incremental runs miss edited tests and changed callees; a full refresh every 28 days clears
    # them (#378).
    assert settings.full_refresh_days == 28
    # The one list of repositories that get coverage and mutation testing (#332, owner 2026-11-18).
    assert set(settings.repositories) == {"troupe"}


MOVED = (
    "packages/troupe/tests/test_cli_startup.py"
    "::test_importing_the_command_line_loads_none_of_the_heavy_modules",
    "packages/troupe/tests/test_config_schemas.py::test_the_models_are_what_the_schemas_generate",
    "packages/troupe/tests/test_package.py"
    "::test_the_built_wheel_carries_the_recorded_protocol_version_and_every_schema",
)
"""troupe's three tests that fail in mutmut's copy, by their ids before troupe-run/troupe#507
moves them (#395)."""


@pytest.mark.parametrize("old", MOVED)
def test_each_deselected_troupe_test_is_named_before_and_after_its_move(old: str) -> None:
    """An unmatched --deselect is silently ignored, so until #394 trims the old ids, each test
    is named by its current id and by exactly one id under tests/unit/ or tests/integration/:
    the same test name, for the same reason. #507 also renames files it splits, so the file
    name may differ. troupe's pull request mutation run then works on either side of #507's
    merge (#395)."""
    troupe = ms.load_settings(DECLARED.read_text(encoding="utf-8")).repositories["troupe"]
    [unit] = [u for u in troupe.units if u.name == "troupe"]
    name = old.split("::")[1]
    named = [(test, why) for test, why in unit.deselect if test.split("::")[1] == name]
    tests = [test for test, _ in named]
    assert old in tests
    moved = [
        test
        for test in tests
        if test.startswith(("packages/troupe/tests/unit/", "packages/troupe/tests/integration/"))
    ]
    assert len(moved) == 1, tests
    assert len(named) == 2, tests
    assert len({why for _, why in named}) == 1, "the same reason"


def test_the_fixtures_three_repositories_name_their_tools_and_what_they_mutate() -> None:
    settings = ms.load_settings(THREE.read_text(encoding="utf-8"))
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


def test_a_per_mutant_memory_cap_is_read_in_megabytes() -> None:
    assert ms.load_settings(changed(["mutant_memory_mb"], 3072)).mutant_memory_mb == 3072


def test_a_settings_file_without_the_per_mutant_cap_fails_naming_it() -> None:
    settings = declared()
    del settings["mutant_memory_mb"]
    with pytest.raises(ms.SettingsError) as raised:
        ms.load_settings(text(settings))
    assert str(raised.value) == "the settings has no 'mutant_memory_mb'"


def test_a_settings_file_without_a_full_refresh_period_fails_naming_it() -> None:
    settings = declared()
    del settings["full_refresh_days"]
    with pytest.raises(ms.SettingsError) as raised:
        ms.load_settings(text(settings))
    assert str(raised.value) == "the settings has no 'full_refresh_days'"


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


GATES = (REPO / "quality-gates.toml").read_text(encoding="utf-8")
"""A whole, valid quality-gates.toml (#322's), which the mutation table is read from (design D7)."""


def test_a_quality_gates_file_hands_over_its_mutation_table() -> None:
    source = (
        GATES + '\n[mutation.baselines."troupe.store.events"]\n'
        f'score = 71.2\nmutants = 140\njudged_at = "{"b" * 40}"\n'
    )
    table = ms.read_mutation_table(source, "quality-gates.toml")
    assert ms.load_baselines(table, "quality-gates.toml") == {
        "troupe.store.events": ms.Baseline(71.2, 140, "b" * 40)
    }


def test_a_quality_gates_file_without_a_mutation_table_has_no_baselines() -> None:
    assert ms.read_mutation_table(GATES, "quality-gates.toml") == {}


def test_a_quality_gates_file_that_isnt_toml_fails_naming_it() -> None:
    with pytest.raises(
        ms.SettingsError,
        match=r"^troupe-run/troupe/quality-gates\.toml: quality-gates\.toml isn't valid TOML",
    ):
        ms.read_mutation_table("[mutation\n", "troupe-run/troupe/quality-gates.toml")


def test_a_quality_gates_file_its_own_parser_refuses_is_an_error_naming_it() -> None:
    with pytest.raises(ms.SettingsError, match=r"^troupe-run/troupe/quality-gates\.toml: "):
        ms.read_mutation_table("version = 1\n", "troupe-run/troupe/quality-gates.toml")


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


SHA_40 = "a" * 40


# Every refusal, word for word (lint-mutation 6b: the pull request report's survivors)

KEYS = (
    "['budget_minutes', 'full_refresh_days', 'max_children', 'max_new_issues', 'min_mutants', "
    "'mutant_memory_mb', 'pr_budget_minutes', 'repositories', 'threshold', 'tolerance', 'tools']"
)


def changed(path: list[str | int], value: object) -> str:
    settings = declared()
    target: Any = settings
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return text(settings)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("[]", "the settings isn't an object"),
        (changed(["tools"], []), "tools isn't an object"),
        (changed(["tools", "mutmut"], ""), "tools.mutmut is ''; it must be a non-empty string"),
        (changed(["repositories"], {}), "repositories must be a non-empty object"),
        (changed(["repositories"], []), "repositories must be a non-empty object"),
        (changed(["threshold"], 101), "threshold is 101; it must be a number from 0 to 100"),
        (changed(["threshold"], True), "threshold is True; it must be a number from 0 to 100"),
        (changed(["tolerance"], -1), "tolerance is -1; it must be a number from 0 to 100"),
        (
            changed(["min_mutants"], 0),
            "min_mutants is 0; it must be a whole number from 1 to 10000",
        ),
        (
            changed(["min_mutants"], 1.5),
            "min_mutants is 1.5; it must be a whole number from 1 to 10000",
        ),
        (
            changed(["budget_minutes"], 331),
            "budget_minutes is 331; it must be a whole number from 1 to 330",
        ),
        (
            changed(["pr_budget_minutes"], 331),
            "pr_budget_minutes is 331; it must be a whole number from 1 to 330",
        ),
        (
            changed(["max_new_issues"], 101),
            "max_new_issues is 101; it must be a whole number from 0 to 100",
        ),
        (
            changed(["max_children"], 0),
            "max_children is 0; it must be a whole number from 1 to 4",
        ),
        (
            changed(["max_children"], 5),
            "max_children is 5; it must be a whole number from 1 to 4",
        ),
        (
            changed(["max_children"], 2.5),
            "max_children is 2.5; it must be a whole number from 1 to 4",
        ),
        (
            changed(["mutant_memory_mb"], 255),
            "mutant_memory_mb is 255; it must be null or a whole number from 256 to 12288",
        ),
        (
            changed(["mutant_memory_mb"], 12289),
            "mutant_memory_mb is 12289; it must be null or a whole number from 256 to 12288",
        ),
        (
            changed(["mutant_memory_mb"], 3072.5),
            "mutant_memory_mb is 3072.5; it must be null or a whole number from 256 to 12288",
        ),
        (
            changed(["mutant_memory_mb"], "3G"),
            "mutant_memory_mb is '3G'; it must be null or a whole number from 256 to 12288",
        ),
        (
            changed(["mutant_memory_mb"], True),
            "mutant_memory_mb is True; it must be null or a whole number from 256 to 12288",
        ),
        (
            changed(["full_refresh_days"], 0),
            "full_refresh_days is 0; it must be a whole number from 1 to 365",
        ),
        (
            changed(["full_refresh_days"], 366),
            "full_refresh_days is 366; it must be a whole number from 1 to 365",
        ),
        (
            changed(["full_refresh_days"], None),
            "full_refresh_days is None; it must be a whole number from 1 to 365",
        ),
        (changed(["repositories", "troupe"], []), "repositories.troupe isn't an object"),
        (
            changed(["repositories", "troupe", "tool"], "pitest"),
            "repositories.troupe.tool is 'pitest'; it must be one of ['mutmut', 'stryker']",
        ),
        (
            changed(["repositories", "troupe", "mutate"], ["x"]),
            "repositories.troupe has the key 'mutate', which isn't one of ['tool', 'units']",
        ),
        (
            changed(["repositories", "troupe", "units"], []),
            "repositories.troupe.units must be a non-empty list",
        ),
        (
            changed(["repositories", "troupe", "units", 0], "x"),
            "repositories.troupe.units[0] isn't an object",
        ),
        (
            changed(["repositories", "troupe", "units", 0, "name"], ""),
            "repositories.troupe.units[0].name is ''; it must be a non-empty string",
        ),
        (
            changed(["repositories", "troupe", "units", 0, "source"], ""),
            "repositories.troupe.units[0].source is ''; it must be a non-empty string",
        ),
        (
            changed(["repositories", "troupe", "units", 0, "tests"], ""),
            "repositories.troupe.units[0].tests is ''; it must be a non-empty string",
        ),
        (
            changed(["repositories", "troupe", "units", 0, "also_copy"], "x"),
            "repositories.troupe.units[0].also_copy must be a list of paths",
        ),
        (
            changed(["repositories", "troupe", "units", 0, "also_copy"], [""]),
            "repositories.troupe.units[0].also_copy is ''; it must be a non-empty string",
        ),
        (
            changed(["repositories", "troupe", "units", 0, "deselect"], "x"),
            "repositories.troupe.units[0].deselect must be a list of {test, why}",
        ),
        (
            changed(["repositories", "troupe", "units", 0, "deselect"], [1]),
            "repositories.troupe.units[0].deselect[0] isn't an object",
        ),
        (
            changed(["repositories", "troupe", "units", 0, "deselect"], [{"test": "", "why": "w"}]),
            "repositories.troupe.units[0].deselect[0].test is ''; it must be a non-empty string",
        ),
        (
            changed(["repositories", "website", "units"], []),
            "repositories.website has the key 'units', "
            "which isn't one of ['mutate', 'tests', 'tool']",
        ),
        (
            changed(["repositories", "website", "mutate"], []),
            "repositories.website.mutate must be a non-empty list of globs",
        ),
        (
            changed(["repositories", "website", "mutate"], [""]),
            "repositories.website.mutate is ''; it must be a non-empty string",
        ),
        (
            changed(["repositories", "website", "tests"], ""),
            "repositories.website.tests is ''; it must be a non-empty string",
        ),
    ],
)
def test_each_refusal_names_the_setting_its_value_and_whats_valid(
    source: str, message: str
) -> None:
    with pytest.raises(ms.SettingsError) as raised:
        ms.load_settings(source)
    assert str(raised.value) == message


def test_an_unknown_top_level_key_lists_every_valid_one() -> None:
    with pytest.raises(ms.SettingsError) as raised:
        ms.load_settings(changed(["extra"], 1))
    assert str(raised.value) == f"the settings has the key 'extra', which isn't one of {KEYS}"


def test_the_fixtures_repositories_load_as_written() -> None:
    settings = ms.load_settings(THREE.read_text(encoding="utf-8"))
    raw = declared()
    assert settings.tools == raw["tools"]
    for name, repository in settings.repositories.items():
        assert repository.name == name
    website = settings.repositories["website"]
    assert (website.mutate, website.tests) == (
        tuple(raw["repositories"]["website"]["mutate"]),
        "tests/unit",
    )
    for unit, written in zip(
        settings.repositories["troupe"].units, raw["repositories"]["troupe"]["units"], strict=True
    ):
        assert (unit.name, unit.source, unit.tests) == (
            written["name"],
            written["source"],
            written["tests"],
        )
    infrastructure = settings.repositories["infrastructure"].units[0]
    assert [test for test, _ in infrastructure.deselect] == [
        entry["test"] for entry in raw["repositories"]["infrastructure"]["units"][0]["deselect"]
    ]


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ({"baselines": []}, "quality-gates.toml [mutation] baselines isn't a table"),
        (
            {"baselines": {"m": {"score": 101, "mutants": 1, "judged_at": SHA_40}}},
            "quality-gates.toml [mutation.baselines.'m'] score is 101; "
            "it must be a number from 0 to 100",
        ),
        (
            {"baselines": {"m": {"score": 50, "mutants": 0, "judged_at": SHA_40}}},
            "quality-gates.toml [mutation.baselines.'m'] mutants is 0; "
            "it must be a whole number from 1 to 1000000",
        ),
    ],
)
def test_each_baseline_refusal_word_for_word(table: dict[str, Any], message: str) -> None:
    with pytest.raises(ms.SettingsError) as raised:
        ms.load_baselines(table, "quality-gates.toml")
    assert str(raised.value) == message


def test_a_mutation_value_that_isnt_a_table_is_refused_naming_the_file() -> None:
    with pytest.raises(ms.SettingsError, match=r"^quality-gates\.toml: "):
        ms.read_mutation_table(GATES + "mutation = 1\n", "quality-gates.toml")
