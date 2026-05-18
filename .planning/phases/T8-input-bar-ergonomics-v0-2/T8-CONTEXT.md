# Phase T8: Input Bar Ergonomics (v0.2) - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the harness TUI input bar stop being the slowest part of the loop. Five behaviors on the existing Textual TUI input bar:

- **INPUT-01** Multi-line input — `Shift+Enter` newline, `Enter` submits.
- **INPUT-02** `!<cmd>` prefix runs an allowlisted shell command without spawning a turn (Claude Code `!`-mode parity).
- **INPUT-03** `#<text>` prefix appends a memory note to `VOSS.md` without spawning a turn (Claude Code `#`-mode parity).
- **INPUT-04** `Ctrl-R` reverse-search through episodic input history.
- **INPUT-05** Paste-image detection — if the clipboard has an image and the model supports vision, attach it as a vision input.

**In scope:** modifying `voss/harness/tui/widgets/input_bar.py`; adding `ctrl+r` (and any other needed) bindings to the M9 `tui/keymap.py` in the `input` region; submit-time `!`/`#` value-prefix dispatch; Ctrl-R over the per-project episodic store; OS-clipboard image probe; Textual snapshot tests + recorder-event assertions for all five.

**Out of scope (LOCKED — do not reopen):**
- Rewriting/redesigning the M9 keymap table — `tui/keymap.py` is the source of truth; T8 **only adds bindings** (cross-cutting constraint).
- Changing the `enter→submit` / `shift+enter→newline` semantics — locked by `keymap.py:23-24`.
- Changing recorder-event names or the run_turn-bypass contract — `!`→`shell.local`, `#`→`memory.note`, both bypass `run_turn` (locked by success criteria).
- A separate `!cmd` security/allowlist layer parallel to the central permission gate (rejected — see D-03).
- Global cross-project history; non-task bar lines in Ctrl-R corpus (rejected — see D-07).

</domain>

<decisions>
## Implementation Decisions

### INPUT-01 — Multi-line widget
- **D-01:** Swap `InputBar` from Textual single-line `Input` to **Textual `TextArea`**. Re-wire the three M9 contracts built around `Input`: the `/`-slash-palette `_on_key` empty-check (open palette only when value empty, else literal `/`), the `Submitted` message contract, and the prompt-glyph render. `Enter`=submit / `Shift+Enter`=newline are M9-locked (`keymap.py:23-24`); implement properly by inverting TextArea's default `Enter`=newline.
- **D-02:** Autogrow: 1 row base, grows with content up to a **5-row cap**; content beyond 5 rows **scrolls inside** the TextArea with the cursor kept visible. Stable turn-view real estate; matches UI-SPEC "grows up to 5 rows".

### INPUT-02 / INPUT-03 — Prefix dispatch
- **D-03:** `!<cmd>` executes through the **existing gated shell-exec path** that normal turns use — inheriting the T5-D12 deny-set and permission-mode behavior (plan-mode refuses cleanly with no escalation; edit/auto prompt under normal approval). No parallel allowlist or second security surface; the "allowlist" is the existing gate's policy. Bypasses `run_turn`, emits `shell.local`.
- **D-04:** `!cmd` output renders as an **ephemeral local block in the turn-view scrollback** — distinct `!` prefix/styling, shows command + stdout/stderr + exit code. Persists in episodic scrollback, snapshot-testable, **not** added to model/conversation history.
- **D-05:** `#<text>` appends `- [<ISO-timestamp>] <text>` as a bullet under a dedicated **`## Notes`** heading in `VOSS.md` (heading created if absent), via the section-aware `voss_md` / `memory_cli` append path. Rest of `VOSS.md` untouched. Bypasses `run_turn`, emits `memory.note`.

### INPUT-04 — Ctrl-R reverse-search
- **D-06:** **Inline readline-style incremental** search (bash/zsh/Claude Code parity). `Ctrl-R` turns the input bar into a ``(reverse-i-search)`query':`` prompt; typing filters, repeated `Ctrl-R` steps to older matches, `Enter` loads the match **into the bar editable (NOT auto-submit)**, `Esc` cancels. Add a **new `ctrl+r` binding in the `input` region** of `keymap.py`. The existing `ctrl+f→open_search` (in-pane *output* search) is a distinct surface and is **not** rebound.
- **D-07:** Searchable corpus = **submitted task inputs only** (prompts that spawned a `run_turn`), most-recent-first, **consecutive duplicates collapsed**, scoped to the **current project's episodic store** (`cli.py:584` episodic memory). Excludes `!cmd` / `#note` / `/`-palette lines (not tasks).

### INPUT-05 — Paste-image
- **D-08:** Detect via **OS-clipboard read on the paste keypress** — probe the clipboard for image data (e.g. `PIL.ImageGrab` / a thin cross-platform clipboard shim) before falling back to normal text paste. If an image is present, attach it; else text paste. Degrades gracefully where clipboard-image is unsupported (falls back to text paste).
- **D-09:** When an image is detected but the active model lacks vision (gated via `capability.py` / provider capabilities): show a **transient inline notice** ("current model has no vision — image not attached"), **drop the image, preserve any text**. No silent data loss; snapshot-testable; rendered as a local block, no `run_turn`.

### Claude's Discretion
- Exact TextArea→prompt-glyph render technique and how the `Submitted`/`_on_key` re-wire is structured (planner/researcher, grounded in current `input_bar.py`).
- Cross-platform clipboard-image shim choice and dependency (`PIL.ImageGrab` vs platform-specific) — planner picks, constraint: hermetic-testable, graceful no-op where unsupported.
- Ctrl-R match algorithm (substring vs fuzzy) and the reverse-i-search prompt rendering details.
- Recorder-event payload shape for `shell.local` / `memory.note` (names are locked; field contents are planner's, consistent with existing `recorder_bridge.py`).
- `!cmd` non-zero-exit and empty `#`/`!` handling (sensible: empty prefix → no-op/normal text; non-zero exit shown in the local block).
- Snapshot-test seeding strategy for episodic history (T7 precedent: deterministic, hermetic, stub provider).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope (requirements source — no locked SPEC.md/REQUIREMENTS.md; INPUT-01..05 are "proposed")
- `.planning/ROADMAP.md` §"Phase T8: Input Bar Ergonomics (v0.2)" (~line 984) — goal, INPUT-01..05, success criteria, cross-cutting constraint (M9 keymap is source of truth).
- `.planning/notes/daily-driver-punch-list.md` §"Phase T8 — Input Bar Ergonomics" (~line 350) — fuller INPUT-0X wording, Claude-Code parity notes, capabilities, sequencing ("lands when M9 keymap stable").

### TUI widgets + locked M9 contracts (T8 modifies / adds-to, does not redesign)
- `voss/harness/tui/widgets/input_bar.py` — the widget T8 rewrites onto `TextArea`: current single-line `Input`, `/`-palette `_on_key` empty-check, `Submitted(Message)` contract, prompt-glyph render.
- `voss/harness/tui/keymap.py` — **LOCKED** M9 single-source-of-truth keymap. `enter/shift+enter/slash` in `input` region; `ctrl+f→open_search` (in-pane output search, distinct from Ctrl-R). T8 adds `ctrl+r` in the `input` region only.
- `voss/harness/tui/app.py`, `voss/harness/tui/widgets/slash_palette.py` — TUI app + palette the InputBar interacts with (focus, mount-before-self).
- `voss/harness/tui/recorder_bridge.py` — recorder-event plumbing for `shell.local` / `memory.note`.

### Bypass + memory + history integration points
- `voss/harness/agent.py`, `voss/harness/cli.py` (`_resolve_run_turn` ~218, `_run_turn_cancellable` ~255, episodic clear ~584) — the `run_turn` path INPUT-02/03 must bypass; episodic store is the Ctrl-R corpus source.
- `voss/harness/memory_cli.py` + `voss_md` module — section-aware `VOSS.md` append path for INPUT-03 (`## Notes`).
- `voss/harness/tui/capability.py` (+ provider capability layer) — vision-capability gate for INPUT-05 (D-09).

### Permission / no-escalation precedent (carry-forward — applies to D-03)
- `.planning/phases/T5-shell-ergonomics/T5-CONTEXT.md` D-12 — edit-mode explicit deny-set / no permission escalation for shell ops.
- `.planning/phases/T7-skills-bootstrap/T7-CONTEXT.md` D-09..D-11 — mutating ops go through existing gated tools, no feature-level bypass; deterministic/hermetic test posture (stub provider).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `voss/harness/tui/widgets/input_bar.py` `InputBar` — base to migrate; keep `Submitted` message + `/`-palette empty-only-open semantics on the new `TextArea`.
- `voss_md` / `memory_cli.py` — existing section-aware `VOSS.md` writer; INPUT-03 reuses it (no new file-write path).
- Existing gated shell-exec tool path + T5-D12 deny-set — INPUT-02 reuses it instead of a new allowlist.
- Episodic store (`cli.py` ~584) — Ctrl-R history source; already records submitted inputs.
- `recorder_bridge.py` — emit `shell.local` / `memory.note` here.
- `capability.py` / provider caps — vision gate for INPUT-05.

### Established Patterns
- M9 keymap is the single source of truth; bindings are added in region tables (`input`/`global`/`main`/`modal`) — T8 adds `ctrl+r` to `input`, never rewrites the table.
- Modal/overlay precedent exists (slash palette, fork modal) but Ctrl-R deliberately uses inline readline UX, not a modal (D-06).
- `Submitted`-message contract decouples the widget from the app loop — preserve it across the TextArea swap.
- Test posture (T7): deterministic, hermetic, stub provider; T8 success criteria mandate Textual snapshot tests + `shell.local`/`memory.note` recorder-event assertions.

### Integration Points
- `input_bar.py` (rewrite) ↔ `keymap.py` (new `ctrl+r` binding) ↔ `app.py` (focus/mount) ↔ `slash_palette.py` (preserved `/` interception).
- Submit-time prefix dispatch (`!`/`#`) branches BEFORE `run_turn`; success path emits the recorder event and renders a local scrollback block.
- INPUT-03 → `voss_md`/`memory_cli` `## Notes` append. INPUT-04 → episodic store query. INPUT-05 → clipboard shim + `capability.py`.

</code_context>

<specifics>
## Specific Ideas

- INPUT-02/03 explicitly mirror Claude Code's `!`-mode and `#`-mode (punch-list parity note).
- Ctrl-R prompt rendering: bash/zsh-style ``(reverse-i-search)`query':`` in the bar; Enter loads editable (user can tweak before submitting), not auto-submit.
- `#note` line format: `- [<ISO-timestamp>] <text>` under `## Notes`.
- `!cmd` local block shows command + stdout/stderr + exit code with a distinct `!` glyph; never enters model history.
- No-vision image paste must produce a visible "image not attached" notice — explicitly no silent drop.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. No scope creep surfaced; no todos matched (`todo.match-phase T8` empty).

Note for SPEC/planner: INPUT-01..05 are **proposed** (no locked SPEC.md / REQUIREMENTS.md entries). If a future `/gsd-spec-phase T8` runs, these nine decisions are the implementation contract; the "explicit attach affordance" alternative for INPUT-05 was considered and rejected as a scope reinterpretation (kept as auto-detect per the requirement wording).

</deferred>

---

*Phase: T8-input-bar-ergonomics-v0-2*
*Context gathered: 2026-05-17*
