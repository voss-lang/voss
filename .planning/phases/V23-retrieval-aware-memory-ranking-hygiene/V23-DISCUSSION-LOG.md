# Phase V23: Retrieval-Aware Memory Ranking & Hygiene - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** V23-retrieval-aware-memory-ranking-hygiene
**Areas discussed:** Sidecar format & locking, Floor mechanics, Pinned injection mechanics, Reindex manifest scope

---

## Sidecar Format & Locking

| Option | Description | Selected |
|--------|-------------|----------|
| JSONL append-log | `.retrieval.jsonl`, one event per recall hit, vacuum-compacted; tombstones pattern | ✓ |
| Single JSON map | `{locator → {count, last}}` rewritten per recall; racy under V21 cross-session | |
| SQLite sidecar | Atomic upserts but new substrate (SPEC arguably forbids) | |

| Option | Description | Selected |
|--------|-------------|----------|
| Separate .pins.json, committed | Curation signal — git history, survives clones; telemetry stays ignored | ✓ |
| Separate .pins.json, gitignored | Local operator preference only | |
| One sidecar for both | Mixes committed-worthy curation into ignored churn log | |

| Option | Description | Selected |
|--------|-------------|----------|
| Sync append, skip-on-contention | Non-blocking portalocker at recall return; dropped event harmless | ✓ |
| Deferred batch | No hot-path I/O but crash loses batch + flush plumbing | |

**User's choice:** All recommended options.

---

## Floor Mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Absolute similarity ~0.25 | Conservative, config `chroma_floor`; kills only true junk | ✓ |
| Match froots 0.45 | Aggressive; risks starving recall on local sentence-transformers | |
| Relative to top hit | Adapts per-query but junk-only sets keep best junk | |

| Option | Description | Selected |
|--------|-------------|----------|
| Relative-to-top ratio ~0.1 | Robust across corpus sizes; preserves tiny-corpus rescue | ✓ |
| Min token-overlap count | Interpretable but N hard to default | |
| Absolute score floor | Breaks across corpus sizes | |

| Option | Description | Selected |
|--------|-------------|----------|
| Per-retriever per-store, pre-fusion | RRF fuses already-floored lists; code corpus untouched | ✓ |
| Also floor fused output | Punishes BM25-only degraded installs | |

**User's choice:** All recommended options.

---

## Pinned Injection Mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Non-evictable allocator item | Fixed-cost item in V18 variable region, counted in ceiling | ✓ |
| Outside packer, own budget | Simpler but escapes V18 accounting | |

| Option | Description | Selected |
|--------|-------------|----------|
| Full text, ~200 tok per-item soft cap | Pins are curated; truncation defeats purpose | ✓ |
| Excerpt only | 200-char Hit excerpts; conventions rarely survive truncation | |

| Option | Description | Selected |
|--------|-------------|----------|
| Project priority on overflow | Both stores inject, `[global]` labels; project wins, then newest-global | ✓ |
| Separate caps | More config surface | |
| Project pins only this phase | Defers global wiring | |

**User's choice:** All recommended options.

---

## Reindex Manifest Scope

| Option | Description | Selected |
|--------|-------------|----------|
| File-based sources only | notes/decisions/conventions — the hand-edit surface | ✓ |
| All five sources | Hashes turns/ledgers; protects a non-existent editing pattern | |

| Option | Description | Selected |
|--------|-------------|----------|
| .reindex-manifest.json, gitignored | sha256 per path, V19 pattern; missing = all stale | ✓ |
| Inside chroma metadata | Requires chroma present — weakens BM25-only degradation | |

| Option | Description | Selected |
|--------|-------------|----------|
| --global flag, project default | Matches V21 vacuum/forget --global convention | ✓ |
| Both stores always | Breaks convention, slows common case | |

**User's choice:** All recommended options.

---

## Claude's Discretion

- Rescore formula shape (exponential recency decay + log frequency, bounded boost) — D-13
- `voss memory list/show` output format + optional `--json` — D-14
- Eviction tie-breaks within buckets; vacuum compaction of telemetry events — D-15
- Telemetry event JSONL schema — D-16

## Deferred Ideas

- Graph visualization of memory (voss-app/TUI seed)
- Supersession edges between memories
- E-track eval gating rescore default-ON flip
- Auto-pinning heuristics
