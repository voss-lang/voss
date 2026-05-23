# Phase A12: voss-app ADE Visual Redesign - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** A12-voss-app-ade-visual-redesign
**Areas discussed:** Sidebar scope & sections, Theme migration strategy, Agent launch UX, Sidebar ↔ grid interaction, Status bar agent badge, Titlebar branding, Animation & transitions

---

## Sidebar Scope & Sections

| Option | Description | Selected |
|--------|-------------|----------|
| Agents + Launch only | Sidebar purely agent-focused | |
| Agents + Files + History | Full sketch layout, ContextPanel stays | ✓ |
| Replace ContextPanel | Sidebar absorbs ContextPanel's role | |

**User's choice:** Agents + Files + History (two panels, two purposes)

| Option | Description | Selected |
|--------|-------------|----------|
| Visible by default | New users see sidebar immediately | ✓ |
| Collapsed by default | Max terminal density on first launch | |
| Context-dependent | Visible when agents running | |

**User's choice:** Visible by default

| Option | Description | Selected |
|--------|-------------|----------|
| Read-only tree | Expand/collapse, no click action | ✓ |
| Clickable tree | Click file opens in editor pane | |
| Defer files entirely | Ship without files section | |

**User's choice:** Read-only tree

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed 280px | Simple, matches sketch | ✓ |
| Fixed 240px | Narrower for more grid space | |
| Resizable (240-360px) | User drags right edge | |

**User's choice:** Fixed 280px

**History source:** User requested BOTH git log AND agent sessions, but as **separate sections** (not merged). Final section order: Agents → Sessions → Files → Git.

**Launch button:** User moved Quick Launch out of sidebar body into a `+ Agent` button in the sidebar header (top-right corner).

---

## Theme Migration Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Full swap in variant-b.css | Rewrite all token values in one shot | |
| New theme file | Create alongside, old preserved | |
| Gradual component-by-component | Add warm tokens, migrate incrementally | |

**User's choice:** Create new theme entry "Voss Ignite" in existing catalog system. Variant B preserved. User shared screenshot of Warp's theme picker as reference for future settings UI (deferred to A9).

**Theme name:** "Voss Ignite" (user specified)

| Option | Description | Selected |
|--------|-------------|----------|
| Selective rounding | 0 on panes, 3-6px on interactive elements | ✓ |
| Stay zero-radius | Everything sharp | |
| Soft rounding everywhere | 6-10px on most elements | |

| Option | Description | Selected |
|--------|-------------|----------|
| Display headings only | Poppins for app name, section titles, modal headers | ✓ |
| Poppins for all UI chrome | Replaces Inter everywhere except terminal | |
| Keep Inter everywhere | Skip Poppins entirely | |

| Option | Description | Selected |
|--------|-------------|----------|
| Chrome + terminal | Full xterm retheme (warm ANSI palette) | ✓ |
| Chrome only | Terminal keeps defaults | |
| Chrome + terminal cursor/bg only | Middle ground | |

---

## Agent Launch UX

**User clarification:** Shared Warp "New Agent Session" screenshot as reference. Wants centered modal with CLI picker, model selector, effort level, mode toggles, task prompt. "Maybe even more robust."

| Option | Description | Selected |
|--------|-------------|----------|
| Centered modal overlay | Floats over grid, Escape to dismiss | ✓ |
| Sidebar inline expansion | Expands within sidebar body | |
| Right panel | Slides in from right | |

**CLI presets:** User specified: Claude, Codex, Antigravity (new Gemini), OpenCode, Voss, Custom

| Option | Description | Selected |
|--------|-------------|----------|
| Full config modal | Model/effort/toggles/prompt — full experience | ✓ |
| CLI + prompt only | Pick CLI, type prompt, launch | |
| CLI picker only | Pick CLI, launches with defaults | |

**Voss CLI preset:** User requested Voss as a first-class preset. When selected, shows Voss-specific config (command: chat/do/resume/skill/agent, mode, auth) instead of generic agent config.

| Option | Description | Selected |
|--------|-------------|----------|
| Full Voss config panel | All CLI commands exposed | ✓ |
| Chat + Do only | Two main commands | |
| Launches chat with defaults | Minimal | |

| Option | Description | Selected |
|--------|-------------|----------|
| Split from focused pane | Consistent with ⌘D fork | ✓ |
| Always bottom-right | Predictable position | |
| User chooses in modal | Spawn position option | |

| Option | Description | Selected |
|--------|-------------|----------|
| Button only | Single entry point via + Agent | ✓ |
| Both button + ⌘K | Palette integration too | |
| Dedicated shortcut | Three ways in | |

| Option | Description | Selected |
|--------|-------------|----------|
| Optional prompt (as CLI arg) | If filled → arg, if empty → interactive | ✓ |
| CLI argument always | Required | |
| Typed into terminal after spawn | Auto-type into stdin | |

---

## Sidebar ↔ Grid Interaction

**All four options selected (multiSelect):**
- ✓ Click to focus pane (bidirectional sync)
- ✓ Right-click context menu (Stop/Restart/Detach/Copy cost/Focus)
- ✓ Live cost/token in sidebar (reactive from OSC telemetry)
- ✓ Drag to reorder (visual only, doesn't affect grid)

| Option | Description | Selected |
|--------|-------------|----------|
| Bidirectional sync | Click pane ↔ sidebar always in sync | ✓ |
| Sidebar → grid only | One-way | |
| No visual sync | Independent | |

| Option | Description | Selected |
|--------|-------------|----------|
| Agents only | Only detected agent CLIs in sidebar | ✓ |
| All panes | Every pane appears | |
| Agents + pinned shells | Opt-in shell visibility | |

---

## Status Bar Agent Badge

| Option | Description | Selected |
|--------|-------------|----------|
| Count + total cost | "3 agents · $1.42" orange pill | ✓ |
| Count only | Simpler | |
| Count + active model | Shows focused agent's model | |

| Option | Description | Selected |
|--------|-------------|----------|
| Toggles sidebar | Click badge opens/closes sidebar | ✓ |
| Opens agent popover | Mini-sidebar above status bar | |
| No action | Display-only | |

---

## Titlebar Branding

| Option | Description | Selected |
|--------|-------------|----------|
| Left of project name | traffic lights → gap → logo → name → presets | ✓ |
| Far left after traffic lights | Logo as brand anchor | |
| No logo in titlebar | Logo only in sidebar header | |

---

## Animation & Transitions

| Option | Description | Selected |
|--------|-------------|----------|
| Subtle and fast | 200ms sidebar, 150ms modal, 100ms focus, prefers-reduced-motion | ✓ |
| Minimal | Snap open/close, hover only | |
| Rich | Spring physics, staggered fades, glow effects | |

---

## Claude's Discretion

- Exact ANSI color remapping for warm xterm palette
- Agent session tracking data structure
- File tree implementation (depth limits, debounce)
- Context menu positioning and dismissal
- Drag-to-reorder implementation approach

## Deferred Ideas

- **Warp-style theme picker** (card previews, filters, search) — A9 or new phase
- **File tree click-to-open** — needs editor pane integration
- **Agent session persistence** — depends on F1
