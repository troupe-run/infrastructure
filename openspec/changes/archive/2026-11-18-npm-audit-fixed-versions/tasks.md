# Tasks

## 1. Root advisories judged by OSV (design D1–D3)

- [x] 1.1 Tests first, from website's real `npm audit --json` and OSV records of 2026-11-18: picomatch's high
      advisory, which npm marks fixable by downgrading astro, doesn't block; each root advisory appears once; the
      moderate ones carry OSV's fixed versions; an advisory OSV fixes blocks when its severity is blocked (the lodash
      and minimist fixture); OSV unreachable fails. Verify they fail on the merged module. Done: all 7 failed, and
      the merged module blocked 20 of website's 30 npm entries on its real lock
- [x] 1.2 Rewrite `npm_audit_advisories` to read root advisories and an injected OSV fixed-version lookup, sharing one
      OSV read with the severity lookup. Verify 1.1 passes, ruff and mypy are clean, and a live run on website's lock
      reports picomatch as not blocking. Done: 77 tests pass; live on website's lock, 4 root advisories, picomatch
      "high, no fix yet", none blocking

## 2. A record OSV lacks (design D4; owner, 2026-11-18)

- [x] 2.1 `_npm_own_fix`: with no OSV record, npm's `fixAvailable` counts only when it names the vulnerable package.
      Tests in `scripts/tests/test_guard_quality_gates.py`:
      `test_without_an_osv_record_npms_fix_counts_when_it_names_the_package_itself`,
      `test_without_an_osv_record_npms_fix_doesnt_count_when_it_names_a_dependent` and
      `test_an_osv_record_wins_over_npms_fix`. Verify each fails when its rule is broken. Done: all three caught

## Workflow follow-up

- The plan the owner approves delivers the new `scripts/quality_gates.py` to troupe and website and changes nothing
  else. Read it before queueing (it needs the owner's approval, so it isn't a tracked task).
