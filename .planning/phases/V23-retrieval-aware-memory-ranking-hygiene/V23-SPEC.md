# Phase V23: Retrieval-Aware Memory Ranking & Hygiene — Specification

**Created:** 2026-06-12
**Ambiguity score:** 0.154 (gate: ≤ 0.20)
**Requirements:** 8 locked (VRNK-01..08)

## Goal

`MemoryStore.recall()` gains a retrieval-quality loop — per-row retrieval telemetry feeding an optional recency×frequency rescore and retrieval-aware eviction, a default-on pre-fusion quality floor, a chroma reindex/drift gate for hand-edited mirror files, and a bounded always-inject pinned tier — with the rescore-off path byte-identical to pre-V23 behavior.

## Background

Recall today (`voss/harness/memory_store.py:411`) is hybrid BM25 + Chroma fused via RRF — structurally stronger than the froots.ai vector-only design that triggered this phase — but ranking is similarity-only:

- **No quality floor anywhere.** `_bm25_recall` drops only score ≤ 0 rows; `_chroma_recall` returns whatever is nearest regardless of distance. Low-relevance hits fill `top_k` and burn injected tokens (works against V18's token-ceiling goals).
- **No retrieval telemetry.** Nothing records that a memory was ever recalled. froots schemas `last_retrieved`/`retrieval_count` but doesn't use them; neither product ships the full loop (telemetry → rescore → eviction). Voss can.
- **Eviction is oldest-mtime-first** (`_maybe_evict`, memory_store.py:151) — a frequently-recalled old memory evicts before a never-recalled newer one.
- **Chroma-only drift.** BM25 reads mirror files directly on every recall, so hand-edits are already visible lexically; the chroma collection embeds at ingest time and silently serves stale embeddings after a hand-edit. (Narrower than the roadmap's original "mirror drift" framing — confirmed in scout.)
- **No always-present tier.** Everything competes through recall; a must-never-miss convention can simply lose the ranking.
- **CLI surface is vacuum/adopt/size only** (`voss/harness/memory_cli.py`) — no list/show, no pin verbs, telemetry would be invisible.

Consumers of `recall()`/`_rrf_merge`: `memory_recall` agent tool (tools.py:178), `voss recall` cross-corpus verb (cli.py:4793, V19), auto-injection attach sites, and V21's locked dual-store plans.

## Requirements

1. **VRNK-01 — Retrieval telemetry**: Agent-path recalls record `last_retrieved` (UTC ISO) and `retrieval_count` per returned hit locator, in a sidecar store under `.voss/memory/` — never by mutating memory files.
   - Current: No telemetry exists; recall is read-only and stateless across calls.
   - Target: `memory_recall` tool + auto-injection attach sites record telemetry for every hit returned; CLI paths (`voss recall`, `voss memory *`) do NOT record by default (no-touch). Memory file mtimes and contents are unchanged by recall (eviction ordering + git mirror stay clean). Sidecar is gitignored alongside `chroma/`.
   - Acceptance: After an agent-path recall returns hit X, the sidecar shows `retrieval_count=1` and a fresh `last_retrieved` for X; a CLI `voss recall` for the same query changes neither; X's file mtime is byte-and-mtime identical before/after.

2. **VRNK-02 — Pre-fusion quality floor (default-on)**: Each retriever applies a raw-score floor before RRF fusion; junk no longer fills `top_k`.
   - Current: BM25 keeps any score > 0 (with token-overlap rescue); chroma keeps any nearest neighbor at any distance.
   - Target: Chroma hits below a similarity floor and BM25 hits below a lexical floor are dropped pre-fusion (default values conservative, config-overridable under `[memory]`); recall may return fewer than `top_k` hits rather than pad with junk.
   - Acceptance: A query matching nothing in the store returns 0 hits (not `top_k` nearest-anything); a query with exactly 2 relevant rows in a 50-row store returns ≤ a small bounded set containing both; floor values are readable from config and a disable knob restores pre-V23 fill behavior.

3. **VRNK-03 — Recency×frequency rescore (default-off)**: Telemetry-driven boost applied to RRF output, behind a config switch defaulting off.
   - Current: Ranking is pure RRF over similarity rankings.
   - Target: With `[memory] rescore` enabled, fused scores receive a configurable recency-decay × retrieval-frequency boost; with it disabled (default), recall output is byte-identical to the pre-V23 path.
   - Acceptance: Unit test with a fixed telemetry fixture produces a deterministic, asserted re-ranking; with rescore off, recall results (order, scores, excerpts) are byte-identical to a pre-V23 baseline test; empty telemetry + rescore on = no-op (identical ordering).

4. **VRNK-04 — Retrieval-aware eviction**: Quota eviction and vacuum prefer never-retrieved and stale-retrieved rows over merely-old ones.
   - Current: `_maybe_evict` sorts by mtime only; `vacuum()` ignores retrieval history.
   - Target: Eviction order = never-retrieved oldest-first, then stale-retrieved (oldest `last_retrieved`) — frequently/recently recalled rows evict last. `decisions/` exemption unchanged. Missing sidecar degrades to current mtime ordering.
   - Acceptance: Test: over-quota source with one old-but-recently-retrieved file and one newer-never-retrieved file evicts the never-retrieved file first; with no sidecar present, ordering matches current behavior.

5. **VRNK-05 — Chroma reindex + drift gate**: `voss memory reindex [--check]` detects and repairs hand-edit drift between mirror files and the chroma collection, mirroring the `voss sync --check` contract.
   - Current: No drift detection; hand-edited memory files serve stale embeddings forever (BM25 unaffected — reads files live).
   - Target: Per-file hash manifest; `--check` exits 0 when clean, exits 1 and lists stale locators on drift; bare `reindex` re-embeds only stale/missing entries and prints the count; chroma-unavailable installs no-op with a notice and exit 0.
   - Acceptance: Hand-editing a conventions file then `--check` → exit 1 naming that locator; `reindex` → re-embedded count ≥ 1, subsequent `--check` → exit 0; with chroma not installed both verbs exit 0 with a notice.

6. **VRNK-06 — Pinned tier**: Operators can pin memories; pinned rows always inject into agent context, bounded by a token cap, without competing through recall.
   - Current: No pin concept; all memories compete via recall ranking.
   - Target: Pin flag per locator (sidecar-stored); pinned memories prepend inside the existing V18/V19 auto-injection region, non-evictable (quota eviction + vacuum skip them), capped at a config token budget (default ~500 tok); overflow keeps newest-pinned and warns. Pinned rows are also exempt from VRNK-04 eviction.
   - Acceptance: Pinned memory text appears in the assembled agent context for a query that would never recall it; pinning beyond the cap drops the oldest pin from injection with a stderr/log warning; eviction test confirms pinned files survive an over-quota purge.

7. **VRNK-07 — CLI verbs**: `voss memory pin/unpin <locator>`, `voss memory list [--source] [--pinned]`, `voss memory show <locator>` expose pins and telemetry.
   - Current: CLI group has vacuum/adopt/size only; telemetry and pins would be operator-invisible.
   - Target: `pin`/`unpin` toggle the flag (exit 1 on unknown locator); `list` prints locator, source, retrieval_count, last_retrieved, pin flag (filterable); `show` prints full text + telemetry for one locator.
   - Acceptance: pin → list --pinned shows the row → unpin → list --pinned empty; `show` on a recalled row displays nonzero retrieval_count; unknown locator exits 1 with stderr message.

8. **VRNK-08 — Regression + coherence guard**: Existing recall consumers are unbroken and the off-path is provably unchanged.
   - Current: M8/V19/V21-planned surfaces (memory_recall tool, voss recall, auto-injection, eviction tests) pass against similarity-only recall.
   - Target: Full existing memory + code_recall test suites stay green; a baseline test locks rescore-off byte-identical output; `voss recall` cross-corpus fusion (cli.py:4793) works unchanged with floors applied per-store.
   - Acceptance: `pytest tests/memory tests/harness/test_memory_*.py tests/code_recall` green; byte-identical baseline test exists and passes; no frozen-schema drift.

## Boundaries

**In scope:**
- Retrieval telemetry sidecar (agent paths only) + no-touch CLI default
- Pre-fusion quality floors (BM25 + chroma), default-on, config-overridable
- Recency×frequency rescore on RRF output, default-off, deterministic
- Retrieval-aware eviction/vacuum ordering with sidecar-absent fallback
- `voss memory reindex [--check]` chroma drift gate (hash manifest, sync-check exit contract)
- Pinned tier: sidecar flag, V18/V19-region injection, token cap, eviction exemption
- CLI verbs: pin, unpin, list, show
- Baseline byte-identical regression test for the rescore-off path

**Out of scope:**
- Graph visualization of memory — derived view, voss-app/TUI seed later; store stays flat
- Embedding model / store swap (BGE, libsql, DiskANN) — chroma works, V19 gotchas already paid
- Cloud sync / multi-device — PROJECT.md exclusion stands
- Supersession edges between memories — telemetry first; separate seed
- Auto-pinning heuristics — manual pin verb only this phase
- E-track quality eval for rescore — deferred to the flip-on proposal (rescore ships default-off; determinism + byte-identical off-path is the V23 bar)
- Code index (V19 CodeIndex) telemetry/floors — memory store only; code corpus is derived and rebuildable, different lifecycle
- forget CLI registration / full verb-set rounding — minimal list/show only

## Constraints

- **Executes after V21** — V21's locked plans (dual-store RRF, promote/forget --global) land first; V23 telemetry, floors, and pinning must then apply per-store (project + global) through the same chokepoints.
- **Memory files are immutable to telemetry** — recall must never write to memory files (mtime changes corrupt eviction ordering; mirror stays hand-editable + git-clean). All V23 state lives in sidecar files under `.voss/memory/`, gitignored like `chroma/`.
- **Rescore-off path byte-identical** — default config produces output indistinguishable from pre-V23; this is a hard regression gate, not a goal.
- **BM25-only degradation preserved** — every feature must behave sanely with chroma absent (floors apply to BM25 only; reindex no-ops exit 0; telemetry/pinning unaffected).
- **No new store substrate** — extend `MemoryStore` + existing hash-manifest/eviction/RRF machinery; no second index, no schema-substrate change.
- Pinned-tier injection rides the existing V18/V19 auto-injection region and respects its token accounting (pinned cap is part of, not additional to, context budgeting).

## Acceptance Criteria

- [ ] Agent-path recall increments `retrieval_count` + updates `last_retrieved` in the sidecar; CLI recall does not
- [ ] Memory file bytes and mtimes unchanged by any recall
- [ ] No-match query returns 0 hits with floors on; disable knob restores fill behavior
- [ ] Fixed telemetry fixture → deterministic asserted re-ranking with rescore on
- [ ] Rescore off (default) → byte-identical recall output vs pre-V23 baseline test
- [ ] Over-quota eviction removes never-retrieved file before old-but-recently-retrieved file; mtime fallback when sidecar absent
- [ ] Hand-edit → `voss memory reindex --check` exit 1 + stale locator list; `reindex` repairs; `--check` exit 0 after
- [ ] Chroma-absent: reindex/check exit 0 with notice; recall/floors/telemetry/pinning still function
- [ ] Pinned memory present in assembled agent context without recall match; survives over-quota eviction; cap overflow warns
- [ ] `voss memory pin/unpin/list/show` behave per VRNK-07 (exit 1 unknown locator)
- [ ] Existing memory + code_recall suites green; no frozen-schema drift

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                          |
|--------------------|-------|------|--------|------------------------------------------------|
| Goal Clarity       | 0.87  | 0.75 | ✓      | All 6 scope items confirmed w/ mechanics       |
| Boundary Clarity   | 0.87  | 0.70 | ✓      | After-V21 ordering locked; reindex scoped chroma-only |
| Constraint Clarity | 0.82  | 0.65 | ✓      | Sidecar immutability + byte-identical off-path |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | 11 pass/fail criteria                          |
| **Ambiguity**      | 0.154 | ≤0.20| ✓      |                                                |

## Interview Log

| Round | Perspective              | Question summary                          | Decision locked                                                        |
|-------|--------------------------|-------------------------------------------|------------------------------------------------------------------------|
| 1     | Researcher               | Ordering vs V21's locked recall plans?    | V23 executes after V21; applies per-store from day one                 |
| 1     | Researcher               | Which paths count for telemetry?          | Agent paths only (tool + auto-injection); CLI is no-touch by default   |
| 1     | Researcher               | Default posture for floor + rescore?      | Floor default-on (conservative), rescore default-off until eval        |
| 2     | Researcher               | Telemetry storage vs mtime eviction?      | Sidecar store; memory files immutable to telemetry (hard constraint)   |
| 2     | Simplifier               | Irreducible core if cut 50%?              | Keep all 6 items; reindex honestly scoped to chroma-only drift         |
| 2     | Simplifier               | Pinned tier injection site + bound?       | V18/V19 auto-injection region, non-evictable, ~500 tok cap, newest-wins overflow |
| 3     | Boundary Keeper          | Rescore verification bar?                 | Determinism fixture + byte-identical off-path; E-track eval deferred   |
| 3     | Boundary Keeper          | Drift gate contract?                      | Mirror V20 sync --check: exit 0/1 + stale list; reindex repairs stale only |
| 3     | Boundary Keeper          | CLI verb scope?                           | pin/unpin + minimal list/show w/ telemetry columns; full verb-set out  |

---

*Phase: V23-retrieval-aware-memory-ranking-hygiene*
*Spec created: 2026-06-12*
*Next step: /gsd-discuss-phase V23 — implementation decisions (sidecar format, floor values, decay formula, manifest layout)*
