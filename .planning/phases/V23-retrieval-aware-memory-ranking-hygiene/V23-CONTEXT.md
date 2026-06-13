# Phase V23: Retrieval-Aware Memory Ranking & Hygiene - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

V23 adds the retrieval-quality loop to `MemoryStore`: per-row retrieval telemetry (agent paths only, sidecar-stored) feeding an optional recency×frequency rescore and retrieval-aware eviction; a default-on pre-fusion quality floor on both retrievers; a chroma reindex/drift gate for hand-edited mirror files; a bounded always-inject pinned tier; and four CLI verbs (pin/unpin/list/show). **Reuse-not-rebuild:** extends `MemoryStore` (RRF, eviction/vacuum, tombstones, portalocker locks), the V19 hash-manifest pattern, and the V18 packer region. Rescore-off path is byte-identical to pre-V23. Executes AFTER V21 (dual-store) — all features apply per-store.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**8 requirements are locked (VRNK-01..08).** See `V23-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `V23-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):** Retrieval telemetry sidecar (agent paths only) + no-touch CLI default; pre-fusion quality floors (BM25 + chroma) default-on config-overridable; recency×frequency rescore on RRF output default-off deterministic; retrieval-aware eviction/vacuum ordering with sidecar-absent fallback; `voss memory reindex [--check]` chroma drift gate (hash manifest, sync-check exit contract); pinned tier (sidecar flag, V18/V19-region injection, token cap, eviction exemption); CLI verbs pin/unpin/list/show; baseline byte-identical regression test for the rescore-off path.

**Out of scope (from SPEC.md):** graph visualization; embedding model/store swap; cloud sync; supersession edges; auto-pinning heuristics; E-track rescore eval (deferred to flip-on proposal); V19 CodeIndex telemetry/floors (code corpus untouched); forget CLI registration / full verb-set rounding.

</spec_lock>

<decisions>
## Implementation Decisions

### Sidecar Format & Locking (USER-LOCKED)
- **D-01 — Telemetry = `.voss/memory/.retrieval.jsonl` append-log:** one event per agent-recall hit; vacuum compacts events into per-locator counts. Matches the `.tombstones.jsonl` pattern; corrupt-line tolerant; gitignored (extend `_VOSS_MEMORY_GITIGNORE`).
- **D-02 — Pins = separate `.voss/memory/.pins.json`, COMMITTED:** pins are operator curation (like decisions) — git history + survive clones. Telemetry is high-churn local state and stays ignored. Different lifecycles, different files. Do NOT add `.pins.json` to the gitignore.
- **D-03 — Sync append, skip-on-contention:** telemetry appends at recall return under non-blocking portalocker (existing `_lock` pattern); on contention, drop the event — one lost increment is harmless. No deferred-batch machinery.

### Floor Mechanics (USER-LOCKED)
- **D-04 — Chroma floor = absolute similarity, default 0.25:** drop hits with `(1 − distance) < 0.25`; config `[memory] chroma_floor`. Conservative (froots ships 0.45 — judged too aggressive for local sentence-transformer spaces).
- **D-05 — BM25 floor = relative-to-top, default ratio 0.1:** keep hits ≥ 10% of this query's top BM25 score; config `[memory] bm25_floor_ratio`. Absolute floors don't transfer across corpus sizes. Must preserve the tiny-corpus token-overlap rescue path (memory_store.py:555) — relative form does so naturally.
- **D-06 — Floors apply per-retriever per-store, PRE-fusion only:** each store's BM25/chroma floors its own ranking before RRF; no post-fusion drop (a fused-output floor would punish BM25-only degraded installs). Code corpus (V19 CodeIndex) untouched per SPEC.

### Pinned Injection Mechanics (USER-LOCKED)
- **D-07 — Pinned block = non-evictable allocator item:** enters the V18 variable region as a fixed-cost item the packer places first and may never digest/fold/evict; its cap counts inside the existing ceiling (honest accounting, no new region type). NOT the stable region — stable region is FOLD-only (V18 gotcha).
- **D-08 — Full text, per-item soft cap ~200 tok:** inject the whole memory body per pin, soft-capped per item, under the ~500 tok tier cap. No Hit-style 200-char excerpts — truncation defeats curated pins.
- **D-09 — Global pins: project priority on overflow:** post-V21 both stores' pins inject, labeled `[global]` like recall hits; when combined size exceeds the cap, project pins win, then newest-global.

### Reindex Manifest Scope (USER-LOCKED)
- **D-10 — Drift gate covers file-based sources only:** notes/decisions/conventions (the hand-edit surface). turns/ledgers excluded — append-only machine-written JSONL, no real drift vector.
- **D-11 — Manifest = `.voss/memory/.reindex-manifest.json`, gitignored:** sha256 per relative file path, V19 CodeIndex manifest pattern. Derived artifact; missing manifest ⇒ everything stale (first run rebuilds).
- **D-12 — Global store via `--global` flag, project default:** matches V21's `vacuum --global` / `forget --global` verb convention; each store owns its manifest.

### Claude's Discretion (planner/researcher may pick within SPEC constraints)
- **D-13 — Rescore formula shape:** multiplicative boost on RRF score from exponential recency decay (e.g. ~7-day half-life) + log-scaled frequency, both weight-configurable, boost bounded so similarity ordering dominates; exact formula = planner. Hard constraints from SPEC: deterministic under fixture, empty-telemetry = no-op, off = byte-identical.
- **D-14 — `voss memory list/show` output format:** table layout, column set beyond SPEC minimum (locator, source, retrieval_count, last_retrieved, pin flag), optional `--json`. Follow existing CLI output conventions.
- **D-15 — Eviction tie-breaks:** ordering within the never-retrieved and stale-retrieved buckets (mtime ascending is the natural default); how vacuum compaction folds `.retrieval.jsonl` events (count summation + max timestamp).
- **D-16 — Telemetry event schema:** minimal JSONL line (locator, ts; maybe session_id). Vacuum compaction format = planner.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract
- `.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-SPEC.md` — Locked requirements VRNK-01..08 — MUST read before planning
- `.planning/ROADMAP.md` — Phase V23 entry (goal, provisional plan/wave shape)

### Implementation substrate
- `voss/harness/memory_store.py` — MemoryStore: `recall()` L411, `_rrf_merge` L431, `_chroma_recall` L447, `_bm25_recall` L530 (token-overlap rescue L555), `_maybe_evict` L151, `vacuum()` L720, tombstones, portalocker `_lock` L134, `_VOSS_MEMORY_GITIGNORE` L36
- `voss/harness/memory_cli.py` — existing `voss memory` click group (vacuum/adopt/size) — pin/unpin/list/show/reindex register here
- `voss/harness/tools.py` L163-214 — `memory_recall` agent tool (telemetry-recording path)
- `voss/harness/cli.py` L4793 — `voss recall` cross-corpus fusion (no-touch path; floors apply per-store upstream)

### Upstream phase contracts (consumed)
- `.planning/phases/V21-global-cross-project-memory/V21-CONTEXT.md` — D-04 layout mirror (same MemoryStore code ⇒ sidecars per-store), D-13 portalocker cross-session, `--global` verb convention, `make_id` locator format
- `.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-CONTEXT.md` + `V19-SPEC.md` — hash-manifest pattern, V18-region injection precedent (≤1000 tok, off-switch)
- `.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-CONTEXT.md` — packer architecture, stable-region-is-FOLD-only constraint, byte-identical escape-hatch precedent

### Origin
- froots.ai/memory teardown (2026-06-12, conversation) — competitive trigger; no doc artifact beyond ROADMAP entry

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MemoryStore._lock` (portalocker, non-blocking, skip-on-contention) — exact pattern for telemetry append guard
- `.tombstones.jsonl` lifecycle (append + vacuum compaction + gitignore entry) — template for `.retrieval.jsonl`
- `_rrf_merge` static + rank-based — floors slot in BEFORE it, untouched fusion
- V19 CodeIndex hash manifest — template for `.reindex-manifest.json`
- `make_id` composite IDs (`<source>:<locator>[:<seq>]`) — locator vocabulary for pins/telemetry/CLI verbs

### Established Patterns
- BM25 reads mirror files live on every recall ⇒ drift is chroma-embeddings-only; reindex re-embeds, never touches BM25
- Eviction sorts by mtime ⇒ telemetry must never mutate memory files (SPEC constraint; sidecar-only writes)
- `decisions/` is eviction-exempt (M8-06 Warning 5) — pinned rows join that exemption
- Chroma optional (`voss[search]`); every V23 feature needs a BM25-only degradation story
- V21 `--global` flag convention for store targeting

### Integration Points
- `recall()` return path in `tools.py` `memory_recall` + auto-injection attach sites — telemetry record point (agent paths only)
- `_chroma_recall` / `_bm25_recall` tails — floor application points
- `_rrf_merge` output in `recall()` — rescore hook (config-gated)
- `_maybe_evict` file-sort + `vacuum()` — retrieval-aware ordering + pin exemption
- V18 allocator — pinned block as non-evictable item
- `memory_cli.py` click group — five new verbs

</code_context>

<specifics>
## Specific Ideas

- froots teardown framing: "their schema admits retrieval metadata matters; neither product ships the ranking loop — Voss ships the full loop (telemetry → rescore → eviction)"
- froots' 0.45 cosine floor explicitly rejected as too aggressive; 0.25 conservative default chosen
- `--check` exit contract deliberately mirrors `voss sync --check` (V20-01) for operator consistency

</specifics>

<deferred>
## Deferred Ideas

- Graph visualization of memory (similarity + category-overlap edges, derived view, flat store) — voss-app/TUI seed, post-V23
- Supersession edges between memories — separate seed after telemetry exists
- E-track quality eval gating a rescore default-ON flip — proposal after V23 ships + telemetry accumulates
- Auto-pinning heuristics — manual verb only this phase

</deferred>

---

*Phase: V23-retrieval-aware-memory-ranking-hygiene*
*Context gathered: 2026-06-12*
