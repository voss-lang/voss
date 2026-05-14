---
phase: M8
plan: 03
status: complete
date: 2026-05-14
---

# M8-03 Summary — MemoryStore + Recall + Runtime Reuse (MEM-03 + MEM-07)

`voss/harness/memory_store.py` now exposes a working `MemoryStore` orchestrator
over `voss_runtime.memory` primitives. Composition only (Req 7 grep gate
locked from M8-00 still green). Lazy chroma; keyword fallback when chromadb
is absent. Per-source advisory locking via portalocker. Composite IDs per
D-04. Pre-M8 SessionRecord JSONs rehydrate cleanly (Pitfall 6 closed).

## Public Surface Delivered

| Symbol | Status |
|--------|--------|
| `MemoryStore(cwd, *, cap_bytes)` constructor | concrete (was concrete in Wave 0) |
| `MemoryStore.bind(*, session_id)` | concrete — ensures `.voss/memory/` layout + `.gitignore`; chromadb stays unimported (Pitfall 4) |
| `MemoryStore.write_turn(*, role, content, session_id, turn_idx)` | concrete — JSONL append + chmod 0o600 + chroma add when available |
| `MemoryStore.write_ledger(run, *, session_id)` | concrete — accepts dataclass / dict / RunRecord-like; serializes via dataclasses.asdict / dict / attribute fallback |
| `MemoryStore.write_note(text, *, session_id)` | concrete — reserve_filename + slug + frontmatter + chmod 0o600 |
| `MemoryStore.write_convention(candidate, *, session_id)` | concrete — D-11 frontmatter + body shape; chroma metadata includes evidence_turn_idx + confidence |
| `MemoryStore.recall(query, *, top_k, source)` | concrete — chroma path via `_collection.query` with where-filter; keyword fallback via `_keyword_scan` |
| `MemoryStore.forget(pattern, *, confirm)` | concrete — fnmatch over composite IDs; appends to `.voss/memory/.tombstones.jsonl`; chroma metadata update; vacuum physically removes (M8-06) |
| `MemoryStore.summary(*, source)` | concrete — per-source file count + bytes + tombstone total |
| `MemoryStore.vacuum()` | still `NotImplementedError("M8-06")` |
| `make_id(source, locator, seq)` | concrete |
| `Hit(source, locator, score, excerpt, session_id, ts)` | concrete |
| `SOURCE_QUOTAS`, `DEFAULT_CAP_BYTES` | concrete (set in Wave 0) |

## Lazy-Chroma + Keyword-Fallback Contract

- `_maybe_chroma()` is the single probe site. First call attempts
  `SemanticMemory(persist_dir=str(self.root/"chroma"), collection_name="voss_memory")`.
  On `ModuleNotFoundError` / `ImportError`: caches `self._chroma_unavailable = True` and returns None for the rest of the process. On any other exception: emits a one-line stderr warning and degrades the same way.
- `recall()` calls `_maybe_chroma()`. If a SemanticMemory instance is returned, calls `chroma._collection.query(query_texts=[query], n_results=top_k, where={"tombstoned": False, ...})` and maps results into `Hit`s with `score = max(0, 1 - distance)`. On any chroma exception, prints a one-liner and falls back to `_keyword_scan`.
- `_keyword_scan` uses `pathlib.Path.rglob` over per-source dirs, scoring by case-insensitive substring count. JSONL files (turns + ledgers) are scanned line-by-line so per-line composite IDs (e.g. `turn:s1:002`) align with chroma's stored IDs.
- Tombstoned IDs (loaded from `.voss/memory/.tombstones.jsonl`) are filtered from both paths.

## Per-Source Locking (Pitfall 3 cross-platform)

`portalocker.Lock(.voss/memory/.locks/<source>.lock, LOCK_EX | LOCK_NB)` wraps every persistent write. On contention, `portalocker.exceptions.LockException` is caught, a one-line stderr warning is emitted ("memory.<source> busy — skipping write"), and the write returns without raising (D-13 degrade-not-die). Five lock sites: turns, ledgers, notes, conventions, forget.

## Composite ID Format (D-04 in active use)

- `turn:<session_id>:<turn_idx:03d>` — written at every `write_turn`.
- `ledger:<run_id>:000` — written at every `write_ledger`.
- `note:<filename_stem>` — written at every `write_note`.
- `convention:<filename_stem>` — written at every `write_convention`.
- `decision:<path>` — emitted by `_keyword_scan` for decisions/* mirror files (recorder.py owns the writes).

Helper `make_id(source, locator, seq)` is the single construction site so the format never drifts.

## Hit-Rate Measurements (Req 3 acceptance)

5-session fake corpus (`tests/harness/conftest.py::fake_session_corpus`):
3 turns + 1 ledger + 1 convention + 1 note + 1 decision per session.
10 known-answer queries cover all 4 source types + 1 ledger.

| Path | Top-3 hit rate | Floor | Result |
|------|---------------|-------|--------|
| chroma (`voss[search]` installed) | 10/10 = 100% | ≥80% | PASS |
| keyword fallback (`chroma_disabled_env` or `_maybe_chroma → None`) | 10/10 = 100% | ≥60% | PASS |

`tests/harness/test_recall_eval.py::test_recall_top3_hit_rate[chroma|keyword]` both GREEN.

## Grep-Gate Enforcement (Req 7)

- `tests/harness/test_memory_runtime_reuse.py::test_no_harness_memory_class_definitions_outside_runtime` — static walk over `voss/harness/**/*.py`; rejects any top-level `class *Memory` definition. Permits `MemoryStore` (suffix is "Store"). Green from M8-00 onward.
- `tests/harness/test_memory_runtime_reuse.py::test_semantic_memory_init_called_on_recall` — monkey-patches `SemanticMemory` with a `FakeSemanticMemory` that records `__init__` calls; asserts (a) zero inits before first recall, (b) exactly one init after first recall, (c) still one after a second recall (cache reused).

## Pre-M8 SessionRecord Backward Compat (Pitfall 6)

`tests/harness/test_session.py::test_resume_pre_m8_no_crash` — loads the M8-00 `pre_m8_session_json` fixture (no memory_* fields), rehydrates via `voss.harness.session.load(session_id, cwd=tmp_voss_repo)`, binds a fresh `MemoryStore(cwd).bind(session_id=record.id)`, writes a turn. All steps succeed; the new `.voss/memory/turns/<session_id>.jsonl` file is created. No AttributeError / KeyError surfaces. `MemoryStore.bind` reads only `session_id` from its kwarg — never `record.<m8-only-field>` (in-source `# Pitfall 6:` comment pins the contract).

## Acceptance Gate Status

| Gate | Result |
|------|--------|
| `pytest tests/harness/test_memory_store.py -x` | green (5 tests) |
| `pytest tests/harness/test_recall_eval.py -x` | green (2 parametrizations) |
| `pytest tests/harness/test_memory_runtime_reuse.py -x` | green (2 tests) |
| `pytest tests/harness/test_session.py -x` | green (`test_resume_pre_m8_no_crash` + pre-existing) |
| `grep -v '^#' voss/harness/memory_store.py | grep -c NotImplementedError` | 1 (only `vacuum`) |
| `grep -nc portalocker.Lock voss/harness/memory_store.py` | 1 (single helper used by 5 sites) |
| `grep -nc chmod(0o600) voss/harness/memory_store.py` | 5 (turns + ledgers + notes + conventions + tombstones) |
| `grep -v '^#' voss/harness/memory_store.py | grep -cE '^class [A-Za-z_]+Memory\\b'` | 0 |
| `grep -nE '_keyword_scan|_maybe_chroma' voss/harness/memory_store.py` | 9 matches |
| Lazy-chroma subprocess invariant | passes (chromadb not in sys.modules after bind) |
| Full harness suite ignoring pre-existing diagnostics failures | 267 passed, 20 skipped |

## Files Touched

- `voss/harness/memory_store.py` — full implementation (~580 lines).
- `tests/harness/conftest.py` — `fake_session_corpus` body filled in (5 sessions × 4 source types + 5 decisions + 10 queries).
- `tests/harness/test_memory_store.py` — 5 tests (module-level skip removed).
- `tests/harness/test_recall_eval.py` — parametrized hit-rate test (module-level skip removed).
- `tests/harness/test_memory_runtime_reuse.py` — grep gate (kept from M8-00) + new mock-init test.
- `tests/harness/test_session.py` — appended `test_resume_pre_m8_no_crash`.

## Remaining Stubs

- `MemoryStore.vacuum` — owned by M8-06 (CLI + physical chroma delete + `.tombstones.jsonl` reclaim).
- `_maybe_evict` — placeholder no-op in M8-03; M8-06 fills with per-source quota + oldest-first eviction (D-14/D-16).
- `/forget` slash UX (interactive confirmation, --yes flag) — owned by M8-05; `MemoryStore.forget` returns count and is ready to wire.

## Deviations from Plan

1. **`_scan_jsonl` helper** added so `_keyword_scan` reads JSONL files line-by-line and emits per-line `turn:<sid>:<seq>` / `ledger:<run_id>:000` locators. Without this the per-line seq would always be `:000` and chroma vs keyword locator strings would diverge for non-zero turn_idx. Additive; preserves plan's contract on locator equality across both recall paths.
2. **Hit-rate eval uses `monkeypatch.setattr(MemoryStore, "_maybe_chroma", lambda self: None)` in the keyword half** instead of `chroma_disabled_env`. The latter manipulates `sys.modules["chromadb"]`, but `SemanticMemory` is imported at module load time by `memory_store.py`, so disabling chromadb post-import requires reloading the module — fragile. Direct method patch is deterministic.
3. **`test_lazy_chroma_init_no_eager_import` runs as a subprocess** rather than asserting in-process, so the assertion holds against a fresh interpreter state regardless of which tests ran before.

No other deviations.
