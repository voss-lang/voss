---
phase: F3-budget-token-visualization
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - crates/voss-app-core/src/pty/commands.rs
  - crates/voss-app-core/src/pty/reader.rs
  - crates/voss-app-core/src/pty/tests.rs
  - voss/harness/recorder.py
  - voss/harness/agent.py
  - voss/harness/test_budget_osc.py
autonomous: true
requirements:
  - D-01
  - D-02
  - D-03
  - D-04
  - D-14

must_haves:
  truths:
    - "extract_voss_osc parses ESC]1337;voss-budget={json}BEL from a byte buffer and returns (json_bytes, display_bytes)"
    - "extract_voss_osc returns None for partial sequences, non-matching bytes, and unrelated ANSI"
    - "reader.rs Ok(n) arm scans for voss-budget OSC and emits BudgetUpdate on match, Data on pass-through"
    - "_emit_budget_osc writes OSC 1337 voss-budget= sequence to sys.stdout with BEL terminator and flush"
    - "All three end_iteration call sites in agent.py _run_turn_exec emit OSC with cumulative totals"
  artifacts:
    - path: "crates/voss-app-core/src/pty/commands.rs"
      provides: "BudgetData struct + BudgetUpdate(BudgetData) variant on PtyEvent"
      contains: "BudgetUpdate"
    - path: "crates/voss-app-core/src/pty/reader.rs"
      provides: "extract_voss_osc pure function + modified Ok(n) arm"
      contains: "extract_voss_osc"
    - path: "crates/voss-app-core/src/pty/tests.rs"
      provides: "4 unit tests for extract_voss_osc"
      contains: "test_extract_voss_osc"
    - path: "voss/harness/recorder.py"
      provides: "_emit_budget_osc module-level function"
      contains: "_emit_budget_osc"
    - path: "voss/harness/test_budget_osc.py"
      provides: "4 unit tests for _emit_budget_osc"
      contains: "test_emit_budget_osc"
    - path: "voss/harness/agent.py"
      provides: "OSC emission at 3 end_iteration call sites"
      contains: "_emit_budget_osc"
  key_links:
    - from: "crates/voss-app-core/src/pty/reader.rs"
      to: "crates/voss-app-core/src/pty/commands.rs"
      via: "use crate::pty::commands::BudgetData"
      pattern: "BudgetData"
    - from: "voss/harness/agent.py"
      to: "voss/harness/recorder.py"
      via: "from voss.harness.recorder import _emit_budget_osc"
      pattern: "_emit_budget_osc"
---

<objective>
Implement the full backend data pipeline: Rust OSC parser in the PTY reader that extracts voss-budget sequences and emits BudgetUpdate events, plus the Python harness emission that writes OSC sequences to stdout at each agent iteration boundary.

Purpose: This is the data source and data sink for the entire F3 feature. Without the Python emission and Rust parsing, the frontend has no budget data to display.

Output: BudgetData struct, BudgetUpdate PtyEvent variant, extract_voss_osc pure function in reader.rs, _emit_budget_osc in recorder.py, call-site wiring in agent.py, and 8 unit tests (4 Rust + 4 Python).
</objective>

<execution_context>
@.planning/phases/F3-budget-token-visualization/F3-RESEARCH.md
@.planning/phases/F3-budget-token-visualization/F3-PATTERNS.md
@.planning/phases/F3-budget-token-visualization/F3-CONTEXT.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From crates/voss-app-core/src/pty/commands.rs (lines 14-21):
```rust
#[derive(serde::Serialize, Clone)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum PtyEvent {
    Data { bytes: Vec<u8> },
    Exit { code: i32 },
    FgProcess { name: String },
    TitleChange { title: String },
}
```

From crates/voss-app-core/src/pty/reader.rs (lines 31-44 — the Ok(n) arm to modify):
```rust
match reader.read(&mut buf) {
    Ok(0) => break,
    Ok(n) => {
        if on_data
            .send(PtyEvent::Data {
                bytes: buf[..n].to_vec(),
            })
            .is_err()
        {
            break;
        }
    }
    Err(_) => break,
}
```

From crates/voss-app-core/src/pty/reader.rs (line 11):
```rust
use crate::pty::commands::PtyEvent;
```

From voss/harness/recorder.py (lines 148-186):
```python
def end_iteration(self, *, plan, tool_results, cost_usd, prompt_tokens,
                  completion_tokens, cache_creation_input_tokens=0,
                  cache_read_input_tokens=0, exit_reason=None) -> None:
```

From voss/harness/agent.py — _run_turn_exec signature (lines 483-501):
```python
async def _run_turn_exec(task, *, tools, cwd, renderer,
    confidence_threshold=0.60, token_budget=60_000,
    model=None, provider=None, history=None, permissions=None,
    session_id=None, cognition=None, prior_context=None,
    voss_md_text=None, project_index_text="", steer_inbox=None):
```

Available variables at each end_iteration call site:
- `iter_cost`, `iter_prompt_tokens`, `iter_completion_tokens`
- `total_cost_usd` (accumulated BEFORE current iter at lines 750/789; accumulated AFTER at lines 810/853)
- `total_prompt_tokens`, `total_completion_tokens` (same accumulation pattern)
- `token_budget` (function parameter, always available)
- `model` (resolved at line 511: `model = model or cfg.default_model`)
- `iteration_index` (loop counter)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rust BudgetData struct + BudgetUpdate variant + extract_voss_osc parser + reader.rs wiring</name>
  <files>crates/voss-app-core/src/pty/commands.rs, crates/voss-app-core/src/pty/reader.rs, crates/voss-app-core/src/pty/tests.rs</files>
  <read_first>
    - crates/voss-app-core/src/pty/commands.rs (full file — 87 lines)
    - crates/voss-app-core/src/pty/reader.rs (full file — 58 lines)
    - crates/voss-app-core/src/pty/tests.rs (full file — 153 lines)
    - crates/voss-app-core/src/pty/mod.rs (first 30 lines — module structure)
    - .planning/phases/F3-budget-token-visualization/F3-PATTERNS.md (lines 29-213 — Pattern Assignments for reader.rs, commands.rs, tests.rs)
  </read_first>
  <action>
    **commands.rs changes (per D-02):**
    Add a `BudgetData` struct ABOVE the `PtyEvent` enum with derives `serde::Serialize, serde::Deserialize, Clone, Debug`. Fields: `tokens_used: u64`, `token_limit: Option<u64>`, `cost_usd: f64`, `iteration: u32`, `model: String`. Add `BudgetUpdate(BudgetData)` as a new variant inside the existing `PtyEvent` enum. The enum already has `#[serde(tag = "type", rename_all = "snake_case")]` so the new variant serializes as `{ "type": "budget_update", ... }`. `BudgetData` needs BOTH `Serialize` and `Deserialize` (existing variants only have `Serialize`; `BudgetData` uniquely needs `Deserialize` for `serde_json::from_slice` in reader.rs).

    **reader.rs changes (per D-01, D-14):**
    Add `use crate::pty::commands::BudgetData;` at the imports (PtyEvent is already imported). Add a `pub(crate) fn extract_voss_osc(data: &[u8]) -> Option<(Vec<u8>, Vec<u8>)>` pure function ABOVE `start_reader`. The function: defines `const PREFIX: &[u8] = b"\x1b]1337;voss-budget=";`, uses `data.windows(PREFIX.len()).position(|w| w == PREFIX)` to find the start, then searches for BEL terminator `0x07` after the prefix. Returns `Some((json_bytes, display_bytes))` where `display_bytes` = bytes before ESC concatenated with bytes after BEL. Returns `None` when prefix not found or BEL not found (buffer fragmentation safe-path per D-03 — next emission has cumulative state).

    Replace the `Ok(n)` arm body in `start_reader` (lines 33-41): call `extract_voss_osc(slice)`. On `Some`: parse `json_bytes` via `serde_json::from_slice::<BudgetData>()` — if Ok, send `PtyEvent::BudgetUpdate(data)` (use `let _ =` to ignore send error for the budget event; budget is best-effort). If `display_bytes` is non-empty, send `PtyEvent::Data { bytes: display_bytes }` with the existing `is_err() => break` pattern. On `None`: pass through unchanged as `PtyEvent::Data { bytes: slice.to_vec() }` with the existing break pattern. No debounce (D-14).

    **tests.rs changes:**
    Add 4 new tests after the existing 4 tests. Import `extract_voss_osc` from `crate::pty::reader`. Tests:
    1. `test_extract_voss_osc_parses_well_formed` — construct `PREFIX + valid_json + BEL`, assert json_bytes matches payload and display_bytes is empty.
    2. `test_extract_voss_osc_strips_surrounding_display_bytes` — prepend "hello " and append " world" around the OSC sequence, assert display_bytes equals b"hello  world".
    3. `test_extract_voss_osc_returns_none_for_partial_sequence` — provide prefix + truncated JSON with no BEL, assert None.
    4. `test_extract_voss_osc_returns_none_for_unrelated_bytes` — provide normal ANSI escape sequences (e.g., `b"\x1b[32mgreen\x1b[0m"`), assert None.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core osc 2>&1 | tail -20 && cargo test -p voss-app-core pty 2>&1 | tail -10 && cargo build -p voss-app-core 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `cargo test -p voss-app-core osc` shows 4 tests passing with names containing `extract_voss_osc`
    - `cargo test -p voss-app-core pty` shows all existing tests still passing (no regression)
    - `cargo build -p voss-app-core` exits 0 with no warnings on the new code
    - `grep -c "BudgetUpdate" crates/voss-app-core/src/pty/commands.rs` returns at least 1
    - `grep -c "extract_voss_osc" crates/voss-app-core/src/pty/reader.rs` returns at least 2 (definition + call)
    - `grep -c "BudgetData" crates/voss-app-core/src/pty/commands.rs` returns at least 1
  </acceptance_criteria>
  <done>BudgetData struct and BudgetUpdate variant exist in commands.rs. extract_voss_osc pure function in reader.rs parses well-formed OSC, strips surrounding display bytes, and returns None for partial/unrelated input. reader.rs Ok(n) arm calls extract_voss_osc and emits BudgetUpdate or Data accordingly. 4 Rust unit tests pass. No regression on existing 4 PTY tests.</done>
</task>

<task type="auto">
  <name>Task 2: Python _emit_budget_osc helper + agent.py call-site wiring + Python tests</name>
  <files>voss/harness/recorder.py, voss/harness/agent.py, voss/harness/test_budget_osc.py</files>
  <read_first>
    - voss/harness/recorder.py (lines 1-30 for imports + lines 140-190 for end_iteration)
    - voss/harness/agent.py (lines 483-510 for _run_turn_exec signature, lines 695-860 for the 3 end_iteration call sites and cumulative total accumulation)
    - .planning/phases/F3-budget-token-visualization/F3-PATTERNS.md (lines 776-862 — test_budget_osc.py pattern)
    - .planning/phases/F3-budget-token-visualization/F3-RESEARCH.md (lines 306-358 — Pattern 4: Harness OSC Emission)
  </read_first>
  <action>
    **recorder.py changes (per D-02, D-04):**
    Add a module-level function `_emit_budget_osc` (NOT a method on RunRecorder — per Open Question 2 resolution). Place it AFTER the imports, BEFORE the `RunRecorder` class. Signature: `def _emit_budget_osc(*, tokens_used: int, token_limit: int | None, cost_usd: float, iteration: int, model: str) -> None`. Body: `import json, sys` at module top (json is likely already imported; add `sys` if not present). Build a dict with the 5 fields, serialize with `json.dumps(..., separators=(",", ":"))` for compact output, then `sys.stdout.write(f"\x1b]1337;voss-budget={payload}\x07")` followed by `sys.stdout.flush()`. The docstring should reference D-02 and note that the sequence is stripped by reader.rs before reaching xterm. Do NOT write to sys.stderr (Pitfall 7).

    **agent.py changes (per D-04, Open Question 1 — emit at all 3 sites):**
    Add `from voss.harness.recorder import _emit_budget_osc` to agent.py imports. After EACH of the three `rec.end_iteration(...)` calls in `_run_turn_exec`, add a call to `_emit_budget_osc(...)`. The cumulative totals differ by call site:

    Call site 1 (line ~750, clarify exit) — `total_cost_usd` and `total_prompt_tokens`/`total_completion_tokens` have NOT been incremented with current iter yet. Use:
      `tokens_used=total_prompt_tokens + total_completion_tokens + iter_prompt_tokens + iter_completion_tokens`
      `token_limit=token_budget`
      `cost_usd=total_cost_usd + iter_cost`
      `iteration=iteration_index + 1`
      `model=model`

    Call site 2 (line ~789, done plan normal) — same situation, totals NOT yet incremented. Same formula as site 1.

    Call site 3 (line ~832, non-terminating) — same situation, totals NOT yet incremented (they get incremented at lines 853-854 AFTER). Same formula as site 1.

    All three use identical kwargs. To avoid repetition, define a local helper at the top of the iteration loop body (or just before the first call site, inside the try block) named `_emit_osc` that captures the closure variables and calls `_emit_budget_osc`. Or simply inline the call 3 times — the kwargs are the same formula.

    **test_budget_osc.py (new file, per D-02/D-04):**
    Create `voss/harness/test_budget_osc.py`. Use `from __future__ import annotations`, import `io`, `json`, `pytest`, and `from voss.harness.recorder import _emit_budget_osc`. Write 4 tests using `monkeypatch` to capture `sys.stdout`:

    1. `test_emit_budget_osc_writes_to_stdout` — capture stdout, call with sample values, assert output starts with `\x1b]1337;voss-budget=` and ends with `\x07`.
    2. `test_emit_budget_osc_payload_is_valid_json` — extract JSON between prefix and BEL, parse with `json.loads`, assert all 5 fields match input values. Use `pytest.approx` for float.
    3. `test_emit_budget_osc_unlimited_budget` — call with `token_limit=None`, assert JSON contains `"token_limit":null`.
    4. `test_emit_budget_osc_not_to_stderr` — capture both stdout and stderr, assert stderr is empty and stdout is non-empty.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest voss/harness/test_budget_osc.py -x -v 2>&1 | tail -20 && .venv/bin/python -c "from voss.harness.recorder import _emit_budget_osc; print('import ok')" && grep -c "_emit_budget_osc" voss/harness/agent.py</automated>
  </verify>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest voss/harness/test_budget_osc.py -x -v` shows 4 tests passing
    - `grep -c "_emit_budget_osc" voss/harness/agent.py` returns at least 3 (one import + 3 call sites, or 1 import + 1 helper + 3 calls)
    - `grep -c "_emit_budget_osc" voss/harness/recorder.py` returns at least 1 (the function definition)
    - `.venv/bin/python -c "from voss.harness.recorder import _emit_budget_osc"` exits 0
    - `grep "sys.stdout.write" voss/harness/recorder.py` finds the OSC write line
    - `grep "sys.stdout.flush" voss/harness/recorder.py` finds the flush call
    - `grep "sys.stderr" voss/harness/recorder.py` returns empty (no stderr usage in _emit_budget_osc)
  </acceptance_criteria>
  <done>_emit_budget_osc is a module-level function in recorder.py that writes OSC 1337 voss-budget= to stdout with flush. All 3 end_iteration call sites in agent.py _run_turn_exec follow with an _emit_budget_osc call passing cumulative tokens_used, token_budget as token_limit, cumulative cost_usd, 1-based iteration, and resolved model. 4 Python unit tests pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Python harness stdout → PTY byte stream | Harness process writes OSC to its own stdout; PTY reader reads raw bytes |
| PTY reader → Channel<PtyEvent> | Rust reader emits typed events to frontend transport |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-F3-01 | Spoofing | reader.rs extract_voss_osc | accept | Non-sensitive payload (cost/tokens only); injected fake data causes cosmetic HUD corruption, not security breach. No secrets in payload (D-03). |
| T-F3-02 | DoS | reader.rs serde_json::from_slice | mitigate | Input bounded by 8192-byte read buffer; serde_json returns Result, errors silently discarded (no panic). |
| T-F3-03 | DoS | reader.rs extract_voss_osc | mitigate | Linear scan with windows(), O(n) on bounded buffer. No regex, no unbounded allocation. |
| T-F3-04 | Info Disclosure | recorder.py _emit_budget_osc | accept | Payload contains only tokens_used/token_limit/cost_usd/iteration/model — no API keys, no session content, no PII. |
| T-F3-SC | Tampering | npm/pip/cargo installs | accept | F3 adds zero new dependencies — all implementation uses existing packages. |
</threat_model>

<verification>
- `cargo test -p voss-app-core` — all PTY tests pass (existing 4 + new 4 OSC tests)
- `cargo build -p voss-app-core` — clean build, no warnings
- `.venv/bin/python -m pytest voss/harness/test_budget_osc.py -x -v` — 4 Python tests pass
- `grep -c "BudgetUpdate" crates/voss-app-core/src/pty/commands.rs` >= 1
- `grep -c "_emit_budget_osc" voss/harness/agent.py` >= 3
</verification>

<success_criteria>
The Rust PTY reader correctly parses OSC 1337 voss-budget= sequences from the byte stream, emits BudgetUpdate events on the existing Channel, and strips the OSC from display bytes. The Python harness emits cumulative budget data as OSC sequences to stdout after every end_iteration call. Both are tested independently.
</success_criteria>

<output>
Create `.planning/phases/F3-budget-token-visualization/F3-01-SUMMARY.md` when done
</output>
