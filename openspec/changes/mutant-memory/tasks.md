# Tasks

## 1. The setting (design D4)

- [x] 1.1 Tests first in `test_mutation_settings.py`:
      - `mutant_memory_mb` null is no cap;
      - a whole number from 256 to 12,288 is read as the cap;
      - a string, a fraction, a boolean or an out-of-range number is refused, word for word, naming the setting, its
        value and the range;
      - a settings file without the key is refused, as every other key is.
- [x] 1.2 `Settings.mutant_memory_mb`, its key and its check in `mutation_settings.py`; `mutation.json` gains
      `"mutant_memory_mb": null`

## 2. The cap in each mutant's process (design D1, D2)

- [x] 2.1 Tests first in `test_mutation_children.py` (split from `test_mutation_run.py`, which the size gate holds at
      48 KB):
      - with a config file beside the plugin naming a cap, `pytest_configure` in a process whose `MUTANT_UNDER_TEST`
        names a mutant sets `RLIMIT_AS` to it (read back with `getrlimit`, in a subprocess);
      - with the stats value, `none.none`, no file, or a null cap, it leaves the limit alone;
      - a malformed file is refused, naming the file;
      - Linux only: a subprocess capped at a small limit that then allocates past it gets `MemoryError`, and the
        process that started it carries on.
- [x] 2.2 The plugin reads `_mutation_children_plugin.json` beside itself, and sets the limit in mutant processes only
- [x] 2.3 Tests first in `test_mutation_run.py`: `run_mutmut` writes the config file beside the plugin copy, with the
      settings' cap and the peaks path, and removes both afterwards, as it does the plugin
- [x] 2.4 `run_mutmut` takes the cap (like `children`), writes the file, and its one caller (`mutation_run.main`, which
      the pull request run also goes through) passes the settings' value

## 3. The peaks (design D3)

- [x] 3.1 Tests first:
      - `pytest_unconfigure` appends `<name> <VmPeak kB> <VmHWM kB>` read from a stand-in `/proc/self/status`, using
        `mutmut` for a pass with no mutant;
      - with no status file it appends nothing;
      - `mutation_run`'s summary of a peaks file logs mutmut's largest, the five largest mutants by `VmPeak` with their
        names, and the count, in MB;
      - an empty or missing file logs that no peaks were recorded;
      - a malformed line is skipped and counted, never fatal.
- [x] 3.2 The plugin's `pytest_unconfigure`, and `mutation_run` logging the `memory:` lines after each unit's run,
      finished or not

## 4. Docs and the check

- [x] 4.1 `docs/development-workflow.md`, "Mutation testing": the per-mutant cap, its setting (null until measured),
      the `memory:` lines, and that the run's 12G cgroup stays as the backstop
- [ ] 4.2 The full check passes (in the orchestrator's slot)

## 5. The measured default: a follow-up change

The owner chose route A (2026-11-20, 13:07 AEST). Measuring, setting the default and proving it under the cap
(design D4) are a follow-up change, a second pull request after this one's apply and a dry run that measures. This
change closes #367; the follow-up closes #366.
