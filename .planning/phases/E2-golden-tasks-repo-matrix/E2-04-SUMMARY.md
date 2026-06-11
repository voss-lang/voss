---
phase: E2-golden-tasks-repo-matrix
plan: 04
subsystem: testing
tags: [typescript, node-test, strip-types, esm, eval, fixtures, matrix]

# Dependency graph
requires:
  - phase: E1-eval-runner
    provides: "_prepare_fixture isolated temp-dir copy that the ts cmd checks rely on"
provides:
  - "Three self-contained TypeScript ESM calc fixtures (ts-01-analyze, ts-03-approved-edit, ts-04-validation)"
  - "Editable export function add() rename target (→ sumTwo camelCase, Open Q2) in src/calc.ts for approved-edit (plan 07)"
  - "node:test call site importing './calc.ts' (explicit extension for strip-types ESM) in src/calc.test.ts"
affects: [E2-07 task.toml authoring, eval matrix runner]

# Tech tracking
tech-stack:
  added: []
  patterns: ["TS fixture = 4-file ESM project, node --experimental-strip-types --test, zero npm install / no deps / no global tsc; tsconfig.json agent-readable only"]

key-files:
  created:
    - tests/eval/matrix/ts-01-analyze/fixture/package.json
    - tests/eval/matrix/ts-01-analyze/fixture/tsconfig.json
    - tests/eval/matrix/ts-01-analyze/fixture/src/calc.ts
    - tests/eval/matrix/ts-01-analyze/fixture/src/calc.test.ts
    - tests/eval/matrix/ts-03-approved-edit/fixture/package.json
    - tests/eval/matrix/ts-03-approved-edit/fixture/tsconfig.json
    - tests/eval/matrix/ts-03-approved-edit/fixture/src/calc.ts
    - tests/eval/matrix/ts-03-approved-edit/fixture/src/calc.test.ts
    - tests/eval/matrix/ts-04-validation/fixture/package.json
    - tests/eval/matrix/ts-04-validation/fixture/tsconfig.json
    - tests/eval/matrix/ts-04-validation/fixture/src/calc.ts
    - tests/eval/matrix/ts-04-validation/fixture/src/calc.test.ts
  modified: []

key-decisions:
  - "None beyond plan — exact PATTERNS.md file bodies; npm test verified in place (no workspace-inheritance issue for npm, unlike cargo in E2-03)"

patterns-established:
  - "Matrix shape fixtures are byte-identical across cells; per-cell behavior lives in task.toml (plan 07)"

requirements-completed: [EVGLD-01]

# Metrics
duration: 4min
completed: 2026-06-11
---

# Phase E2 Plan 04: TypeScript Matrix Fixtures Summary

**Three byte-identical 4-file TypeScript ESM calc projects running on node --experimental-strip-types --test (Node v22 built-in node:test) — npm test green in all three with zero install, no deps, no global tsc**

## Performance

- **Duration:** ~4 min
- **Completed:** 2026-06-11
- **Tasks:** 1
- **Files modified:** 12 created

## Accomplishments
- ts-01-analyze, ts-03-approved-edit, ts-04-validation built as identical ESM projects (package.json `type: module` + tsconfig.json + src/calc.ts + src/calc.test.ts)
- `npm test` exits 0 in each WITHOUT npm install (node:test built-in; T-E2-08/T-E2-SC mitigations hold — no deps, no pretest hook)
- `src/calc.test.ts` imports `{ add } from './calc.ts'` with explicit .ts extension (strip-types ESM resolution requirement)
- tsconfig.json present as agent-readable type aid only — never invoked by the runner (no tsc gate; tsc not installed on this machine)

## Task Commits

1. **Task 1: Build the three TypeScript shape fixtures** - `0f5fe87` (test)

## Files Created/Modified
- `tests/eval/matrix/ts-*/fixture/package.json` - `name: calc`, `type: module`, test script `node --experimental-strip-types --test src/*.test.ts`; no dependencies
- `tests/eval/matrix/ts-*/fixture/tsconfig.json` - ES2022/NodeNext/strict, `include: ["src"]`; agent-readable only
- `tests/eval/matrix/ts-*/fixture/src/calc.ts` - `export function add(a: number, b: number): number` (approved-edit rename target → sumTwo)
- `tests/eval/matrix/ts-*/fixture/src/calc.test.ts` - node:test + assert, imports './calc.ts'

## Decisions Made
None - followed plan as specified. Verification ran in place per the plan's verify command — npm has no workspace-inheritance problem (unlike cargo in E2-03), and node:test emitted clean TAP output on Node v22.22.3 (no ExperimentalWarning failure, Pitfall 2 non-issue).

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- TypeScript shape fixtures ready for plan 07 (task.toml cmd checks)
- Approved-edit cell has definition site (src/calc.ts) + call site (src/calc.test.ts) with camelCase rename target sumTwo ready

---
*Phase: E2-golden-tasks-repo-matrix*
*Completed: 2026-06-11*
