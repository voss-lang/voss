# Phase V23: Retrieval-Aware Memory Ranking & Hygiene - Research

**Researched:** 2026-06-12
**Domain:** MemoryStore retrieval-quality loop — telemetry sidecar, quality floors, rescore, eviction, reindex drift gate, pinned tier, CLI verbs
**Confidence:** HIGH (all findings grounded in live codebase reads)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01** — Telemetry = `.voss/memory/.retrieval.jsonl` append-log; one event per agent-recall hit; vacuum compacts events into per-locator counts. Matches the `.tombstones.jsonl` pattern; corrupt-line tolerant; gitignored (extend `_VOSS_MEMORY_GITIGNORE`).
- **D-02** — Pins = separate `.voss/memory/.pins.json`, COMMITTED. Pins are operator curation — git history + survive clones. Telemetry is high-churn local state and stays ignored. Do NOT add `.pins.json` to the gitignore.
- **D-03** — Sync append, skip-on-contention: telemetry appends at recall return under non-blocking portalocker (existing `_lock` pattern); on contention, drop the event — one lost increment is harmless. No deferred-batch machinery.
- **D-04** — Chroma floor = absolute similarity, default 0.25: drop hits with `(1 − distance) < 0.25`; config `[memory] chroma_floor`. Conservative (froots ships 0.45 — judged too aggressive for local sentence-transformer spaces).
- **D-05** — BM25 floor = relative-to-top, default ratio 0.1: keep hits ≥ 10% of this query's top BM25 score; config `[memory] bm25_floor_ratio`. Absolute floors don't transfer across corpus sizes. Must preserve the tiny-corpus token-overlap rescue path (memory_store.py:555) — relative form does so naturally.
- **D-06** — Floors apply per-retriever per-store, PRE-fusion only. Each store's BM25/chroma floors its own ranking before RRF; no post-fusion drop. Code corpus (V19 CodeIndex) untouched per SPEC.
- **D-07** — Pinned block = non-evictable allocator item: enters the V18 variable region as a fixed-cost item the packer places first and may never digest/fold/evict; cap counts inside the existing ceiling (honest accounting, no new region type). NOT the stable region — stable region is FOLD-only (V18 gotcha).
- **D-08** — Full text, per-item soft cap ~200 tok: inject whole memory body per pin, soft-capped per item, under the ~500 tok tier cap. No Hit-style 200-char excerpts — truncation defeats curated pins.
- **D-09** — Global pins: project priority on overflow: post-V21 both stores' pins inject, labeled `[global]` like recall hits; when combined size exceeds the cap, project pins win, then newest-global.
- **D-10** — Drift gate covers file-based sources only: notes/decisions/conventions (the hand-edit surface). turns/ledgers excluded — append-only machine-written JSONL, no real drift vector.
- **D-11** — Manifest = `.voss/memory/.reindex-manifest.json`, gitignored: sha256 per relative file path, V19 CodeIndex manifest pattern. Derived artifact; missing manifest ⇒ everything stale (first run rebuilds).
- **D-12** — Global store via `--global` flag, project default: matches V21's `vacuum --global` / `forget --global` verb convention; each store owns its manifest.

### Claude's Discretion
- **D-13** — Rescore formula shape: multiplicative boost on RRF score from exponential recency decay (e.g. ~7-day half-life) + log-scaled frequency, both weight-configurable, boost bounded so similarity ordering dominates; exact formula = planner. Hard constraints from SPEC: deterministic under fixture, empty-telemetry = no-op, off = byte-identical.
- **D-14** — `voss memory list/show` output format: table layout, column set beyond SPEC minimum (locator, source, retrieval_count, last_retrieved, pin flag), optional `--json`. Follow existing CLI output conventions.
- **D-15** — Eviction tie-breaks: ordering within the never-retrieved and stale-retrieved buckets (mtime ascending is the natural default); how vacuum compaction folds `.retrieval.jsonl` events (count summation + max timestamp).
- **D-16** — Telemetry event schema: minimal JSONL line (locator, ts; maybe session_id). Vacuum compaction format = planner.

### Deferred Ideas (OUT OF SCOPE)
- Graph visualization of memory (similarity + category-overlap edges, derived view, flat store) — voss-app/TUI seed, post-V23
- Supersession edges between memories — separate seed after telemetry exists
- E-track quality eval gating a rescore default-ON flip — proposal after V23 ships + telemetry accumulates
- Auto-pinning heuristics — manual verb only this phase
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VRNK-01 | Retrieval telemetry sidecar (agent paths only, `.retrieval.jsonl`) | `_lock` pattern at L134; `_tombstones.jsonl` as template; telemetry record site = tools.py:183 `memory_recall` tool + auto-injection call sites |
| VRNK-02 | Pre-fusion quality floor default-on (chroma absolute 0.25, BM25 relative-to-top 0.1) | Floor slots after `_chroma_recall` L447 and `_bm25_recall` L530 tail, before `_rrf_merge` L431 |
| VRNK-03 | Recency×frequency rescore on RRF output, default-off, byte-identical off-path | Rescore hook at `_rrf_merge` output in `recall()` L428; identical path = `if not profile.rescore: return fused` |
| VRNK-04 | Retrieval-aware eviction/vacuum preferring never-retrieved rows | `_maybe_evict` sort key at L183; `vacuum()` pass order — extend both to consult sidecar |
| VRNK-05 | `voss memory reindex [--check]` chroma drift gate, hash manifest | V19 `_manifest_path`/`_load_manifest`/`_save_manifest` pattern in `code/semantic_index.py:109-124`; `sync --check` exit contract at `voss/cli.py:519-522` |
| VRNK-06 | Pinned tier: sidecar flag, V18 variable region injection, token cap, eviction exemption | `ContextAllocator.pack()` is the injection site; `_maybe_evict` needs pin-exempt check before sorting; `.pins.json` is the sidecar |
| VRNK-07 | CLI verbs: pin/unpin/list/show | `memory_group` at `memory_cli.py:18`; pattern = existing `vacuum`/`adopt`/`size` commands |
| VRNK-08 | Regression + coherence guard: existing suites stay green, byte-identical baseline test | Test paths: `tests/memory`, `tests/harness/test_memory_*.py`, `tests/code_recall`; byte-identical precedent = `test_no_pack_byte_identical` in `test_agent_packing.py:203` |
</phase_requirements>

---

## Summary

V23 adds a retrieval-quality loop to `MemoryStore` in `voss/harness/memory_store.py`. The substrate is mature: RRF hybrid recall (BM25 + Chroma), per-source portalocker advisory locks, a tombstones append-log lifecycle, and an existing V19 hash-manifest pattern from the code index. The design is extension-not-replacement — V23 introduces no new store type, no new schema substrate, no new index.

The eight requirements divide into five implementation tiers. (1) A sidecar append-log (`.retrieval.jsonl`) records telemetry at the two agent-path recall sites — the `memory_recall` tool in `tools.py:178` and auto-injection call sites (tools, not `/recall` CLI); the log is compacted by vacuum. (2) Two pre-fusion floor functions are inserted at the tails of `_chroma_recall` and `_bm25_recall` before `_rrf_merge` is called; the floor values are config-readable from `[memory]` in `.voss/config.yml` via `_load_memory_config()`. (3) An optional rescore step multiplies the fused RRF score by a telemetry-derived boost after `_rrf_merge`; with `rescore` off (the default) the recall return path is byte-identical to pre-V23. (4) Eviction in `_maybe_evict` and vacuum gain a sidecar-aware sort key: never-retrieved files first, stale-retrieved second, mtime fallback when no sidecar. (5) A new `voss memory reindex [--check]` CLI command tracks sha256 hashes of notes/decisions/conventions files; `--check` exits 1 on drift; bare reindex re-embeds only stale/missing entries.

V23 executes AFTER V21 (dual-store). V21's locked plan adds `root_override: Path | None = None` to `MemoryStore.__init__` and a `make_global_store() -> MemoryStore | None` factory. V23 must apply floors, telemetry, and pinning through the same chokepoints in both stores. The `voss recall` CLI at `cli.py:4835` is a no-touch path — it calls `MemoryStore(cwd).recall(...)` directly and floors apply per-store upstream; the CLI itself does not record telemetry.

**Primary recommendation:** Implement in strict wave order — Wave 0 RED test scaffold first (all VRNK tests RED), then Wave 1 telemetry + floors (VRNK-01/02), Wave 2 rescore + eviction (VRNK-03/04), Wave 3 reindex + pin/CLI (VRNK-05/06/07), Wave 4 regression lock (VRNK-08 byte-identical baseline).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Retrieval telemetry recording | API/Backend (MemoryStore) | — | Recall is synchronous; telemetry appended at return, sidecar lives next to store |
| Pre-fusion quality floors | API/Backend (_chroma_recall, _bm25_recall) | — | Floors must be per-retriever before RRF; not a CLI/display concern |
| Rescore boost | API/Backend (recall() post-RRF hook) | — | Config-gated; pure transform on fused scores; no filesystem access |
| Retrieval-aware eviction | API/Backend (_maybe_evict, vacuum) | — | Extends existing sort key; sidecar read at eviction time |
| Reindex drift gate | API/Backend (new MemoryStore method) | CLI (memory_cli.py) | Core logic in store; CLI surfaces check/repair verbs |
| Pinned tier injection | API/Backend (MemoryStore) + Allocator | CLI (pin/unpin verbs) | Pin flag read from `.pins.json` at recall time; packer places pinned block first |
| CLI verbs (pin/unpin/list/show/reindex) | CLI (memory_cli.py) | — | Click group extension; all commands delegate to MemoryStore methods |
| Config surface | API/Backend (_load_memory_config) | — | Existing `[memory]` YAML section; planner adds new keys inline |

---

## Standard Stack

### Core (no new packages — V23 is extension-only)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rank-bm25 | 0.2.2 | BM25Okapi lexical scoring | Already installed; `_bm25_recall` uses it directly [VERIFIED: pip show] |
| portalocker | 3.2.0 | Per-source advisory locking | Already installed; `_lock` context manager pattern used throughout [VERIFIED: pip show] |
| chromadb | 1.5.9 | Vector embeddings store | Already installed; `SemanticMemory` wrapper in `voss_runtime/memory/semantic.py` [VERIFIED: pip show] |
| hashlib | stdlib | sha256 for manifest | stdlib; identical to V19 `_file_hash` in `code/semantic_index.py:92` [ASSUMED] |
| json | stdlib | JSONL sidecar serialization | stdlib; matches `.tombstones.jsonl` pattern [ASSUMED] |
| datetime | stdlib | UTC ISO timestamps for telemetry | stdlib; `datetime.now(timezone.utc).isoformat(timespec="seconds")` is the project pattern [ASSUMED] |

### No New Dependencies
V23 extends existing infrastructure. The sidecar files (`.retrieval.jsonl`, `.pins.json`, `.reindex-manifest.json`) are plain JSON/JSONL. The rescore formula uses only Python `math` (stdlib). No new pip install step is needed.

**Version verification:** All packages confirmed installed in `.venv` via `pip show`. No new packages are introduced.

---

## Package Legitimacy Audit

> No new external packages are introduced in V23 — this is a pure extension of existing infrastructure. All libraries used (rank-bm25, portalocker, chromadb) are already installed project dependencies verified in the current `.venv`.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| rank-bm25 | PyPI | existing dep | — | github.com/dorianbrown/rank_bm25 | [OK] — existing dep, already used | Approved |
| portalocker | PyPI | existing dep | — | github.com/WoLpH/portalocker | [OK] — existing dep, already used | Approved |
| chromadb | PyPI | existing dep | — | github.com/chroma-core/chroma | [OK] — existing dep, already used | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*Note: slopcheck binary installed under system Python but not .venv; all packages above are existing verified project dependencies, not new introductions — audit is informational only.*

---

## Architecture Patterns

### System Architecture Diagram

```
Agent turn input
       │
       ▼
  tools.py:178              cli.py:4835 (NO-TOUCH)
  memory_recall()           voss recall CLI
  [TELEMETRY RECORD]        [no telemetry]
       │                         │
       ▼                         ▼
  MemoryStore.recall()    MemoryStore.recall()
       │                         │
  ┌────┴────┐               ┌────┴────┐
  │         │               │         │
  ▼         ▼               ▼         ▼
_bm25_   _chroma_       _bm25_   _chroma_
recall   recall         recall   recall
  │         │               │         │
  [FLOOR]  [FLOOR]         [FLOOR]  [FLOOR]
  │         │               │         │
  └────┬────┘               └────┬────┘
       │                         │
       ▼                         ▼
  _rrf_merge()            _rrf_merge()
       │                         │
  [RESCORE hook]          [RESCORE hook]
  (config-gated)          (config-gated)
       │                         │
       ▼                         ▼
  top_k hits              top_k hits
       │
  [TELEMETRY WRITE]
  .retrieval.jsonl
  (portalocker, skip-on-contention)
       │
       ▼
  [PIN PREPEND]
  .pins.json → fixed-cost
  allocator item (V18 region)
```

```
voss memory reindex [--check]
       │
  _load_manifest(.reindex-manifest.json)
       │
  Walk notes/ decisions/ conventions/
       │
  sha256 each file → compare manifest
       │
  --check: exit 1 + stale list  │  bare: re-embed stale + update manifest
       │                         │
  _chroma upsert (by id)        │  exit 0 + count
  (chroma absent → exit 0 + notice)
```

### Recommended Project Structure

No new directories. All sidecar files live under `.voss/memory/`:

```
.voss/memory/
├── .retrieval.jsonl       # telemetry sidecar (gitignored, append-log)
├── .pins.json             # pinned locators (COMMITTED)
├── .reindex-manifest.json # sha256 per file-based source (gitignored)
├── .tombstones.jsonl      # existing (unchanged)
├── .locks/                # existing portalocker lock files
├── chroma/                # existing (gitignored)
├── turns/
├── ledgers/
├── decisions/
├── conventions/
└── notes/
```

New source modules (inline extensions, no new files unless planner chooses to split):
```
voss/harness/
├── memory_store.py        # Core extensions (telemetry, floors, rescore, eviction, pins, reindex)
├── memory_cli.py          # New verbs: pin, unpin, list, show, reindex
└── tools.py               # Telemetry record at memory_recall return site
```

---

### Pattern 1: Telemetry Append (VRNK-01)

**What:** Append one JSONL line per returned hit immediately after `store.recall()` returns, inside `memory_recall` tool and auto-injection sites. Use the existing `_lock` portalocker pattern with skip-on-contention.

**When to use:** Agent-path recall only (tools.py `memory_recall` + auto-injection). Never on CLI paths (`/recall`, `voss recall`, `voss memory *`).

**Current `_lock` pattern** (verified `memory_store.py:134`):
```python
@contextmanager
def _lock(self, source: str):
    lock_path = self.root / ".locks" / f"{source}.lock"
    try:
        with portalocker.Lock(
            str(lock_path),
            mode="a",
            flags=portalocker.LOCK_EX | portalocker.LOCK_NB,
            timeout=0,
        ) as fh:
            yield fh
    except portalocker.exceptions.LockException:
        yield None  # skip-on-contention
```

**Telemetry append on recall return:**
```python
def _record_telemetry(self, hits: list[Hit]) -> None:
    """Append one JSONL line per hit to .retrieval.jsonl (D-01/D-03)."""
    if not hits:
        return
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path = self.root / ".retrieval.jsonl"
    with self._lock("retrieval") as lock:
        if lock is None:  # skip-on-contention (D-03)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            for hit in hits:
                f.write(json.dumps({"locator": hit.locator, "ts": ts}) + "\n")
```

The `.retrieval.jsonl` must be added to `_VOSS_MEMORY_GITIGNORE` (currently `"chroma/\n.locks/\n.tombstones.jsonl\n"` at `memory_store.py:37`). Add `".retrieval.jsonl\n.reindex-manifest.json\n"`.

**Telemetry record point in tools.py (L183):**
```python
# Inside memory_recall tool, after: hits = store.recall(query, ...)
if hits:
    store._record_telemetry(hits)  # agent-path only
```

**Auto-injection sites:** The `code_recall_text` rendering path in `cli.py:801` is NOT an agent tool — it renders text for the system prompt, not a tool call return. The actual `memory_recall` tool in tools.py is the primary agent-path site. V21 will add a `global_store.recall()` call in `attach_memory_tools` — V23's telemetry must fire on that too (same `global_store._record_telemetry(global_hits)` pattern post-V21).

---

### Pattern 2: Pre-Fusion Quality Floors (VRNK-02)

**What:** Filter out low-quality hits from each retriever's output list before `_rrf_merge` is called.

**BM25 floor position** — tail of `_bm25_recall` at `memory_store.py:575`:
```python
# After: ranked.sort(key=lambda item: item[0], reverse=True)
# Before: return [hit for _, hit in ranked[:top_k]]
cfg = self._load_memory_config()
bm25_floor_ratio = float(cfg.get("bm25_floor_ratio", 0.1))
if ranked and bm25_floor_ratio > 0:
    top_score = ranked[0][0]
    ranked = [(s, h) for s, h in ranked if s >= top_score * bm25_floor_ratio]
return [hit for _, hit in ranked[:top_k]]
```

**Key property of BM25Okapi scores** (verified): Scores are non-negative numpy float64. Top score is always ≥ all others (the ATIRE variant with epsilon floor for IDF). Tiny-corpus token-overlap rescue path (L555) produces positive integer scores, which are also non-negative — they participate correctly in relative-to-top comparison. An empty `ranked` after floor = no BM25 hits (0 hits from this retriever into fusion).

**Chroma floor position** — tail of `_chroma_recall` at `memory_store.py:483`:
```python
# After: out.append(Hit(...))
# Before: return out
cfg = self._load_memory_config()
chroma_floor = float(cfg.get("chroma_floor", 0.25))
if chroma_floor > 0:
    out = [h for h in out if h.score >= chroma_floor]
return out
```

Chroma score = `max(0.0, 1.0 - float(dist))` (verified at L470). Floor of 0.25 maps to cosine similarity ≥ 0.25 (distance ≤ 0.75). Conservative default — froots' 0.45 was explicitly rejected (D-04).

**Disable knob:** `chroma_floor = 0` and `bm25_floor_ratio = 0` in config restores pre-V23 behavior (any score passes).

---

### Pattern 3: Rescore Formula (VRNK-03, Claude's Discretion D-13)

**What:** Multiplicative boost on RRF fused score from telemetry. Applied after `_rrf_merge` in `recall()`, behind a config switch.

**Rescore hook in recall()** — after L428:
```python
fused = self._rrf_merge([bm25_hits, chroma_hits], top_k=top_k)
cfg = self._load_memory_config()
if cfg.get("rescore", False):  # default-off (D-13)
    fused = self._rescore(fused, cfg)
return fused
```

**Recommended formula** (within D-13 constraints):
```python
import math

def _rescore(self, hits: list[Hit], cfg: dict) -> list[Hit]:
    """Recency×frequency boost on RRF output (VRNK-03).

    boost = 1 + w_recency * recency_factor + w_freq * freq_factor
    where:
      recency_factor = exp(-days_since_retrieved / half_life_days)
      freq_factor = log(1 + retrieval_count) / log(1 + freq_scale)
    Bounded: boost in [1.0, 1 + w_recency + w_freq] so similarity ordering dominates.
    Empty telemetry → boost = 1.0 for all → byte-identical ordering (SPEC constraint).
    """
    telemetry = self._load_telemetry_compacted()  # locator → {count, last_retrieved}
    if not telemetry:
        return hits  # no-op: identical ordering

    half_life = float(cfg.get("rescore_half_life_days", 7.0))
    freq_scale = float(cfg.get("rescore_freq_scale", 10.0))
    w_recency = float(cfg.get("rescore_w_recency", 0.3))
    w_freq = float(cfg.get("rescore_w_freq", 0.2))

    now = datetime.now(timezone.utc)
    rescored: list[Hit] = []
    for hit in hits:
        entry = telemetry.get(hit.locator)
        if entry is None:
            boost = 1.0
        else:
            count = int(entry.get("count", 0))
            last_ts = entry.get("last_retrieved")
            if last_ts:
                last_dt = datetime.fromisoformat(last_ts)
                days_ago = max(0.0, (now - last_dt).total_seconds() / 86400.0)
                recency = math.exp(-days_ago / max(half_life, 0.001))
            else:
                recency = 0.0
            freq = math.log1p(count) / math.log1p(max(freq_scale, 1.0))
            boost = 1.0 + w_recency * recency + w_freq * min(freq, 1.0)
        rescored.append(dataclasses.replace(hit, score=hit.score * boost))
    rescored.sort(key=lambda h: (-h.score, h.locator))
    return rescored
```

**Byte-identical guarantee:** When `rescore=False` (default), `recall()` returns `_rrf_merge` output directly — no extra sort, no copy. The path through `_rrf_merge` itself is unchanged. Tests must freeze `_rrf_merge` output as the pre-V23 baseline and assert equality.

---

### Pattern 4: Retrieval-Aware Eviction (VRNK-04)

**What:** Change the sort key in `_maybe_evict` and vacuum to prefer never-retrieved and stale-retrieved rows over mtime-only ordering.

**Current sort** (`memory_store.py:183`):
```python
files.sort(key=lambda p: p.stat().st_mtime)
```

**V23 sort key** (bucket 0 = never-retrieved, bucket 1 = stale-retrieved, bucket 2 = recent — within each bucket, ascending mtime):
```python
def _eviction_key(self, path: Path, telemetry: dict) -> tuple:
    """(bucket, mtime): never-retrieved=0, stale=1, recent=2."""
    mtime = path.stat().st_mtime
    locator = self._locator_from_path(path.parent.name, path)
    entry = telemetry.get(locator)
    if entry is None:
        return (0, mtime)  # never-retrieved — evict first
    last_ts = entry.get("last_retrieved")
    if not last_ts:
        return (0, mtime)
    # "stale" threshold: configurable, default 30 days
    # For simplicity use mtime ordering within stale bucket (D-15)
    return (1, entry.get("last_retrieved", ""))  # ascending = stale-first

# In _maybe_evict, replace:
# files.sort(key=lambda p: p.stat().st_mtime)
# with:
telemetry = self._load_telemetry_compacted()
files.sort(key=lambda p: self._eviction_key(p, telemetry))
```

**Sidecar-absent fallback:** `_load_telemetry_compacted()` returns `{}` when `.retrieval.jsonl` is absent → all files get bucket 0 (never-retrieved) → sort degrades to mtime within bucket → identical to pre-V23 mtime ordering (SPEC constraint verified).

**Pin exemption:** Before the eviction loop, filter out pinned locators:
```python
pins = self._load_pins()  # reads .pins.json → set of locators
files = [f for f in files if self._locator_from_path(source, f) not in pins]
```

**decisions/ exemption:** Already in place at `memory_store.py:161` — unchanged.

---

### Pattern 5: Reindex Drift Gate (VRNK-05) — V19 manifest pattern

**What:** sha256 per file-based source file, stored in `.voss/memory/.reindex-manifest.json`. `--check` exits 1 on drift. Bare `reindex` re-embeds stale entries via chroma upsert.

**V19 manifest pattern** (`code/semantic_index.py:109-124`) — verified:
```python
def _manifest_path(cwd: Path) -> Path:
    return cwd / ".voss-cache" / "code" / "semantic-manifest.json"

def _load_manifest(cwd: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}

def _save_manifest(cwd: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=0, sort_keys=True))
```

**V23 memory manifest** (adapted for D-11):
```python
@property
def _reindex_manifest_path(self) -> Path:
    return self.root / ".reindex-manifest.json"

def _load_reindex_manifest(self) -> dict:
    try:
        return json.loads(self._reindex_manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}  # missing → everything stale

def _save_reindex_manifest(self, data: dict) -> None:
    self._reindex_manifest_path.write_text(
        json.dumps(data, indent=0, sort_keys=True)
    )

def _file_based_sources(self) -> list[Path]:
    """notes/ decisions/ conventions/ only (D-10: turns/ledgers excluded)."""
    return [
        p
        for src in ("notes", "decisions", "conventions")
        for p in (self.root / src).rglob("*")
        if p.is_file()
    ]
```

**Chroma re-embed on stale:** `chroma._collection.upsert(ids=[locator], documents=[text], metadatas=[meta])` — verified in chroma 1.5.9:
```python
# upsert replaces existing document for the same id
col.upsert(ids=['a'], documents=['new text'], metadatas=[{'k':'v'}])
```

**Chroma upsert vs add:** `add` raises on duplicate id; `upsert` is idempotent. Use `upsert` for reindex to handle cases where the item was added at write time but its embedding is now stale.

**Chroma-unavailable exit contract:** If `_maybe_chroma()` returns None, both `reindex` and `reindex --check` print a notice and exit 0 (per SPEC).

**Exit contract** mirrors `voss sync --check` (`voss/cli.py:519-522`):
```python
if check_mode:
    stale = [loc for loc, reason in drift_items]
    if stale:
        for loc in stale:
            click.echo(loc, err=True)
        raise SystemExit(1)
    click.echo("memory index in sync")
    return
```

---

### Pattern 6: Pinned Tier (VRNK-06)

**What:** `.pins.json` sidecar stores pinned locators. Pinned memories prepend inside the V18/V19 variable region as a non-evictable block. Cap ~500 tok total, ~200 tok per item.

**`.pins.json` format** (committed per D-02):
```json
{
  "pins": [
    {"locator": "convention:my-rule", "pinned_at": "2026-06-12T10:00:00+00:00"}
  ]
}
```

**Pin load:**
```python
@property
def _pins_path(self) -> Path:
    return self.root / ".pins.json"

def _load_pins(self) -> set[str]:
    try:
        data = json.loads(self._pins_path.read_text())
        return {p["locator"] for p in data.get("pins", []) if "locator" in p}
    except (OSError, json.JSONDecodeError):
        return set()
```

**V18 allocator integration** (D-07): The allocator `ContextAllocator.pack()` receives `iter_records` and a `packing_budget`. The pinned block is passed as a **fixed-cost prefix** to the packing budget calculation — similar to `code_recall_text` which rides the variable region as an injected system block (D-07 says it is NOT the stable region; stable region is FOLD-only per V18 gotcha).

The pinned tier is delivered by adding a `pinned_memory_text: str` parameter to `_compose_system_blocks()` in `agent.py` — same pattern as `code_recall_text` at L379. The `_code_recall_kwargs` pattern at `cli.py:841` provides the signature-guard idiom to use.

**Injection site in `recall()` (extended):** After the standard recall and optional rescore, `recall()` may also return a `pinned` list (or pin injection happens at a higher call site in `tools.py`/`cli.py`). Given D-07 specifies "enters the V18 variable region", pin injection happens at the system-prompt composition level, not inside `recall()`. The planner must thread a `pinned_memory_text` block through `_compose_system_blocks` → `run_turn` → `cli.py` call sites.

**Token accounting:** Use `_default_token_count` (same as code_recall injection in `cli.py:833`). Soft cap per-item ~200 tok, tier cap ~500 tok total.

---

### Pattern 7: CLI Verb Registration (VRNK-07)

**What:** Five new commands under `memory_group` in `memory_cli.py:18`.

**Existing pattern** (verified `memory_cli.py`):
```python
@memory_group.command("vacuum")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def memory_vacuum_cmd(cwd_str: str) -> None:
    ...
```

**New verbs:**
```python
@memory_group.command("pin")          # pin <locator> [--global]
@memory_group.command("unpin")        # unpin <locator> [--global]
@memory_group.command("list")         # list [--source] [--pinned] [--json] [--global]
@memory_group.command("show")         # show <locator> [--global]
@memory_group.command("reindex")      # reindex [--check] [--global]
```

All commands follow `--cwd` + `--global` flag pattern (D-12 mirrors V21's `vacuum --global` convention). Unknown locator → `sys.exit(1)` with stderr message.

---

### Anti-Patterns to Avoid

- **Writing telemetry inside `recall()`:** Record telemetry in the callers (tools.py, auto-injection sites), not inside `recall()` itself — callers know whether they are agent-path or CLI-path. Putting telemetry in `recall()` would require a flag parameter and makes the no-touch CLI contract fragile.
- **Mutating memory files in any recall path:** Memory file mtimes must be immutable to recall (SPEC hard constraint). All V23 writes go to sidecar files under `.voss/memory/`.
- **Adding `.pins.json` to gitignore:** D-02 explicitly commits pins. Only `.retrieval.jsonl` and `.reindex-manifest.json` are gitignored.
- **Post-fusion score floors:** D-06 mandates pre-fusion only. Post-fusion drops would punish BM25-only degraded installs.
- **Injecting pinned block into the stable region:** D-07 + V18 gotcha — stable region is FOLD-only. Pin block goes into the variable region (same as `code_recall_text`).
- **Calling `_load_memory_config()` inside `_rrf_merge` (static method):** `_rrf_merge` is a `@staticmethod`. Floor/rescore config reads must happen in the calling instance methods (`_bm25_recall`, `_chroma_recall`, `recall()`).
- **Chroma upsert vs add for reindex:** Use `upsert` — `add` raises `DuplicateIDError` on already-indexed entries.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File locking | Custom lock files | `portalocker.Lock(LOCK_EX | LOCK_NB)` | Already in project; handles contention, lock release on crash |
| Hash manifest | Custom digest tracking | Pattern from `code/semantic_index.py:92-124` (`_file_hash`, `_load_manifest`, `_save_manifest`) | Copy the exact V19 pattern; do not reinvent |
| JSONL append log | Custom log format | `.tombstones.jsonl` pattern — one JSON object per line, corrupt-line tolerant | Proven in production vacuum |
| Telemetry compaction | Custom counter logic | Fold `.retrieval.jsonl` in vacuum pass (analogous to `_vacuum_jsonl` JSONL compaction) | Existing two-pass vacuum pattern handles atomicity |
| Chroma re-embed | Full collection rebuild | `_collection.upsert(ids=[id], documents=[text], metadatas=[meta])` | Chroma 1.5.9 upsert is idempotent; only stale entries need re-embed |
| Token counting for pins | Custom tokenizer | `_default_token_count` from `voss.harness.agent` | Same counter V18 and V19 use; consistent budget accounting |

**Key insight:** The tombstone lifecycle (append → vacuum compact) is the exact template for the telemetry lifecycle. The V19 hash manifest is the exact template for the reindex manifest. Copy these patterns verbatim.

---

## Runtime State Inventory

> Not a rename/refactor phase. Skip.

---

## Common Pitfalls

### Pitfall 1: Telemetry on CLI paths breaks the no-touch contract
**What goes wrong:** If telemetry is recorded inside `recall()` unconditionally, `/recall` REPL command, `voss recall` CLI, and `voss memory list/show` all write telemetry, corrupting the count.
**Why it happens:** `recall()` is called from both agent tools and CLI; there's no internal flag in the current API.
**How to avoid:** Record telemetry only in callers that are agent-path (tools.py `memory_recall`, auto-injection render). Do NOT add a `record_telemetry=True` kwarg to `recall()` — that would require changing every call site. Instead, callers explicitly call `store._record_telemetry(hits)` after `recall()`.
**Warning signs:** Test for `retrieval_count > 0` after a CLI recall — must stay 0.

### Pitfall 2: chroma 1.5.9 has no `clear_system_cache` function
**What goes wrong:** Code imports `from chromadb.utils.embedding_functions import clear_system_cache` and crashes.
**Why it happens:** This function was removed/moved in chroma 1.5.x — V19 memory confirms it's not available.
**How to avoid:** Do not import `clear_system_cache`. The V19 codebase already avoids this.
**Warning signs:** `ImportError: cannot import name 'clear_system_cache'`.

### Pitfall 3: DefaultEmbeddingFunction loads on import
**What goes wrong:** Creating a `DefaultEmbeddingFunction()` triggers model download in tests.
**Why it happens:** Verified: `DefaultEmbeddingFunction()` succeeds but may trigger network/disk ops.
**How to avoid:** Test scaffold must use `chroma_disabled_env` fixture (monkeypatches `chromadb = None`) for all tests where chroma is not under test. Exact pattern in `tests/harness/conftest.py:278`.
**Warning signs:** Tests slow > 10s; unexpected network activity.

### Pitfall 4: BM25 relative floor with zero-score corpus
**What goes wrong:** If all BM25 scores are 0 (empty query or all filtered by score-≤-0 check), `top_score` is 0.0 and `score >= top_score * 0.1` = `score >= 0.0` passes everything including 0-score rows.
**Why it happens:** The floor is relative-to-top but top is 0.
**How to avoid:** Apply relative floor only when `ranked` is non-empty AND top score > 0. The existing score-≤-0 filter at L554-561 already eliminates 0-score rows before ranking, so the floor applies only to positive-scored rows. Check: `if ranked and ranked[0][0] > 0`.
**Warning signs:** `test_no_match_returns_zero_hits` fails with hits returned.

### Pitfall 5: Rescore with missing `last_retrieved` in compacted telemetry
**What goes wrong:** Compacted telemetry has a locator entry but no `last_retrieved` field (e.g., events were all missing timestamps). Rescore crashes on `datetime.fromisoformat(None)`.
**Why it happens:** Corrupt or partially-written JSONL events.
**How to avoid:** Rescore formula handles `last_retrieved = None` → `recency_factor = 0.0` (no recency boost). Guard: `if last_ts:`.
**Warning signs:** `TypeError` in rescore with `fromisoformat` argument.

### Pitfall 6: Pin locator format must match `_locator_from_path`
**What goes wrong:** Pin is stored as `"convention:my-slug"` but `_locator_from_path` returns `"convention:my-slug"` — these must match exactly or pin exemption in eviction never fires.
**Why it happens:** `make_id("convention", stem)` = `"convention:stem"` (L62-65). `_locator_from_path("conventions", path)` = `make_id("convention", path.stem)`. These match — but only if the stem is stable. JSONL sources use `make_id("turn", stem, seq=idx)` which includes sequence.
**How to avoid:** Pin verbs must store locators using the same `_locator_from_path` output. Show the full composite ID to operators in `voss memory list`.
**Warning signs:** `voss memory pin note:my-note` → eviction still removes the file.

### Pitfall 7: `.retrieval.jsonl` vacuum compaction must not include CLI-path non-events
**What goes wrong:** If telemetry events from the CLI path leak in, `retrieval_count` is inflated and rescore is wrong.
**Why it happens:** Defensive coding that "helpfully" records everywhere.
**How to avoid:** Only `_record_telemetry` callers that are agent-path. If in doubt, check call stack — `tools.py` = agent; `cli.py` slash commands = CLI.
**Warning signs:** `retrieval_count` increments on `voss memory show`.

### Pitfall 8: V21 adds `root_override` and `make_global_store` — V23 plans must use post-V21 `MemoryStore.__init__` signature
**What goes wrong:** V23 plan creates a `MemoryStore(cwd)` and uses V20-era signature; V21 adds `root_override: Path | None = None` as a new kwarg.
**Why it happens:** V23 executes after V21; the code is post-V21 when V23 runs.
**How to avoid:** V23 plan tasks reference the post-V21 `MemoryStore(cwd, *, cap_bytes=..., root_override=None)` signature. The V23 extension itself does not need to change the signature again — it only adds new methods.
**Warning signs:** `TypeError: __init__() got unexpected keyword argument 'root_override'` on a test that tries to use the global store.

---

## Code Examples

Verified patterns from the live codebase:

### Existing `_lock` portalocker pattern (`memory_store.py:134`)
```python
@contextmanager
def _lock(self, source: str):
    lock_path = self.root / ".locks" / f"{source}.lock"
    try:
        with portalocker.Lock(
            str(lock_path), mode="a",
            flags=portalocker.LOCK_EX | portalocker.LOCK_NB, timeout=0,
        ) as fh:
            yield fh
    except portalocker.exceptions.LockException:
        print(f"memory.{source} busy — skipping write", file=sys.stderr)
        yield None
```

### `_load_memory_config()` pattern (`memory_store.py:205`)
```python
def _load_memory_config(self) -> dict:
    config_path = self.cwd / ".voss" / "config.yml"
    if not config_path.exists():
        return {}
    try:
        import yaml
        data = yaml.safe_load(config_path.read_text()) or {}
    except Exception:
        return {}
    memory = data.get("memory") if isinstance(data, dict) else None
    return memory if isinstance(memory, dict) else {}
```

**New config keys for V23:**
```yaml
# .voss/config.yml [memory] section
memory:
  chroma_floor: 0.25       # VRNK-02 (0 = disable)
  bm25_floor_ratio: 0.1    # VRNK-02 (0 = disable)
  rescore: false            # VRNK-03 (default-off)
  rescore_half_life_days: 7.0
  rescore_w_recency: 0.3
  rescore_w_freq: 0.2
  rescore_freq_scale: 10.0
  pin_cap_tokens: 500       # VRNK-06 tier cap
  pin_item_cap_tokens: 200  # VRNK-06 per-item cap
```

### V19 hash manifest pattern (`code/semantic_index.py:92-124`)
```python
def _file_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()

def _manifest_path(cwd: Path) -> Path:
    return cwd / ".voss-cache" / "code" / "semantic-manifest.json"

def _load_manifest(cwd: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}

def _save_manifest(cwd: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=0, sort_keys=True))
```

### `sync --check` exit contract (`voss/cli.py:519-522`)
```python
if result.drifted:
    click.echo(f"{len(result.drifted)} artifact(s) drifted")
    raise SystemExit(1)
click.echo("all artifacts in sync")
```

### Chroma upsert API (verified chroma 1.5.9)
```python
# Idempotent re-embed for a stale locator
chroma._collection.upsert(
    ids=[locator],
    documents=[fresh_text],
    metadatas=[{"source_type": src, "path": str(path), "tombstoned": False}],
)
```

### `code_recall_text` injection pattern for pinned block (`cli.py:841-853`)
```python
def _code_recall_kwargs(run_turn_fn, cwd, task_text, session_id=None) -> dict:
    try:
        import inspect as _inspect
        if "code_recall_text" not in _inspect.signature(run_turn_fn).parameters:
            return {}
    except (TypeError, ValueError):
        return {}
    text = _render_code_recall_text(cwd, task_text, session_id=session_id)
    return {"code_recall_text": text} if text else {}
```
The pinned memory text uses the same signature-guard kwarg pattern: add `pinned_memory_text: str = ""` to `run_turn`, guard with `inspect.signature` at call sites, thread through `_compose_system_blocks`.

### Eviction test pattern (`tests/harness/test_memory_eviction.py`)
```python
def test_oldest_evicted_first_within_source(tmp_voss_repo):
    # Seed files with explicit mtimes
    for i, ts in enumerate((1000, 2000, 3000)):
        p = turns_dir / f"seed-{i}.jsonl"
        p.write_text(body + "\n")
        os.utime(p, (ts, ts))
    store.write_turn(...)
    assert not paths[0].exists()   # oldest evicted
    assert paths[2].exists()       # newest survived
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No quality floor | Pre-fusion floor default-on | V23 | Junk hits no longer fill top_k |
| Mtime-only eviction | Retrieval-aware eviction (never-retrieved first) | V23 | Hot memories survive |
| No drift detection | Hash manifest + `--check` exit gate | V23 | Hand-edited mirror files are detectable |
| No pinned tier | Operator-curated always-inject tier | V23 | Must-never-miss conventions always present |
| No telemetry | Append-log sidecar + vacuum compaction | V23 | Rescore and eviction can use recall history |

**Deprecated/outdated:**
- mtime-as-eviction-proxy: Still the fallback when sidecar is absent, but sidecar-aware ordering is the primary path post-V23.

---

## Open Questions

1. **Post-V21 global store pin injection site**
   - What we know: V23's pin block must inject for both project and global stores when V21 lands (D-09); global store's `.pins.json` lives under `~/.voss/memory/.pins.json`
   - What's unclear: V21 plan is not yet executed — the exact call sites where global store recall is fused may differ from the V21-01-PLAN description; the planner must verify post-V21 shape before wiring global pin injection
   - Recommendation: Plan V23-01 (Wave 0 scaffold) with a stub test for global pin injection; wire it in the last wave once V21 code is merged

2. **Vacuum compaction of `.retrieval.jsonl` — fold strategy**
   - What we know: D-15 says "count summation + max timestamp" is the fold output (Claude's discretion)
   - What's unclear: Whether vacuum compaction should run as a separate pass or piggyback on the existing `vacuum()` method's three-pass structure
   - Recommendation: Piggyback on `vacuum()` as a fourth pass (after chroma tombstone delete, before tombstone truncation) using the same lock pattern as `_vacuum_jsonl`

3. **`voss memory list` output format for the no-memory-store case**
   - What we know: Existing CLI verbs exit 1 if `store.root` doesn't exist
   - What's unclear: Should `list --pinned` return empty vs exit 1 when no `.pins.json` exists (but store does exist)?
   - Recommendation: Empty list is correct — no pins ≠ store error. Only exit 1 on missing store root.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| chromadb | VRNK-05 reindex, VRNK-02 chroma floor | ✓ | 1.5.9 | All features degrade gracefully; reindex exits 0 with notice; floors apply BM25-only |
| rank-bm25 | VRNK-02 BM25 floor | ✓ | 0.2.2 | No fallback needed — always available |
| portalocker | VRNK-01 telemetry locking | ✓ | 3.2.0 | No fallback needed — always available |
| pyyaml | _load_memory_config for floor/rescore config | ✓ | in .venv | Default values apply when config absent |

**Missing dependencies with no fallback:** none — all needed packages are already installed.

---

## Validation Architecture

> Nyquist validation enabled (workflow.nyquist_validation = true in .planning/config.json).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (detected in .venv) |
| Config file | pytest.ini or pyproject.toml (project standard) |
| Quick run command | `.venv/bin/python -m pytest tests/harness/test_memory_store.py tests/harness/test_memory_eviction.py -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/memory tests/harness/test_memory_*.py tests/code_recall -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VRNK-01 | Agent-path recall increments telemetry, CLI does not | unit | `.venv/bin/python -m pytest tests/harness/test_memory_telemetry.py -x` | ❌ Wave 0 |
| VRNK-01 | Memory file bytes/mtimes unchanged by any recall | unit | `.venv/bin/python -m pytest tests/harness/test_memory_telemetry.py::test_mtime_unchanged -x` | ❌ Wave 0 |
| VRNK-02 | No-match query returns 0 hits with floors on | unit | `.venv/bin/python -m pytest tests/harness/test_memory_floors.py::test_no_match_returns_zero_hits -x` | ❌ Wave 0 |
| VRNK-02 | Disable knob restores fill behavior | unit | `.venv/bin/python -m pytest tests/harness/test_memory_floors.py::test_floor_disabled_restores_fill -x` | ❌ Wave 0 |
| VRNK-03 | Fixed telemetry fixture → deterministic re-ranking | unit | `.venv/bin/python -m pytest tests/harness/test_memory_rescore.py::test_rescore_deterministic -x` | ❌ Wave 0 |
| VRNK-03 | Rescore off (default) → byte-identical output | unit | `.venv/bin/python -m pytest tests/harness/test_memory_rescore.py::test_rescore_off_byte_identical -x` | ❌ Wave 0 |
| VRNK-03 | Empty telemetry + rescore on = no-op | unit | `.venv/bin/python -m pytest tests/harness/test_memory_rescore.py::test_empty_telemetry_noop -x` | ❌ Wave 0 |
| VRNK-04 | Over-quota eviction removes never-retrieved before old-but-recently-retrieved | unit | `.venv/bin/python -m pytest tests/harness/test_memory_eviction.py::test_retrieval_aware_eviction -x` | ❌ Wave 0 (add to existing file) |
| VRNK-04 | No sidecar → mtime fallback | unit | `.venv/bin/python -m pytest tests/harness/test_memory_eviction.py::test_eviction_mtime_fallback_no_sidecar -x` | ❌ Wave 0 |
| VRNK-05 | Hand-edit → `--check` exit 1 + stale locator | unit | `.venv/bin/python -m pytest tests/harness/test_memory_reindex.py::test_check_detects_drift -x` | ❌ Wave 0 |
| VRNK-05 | `reindex` repairs; subsequent `--check` → exit 0 | unit | `.venv/bin/python -m pytest tests/harness/test_memory_reindex.py::test_reindex_repairs -x` | ❌ Wave 0 |
| VRNK-05 | Chroma-absent: both verbs exit 0 with notice | unit | `.venv/bin/python -m pytest tests/harness/test_memory_reindex.py::test_chroma_absent_no_error -x` | ❌ Wave 0 |
| VRNK-06 | Pinned memory in assembled agent context without recall match | unit | `.venv/bin/python -m pytest tests/harness/test_memory_pins.py::test_pinned_always_injected -x` | ❌ Wave 0 |
| VRNK-06 | Cap overflow warns; survives over-quota eviction | unit | `.venv/bin/python -m pytest tests/harness/test_memory_pins.py::test_pin_cap_overflow_warns tests/harness/test_memory_pins.py::test_pinned_survives_eviction -x` | ❌ Wave 0 |
| VRNK-07 | pin → list --pinned shows; unpin → list --pinned empty | unit | `.venv/bin/python -m pytest tests/harness/test_memory_cli_verbs.py::test_pin_unpin_list -x` | ❌ Wave 0 |
| VRNK-07 | show → nonzero retrieval_count; unknown locator → exit 1 | unit | `.venv/bin/python -m pytest tests/harness/test_memory_cli_verbs.py::test_show_telemetry tests/harness/test_memory_cli_verbs.py::test_unknown_locator_exits_1 -x` | ❌ Wave 0 |
| VRNK-08 | Full memory + code_recall suites green | regression | `.venv/bin/python -m pytest tests/memory tests/harness/test_memory_*.py tests/code_recall -x -q` | ✅ (existing suites) |
| VRNK-08 | Byte-identical baseline test | unit | `.venv/bin/python -m pytest tests/harness/test_memory_rescore.py::test_rescore_off_byte_identical -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/harness/test_memory_store.py tests/harness/test_memory_eviction.py -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/memory tests/harness/test_memory_*.py tests/code_recall -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
New test files required:
- [ ] `tests/harness/test_memory_telemetry.py` — covers VRNK-01 (telemetry append, mtime invariant, CLI no-touch)
- [ ] `tests/harness/test_memory_floors.py` — covers VRNK-02 (chroma floor, BM25 floor, disable knob)
- [ ] `tests/harness/test_memory_rescore.py` — covers VRNK-03 (deterministic fixture, byte-identical off-path, empty-telemetry no-op)
- [ ] `tests/harness/test_memory_reindex.py` — covers VRNK-05 (drift detection, repair, chroma-absent exit 0)
- [ ] `tests/harness/test_memory_pins.py` — covers VRNK-06 (always-inject, eviction exempt, cap overflow)
- [ ] `tests/harness/test_memory_cli_verbs.py` — covers VRNK-07 (pin/unpin/list/show/reindex CLI)

Extend existing files:
- [ ] `tests/harness/test_memory_eviction.py` — add VRNK-04 retrieval-aware eviction tests

All new tests use `tmp_voss_repo` fixture from `tests/harness/conftest.py` (creates `.voss/memory/` layout). Use `chroma_disabled_env` for tests where chroma is not under test (per existing conftest.py:278 pattern). Tests must import from `voss.harness.memory_store` only — no test should reach into `voss_runtime.memory.semantic` directly.

---

## Security Domain

> Security enforcement enabled (no explicit `security_enforcement: false` in config).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Locator strings from CLI — validate against `make_id` format before writing to `.pins.json`; reject unknown locators with exit 1 |
| V6 Cryptography | no | sha256 for integrity (manifest), not secrecy — no secret material |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed JSONL in `.retrieval.jsonl` | Tampering | Corrupt-line tolerant reader (try/except json.JSONDecodeError on each line — same as tombstones reader at L237) |
| Locator injection via CLI (`pin "../../etc/passwd"`) | Tampering | Validate locator against known `make_id` prefixes (turn:/note:/convention:/decision:/ledger:) before writing to `.pins.json` |
| `.pins.json` format corruption | Tampering | Wrap `_load_pins()` in try/except; return empty set on parse failure |
| Chroma reindex re-embeds attacker-controlled content | Tampering | Not applicable — reindex only re-embeds existing memory files already written by the project's own write paths |

---

## Sources

### Primary (HIGH confidence)
- `voss/harness/memory_store.py` — MemoryStore full source: `recall()` L411, `_rrf_merge` L431, `_chroma_recall` L447, `_bm25_recall` L530, token-overlap rescue L555, `_maybe_evict` L151, `vacuum()` L720, `_lock` L134, `_VOSS_MEMORY_GITIGNORE` L37, `_load_memory_config()` L205 — read in this session
- `voss/harness/memory_cli.py` — Click group registration pattern for existing verbs (vacuum/adopt/size) — read in this session
- `voss/harness/tools.py` — `memory_recall` agent tool L178-214 (telemetry recording site) — read in this session
- `voss/harness/context_allocator.py` — ContextAllocator.pack() L198, PackingProfile L39, stable-region-is-FOLD-only pattern — read in this session
- `voss/harness/code/semantic_index.py` — V19 hash manifest pattern `_file_hash`/`_load_manifest`/`_save_manifest` L92-124 — read in this session
- `voss/harness/cli.py` — `_render_code_recall_text` L801, `_code_recall_kwargs` L841, `voss recall` CLI L4835, all `MemoryStore` instantiation sites — read in this session
- `voss/harness/agent.py` — `_compose_system_blocks` L373, `code_recall_text` injection pattern L379/396 — read in this session
- `.planning/phases/V21-global-cross-project-memory/V21-CONTEXT.md` — `root_override`, `make_global_store`, post-V21 `MemoryStore.__init__` signature, `--global` verb convention — read in this session
- `.planning/phases/V21-global-cross-project-memory/V21-01-PLAN.md` — exact post-V21 API: `MemoryStore(cwd, *, cap_bytes=..., root_override: Path | None = None)`, `make_global_store()` factory, `attach_memory_tools(tools, *, store, session_id, global_store=None)` — read in this session
- `tests/harness/test_memory_eviction.py` — eviction test pattern (mtime seeding with `os.utime`) — read in this session
- `tests/harness/conftest.py` — `tmp_voss_repo`, `chroma_disabled_env` fixture patterns — read in this session
- `tests/harness/test_agent_packing.py:203` — `test_no_pack_byte_identical` as the byte-identical test pattern — read in this session
- `voss_runtime/memory/semantic.py` — SemanticMemory wrapper; `_collection.upsert`/`delete`/`update` — read in this session
- `voss/cli.py:519-522` — `sync --check` exit contract (`raise SystemExit(1)` on drift) — read in this session

### Secondary (MEDIUM confidence — runtime verification)
- chromadb 1.5.9 upsert/delete/update API — verified via `.venv/bin/python` live test in this session
- BM25Okapi score range (non-negative numpy float64, ATIRE variant) — verified via `.venv/bin/python` live test
- `clear_system_cache` absent in chroma 1.5.9 — verified via `.venv/bin/python` live ImportError test

### Tertiary (LOW confidence)
- Rescore formula weights (D-13 is Claude's discretion) — recommended values based on training knowledge; planner may adjust

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | stdlib `hashlib`, `json`, `datetime` are used for sidecar files | Standard Stack | No risk — these are standard Python stdlib modules, always available |
| A2 | Rescore formula weights (half-life=7d, w_recency=0.3, w_freq=0.2) produce "similarity ordering dominates" | Pattern 3 (rescore) | Boost could be too large, causing rescore to override similarity; planner should verify with the determinism fixture |
| A3 | V21 code is not yet merged; V23 plan references post-V21 API based on V21-01-PLAN.md description | Pitfall 8, VRNK-08 | If V21 ships with different signature, V23 Wave 0 test stubs will need adjustment |

**If this table is empty:** All other claims in this research were verified against live source code or runtime in this session.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages are existing project dependencies verified via pip show
- Architecture: HIGH — grounded in direct source reads with line numbers
- Pitfalls: HIGH — derived from live code inspection and V19/V18 gotcha records
- V21 post-merge shape: MEDIUM — based on V21-01-PLAN.md plan description, not merged code

**Research date:** 2026-06-12
**Valid until:** 2026-07-12 (stable domain; chroma 1.5.x API stable; BM25 scoring properties stable)
