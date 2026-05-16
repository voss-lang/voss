---
sketch: 001
name: voss-grid-shell
question: "What chrome density and visual structure feels right for a harness-native grid of agent cells?"
winner: null
tags: [layout, grid, terminal, ade, shell]
---

# Sketch 001: Voss Grid Shell

## Design Question

A Voss-powered ADE puts a live agent loop in every grid cell. Three forces pull against each other:

- **Density** — terminal users want lots of panes, low chrome
- **Legibility** — turn structure (user / assistant / tool / reviewer) needs visual hierarchy
- **Flow** — cells aren't independent. Pipelines, fan-outs, reviewer-attachments must be visible

What balance of chrome, density, and structure makes the grid feel like a *power tool* instead of either a chat app or a raw tmux?

## How to View

```
open .planning/sketches/001-voss-grid-shell/index.html
```

Press `1` / `2` / `3` to flip variants. Click any cell to focus.

## Variants

- **A: Warp-Block Heavy** — discrete turn cards with chrome (head/foot per cell), rounded panels, gap between. Each turn = bordered card. Closest to Warp's block metaphor.
- **B: Minimal Tile** — tmux-density. Thin 1px borders, no rounding, 22px headers, status footer collapses. Streaming lines dominate. Max info per screen.
- **C: Floating Canvas** — cells float on dotted-grid canvas with glass backdrop. SVG pipeline arrows drawn between cells (planner→executor cyan, executor→reviewer amber). Highest visual hierarchy.

## What to Look For

Compare the four cells in each variant (planner / executor / reviewer / watcher):

1. **Cell HUD** — model, cwd, iteration, cost, DSL hot-reload badge. Which variant surfaces these without crowding the stream?
2. **Streaming turn** — the live `<span class="cursor">` block. Which variant makes "agent is thinking now" obvious?
3. **Inter-cell flow** — pipeline arrow (planner→executor). A has tiny inline arrow, B uses `←` text indicator in header, C draws animated SVG. Which reads at a glance?
4. **Reviewer attachment** — reviewer cell critiquing executor. A uses a label badge, B uses header text, C uses a floating pill above the cell.
5. **Command bar** — focused cell has input with `❯`. Broadcast prefix (`>>`, `>>>`) hint. Which feels most "type to drive"?
6. **Titlebar** — layout-preset switcher (fanout/pipeline/swarm/watchers) + cost meter. A and C give them breathing room, B compresses for density.

## Key Tradeoffs

| | Density | Hierarchy | Flow visualization |
|---|---|---|---|
| A | medium | high (cards) | weak (small inline arrow) |
| B | **max** | low | medium (text indicator) |
| C | low | **highest** | **strong** (animated SVG) |

## Open Questions for Synthesis

- B's density wins for power users — could A's turn-card structure work *inside* B's thin-bordered cells?
- C's SVG arrows are killer but only work at sparse density. Worth a layout-preset toggle (compact vs canvas)?
- DSL hot-reload badge (`⟳ loop.voss`) needs to be *findable* — A puts it in head-right, B compresses, C puts it in a pill. Which sticks?
