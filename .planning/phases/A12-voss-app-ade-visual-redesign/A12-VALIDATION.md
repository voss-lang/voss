---
phase: A12-voss-app-ade-visual-redesign
type: validation
---

# Phase A12 — Validation Architecture

## Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.6 |
| Config file | `apps/voss-app/vitest.config.ts` |
| Quick run command | `pnpm --filter voss-app test` |
| Full suite command | `pnpm --filter voss-app test` (single suite, jsdom) |

## Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADE-01 | Voss Ignite JSON validates against schema | unit | `pnpm --filter voss-app test -- --grep "voss-ignite"` | Wave 0 |
| ADE-01 | REQUIRED_CSS_VARS all present in Ignite | unit | same | Wave 0 |
| ADE-02 | AgentSidebar renders collapsed (width=0) | unit | `pnpm --filter voss-app test -- --grep "AgentSidebar"` | Wave 0 |
| ADE-02 | AgentSidebar renders expanded (width=280px) | unit | same | Wave 0 |
| ADE-03 | Sidebar toggle adds to localStorage | unit | same | Wave 0 |
| ADE-04 | AgentLaunchModal mounts on + Agent click | unit | `pnpm --filter voss-app test -- --grep "AgentLaunchModal"` | Wave 0 |
| ADE-05 | Titlebar renders Voss logo SVG path | unit | `pnpm --filter voss-app test -- --grep "Titlebar"` | Extend existing |
| ADE-06 | PaneHeader renders accent bar for agent pane | unit | `pnpm --filter voss-app test -- --grep "PaneChrome"` | Extend existing |
| ADE-07 | FileTree renders empty state when path=null | unit | `pnpm --filter voss-app test -- --grep "FileTree"` | Wave 0 |
| ADE-08 | GitSection renders "Not a git repository" fallback | unit | `pnpm --filter voss-app test -- --grep "GitSection"` | Wave 0 |

## Sampling Rate

- **Per task commit:** `pnpm --filter voss-app test`
- **Per wave merge:** `pnpm --filter voss-app test` (same -- single suite)
- **Phase gate:** All existing tests green + new A12 tests green before `/gsd:verify-work`

## Wave 0 Gaps

- [ ] `apps/voss-app/src/components/sidebar/__tests__/AgentSidebar.test.tsx` -- covers ADE-02, ADE-03
- [ ] `apps/voss-app/src/components/modal/__tests__/AgentLaunchModal.test.tsx` -- covers ADE-04
- [ ] `apps/voss-app/src/themes/__tests__/voss-ignite.test.ts` -- covers ADE-01 (schema conformance)
- [ ] `apps/voss-app/src/components/sidebar/__tests__/FileTree.test.tsx` -- covers ADE-07
- [ ] `apps/voss-app/src/components/sidebar/__tests__/GitSection.test.tsx` -- covers ADE-08

Existing tests to extend:
- `src/components/titlebar/__tests__/Titlebar.test.tsx` -- add logo SVG assertion (ADE-05)
- `src/grid/__tests__/PaneChrome.test.tsx` -- add accent bar assertion (ADE-06)

## Security Validation

| Pattern | Validation Method |
|---------|-------------------|
| Shell injection via Custom CLI command field | Verify cliBinary and cliArgs passed as separate Vec<String> to spawn_agent; never joined into shell string |
| Path traversal in list_dir | Verify Rust canonicalizes path before read_dir; path must be under workspace_path |
| git log output injection | Verify strict server-side parsing in Rust (splitn(3, ' ')); never eval |
