---
phase: F3
slug: budget-token-visualization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-21
---

# Phase F3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Frontend framework** | Vitest + jsdom (`vitest.config.ts`: `environment: 'jsdom'`) |
| **Rust framework** | `cargo test` (crates/voss-app-core) |
| **Python framework** | pytest (`.venv/bin/python -m pytest`) |
| **Frontend quick run** | `cd apps/voss-app && npm run test -- --reporter=dot` |
| **Frontend full suite** | `cd apps/voss-app && npm run test` |
| **Rust quick run** | `cd crates/voss-app-core && cargo test pty` |
| **Python quick run** | `.venv/bin/python -m pytest voss/harness/ -x -q` |
| **Estimated runtime** | ~15 seconds (vitest) + ~5 seconds (cargo) + ~3 seconds (pytest) |

---

## Sampling Rate

- **After every task commit:** `cd apps/voss-app && npm run test -- --reporter=dot` + `cargo test pty -q`
- **After every plan wave:** Full vitest suite + full cargo test + pytest harness
- **Before `/gsd:verify-work`:** All suites green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Req | Behavior | Test Type | Automated Command | File | Status |
|-----|----------|-----------|-------------------|------|--------|
| D-02 | `extract_voss_osc` parses prefix + BEL, strips from display bytes | unit (Rust) | `cargo test osc` | `crates/voss-app-core/src/pty/tests.rs` | ⬜ pending |
| D-02 | `extract_voss_osc` returns None for non-matching bytes | unit (Rust) | `cargo test osc` | same | ⬜ pending |
| D-02 | `extract_voss_osc` handles partial sequences (no BEL) | unit (Rust) | `cargo test osc` | same | ⬜ pending |
| D-03 | `_emit_budget_osc` writes correct OSC format to stdout | unit (Python) | `.venv/bin/python -m pytest voss/harness/test_budget_osc.py -x` | `voss/harness/test_budget_osc.py` | ⬜ pending |
| D-07 | `token_limit: None` → no bar track rendered | unit (TSX) | `npm run test -- BudgetBar` | `src/grid/__tests__/BudgetBar.test.tsx` | ⬜ pending |
| D-08 | Color threshold: <70% green, 70-90% amber, ≥90% red | unit (TSX) | `npm run test -- BudgetBar` | same | ⬜ pending |
| D-08 | Bar fill width clamped to [0, 100]% | unit (TSX) | `npm run test -- BudgetBar` | same | ⬜ pending |
| D-09 | BudgetBar click opens popover; second click closes | unit (TSX) | `npm run test -- BudgetBar` | same | ⬜ pending |
| D-10 | Popover dismisses on click-outside | unit (TSX) | `npm run test -- Popover` | `src/grid/__tests__/Popover.test.tsx` | ⬜ pending |
| D-10 | Popover dismisses on Escape | unit (TSX) | `npm run test -- Popover` | same | ⬜ pending |
| D-12 | Budget signal starts null; updates on BudgetUpdate event | unit (TSX) | `npm run test -- pty-ipc` | `src/pane/__tests__/pty-ipc.test.ts` | ⬜ pending |
| D-13 | `.budget-bar-fill` has CSS transition; media query disables | CSS audit | manual | `src/grid/BudgetBar.tsx` | ⬜ pending |
| — | Cost format: <$0.01 → 4dp, <$100 → 2dp, ≥$100 → 0dp | unit (TSX) | `npm run test -- BudgetBar` | same | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `crates/voss-app-core/src/pty/tests.rs` — add `test_extract_voss_osc_*` tests (pure function, Tauri-free)
- [ ] `voss/harness/test_budget_osc.py` — new file, tests `_emit_budget_osc` stdout output
- [ ] `apps/voss-app/src/grid/__tests__/BudgetBar.test.tsx` — new file
- [ ] `apps/voss-app/src/grid/__tests__/Popover.test.tsx` — new file

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Budget bar animates smoothly at 150ms | D-13 | CSS transition requires visual inspection | Run agent, observe bar fill transition |
| HUD self-heals after app restart | D-11 | Requires full app restart cycle | Quit app with active agent → relaunch → verify budget repopulates after first LLM response |
| 3-tier color visually distinct | D-08 | Color perception requires human eye | Trigger each threshold, verify green/amber/red distinguishable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
