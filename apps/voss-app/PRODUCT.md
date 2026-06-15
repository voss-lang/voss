# voss-app — Product & Design Contract (V24)

> **Status:** locked contract. This is the W0 source of truth for the V24 ADE
> product revamp (requirement **VADE2-01**). Plans V24-02 through V24-08 cite this
> file by section name for information architecture, success criteria, and the
> locked copy vocabulary. Do **not** re-derive labels, IA, or success bars
> elsewhere — change them here first.
>
> **Authoritative visual/interaction spec:** see the **Visual & Interaction
> Contract** section below, which points at `V24-UI-SPEC.md`. This document owns
> *product* decisions (register, IA, vocabulary, success); the UI-SPEC owns
> *visual* decisions (tokens, geometry, component anatomy). They must not
> contradict; where they overlap on copy, the UI-SPEC §Copywriting Contract and
> this file's **Locked Vocabulary** are byte-consistent.

---

## Product Register

**Default register: product.** Every default-chrome surface speaks to a developer
who has never read Voss internals. Internal vocabulary (`runId`, `RunData`,
presets, raw modes) is an implementation detail, not a user-facing word.

| Attribute | Value |
|-----------|-------|
| Default register | **Product** (not engineering, not internal tooling) |
| Primary user | **Ben** — a fluent terminal-native developer |
| Future audience | **Developer teams** licensing controlled, observable agent work |
| Register test | A fluent developer understands what Voss does on first open *without* learning internal labels first |

**Product thesis (from ROADMAP §V24):**

> Terminals are where work runs. **Voss is where agent work becomes scoped,
> observable, reviewable, and trustworthy.**

Voss is the operating layer *around* the work, not a requirement imposed on every
pane. The terminal workbench stands on its own; the managed-agent layer and the
Swarm Map are what Voss adds on top.

---

## Information Architecture

Navigation is a **left portal**. The **terminal grid is the persistent canvas.**
Selecting a portal surface uses **canvas-swap** (D-01): the chosen surface takes
the canvas while `GridRoot` stays mounted and alive behind it and restores
instantly on return — not a split, not a floating drawer.

**Launch behavior (D-02):** fresh / project-less workspaces boot to the terminal
grid (enforces the L1 "ignore Voss, still a terminal" constraint on first paint).
Workspaces with active managed runs restore their last-used surface.

The left portal has **8 items, in this order**:

| # | Portal item | Surface kind | Notes |
|---|-------------|--------------|-------|
| 1 | **Overview** | NEW product surface | Mission-control summary of managed work |
| 2 | **Tasks** | NEW product surface | Top-level unit of managed agent work (D-08; NOT "Runs") |
| 3 | **Agents** | NEW product surface | Agent roster by role/status |
| 4 | **Swarm Map** | NEW product surface | Observability/replay graph (D-10) |
| 5 | **Review** | Reused as-is | Wires to existing V14 cockpit / panels — no redesign this phase |
| 6 | **Context** | Reused as-is | Wires to existing panels/drawers — no redesign this phase |
| 7 | **Memory** | Reused as-is | Wires to existing panels/drawers — no redesign this phase |
| 8 | **Settings** | Reused as-is | Wires to existing settings UI — no redesign this phase |

- **4 NEW product surfaces:** Overview, Tasks, Agents, Swarm Map (built in V24-05/06/07).
- **4 reused surfaces:** Review, Context, Memory, Settings (wire to existing V14/panels/drawers as-is; redesign is explicitly out of scope for V24).

**Spatial model recap:** left portal = navigation; terminal grid = persistent
canvas via canvas-swap (D-01). Top chrome carries project/window identity,
command palette/status, and mode indicators only — layout presets
(`fanout/pipeline/swarm/watchers`) are demoted to a layout menu / pane toolbar,
they are **not** product navigation (VADE2-03).

---

## Success Criteria

The revamp is proven, not assumed. These are the falsifiable bars copied from
**V24-SPEC §Acceptance Criteria**:

- [ ] Product/design contract committed with IA, success criteria, and locked vocabulary (Task / Swarm Map / Read only·Can edit·Autopilot / steps·cards) — *this file*.
- [ ] Left portal exposes all 8 items; selecting a surface uses canvas-swap and grid/pane state survives a portal round-trip.
- [ ] Fresh / project-less workspace boots to the terminal grid.
- [ ] Default top chrome contains no `fanout/pipeline/swarm/watchers` presets and no raw `Plan/Edit/Auto` toggles; presets reachable via layout menu / pane control.
- [ ] "Ask Voss to…" composer is global, defaults to **Read only**, and hides scope/agent/team/budget/context behind "Advanced".
- [ ] Overview/Tasks/Agents show fixture runs under correct statuses with a working attention action + deep link.
- [ ] Swarm Map renders radial clusters (one per run) from full fixture data.
- [ ] No-fake-signal guard test passes: empty/partial sources yield placeholders/omission and zero source-less edges.
- [ ] Live edges update from a stream fixture; reduced-motion yields static connectors + trace fallback; a completed run is replay-scrubbable.
- [ ] Manual terminal-first checklist passes and is documented; existing grid/pane/terminal unit tests stay green.
- [ ] Deep-link, a11y/reduced-motion, visual screenshot, and focused Tauri/Rust/TS checks pass.

**Two hard-fails (from the V24-SPEC Interview Log — either alone = product failure):**

1. **Raw internal labels in default chrome.** If any default-chrome surface shows
   `runId`, `RunData`, `Plan/Edit/Auto`, or a layout-preset name as if it were
   product vocabulary, the revamp has failed.
2. **Presets-as-navigation.** If `fanout/pipeline/swarm/watchers` presets are
   presented as top-level navigation rather than a demoted layout control, the
   revamp has failed.

**Non-negotiable constraint (L1 terminal credibility):** a user can ignore Voss
entirely and use the app as a terminal — open/split/focus panes, run arbitrary
commands, launch a custom CLI agent, work project-less, and persist sessions —
all **without Voss credentials**.

---

## Locked Vocabulary

These are the load-bearing user-facing terms. Every downstream surface uses
exactly these strings; they are byte-consistent with `V24-UI-SPEC` §Copywriting
Contract. Each entry cites the decision that locks it.

| Concept | User-facing copy | Decision | Notes |
|---------|------------------|----------|-------|
| Top-level unit of managed agent work | **Task** | D-08 / VADE2-01 | The portal item is **"Tasks"**, **NOT "Runs."** The ROADMAP-listed "Runs" item is renamed to "Tasks" for IA consistency. |
| Observability / replay surface | **Swarm Map** | D-10 / VADE2-01 | Nav label + brand; on-brand with the swarm-coordination differentiator. |
| Safety mode 1 (default) | **Read only** | D-11 / VADE2-01 | Two words, no hyphen. Default posture — agent can analyze/plan but not edit until elevated (D-04). |
| Safety mode 2 | **Can edit** | D-11 / VADE2-01 | Two words. |
| Safety mode 3 | **Autopilot** | D-11 / VADE2-01 | One word; highest risk, most salient. |
| (Retired modes) | ~~Plan / Edit / Auto~~ | D-11 | The exposed top-level `Plan/Edit/Auto` toggles are **retired** — never shown in default chrome. |
| Board work-items inside a Task | **steps** / **cards** | D-09 / VADE2-01 | Lowercase. **Never "tasks"** inside a Task, so the Swarm Map stays unambiguous. |
| Composer primary CTA | **Create Task** | D-08 / VADE2-01 | Verb + locked noun; the composer "creates a Task." |
| Composer title | **Ask Voss to…** | VADE2-04 | Unicode ellipsis (…), not three dots. Global, always-present, Cmd-K-style (D-03). |
| Internal code identifiers | `runId` / `RunData` / `currentRunId` | D-09 | **Retained in code only. NEVER shown to the user.** Zero display exposure; zero internal rename churn — display layer only. |

**Vocabulary rule:** if a string appears to a user in default chrome, it must be
a row in this table or in the `V24-UI-SPEC` §Copywriting Contract. Internal
identifiers stay in code.

---

## Visual & Interaction Contract

The authoritative visual and interaction specification for V24 is:

> **`.planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md`**

That `V24-UI-SPEC` document owns the design system (Tailwind v4 + Variant B CSS
vars), spacing scale, typography, color tokens, the canvas-swap interaction
contract, the full component inventory (PortalRail, TopChrome, VossComposer,
mission-control surfaces, SwarmMap canvas, live connectors, replay scrubber),
per-surface states, accessibility, and the animation budget.

This PRODUCT.md does **not** duplicate token tables or component geometry —
reference `V24-UI-SPEC` for all visual/interaction detail. Where the two overlap
on copy, the **Locked Vocabulary** table above and the `V24-UI-SPEC` §Copywriting
Contract are kept identical.

---

*Phase: V24-ade-product-revamp-swarm-observability*
*Contract authored: 2026-06-15 — VADE2-01 (W0)*
