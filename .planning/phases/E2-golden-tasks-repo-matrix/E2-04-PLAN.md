---
phase: E2-golden-tasks-repo-matrix
plan: 04
type: execute
wave: 1
depends_on: []
files_modified:
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
autonomous: true
requirements: [EVGLD-01]
must_haves:
  truths:
    - "Each TypeScript shape fixture (ts-01/03/04) is a 4-file ESM project (package.json + tsconfig.json + src/calc.ts + src/calc.test.ts) with an editable add() function"
    - "npm test exits 0 inside any of the three fixtures WITHOUT npm install (node:test is built-in)"
    - "The test runner is node --experimental-strip-types --test — no global tsc dependency"
  artifacts:
    - path: "tests/eval/matrix/ts-01-analyze/fixture/package.json"
      provides: "ESM manifest with node:test script, type: module"
      contains: "node --experimental-strip-types --test"
    - path: "tests/eval/matrix/ts-03-approved-edit/fixture/src/calc.ts"
      provides: "Editable add() rename target (→ sumTwo camelCase)"
      contains: "export function add"
    - path: "tests/eval/matrix/ts-04-validation/fixture/src/calc.test.ts"
      provides: "node:test importing calc.ts"
      contains: "from './calc.ts'"
  key_links:
    - from: "tests/eval/matrix/ts-*/fixture/src/calc.test.ts"
      to: "tests/eval/matrix/ts-*/fixture/src/calc.ts"
      via: "import { add } from './calc.ts' (ESM, node strip-types)"
      pattern: "from './calc"
---

<objective>
Build the three TypeScript matrix fixture directories under `tests/eval/matrix/ts-*/fixture/`. Each shape-sensitive cell (ts-01-analyze, ts-03-approved-edit, ts-04-validation) gets an identical 4-file ESM `calc` project: `package.json` (`type: module`, `test` script running `node --experimental-strip-types --test src/*.test.ts`) + `tsconfig.json` (agent-readable type aid, NOT used by the test runner) + `src/calc.ts` with an editable `export function add()` + `src/calc.test.ts` using `node:test`. TypeScript has no language-agnostic cells (D-02: only analyze/approved-edit/validation run on ts).

Purpose: Provides the TypeScript project shape the runner copies + `npm test`-checks in an isolated temp dir (EVGLD-01, D-01). Uses Node v22's built-in `node:test` + `--experimental-strip-types` so there is ZERO npm install and NO global `tsc` requirement (RESEARCH: tsc not installed on this machine).
Output: Three `ts-*/fixture/` projects, each self-contained and ≤ 5 files (D-01 limit, 4 files each).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/E2-golden-tasks-repo-matrix/E2-RESEARCH.md
@.planning/phases/E2-golden-tasks-repo-matrix/E2-PATTERNS.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Build the three TypeScript shape fixtures (ts-01, ts-03, ts-04)</name>
  <files>tests/eval/matrix/ts-01-analyze/fixture/{package.json,tsconfig.json,src/calc.ts,src/calc.test.ts}, tests/eval/matrix/ts-03-approved-edit/fixture/{package.json,tsconfig.json,src/calc.ts,src/calc.test.ts}, tests/eval/matrix/ts-04-validation/fixture/{package.json,tsconfig.json,src/calc.ts,src/calc.test.ts}</files>
  <read_first>
    - E2-RESEARCH.md §TypeScript Fixture lines 422-471 (VERIFIED locally: `npm test` passes without npm install via node --experimental-strip-types --test; tsconfig.json is for agent-readability only, NOT compilation; tsc not global so no tsc gate)
    - E2-PATTERNS.md §`tests/eval/matrix/ts-*/fixture/` lines 320-366 (exact file bodies; package.json `type: module` required for ESM imports)
    - E2-RESEARCH.md Pitfall 2 lines 613-616 (Node ExperimentalWarning on stderr does NOT cause non-zero exit — _run_checks keys on returncode, no special handling)
    - E2-RESEARCH.md "Don't Hand-Roll" lines 351 + anti-pattern lines 336-337 (do NOT add a scripts.pretest npm install; do NOT use tsc for test execution)
  </read_first>
  <action>
    Create three IDENTICAL ESM project trees (one per shape cell). For each of ts-01-analyze, ts-03-approved-edit, ts-04-validation: write `fixture/package.json` with `"name": "calc"`, `"type": "module"` (required for the `./calc.ts` ESM import), and `"scripts": { "test": "node --experimental-strip-types --test src/*.test.ts" }` — NO `dependencies`, NO `devDependencies`, NO `pretest` install hook (node:test is built-in to Node v22). Write `fixture/tsconfig.json` with `compilerOptions` (`target: ES2022`, `module: NodeNext`, `moduleResolution: NodeNext`, `strict: true`) and `"include": ["src"]` — this exists ONLY so analyze can name the `tsconfig`/`package.json` tooling and the agent reads types; it is NOT invoked by the test runner. Write `fixture/src/calc.ts` defining `export function add(a: number, b: number): number { return a + b; }` (approved-edit rename target → `sumTwo`, camelCase per RESEARCH Open Q2). Write `fixture/src/calc.test.ts` importing `{ test } from 'node:test'`, `assert from 'node:assert'`, and `{ add } from './calc.ts'` (note the explicit `.ts` extension — required for node strip-types ESM resolution), then `test('add(1, 2) === 3', () => { assert.strictEqual(add(1, 2), 3); })`. The three projects are byte-identical; per-cell behavior lives in the task.toml (plan 07).
  </action>
  <acceptance_criteria>
    - For each of the three dirs: `npm test` exits 0 WITHOUT a prior `npm install` (run via the verify command below; ExperimentalWarning on stderr is expected and does NOT fail the check per Pitfall 2)
    - `grep -L "node_modules\|npm install\|\"dependencies\"" tests/eval/matrix/ts-0{1,3,4}-*/fixture/package.json` lists all three (no install step, no deps)
    - `grep -l "export function add" tests/eval/matrix/ts-0{1,3,4}-*/fixture/src/calc.ts` lists all three
    - Each fixture dir contains exactly 4 files: `find tests/eval/matrix/ts-01-analyze/fixture -type f | wc -l` equals 4
    - `grep -c "from './calc.ts'" tests/eval/matrix/ts-03-approved-edit/fixture/src/calc.test.ts` equals 1 (explicit .ts extension for strip-types ESM)
  </acceptance_criteria>
  <verify>
    <automated>for d in ts-01-analyze ts-03-approved-edit ts-04-validation; do (cd tests/eval/matrix/$d/fixture && npm test) || exit 1; done</automated>
  </verify>
  <done>All three TypeScript shape fixtures exist as 4-file ESM projects; npm test passes in each with no npm install and no global tsc; editable export function add() present; node:test imports calc.ts with explicit extension.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| fixture project → runner's isolated copy | Project is static, committed; copied to a temp dir before any node invocation (E1 `_prepare_fixture`) |
| npm test → fixture copy cwd | `npm test` (→ node --test) executes ONLY in the isolated temp copy, never the Voss repo root |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E2-08 | Tampering | node executing arbitrary package code | mitigate | NO `dependencies`/`devDependencies` and NO `npm install` — node:test is a built-in; zero third-party code fetched or run; node executes in the isolated temp copy only. |
| T-E2-09 | Tampering | Prompt injection via fixture content | accept | Fixtures are static + committed; no user-supplied content (RESEARCH Security Domain). |
| T-E2-SC | Tampering | npm install in fixture | mitigate | NO `scripts.pretest` install hook (anti-pattern lines 336); the test script is offline-only `node --experimental-strip-types --test`. |
</threat_model>

<verification>
- All three projects pass `npm test` in their isolated dirs with no npm install.
- No package.json has dependencies/devDependencies or an install hook.
- Each fixture ≤ 5 files (4 each); test imports calc.ts with explicit extension; no tsc gate.
</verification>

<success_criteria>
- Three `tests/eval/matrix/ts-*/fixture/` projects exist
- Each is a self-contained 4-file ESM calc project with editable `export function add()`
- npm test green in each (zero install, no global tsc); EVGLD-01 TypeScript shape satisfied
- camelCase rename target (sumTwo) + explicit .ts import extension ready for approved-edit (plan 07)
</success_criteria>

<output>
Create `.planning/phases/E2-golden-tasks-repo-matrix/E2-04-SUMMARY.md` when done
</output>
