# Phase A4: voss-app Layout Presets - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-19
**Phase:** A4-voss-app-layout-presets
**Areas discussed:** Preset→pane mapping, Count vs capacity (LAY-05), ⌘G cycle + reversibility, Saved layout: content + load

---

## Preset → pane mapping

| Option | Description | Selected |
|--------|-------------|----------|
| By pane index order | Fill slots in A3's stable index order (left→right, top→bottom), reuse recomputeIndices(); deterministic, testable | ✓ |
| Focused pane = primary | Focused pane takes the primary slot, rest by index; intent-preserving but focus-state dependent | |
| Nearest spatial position | Each pane → closest target slot; minimizes jump but ambiguous/hard to test | |

**User's choice:** By pane index order
**Notes:** Pane #1 fills the preset primary slot (fanout source / watchers main / swarm top-left / pipeline leftmost).

| Option | Description | Selected |
|--------|-------------|----------|
| Follow same pane | Focus stays on the same PTY pane wherever it lands; content-follows-focus | ✓ |
| Primary slot | Focus jumps to pane #1 / primary slot every switch | |
| Keep slot position | Focus stays at same screen slot (different content) | |

**User's choice:** Follow same pane
**Notes:** Least disorienting; consistent with never-destroy intent.

---

## Count vs capacity (LAY-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Grow the flexible region | Extras pack into preset's repeatable region (fanout/watchers grow count, pipeline adds cols, swarm toward 4×4) | ✓ |
| Split the last slot | Fixed slot count; overflow binary-splits final slot | |
| Even grid fallback | Over capacity → abandon preset, even NxN grid | |

**User's choice:** Grow the flexible region

| Option | Description | Selected |
|--------|-------------|----------|
| Spill-extra + lay-what-exists | Over hard cap: split last region cell (kept). Under: lay out only existing panes, no fillers | ✓ |
| Spill-extra + spawn fillers | Over: split last cell. Under: spawn fresh panes to fill preset minimum | |
| Block over cap | Refuse switch if over cap (toast); under lays what exists | |

**User's choice:** Spill-extra + lay-what-exists
**Notes:** Hard cap = swarm 4×4 / watchers max; never destroy panes; no unasked filler panes.

---

## ⌘G cycle + reversibility

| Option | Description | Selected |
|--------|-------------|----------|
| Snap to first preset | ⌘G from custom → fanout; order fanout→pipeline→swarm→watchers→wrap; widget shows 'custom' until ⌘G | ✓ |
| Resume last preset's next | Track last preset; ⌘G advances to the one after it | |
| Treat custom as a 5th stop | custom→fanout→…→watchers→custom; most reversible, needs custom state in ring | |

**User's choice:** Snap to first preset

| Option | Description | Selected |
|--------|-------------|----------|
| Recompute fresh | Each preset entry recomputes canonical geometry; stateless; tweaks transient; Save layout = persistence | ✓ |
| Remember per-preset tweaks | Cache each preset's last geometry for the session | |

**User's choice:** Recompute fresh

---

## Saved layout: content + load

| Option | Description | Selected |
|--------|-------------|----------|
| Geometry + cwds + shell | Tree shape + ratios + active preset + per-pane cwd + shell; no scrollback/procs (A6) | ✓ |
| Geometry only | Tree shape + ratios + preset only; reload = empty panes | |
| Geometry + cwds + shell + env | Above + per-pane env snapshot; fragile, edges into A6 scope | |

**User's choice:** Geometry + cwds + shell

| Option | Description | Selected |
|--------|-------------|----------|
| Remap existing onto geometry | Apply saved geometry to open panes (index-order); saved cwd/shell only for net-new slots; never kill running | ✓ |
| Kill + respawn from file | Close current, spawn fresh per saved cwd/shell; contradicts A3 D-04 | |
| Open in addition | Spawn saved layout alongside current; pane count balloons | |

**User's choice:** Remap existing onto geometry

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-apply + version+migrate | default.json auto-applies on open; integer schema version; best-effort migrate; fail→ignore+log | ✓ |
| Auto-apply + reject mismatch | Auto-apply; version mismatch ignored entirely (no migration) | |
| Opt-in load + version+migrate | default.json never auto-applies; explicit palette load; fails ROADMAP success criterion 3 | |

**User's choice:** Auto-apply + version+migrate

---

## Claude's Discretion

- Exact tree-construction algorithm mapping preset shapes onto A3 binary-split tree (bounded by D-01..D-04 + A3 D-02 geometry model).
- Switcher-widget interaction states / click-to-pick vs display-only (within locked Variant B tokens).
- `⌘G` behavior during one-pane flood (inherits A2 D-02/D-03 coalesce; correctness only hard requirement).
- Layout-name collision policy on "Save layout as…" (overwrite/confirm/auto-suffix).
- Versioned-schema concrete shape + migration mechanics (bounded by D-09).

## Deferred Ideas

None — discussion stayed within A4 scope. Adjacent capabilities already fenced: scrollback/process restore → A6; command palette UI → A7; project open → A5; status bar → A9; L2 preset semantics → post-A10.
