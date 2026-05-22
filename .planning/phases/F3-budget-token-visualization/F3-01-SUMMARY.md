---
phase: F3-budget-token-visualization
plan: 01
status: done
---

# F3-01 Summary: Backend Data Pipeline

## What was built

### Rust (PTY reader → BudgetUpdate events)
- **`commands.rs`** — `BudgetData` struct (Serialize + Deserialize) with 5 fields: `tokens_used`, `token_limit`, `cost_usd`, `iteration`, `model`. `BudgetUpdate(BudgetData)` variant added to `PtyEvent` enum.
- **`reader.rs`** — `extract_voss_osc(data: &[u8])` pure function scans for `ESC]1337;voss-budget={json}BEL`, returns `(json_bytes, display_bytes)`. `Ok(n)` arm calls it: on match, parses JSON into `BudgetData`, emits `BudgetUpdate` (best-effort), forwards remaining display bytes; on `None`, passes through unchanged.
- **`tests.rs`** — 4 unit tests: well-formed parse, surrounding display byte stripping, partial sequence → None, unrelated ANSI → None.

### Python (harness emission)
- **`recorder.py`** — `_emit_budget_osc()` module-level function writes compact JSON as OSC 1337 to `sys.stdout` with flush. No stderr.
- **`agent.py`** — Import + 3 call sites after each `rec.end_iteration()` in `_run_turn_exec`. All use cumulative totals (not yet incremented) + current iter values. 1-based iteration index.
- **`test_budget_osc.py`** — 4 tests: stdout write, valid JSON payload, `token_limit=None`, no stderr.

## Verification

| Check | Result |
|-------|--------|
| `cargo test -p voss-app-core osc` | 4 passed |
| `cargo test -p voss-app-core pty` | 14 passed (no regression) |
| `cargo build -p voss-app-core` | clean, no warnings |
| `pytest voss/harness/test_budget_osc.py` | 4 passed |
| `_emit_budget_osc` refs in agent.py | 4 (1 import + 3 calls) |

## Files modified
- `crates/voss-app-core/src/pty/commands.rs`
- `crates/voss-app-core/src/pty/reader.rs`
- `crates/voss-app-core/src/pty/tests.rs`
- `voss/harness/recorder.py`
- `voss/harness/agent.py`
- `voss/harness/test_budget_osc.py` (new)
