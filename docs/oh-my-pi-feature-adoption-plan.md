# oh-my-pi Feature Adoption Plan for Voss

Status: Proposed
Date: 2026-06-05
Source: [`can1357/oh-my-pi`](https://github.com/can1357/oh-my-pi) (omp) — TS/Rust/Python coding-agent CLI+TUI, fork of Mario Zechner's Pi.

## Purpose

omp overlaps Voss heavily (terminal-first harness, multi-provider, multi-agent, Rust core). This plan selects the omp features that graft cleanly onto Voss's existing architecture and sequences them by value-to-effort. It is grounded in the current Voss code, not a wishlist.

### Voss code touched by this plan

| Area | File(s) |
|------|---------|
| Edit tool | `crates/voss-tools/src/fs_edit.rs` |
| Tool registry | `crates/voss-tools/src/registry.rs`, `tool_trait.rs` |
| Provider trait | `crates/voss-providers/src/traits.rs`, `lib.rs`, `anthropic.rs`, `openai.rs` |
| Turn loop / routing | `crates/voss-agent/src/dispatch.rs`, `run_turn.rs`, `plan.rs` |
| Auth | `crates/voss-auth/src/*` (codex/anthropic oauth already present) |
| Render / TUI | `crates/voss-render`, `crates/voss-tui` |
| Python bridge | `voss/bridge_server.py`, `voss/harness` |

---

## Selected features (ranked)

### Tier 1 — High value, isolated, do first

#### 1. Hashline edits
**What omp does:** model edits by referencing a content-hash anchor instead of retyping line ranges. Stale anchors are rejected before write. Reported ~61% fewer output tokens (Grok 4 Fast).

**Voss today:** `fs_edit.rs` takes `{path, old, new}`, requires `old` to appear exactly once (`text.matches(&args.old).count()`), then `replacen`. Works, but the model must emit the full `old` block verbatim every edit — the token cost omp eliminates.

**Plan:**
- Add an optional `anchor` field to `FsEditArgs`: a short content hash (e.g. first 8 hex of SHA-256 of the target line(s)).
- New flow: model supplies `anchor` + `new`; tool resolves anchor → unique span, applies replacement. Reject on zero/multiple/stale anchor with explicit error (mirror existing zero/multi-match errors).
- Keep `old`-based path as fallback for back-compat.
- Emit anchors in `fs_read` output (gutter hash per line or per hunk) so the model has them without extra reads.

**Effort:** S–M. Single crate (`voss-tools`) + read-tool annotation. No protocol change.
**Risk:** anchor collision on duplicate lines — disambiguate with line-range qualifier.

#### 2. Model roles + fallback chains
**What omp does:** four/five named roles (`default`, `smol` cheap subagents, `slow` deep reasoning, `plan`, `commit`). Per-role fallback chains cascade on 429/quota; per-credential backoff; path-scoped overrides (closest path wins).

**Voss today:** `ModelProvider::complete` takes a single `model` string per request (`traits.rs`). `voss-auth` already handles codex + anthropic oauth, so multi-credential is half-built. No role concept, no fallback.

**Plan:**
- Define a `Role` enum (`Default | Smol | Slow | Plan | Commit`) and a `RoleRouter` that maps role → ordered list of `(provider, model, credential)`.
- Config: `~/.voss/models.yml` (or extend existing config) declaring per-role chains. Support path-scoped overrides keyed by repo/dir prefix.
- Wrap `complete()` calls in `run_turn.rs` / `dispatch.rs`: select chain by role, try in order, advance on 429/quota/terminal error, apply per-credential backoff.
- Wire roles to call sites: subagents → `smol`, plan mode (`plan.rs`) → `plan`, commit messages → `commit`.

**Effort:** M. Leverages existing `voss-auth` multi-credential. Touches providers + agent.
**Risk:** retry/backoff interacting with cancellation (`cancelled()` in `run_turn.rs`) — thread the cancel token through retries.

#### 3. Preview-then-accept (diff cards / `resolve`)
**What omp does:** mutating tools stage changes as a preview; agent calls `resolve` to commit atomically. Destructive ops surface as clickable/dismissible TUI cards.

**Voss today:** `dispatch.rs` runs mutating tools serially with a per-step permission gate (`PermissionCheck`), but the write happens immediately inside `invoke()` (`fs_edit.rs` writes the file in-place). No staging, no visible diff before apply. Directly addresses the "feels like a terminal spawner, not an ADE" gap.

**Plan:**
- Introduce a staging layer: mutating tools return a `Preview { path, diff, apply_fn }` instead of writing. Extend `tool_trait.rs` with an optional `stage()` path or a `Staged` result variant.
- Add a `resolve` tool / action that commits or discards staged previews atomically.
- Render previews as diff cards in `voss-render` / `voss-tui` (counts + hunks), with accept/reject keybindings.
- Default policy: auto-apply read-only and low-risk; require resolve for destructive (align with existing permission gate severity).

**Effort:** M–L. Touches tool trait, dispatch, render, TUI.
**Risk:** largest blast radius of Tier 1. Land behind a flag; keep immediate-apply as default until UI proven.

### Tier 2 — Multi-agent launcher alignment

#### 4. `task` subagents + worktree isolation
**What omp does:** `task` spawns isolated worktrees with independent tool surfaces, returns schema-validated JSON.

**Voss alignment:** matches the requested navbar Agents launcher (Claude/Codex/Gemini/OpenCode prefixes). Voss already has worktree isolation as a Workflow primitive and parallel/serial dispatch in `dispatch.rs`.

**Plan:**
- Define a `task` tool: spawn a sub-run in a git worktree, isolated tool registry, `smol` role, JSON-schema'd return.
- Reuse `dispatch.rs` fan-out cap for concurrent subagents.

**Effort:** M. Defer until Tier 1 lands. Feeds the post-A3 Agents feature.

#### 5. Inter-agent messaging (`irc`)
**What omp does:** live sibling-to-sibling coordination channel.

**Plan:** lightweight message bus over the Python bridge (`bridge_server.py`) for running subagents. Only build if `task` subagents prove useful. **Effort:** M. Speculative — gate on demand.

#### 6. Hindsight memory bank
**What omp does:** checkpoint / rewind / retain / recall / reflect; project-scoped durable facts reloaded next session.

**Voss today:** `voss-agent/src/episodic.rs` exists; SecondBrain sidecar covers some of this externally.
**Plan:** evaluate whether to extend `episodic.rs` in-harness vs. keep SecondBrain external. **Effort:** M. Decision-first, not build-first.

**RESOLVED (2026-06-06):** Original framing under-counted Voss. The durable bank already exists in-harness: `voss/harness/memory_store.py` `MemoryStore` (839 lines — `.voss/memory/` fs mirror + chroma vector + BM25 recall + per-source quotas + tombstones). `episodic.{rs,py}` is only the rolling turn-summary tier, **not** the durable layer — do not extend it for this. SecondBrain has **zero references** in the Voss product; it is an external Claude Code dev sidecar (personal vault) — keep it external, do **not** bridge (wrong layer, would couple Voss to personal tooling). omp-verb mapping onto existing Voss: `recall` ✓ (`voss recall` CLI / `MemoryStore.recall`), `retain` ✓ (`MemoryStore.write_note`), `reflect` ≈ (`conventions.write_convention`, user-confirmed at session end). **Real gaps** (only if pursued): (a) expose `recall`+`retain` as **agent-callable tools** (today they are user/CLI-driven only) — cheap, wraps existing methods, enables model-driven memory; (b) `checkpoint`/`rewind` session snapshot+restore (no equivalent; `session_store`/`SessionRecord` is the foundation) — larger. **Decision: keep durable memory in-harness via MemoryStore; build nothing now; if demand appears, do (a) first.**

### Tier 3 — Rust core performance (already Rust client)

- **In-process ripgrep/glob/find** — Voss has `fs_grep.rs`/`fs_glob.rs`; confirm no fork/exec on hot path, match omp's in-process model.
- **AST structural edits** — tree-sitter structural rewrites previewed before apply. Voss already has AST machinery in Python (`voss/ast_*.py`, `parser.py`, `grammar.lark`); decide Rust vs. reuse Python bridge.
- **mtime-keyed fs-cache** shared across read/grep/lsp.

**Effort:** varies. Opportunistic — pick up when touching those tools.

### Explicitly out of scope

- Browser stealth / Electron driving — not Voss's domain.
- 14-provider `web_search` chain — overkill unless Voss adds research mode.
- ACP/RPC editor-embed modes — only if editor integration becomes a goal.
- Config inheritance from `.cursor`/`.windsurf`/etc. — nice adoption lever, low priority; revisit for launch.

---

## Sequencing

```
Phase 1 (isolated wins):     [1] hashline edits  →  [2] model roles + fallback
Phase 2 (UX, the ADE gap):   [3] preview-then-accept diff cards
Phase 3 (agents feature):    [4] task subagents  →  [5] irc  (gate on demand)
Phase 4 (decisions):         [6] memory bank scope  +  Tier 3 perf opportunistic
```

Rationale: 1 and 2 are single-crate, high-leverage, no UI risk — ship them to bank the token savings and routing robustness. 3 is the highest-value UX change but also the largest blast radius, so it follows once Tier 1 proves the staging/anchor plumbing. Tier 2 explicitly feeds the already-requested Agents launcher and waits for the A-track slot. Tier 3 is picked up opportunistically.

## Success criteria

| Item | Verify |
|------|--------|
| Hashline edits | edit by anchor applies correctly; stale anchor rejected; measure output-token delta on a real edit session |
| Model roles | subagent uses `smol`, plan uses `plan`; 429 on primary cascades to next in chain without turn failure |
| Preview-then-accept | destructive edit shows diff card; resolve commits atomically; discard leaves file untouched |
| task subagents | subagent runs in isolated worktree, returns schema-valid JSON, parent merges result |

## Open questions

1. ~~Hashline anchor scheme — per-line hash vs. per-hunk? Collision handling on duplicate lines?~~ **RESOLVED:** per-line anchor (first 8 hex SHA-256 of line content, `split('\n')` canonical both langs); duplicates → multi-match error → use `old` or `end_anchor` span. Shipped.
2. ~~Model-role config — new `~/.voss/models.yml` or extend existing config surface?~~ **RESOLVED:** extend harness toml `[harness.roles.<role>] chain=[...]` (read via tomllib). Shipped.
3. ~~Preview staging — extend `Tool` trait with `stage()` vs. add a `Staged` return variant?~~ **RESOLVED (Python live path):** reused existing `DiffModal`; single `fs_edit` now routes through it (builds one Hunk, approve-before-write). No `Tool`-trait change needed — non-textual renderers skip the modal. Rust trait change deferred (Rust UI is fallback). Shipped.
4. ~~Memory bank — extend `episodic.rs` in-harness, or keep SecondBrain external and just bridge to it?~~ **RESOLVED:** keep in-harness via existing `MemoryStore` (the real durable bank); do not extend `episodic.{rs,py}` (wrong tier); do not bridge SecondBrain (external dev sidecar, wrong layer). See item 6 above. Build nothing now; if pursued, expose recall/retain as agent tools first.
