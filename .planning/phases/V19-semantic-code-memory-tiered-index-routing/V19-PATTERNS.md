# Phase V19: Semantic Code Memory + Tiered Index Routing - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 12 new/modified files
**Analogs found:** 12 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/code/semantic_index.py` | service | CRUD + event-driven | `voss/harness/memory_store.py` | role-match (same lazy-chroma + BM25 + RRF contract) |
| `voss/harness/code/service.py` (modify) | service | request-response | `voss/harness/code/service.py` (existing) | exact (add lazy property) |
| `voss/harness/tools.py` (modify) | utility | request-response | `voss/harness/tools.py:159` (`attach_memory_tools`) | exact |
| `voss/harness/cli.py` (modify — `recall_cmd` + injection wiring) | controller | request-response | `voss/harness/memory_cli.py` + `voss/harness/cli.py:do_cmd` | exact |
| `voss/harness/agent.py` (modify — `_compose_system_blocks`) | middleware | request-response | `voss/harness/agent.py:372` (existing function) | exact |
| `voss/harness/config.py` (modify — `[code_recall]` section) | config | transform | `voss/harness/config.py:233` (`_parse_model_tiers_section`) | exact |
| `voss/harness/memory_store.py` (modify — extend `Hit`) | model | transform | `voss/harness/memory_store.py:41` (`Hit` dataclass) | exact |
| `voss/harness/recorder.py` (modify — enrichment ledger row) | utility | batch | `voss/harness/recorder.py:143` (`_append_savings_record`) | exact |
| `tests/code_recall/__init__.py` | test | n/a | `tests/memory/__init__.py` | role-match |
| `tests/code_recall/conftest.py` | test | n/a | `tests/memory/test_semantic.py:4-11` + `tests/harness/conftest.py` | role-match |
| `tests/code_recall/test_chunker.py` | test | CRUD | `tests/memory/test_semantic.py` | role-match |
| `tests/code_recall/test_*.py` (remaining 7 test files) | test | various | `tests/harness/test_agent_packing.py` + `tests/memory/test_semantic.py` | role-match |

---

## Pattern Assignments

### `voss/harness/code/semantic_index.py` (service, CRUD + event-driven)

**Analog:** `voss/harness/memory_store.py`

**Imports pattern** (`memory_store.py:1-24`):
```python
from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rank_bm25 import BM25Okapi
from voss_runtime.memory import SemanticMemory
```

**Lazy Chroma init pattern** (`memory_store.py:108-126`) — copy this guard exactly:
```python
def _maybe_chroma(self) -> "SemanticMemory | None":
    if self._chroma is not None:
        return self._chroma
    if self._chroma_unavailable:
        return None
    try:
        chroma = SemanticMemory(
            persist_dir=str(self.root / "chroma"),
            collection_name="voss_memory",
        )
    except (ModuleNotFoundError, ImportError):
        self._chroma_unavailable = True
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"memory: chroma init failed ({exc}); using BM25 fallback", file=sys.stderr)
        self._chroma_unavailable = True
        return None
    self._chroma = chroma
    return chroma
```
For `semantic_index.py`, the equivalent is `_maybe_semantic()` with:
- `persist_dir=str(cwd / ".voss-cache" / "code" / "chroma")`
- `collection_name="voss_code"`

**Composite ID convention** (`memory_store.py:56-60`) — same prefix style:
```python
def make_id(source: str, locator: str, seq: int | None = None) -> str:
    """D-04 composite ID format <source>:<locator>:<seq>."""
    if seq is None:
        return f"{source}:{locator}"
    return f"{source}:{locator}:{seq:03d}"
```
For code chunks use: `f"code:{rel_path}:{seq:03d}"` (prefix `code:` guarantees no collision with `turn:`, `note:`, etc.)

**BM25 tokenizer** (`memory_store.py:63-68`) — reuse exactly, do not copy:
```python
def _bm25_tokenize(text: str) -> list[str]:
    """Tokenize memory text for lexical recall, including code-like symbols."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    spaced = re.sub(r"[_\-\./\\]+", " ", spaced)
    spaced = re.sub(r"[^\w\s]", " ", spaced)
    return [tok for tok in spaced.lower().split() if tok]
```
Import it via `from voss.harness.memory_store import _bm25_tokenize`.

**RRF merge** (`memory_store.py:425-440`) — call as static method, do not copy:
```python
@staticmethod
def _rrf_merge(rankings: list[list[Hit]], *, top_k: int, k: int = 60) -> list[Hit]:
    scores: dict[str, float] = {}
    carriers: dict[str, Hit] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            carriers.setdefault(hit.locator, hit)
            scores[hit.locator] = scores.get(hit.locator, 0.0) + (1.0 / (k + rank))
    fused: list[Hit] = []
    for locator, score in scores.items():
        carrier = carriers[locator]
        fused.append(dataclasses.replace(carrier, score=score))
    fused.sort(key=lambda hit: (-hit.score, hit.locator))
    return fused[:top_k]
```
Call as `MemoryStore._rrf_merge([bm25_hits, chroma_hits], top_k=top_k)`.

**Hash pattern** (`voss/harness/code/index.py:187`) — identical to M10, use same call:
```python
digest = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
```

**M10 SQLite read pattern** (`voss/harness/code/index.py:188-208`) — read symbols table:
```python
# Read-only connection, same db path M10 builds
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
```
`db_path` = `cwd / ".voss-cache" / "code" / "index.db"` (same as `index._get_db_path()`).

**Daemon thread pattern** — mirror `CodeIntelService.for_cwd()` (`service.py:26-32`) but add a `threading.Event`:
```python
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
            self._code_index.build()
        except Exception as exc:
            print(f"code index build failed: {exc}", file=sys.stderr)
        finally:
            self._ready.set()  # always signal ready (degraded if failed)

    def is_ready(self) -> bool:
        return self._ready.is_set()
```

**Chroma delete-then-upsert for incremental reindex** — verified chromadb 1.5.9 API:
```python
# Stale chunks: delete by id list, then upsert new
if old_ids:
    sem._collection.delete(ids=old_ids)
sem._collection.upsert(
    documents=texts,
    ids=chunk_ids,
    metadatas=metas,
)
```
Never use `add()` — raises `DuplicateIDError` on existing ids.

---

### `voss/harness/code/service.py` (modify — add lazy `CodeIndexService` property)

**Analog:** `voss/harness/code/service.py` (existing, all lines)

**Pattern to extend** (`service.py:21-32`):
```python
class CodeIntelService:
    def __init__(self, cwd: Path, session_id: str | None = None):
        self.cwd = cwd.resolve()
        self.session_id = session_id

    @classmethod
    def for_cwd(cls, cwd: Path, session_id: str | None = None, renderer: Any = None) -> "CodeIntelService":
        try:
            build_index(cwd)
        except Exception:
            pass
        return cls(cwd, session_id)
```

Add a lazy property using the same `hasattr` pattern already used for `_registry` (`service.py:117-119`):
```python
def _get_registry(self) -> LspRegistry:
    if not hasattr(self, "_registry") or self._registry is None:
        self._registry = LspRegistry(self.cwd, self.session_id or "default")
    return self._registry
```
Mirror this: add `_get_code_index_service() -> CodeIndexService` using identical guard pattern.

---

### `voss/harness/tools.py` (modify — `attach_code_recall_tool`)

**Analog:** `voss/harness/tools.py:159-215` (`attach_memory_tools`)

**Tool registration pattern** (`tools.py:159-215`):
```python
def attach_memory_tools(tools: dict[str, "ToolEntry"], *, store, session_id: str) -> None:
    @tool(
        name="memory_recall",
        description="Search durable project memory by query ...",
    )
    async def memory_recall(query: str, top_k: int = 5, source: str | None = None) -> str:
        ...
        hits = store.recall(query, top_k=top_k, source=source)
        if not hits:
            return "(no hits)"
        lines: list[str] = []
        for h in hits:
            lines.append(f"[{h.source}] {h.locator} (score {h.score:.2f})")
            excerpt = (h.excerpt or "").replace("\n", " ")[:160]
            if excerpt:
                lines.append(f"  {excerpt}")
        return "\n".join(lines)

    tools["memory_recall"] = ToolEntry(
        descriptor=memory_recall,
        is_mutating=False,
        group="memory",
        scope_requirements=("memory",),
    )
```

For `attach_code_recall_tool`, use identical shape:
- Function name: `attach_code_recall_tool(tools, *, code_index_service)`
- Tool name: `"code_recall"`
- `group="code"`, `scope_requirements=("code",)` — matches existing code tools at `tools.py:829-832`
- `is_mutating=False`

**Existing code tools placement** (`tools.py:829-832`) — insert `code_recall` alongside:
```python
result["code_search"] = ToolEntry(descriptor=code_search, is_mutating=False, group="code", scope_requirements=("code",))
result["find_definition"] = ToolEntry(descriptor=find_definition, is_mutating=False, group="code", scope_requirements=("code",))
result["find_references"] = ToolEntry(descriptor=find_references, is_mutating=False, group="code", scope_requirements=("code",))
result["code_refresh"] = ToolEntry(descriptor=code_refresh, is_mutating=False, group="code", scope_requirements=("code",))
```
Call `attach_code_recall_tool(result, code_index_service=...)` at the same `make_toolset` call sites.

---

### `voss/harness/cli.py` (modify — `recall_cmd` + injection wiring)

**Analog A — click command structure:** `voss/harness/memory_cli.py` (all lines)

**Click group/command pattern** (`memory_cli.py:18-40`):
```python
@click.group("memory")
def memory_group() -> None:
    """Manage Voss project memory store."""

@memory_group.command("vacuum")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def memory_vacuum_cmd(cwd_str: str) -> None:
    cwd = Path(cwd_str).resolve()
    store = MemoryStore(cwd)
    ...
```

`recall_cmd` is a **top-level command** (not a group), registered directly in `AGENT_COMMANDS` tuple (`cli.py:4558-4594`). Pattern:
```python
@click.command("recall")
@click.argument("query", nargs=-1, required=False)
@click.option("--json", "json_out", is_flag=True)
@click.option("--top", "top_k", default=10, type=int)
@click.option("--refresh", "do_refresh", is_flag=True)
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def recall_cmd(query, json_out, top_k, do_refresh, cwd_str):
    ...
```
Add `recall_cmd` to `AGENT_COMMANDS` tuple (`cli.py:4558`) alongside `memory_group`.

**Analog B — injection wiring in `do_cmd`:** `cli.py:1751` and `cli.py:1807`

The existing `project_index_text` threading pattern to mirror:
```python
# cli.py:1751
project_index_text = _render_project_index_text(cwd)

# cli.py:1807 — passed to run_turn
project_index_text=project_index_text,
```
Add a parallel `code_recall_text = _render_code_recall_text(cwd, text)` at `cli.py:1751` and pass it to `run_turn`. Same pattern applies at `chat_cmd` (`cli.py:2045-2075`).

**Analog C — `/recall` slash command** (`cli.py:640-659`):
```python
def _recall(ctx, args: list[str], _line: str) -> None:
    ...
    hits = store.recall(query, top_k=top_k, source=source)
```
The new `recall_cmd` output format mirrors this: one block per hit, `[source] path:line  score  excerpt`.

---

### `voss/harness/agent.py` (modify — `_compose_system_blocks`)

**Analog:** `voss/harness/agent.py:372-404` (the exact function)

**Current signature** (`agent.py:372-380`):
```python
def _compose_system_blocks(
    *,
    voss_md_block: str,
    cognition_text: str,
    principles_text: str = "",
    project_index_text: str = "",
    prior_context_text: str,
    loop_system: str,
) -> list[dict]:
```

**Surgical change:** add `code_recall_text: str = ""` parameter and insert it in the text tuple after `project_index_text`:
```python
blocks = [
    {"type": "text", "text": text}
    for text in (
        voss_md_block,
        cognition_text,
        principles_text,
        project_index_text,
        code_recall_text,      # NEW — inserted after project_index
        prior_context_text,
        loop_system,
    )
    if text
]
```
The `if text` filter (`agent.py:398`) means empty string default produces zero output — fully backward compatible with all 3 existing call sites. Also update `run_turn()` signature at `agent.py:502-520` to accept `code_recall_text: str = ""` parallel to `project_index_text: str = ""`.

---

### `voss/harness/config.py` (modify — `index_enrich` role via `[model_tiers]`)

**Analog:** `voss/harness/config.py:222-258` (`_parse_model_tiers_section` + `get_model_tiers`)

**Parse pattern** (`config.py:233-258`):
```python
_DEFAULT_MODEL_TIERS: dict[str, str] = {
    "strong": "claude-opus-4-8",
    "cheap":  "claude-haiku-4-5",
    "fast":   "claude-haiku-4-5",
}

def _parse_model_tiers_section(text: str) -> dict[str, str]:
    m = _MODEL_TIERS_BLOCK.search(text)
    if not m:
        return {}
    block = m.group(0)
    return {k: v for k, v in _KV.findall(block)}

def get_model_tiers() -> dict[str, str]:
    merged = dict(_DEFAULT_MODEL_TIERS)
    p = config_path()
    if not p.exists():
        return merged
    try:
        text = p.read_text()
    except OSError:
        return merged
    merged.update(_parse_model_tiers_section(text))
    return merged
```

Add `index_enrich` to `_DEFAULT_MODEL_TIERS` defaults (value `None` or absent — fail-closed) and a `get_index_enrich_model() -> str | None` accessor:
```python
def get_index_enrich_model() -> str | None:
    """Return configured index_enrich model id, or None (fail-closed)."""
    return get_model_tiers().get("index_enrich")  # absent = enrichment off
```
One-line addition to `_DEFAULT_MODEL_TIERS`: `"index_enrich": None` (or simply absent, so `get("index_enrich")` returns `None` by default).

Also need to parse a `[code_recall]` section for `enrich_budget_tokens` and `inject` flag — follow identical regex/text-parse pattern as `_parse_net_rate_limits_section` (`config.py:152-207`).

---

### `voss/harness/memory_store.py` (modify — extend `Hit` dataclass)

**Analog:** `voss/harness/memory_store.py:40-46` (the `Hit` dataclass itself)

**Current definition** (`memory_store.py:40-46`):
```python
@dataclass
class Hit:
    source: str
    locator: str
    score: float
    excerpt: str
    session_id: str | None = None
    ts: str | None = None
```

**Surgical change:** add two optional trailing fields:
```python
    line_start: int | None = None
    line_end: int | None = None
```
All existing memory hits leave these as `None` (no behavior change). Code hits populate them. `_rrf_merge` uses only `hit.locator` for dedup and `dataclasses.replace(carrier, score=score)` for update — both remain correct with extra fields.

---

### `voss/harness/recorder.py` (modify — enrichment ledger row)

**Analog:** `voss/harness/recorder.py:143-161` (`_append_savings_record`)

**Existing write pattern** (`recorder.py:143-161`):
```python
def _append_savings_record(cwd, session_id: str, record: dict) -> None:
    from .session import _sessions_dir

    row = dict(record)
    original = int(row.get("original_tokens_est", 0))
    packed = min(int(row.get("packed_tokens_est", 0)), original)
    row["packed_tokens_est"] = packed
    row["saved_tokens_est"] = max(original - packed, 0)
    path = _sessions_dir(Path(cwd)) / str(session_id) / "token-savings.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
```

The function is unchanged. Enrichment spend writes a new row type via the same call:
```python
from voss.harness.recorder import _append_savings_record

_append_savings_record(cwd, session_id, {
    "iter": 0,
    "original_tokens_est": chunks_count * avg_chunk_tokens,
    "packed_tokens_est": 0,       # no packing
    "method": "enrich",           # distinct from "FOLD"/"DIGEST"
    "enrichment_tokens_used": total_enrich_tokens,
    "enrichment_chunks": enriched_count,
    "saved_usd_est": None,        # cost line, not savings claim
    "model": enrich_model_id,
    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
})
```
Note: `_append_savings_record` clamps `packed_tokens_est` ≤ `original_tokens_est` and forces `saved_tokens_est` ≥ 0, so `packed=0, original>0` produces a nonzero `saved_tokens_est` — consider sending `original_tokens_est=0` for enrichment rows where no packing claim is intended, or document the ledger semantics explicitly.

---

### `tests/code_recall/conftest.py` (test fixture file)

**Analog:** `tests/memory/test_semantic.py:4-11` (fake embed function pattern)

**Core fixture pattern** (`test_semantic.py:4-28`):
```python
def _default_embed_fn():
    try:
        from chromadb.utils import embedding_functions
        return embedding_functions.DefaultEmbeddingFunction()
    except Exception:
        return None

def test_semantic_memory_round_trip(tmp_path, monkeypatch):
    embed_fn = _default_embed_fn()
    if embed_fn is None:
        pytest.skip("chromadb DefaultEmbeddingFunction unavailable")

    from voss_runtime.memory.semantic import SemanticMemory
    monkeypatch.setattr(
        SemanticMemory, "_embedding_function", lambda self: embed_fn
    )
    mem = SemanticMemory(persist_dir=str(tmp_path / "chroma"))
    ...
```

`conftest.py` should expose this as a pytest fixture:
```python
@pytest.fixture
def fake_embed_fn(monkeypatch):
    """Patch SemanticMemory to use DefaultEmbeddingFunction (ONNX, no download, no network)."""
    from chromadb.utils import embedding_functions
    from voss_runtime.memory.semantic import SemanticMemory
    fn = embedding_functions.DefaultEmbeddingFunction()
    monkeypatch.setattr(SemanticMemory, "_embedding_function", lambda self: fn)
    return fn

@pytest.fixture
def indexed_fixture_repo(tmp_path, fake_embed_fn):
    """Tiny 2-file fixture repo with known symbols, pre-indexed."""
    ...  # write minimal Python files, call CodeIndex(tmp_path).build()
    return tmp_path
```

---

### `tests/code_recall/test_chunker.py` (VSEM-01)

**Analog:** `tests/memory/test_semantic.py` — same `tmp_path`+`monkeypatch` pattern

**Test structure** (`test_semantic.py:13-34`):
```python
def test_semantic_memory_round_trip(tmp_path, monkeypatch):
    embed_fn = _default_embed_fn()
    if embed_fn is None:
        pytest.skip("chromadb DefaultEmbeddingFunction unavailable")
    from voss_runtime.memory.semantic import SemanticMemory
    monkeypatch.setattr(SemanticMemory, "_embedding_function", lambda self: embed_fn)
    try:
        mem = SemanticMemory(persist_dir=str(tmp_path / "chroma"))
    except Exception as e:
        pytest.skip(f"SemanticMemory init failed (likely needs network): {e}")
    mem.add("...")
    results = mem.retrieve("...", top_k=2)
    assert results
```

For `test_chunker.py`, skip the Chroma init and just test chunk extraction:
```python
def test_chunks_split_on_symbol_boundaries(tmp_path):
    """VSEM-01: multi-symbol file produces one chunk per symbol region."""
    src = tmp_path / "foo.py"
    src.write_text("def alpha():\n    pass\n\ndef beta():\n    pass\n")
    chunks = extract_chunks(tmp_path / ".voss-cache/code/index.db", "foo.py", src.read_text())
    # expect 2 chunks: one for alpha region, one for beta region
    assert len(chunks) == 2
    assert chunks[0][0] == 1   # alpha starts at line 1
    assert chunks[1][0] == 4   # beta starts at line 4
```

---

### `tests/code_recall/test_code_recall_tool.py` (VSEM-04)

**Analog:** `tests/harness/test_agent_packing.py` — `_run_turn_exec` + `ToolEntry` fixture approach

**Tool registration test pattern** (`test_agent_packing.py:28-46`):
```python
def _make_tool(name: str, result: str) -> ToolEntry:
    async def _impl() -> str:
        return result
    desc = ToolDescriptor(name=name, description=name, parameters={...}, func=_impl)
    return ToolEntry(descriptor=desc, is_mutating=False, group="fs")
```

For `test_code_recall_tool.py`:
```python
def test_registration(tmp_path, fake_embed_fn):
    """VSEM-04: code_recall present in tools dict after attach_code_recall_tool."""
    from voss.harness.tools import ToolEntry, attach_code_recall_tool
    from voss.harness.code.semantic_index import CodeIndexService

    svc = CodeIndexService(tmp_path)
    tools: dict = {}
    attach_code_recall_tool(tools, code_index_service=svc)
    assert "code_recall" in tools
    assert isinstance(tools["code_recall"], ToolEntry)
    assert tools["code_recall"].group == "code"
```

---

## Shared Patterns

### Lazy Import Guard (chromadb optional)

**Source:** `voss/harness/memory_store.py:108-126`
**Apply to:** `voss/harness/code/semantic_index.py` (`_maybe_semantic` method), any function that touches Chroma

The exact pattern — try `SemanticMemory(...)`, catch `(ModuleNotFoundError, ImportError)` first, then `Exception` — must be used everywhere Chroma is initialized. The broad `except Exception` catch is the `voss[search]` optional-dep contract.

### Hit Formatting in CLI Output

**Source:** `voss/harness/cli.py:640-659` (`_recall` slash handler), `voss/harness/tools.py:189-193` (memory_recall body)

```python
for h in hits:
    lines.append(f"[{h.source}] {h.locator} (score {h.score:.2f})")
    excerpt = (h.excerpt or "").replace("\n", " ")[:160]
    if excerpt:
        lines.append(f"  {excerpt}")
```
D-10: `recall_cmd` uses this same block-per-hit format. For code hits, `h.locator` = `code:<rel_path>:<seq>` so display should reformat as `path:line_start` using `h.line_start`.

### Config Section Parse Pattern

**Source:** `voss/harness/config.py:233-258` (`_parse_model_tiers_section` / `get_model_tiers`)
**Apply to:** New `get_index_enrich_model()` and `get_code_recall_config()` accessors

The pattern is: define a `_DEFAULT_*` dict, read-file-or-return-default, regex-parse the section, shallow-merge, return. Missing file and missing section both silently return defaults. Never raise.

### Test Skip on Missing Dependency

**Source:** `tests/memory/test_semantic.py:17-18`
```python
if embed_fn is None:
    pytest.skip("chromadb DefaultEmbeddingFunction unavailable")
```
**Apply to:** All `tests/code_recall/` tests that touch Chroma. Gate on `try/import` or `embed_fn is None`.

### Content Hash

**Source:** `voss/harness/code/index.py:187`
```python
digest = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
```
**Apply to:** `semantic_index.py` manifest hash computation. Use identical call so manifests stay consistent with M10's existing `files.hash` column.

### File Discovery

**Source:** `voss/harness/code/index.py:59-90` (`_discover_files`)
**Apply to:** `semantic_index.py` — import and call `_discover_files(cwd)` directly from `voss.harness.code.index`. Do not re-implement git discovery. Filter to `LANGUAGE_EXTS` extensions only.

---

## No Analog Found

All planned files have analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `voss/harness/`, `voss/harness/code/`, `voss_runtime/memory/`, `tests/memory/`, `tests/harness/`
**Files scanned:** 12 analog reads across 9 source files
**Pattern extraction date:** 2026-06-11

**Key seams with verified line numbers (from RESEARCH.md — all confirmed against live codebase):**
- `memory_store.py:41` — `Hit` dataclass (extend with `line_start`, `line_end`)
- `memory_store.py:56-60` — `make_id` D-04 convention (chunk id prefix pattern)
- `memory_store.py:63-68` — `_bm25_tokenize` (import, don't copy)
- `memory_store.py:108-126` — `_maybe_chroma` lazy-init guard (copy pattern)
- `memory_store.py:425-440` — `_rrf_merge` static method (call, don't copy)
- `agent.py:372-404` — `_compose_system_blocks` (add `code_recall_text=""` param)
- `agent.py:502-520` — `run_turn` signature (add `code_recall_text=""` param)
- `recorder.py:143-161` — `_append_savings_record` (call with `method="enrich"` row)
- `config.py:233-258` — `_parse_model_tiers_section` / `get_model_tiers` (extend for `index_enrich`)
- `tools.py:159-215` — `attach_memory_tools` (copy shape for `attach_code_recall_tool`)
- `tools.py:829-832` — existing code tool registration (insert `code_recall` entry here)
- `cli.py:4558-4594` — `AGENT_COMMANDS` tuple (add `recall_cmd`)
- `cli.py:1751` / `cli.py:1807` — `project_index_text` flow in `do_cmd` (parallel for `code_recall_text`)
- `code/index.py:59-90` — `_discover_files` (call directly, do not re-implement)
- `code/index.py:187` — sha256 content hash (copy identically)
- `code/service.py:117-119` — lazy `_registry` pattern (mirror for `CodeIndexService` property)
- `tests/memory/test_semantic.py:4-11` — `DefaultEmbeddingFunction` monkeypatch (conftest fixture)
