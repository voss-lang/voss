# Phase V19: Semantic Code Memory + Tiered Index Routing — Research

**Researched:** 2026-06-11
**Domain:** Python / Chroma vector index / sentence-transformers / BM25 RRF / Click CLI
**Confidence:** HIGH (all key claims verified against live codebase and installed packages)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-09 — CLI verb = `voss recall <q>`, unified corpus:** top-level verb (not a `voss code` group), queries code index AND memory store, RRF-fused across corpora, every hit labeled `[code]`/`[memory]`. `--json` schema includes `source` field. SPEC VSEM-05 amended accordingly. Agent tool `code_recall` remains code-only.
- **D-10 — Default hit display:** one block per hit — clickable `path:line` header, score, 2–3 line excerpt. Table/card formats not in v1.
- **D-11 — Embedding default = `all-MiniLM-L6-v2`:** existing sentence-transformers default path in `semantic.py`; 384-dim, 256-token max sequence length. Swap is config knob.
- **D-12 — Cheap tier documented default = Ollama-local:** docs + example config point `index_enrich` at an Ollama-served small model; Haiku-class API shown as alternate. Profile OFF by default. Fail-closed without config (D-06).
- **D-13 — Reindex triggers (three):** (1) background hash-sweep at session start; (2) targeted re-hash on agent file mutation — hook `fs_write`/`fs_edit` tool paths; (3) explicit refresh verb (`voss recall --refresh` or equivalent). No watch daemon; no per-recall sweep.

### Claude's Discretion

- **D-01 — Module placement:** `CodeIndex` in `voss/harness/code/semantic_index.py`, reusing `voss_runtime/memory/semantic.py` for the Chroma client.
- **D-02 — Chunk boundaries:** M10 `symbols` table start lines sorted per file; chunk = [symbol start, next symbol start); preamble = chunk 0. Oversize chunks split at max-token threshold.
- **D-03 — Manifest:** JSON at `.voss-cache/code/semantic-manifest.json`.
- **D-04 — Background worker:** daemon thread spawned lazily on first session; sentence-transformers import + model load inside worker.
- **D-05 — BM25 corpus for code_recall:** build lexical side from same chunk set, reuse `_bm25_tokenize`.
- **D-06 — Router role mechanics:** `index_enrich` resolves via named role key in config (`[models] index_enrich = "..."`); absent config → enrichment unavailable; fail closed.
- **D-07 — Injection selection:** query = current task goal text, top-k chunks under 1000-token cap, formatted as `## Code Recall` section.
- **D-08 — Golden query gate:** `tests/code_recall/test_golden_queries.py`, ~10–15 (query, expected_file) pairs against the Voss repo.

### Deferred Ideas (OUT OF SCOPE)

- voss-app/TUI recall panel (A-track follow-up consuming VSEM-05 JSON)
- Repo docs/markdown or `.planning/` corpus
- Global cross-project memory layer
- Code-tuned embedding API models as default
- E-track eval cell for retrieval quality
- File-watch-driven reindex (M14 owns watch)
- Modifying M10 lexical/structural search, LSP surfaces, or SQLite index schema
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VSEM-01 | `CodeIndex` derived cache: Chroma `voss_code` collection over symbol-aware chunks under `.voss-cache/`, content-hash manifest | Verified: Chroma 1.5.9 `PersistentClient` + `get_or_create_collection` + `upsert` API confirmed live |
| VSEM-02 | Incremental reindex: hash-unchanged files produce zero embedding calls; changed-file batch <2s per batch | Verified: `delete(ids=[...])` + `upsert` API confirmed; manifest tracks path→hash→chunk_ids |
| VSEM-03 | Background non-blocking build: session start usable immediately; recall degrades gracefully until ready | Verified: daemon thread pattern safe with same-client concurrent access (tested) |
| VSEM-04 | `code_recall` harness tool: RRF-fused (BM25 + vector, k=60), file:line locators, Chroma-absent BM25-only, p95 <500ms | Verified: `_rrf_merge` reusable; `attach_memory_tools` pattern confirmed at `tools.py:159` |
| VSEM-05 | CLI `voss recall <q>`: queries both corpora, RRF-fused, `[code]`/`[memory]` labeled, `--json` with `source` field | Verified: `register()` / `AGENT_COMMANDS` tuple / `cli.py:4597` is the seam |
| VSEM-06 | Auto-injection ≤1000 tokens inside V18 variable region, evictable, off-switch | Verified: `_compose_system_blocks` at `agent.py:372` is the injection seam; `project_index_text` slot exists |
| VSEM-07 | `index_enrich` router role; profile OFF by default; zero LLM calls when off | Verified: `[model_tiers]` section in config.toml + `get_model_tiers()` is the extension pattern |
| VSEM-08 | Enrichment cost guardrails: `enrich_budget_tokens` cap, ledger line, `/cost` visibility | Verified: `_append_savings_record` at `recorder.py:143` is the write surface; row format known |
</phase_requirements>

---

## Summary

V19 wires a **derived Chroma vector index over M10-discovered code** (`voss/harness/code/semantic_index.py`) that lives beside the existing SQLite symbol index at `.voss-cache/code/`. Chunk boundaries come directly from the M10 `symbols` table (sorted start lines per file; chunk = [symbol_start_line, next_symbol_start_line)); for files with zero symbols a single whole-file chunk is used; for oversize chunks, split at ~512 characters (covering the 256-token MiniLM window at ~2 chars/token). First build runs in a daemon thread; no session call blocks on it. Recall degrades to BM25-only when Chroma is absent.

The F2 `_rrf_merge` static method (in `memory_store.py:426`) is directly reusable for both the `code_recall` agent tool (code-corpus only) and the `voss recall` CLI verb (cross-corpus fusion) because RRF merges ranked lists, not corpus internals. The `Hit` dataclass (source, locator, score, excerpt) must be extended or paralleled with code-chunk fields (file path, line range) — the cleanest approach is adding `line_start: int | None = None` and `line_end: int | None = None` optional fields to `Hit`, since it is already used in `memory_store.py` and is a plain dataclass.

The V18 injection seam is `_compose_system_blocks()` in `agent.py:372`, which takes named text parameters and filters out empty strings. Adding a `code_recall_text: str = ""` parameter (parallel to `project_index_text`) is the correct surgical incision. The V18 ledger seam is `_append_savings_record()` in `recorder.py:143`; V19 enrichment spend is a new row type (different `method` field) appended via the same function. The `[model_tiers]` section in `config.toml` + `get_model_tiers()` / `_parse_model_tiers_section()` in `config.py:233` is the template for `index_enrich` — add it as a new named role key in a new `[models]` config section or extend `[model_tiers]`.

**Primary recommendation:** Build `voss/harness/code/semantic_index.py` as a thin orchestrator over the existing `SemanticMemory` wrapper; spawn a daemon thread in `CodeIntelService.for_cwd()` or a lazy property on a new `CodeIndexService`; wire `code_recall` into `attach_memory_tools` (or a parallel `attach_code_recall_tool` call at the same `do_cmd`/`chat_cmd` sites); register `voss recall` in `AGENT_COMMANDS` tuple via a new `recall_cmd` click command.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CodeIndex build + manifest | `voss/harness/code/semantic_index.py` | `.voss-cache/code/` (disk) | Derived cache beside M10 SQLite — same tier as `index.py` |
| Chunk extraction from M10 SQLite | `CodeIndex.build()` | M10 `symbols` table (read-only) | V19 reads M10 data; never writes to M10 tables |
| Embedding function selection | `SemanticMemory._embedding_function()` (reused) | `voss_runtime/memory/semantic.py` | Already owns embedding selection; do not duplicate |
| Background worker / daemon thread | `CodeIndexService` (new) in `code/` | `threading.Thread(daemon=True)` | Same lazy-init spirit as `_maybe_chroma()` in `memory_store.py` |
| BM25 lexical side for `code_recall` | `CodeIndex` (inline BM25) | Reuse `_bm25_tokenize` from `memory_store.py` | Like-for-like corpus so RRF compares comparable ranked lists |
| RRF fusion (tool level) | `MemoryStore._rrf_merge` (reused, static) | `code_recall` tool handler | Static method, corpus-agnostic, reuse without subclassing |
| `code_recall` agent tool | `voss/harness/tools.py` (attach call) | `voss/harness/code/semantic_index.py` | Pattern identical to `attach_memory_tools`; use `attach_code_recall_tool` |
| `voss recall` CLI verb | `voss/harness/cli.py` → `AGENT_COMMANDS` | `memory_store.py` + `CodeIndex` | New `recall_cmd` click command, registered alongside `do_cmd` etc. |
| V18 injection (≤1000 tok) | `agent.py:_compose_system_blocks()` | `cli.py:do_cmd` / `chat_cmd` | Parallel to `project_index_text`; new `code_recall_text` param |
| V18 savings ledger (enrichment line) | `recorder.py:_append_savings_record()` | session dir `token-savings.jsonl` | Reuse exact write path; add distinct `method="enrich"` row |
| `index_enrich` model role | `voss/harness/config.py` (new `[code_recall]` section) | `model_router.py:build_provider_for_model` | Extend `[model_tiers]` parse pattern; new role key |
| Enrichment dispatch + budget cap | `CodeIndex._run_enrichment()` | `model_router.resolve_key` | Fail-closed on absent config; cap = `enrich_budget_tokens` |
| Golden query CI gate | `tests/code_recall/test_golden_queries.py` | fixture subset of Voss repo files | Deterministic pytest, no network, behind `@pytest.mark.slow` |

---

## Standard Stack

### Core (all pre-installed in `voss[search]`)

| Library | Version (verified) | Purpose | Why Standard |
|---------|-------------------|---------|--------------|
| `chromadb` | 1.5.9 [VERIFIED: .venv] | Chroma vector collection `voss_code` + PersistentClient | Already the memory store backend; `SemanticMemory` wraps it |
| `sentence-transformers` | 5.5.0 [VERIFIED: .venv] | `all-MiniLM-L6-v2` embedding (384-dim, 256 token window) | Already the default in `semantic.py._embedding_function()` |
| `rank-bm25` | (installed in venv) | BM25 lexical side for `code_recall` | Already used in `memory_store.py`; `BM25Okapi` |
| `sqlite3` | stdlib | Read M10 `symbols` table | M10 already writes to `.voss-cache/code/index.db` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `threading` | stdlib | Daemon background index thread | Background build without asyncio complexity |
| `hashlib` | stdlib | sha256 content hash for manifest | Same hash family used by M10 `build_index()` |
| `portalocker` | installed | Lock file during index write | If write-while-query race is detected; low priority initially |

### No New Dependencies Required

V19 adds zero new pip dependencies. All required libraries are already in `voss[search]`. The `index_enrich` path uses `LiteLLMProvider` which is already in core.

---

## Package Legitimacy Audit

No new packages are installed by this phase. All dependencies (`chromadb`, `sentence-transformers`, `rank-bm25`) are existing `voss[search]` extra dependencies already present in the venv.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none
**Slopcheck run:** SKIPPED — no new packages being added.

---

## Architecture Patterns

### System Architecture Diagram

```
[session start]
      │
      ▼
CodeIndexService.ensure_background_build()
      │
      ├─ index ready? ──YES──► ready_event.set()
      │
      └─ NO ──► Thread(daemon=True, target=_build_loop)
                      │
                      ▼
                CodeIndex.build(cwd)
                  │
                  ├─ read M10 symbols table (SQLite, read-only)
                  ├─ discover files (M10 _discover_files pattern)
                  ├─ diff vs semantic-manifest.json (hash check)
                  ├─ skip unchanged files (zero embeds)
                  ├─ [if changed] slice chunks from file content
                  ├─ batch upsert to voss_code (Chroma PersistentClient)
                  ├─ [if enrich_profile=ON] → index_enrich model role → summaries
                  └─ write semantic-manifest.json
                      │
                      ▼
               ready_event.set()

[agent turn / code_recall tool call]
      │
      ├─ index ready? → RRF(BM25_chunks + Chroma_query) → top-k Hit[]
      └─ NOT ready  → BM25_chunks only (degraded, source="code[degraded]")

[voss recall <query>]
      │
      ├─ code hits   ← CodeIndex.query(query, k=top_k*3)  [code corpus]
      ├─ memory hits ← MemoryStore.recall(query, top_k=top_k*3)
      └─ _rrf_merge([code_hits, memory_hits], top_k=top_k)
               │
               └─ stdout: "[code] path:line  score  excerpt"
                          "[memory] locator  score  excerpt"

[do_cmd / chat_cmd — V18 injection seam]
      │
      ├─ _render_code_recall_text(cwd, task_text)  ← top-k, ≤1000 tok
      └─ _compose_system_blocks(... code_recall_text=...) → system context
```

### Recommended Project Structure

```
voss/harness/code/
├── index.py             # M10 SQLite index (unchanged)
├── service.py           # CodeIntelService (add _maybe_semantic_index lazy prop)
├── semantic_index.py    # NEW — CodeIndex + CodeIndexService + chunker
├── context.py           # render_project_index_section (unchanged)
└── models.py            # CodeLocation, IndexSummary (possibly extend Hit)

tests/
└── code_recall/
    ├── __init__.py
    ├── conftest.py              # fake embedding function fixture
    ├── test_chunker.py          # VSEM-01 chunk boundary tests
    ├── test_incremental.py      # VSEM-02 hash manifest tests
    ├── test_background.py       # VSEM-03 non-blocking build tests
    ├── test_code_recall_tool.py # VSEM-04 tool registration + degradation
    ├── test_recall_cli.py       # VSEM-05 CLI exit 0 + --json schema
    ├── test_injection.py        # VSEM-06 token cap + evictability
    ├── test_enrichment.py       # VSEM-07/08 profile on/off + ledger
    └── test_golden_queries.py   # VSEM-08 golden concept-query gate
```

### Pattern 1: CodeIndex — Chroma PersistentClient Reuse

**What:** Instantiate `SemanticMemory` with collection `voss_code` at `.voss-cache/code/chroma/` — reuse `_embedding_function()` selection, which falls back to MiniLM when no OpenAI key.
**When to use:** Everywhere in `semantic_index.py`.
**Example:**
```python
# Source: voss_runtime/memory/semantic.py (existing pattern)
from voss_runtime.memory.semantic import SemanticMemory

class CodeIndex:
    def __init__(self, cwd: Path):
        self._cwd = cwd
        self._sem: SemanticMemory | None = None  # lazy, same as _maybe_chroma()
        self._unavailable = False

    def _maybe_semantic(self) -> SemanticMemory | None:
        if self._sem is not None:
            return self._sem
        if self._unavailable:
            return None
        try:
            self._sem = SemanticMemory(
                persist_dir=str(self._cwd / ".voss-cache" / "code" / "chroma"),
                collection_name="voss_code",
            )
        except (ModuleNotFoundError, ImportError):
            self._unavailable = True
            return None
        except Exception as exc:
            print(f"code index: chroma init failed ({exc}); BM25-only", file=sys.stderr)
            self._unavailable = True
            return None
        return self._sem
```
[VERIFIED: codebase — mirrors `memory_store.py:108-126`]

### Pattern 2: Incremental Reindex via Delete-by-id + Upsert

**What:** On changed files, delete old chunk ids from Chroma by id list, then upsert new chunks. On unchanged files, skip entirely — zero embedding calls.
**When to use:** Every reindex pass after first build.
**Example:**
```python
# Source: chromadb 1.5.9 verified API
manifest = self._load_manifest()
for path, content_hash, chunks in new_chunks:
    if manifest.get(str(path), {}).get("hash") == content_hash:
        continue  # unchanged — zero embeds
    old_ids = manifest.get(str(path), {}).get("chunk_ids", [])
    if old_ids:
        sem._collection.delete(ids=old_ids)  # delete stale chunks
    sem._collection.upsert(documents=texts, ids=chunk_ids, metadatas=metas)
    manifest[str(path)] = {"hash": content_hash, "chunk_ids": chunk_ids}
```
[VERIFIED: chromadb 1.5.9 — `delete(ids=[...])` and `upsert(...)` confirmed working]

### Pattern 3: Chunk IDs Following D-04 Convention

**What:** Chunk ids use the composite format `code:<relative_path>:<seq:03d>` to parallel `memory_store.make_id("turn", ...)`.
**Example:**
```python
def _chunk_id(rel_path: str, seq: int) -> str:
    return f"code:{rel_path}:{seq:03d}"
```
[VERIFIED: codebase — `memory_store.py:56-61` D-04 convention]

### Pattern 4: Daemon Background Thread

**What:** Daemon thread spawned lazily in `CodeIndexService` after M10 index build. sentinel `threading.Event` tracks readiness. Session callers poll `is_ready()` before invoking Chroma query.
**Example:**
```python
# Source: mirrors _maybe_chroma() lazy-init spirit
import threading

class CodeIndexService:
    def __init__(self, cwd: Path):
        self._code_index = CodeIndex(cwd)
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None

    def ensure_background_build(self) -> None:
        if self._thread is not None:
            return
        t = threading.Thread(target=self._build_loop, daemon=True)
        self._thread = t
        t.start()

    def _build_loop(self) -> None:
        try:
            self._code_index.build()  # may take 30-120s on cold start
        except Exception as exc:
            print(f"code index build failed: {exc}", file=sys.stderr)
        finally:
            self._ready.set()  # always signal ready (degraded if failed)

    def is_ready(self) -> bool:
        return self._ready.is_set()
```
[ASSUMED — daemon thread pattern; chromadb same-client thread safety verified]

### Pattern 5: RRF Reuse for Cross-Corpus CLI

**What:** `MemoryStore._rrf_merge` is a static method that takes `list[list[Hit]]`. For the CLI verb, call both `code_index.query(...)` and `memory_store.recall(...)`, set the `source` field of code hits to `"code"`, then pass both lists to `_rrf_merge`.
**Example:**
```python
# Source: memory_store.py:426 (static, reusable)
code_hits = code_index.query(query, top_k=top_k * 3)   # source="code"
mem_hits = store.recall(query, top_k=top_k * 3)          # source="turn"/"note"/etc.
fused = MemoryStore._rrf_merge([code_hits, mem_hits], top_k=top_k)
```
[VERIFIED: codebase — `_rrf_merge` is `@staticmethod`, takes `list[list[Hit]]`]

### Pattern 6: V18 Injection Seam

**What:** `_compose_system_blocks()` in `agent.py:372` accepts named keyword arguments, filters empty strings. Add `code_recall_text: str = ""` parameter and include it in the tuple. Pass it from `run_turn()` signature down from `do_cmd` (parallel to `project_index_text`).
**Example:**
```python
# Source: agent.py:372-404 (exact seam)
def _compose_system_blocks(
    *,
    voss_md_block: str,
    cognition_text: str,
    principles_text: str = "",
    project_index_text: str = "",
    code_recall_text: str = "",      # NEW V19 parameter
    prior_context_text: str,
    loop_system: str,
) -> list[dict]:
    blocks = [
        {"type": "text", "text": text}
        for text in (
            voss_md_block,
            cognition_text,
            principles_text,
            project_index_text,
            code_recall_text,        # inserted after project_index
            prior_context_text,
            loop_system,
        )
        if text
    ]
    ...
```
[VERIFIED: codebase — `agent.py:372-404`]

### Pattern 7: `index_enrich` Model Role via `[model_tiers]` Extension

**What:** The `[model_tiers]` section + `get_model_tiers()` / `_parse_model_tiers_section()` in `config.py` is the template for named model roles. Add a `[code_recall]` section (or extend `[model_tiers]` with an `index_enrich` key) and a `get_index_enrich_model()` accessor. Build the enrichment provider via `find_entry()` + `build_provider_for_model()` from `model_router.py`.
**When to use:** When `enrich_profile = true` is set in config and `index_enrich` model is configured.
**Fail-closed rule:** If `[code_recall] index_enrich` is not set, the enrichment profile is silently disabled even if `enrich_profile = true` — never fall back to the session model.
[VERIFIED: codebase — `config.py:222-258`, `model_router.py:102-116`]

### Pattern 8: V18 Ledger Row for Enrichment Spend

**What:** `_append_savings_record()` in `recorder.py:143` writes a JSONL row to `.voss/sessions/<id>/token-savings.jsonl`. Enrichment spend is a new row type appended via the same function.
**Example:**
```python
# Source: recorder.py:143 (exact function)
from voss.harness.recorder import _append_savings_record

_append_savings_record(cwd, session_id, {
    "iter": 0,                      # enrichment is index-time, not iter-time
    "original_tokens_est": chunks_count * avg_chunk_tokens,
    "packed_tokens_est": 0,
    "method": "enrich",             # distinguishes from "FOLD"/"DIGEST"
    "enrichment_tokens_used": total_enrich_tokens,
    "enrichment_chunks": enriched_count,
    "saved_usd_est": None,          # no savings claim; cost line only
    "model": enrich_model_id,
    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
})
```
[VERIFIED: codebase — `recorder.py:143-161`]

### Pattern 9: Click Command Registration

**What:** New `recall_cmd` is a `@click.command("recall")` added to `AGENT_COMMANDS` tuple in `cli.py:4558`. Alternatively, since `recall` is a top-level `voss` verb, it could register directly in `voss/cli.py` via `_register_agent_commands(main)` — the same path all other agent commands take.
**Example:**
```python
# In voss/harness/cli.py — add to AGENT_COMMANDS tuple
AGENT_COMMANDS = (
    ...,
    recall_cmd,   # new: voss recall <query> [--json] [--refresh] [--top N]
)

@click.command("recall")
@click.argument("query", nargs=-1, required=False)
@click.option("--json", "json_out", is_flag=True)
@click.option("--top", "top_k", default=10, type=int)
@click.option("--refresh", "do_refresh", is_flag=True)
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def recall_cmd(query, json_out, top_k, do_refresh, cwd_str):
    ...
```
[VERIFIED: codebase — `cli.py:4558-4594`]

### Anti-Patterns to Avoid

- **Importing sentence-transformers on the session thread:** `_embedding_function()` in `semantic.py` lazy-imports `chromadb.utils.embedding_functions` — call it only inside the daemon thread or a method that runs in the worker. MiniLM cold-load is 4.86s (measured) and RSS cost is ~419 MB.
- **Two PersistentClient instances to the same path concurrently writing:** Chromadb 1.5.9 uses SQLite `delete` journal mode (not WAL). Same-client concurrent reads/writes from different threads are safe (tested). Two different client instances opening the same path is allowed for reads (tested: OK) but writing from two `PersistentClient` instances simultaneously to the same path is untested and may cause corruption — use one shared client per process.
- **Polling `is_ready()` blocking the session thread:** Never sleep or block waiting on the daemon thread. If not ready, return degraded BM25 results immediately.
- **Per-recall full-corpus BM25 rescan from disk:** Build the BM25 index in-memory at `CodeIndex.build()` time and hold a reference. Rebuild only when the content manifest changes. (Protects the p95 <500ms target.)
- **Rebuilding the embedding collection when dim hasn't changed:** Check the collection metadata to detect embedding-dim mismatch. If the user swaps `default_embedding_model`, the dim may change (e.g., 384→1536). Drop and rebuild the collection; do not silently append with wrong dims.
- **Using `add()` instead of `upsert()` for incremental reindex:** `add()` raises `DuplicateIDError` on existing ids. Always `delete(ids=old_ids)` first, then `upsert()` — or use `upsert()` unconditionally for new chunks.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RRF fusion across ranked lists | Custom score normalization | `MemoryStore._rrf_merge` (static) | Already handles dedup, score normalization, top-k; corpus-agnostic |
| Embedding function selection | New embedding dispatch code | `SemanticMemory._embedding_function()` (reuse) | Handles MiniLM / OpenAI key detection / config `default_embedding_model` |
| Chroma client initialization | Direct `chromadb.PersistentClient` construction inline | `SemanticMemory(persist_dir=..., collection_name="voss_code")` | Wraps Settings(anonymized_telemetry=False); handles import errors |
| Code tokenization for BM25 | Custom tokenizer | `_bm25_tokenize` from `memory_store.py:63` | Already handles camelCase, snake_case, dots, slashes |
| Content hash for files | Custom hash scheme | `hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()` | Identical to M10 `build_index()` — consistent manifest |
| Savings ledger write | New JSONL writer | `_append_savings_record()` from `recorder.py:143` | Handles clamping, path creation, json serialization |
| Provider build for enrichment model | New LiteLLM setup | `build_provider_for_model()` from `model_router.py:102` | Handles openai-compat vs native routing |
| Session config reading | Direct file parse | `get_model_tiers()` / `_parse_model_tiers_section()` pattern from `config.py` | Handles missing file, malformed TOML, merge with defaults |

---

## Runtime State Inventory

> SKIPPED — V19 is a greenfield feature addition, not a rename/refactor/migration. No existing runtime state (stored data, live service config, OS-registered state, secrets, or build artifacts) will be renamed or migrated.
>
> However: V19 CREATES `.voss-cache/code/semantic-manifest.json` and `.voss-cache/code/chroma/` as derived, rebuildable cache. If a schema change occurs in a future phase, `rm -rf .voss-cache/code/chroma/` + reindex is the recovery path (no migration needed by design).

---

## Common Pitfalls

### Pitfall 1: Embedding-Dim Mismatch on Model Swap

**What goes wrong:** User changes `default_embedding_model` from `all-MiniLM-L6-v2` (384-dim) to an OpenAI model (1536-dim). Chroma collection was built with 384-dim vectors. Subsequent queries raise dimension-mismatch errors or return garbage results.
**Why it happens:** Chroma collection stores its embedding dimension at creation time; mismatched upserts are silently discarded or error.
**How to avoid:** Store the `embedding_model` name in the manifest. On each build/query, compare manifest model to current `default_embedding_model`. If mismatch, drop the entire collection (`client.delete_collection("voss_code")`) and rebuild from scratch. Log a user-visible message.
**Warning signs:** Chroma query exceptions mentioning dimension; manifest model != config model.

### Pitfall 2: sentence-transformers Import on Session Thread (Cold-Load Latency)

**What goes wrong:** Instantiating `SemanticMemory` (which calls `_embedding_function()`, which imports `sentence_transformers`) on the main thread stalls session startup by ~4.86s (measured on this machine; CI may be 15-30s without cached model weights).
**Why it happens:** `SentenceTransformerEmbeddingFunction.__init__` loads the model weights immediately on import.
**How to avoid:** All calls to `_maybe_semantic()` that trigger `SemanticMemory.__post_init__` MUST happen inside the daemon thread, not at `CodeIndexService.__init__` or `CodeIntelService.for_cwd()`. Use `threading.Event` to signal readiness. Never call `code_index.query()` from the session thread without checking `is_ready()` first.
**Warning signs:** `voss do` startup time increases by >2s.

### Pitfall 3: Chroma SQLite Journal Mode = DELETE (Not WAL)

**What goes wrong:** Concurrent writes from two different `PersistentClient` instances to the same `.voss-cache/code/chroma/` path cause lock errors or corruption.
**Why it happens:** Chromadb 1.5.9 (verified) uses SQLite `journal_mode=DELETE` (not WAL). This means SQLite takes an exclusive write lock. Multiple processes holding `PersistentClient` instances to the same path are not guaranteed safe.
**How to avoid:** One `PersistentClient` instance per process. The background thread and the query path MUST share the same `SemanticMemory` instance (held on `CodeIndex`). Do not allow `voss recall --refresh` and an in-session `code_recall` tool call to race on two separate instances.
**Warning signs:** `sqlite3.OperationalError: database is locked` in stderr.

### Pitfall 4: BM25 Corpus Must Be Rebuilt After Incremental Reindex

**What goes wrong:** The in-memory `BM25Okapi` instance was built from chunks at index time. After a file changes and chunks are re-embedded, the BM25 corpus is stale — query results return old content.
**Why it happens:** `BM25Okapi` is built at initialization time from a static corpus list.
**How to avoid:** Rebuild the BM25 corpus whenever the manifest changes. Since BM25 corpus build is fast (no model call), rebuild it from the full chunk set after every incremental reindex pass.
**Warning signs:** `code_recall` returns stale content that no longer matches the changed file.

### Pitfall 5: Oversize Chunks Exceeding MiniLM Window (256 Tokens)

**What goes wrong:** A large file with few symbols produces a single chunk that is 1000+ lines long. MiniLM silently truncates at 256 BPE tokens (the `max_seq_length` is 256, verified: `m.max_seq_length == 256`). The embedding represents only the first ~512 characters.
**Why it happens:** MiniLM uses BertTokenizer; typical code is ~2 chars/token, so 256 tokens ≈ 512 chars ≈ 30-40 lines. Preambles (imports block) can exceed this trivially.
**How to avoid:** After extracting symbol-boundary chunks, apply a secondary split: if a chunk's character count exceeds ~800 chars (safe estimate for 256-token window at 3 chars/token), split it into overlapping sub-chunks of ~600 chars with ~100-char overlap. Track all sub-chunks as separate `code:<path>:<seq:03d>` ids.
**Warning signs:** Golden query gate failures on large single-class files.

### Pitfall 6: Files with Zero Symbols

**What goes wrong:** M10's `symbols` table has no rows for files that match no `SYMBOL_PATTERNS` (e.g., `*.go` in a new language, config files with a `.py` extension but no defs). The chunk-boundary algorithm produces nothing.
**Why it happens:** `_extract_symbols()` returns `[]` for unknown languages and for files whose content matches no pattern.
**How to avoid:** When `symbols` count for a file is 0, produce a single whole-file chunk (from line 1 to EOF), subject to the oversize split of Pitfall 5. This is the "preamble = chunk 0" case from D-02.
**Warning signs:** Files present in M10 `files` table but absent from `voss_code` Chroma collection.

### Pitfall 7: Profile-Off Enrichment Must Produce ZERO LLM Calls

**What goes wrong:** A code path accidentally calls `resolve_key()` or `build_provider_for_model()` even when `enrich_profile` is false, causing a provider instantiation.
**Why it happens:** Eager initialization of the enrichment provider at module import or `__init__` time.
**How to avoid:** Guard ALL enrichment code paths behind `if enrich_profile and enrich_model_configured`. The `profile_off` test in the acceptance criteria instruments via mock/stub at the provider level — failing this test is a hard gate.
**Warning signs:** Test assertions `assert provider.call_count == 0` failing.

### Pitfall 8: `Hit.locator` Collisions Between Code and Memory Corpora

**What goes wrong:** `_rrf_merge` deduplicates by `hit.locator`. If a code chunk id and a memory id share the same string, one hit is silently dropped.
**Why it happens:** Code chunk ids use `code:<path>:<seq>` prefix; memory ids use `turn:<...>`, `note:<...>`, etc. These should not collide — but if memory notes are about code files, an edge case could create a match.
**How to avoid:** The `code:` prefix in chunk ids (D-04) guarantees no collision with `turn:`, `note:`, `ledger:`, `decision:`, `convention:` memory id prefixes. Enforce the prefix in `_chunk_id()` and test for it.
**Warning signs:** Fewer-than-expected hits from `voss recall` when both corpora are populated.

---

## Code Examples

### Chunk Extraction from M10 Symbols Table

```python
# Source: verified against voss/harness/code/index.py schema
import sqlite3
from pathlib import Path

def extract_chunks(db_path: Path, file_path: str, content: str) -> list[tuple[int, int, str]]:
    """Returns list of (start_line, end_line, chunk_text) for one file."""
    lines = content.splitlines(keepends=True)
    total_lines = len(lines)

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """SELECT s.line FROM symbols s
               JOIN files f ON s.file_id = f.id
               WHERE f.path = ? ORDER BY s.line""",
            (file_path,)
        ).fetchall()
    finally:
        conn.close()

    starts = sorted({r[0] for r in rows})  # symbol start lines (1-based)
    if not starts:
        # Zero symbols: one whole-file chunk
        return _split_oversize(1, total_lines, lines)

    boundaries = starts + [total_lines + 1]
    chunks = []
    for i, start in enumerate(boundaries[:-1]):
        end = boundaries[i + 1] - 1
        chunks.extend(_split_oversize(start, end, lines))
    # Preamble: lines before first symbol
    if starts[0] > 1:
        chunks = _split_oversize(1, starts[0] - 1, lines) + chunks
    return chunks

def _split_oversize(start: int, end: int, lines: list[str], max_chars: int = 800) -> list[tuple[int, int, str]]:
    text = "".join(lines[start - 1: end])
    if len(text) <= max_chars:
        return [(start, end, text)]
    # Simple line-based split with overlap
    step = max(1, (end - start + 1) // 2)
    mid = start + step
    return (
        _split_oversize(start, mid, lines, max_chars) +
        _split_oversize(mid + 1, end, lines, max_chars)
    )
```
[VERIFIED: SQL schema from `code/index.py:115-148`; `symbols.line` column confirmed]

### Fake Embedding Function for Unit Tests

```python
# Source: tests/memory/test_semantic.py pattern (existing)
def fake_embed_fn():
    """Returns a constant 384-dim embedding — no model download, no network."""
    import numpy as np
    class _FakeEmbedFn:
        def __call__(self, texts):
            return [np.ones(384, dtype=np.float32).tolist() for _ in texts]
    return _FakeEmbedFn()

# In test: monkeypatch SemanticMemory._embedding_function
monkeypatch.setattr(SemanticMemory, "_embedding_function", lambda self: fake_embed_fn())
```
[VERIFIED: codebase — `tests/memory/test_semantic.py:4-11` uses `DefaultEmbeddingFunction` as equivalent pattern]

### `attach_code_recall_tool` Pattern

```python
# Source: tools.py:159 (attach_memory_tools pattern)
def attach_code_recall_tool(
    tools: dict[str, "ToolEntry"],
    *,
    code_index_service: "CodeIndexService",
) -> None:
    @tool(
        name="code_recall",
        description=(
            "Search codebase semantically by concept. Returns file:line-anchored "
            "chunk hits (BM25 + vector RRF). Use for concept queries "
            "('where is retry handled', 'all authentication points'). "
            "For exact-name lookup use code_search instead."
        ),
    )
    async def code_recall(query: str, top_k: int = 5) -> str:
        hits = code_index_service.query(query, top_k=top_k)
        if not hits:
            return "(no hits)"
        lines = []
        for h in hits:
            prefix = f"[{h.source}]" if getattr(h, "source", None) else "[code]"
            lines.append(f"{prefix} {h.locator} (score {h.score:.2f})")
            if h.excerpt:
                lines.append(f"  {h.excerpt[:160]}")
        return "\n".join(lines)

    tools["code_recall"] = ToolEntry(
        descriptor=code_recall,
        is_mutating=False,
        group="code",
        scope_requirements=("code",),
    )
```
[VERIFIED: codebase — `tools.py:159-214`, `tools.py:28` CAPABILITY_GROUPS includes "code"]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Chroma used SQLite WAL | Chroma 1.5.9 uses `journal_mode=DELETE` (verified 2026-06-11) | Chromadb 1.x restructure | Must use single PersistentClient per process for writes |
| sentence-transformers separate from chromadb | chromadb bundles `DefaultEmbeddingFunction` (ONNX, no download) for tests | chromadb ≥0.4 | Tests can use `DefaultEmbeddingFunction` without loading MiniLM |
| No upsert API | `collection.upsert()` available (verified) | chromadb ≥0.4 | Clean incremental reindex: upsert is idempotent by id |
| BM25 tokenizer not code-aware | `_bm25_tokenize` handles camelCase + snake_case | F2 (memory_store.py) | Reuse for code recall — no new tokenizer needed |

**Deprecated/outdated:**
- `chromadb.Client()` (in-memory only, no persistence): Use `chromadb.PersistentClient(path=...)` for `voss_code`. In-memory client is fine for unit tests.
- `chromadb.Settings(chroma_db_impl="duckdb+parquet")`: Removed in chromadb 1.x. Do not reference.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Daemon thread safety with same `PersistentClient` instance (background write + main-thread read) | Patterns 1, 4 | If NOT thread-safe: need a lock or move all Chroma calls to the worker; query must wait for round-trip | 
| A2 | `BM25Okapi` in-memory reconstruction from all chunks is fast enough (<500ms) for a ~10K LoC repo | Pitfall 4 | If too slow: cache BM25 corpus between sessions in a pickle; test confirms p95 |
| A3 | `_compose_system_blocks()` change is backward-compatible — adding a new optional `code_recall_text=""` param does not break callers | Pattern 6 | Unlikely: default is `""` (filtered out by `if text`); grep reveals 3 call sites |
| A4 | The `fs_write`/`fs_edit` tool hooks can synchronously trigger a targeted re-hash of the written path without blocking the turn | Architecture | If blocking: make it fire-and-forget with `threading.Thread(daemon=True)` per mutation |

**If this table is empty:** it is not — A1-A4 require attention from the planner.

---

## Open Questions (RESOLVED)

1. **`[code_recall]` vs `[model_tiers]` config section for `index_enrich`** — **(RESOLVED)**
   - What we know: `[model_tiers]` already has a parse pattern; adding `index_enrich` there is one key change. Alternatively, a new `[code_recall]` section is cleaner but requires a new parser.
   - What's unclear: Whether `index_enrich` semantically belongs with tier aliases (strong/cheap/fast) or is distinct enough to warrant its own section.
   - Recommendation: Add `index_enrich` to `[model_tiers]` as a fourth tier key — lowest friction, one-line parser change, consistent with D-12 intent.
   - **RESOLVED (V19-06, Task 1):** Split decision — `index_enrich` is added as a named role to the model-tier resolution (`get_index_enrich_model()` reads `get_model_tiers().get("index_enrich")`, fail-closed None default per D-06), AND a separate `[code_recall]` section parser (`get_code_recall_config()`) owns the non-model knobs `enrich_profile`/`enrich_budget_tokens`/`inject`. Model role stays with tiers (lowest friction); behavioral flags get their own section (they are not tier aliases). See V19-06 Task 1.

2. **`Hit` dataclass extension vs separate `CodeHit` dataclass** — **(RESOLVED)**
   - What we know: `_rrf_merge` operates on `list[list[Hit]]` using `hit.locator` as the dedup key. Code hits need `line_start`/`line_end` for CLI display; memory hits do not have these.
   - What's unclear: Whether adding optional fields to `Hit` creates coupling or confusion.
   - Recommendation: Add `line_start: int | None = None` and `line_end: int | None = None` to the existing `Hit` dataclass in `memory_store.py`. They are `None` for memory hits and populated for code hits. This avoids a second dataclass and keeps `_rrf_merge` unchanged.
   - **RESOLVED (V19-01, Task 1):** `Hit` is extended with trailing optional `line_start`/`line_end` fields (no separate `CodeHit`); memory hits leave both `None`, code hits populate them, and `_rrf_merge`'s `dataclasses.replace` carries them through unchanged. See V19-01 Task 1.

3. **Golden query fixture strategy: committed subset vs full live build** — **(RESOLVED)**
   - What we know: D-08 says "planner decides" between a committed fixture index (small subset) or full local build behind a marker.
   - What's unclear: A committed fixture is CI-safe but may go stale. A full build needs MiniLM model cached in CI.
   - Recommendation: Use `@pytest.mark.slow` for the golden-query test that builds the full Voss repo index; in CI without slow marker it runs against a tiny 5-file fixture with a fake embedding function checking structural correctness (top-k contains expected file). Only the `slow` gate tests real semantic quality.
   - **RESOLVED (V19-01, Task 2/3):** Both strategies adopted — the committed-subset path uses the `fake_embed_fn` (Chroma `DefaultEmbeddingFunction`, no network) for CI structural checks, and the full-build golden-query test carries `@pytest.mark.slow` for real semantic-quality runs against the cached MiniLM model. The `slow` marker is registered in `pyproject.toml` (V19-01 Task 2). See V19-01 Task 3 (`test_golden_concept_queries`).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `chromadb` | VSEM-01..04 | ✓ | 1.5.9 | BM25-only degradation (F2 contract) |
| `sentence-transformers` | VSEM-01 (embeddings) | ✓ | 5.5.0 | Chroma `DefaultEmbeddingFunction` (ONNX, tests only) |
| `all-MiniLM-L6-v2` (HF model) | VSEM-01..04 | ✓ | cached in `~/.cache/huggingface/hub/` | Not available in offline CI without cache — use `DefaultEmbeddingFunction` for non-live tests |
| `rank-bm25` | VSEM-04 BM25 side | ✓ | (installed) | No fallback needed — already a core dep |
| `sqlite3` | VSEM-01 chunk extraction | ✓ | stdlib | N/A |
| `psutil` | Memory footprint checks | ✓ | (installed in venv) | N/A |
| Git | M10 `_discover_files` | ✓ | system git | os.walk fallback already in `index.py` |

**Missing dependencies with no fallback:** none.

**Missing dependencies with fallback:** `all-MiniLM-L6-v2` model weights (HF cache) — CI must either cache the model or tests run with `DefaultEmbeddingFunction` for non-`@pytest.mark.live` paths.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, `pyproject.toml:110`) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python -m pytest tests/code_recall/ -q -x` |
| Full suite command | `.venv/bin/python -m pytest tests/ -q --ignore=tests/eval/golden --ignore=tests/eval/matrix` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VSEM-01 | `CodeIndex.build()` populates `voss_code` collection; chunk split on symbol boundaries | unit (fake embed) | `.venv/bin/python -m pytest tests/code_recall/test_chunker.py -x -q` | ❌ Wave 0 |
| VSEM-01 | `rm -rf .voss-cache/` + reindex reproduces working index | integration | `.venv/bin/python -m pytest tests/code_recall/test_chunker.py::test_derived_cache -x` | ❌ Wave 0 |
| VSEM-02 | Touch-one-file: only that file's chunks re-embed | unit (embed call counter) | `.venv/bin/python -m pytest tests/code_recall/test_incremental.py -x -q` | ❌ Wave 0 |
| VSEM-02 | Unchanged-repo reindex: zero embed calls | unit | `.venv/bin/python -m pytest tests/code_recall/test_incremental.py::test_no_reembed_on_unchanged -x` | ❌ Wave 0 |
| VSEM-03 | Session on unindexed repo: first round-trip does not block | unit (threading.Event mock) | `.venv/bin/python -m pytest tests/code_recall/test_background.py -x -q` | ❌ Wave 0 |
| VSEM-03 | Recall before ready returns degraded hits (not error) | unit | `.venv/bin/python -m pytest tests/code_recall/test_background.py::test_degraded_before_ready -x` | ❌ Wave 0 |
| VSEM-04 | `code_recall` registered in tool registry; schema valid | unit | `.venv/bin/python -m pytest tests/code_recall/test_code_recall_tool.py::test_registration -x` | ❌ Wave 0 |
| VSEM-04 | Chroma-absent install returns BM25-only hits without error | unit (chromadb unimported) | `.venv/bin/python -m pytest tests/code_recall/test_code_recall_tool.py::test_degradation -x` | ❌ Wave 0 |
| VSEM-04 | Recall p95 <500ms on indexed ~10K LoC fixture | perf | `.venv/bin/python -m pytest tests/code_recall/test_code_recall_tool.py::test_perf_p95 -x` | ❌ Wave 0 |
| VSEM-05 | `voss recall` exits 0, ranked labeled output | CLI subprocess | `.venv/bin/python -m pytest tests/code_recall/test_recall_cli.py::test_exit_0_labeled -x` | ❌ Wave 0 |
| VSEM-05 | `--json` output validates against documented schema (incl. `source` field) | CLI subprocess | `.venv/bin/python -m pytest tests/code_recall/test_recall_cli.py::test_json_schema -x` | ❌ Wave 0 |
| VSEM-06 | Injected section ≤1000 tokens (V18 counter) | unit | `.venv/bin/python -m pytest tests/code_recall/test_injection.py::test_token_cap -x` | ❌ Wave 0 |
| VSEM-06 | V18 allocator can evict injection section | unit (context_allocator fixture) | `.venv/bin/python -m pytest tests/code_recall/test_injection.py::test_evictable -x` | ❌ Wave 0 |
| VSEM-06 | `inject = false` produces zero injection bytes | unit | `.venv/bin/python -m pytest tests/code_recall/test_injection.py::test_off_switch -x` | ❌ Wave 0 |
| VSEM-07 | Profile-off full build: zero provider calls | unit (stub provider) | `.venv/bin/python -m pytest tests/code_recall/test_enrichment.py::test_profile_off_zero_llm -x` | ❌ Wave 0 |
| VSEM-07 | Profile-on enrichment routes via `index_enrich` role, not session model | unit (stub provider) | `.venv/bin/python -m pytest tests/code_recall/test_enrichment.py::test_routes_index_enrich_role -x` | ❌ Wave 0 |
| VSEM-08 | Tiny-cap enrichment: clean abort, index valid, ledger line correct | unit (stub provider) | `.venv/bin/python -m pytest tests/code_recall/test_enrichment.py::test_budget_cap_abort -x` | ❌ Wave 0 |
| VSEM-08 | `/cost` output shows enrichment line | unit | `.venv/bin/python -m pytest tests/code_recall/test_enrichment.py::test_cost_ledger_line -x` | ❌ Wave 0 |
| all | Golden concept-query gate: ≥10 queries, expected file in top-5 | integration / `@pytest.mark.slow` | `.venv/bin/python -m pytest tests/code_recall/test_golden_queries.py -x -m slow` | ❌ Wave 0 |
| all | Coherence: `voss do`/`voss chat` work end-to-end | integration | existing regression suite | ✅ exists |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/code_recall/ -q -x --ignore=tests/code_recall/test_golden_queries.py`
- **Per wave merge:** `.venv/bin/python -m pytest tests/code_recall/ tests/memory/ tests/harness/test_agent_packing.py -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`; golden query gate (`-m slow`) gated on wave with full index

### Wave 0 Gaps

- [ ] `tests/code_recall/__init__.py` — new test subdirectory
- [ ] `tests/code_recall/conftest.py` — shared fixtures: `fake_embed_fn`, `indexed_fixture_repo`, `chroma_disabled_env`, `stub_provider`
- [ ] `tests/code_recall/test_chunker.py` — covers VSEM-01
- [ ] `tests/code_recall/test_incremental.py` — covers VSEM-02
- [ ] `tests/code_recall/test_background.py` — covers VSEM-03
- [ ] `tests/code_recall/test_code_recall_tool.py` — covers VSEM-04
- [ ] `tests/code_recall/test_recall_cli.py` — covers VSEM-05
- [ ] `tests/code_recall/test_injection.py` — covers VSEM-06
- [ ] `tests/code_recall/test_enrichment.py` — covers VSEM-07/08
- [ ] `tests/code_recall/test_golden_queries.py` — covers quality gate (VSEM-01 acceptance)
- [ ] Add `slow` marker to `pyproject.toml [tool.pytest.ini_options] markers` list

---

## Security Domain

> `security_enforcement` not explicitly false in config — including.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — local-only index cache |
| V3 Session Management | no | N/A |
| V4 Access Control | partial | `.voss-cache/` is user-local; enrichment model key (Ollama/API) via existing `auth.load_provider_key` |
| V5 Input Validation | yes | Chunk text is raw source code — do not eval, do not exec; only text/metadata into Chroma |
| V6 Cryptography | no | sha256 for content hash (integrity only, no crypto auth needed) |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal in chunk ids | Tampering | Chunk ids use relative paths from cwd; `jail_path` pattern enforced at query origin |
| LLM enrichment prompt injection via code chunks | Spoofing | Enrichment prompt wraps chunk text in a fenced context; model output is a one-liner summary stored as metadata, never executed |
| Stale enrichment summaries misleading agent | Tampering | Summaries are evicted when the file is re-chunked (same manifest hash check); stale entries are deleted with old chunk ids |
| Enrichment API key leakage to stderr | Information Disclosure | Key resolution via `resolve_key()` which reads env/keyring; never log the key; existing `model_router.py` pattern safe |

---

## Sources

### Primary (HIGH confidence — verified against installed packages and live codebase)

- `voss/harness/memory_store.py` — `_rrf_merge` (L426), `_bm25_tokenize` (L63), `_maybe_chroma` (L108), `Hit` dataclass (L41), `make_id` D-04 convention (L56)
- `voss_runtime/memory/semantic.py` — `SemanticMemory.__post_init__`, `_embedding_function()`, `add()`, `retrieve()` — complete API surface
- `voss/harness/code/index.py` — exact SQLite schema: `files(id, path, lang, mtime, hash)`, `symbols(id, file_id, name, kind, line)`, `_extract_symbols()` 200-symbol cap (L98), `LANGUAGE_EXTS` (L33), `VENDORED_DIRS` (L25)
- `voss/harness/code/service.py` — `CodeIntelService.for_cwd()` pattern for `CodeIndexService`
- `voss/harness/agent.py` — `_compose_system_blocks()` (L372-404), `run_turn()` signature (L502), `project_index_text` threading (L377, L518)
- `voss/harness/cli.py` — `attach_memory_tools` (L159), `AGENT_COMMANDS` tuple (L4558), `register()` (L4597), `_recall` slash handler (L640), `/cost` ledger read (L924-957), `voss do_cmd` project_index_text flow (L1750-1807)
- `voss/harness/recorder.py` — `_append_savings_record()` (L143-161), token-savings.jsonl format
- `voss/harness/model_router.py` — `resolve_key()` (L32), `build_provider_for_model()` (L102), `find_entry()` (L151)
- `voss/harness/config.py` — `[model_tiers]` parse pattern (L222-258), `_write_harness()` (L438)
- `voss/harness/context_allocator.py` — `ContextAllocator.pack()`, `PackingProfile`, eviction mechanics
- `tests/memory/test_semantic.py` — `DefaultEmbeddingFunction` test pattern (L4-11)
- `chromadb` 1.5.9 (live) — upsert/add/delete API verified; SQLite `journal_mode=DELETE` confirmed; same-client thread safety confirmed
- `sentence-transformers` 5.5.0 (live) — `all-MiniLM-L6-v2` max_seq_length=256 confirmed; cold-load 4.86s measured; RSS ~419MB measured

### Secondary (MEDIUM confidence)

- `pyproject.toml` — pytest markers config, `voss[search]` extras definition
- `voss/cli.py:539-541` — `_register_agent_commands(main)` seam for new `recall_cmd`
- `voss/harness/tools.py` — `CAPABILITY_GROUPS` (L28), `ToolEntry` (L64), `make_toolset` entry point

### Tertiary (LOW confidence)

- Chunking overlap/sub-split strategy for oversize chunks: reasonable heuristic from MiniLM spec; not directly validated against golden query quality on this codebase.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified live in .venv
- Architecture: HIGH — all seams read from source
- Pitfalls: HIGH (P1-P7) / MEDIUM (P8) — P1-P7 verified against actual code or measured; P8 inferred from RRF design

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (30 days; sentence-transformers 5.x / chromadb 1.5.x are stable)
