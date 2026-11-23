# Proposal

## Why

troupe's pull request mutation run reads the delivered `scripts/mutation.json`. That file deselects three of troupe's
tests by node id because they fail inside mutmut's copy, each for a reason recorded beside it:

- `packages/troupe/tests/test_cli_startup.py::test_importing_the_command_line_loads_none_of_the_heavy_modules`;
- `packages/troupe/tests/test_config_schemas.py::test_the_models_are_what_the_schemas_generate`;
- `packages/troupe/tests/test_package.py::test_the_built_wheel_carries_the_recorded_protocol_version_and_every_schema`.

troupe-run/troupe#507 moves troupe's tests into `tests/unit/` and `tests/integration/`. pytest's `--deselect` silently
ignores an id it can't find, so the three would then run in mutmut's copy and fail. mutmut stops before mutating when a
unit's tests fail there, so "mutate the changes" would fail on every troupe pull request, #507's own included, until
infrastructure delivered the new ids (#395).

## What Changes

- Each of the three deselects names both its current id and its id after #507's move, with the same reason. A deselect
  that matches nothing is harmless, so the file works before and after #507, with no window where the run fails. It is
  applied before #507 merges (#507 is blocked by #395).
- A test holds that troupe's declared deselects name both ids for each of the three, so neither half is dropped before
  #394 (mutation runs use only unit tests, after #507) removes the old ones.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None: a settings change, with no requirement changing (`skip_specs`).

## Impact

- `scripts/mutation.json` (delivered to troupe) and `scripts/tests/test_mutation_settings.py`.
- The plan updates troupe's delivered `scripts/mutation.json`.
