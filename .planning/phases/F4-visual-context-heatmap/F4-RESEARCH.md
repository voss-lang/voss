# Phase F4: Visual Context Heatmap - Research

**Confidence:** HIGH
**Date:** 2026-05-22
**Researcher:** inline (local GSD agents not installed)

## Riskiest Unknown: Harness per-file context state

The harness (`agent.py`) builds LLM messages from tool results. Files enter context as `fs_read` tool results. `RunRecorder` tracks `inspected[]`/`changed[]` as flat path lists — **no per-file token counts, no compression state, no "in-context" tracking.** `ContextScope` (`voss_runtime/context.py`) is for the `.voss` language runtime, not the harness agent loop.

**Resolution:** Build a new `ContextTracker` inside `RunRecorder` that accumulates per-file state at `observe()` time. When `fs_read` returns, count tokens (via `len(result) // 4` heuristic or provider `count_tokens`), record as `full`. Emit the tracker state at `end_iteration()`.

Files don't get `compressed` in the harness — the LLM API handles context windows. For F4 MVP, states are:
- `full` — file was read and result is in message history
- `dropped` — file was read, but message history was truncated (detectable when prompt_tokens decreases between iterations)
- `compressed` — deferred (requires harness-level summarization, which is a future feature)

**Pinned state** lives in the `ContextTracker` as a `Set[str]`. Pin commands from stdin inject into this set. Pinned files get priority in any future context compression.

## Existing Infrastructure (what we reuse)

### Rust OSC Parsing (`reader.rs`)

**Pattern:** `extract_voss_osc()` at `reader.rs:19-29`.
- Scans for `PREFIX` byte prefix (`\x1b]1337;voss-budget=`)
- Finds BEL terminator (`0x07`)
- Returns `(json_bytes, display_bytes)` — strips OSC from terminal output
- Single-OSC-per-read: returns first match, rest passes through

**F4 extension:** Generalize to handle multiple OSC prefixes. Current function is hardcoded to `voss-budget=`. Two approaches:
1. **Parameterized prefix** — `extract_voss_osc(data, prefix)`. Called twice per read: once for budget, once for context.
2. **Multi-prefix scan** — Single pass extracting all `voss-*=` sequences. More efficient but more complex.

**Recommendation:** Approach 1 (parameterized prefix). Two scans per read is negligible at OSC cadence (~1/iteration). Simpler, matches existing pattern.

### PtyEvent Enum (`commands.rs:28-34`)

```rust
pub enum PtyEvent {
    Data { bytes: Vec<u8> },
    Exit { code: i32 },
    FgProcess { name: String },
    TitleChange { title: String },
    BudgetUpdate(BudgetData),
    // F4 adds: ContextUpdate(ContextData),
}
```

Tagged with `#[serde(tag = "type", rename_all = "snake_case")]`. F4 adds `ContextUpdate(ContextData)` — automatically serializes as `{ type: "context_update", ... }`.

### Frontend Signal Pattern (`pty-ipc.ts`)

`PtyTransport` at `pty-ipc.ts` receives events via Tauri Channel. `BudgetState` type + `onBudgetUpdate` callback established by F3. F4 mirrors: `ContextData` type + `onContextUpdate` callback. PaneComponent stores via `createSignal<ContextData | undefined>()`.

### Budget Emission (`recorder.py:22-46`)

`_emit_budget_osc()` is a module-level function called from `end_iteration()` call site in `agent.py`. F4 adds `_emit_context_osc()` with same pattern — module-level, called right after budget.

**Current `end_iteration` signature** (`recorder.py:178-216`):
```python
def end_iteration(self, *, plan, tool_results, cost_usd,
                  prompt_tokens, completion_tokens,
                  cache_creation_input_tokens=0,
                  cache_read_input_tokens=0,
                  exit_reason=None) -> None
```

F4 does NOT modify this signature. Context emission reads from `self._context_tracker` (new field) populated during `observe()`.

## New Components

### 1. ContextTracker (Python, in recorder.py)

```python
@dataclass
class FileContextState:
    path: str
    tokens: int
    state: str  # "full" | "dropped"
    pinned: bool = False

class ContextTracker:
    files: dict[str, FileContextState]
    pinned: set[str]
    prev_prompt_tokens: int
```

Populated at:
- `observe()` — when `fs_read` result arrives, estimate tokens, add as `full`
- `end_iteration()` — if `prompt_tokens < prev_prompt_tokens`, mark oldest non-pinned files as `dropped`
- Pin command — adds/removes from `pinned` set, applied at next emission

### 2. ContextData / FileContextEntry (Rust, in commands.rs)

```rust
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct FileContextEntry {
    pub path: String,
    pub tokens: u64,
    pub state: String,  // "full" | "compressed" | "dropped"
    pub pinned: bool,
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct ContextData {
    pub system_tokens: u64,
    pub conversation_tokens: u64,
    pub total_tokens: u64,
    pub token_limit: Option<u64>,
    pub files: Vec<FileContextEntry>,
}
```

### 3. ContextPanel (Solid.js, new component)

Side panel overlay. Reads focused pane's context signal. Renders:
- Summary bar (total tokens / limit + progress bar)
- System prompt + conversation special rows
- Per-file rows sorted by token count desc
- Pin toggle buttons

Mount in App.tsx as absolute-positioned sibling to grid container.

### 4. Stdin Pin Parser (Python, in agent.py)

Harness stdin is already read by the PTY process. Pin commands (`ESC]1337;voss-pin={json}BEL`) are NOT read by the harness directly — they arrive as bytes in the terminal's stdin, which the harness shell (bash/zsh) receives.

**Critical finding:** The harness doesn't read raw stdin — it reads via `input()` or the REPL loop. OSC sequences in stdin would be echoed as garbage by the shell.

**Revised approach for pin commands:**
1. **File-based reverse channel.** ADE writes `.voss/context-pins.json`. Harness reads at iteration start. Simple, decoupled.
2. **Tauri command → IPC.** ADE calls a Tauri command that writes to a file/pipe the harness reads.
3. **Harness poll file.** At `_run_turn_exec()` start, check for `.voss/context-pins.json`.

**Recommendation:** Approach 1 (file-based). Despite D-19 specifying "PTY stdin injection", research reveals stdin injection won't work because the harness reads stdin through the shell, not raw. The file-based approach is simpler and more reliable. The OSC sequence won't reach the harness Python process.

**Note:** This is a RESEARCH correction to D-19. The planner should note this deviation and the CONTEXT.md decision should be updated.

## Validation Architecture

### Test Seams

| Test | Type | What it validates |
|------|------|-------------------|
| T-F4-01 | Rust unit | `extract_voss_osc` with `voss-context=` prefix parses well-formed JSON |
| T-F4-02 | Rust unit | `extract_voss_osc` strips context OSC from display bytes |
| T-F4-03 | Rust unit | `ContextData` serde round-trip (serialize + deserialize) |
| T-F4-04 | Rust unit | Reader loop routes `PtyEvent::ContextUpdate` through channel |
| T-F4-05 | Python unit | `ContextTracker` adds file on `observe()` with token estimate |
| T-F4-06 | Python unit | `ContextTracker` marks files dropped when prompt_tokens decreases |
| T-F4-07 | Python unit | `_emit_context_osc()` produces well-formed OSC 1337 sequence |
| T-F4-08 | Python unit | Pin file read/write round-trip (`.voss/context-pins.json`) |
| T-F4-09 | Vitest | ContextPanel renders file list from mock ContextData signal |
| T-F4-10 | Vitest | ContextPanel shows empty state when no context / shell pane |
| T-F4-11 | Vitest | Pin click sends Tauri command + toggles UI optimistically |
| T-F4-12 | Vitest | Panel slide animation 150ms + prefers-reduced-motion |
| T-F4-13 | tsc | Zero type errors after ContextData type additions |
| T-F4-14 | Cargo test | Zero failures after ContextData + ContextUpdate additions |

### Security Domain (STRIDE)

| Threat | Category | Mitigation |
|--------|----------|------------|
| Malformed OSC JSON crashes reader | Tampering | `serde_json::from_slice` returns `Err` → silently dropped (existing pattern) |
| Oversized context payload DoS | DoS | Cap file list at 200 entries in emission (truncate oldest) |
| Pin command injection via terminal | Elevation | File-based pin channel — no stdin injection, no OSC in stdin |
| File paths in OSC expose directory structure | Info Disclosure | Context data stays local (Tauri Channel, no network) |
| Pin file race (ADE writes while harness reads) | Race | Atomic write (write-then-rename) for `.voss/context-pins.json` |
| Crafted pin path traversal | Tampering | Pin only validates against existing `files_in_context` keys (D-22) |

## Open Questions (RESOLVED)

### OQ-1: Can we inject OSC into PTY stdin for pin commands?

**RESOLVED: No.** The harness Python process reads stdin through the shell (`input()` / readline), not raw bytes. OSC sequences injected via `pty_write` go to the PTY master → shell → displayed as garbage. The shell doesn't parse OSC from stdin.

**Decision:** Use file-based pin channel (`.voss/context-pins.json`). This deviates from D-19 in CONTEXT.md. Planner must note this.

### OQ-2: How to estimate per-file token counts?

**RESOLVED:** Use `len(result) // 4` heuristic (1 token ≈ 4 chars). This is the standard approximation used by Claude/GPT tokenizers. Exact counting via provider `count_tokens()` is available but adds latency per `fs_read`. Heuristic is sufficient for a visualization — exact counts not needed.

### OQ-3: How to detect "dropped" files?

**RESOLVED:** Compare `prompt_tokens` between iterations. If it decreases (or increases less than expected), oldest non-pinned files are marked `dropped`. This is a heuristic — the actual context window management happens at the LLM API level. Good enough for visualization.

### OQ-4: Settings persistence — does A9 exist yet?

**RESOLVED:** A9 is "Plans ready to execute" but NOT executed. No `settings.json` infrastructure exists yet. F4 must implement its own minimal settings read/write for `contextPanel.open` boolean. Use the pattern from A1's `get_theme_overrides` (reads `~/.config/voss-app/` JSON file). F4's settings logic is forward-compatible with A9.

### OQ-5: Status bar — does A10 exist yet?

**RESOLVED:** A10 is "Plans ready to execute" but has code on dev branch (recent commits show StatusBar implementation). Check if StatusBar.tsx exists. If yes, add toggle button. If no, add ⌘I keybind in App.tsx only — status bar button deferred to A10 execution.

---

*Phase: F4-visual-context-heatmap*
*Research completed: 2026-05-22*
