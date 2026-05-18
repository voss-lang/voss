# Phase T8: Input Bar Ergonomics (v0.2) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** T8-input-bar-ergonomics-v0-2
**Areas discussed:** Multi-line widget strategy (INPUT-01), !cmd + #note prefix dispatch (INPUT-02/03), Ctrl-R reverse-search UX (INPUT-04), Paste-image detection + fallback (INPUT-05)

> **Pre-discussion fix:** ROADMAP T8 heading used an em-dash (`### Phase T8 — …`) the GSD parser can't resolve (all T-phases affected; only T8 fixed per user). Converted line 984 to colon form `### Phase T8: Input Bar Ergonomics (v0.2)` so `roadmap.get-phase` / `init.phase-op` resolve it. Committed separately (`8c699ba`).

---

## Multi-line widget strategy (INPUT-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Swap to Textual TextArea | Real multi-line; re-wire slash-palette `_on_key`, `Submitted`, prompt glyph | ✓ |
| Custom newline buffer on Input | Keep single-line `Input`, hand-roll multi-line string + grow | |
| TextArea only past row 1 | Stay `Input`, swap to TextArea overlay on Shift+Enter | |

**User's choice:** Swap to Textual TextArea
**Notes:** Enter=submit / Shift+Enter=newline already M9-locked (`keymap.py:23-24`); TextArea default Enter=newline must be inverted.

| Option | Description | Selected |
|--------|-------------|----------|
| Cap at 5 rows, scroll inside | Grow 1→5 then stop; overflow scrolls within TextArea | ✓ |
| Cap at 5, expand to modal | Offer full-height compose modal on overflow | |
| Soft cap, burst to ~10 | Larger transient max before scrolling | |

**User's choice:** Cap at 5 rows, scroll inside
**Notes:** Stable turn-view real estate; matches UI-SPEC "grows up to 5 rows".

---

## !cmd + #note prefix dispatch (INPUT-02/03)

| Option | Description | Selected |
|--------|-------------|----------|
| Route through existing gated shell tool | Inherits T5-D12 deny-set + permission mode; no parallel allowlist | ✓ |
| Static curated allowlist | Hardcoded safe-command set | |
| Config-driven allowlist | User-defined allowlist in .voss/ settings | |

**User's choice:** Route through existing gated shell tool
**Notes:** Consistent with carry-forward (T5-D12 / T7-D09–D11) — no feature-level escalation.

| Option | Description | Selected |
|--------|-------------|----------|
| Ephemeral local block in turn view | `!`-styled scrollback block, cmd+out+exit, not in model history | ✓ |
| Status line / transient toast | Result in status line / toast, nothing persisted | |
| Collapsed block, expand on focus | One-line summary expands when focused | |

**User's choice:** Ephemeral local block in turn view

| Option | Description | Selected |
|--------|-------------|----------|
| Timestamped bullet under `## Notes` | `- [ts] text` under dedicated heading, section-aware append | ✓ |
| Raw line at EOF | Bare text appended to end of VOSS.md | |
| Date-grouped log section | `## Notes / ### YYYY-MM-DD` subheadings | |

**User's choice:** Timestamped bullet under `## Notes`
**Notes:** Reuses voss_md/memory_cli; non-destructive to rest of VOSS.md.

---

## Ctrl-R reverse-search UX (INPUT-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Inline readline-style incremental | `(reverse-i-search)` in bar; Enter loads editable; Esc cancels | ✓ |
| Modal overlay picker | Searchable list overlay (palette/fork-modal precedent) | |
| Dropdown under input bar | Live filtered suggestions beneath bar | |

**User's choice:** Inline readline-style incremental
**Notes:** New `ctrl+r` binding in `input` region; existing `ctrl+f→open_search` (in-pane output search) is a distinct surface, not rebound (M9 keymap locked).

| Option | Description | Selected |
|--------|-------------|----------|
| Submitted task inputs only, deduped, per-project | run_turn prompts only, consecutive dups collapsed, current project | ✓ |
| All input-bar submissions incl !/#// | Everything entered in the bar | |
| Global cross-project history | Inputs across all projects | |

**User's choice:** Submitted task inputs only, deduped, per-project

---

## Paste-image detection + fallback (INPUT-05)

| Option | Description | Selected |
|--------|-------------|----------|
| OS clipboard read on paste keypress | Probe clipboard for image (PIL.ImageGrab/shim) before text paste | ✓ |
| Terminal bracketed-paste inspection only | Treat data-URI/path strings as images; no clipboard dep | |
| Explicit attach affordance instead | Key/command to pick an image file (scope reinterpretation) | |

**User's choice:** OS clipboard read on paste keypress
**Notes:** Graceful degrade to text paste where clipboard-image unsupported.

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse with inline notice, keep text | Capability-gated; visible "no vision" notice; drop image, keep text | ✓ |
| Attach as file path reference | Save to temp/.voss path, inject path as text | |
| Silently ignore the image | Normal text paste, no message | |

**User's choice:** Refuse with inline notice, keep text
**Notes:** Explicitly no silent data loss; gated via capability.py / provider caps.

---

## Claude's Discretion

- TextArea prompt-glyph render technique + `Submitted`/`_on_key` re-wire structure.
- Cross-platform clipboard-image shim choice/dependency.
- Ctrl-R match algorithm (substring vs fuzzy) + reverse-i-search prompt rendering.
- `shell.local` / `memory.note` recorder-event payload shape (names locked).
- `!cmd` non-zero-exit and empty `!`/`#` handling.
- Episodic-history snapshot-test seeding strategy (T7 hermetic/stub-provider precedent).

## Deferred Ideas

None — discussion stayed within phase scope. No todos matched (`todo.match-phase T8` empty). INPUT-05 "explicit attach affordance" alternative considered and rejected as a scope reinterpretation (kept auto-detect per requirement wording).
