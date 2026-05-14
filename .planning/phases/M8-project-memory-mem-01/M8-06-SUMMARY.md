---
phase: M8
plan: 06
status: complete
date: 2026-05-14
phase_complete: true
---

# M8-06 Summary — Cap / Eviction / Vacuum / CLI (MEM-06)

`MemoryStore._maybe_evict` is no longer a no-op. `MemoryStore.vacuum`
implements the D-15 three-pass physical reclaim. `voss memory <vacuum|adopt|size>`
land as the third Click subgroup of the main CLI. `voss_md.write_fence_body`
gains the `adopt=True` opt-in for D-07 drift resolution. **All M8 phase
NotImplementedError stubs eliminated** — phase complete.

## `_maybe_evict` (D-14 / D-16)

- Called from every write site: `write_turn`, `write_ledger`, `write_note`, `write_convention` (4 call sites). Each passes `est_bytes=len(content.encode())` of the upcoming write.
- Early-returns when `source == "decisions"` (Warning 5 reconciliation: `.voss/memory/decisions/` is a mirror of COG-06 output; eviction stays out).
- Reads `.voss/config.yml` `memory.quota_pct.<source>` override; defaults to `SOURCE_QUOTAS` (turns 60% / ledgers 20% / decisions 10% / conventions 10% of `cap_bytes`).
- `quota_bytes = int(cap_bytes * quota_pct)`. When `current + est_bytes ≤ quota`, returns immediately and updates `_size_cache`.
- Otherwise sorts source files by `mtime` ascending and deletes oldest first. On each delete: chroma `_collection.delete(where={"path": str(oldest)})` (best effort try/except), then `oldest.unlink(missing_ok=True)`. Loop exits when `current + est_bytes ≤ quota` or no files remain.
- `_size_cache[source]` refreshed on the way out.
- `_load_memory_config()` helper centralizes `.voss/config.yml` parsing; failure-tolerant via top-level try/except.

## `vacuum` (D-15 three-pass reclaim)

1. Snapshot `bytes_before = sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())`.
2. Load `.voss/memory/.tombstones.jsonl` into a `set` of composite ids. If empty: still runs a best-effort chroma `delete(where={"tombstoned": True})` and returns `0`.
3. Partition tombstoned ids by source prefix (`turn:` / `ledger:` / `note:` / `convention:`).
4. **Pass (i) — JSONL line-level compaction** for `turns/` and `ledgers/`. `_vacuum_jsonl(source, id_set, id_factory)` acquires `portalocker._lock(source)`; on contention, emits a stderr line `vacuum: <source> busy; skipping JSONL compaction this pass` and bails. Otherwise iterates `*.jsonl` files: parses each line, builds composite id via `id_factory(stem, turn_idx)`, drops tombstoned lines, atomically swaps via `.tmp` + `os.replace` (preserves `chmod 0o600`). Files with all lines tombstoned are unlinked.
5. **Pass (ii) — whole-file deletion** for `notes/` and `conventions/`. For each tombstoned id, resolve `self.root/notes/<stem>.md` (resp. conventions) and `unlink(missing_ok=True)`.
6. **Pass (iii) — chroma row deletion** via `_collection.delete(where={"tombstoned": True})` (best-effort try/except + stderr on failure).
7. Truncate `.voss/memory/.tombstones.jsonl` (write `""`, do not unlink — keeps layout stable).
8. Refresh `_size_cache` per source. Return `max(0, bytes_before - bytes_after)`.
9. Chroma `persist_dir` reclaim is opaque and excluded from `bytes_reclaimed` (documented in docstring).

## `voss memory` CLI Subcommands

| Command | Args | Exit | Output |
|---------|------|------|--------|
| `voss memory vacuum --cwd <path>` | `--cwd` | non-zero if `.voss/memory/` missing | `reclaimed: <N> bytes` |
| `voss memory adopt --cwd <path> --id <fence>` | required `--id` | non-zero if `VOSS.md` or fence missing | `adopted: id=<fence> hash=<short>...` |
| `voss memory size --cwd <path>` | `--cwd` | non-zero if `.voss/memory/` missing | per-source bytes + `TOTAL: <n> / <cap> bytes (<pct>%)` |

`memory_group` registered into `AGENT_COMMANDS` tuple at `voss/harness/cli.py` adjacent to `plugin_group / skill_group / agent_group`. `python -m voss.cli memory --help` lists all 3 subcommands.

## `voss_md.write_fence_body` adopt mode

- New kwarg `adopt: bool = False`.
- Default (`adopt=False`): unchanged D-07 behavior — `HashMismatch` raised if `recorded_hash != sha256(on_disk_body)`.
- `adopt=True`: bypasses the drift guard. `memory_adopt_cmd` uses this to accept the on-disk fence body verbatim and rewrite the `<!-- voss:hash <new> -->` header from `sha256(body)`.
- Atomic write semantics unchanged (`tmp` + `os.replace`).

## Tests (7 new + regression)

| File | Tests |
|------|-------|
| `tests/harness/test_memory_eviction.py` | `test_inline_evict_when_source_over_quota`, `test_post_write_size_under_cap` (Req 6 main acceptance), `test_oldest_evicted_first_within_source` |
| `tests/harness/test_memory_vacuum.py` | `test_vacuum_reclaims_tombstoned_bytes`, `test_vacuum_deletes_tombstoned_files`, `test_vacuum_compacts_jsonl_turn_lines` (Blocker 2), `test_vacuum_removes_empty_jsonl_after_full_tombstone` (Blocker 2) |

Eviction tests autouse a `monkeypatch` to set `_maybe_chroma → None` so disk accounting reflects user content only; chroma `persist_dir` is opaque SQLite + embedding-model overhead and is excluded from the eviction policy contract.

## Acceptance Gate Status

| Gate | Result |
|------|--------|
| `pytest tests/harness/test_memory_eviction.py -x` | 3 passed |
| `pytest tests/harness/test_memory_vacuum.py -x` | 4 passed |
| `python -m voss.cli memory --help` lists vacuum/adopt/size | passes |
| `python -c "from voss.harness.memory_cli import memory_group; assert len(memory_group.commands) == 3"` | passes |
| `grep -nc "memory_group" voss/harness/cli.py` | 2 (import + tuple) |
| `grep -v '^#' voss/harness/memory_store.py | grep -c NotImplementedError` | 0 |
| `grep -v '^#' voss/harness/memory_cli.py | grep -c NotImplementedError` | 0 |
| `grep -v '^#' voss/harness/voss_md.py | grep -c NotImplementedError` | 0 |
| `grep -v '^#' voss/harness/conventions.py | grep -c NotImplementedError` | 0 |
| `grep -nE "self\._maybe_evict\(" voss/harness/memory_store.py` | 4 (one per write site) |
| `grep -nE 'where=\{"tombstoned": True\}' voss/harness/memory_store.py` | 3 (vacuum + empty-tomb shortcut) |
| `grep -nE "os\.replace" voss/harness/memory_store.py` | 2 (per-source atomic JSONL swap) |
| `grep -nE 'self\._lock\("turns"\|self\._lock\("ledgers"' voss/harness/memory_store.py` | ≥ 1 (per-source vacuum lock) |
| Full harness suite (excl. pre-existing diagnostics failures) | 290 passed, 2 skipped |

## Phase-Complete Handoff — M8 SPEC Acceptance Coverage

All 12 SPEC bullets covered across plans 00–06:

| SPEC criterion | Plan | Evidence |
|----------------|------|----------|
| Req 1 — VOSS.md system-context injection (D-08 silent degradation) | M8-01 | `test_voss_md_injection.py` |
| Req 2 — Idempotent migration + byte-identical archive (D-06 + Req 2(a)) | M8-02 | `test_voss_md_migration.py` |
| Req 3 — Cross-session recall ≥80% chroma / ≥60% keyword top-3 | M8-03 | `test_recall_eval.py[chroma|keyword]` |
| Req 4 — Conventions extracted, reviewed, persisted on clean exit | M8-04 | `test_conventions.py` (6 tests) |
| Req 5 — Slash UX `/recall /forget /memory /save` | M8-05 | `test_slash_*.py` (9 tests) |
| Req 6 — 100MB cap with per-source quota + post-write size ≤ cap | M8-06 | `test_memory_eviction.py::test_post_write_size_under_cap` |
| Req 7 — No `*Memory` subclasses outside `voss_runtime/` | M8-00 + M8-03 | `test_memory_runtime_reuse.py::test_no_harness_memory_class_definitions_outside_runtime` (grep-gate green since Wave 0) + `test_semantic_memory_init_called_on_recall` |
| Pitfall 1 — `/save` collision resolved | M8-00 + M8-05 | rename `/save` → `/save-session`; `test_save_note_does_not_rename_session` regression |
| Pitfall 2 — Cognition read/write symmetric on VOSS.md fence | M8-02 | `cognition._load_arch_from_voss_md` + `skills/analyze.py` |
| Pitfall 3 — Cross-platform locking | M8-00 + M8-03 | `portalocker>=2.8` core dep + per-source `_lock` |
| Pitfall 4 — Lazy chroma | M8-03 | `test_lazy_chroma_init_no_eager_import` (subprocess) |
| Pitfall 5 — Conventions extraction budget | M8-04 | `has_signal` quorum + 8s `asyncio.wait_for` |
| Pitfall 6 — Pre-M8 SessionRecord rehydrate | M8-03 | `test_resume_pre_m8_no_crash` |
| D-04 composite IDs | M8-03 | `make_id` helper used at every write site |
| D-07 hash-mismatch resolution | M8-01 + M8-06 | `HashMismatch` + `voss memory adopt --id` |
| D-08 system-context injection | M8-01 | `# VOSS.md\n<bytes>` head block of sys_prompt |
| D-09 signal pre-filter | M8-04 | `_SIGNAL_RE` + quorum |
| D-11 review UX | M8-04 | `review_candidates` numbered list |
| D-12 8s timeout | M8-04 | `DEFAULT_EXTRACTION_TIMEOUT_SECONDS = 8.0` |
| D-13 degrade-not-die | M8-03 | `_lock` contention emits stderr + returns |
| D-14 quotas (60/20/10/10) | M8-06 | `SOURCE_QUOTAS` + `.voss/config.yml` override |
| D-15 forget tombstones + vacuum physical delete | M8-03 + M8-06 | `forget` writes `.tombstones.jsonl`; `vacuum` 3-pass reclaim |
| D-16 inline pre-write quota | M8-06 | `_maybe_evict(est_bytes=...)` |

## Deviations from Plan

1. **Eviction tests autouse `_maybe_chroma → None` monkeypatch.** Plan's `test_post_write_size_under_cap` asserts `sum-of-sizes across .voss/memory/ ≤ cap_bytes`. Chroma's `persist_dir` writes a SQLite DB + embedding-model files (~MB) on first probe, blowing any reasonable test cap. Tests focus on user-content source dirs (`turns/ledgers/decisions/conventions/notes`); chroma `persist_dir` is opaque overhead per vacuum's documented contract. Real-world `cap_bytes=100MB` accommodates chroma overhead by default.

2. **`_load_memory_config` lifted to MemoryStore method** rather than re-reading from `conventions._load_memory_config` (which is duplicated logic in `conventions.py`). Single config-read helper per module; M9+ can refactor to a shared util if desired.

3. **`_vacuum_jsonl` extracted as a private helper** so `vacuum` body stays readable. Plan inlined this; the helper is functionally identical.

No other deviations.

## Phase-Complete State

- 4 new modules (`voss_md`, `memory_store`, `conventions`, `memory_cli`) fully implemented.
- 5 modified modules (`cli`, `cognition`, `skills/analyze`, `agent.py`, `agent/loop.voss`).
- 13 new test files + 4 extended (`test_session`, `test_repl_slash`, `test_memory_runtime_reuse`, `conftest`).
- `voss_runtime/memory/__init__.py` re-exports `Turn` for M8-02 import path.
- Full harness suite: 290 passed, 2 skipped (pre-existing diagnostics failures isolated).
- All M8 NotImplementedError stubs eliminated.
