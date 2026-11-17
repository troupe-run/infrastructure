Captured from a real Stryker 10.1.1 run with its vitest runner (2026-11-18, lint-mutation task 2.3): website's `main` at
bc78d22, `--mutate "src/lib/*.ts" --inPlace --concurrency 1`, the JSON reporter's `mutation.json` as written. 298
mutants in 31 seconds: `docs-nav.ts` 56.7%, `docs-versions.ts` 90.2%, `site-section.ts` 92.7%, `site-path.ts` 100%,
and `copy.ts`'s 9 mutants reached by no test.
