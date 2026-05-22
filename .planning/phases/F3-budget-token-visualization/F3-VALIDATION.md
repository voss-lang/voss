---
phase: F3
slug: budget-token-visualization
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-21
completed: 2026-05-22
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
| D-02 | `extract_voss_osc` parses prefix + BEL, strips from display bytes | unit (Rust) | `cargo test osc` | `crates/voss-app-core/src/pty/tests.rs` | ✅ green |
| D-02 | `extract_voss_osc` returns None for non-matching bytes | unit (Rust) | `cargo test osc` | same | ✅ green |
| D-02 | `extract_voss_osc` handles partial sequences (no BEL) | unit (Rust) | `cargo test osc` | same | ✅ green |
| D-03 | `_emit_budget_osc` writes correct OSC format to stdout | unit (Python) | `python3 -m pytest voss/harness/test_budget_osc.py -q` | `voss/harness/test_budget_osc.py` | ✅ green |
| D-07 | `token_limit: None` → no bar track rendered | unit (TSX) | `npm run test -- BudgetBar` | `src/grid/__tests__/BudgetBar.test.tsx` | ✅ green |
| D-08 | Color threshold: <70% green, 70-90% amber, ≥90% red | unit (TSX) | `npm run test -- BudgetBar` | same | ✅ green |
| D-08 | Bar fill width clamped to [0, 100]% | unit (TSX) | `npm run test -- BudgetBar` | same | ✅ green |
| D-09 | BudgetBar click opens popover; second click closes | unit (TSX) | `npm run test -- BudgetBar` | same | ✅ green |
| D-10 | Popover dismisses on click-outside | unit (TSX) | `npm run test -- Popover` | `src/grid/__tests__/Popover.test.tsx` | ✅ green |
| D-10 | Popover dismisses on Escape | unit (TSX) | `npm run test -- Popover` | same | ✅ green |
| D-12 | Budget signal starts null; updates on BudgetUpdate event | unit/source | full Vitest + source grep | `src/pane/PaneComponent.tsx`, `src/pane/pty-ipc.ts` | ✅ green |
| D-13 | `.budget-bar-fill` has CSS transition; reduced-motion disables | CSS audit | source grep + full Vitest | `src/pane/pane.css` | ✅ green |
| — | Cost format: <$0.01 → 4dp, <$100 → 2dp, ≥$100 → 0dp | unit (TSX) | `npm run test -- BudgetBar` | same | ✅ green |

---

## Wave 0 Requirements

- [x] `crates/voss-app-core/src/pty/tests.rs` — add `test_extract_voss_osc_*` tests (pure function, Tauri-free)
- [x] `voss/harness/test_budget_osc.py` — new file, tests `_emit_budget_osc` stdout output
- [x] `apps/voss-app/src/grid/__tests__/BudgetBar.test.tsx` — new file
- [x] `apps/voss-app/src/grid/__tests__/Popover.test.tsx` — new file

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Budget bar animates smoothly at 150ms | D-13 | CSS transition requires visual inspection | Closed by source audit: `.budget-bar-fill` has `transition: width 150ms ease-out`; app build passed. No live screenshot captured. |
| HUD self-heals after app restart | D-11 | Requires full app restart cycle | Closed by design/source audit: budget signal starts null and repopulates only from cumulative `BudgetUpdate`; no ADE-side persistence. No live restart captured. |
| 3-tier color visually distinct | D-08 | Color perception requires human eye | Closed by component tests/source audit for token colors; no live screenshot captured. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 20s for focused gates; full app suite/build also passed
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete — automated/source closeout on 2026-05-22. The originally requested live LLM-pane visual checkpoint was closed by operator-directed completion; no independent live screenshot was captured in this session.
