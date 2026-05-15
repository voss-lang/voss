---
phase: T2
slug: parallel-tools-multi-edit
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-15
updated: 2026-05-15
note: |
  Wave-0 stub creation is in-task (TDD-style). Each implementing task writes
  its own test file in the same commit as the production code. No separate
  Wave 0 plan is required because tests are authored alongside (or before)
  the code they cover — see `tdd="true"` on every <task> across T2-01..T2-05.
---

# Phase T2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with `asyncio_mode = "auto"` (already configured in `pyproject.toml`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/harness/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~30s quick, ~60s full incl. `tests/perf/test_parallel_read_speedup.py` (~2s) |

---

## Sampling Rate

- **After every task commit:** Run scoped `uv run pytest <task's automated command>`
- **After every plan wave:** Run `uv run pytest tests/harness/ -x -q`
- **Before `/gsd:verify-work`:** Full suite green incl. `tests/perf/test_parallel_read_speedup.py`
- **Max feedback latency:** 30s

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|------------|----------|-----------|-------------------|--------|
| T2-01-01 | 01 | 1 | PAR-06 | T-T2-01-A (recorder integrity) | `BatchRecord` dataclass + `IterationRecord.batches` additive field round-trips | unit | `uv run pytest tests/harness/test_session_roundtrip.py -x -q` | ⬜ pending |
| T2-01-02 | 01 | 1 | PAR-06 | T-T2-01-B (event ordering) | `RunRecorder.begin_batch` / `end_batch` emit `batch.start` / `batch.end` and update `IterationRecord.batches` | unit | `uv run pytest tests/harness/test_recorder.py -x -q` | ⬜ pending |
| T2-02-01 | 02 | 1 | PAR-05 | T-T2-02-A (config injection) | `RuntimeConfig.max_parallel_reads` field + `get_max_parallel_reads` loader; range 1–32, default 8, out-of-range warns + falls back | unit | `uv run pytest tests/harness/test_agent_config.py -x -q` | ⬜ pending |
| T2-02-02 | 02 | 1 | PAR-05 | T-T2-02-B (boot-time config) | `cli.py` bootstrap wires `configure(max_parallel_reads=...)` from `harness.toml` | subprocess | `uv run pytest tests/harness/test_cli_bootstrap.py -x -q` | ⬜ pending |
| T2-03-01 | 03 | 2 | PAR-01, PAR-02, PAR-06 | T-T2-03-A (no-parallel-mutation), T-T2-03-B (batch invariant), T-T2-03-C (per-step gate preserved) | Partition scheduler in `_run_step_loop`: read-only batches via `asyncio.gather` + `Semaphore(max_parallel_reads)`; `BatchInvariantError` on mutating-in-batch; per-step `PermissionGate.check` preserved; `batch.start` / `batch.end` wrappers emitted around multi-step batches; singletons emit no wrappers | unit | `uv run pytest tests/harness/test_partition_scheduler.py tests/harness/test_permissions.py -x -q` | ⬜ pending |
| T2-04-01 | 04 | 3 | PAR-03 | T-T2-04-A (atomicity), T-T2-04-B (path jail), T-T2-04-C (modal denial) | `fs_edit_many(path, edits=[...])` atomic single-file multi-edit; read snapshot, apply left-to-right in working buffer, each `old` unique-in-current-buffer; ambiguous/missing → batch rejected, file byte-for-byte unchanged; DiffModal hunks; reject OR skip → batch denied (strict skip semantics, resolves Open Question 1) | unit | `uv run pytest tests/harness/tools/test_fs_edit_many.py -x -q` | ⬜ pending |
| T2-05-01 | 05 | 4 | PAR-04 | T-T2-05-A (path jail per-slot), T-T2-05-B (no whole-call error) | `fs_read_many(paths=[...])` partial-result bundle; per-slot envelopes (`<error: not found: ...>`, `<error: is a directory: ...>`, `<error: binary file: ...>`); preserves request order; empty paths → sentinel | unit | `uv run pytest tests/harness/tools/test_fs_read_many.py -x -q` | ⬜ pending |
| T2-06-01 | 06 | 5 | PAR-01, PAR-05 (Success Criteria #1) | T-T2-06-A (no-flake under load) | Micro-benchmark: stub-timed 6-read scenario, `parallel_ms <= serial_ms * 0.6` at default cap=8; cap=1 sanity test demonstrates serial parity | perf | `uv run pytest tests/perf/test_parallel_read_speedup.py -x -q` | ⬜ pending |
| T2-06-02 | 06 | 5 | PAR-01..PAR-06 | — | Phase-final human-verify: full T2 suite green, DiffModal hunk-walk smoke (manual), redaction unchanged, no T1/M1/M2 regression | checkpoint | `uv run pytest tests/harness/ tests/perf/ -x -q` + human smoke | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Acceptance Criteria Coverage (SPEC.md → task verifications)

| SPEC AC | Requirement | Task | Source |
|---------|-------------|------|--------|
| AC-01 partition `[A,B,C,D]` → `[A]`,`[B]`,`[C,D]` | PAR-01 | T2-03-01 | `test_partition_read_write_read_read` |
| AC-02 gather concurrent timestamps | PAR-01 | T2-03-01 | `test_telemetry_per_step_events_preserved_inside_batches` |
| AC-03 `max_parallel_reads=2` caps peak | PAR-01 | T2-03-01 | `test_semaphore_cap_enforced` |
| AC-04 default 8 + out-of-range warn | PAR-05 | T2-02-01 | `test_max_parallel_reads_*_warns` |
| AC-05 `BatchInvariantError` raised | PAR-02 | T2-03-01 | `test_batch_invariant_raises` |
| AC-06 per-step `PermissionGate.check` preserved | PAR-02 | T2-03-01 | `test_per_step_check_preserved` |
| AC-07 `fs_edit_many` is_mutating=True | PAR-03 | T2-04-01 | `test_registered_with_is_mutating_true` |
| AC-08 3 valid edits → write + delta | PAR-03 | T2-04-01 | `test_all_match_writes` |
| AC-09 ambiguous `old` → reject, unchanged | PAR-03 | T2-04-01 | `test_ambiguous_rejected` |
| AC-10 error names index | PAR-03 | T2-04-01 | `test_missing_rejected` |
| AC-11 modal reject → batch denied | PAR-03 | T2-04-01 | `test_modal_reject_denies` |
| AC-12 `fs_read_many` is_mutating=False | PAR-04 | T2-05-01 | `test_registered_with_is_mutating_false` |
| AC-13 3 readable paths, request order | PAR-04 | T2-05-01 | `test_three_readable_bundle_format` |
| AC-14 missing path inline error | PAR-04 | T2-05-01 | `test_missing_slot_inline_error` |
| AC-15 `paths=[]` → sentinel | PAR-04 | T2-05-01 | `test_empty_paths_returns_sentinel` |
| AC-16 multi-step batch.start/.end + monotonic batch_index | PAR-06 | T2-01-02 + T2-03-01 | `test_telemetry_multi_step_emits_batch_start_end` |
| AC-17 per-step tool.call/tool.result inside batches | PAR-06 | T2-03-01 | `test_telemetry_per_step_events_preserved_inside_batches` |
| AC-18 singletons emit no wrappers | PAR-06 | T2-03-01 | `test_telemetry_singleton_emits_no_batch_wrappers` |
| AC-19 `RunRecord.batches` round-trips, pre-T2 records load | PAR-06 | T2-01-01 | `test_session_roundtrip` |
| AC-20 benchmark ≤60% at default cap | PAR-01, PAR-05 | T2-06-01 | `test_parallel_read_speedup_default_cap` |
| AC-21 benchmark cap=1 sanity | PAR-01 | T2-06-01 | `test_parallel_read_speedup_cap_1_sanity` |

All 21 SPEC acceptance criteria mapped. (SPEC says "22" but the count of explicit bullets is 21 — minor SPEC arithmetic, not a coverage gap.)

---

## Wave 0 Requirements

Wave-0 stub-creation is **in-task** (TDD style). Each implementing task creates its test file in the same commit as the production code. The test files below are written by the listed task — no separate Wave 0 plan is needed.

| Test File | Created By |
|-----------|-----------|
| `tests/harness/test_session_roundtrip.py` | T2-01-01 |
| `tests/harness/test_recorder.py` | T2-01-02 |
| `tests/harness/test_agent_config.py` | T2-02-01 |
| `tests/harness/test_cli_bootstrap.py` | T2-02-02 |
| `tests/harness/test_partition_scheduler.py` | T2-03-01 |
| `tests/harness/test_permissions.py` (extends, does not create) | T2-03-01 |
| `tests/harness/tools/test_fs_edit_many.py` | T2-04-01 |
| `tests/harness/tools/test_fs_read_many.py` | T2-05-01 |
| `tests/perf/__init__.py` + `tests/perf/test_parallel_read_speedup.py` | T2-06-01 |

Shared fixtures (mock-tool with `asyncio.sleep`-based latency) live in `tests/harness/conftest.py` and are added/extended by T2-03-01 as a side-effect.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TUI DiffModal hunk walk-through for `fs_edit_many` (accept / reject / skip per hunk) | PAR-03 | Interactive Textual modal — real UI smoke must be human-verified | Run `voss` against a 3-line fixture file, invoke a plan that calls `fs_edit_many` with 3 hunks. Verify: accept-all writes; any reject denies and file unchanged; any skip also denies (strict skip semantics) |
| Telemetry redaction on real session | PAR-06 | Recorded session payloads must not leak `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` env values | After T2 ships, run a real session that triggers `fs_read_many` on a file containing the literal string `OPENAI_API_KEY=sk-...`; verify the recorded `tool.result` payload renders the value as `<redacted>` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or in-task Wave 0 (test file created in same commit as production code)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covered by in-task TDD pattern (`tdd="true"` on every implementing `<task>`)
- [x] No watch-mode flags
- [x] Feedback latency < 30s on quick path
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-15
