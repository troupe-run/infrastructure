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

## 2. Delivery

- [ ] 2.1 The plan delivers the new `scripts/quality_gates.py` to troupe and website and changes nothing else. Verify
      with the pull request's plan run
