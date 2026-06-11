# Phase V19: Semantic Code Memory + Tiered Index Routing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** V19-semantic-code-memory-tiered-index-routing
**Areas discussed:** CLI verb naming + output UX, Embedding model default, Cheap-tier default for index_enrich, Reindex trigger policy
**Mode:** default interactive, SPEC-locked (8 requirements); CONTEXT.md pre-existed (direct-from-SPEC draft) — user chose "Update it"

---

## CLI verb naming + output UX

| Option | Description | Selected |
|--------|-------------|----------|
| `voss code recall <q>` (recommended) | New `voss code` click group mirroring `voss memory` precedent; room for status/refresh | |
| `voss recall <q>` top-level | Shortest; 'recall' collides conceptually with memory recall | ✓ |
| `voss search <q>` top-level | Most intuitive word; grep-expectation mismatch risk | |

**Follow-up — corpus for `voss recall`:**

| Option | Description | Selected |
|--------|-------------|----------|
| Code only (recommended) | Matches SPEC D-05 separation | |
| Unified: code + memory | One verb, RRF across corpora, source-labeled hits; required VSEM-05 amendment | ✓ |
| Code default, `--memory` flag | Middle ground, no score mixing | |

**User's choice:** `voss recall`, unified corpus.
**Notes:** Collision concern resolved by embracing it — one "ask the repo anything" verb. Cross-corpus RRF accepted as legitimate (rank-based fusion). SPEC VSEM-05 amended same session; agent tool `code_recall` stays code-only.

**Display format:**

| Option | Description | Selected |
|--------|-------------|----------|
| file:line + score + excerpt (recommended) | Block per hit, grep -n mental model | ✓ |
| Compact table | Densest, excerpt behind --verbose | |
| Excerpt-first cards | Search-results feel, more lines | |

---

## Embedding model default

| Option | Description | Selected |
|--------|-------------|----------|
| all-MiniLM-L6-v2 (recommended) | Existing chroma/sentence-transformers default path, 80MB, 384-dim, fast CPU | ✓ |
| BAAI/bge-small-en-v1.5 | Better benchmarks, similar size, not code-tuned | |
| jinaai/jina-embeddings-v2-base-code | Code-tuned, best quality, heavier | |
| Match existing default_embedding_model | Zero new decisions | |

**User's choice:** all-MiniLM-L6-v2.
**Notes:** Golden-query gate is the measuring instrument; swap later via config if gate shows weakness.

---

## Cheap-tier default for index_enrich

| Option | Description | Selected |
|--------|-------------|----------|
| Ollama-local first, documented (recommended) | gpt-oss/qwen-coder class, $0, private; API tier as alternate snippet | ✓ |
| Haiku-class API default | Better quality, costs $, cap protects | |
| No documented default | Pure config, least docs | |

**Enrichment unit:**

| Option | Description | Selected |
|--------|-------------|----------|
| Per-chunk one-liner (recommended) | Highest retrieval lift per token, parallelizable | ✓ |
| Per-file summary | Fewer calls, coarser | |
| Per-symbol description | Tightest, most calls, overlaps per-chunk | |

**User's choice:** Ollama-local documented default; per-chunk one-liners.
**Notes:** Matches user's original GPT-OSS framing from seed capture. Profile remains OFF by default per VSEM-07.

---

## Reindex trigger policy

| Option | Description | Selected |
|--------|-------------|----------|
| Session-start + post-write + verb (recommended) | Background sweep + fs_write/fs_edit hook + explicit refresh | ✓ |
| Session-start + verb only | Simplest; mid-session agent edits stale | |
| Lazy on every recall | Always fresh; threatens p95 <500ms | |

**User's choice:** Three triggers — session-start sweep, post-write targeted re-hash, explicit refresh verb.
**Notes:** No watch daemon (M14 owns watch).

---

## Deferred Ideas

None raised — no scope creep this discussion.

## Claude's Discretion

D-01..D-08 from the direct-from-SPEC draft remain discretion defaults (module placement, chunk boundaries, manifest format, worker mechanics, BM25 corpus build, router fail-closed, injection selection, golden-gate harness shape). Planner may revisit within SPEC bounds.
