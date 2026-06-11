# Voss TUI Visual Redesign — Spec Plan

**Status:** Draft for review
**Scope:** `voss/harness/tui/` (Python Textual client). The Rust `crates/voss-tui` fallback client and the OpenCode-fork track are out of scope (see Open Questions).
**Supersedes:** M9-02 UI-SPEC color contract and glyph allowlist (revised here as Contract v2 — requires rebaselining the contract audit tests).

---

## 1. Problem statement

The current TUI is structurally sound (region grid, modals, palettes, permissions bridge) but reads as flat and dated next to OpenCode, Claude Code, and Codex CLI. Root causes, in priority order:

1. **`TurnView` is a `RichLog`** — append-only. No widget can be updated after it is written. This single choice blocks every modern transcript behavior: in-place tool status, collapsible output, live markdown, block navigation, working indicators.
2. **Tool calls render as two disconnected lines** (`renderer.py:184-203`): a `pending` line and later an `ok`/`error` line. Transcript fills with pending-noise; no result metrics, no output access.
3. **Stream finalize writes the header *below* the body** (`turn_view.py:151-185`) — an explicit workaround for RichLog's append-only constraint. Reads backwards.
4. **Streaming shows raw text, then re-renders markdown after finalize** — visible reflow "pop" at end of every response.
5. **No working indicator** — no spinner, elapsed time, token tick, or interrupt hint while the agent runs.
6. **No surface layering** — the 5-color contract is foreground-only. No background tints means no visual blocking of user messages, no depth on modals, no selection states.
7. **HeaderBar duplicates StatusLine** (session/model/budget appear in both) — spends a row on redundancy.
8. **Sub-agent side panel costs 40% width** for a rare event, and shares the region with CodeIntelPanel via a pin state machine (`app.py:288-335`) that adds complexity for little visible payoff.

## 2. Design goals

- **Blocks, not log.** Every transcript entry is a discrete, mutable, addressable widget.
- **One line per tool call, mutating in place**, with collapsed-by-default output.
- **Live feedback always**: spinner + elapsed + tokens whenever the agent is working.
- **Depth via surfaces**: 3 background layers, semantic foreground roles preserved.
- **Less chrome, more transcript**: drop the header row; two-zone status line.
- **Keep what works**: `●` assistant gutter, orange brand identity, modal system, palettes, plain/no-unicode fallbacks, keymap contexts.

Non-goals: theming marketplace (single built-in theme; theme files are a follow-on), mouse-first interaction, any harness/server protocol changes beyond tool-call IDs (§6.3).

---

## 3. Architecture: TranscriptView replaces TurnView

### 3.1 Widget tree

```
VossTUIApp
 ├─ TranscriptView(VerticalScroll, id="main")     # replaces TurnView(RichLog)
 │   ├─ HomeScreen                                 # empty-state splash (removed on first turn)
 │   ├─ UserBlock                                  # one per user message
 │   ├─ ToolCard                                   # one per tool call, keyed by call id
 │   │   └─ ToolOutput (collapsed)                 # expandable body: output / mini-diff
 │   ├─ AgentTree                                  # nested ToolCards for sub-agent spawns
 │   ├─ AssistantBlock                             # streaming Markdown widget
 │   ├─ LocalBlock*                                # existing shell/note/notice blocks, as widgets
 │   └─ WorkingIndicator                           # ephemeral, always last child while running
 ├─ SideRegion(id="side")                          # CodeIntelPanel only (see §5.6)
 ├─ StatusLine(id="status")
 └─ InputBar(id="input")                           # HeaderBar deleted
```

### 3.2 TranscriptView contract

```python
class TranscriptView(VerticalScroll):
    # Append API (called by TextualRenderer via _post / call_from_thread)
    def add_user(self, body: str) -> None
    def add_assistant_stream(self) -> AssistantBlock      # returns live handle
    def add_tool_card(self, call_id: str, name: str, args: dict) -> ToolCard
    def get_tool_card(self, call_id: str) -> ToolCard | None
    def add_local_block(self, widget: Widget) -> None
    def show_working(self, label: str = "working") -> None
    def update_working(self, elapsed_s: float, tokens: int) -> None
    def hide_working(self) -> None

    # Scroll policy: auto-follow tail unless the user has scrolled up
    # (preserve the current TurnView behavior; Textual `anchor()` on the
    # last child or manual is-at-bottom check).

    # Block navigation (new, §7.1)
    def focus_block(self, delta: int) -> None      # j/k or up/down in nav mode
    def toggle_focused(self) -> None               # expand/collapse focused ToolCard
```

Rules:

- Auto-scroll only when pinned to bottom; user scroll-up disengages, `G`/new user message re-engages.
- `WorkingIndicator` is always re-mounted as the last child after any append while a turn is active.
- `HomeScreen` is removed (not cleared) on first `add_*` call.
- Trim policy: above 500 blocks, oldest blocks are flattened into a single static "≈ N earlier turns · /resume to reload" placeholder to bound widget count (RichLog had `max_lines`; a widget transcript needs an equivalent).

### 3.3 Streaming pipeline

`AssistantBlock` wraps a Textual `Markdown` widget plus the `●` accent gutter (grid layout: 1-cell gutter column + body column, same as today's `_write_assistant`).

- `stream_delta(text)` → accumulate into a buffer; throttle re-render to ≤ 10 Hz (`set_timer` coalescing) and call `Markdown.update(buffer)`. Live markdown from the first token; no finalize reflow.
- `finalize(role, cost, confidence, timestamp)` → final `Markdown.update`, then write the metadata footer **below the block in dim style** — but now by choice, as a footer, not as a misplaced header: `· 2.4s · $0.0041 · conf 0.92` (only fields that are present). Cost/confidence stay out of the body per the existing chat-layout decision.
- Interrupt (`ctrl+c` mid-turn) → block keeps streamed content, footer reads `· interrupted`.

If profiling shows `Markdown.update` re-parse cost is too high for long responses (>50 KB), fall back to: stream into a plain `Static` and swap to `Markdown` on finalize — visually identical to today's behavior but contained in one block. Decide by measurement in R2, not up front.

### 3.4 ToolCard states

One widget per call, keyed by `call_id`. Layout: status glyph + name + arg summary, result metric right-aligned.

```
running:   ⠹ edit voss/provider.py                          1.2s
ok:        ⏺ edit voss/provider.py                       +12 -48
           ⎿ ▸ 3 hunks · ctrl+d full diff
error:     ⏺ shell pytest tests/harness -x                exit 1
           ⎿ ▾ FAILED tests/harness/test_loop.py::test_clamp …
              (output auto-expanded on error, first 10 lines)
```

- **running** → braille spinner frames (§6.2), dim text, live elapsed right-aligned.
- **ok** → `⏺` in `$good`; right metric per tool class: `read → N lines`, `edit/write → +a -d`, `shell → exit 0 · 1.2s`, `grep/glob → N matches`, default → duration.
- **error** → `⏺` in `$error`; output body auto-expands (first 10 lines, `⎿ ▾ …` to collapse).
- Output body (`ToolOutput`) collapsed by default for `ok`. Expand: click, or focus + `enter` in nav mode, or global `ctrl+o` (§7.2). Body content: tool output tail (last 20 lines, dim), or mini-diff for edit tools — up to 3 hunks rendered with `$good`/`$error` foreground on 8% background tints; `ctrl+d` still opens the existing full `DiffModal`.
- Args summary reuses `_short()` truncation from `renderer.py`; full args visible in expanded body.

### 3.5 Sub-agents: inline AgentTree, side panel retired

`show_subagent_start/end` no longer mount `SubAgentPanel` into `#side`. Instead:

```
⏺ spawn researcher                                   12.4k/32k tok
  ├─ ⠹ read docs/sdk.md                                       …
  ├─ ⏺ grep "max_turns" · 7 matches
  └─ ⏺ gathered · 3 results
```

- Spawn renders as a parent `ToolCard`; child tool events (today's `update_subagent` body lines) render as nested cards indented under it using the locked `NEST_MID`/`NEST_LAST` glyphs.
- Parent right-metric = live budget `used/total` (replaces `BudgetMeter`-in-panel).
- `ctrl+o` (existing `action_toggle_subagent_detail`) generalizes to the global expand/collapse-all action (§7.2) — child cards are hidden by default beyond the most recent one (quiet-by-default D-09 preserved: collapsed parent shows just the spawn line + live counter).
- `SubAgentPanel`, `mount_subagent_panel`, `collapse_subagent`, `show_subagent_panel`, `pin_side_panel`, `unpin_side_panel`, and the `_side_owner`/`_side_pinned` state machine are deleted. `#side` keeps exactly one occupant: `CodeIntelPanel` (§5.6).

### 3.6 WorkingIndicator

Ephemeral last-child widget, mounted on turn dispatch, removed on finalize/interrupt:

```
✦ working · 8s · 2.1k tok · esc to interrupt
```

- Glyph animates through a 4-frame cycle (§6.2) at 2 Hz via `set_interval`.
- Elapsed updates every second; token count updates on each delta event (renderer already receives deltas; thread the running count).
- Label varies by phase if the event stream distinguishes it: `working` (default), `tool: <name>` while a call is pending, `compacting` during fold. Keep the variant set fixed and boring — no randomized verbs.
- Plain renderer parity: plain mode prints a single `working...` line on turn start (no animation), nothing else.

---

## 4. Contract v2: colors and glyphs

### 4.1 Color contract v2 (revises M9-02 locked contract)

The 5 foreground roles are kept verbatim. Three background surfaces and two text levels are added. **Exactly 10 hex values** in `styles.tcss`; the audit test updates from "exactly 5" to "exactly 10".

| Role | Var | Value | Use |
|---|---|---|---|
| Accent | `$accent` | `#ff5b1f` | unchanged allow-list (6 sites) + UserBlock border/tint |
| Secondary | `$dim` | `#888888` | unchanged |
| Signal-good | `$good` | `#5FD75F` | unchanged + ToolCard ok glyph, diff adds |
| Signal-warn | `$warn` | `#FFD75F` | unchanged |
| Signal-error | `$error` | `#FF5F5F` | unchanged + ToolCard error glyph, diff dels |
| Background | `$bg` | `#121212` | app background (explicit, was terminal default) |
| Surface | `$surface` | `#1c1c1c` | UserBlock bg, ToolOutput bg, input bar bg |
| Raised | `$raised` | `#262626` | modals, palettes, toast |
| Text | `$text` | `#dadada` | primary body text (replaces ad-hoc `white`/`#cccccc`) |
| Text-dim → alias | — | — | `$dim` doubles as dim text; no sixth gray |

Tint rule unchanged: translucent uses of palette vars (`$accent 8%`, `$good 8%`) do not count as new hex. The two hard-coded `#cccccc` literals in `status_line.py` and `IGNITE_ORANGE` in `turn_view.py` migrate to vars/classes — after this change **no hex literal exists outside `styles.tcss`** (new audit assertion).

Terminals without truecolor: Textual auto-downgrades; `$bg/$surface/$raised` collapse acceptably on 256-color. `--no-color` / plain renderer path unchanged.

### 4.2 Glyph allowlist v2

Existing 12 entries unchanged. Additions:

| Name | Glyph | Codepoints | ASCII fallback | Use |
|---|---|---|---|---|
| `TOOL_OK` | `⏺` | U+23FA | `*` | settled tool card |
| `OUTPUT_ELBOW` | `⎿` | U+23BF | `\|_` | tool output lead-in |
| `CHEVRON_CLOSED` | `▸` | U+25B8 | `>` | collapsed expander |
| `CHEVRON_OPEN` | `▾` | U+25BE | `v` | expanded expander |
| `SPINNER_FRAMES` | `⠋⠙⠹⠸⠼⠴⠦⠧` | U+2800-block | `\|/-\` (4-frame) | running spinner |
| `WORKING` | `✦` | U+2726 | `*` | working indicator brand glyph |

`TOOL_CALL ⏵` is retained for the plain renderer's one-line tool format (parity tests) but the TUI ToolCard uses spinner→`TOOL_OK`. `glyphs.py` allowlist, `NO_UNICODE_FALLBACK`, and `test_no_unicode_fallback` extend accordingly. `SPINNER_FRAMES` is a string constant (iterated by index), not a single glyph — fallback table maps it to the 4-char ASCII cycle.

No emoji rule stands.

---

## 5. Chrome redesign

### 5.1 HeaderBar: deleted

Remove `HeaderBar`, its compose entry, `update_header` call sites, and `header.py`. Session id moves to HomeScreen (§5.4) and `/status` output (status slash command if absent, else toast). Budget moves to StatusLine right zone. One more transcript row.

### 5.2 StatusLine: two zones

Replace the single pipe-joined string with a two-column grid (left grows, right is content-width, middle truncates first):

```
▌ voss · anthropic/claude-fable-5 · plan        ▰▰▱▱ 34% · $0.42 · dev*
```

- Left: brand glyph + `voss` (accent, allow-listed site), provider/model, mode.
- Right: context bar (4-cell `BUDGET_FILL/EMPTY` + percent; turns `$warn` ≥ 75%, `$error` at 100% — same thresholds as the locked color contract rows), session cost, git branch+dirty marker.
- Toast no longer lives here (§5.3). `set_status` API keeps its signature; `toast=` kwarg delegates to the toast overlay during a deprecation window, then is removed along with `set_persistent_toast` call sites.

### 5.3 Toast overlay

New 1-line `Toast` widget, layer `overlay`, top-right, `$raised` background, auto-dismiss 1.5 s (persistent variant kept for the permissions bridge). Replaces the status-line toast field so session metadata never jumps. `app._toast()` retargets here — call sites unchanged.

### 5.4 HomeScreen (empty state)

Replaces the `on_mount` splash writes in `TurnView`:

```
            __      ______  _____ _____
            \ \    / / __ \/ ____/ ____|        ← existing logo, accent
             ...                                   (≥70 cols; "VOSS" below)
                         v1

      cwd      ~/Projects/Voss  (dev*)
      model    anthropic / claude-fable-5
      resume   ⎇ a3f9c2 "harness refactor" · 2h ago    (most recent session, if any)

      ❯ type to begin · / commands · @ files · ctrl+k models
```

- Data: cwd/git from existing app fields; resume line from `EpisodicMemory`/session store (newest non-current session: short id, first-user-message truncated to 40 chars, relative age). Omit the row when no prior session exists.
- `enter` on empty input with a resume row present does nothing special in v1 (resume stays `/resume`); the row is informational. (Interactive session picker = follow-on.)
- Removed on first transcript append.

### 5.5 InputBar framing

Keep the existing `TextArea` machinery (reverse search, paste, palettes) untouched. Visual changes only:

- Rounded border, color by state: `$dim` idle → `$accent` focused → `$warn` when mode ∈ {plan, restricted} — border-title shows the mode name (`╭─ plan ─…`).
- Background `$surface`.
- Placeholder when empty: static `/ commands · @ files · ctrl+r history` (no cycling animation — cheap to add later, distracting by default).
- Paste detection: a paste of > 5 lines collapses to a `[pasted N lines]` chip token in the buffer (expanded on submit; `backspace` on the chip deletes it whole). This is the only InputBar behavior change; it can be cut from scope independently.

### 5.6 SideRegion: CodeIntelPanel only

With sub-agents inline (§3.5), `#side` has one occupant. The pin/share state machine is deleted; `show_code_intel_panel`/`restore_code_intel_panel` collapse to a simple show/hide toggle. Width stays 40%/28-50 bounds; hidden by default as today.

---

## 6. Renderer and event plumbing

### 6.1 TextualRenderer protocol changes

The `Renderer` protocol (consumed by plain + textual implementations) changes minimally:

| Method | Change |
|---|---|
| `show_tool_call(name, args, summary, state)` | → `show_tool_call(call_id, name, args, summary, state)` — same method now *updates* the existing card when `call_id` is known |
| `stream_delta(text)` | unchanged signature; routes to active `AssistantBlock` |
| `finalize_stream(...)` | unchanged signature; metadata becomes block footer |
| `append_turn` / `append_markdown_turn` | kept for non-stream paths (resume replay, errors); route to block factories |
| new: `show_working(label)` / `update_working(elapsed, tokens)` / `hide_working()` | no-ops in plain renderer except a single `working...` line on start |
| `show_subagent_start/end`, `update_subagent` | retarget from SubAgentPanel to AgentTree child cards; signatures unchanged |

Plain renderer keeps today's line formats (parity tests `test_plain_parity` stay green modulo the `call_id` arg).

### 6.2 Tool-call identity

In-place mutation needs a stable id per call. Requirement on the harness event stream: tool events carry `call_id` (provider tool-use id or harness-generated). Fallback when absent: key = `f"{name}:{stable_hash(args)}:{seq}"` matching pending→settled by FIFO per name. The fallback must be implemented (codex/older provider paths may lack ids), but `call_id` threading is the correct fix — verify which providers already emit it during R1 discovery and list gaps in the R1 deliverable.

### 6.3 Threading model

Unchanged: renderer methods are called from worker threads and marshal via `_post`/`call_from_thread`. New constraint: `update_working` fires per-delta — coalesce in the renderer (≤ 4 Hz for the token counter) before posting, so the UI thread isn't flooded.

---

## 7. Interaction additions

### 7.1 Transcript nav mode

- `esc` (when input has focus and no modal/palette open, and no turn is running — running-turn `esc` stays interrupt): focus moves to TranscriptView.
- `j/k` or `↓/↑`: move block focus (focused block gets `$accent 8%` background).
- `enter`: expand/collapse focused ToolCard.
- `y`: copy focused block body to clipboard (reuses `copy_to_clipboard`; replaces nothing — `ctrl+y` last-code-block copy stays).
- `g g` / `G`: top / bottom (G re-engages auto-follow).
- `i` or any printable: return focus to input.
- Keymap entries added to `keymap.py` with context `"transcript"`; `test_keymap_baseline` rebaselines.

### 7.2 Global expand/collapse

`ctrl+o` (existing binding, generalized): toggles all ToolOutput bodies + AgentTree children between collapsed and expanded. Replaces `action_toggle_subagent_detail` (same key, superset behavior).

### 7.3 Queued input

Typing + `enter` while a turn is running: message is queued (not dispatched), a chip renders above the input (`▌ queued: "fix the test too"`, dim, accent bar). On turn finalize, queued messages dispatch FIFO. `ctrl+c` clears the queue before it interrupts. Plain renderer: unsupported (submit blocked as today).

---

## 8. Delivery plan

Phases are sequential; each leaves the suite green and the TUI shippable. No GSD machinery — each phase is a normal branch/PR with the listed acceptance checks.

### R1 — Block transcript core (the unlock)

Replace `TurnView(RichLog)` with `TranscriptView(VerticalScroll)` + `UserBlock` + `AssistantBlock` (non-streaming first: `append_turn`/`append_markdown_turn` paths), `LocalBlock*` mounted as widgets instead of `tv.write(block.render())`. HomeScreen as a widget. Auto-follow scroll policy. Renderer routes through block factories. Discovery task: audit `call_id` availability per provider event stream (input to R3).

*Acceptance:* all existing transcript content renders block-per-entry; scroll-follow behavior matches today (manual: scroll up during long replay → no jump; `G` re-engages); `test_app_shell`, `test_full_flow_pilot` adapted; snapshot tests rebaselined once.
*Test impact (expected, per stale-sentinel policy — update sentinels deliberately, not reactively):* `test_turn_view_streaming`, `__snapshots__`, `test_app_shell`.

### R2 — Live streaming + working indicator

`AssistantBlock` streaming via throttled `Markdown.update` (measure re-parse cost; fall back to Static-then-swap if p95 frame > 50 ms on a 20 KB response). Footer-style finalize metadata. WorkingIndicator with spinner/elapsed/tokens/interrupt-hint. Glyph allowlist v2 additions (spinner, `WORKING`).

*Acceptance:* markdown visible during stream (manual: code fence renders highlighted before finalize); no trailing reflow pop; indicator appears ≤ 100 ms after dispatch, disappears on finalize and on interrupt; `--no-unicode` run shows ASCII spinner; plain renderer prints one `working...` line.

### R3 — ToolCards

In-place tool cards with running/ok/error states, right-aligned metrics, collapsed output, error auto-expand, inline mini-diff for edit tools, `call_id` threading + FIFO fallback. `show_tool_call` signature change across plain/textual renderers.

*Acceptance:* a tool call occupies exactly one card pending→settled (no duplicate lines); error output auto-expands; `ctrl+d` on an edit card opens DiffModal; `test_plain_parity` green with new signature; `test_live_visualization` adapted.

### R4 — Sub-agents inline; side panel reduced

AgentTree nested cards; delete SubAgentPanel + pin state machine; `ctrl+o` generalized; CodeIntelPanel sole side occupant; live budget on the spawn card.

*Acceptance:* spawn → nested tree with live child updates and budget counter; quiet-by-default (collapsed shows spawn line + counter only); `test_subagent_reveal`, `test_code_intel_region_share` rewritten to the simplified model; `BudgetMeter` widget deleted or repurposed for the spawn card.

### R5 — Contract v2 + chrome

Color contract v2 in `styles.tcss` (10 hex), hex-literal purge from `.py` files, UserBlock surface styling, HeaderBar deletion, two-zone StatusLine with context bar, Toast overlay, InputBar border states + placeholder.

*Acceptance:* `test_glyph_and_color_contract` + `test_accent_allowlist_audit` rebaselined to v2 rules (10 hex in tcss, 0 hex in py, accent allow-list re-verified — UserBlock border becomes the 7th allow-listed accent site or reuses tint-only); header gone, no information lost (budget visible in status right zone); toast no longer shifts status content.

### R6 — Home screen + nav mode + queue

HomeScreen data rows (cwd/model/resume), transcript nav mode (`esc`/`j`/`k`/`enter`/`y`/`G`), queued input chips, paste chip.

*Acceptance:* fresh launch shows resume row when a prior session exists and omits it otherwise; nav mode reachable only when idle; queue dispatches FIFO after finalize and clears on interrupt; `test_keymap_baseline` rebaselined.

### R7 — Polish + audit sweep

Trim policy (500-block flatten), 256-color/`--no-unicode`/plain parity passes, performance pass (long session: 200 blocks, 100 KB response — scroll stays < 16 ms/frame), windows console strategy re-check (`test_windows_console_strategy`), docs + UI-SPEC artifact update so the contract tests and the spec document agree.

*Acceptance:* full suite green via `.venv/bin/python -m pytest tests/harness/tui`; manual checklist (stream, interrupt, spawn, diff, resume, no-unicode, plain) recorded in PR description.

Rough sizing: R1 and R3 are the heavy phases (renderer rewiring + test rebaselines); R2/R5 medium; R4/R6/R7 small-medium.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| `Markdown.update` re-parse cost on long streams | Throttle to 10 Hz; measured fallback to Static-then-swap (decided in R2, not assumed) |
| Widget-count growth on long sessions (RichLog was O(1) widgets) | Trim policy §3.2; verify in R7 perf pass |
| `call_id` absent on some provider paths | FIFO fallback specified §6.2; discovery in R1 |
| Contract tests are tripwires by design — broad rebaselines risk hiding real regressions | Rebaseline each contract test exactly once, in its named phase, with the new rule stated in the test docstring |
| Auto-commit process bundling mid-redesign edits | Per repo convention: verify via `git log`, keep phases small and branch-isolated |
| OpenCode-fork track makes this work throwaway | Decision gate below — resolve before R1 |

## 10. Open questions (resolve before R1)

1. **Plan of record vs OpenCode fork.** The H-track fork of OpenCode's TUI exists as a competing direction. If the fork ships, this spec becomes its design contract and the Python phases stop after R3 (blocks + tool cards + working indicator are still worth having in the interim client). Decide explicitly.
2. **Accent allow-list site count.** UserBlock border in accent = a 7th site (contract change) vs tint-only (`$accent 6%` background, no new site). Default: tint-only, keep the list at 6.
3. **Resume row interactivity** (enter-to-resume vs informational). Default: informational in v1.
4. **Theme files** (gruvbox/catppuccin via tcss variable swap). Out of scope here; trivially enabled by Contract v2 centralization. Park as follow-on.

---

## As-built deltas (R1-R7)

Where the shipped implementation deliberately diverges from the spec body above. The contract tests pin the as-built rules; this list is the reconciliation (R7, §8).

- **9 hex, not 10** (§4.1): the spec header says "exactly 10 hex values" but its own table lists 9 distinct values — `$dim` doubles as dim text ("no sixth gray"). `test_styles_tcss_has_only_locked_palette` pins exactly 9. `palette.py` is the single audited Python-side mirror (Rich `Text` styles cannot read tcss vars); `test_palette_matches_tcss` cross-checks it against `styles.tcss`.
- **Interrupt hint is `ctrl+c to interrupt`, not `esc`** (§3.6): `esc` was never bound to interrupt (it enters transcript nav mode when idle); `ctrl+c` is the real interrupt binding and the WorkingIndicator hint says so.
- **FIFO fallback replaced by settled-first cards** (§6.2): read batches run via `asyncio.gather`, making pending→settled FIFO matching per name unsafe. Instead, `call_id` is minted by the harness in `agent.py::_invoke_step_with_gate` (`uuid4().hex[:12]`) for every call, and a settle event with an unknown/absent `call_id` creates a settled-first card rather than matching by FIFO.
- **`show_tool_call` gained an `output=` kwarg** (§6.1): the settled card needs the tool output body (tail/error excerpt, read/grep metrics); signature is `show_tool_call(call_id, name, args, summary, state, *, output=None)`. Plain/json/eventbus renderers accept and ignore the new args; the server event contract is untouched.
- **Toast also carries the session-id launch announce** (§5.1/§5.3): with HeaderBar deleted, the session id surfaces once at launch as a `session <id8>` toast (plus `/status`), not as a HomeScreen row.
- **Sub-agent child rows are internal lines, not nested widgets** (§3.5): `AgentTreeCard` renders child progress rows as lines inside one card (`NEST_MID`/`NEST_LAST` indents), not as nested `ToolCard` children. Quiet-by-default and the live `used/total` budget metric are preserved.
- **Paste chip shipped** (§5.5): >5-line pastes collapse to a `[pasted N lines]` chip, expanded on submit, whole-chip backspace.
- **`compacting` working-label skipped** (§3.6): the fold/compaction path emits no renderer-visible event, so the label variant set is `working` / `tool: <name>` only.
- **Textual `Markdown.update` rejected by R2 measurement** (§3.3): ~1.4–1.8 s per update at 20 KB (widget re-measure dominates) vs ~40 ms for re-rendering Rich `Markdown` inside a `Static` — so `AssistantBlock` streams by re-rendering Rich Markdown in place, throttled ≤10 Hz. The spec's Static-then-swap fallback was unnecessary; live markdown ships from the first token.
- **HomeScreen hint copy** (§5.4): reads `type a message below to begin · / for commands`; the `❯` lead-in, `@ files` and `ctrl+k models` fragments were dropped (`ctrl+k` is unbound — the model picker is `/models`).
- **Trim policy as-built** (§3.2, R7): trips above 500 mounted blocks, keeps the newest 400, flattens the rest into a single static first-child placeholder `≈ N earlier turns · /resume to reload` (dim); N counts flattened blocks and accumulates across trims. Trimmed `call_id`/`parent_id` entries are dropped from the ToolCard/AgentTree registries (late settles become no-ops). New glyph `APPROX ≈` (fallback `~`) joined the allow-list for the placeholder — the only R7 contract change.
- **Glyph contract scope** (§4.2): typographic punctuation in copy (`·`, `…`, `—`, `→`, `×`, `│`) is not part of the glyph allow-list and does not downgrade under `--no-unicode`; this matches pre-redesign behavior (modals, status line). R7 migrated the remaining *glyph* literals in `renderer.py` (`⏵` thinking toast, `⚠` warnings) to `glyphs.TOOL_CALL`/`glyphs.WARN` so they downgrade. Known leftover: `app.py::append_tool_line` prefixes `✓`/`✗` on the recorder-bridge path — predates Contract v2, not allow-listed, renders raw under `--no-unicode`.
- **StatusLine right zone** (§5.2): context bar is `▰▱`-style 4-cell + percent with the locked $warn/$error thresholds, plus session cost and git branch — as specced; the `set_status(toast=)` deprecation window is still open (delegates to the Toast overlay).
