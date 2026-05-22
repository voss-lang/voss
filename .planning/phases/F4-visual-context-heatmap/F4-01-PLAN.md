---
phase: F4
plan_id: F4-01
title: "Rust OSC parsing for voss-context= + PtyEvent::ContextUpdate + tests"
wave: 1
depends_on: []
files_modified:
  - crates/voss-app-core/src/pty/commands.rs
  - crates/voss-app-core/src/pty/reader.rs
  - crates/voss-app-core/src/pty/tests.rs
autonomous: true
status: pending
---

<objective>
Extend the Rust PTY reader to parse `voss-context=` OSC sequences alongside the existing `voss-budget=` parsing. Add `ContextData` and `FileContextEntry` structs to `commands.rs`, add a `PtyEvent::ContextUpdate(ContextData)` variant, parameterize `extract_voss_osc` to handle both prefixes, and wire the reader loop to emit `ContextUpdate` events. All changes extend the F3 pattern — no new architectural decisions.

Purpose: This is the Rust side of the data pipeline. Without context OSC parsing, no context data reaches the frontend.

Output: `ContextData`/`FileContextEntry` structs, `ContextUpdate` PtyEvent variant, parameterized `extract_voss_osc`, updated reader loop handling both OSC types, and 6 new Rust unit tests.
</objective>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Python harness stdout -> PTY byte stream | Harness writes `voss-context=` OSC to stdout; Rust reader parses raw bytes |
| PTY reader -> Channel\<PtyEvent\> | Reader emits typed ContextUpdate events to frontend transport |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-F4-01 | Tampering | reader.rs serde_json::from_slice | mitigate | Malformed JSON returns Err -> silently dropped (existing pattern). No panic path. |
| T-F4-02 | DoS | reader.rs extract_voss_osc | mitigate | Linear scan on 8192-byte bounded buffer. Two scans per read (budget + context) is negligible at OSC cadence (~1/iteration). |
| T-F4-03 | DoS | ContextData payload | mitigate | File list capped at 200 entries in Python emission (F4-02). Rust side bounded by 8192 read buffer. |
| T-F4-04 | Info Disclosure | ContextData file paths | accept | Paths are relative project paths, data stays local (Tauri Channel, no network). |
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add ContextData/FileContextEntry structs + PtyEvent::ContextUpdate variant</name>
  <files>crates/voss-app-core/src/pty/commands.rs</files>
  <read_first>
    - crates/voss-app-core/src/pty/commands.rs (full file — 100 lines)
    - .planning/phases/F4-visual-context-heatmap/F4-CONTEXT.md (D-23, D-25 — payload shape and event variant)
    - .planning/phases/F4-visual-context-heatmap/F4-RESEARCH.md (lines 93-112 — ContextData/FileContextEntry struct definitions)
  </read_first>
  <action>
    **Add `FileContextEntry` struct** after the existing `BudgetData` struct (around line 22). Derives: `serde::Serialize, serde::Deserialize, Clone, Debug`. Fields:
    - `pub path: String`
    - `pub tokens: u64`
    - `pub state: String` (values: "full" | "compressed" | "dropped")
    - `pub pinned: bool`

    **Add `ContextData` struct** immediately after `FileContextEntry`. Same derives. Fields per D-25:
    - `pub system_tokens: u64`
    - `pub conversation_tokens: u64`
    - `pub total_tokens: u64`
    - `pub token_limit: Option<u64>`
    - `pub files: Vec<FileContextEntry>`

    **Add `ContextUpdate(ContextData)` variant** to the `PtyEvent` enum, after the existing `BudgetUpdate(BudgetData)` variant. The existing `#[serde(tag = "type", rename_all = "snake_case")]` attribute auto-serializes this as `{ "type": "context_update", ... }`.

    Doc comment on `ContextData`: `/// Context window telemetry extracted from ESC]1337;voss-context={json}BEL OSC sequences.`
    Doc comment on `FileContextEntry`: `/// Per-file entry within ContextData.`
  </action>
  <acceptance_criteria>
    - `grep -c "ContextData" crates/voss-app-core/src/pty/commands.rs` returns at least 2 (struct def + variant usage)
    - `grep -c "FileContextEntry" crates/voss-app-core/src/pty/commands.rs` returns at least 2 (struct def + field usage)
    - `grep -c "ContextUpdate" crates/voss-app-core/src/pty/commands.rs` returns at least 1
    - `ContextData` has both `Serialize` and `Deserialize` derives (needed for `serde_json::from_slice` in reader.rs)
    - `cargo build -p voss-app-core` exits 0 with no warnings on new code
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Parameterize extract_voss_osc for multi-prefix scanning</name>
  <files>crates/voss-app-core/src/pty/reader.rs</files>
  <read_first>
    - crates/voss-app-core/src/pty/reader.rs (full file — 97 lines)
    - crates/voss-app-core/src/pty/tests.rs (lines 155-191 — existing extract_voss_osc tests reference the old signature)
    - .planning/phases/F4-visual-context-heatmap/F4-RESEARCH.md (lines 22-34 — Approach 1: parameterized prefix recommendation)
  </read_first>
  <action>
    **Change `extract_voss_osc` signature** from `pub(crate) fn extract_voss_osc(data: &[u8])` to `pub(crate) fn extract_voss_osc(data: &[u8], prefix: &[u8])`. Remove the hardcoded `const PREFIX` inside the function body and use the `prefix` parameter instead. The logic remains identical — scan with `data.windows(prefix.len()).position(|w| w == prefix)`, find BEL, split into (json_bytes, display_bytes).

    **Update the doc comment** to describe the generic behavior: "Scans `data` for one complete `{prefix}{json}BEL` OSC 1337 sequence."

    **Update the import** at the top: add `use crate::pty::commands::ContextData;` alongside the existing `BudgetData` import.
  </action>
  <acceptance_criteria>
    - `extract_voss_osc` takes a `prefix: &[u8]` parameter
    - No hardcoded `const PREFIX` inside the function body
    - `cargo build -p voss-app-core` exits 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Update reader loop to handle both budget and context OSC</name>
  <files>crates/voss-app-core/src/pty/reader.rs</files>
  <read_first>
    - crates/voss-app-core/src/pty/reader.rs (lines 41-82 — the Ok(n) arm with existing budget handling)
    - .planning/phases/F4-visual-context-heatmap/F4-CONTEXT.md (D-23 — separate voss-context= OSC type)
    - .planning/phases/F4-visual-context-heatmap/F4-RESEARCH.md (lines 30-34 — two scans per read recommendation)
  </read_first>
  <action>
    **Define prefix constants** at module level (above `extract_voss_osc`):
    ```rust
    const BUDGET_PREFIX: &[u8] = b"\x1b]1337;voss-budget=";
    const CONTEXT_PREFIX: &[u8] = b"\x1b]1337;voss-context=";
    ```

    **Replace the Ok(n) arm** in `start_reader`. The new logic:
    1. Let `slice = &buf[..n]`.
    2. Try budget first: `extract_voss_osc(slice, BUDGET_PREFIX)`. If `Some((json, display))`:
       - Parse `serde_json::from_slice::<BudgetData>(&json)` — if Ok, send `PtyEvent::BudgetUpdate(data)` (ignore send error with `let _ =`).
       - If `display` is non-empty, send `PtyEvent::Data { bytes: display }` with `is_err() => break`.
       - `continue` to next read (skip context check for this buffer — at most one OSC per read).
    3. Try context: `extract_voss_osc(slice, CONTEXT_PREFIX)`. If `Some((json, display))`:
       - Parse `serde_json::from_slice::<ContextData>(&json)` — if Ok, send `PtyEvent::ContextUpdate(data)` (ignore send error with `let _ =`).
       - If `display` is non-empty, send `PtyEvent::Data { bytes: display }` with `is_err() => break`.
       - `continue`.
    4. Fallback (neither prefix found): send `PtyEvent::Data { bytes: slice.to_vec() }` with `is_err() => break`.

    This two-scan approach matches the Research recommendation. Budget and context OSCs never arrive in the same read (different emission calls), so checking both per-read is correct but at most one matches.
  </action>
  <acceptance_criteria>
    - `BUDGET_PREFIX` and `CONTEXT_PREFIX` are defined as module-level constants
    - The `Ok(n)` arm calls `extract_voss_osc` twice (once per prefix) with early `continue`
    - `PtyEvent::ContextUpdate(data)` is sent when context OSC is parsed
    - `cargo build -p voss-app-core` exits 0 with no warnings
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Update existing tests + add context OSC tests</name>
  <files>crates/voss-app-core/src/pty/tests.rs</files>
  <read_first>
    - crates/voss-app-core/src/pty/tests.rs (lines 155-191 — existing F3 extract_voss_osc tests)
    - crates/voss-app-core/src/pty/reader.rs (new extract_voss_osc signature from Task 2)
    - .planning/phases/F4-visual-context-heatmap/F4-RESEARCH.md (lines 143-158 — test seams T-F4-01..T-F4-04)
  </read_first>
  <action>
    **Update existing 4 F3 tests** to pass the budget prefix to `extract_voss_osc`. Each existing call `extract_voss_osc(&data)` becomes `extract_voss_osc(&data, b"\x1b]1337;voss-budget=")`. The test assertions remain identical.

    **Add 6 new tests** after the existing F3 tests, under a section comment `// -- F4: context OSC unit tests --`:

    1. `test_extract_context_osc_parses_well_formed` — construct `CONTEXT_PREFIX + valid_context_json + BEL`. Valid JSON: `{"system_tokens":500,"conversation_tokens":1200,"total_tokens":3000,"token_limit":200000,"files":[{"path":"src/main.rs","tokens":800,"state":"full","pinned":false}]}`. Assert json_bytes matches and display_bytes is empty.

    2. `test_extract_context_osc_strips_surrounding_bytes` — prepend "output " and append " more" around the context OSC. Assert display_bytes equals `b"output  more"`.

    3. `test_extract_context_osc_returns_none_for_partial` — provide `CONTEXT_PREFIX + truncated_json` with no BEL. Assert None.

    4. `test_extract_context_osc_returns_none_for_budget_prefix` — provide a valid `voss-budget=` sequence, call with the `voss-context=` prefix. Assert None (wrong prefix does not match).

    5. `test_context_data_serde_roundtrip` — construct a `ContextData` struct in Rust, serialize with `serde_json::to_vec`, deserialize back, assert fields match. Requires `use crate::pty::commands::{ContextData, FileContextEntry};`.

    6. `test_extract_budget_osc_ignores_context_prefix` — provide a valid `voss-context=` sequence, call with the `voss-budget=` prefix. Assert None (cross-prefix isolation).
  </action>
  <acceptance_criteria>
    - `cargo test -p voss-app-core osc` shows 10 tests passing (4 existing budget + 6 new context)
    - `cargo test -p voss-app-core pty` shows all existing tests still passing (no regression)
    - Tests cover: well-formed parse, display stripping, partial sequence, cross-prefix isolation, serde roundtrip
    - `cargo build -p voss-app-core` exits 0 with no warnings
  </acceptance_criteria>
</task>

</tasks>

<must_haves>
  truths:
    - "extract_voss_osc accepts a prefix parameter and scans for that specific prefix in the byte buffer"
    - "extract_voss_osc returns None for partial sequences, non-matching prefixes, and unrelated ANSI"
    - "reader.rs Ok(n) arm scans for both BUDGET_PREFIX and CONTEXT_PREFIX, emitting BudgetUpdate or ContextUpdate respectively"
    - "ContextData and FileContextEntry have both Serialize and Deserialize derives"
    - "ContextData serde roundtrip preserves all fields including nested FileContextEntry Vec"
    - "Existing F3 budget OSC tests pass unchanged (except adding the prefix parameter)"
  artifacts:
    - path: "crates/voss-app-core/src/pty/commands.rs"
      provides: "ContextData + FileContextEntry structs + ContextUpdate(ContextData) PtyEvent variant"
      contains: "ContextUpdate"
    - path: "crates/voss-app-core/src/pty/reader.rs"
      provides: "Parameterized extract_voss_osc + BUDGET_PREFIX/CONTEXT_PREFIX constants + dual-scan Ok(n) arm"
      contains: "CONTEXT_PREFIX"
    - path: "crates/voss-app-core/src/pty/tests.rs"
      provides: "10 unit tests (4 budget + 6 context) for extract_voss_osc"
      contains: "test_extract_context_osc"
  key_links:
    - from: "crates/voss-app-core/src/pty/reader.rs"
      to: "crates/voss-app-core/src/pty/commands.rs"
      via: "use crate::pty::commands::{BudgetData, ContextData}"
      pattern: "ContextData"
</must_haves>
