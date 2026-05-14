# Phase M9: TUI Shell (TUI-01) — Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Source:** PRD Express Path (`.planning/seeds/tui-shell-textual.md`)

<domain>
## Phase Boundary

Replace the current `rich`-based line-streamed CLI for `voss chat` / `voss do` with a full-screen TUI shell. Match Claude Code / Aider interaction depth, and expose Voss's language primitives (probable values, ctx budgets, spawn/gather sub-agents) directly in the UI as user-visible product surfaces. The phase ships the shell + the streaming view of running `.voss` workflow internals; integration with M8 memory panels and M10 capability surfaces is reserved for after their phases ship but is not blocking.

</domain>

<decisions>
## Implementation Decisions

### App shell

- Full-screen TUI app replaces line-streamed output for `voss chat` and `voss do` (interactive paths).
- Layout regions (locked at this level; precise pixel/character details left to planner):
  - **Header** — session id, budget remaining, provider/model in use.
  - **Main pane** — turn history (scrollable).
  - **Input bar** — slash-command palette with autocomplete.
  - **Modal pane** — diff approval per hunk, permission prompts.

### Streaming workflow visualization

- Live render of running `.voss` program internals using the existing recorder (`voss/harness/recorder.py`) as the event source.
- Probable values rendered with confidence bars.
- `ctx(budget:)` token meter drains live as tokens are consumed.
- `spawn` / `gather` sub-agents rendered as side panels with per-sub-agent budget.

### Diff approval

- Per-hunk yes/no instead of blind apply for any edit the agent proposes.
- This replaces the current behavior where edits stream and apply mid-flow.

### Session UX

- Prior turns are scrollable inside the main pane.
- User can fork from any turn (branch a session from a chosen point).
- Session resume (`voss resume <id>`) opens in the same TUI shell.

### Slash command palette

- `/` opens a palette in the input bar with autocomplete over registered slash commands (`voss/harness/slash.py`).
- `?` opens a help overlay listing keybindings + commands.
- Existing slash commands from M2/M7 register into the palette unchanged.
- Reserve naming/UI hooks for M8 memory commands (`/recall`, `/forget`, `/memory`, `/save`) so M8 can render in the same palette without rework.

### Keybindings

- Vim-ish navigation in the main pane (`j`/`k` scroll, `g`/`G` jump, search with `/` when not in palette context — disambiguation rule decided by planner).

### Headless fallback

- `--plain` flag preserves the current line-streamed mode for pipes / CI / non-TTY environments.
- Auto-detect non-TTY stdout and degrade to `--plain` behavior without requiring the flag.
- Exit codes, stdout shape, and pipe semantics in `--plain` must be byte-identical to current v0.1 behavior.

### Claude's Discretion

- **Library choice** — Textual is the strong default per seed, but `prompt_toolkit` and a hand-rolled curses path are not ruled out; planner picks based on cross-platform behavior and license/dependency weight. Researcher should compare Textual vs prompt_toolkit specifically for: streaming updates from an asyncio recorder, modal overlays, vendored-Python compatibility, and Windows-console rendering quality.
- **Recorder integration mechanics** — whether to consume recorder events via an existing API or add a small subscriber/observer hook in `voss/harness/recorder.py`. Per ROADMAP out-of-scope: do NOT add new runtime hooks; if existing hooks are insufficient, the TUI degrades the visualization rather than expanding the runtime surface — runtime hook extension is a follow-up phase.
- **Diff renderer** — character-level vs line-level highlighting, color palette, side-by-side vs unified — planner picks; must work on a 80-column terminal.
- **Palette ranking** — fuzzy-match scoring and recency weighting are at planner's discretion.
- **Permission prompt UX** — modal blocking vs inline toast — planner picks; must surface the same permission scopes the current harness already enforces (`voss/harness/permissions.py`).
- **Fork-from-turn data model** — how branched sessions are stored on disk (new session row vs parent_id pointer in existing session JSON) — planner picks, but must be backward compatible with `voss sessions` listing.
- **Windows console quirks** — planner must enumerate known Textual-on-Windows failures (vendored-Python via M6 npm wrapper) and pick a strategy: hard-block, soft-degrade, or `--plain` auto-fallback.
- **Theme / color contrast** — defer to a follow-up unless dark/light terminal detection is trivial; do not block phase on aesthetic polish.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source documents

- `.planning/seeds/tui-shell-textual.md` — Seed that became this phase. Contains scope sketch, non-goals, open questions, promotion path.
- `.planning/notes/voss-agent-unfair-advantage.md` — Thesis. Frames *why* the TUI must expose probable values + budgets + spawn/gather as visible product surfaces — they are the Voss differentiation lever.
- `.planning/ROADMAP.md` (Phase M9 section) — Headline deliverables, cross-cutting constraints, explicit out-of-scope.

### Runtime + harness code the TUI must integrate with

- `voss/harness/cli.py` — Current CLI entry points for `voss chat`, `voss do`, `voss resume`. TUI replaces the interactive output path; keep the same argument parsing surface.
- `voss/harness/recorder.py` — Recorder stream the TUI consumes for live workflow visualization. Read-only integration — must not extend the runtime surface (see Claude's Discretion).
- `voss/harness/render.py` — Existing `rich`-based renderer. TUI replaces this for interactive sessions; `--plain` mode continues to use it.
- `voss/harness/session.py` — Session record + rehydration. Fork-from-turn must be backward compatible with this schema.
- `voss/harness/slash.py` — Slash command registry. Palette wraps this.
- `voss/harness/permissions.py` — Permission scopes. Diff/permission modals enforce same scopes.
- `voss_runtime/probable.py`, `voss_runtime/budget.py`, `voss_runtime/agent.py` — Sources of probable values, budgets, spawn/gather state that the live view renders.

### M6 npm wrapper interaction

- `npm/` directory (Voss CLI npm package) — TUI must run inside the vendored Python 3.12 environment shipped via M6 on macOS, Linux, and Windows.

</canonical_refs>

<specifics>
## Specific Ideas

- **Visible primitive thesis** — every probable value, budget meter, and sub-agent panel rendered by the TUI is the "unfair advantage" surface. The TUI is not generic agent chrome — it is the product face of the Voss language primitives. Researcher and planner should treat visible-primitives as the highest-leverage product feature, not a side panel.
- **M4 dogfood compound** — the harness is being rewritten in Voss in M4. The TUI must render `.voss` workflows produced by M4, so the visualization layer should consume recorder events generic enough to handle any user `.voss` workflow, not just hard-code the harness's own structure.
- **Reserved slash command names** for M8 (`/recall`, `/forget`, `/memory`, `/save`) — palette must not conflict; M8 will register these.

</specifics>

<deferred>
## Deferred Ideas

- **Editor / VSCode integration** — separate EDIT-01/02 track.
- **Web UI** — explicitly out-of-scope for v0.2.
- **New runtime hooks** — if the recorder API is insufficient for visualization, runtime-hook extension is a follow-up phase, not part of M9.
- **Theme / aesthetic polish** — minimal viable contrast only in M9; theming follow-up later.
- **M8 memory browse panel** — UI hooks reserved, full integration lands when M8 ships.
- **M10 multi-agent chat panels** — sub-agent panel primitives ship here; rich multi-agent chat UX is M10.
- **Long-running task / watch bottom strip** — M10 capability.

</deferred>

---

*Phase: M9-tui-shell-tui-01*
*Context gathered: 2026-05-14 via PRD Express Path*
