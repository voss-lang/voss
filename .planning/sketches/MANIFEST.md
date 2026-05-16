# Sketch Manifest

## Design Direction

**Voss ADE** — desktop app where the Voss harness is the substrate, not a guest. Each grid cell is a live agent loop (planner / executor / reviewer / watcher), wired via DSL events. Aesthetic: dark terminal, mono font, but more visual structure than raw tmux. Inspired by Warp blocks + agent-loop inspector + tmux density.

**Core conviction:** the grid is for *steering agents*, not typing commands. Shell is one tool among many; the loop is primary.

## Reference Points

- **Warp** — turn-as-block metaphor, but bolted-on AI. Voss inverts: agent is primary.
- **tmux / Zellij** — grid density, keyboard-driven, but no loop semantics.
- **Cursor / Zed agent panel** — chat-with-files, single-thread. Voss is multi-cell, event-wired.
- **Excalidraw / tldraw** — canvas + cards for variant C inspiration.

## Sketches

| # | Name | Design Question | Winner | Tags |
|---|------|----------------|--------|------|
| 001 | voss-grid-shell | Chrome density and visual structure for harness-native grid of agent cells | **B: Minimal Tile** — tmux-density wins. Thin 1px borders, 22px headers, max info/pixel. | layout, grid, terminal, ade, shell |

## Key Decisions

- **Density over chrome.** Power-user grid. Turn-card chrome (Variant A) trades too much vertical real estate. Floating canvas (Variant C) too sparse for >4 cells.
- **Header = single line, 22px.** Role · model · cwd · iter · cost · DSL badge, all inline. Right-align side notes (`← planner`, `watching ↑ exec`).
- **Streaming via inline cursor**, not progress bars. Lines accumulate top-down like real terminal.
- **Focused cell = inset shadow + bg lift.** No heavy border ring. Subtle enough to stack 6+ cells without visual chaos.
- **Tool calls = `⏵` prefix, dim color.** User = `❯` green. Reviewer = `※` amber. Glyph-as-affordance.

i think 