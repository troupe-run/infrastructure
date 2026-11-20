## Context

`scripts/mutation_children.py` gained `cap_address_space()` in #368, which imports `resource` inside the function.
Troupe's Windows legs run `mypy --strict` over the delivered scripts, and typeshed's `resource` stub gives win32
none of the names it uses. Infrastructure's check runs mypy on Linux and macOS only (its Windows legs run just the
guard's tests, `ci.yml`), so the same check passed here. All eight other delivered Python files already pass
`mypy --platform win32` (checked 2026-11-20).

## Goals / Non-Goals

**Goals:** troupe's Windows check passes again, fast (release path), and a POSIX-only use in a delivered file can't
reach a receiving repository again.

**Non-Goals:** running infrastructure's whole mypy for win32 (its own POSIX-only scripts and tests aren't delivered);
running mypy on infrastructure's Windows legs.

## Decisions

### D1. Narrow on `sys.platform` before the import

`cap_address_space()` returns at once under `if sys.platform == "win32":`, before `import resource`. mypy treats
the rest as unreachable on win32 and doesn't check it, and on Windows, where no mutation run happens, the cap is a
no-op. A pytest `skipif` or a `hasattr` doesn't narrow types; `sys.platform` does.

### D2. A gate for delivered files, from the delivered lists

The check gains a gate, `mypy win32 (delivered)`, running `mypy --platform win32` over the Python files named in
`tofu/guard_delivery.tf`'s `guard_files` and `mutation_report_files`. They're read through `scripts/tofu_text.py`,
which `dependabot_config.py` already uses for the same lists, so there's no second list to keep in step. It runs
everywhere the check runs (locally and CI's `check` jobs). `--platform` sets what mypy assumes, so it doesn't need
Windows.

## Risks / Trade-offs

- A second mypy pass adds a few seconds to the check → only the delivered files are checked (nine today).
- `tofu_text`'s parsing of the `.tf` file is the shared source → if that file's shape changes, its existing tests
  and this gate both fail loudly. An empty list is refused rather than passing vacuously.
