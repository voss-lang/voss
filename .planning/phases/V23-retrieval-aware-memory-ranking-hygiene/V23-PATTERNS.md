# Phase V23: Retrieval-Aware Memory Ranking & Hygiene - Pattern Map

**Mapped:** 2026-06-12
**Files analyzed:** 7 (3 modified source + 6 new test files + 1 extended test file)
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/memory_store.py` | service | CRUD + event-driven | `voss/harness/memory_store.py` (self — extension) | exact |
| `voss/harness/memory_cli.py` | CLI / controller | request-response | `voss/harness/memory_cli.py` (self — extension) | exact |
| `voss/harness/tools.py` | service | event-driven | `voss/harness/tools.py` (self — telemetry call site) | exact |
| `tests/harness/test_memory_telemetry.py` | test | CRUD | `tests/harness/test_memory_eviction.py` | role-match |
| `tests/harness/test_memory_floors.py` | test | CRUD | `tests/harness/test_memory_eviction.py` | role-match |
| `tests/harness/test_memory_rescore.py` | test | CRUD | `tests/harness/test_agent_packing.py` (byte-identical pattern) | role-match |
| `tests/harness/test_memory_reindex.py` | test | CRUD | `tests/harness/test_memory_eviction.py` | role-match |
| `tests/harness/test_memory_pins.py` | test | CRUD | `tests/harness/test_memory_eviction.py` | role-match |
| `tests/harness/test_memory_cli_verbs.py` | test | request-response | `tests/harness/test_memory_eviction.py` | role-match |
| `tests/harness/test_memory_eviction.py` (extend) | test | CRUD | self — extension | exact |

---

## Pattern Assignments

### `voss/harness/memory_store.py` (service, CRUD + event-driven)

**All patterns are in-file extensions — read the actual source, do not reinvent adjacent code.**

#### Imports pattern (lines 1-25):
```python
from __future__ import annotations

import dataclasses
import fnmatch
import json
import os
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import portalocker
from rank_bm25 import BM25Okapi

from voss.template_render import render_package_template
from voss_runtime.memory import EpisodicMemory, SemanticMemory, Turn  # noqa: F401
```

**V23 adds:** `import math` (for rescore formula), `import hashlib` (for reindex manifest). Both are stdlib — no pip install.

#### Gitignore constant (line 37) — extend this:
```python
_VOSS_MEMORY_GITIGNORE = "chroma/\n.locks/\n.tombstones.jsonl\n"
```
**V23 target:**
```python
_VOSS_MEMORY_GITIGNORE = "chroma/\n.locks/\n.tombstones.jsonl\n.retrieval.jsonl\n.reindex-manifest.json\n"
```

#### Portalocker `_lock` pattern (lines 133-149) — copy verbatim for telemetry guard:
```python
@contextmanager
def _lock(self, source: str):
    """Per-source advisory lock via portalocker; yields None on contention."""
    self.root.mkdir(parents=True, exist_ok=True)
    (self.root / ".locks").mkdir(parents=True, exist_ok=True)
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
        print(f"memory.{source} busy — skipping write", file=sys.stderr)
        yield None
```
**Telemetry usage:** call `self._lock("retrieval")` — yields `None` on contention; caller drops the event (D-03 skip-on-contention semantics).

#### Tombstone sidecar pattern (lines 222-244) — template for `.retrieval.jsonl`:
```python
@property
def _tombstones_path(self) -> Path:
    return self.root / ".tombstones.jsonl"

def _load_tombstones(self) -> set[str]:
    path = self._tombstones_path
    if not path.exists():
        return set()
    ids: set[str] = set()
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue  # corrupt-line tolerant
            if isinstance(rec, dict) and "id" in rec:
                ids.add(str(rec["id"]))
    except OSError:
        return set()
    return ids
```
**V23 analog:** `_retrieval_path` property + `_load_telemetry_compacted()` follows the same corrupt-line-tolerant reader shape. Replace `"id"` key lookup with `"locator"` and `"ts"`.

#### `_load_memory_config` pattern (lines 205-216) — use for all floor/rescore config reads:
```python
def _load_memory_config(self) -> dict:
    config_path = self.cwd / ".voss" / "config.yml"
    if not config_path.exists():
        return {}
    try:
        import yaml
        data = yaml.safe_load(config_path.read_text()) or {}
    except Exception:  # noqa: BLE001
        return {}
    memory = data.get("memory") if isinstance(data, dict) else None
    return memory if isinstance(memory, dict) else {}
```
**Critical:** `_rrf_merge` is a `@staticmethod` — do NOT call `_load_memory_config` inside it. Call it in instance methods `_bm25_recall`, `_chroma_recall`, and `recall()` only.

#### `_maybe_evict` sort key (lines 151-203) — extend, do not replace:
```python
def _maybe_evict(self, source: str, *, est_bytes: int = 0) -> None:
    if source == "decisions":
        return
    # ... quota calculation ...
    files = [p for p in source_dir.rglob("*") if p.is_file()]
    # ... current_bytes check ...
    files.sort(key=lambda p: p.stat().st_mtime)  # V23: replace with _eviction_key
    # ... eviction loop ...
```
**V23 replacement for line 183:**
```python
telemetry = self._load_telemetry_compacted()
pins = self._load_pins()
files = [f for f in files if self._locator_from_path(source, f) not in pins]
files.sort(key=lambda p: self._eviction_key(p, telemetry))
```

#### `recall()` method (lines 411-428) — add rescore hook after `_rrf_merge`:
```python
def recall(self, query, *, top_k=5, source=None) -> list[Hit]:
    recall_k = max(top_k * 3, top_k)
    bm25_hits = self._bm25_recall(query, top_k=recall_k, source=source)
    chroma = self._maybe_chroma()
    if chroma is None:
        return bm25_hits[:top_k]
    try:
        chroma_hits = self._chroma_recall(chroma, query, top_k=recall_k, source=source)
    except Exception as exc:  # noqa: BLE001
        print(f"memory: chroma recall failed ({exc}); falling back to BM25", file=sys.stderr)
        return bm25_hits[:top_k]
    return self._rrf_merge([bm25_hits, chroma_hits], top_k=top_k)
    # V23: add rescore hook here (VRNK-03):
    # fused = self._rrf_merge([bm25_hits, chroma_hits], top_k=top_k)
    # cfg = self._load_memory_config()
    # if cfg.get("rescore", False):
    #     fused = self._rescore(fused, cfg)
    # return fused
```

#### `_bm25_recall` tail (line 575-576) — BM25 floor insertion point:
```python
ranked.sort(key=lambda item: item[0], reverse=True)
return [hit for _, hit in ranked[:top_k]]   # V23: insert floor before this return
```
**V23 floor pattern (insert before the return at line 576):**
```python
cfg = self._load_memory_config()
bm25_floor_ratio = float(cfg.get("bm25_floor_ratio", 0.1))
if ranked and ranked[0][0] > 0 and bm25_floor_ratio > 0:
    top_score = ranked[0][0]
    ranked = [(s, h) for s, h in ranked if s >= top_score * bm25_floor_ratio]
return [hit for _, hit in ranked[:top_k]]
```

#### `_chroma_recall` tail (lines 481-483) — chroma floor insertion point:
```python
            out.append(Hit(...))
    return out   # V23: insert floor before this return
```
**V23 floor pattern (insert before the return at line 483):**
```python
cfg = self._load_memory_config()
chroma_floor = float(cfg.get("chroma_floor", 0.25))
if chroma_floor > 0:
    out = [h for h in out if h.score >= chroma_floor]
return out
```
Chroma score = `max(0.0, 1.0 - float(dist))` confirmed at line 470. Floor of 0.25 = cosine similarity ≥ 0.25.

#### `_locator_from_path` (lines 628-641) — use for eviction key and pin exemption:
```python
def _locator_from_path(self, source_dir: str, path: Path) -> str:
    stem = path.stem
    if source_dir == "turns":
        return make_id("turn", stem, seq=0)
    if source_dir == "ledgers":
        return make_id("ledger", stem, seq=0)
    if source_dir == "decisions":
        return make_id("decision", str(path.relative_to(self.root.parent)))
    if source_dir == "conventions":
        return make_id("convention", stem)
    if source_dir == "notes":
        return make_id("note", stem)
    return f"{source_dir}:{stem}"
```
**Pin CLI verbs must store locators using exactly this output.** Show the full composite ID to operators in `voss memory list`.

#### `vacuum()` three-pass structure (lines 720-788) — add telemetry compaction as a fourth pass:
```python
def vacuum(self) -> int:
    bytes_before = self._tree_bytes()
    # Pass (i): JSONL line-level compaction for turns/ ledgers/
    self._vacuum_jsonl("turns", turn_ids, ...)
    self._vacuum_jsonl("ledgers", ledger_ids, ...)
    # Pass (ii): whole-file deletion for notes/ conventions/
    # Pass (iii): chroma where-filter delete
    # V23 Pass (iv): compact .retrieval.jsonl → per-locator {count, last_retrieved}
    self._vacuum_telemetry()
    # Truncate tombstones index
    self._tombstones_path.write_text("")
```

#### V19 hash manifest pattern for reindex — from `voss/harness/code/semantic_index.py` lines 92-124:
```python
def _file_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()

def _manifest_path(cwd: Path) -> Path:
    return cwd / ".voss-cache" / "code" / "semantic-manifest.json"

def _load_manifest(cwd: Path) -> dict:
    path = _manifest_path(cwd)
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}

def _save_manifest(cwd: Path, data: dict) -> None:
    path = _manifest_path(cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=0, sort_keys=True))
```
**V23 adaptation:** these become instance methods on `MemoryStore` with paths under `self.root`:
```python
@property
def _reindex_manifest_path(self) -> Path:
    return self.root / ".reindex-manifest.json"

def _load_reindex_manifest(self) -> dict:
    try:
        return json.loads(self._reindex_manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}  # missing → everything stale (D-11)

def _save_reindex_manifest(self, data: dict) -> None:
    self._reindex_manifest_path.write_text(
        json.dumps(data, indent=0, sort_keys=True)
    )
```
Sources covered: `notes/`, `decisions/`, `conventions/` only (D-10 — turns/ledgers excluded).

---

### `voss/harness/memory_cli.py` (CLI / controller, request-response)

**Analog:** `voss/harness/memory_cli.py` (self — new verbs added to existing group)

#### Imports pattern (lines 1-16):
```python
"""Click subcommand group for `voss memory <vacuum|adopt|size>`."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import click

from . import voss_md
from .memory_store import MemoryStore
```

#### Click group registration (line 18-19):
```python
@click.group("memory")
def memory_group() -> None:
    """Manage Voss project memory store."""
```

#### Existing command pattern — copy structure for all new verbs (lines 23-40):
```python
@memory_group.command("vacuum")
@click.option(
    "--cwd",
    "cwd_str",
    default=".",
    type=click.Path(file_okay=False),
    help="Project root.",
)
def memory_vacuum_cmd(cwd_str: str) -> None:
    """Compact chroma + delete tombstoned entries; report bytes reclaimed."""
    cwd = Path(cwd_str).resolve()
    store = MemoryStore(cwd)
    if not store.root.exists():
        click.echo(f"no memory store at {store.root}", err=True)
        sys.exit(1)
    store.bind(session_id="vacuum")
    reclaimed = store.vacuum()
    click.echo(f"reclaimed: {reclaimed} bytes")
```

**Pattern for new verbs (pin/unpin/list/show/reindex):**
- Each gets `--cwd` option (same default=".") + `--global` flag (D-12, V21 convention)
- Store instantiation: `store = MemoryStore(cwd)` or `MemoryStore(cwd, root_override=global_root)`
- Missing store root → `click.echo(..., err=True); sys.exit(1)`
- Unknown locator → `click.echo(f"unknown locator: {locator}", err=True); sys.exit(1)`
- `session_id` for bind: use a descriptive string matching the verb name (e.g. `"pin"`, `"list"`)

#### `sync --check` exit contract — mirror from `voss/cli.py` lines 519-522:
```python
if result.drifted:
    click.echo(f"{len(result.drifted)} artifact(s) drifted")
    raise SystemExit(1)
click.echo("all artifacts in sync")
```
**V23 `reindex --check` exit contract:**
```python
if check_mode:
    stale = [loc for loc, _ in drift_items]
    if stale:
        for loc in stale:
            click.echo(loc, err=True)
        raise SystemExit(1)
    click.echo("memory index in sync")
    return
```

---

### `voss/harness/tools.py` (service, event-driven — telemetry call site only)

**Analog:** `voss/harness/tools.py` (self — surgical addition after `hits = store.recall(...)`)

#### `memory_recall` tool (lines 178-194) — telemetry insertion point:
```python
async def memory_recall(query: str, top_k: int = 5, source: str | None = None) -> str:
    query = query.strip()
    if not query:
        return "<error: empty query>"
    try:
        hits = store.recall(query, top_k=top_k, source=source)
    except Exception as exc:  # noqa: BLE001
        return f"<error: recall failed: {exc}>"
    if not hits:
        return "(no hits)"
    # V23: ADD HERE (agent-path only — never in CLI paths):
    # store._record_telemetry(hits)
    lines: list[str] = []
    for h in hits:
        lines.append(f"[{h.source}] {h.locator} (score {h.score:.2f})")
        ...
```
**One surgical line addition.** The auto-injection global store call site (post-V21 `attach_memory_tools`) gets the same treatment: `global_store._record_telemetry(global_hits)` immediately after the global store's `recall()` return.

---

### `voss/harness/agent.py` — pinned block injection (surgical addition)

**Analog:** `voss/harness/agent.py` — `_compose_system_blocks` (lines 373-407) + `_code_recall_kwargs` idiom (lines 841-853 in cli.py)

#### `_compose_system_blocks` parameter — add `pinned_memory_text` (line 373):
```python
def _compose_system_blocks(
    *,
    voss_md_block: str,
    cognition_text: str,
    principles_text: str = "",
    project_index_text: str = "",
    code_recall_text: str = "",     # V19 — rides variable region
    pinned_memory_text: str = "",   # V23 — same slot, same budget
    prior_context_text: str,
    loop_system: str,
) -> list[dict]:
```
Add `pinned_memory_text` to the block list in the same position pattern as `code_recall_text`.

#### `_code_recall_kwargs` signature-guard idiom (cli.py lines 841-853) — copy for pinned text:
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
**V23 analog:** `_pinned_memory_kwargs(run_turn_fn, store) -> dict` — same `inspect.signature` guard, checks for `"pinned_memory_text"` parameter, renders pinned block text.

#### `_default_token_count` (agent.py line 83) — use for pin cap accounting:
```python
def _default_token_count(text: str, *, model: str) -> int:
    if _litellm is not None:
        try:
            return int(_litellm.token_counter(model=model, text=text))
        except Exception:  # noqa: BLE001
            pass
    return max(len(text) // 4, 1)
```
Import: `from voss.harness.agent import _default_token_count`. Use with `model` bound at call site (same pattern as V18/V19 token accounting).

---

### `tests/harness/test_memory_telemetry.py` (test, CRUD — new file)

**Analog:** `tests/harness/test_memory_eviction.py`

#### Test file structure pattern (lines 1-22):
```python
"""M8-06 inline eviction tests (Req 6 cap + D-14/D-16 quota)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from voss.harness.memory_store import MemoryStore


@pytest.fixture(autouse=True)
def _no_chroma(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MemoryStore, "_maybe_chroma", lambda self: None)
```

**V23 telemetry tests:** also import `json` for reading `.retrieval.jsonl`. Use `tmp_voss_repo` fixture (from `tests/harness/conftest.py`) — creates `.voss/memory/` layout. Use `chroma_disabled_env` fixture (conftest.py line 278) when chroma is not under test.

#### `tmp_voss_repo` fixture — from conftest, do not redefine:
Available in `tests/harness/conftest.py`. Creates the standard `.voss/memory/` tree. All new memory test files use it as their store factory fixture.

#### `chroma_disabled_env` fixture (conftest.py lines 277-291) — for chroma-absent tests:
```python
@pytest.fixture
def chroma_disabled_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys as _sys
    monkeypatch.setitem(_sys.modules, "chromadb", None)
    if "voss_runtime.memory.semantic" in _sys.modules:
        import importlib
        importlib.reload(_sys.modules["voss_runtime.memory.semantic"])
```

#### `os.utime` mtime seeding pattern (test_memory_eviction.py lines 83-87):
```python
for i, ts in enumerate((1000, 2000, 3000)):
    p = turns_dir / f"seed-{i}.jsonl"
    p.write_text(body + "\n")
    os.utime(p, (ts, ts))
```
Use this pattern in eviction tests to control mtime ordering deterministically.

---

### `tests/harness/test_memory_rescore.py` (test, CRUD — new file, byte-identical pattern)

**Primary analog:** `tests/harness/test_agent_packing.py` (byte-identical guarantee pattern)

#### Byte-identical test structure (test_agent_packing.py lines 202-208):
```python
@pytest.mark.asyncio
async def test_no_pack_byte_identical(tmp_path: Path) -> None:
    """VOPT-06: below-threshold run with packing on == packing off, byte-for-byte."""
    provider_off, _ = await _run_short(tmp_path, packing_enabled=False)
    provider_on, _ = await _run_short(tmp_path, packing_enabled=True)

    assert provider_on.stream_calls[-1]["messages"] == provider_off.stream_calls[-1]["messages"]
```

**V23 byte-identical analog:**
```python
def test_rescore_off_byte_identical(tmp_voss_repo: Path) -> None:
    """VRNK-08: rescore=False (default) → recall output byte-identical to pre-V23 baseline."""
    store = MemoryStore(tmp_voss_repo)
    # Seed known memory content + BM25 corpus
    # Capture recall output with rescore config absent (default False)
    hits_baseline = store.recall("test query", top_k=5)
    # Freeze baseline — second call must be identical
    hits_second = store.recall("test query", top_k=5)
    assert [(h.locator, h.score) for h in hits_baseline] == \
           [(h.locator, h.score) for h in hits_second]
```
The rescore fixture tests use fixed `telemetry` data written to `.retrieval.jsonl` before recall to ensure determinism (D-13 constraint: deterministic under fixture).

---

### `tests/harness/test_memory_reindex.py` (test, CRUD — new file)

**Analog:** `tests/harness/test_memory_eviction.py` (store setup) + `voss/harness/code/semantic_index.py` (manifest pattern)

No additional analog excerpts needed beyond those already listed. Follow the `tmp_voss_repo` + `chroma_disabled_env` fixture pattern. The `reindex --check` exit-code tests use `pytest.raises(SystemExit)` or `click.testing.CliRunner` to capture `sys.exit(1)`.

---

### `tests/harness/test_memory_cli_verbs.py` (test, request-response — new file)

**Analog:** `voss/harness/memory_cli.py` click group

Use `click.testing.CliRunner` for all CLI verb tests:
```python
from click.testing import CliRunner
from voss.harness.memory_cli import memory_group

def test_pin_unpin_list(tmp_voss_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(memory_group, ["pin", "note:my-note", "--cwd", str(tmp_voss_repo)])
    assert result.exit_code == 0
    result = runner.invoke(memory_group, ["list", "--pinned", "--cwd", str(tmp_voss_repo)])
    assert "note:my-note" in result.output
```

---

## Shared Patterns

### Portalocker Skip-on-Contention
**Source:** `voss/harness/memory_store.py` lines 133-149
**Apply to:** `_record_telemetry` method (VRNK-01 telemetry append), any new sidecar write
```python
with self._lock("retrieval") as lock:
    if lock is None:  # skip-on-contention (D-03)
        return
    # ... write to sidecar ...
```

### Corrupt-Line-Tolerant JSONL Reader
**Source:** `voss/harness/memory_store.py` lines 226-244 (`_load_tombstones`)
**Apply to:** `_load_telemetry_compacted`, any new JSONL sidecar reader
```python
for line in path.read_text().splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        rec = json.loads(line)
    except json.JSONDecodeError:
        continue  # corrupt-line tolerant — never crash
```

### Chroma Optional / BM25-Only Degradation
**Source:** `voss/harness/memory_store.py` lines 113-131 (`_maybe_chroma`)
**Apply to:** reindex verb, chroma floor, all chroma-touching code
```python
chroma = self._maybe_chroma()
if chroma is None:
    # degrade gracefully — BM25 path only
    return ...
```
For reindex: if `_maybe_chroma()` returns None, print notice and exit 0 (per SPEC).

### V18 Stable-Region Constraint
**Source:** `voss/harness/context_allocator.py` lines 198-208, docstring lines 20-26
**Apply to:** pinned block injection (VRNK-06)
Stable region = FOLD-only. Pinned block goes in the **variable region** (same slot as `code_recall_text` in `_compose_system_blocks`). Do NOT add pin text to stable region.

### `decisions/` Eviction Exemption
**Source:** `voss/harness/memory_store.py` lines 161-162
**Apply to:** `_maybe_evict` extension — preserve this guard, pinned exemption goes AFTER it
```python
if source == "decisions":
    return
```

### Error Handling — BLE001 Pattern
**Source:** Throughout `memory_store.py`
**Apply to:** All new methods that touch filesystem or chroma
```python
except Exception:  # noqa: BLE001 — defensive; <operation> must not crash <parent>
    pass  # or: return default
```

### Config Key Access Pattern
**Source:** `voss/harness/memory_store.py` lines 205-216
**Apply to:** All new config reads (floor ratios, rescore switch, pin caps)
```python
cfg = self._load_memory_config()
value = float(cfg.get("chroma_floor", 0.25))  # default inline, not a separate constant
```

---

## No Analog Found

All files have clear analogs. No gaps requiring RESEARCH.md patterns as fallback.

---

## Anti-Pattern Summary (from RESEARCH.md — enforce in planner actions)

| Anti-Pattern | Correct Pattern |
|---|---|
| Telemetry inside `recall()` | Record in callers (`tools.py`, auto-injection) only |
| Post-fusion score floors | Floor in `_bm25_recall` tail and `_chroma_recall` tail, BEFORE `_rrf_merge` |
| Calling `_load_memory_config` in `_rrf_merge` | `_rrf_merge` is `@staticmethod` — config reads in instance methods only |
| Pinned block in stable region | Variable region only (`_compose_system_blocks`, same slot as `code_recall_text`) |
| Chroma `add` for reindex | Use `upsert` — `add` raises `DuplicateIDError` |
| `.pins.json` in gitignore | D-02: `.pins.json` is committed; only `.retrieval.jsonl` and `.reindex-manifest.json` are gitignored |
| `from chromadb.utils.embedding_functions import clear_system_cache` | Do not import — removed in chroma 1.5.x |
| BM25 floor when top_score == 0 | Guard: `if ranked and ranked[0][0] > 0` before applying ratio floor |

---

## Metadata

**Analog search scope:** `voss/harness/`, `voss/harness/code/`, `tests/harness/`, `voss/cli.py`
**Files scanned:** 9 source files (memory_store.py, memory_cli.py, tools.py, agent.py, cli.py, context_allocator.py, code/semantic_index.py, test_memory_eviction.py, test_agent_packing.py, conftest.py)
**Pattern extraction date:** 2026-06-12
