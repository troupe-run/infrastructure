# Tasks

## 1. The plugin on Windows (design D1)

- [x] 1.1 Test first: `mypy --platform win32 scripts/mutation_children.py` passes (it fails on main with five
      `attr-defined` errors at lines 150-153)
- [x] 1.2 `cap_address_space()` returns under `if sys.platform == "win32":` before `import resource`; the cap's Linux
      tests still pass

## 2. The gate (design D2)

- [x] 2.1 Tests first in `test_check.py`:
      - the check's gates include `mypy win32 (delivered)`, running `mypy --platform win32` over exactly the Python
        files `tofu/guard_delivery.tf` delivers (read through `tofu_text`);
      - an empty list is refused, never a vacuous pass.
- [x] 2.2 The gate in `scripts/check.py`

## 3. Docs and the check

- [x] 3.1 `docs/development-workflow.md`: the new gate in the check's list, and why (#369)
- [x] 3.2 The full check passes, with the new gate (in the commit hook, in the orchestrator's slot, 2026-11-20)
