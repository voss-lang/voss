---
phase: T2
slug: parallel-tools-multi-edit
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-15
---

# Phase T2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with `asyncio_mode = "auto"` (already configured in `pyproject.toml`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/ -x -q --no-cov` |
| **Full suite command** | `pytest tests/ --cov=voss --cov-report=term-missing` |
| **Estimated runtime** | ~30s quick, ~120s full (incl. micro-benchmark) |

---

## Sampling Rate

- **After every task commit:** Run scoped `pytest tests/<plan-area>/ -x -q --no-cov`
- **After every plan wave:** Run `pytest tests/ -x -q --no-cov`
- **Before `/gsd:verify-work`:** Full suite must be green incl. `tests/perf/test_parallel_read_speedup.py`
- **Max feedback latency:** 30s

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T2-01-01 | 01 | 1 | PAR-01 | — | order-preserving partition, read-only batch dispatch | unit | `pytest tests/harness/test_partition_scheduler.py -x -q` | ❌ W0 | ⬜ pending |
| T2-01-02 | 01 | 1 | PAR-01 | — | `asyncio.gather` with `Semaphore(max_parallel_reads)` bounded | unit | `pytest tests/harness/test_partition_scheduler.py::test_semaphore_cap -x -q` | ❌ W0 | ⬜ pending |
| T2-02-01 | 02 | 1 | PAR-02 | — | `BatchInvariantError` raised on mutating-in-batch | unit | `pytest tests/harness/test_partition_scheduler.py::test_batch_invariant -x -q` | ❌ W0 | ⬜ pending |
| T2-02-02 | 02 | 1 | PAR-02 | — | per-step `PermissionGate.check` still fires once-per-step | unit | `pytest tests/harness/test_permissions.py::test_per_step_check_preserved -x -q` | ❌ W0 | ⬜ pending |
| T2-05-01 | 05 | 1 | PAR-05 | — | `harness.toml` knob `agent.max_parallel_reads` (default 8, range 1–32) | unit | `pytest tests/harness/test_config.py::test_max_parallel_reads -x -q` | ❌ W0 | ⬜ pending |
| T2-03-01 | 03 | 2 | PAR-03 | — | `fs_edit_many` all-pass writes once | unit | `pytest tests/harness/tools/test_fs_edit_many.py::test_all_match_writes -x -q` | ❌ W0 | ⬜ pending |
| T2-03-02 | 03 | 2 | PAR-03 | — | ambiguous `old` → batch rejected, file unchanged | unit | `pytest tests/harness/tools/test_fs_edit_many.py::test_ambiguous_rejected -x -q` | ❌ W0 | ⬜ pending |
| T2-03-03 | 03 | 2 | PAR-03 | — | missing `old` → batch rejected, error names index | unit | `pytest tests/harness/tools/test_fs_edit_many.py::test_missing_rejected -x -q` | ❌ W0 | ⬜ pending |
| T2-03-04 | 03 | 2 | PAR-03 | — | DiffModal hunk reject → batch denied (atomicity) | unit | `pytest tests/harness/tools/test_fs_edit_many.py::test_modal_reject_denies -x -q` | ❌ W0 | ⬜ pending |
| T2-04-01 | 04 | 2 | PAR-04 | — | `fs_read_many` bundle format stable, per-slot errors inline | unit | `pytest tests/harness/tools/test_fs_read_many.py::test_bundle_format -x -q` | ❌ W0 | ⬜ pending |
| T2-04-02 | 04 | 2 | PAR-04 | — | partial-result: missing path renders `<error: not found: ...>` slot | unit | `pytest tests/harness/tools/test_fs_read_many.py::test_partial_result -x -q` | ❌ W0 | ⬜ pending |
| T2-06-01 | 06 | 3 | PAR-06 | — | `batch.start` / `batch.end` telemetry emitted for multi-step batches only | unit | `pytest tests/harness/test_recorder.py::test_batch_events -x -q` | ❌ W0 | ⬜ pending |
| T2-06-02 | 06 | 3 | PAR-06 | — | `IterationRecord.batches: list[BatchRecord]` additive, serializes | unit | `pytest tests/harness/test_recorder.py::test_iteration_record_schema -x -q` | ❌ W0 | ⬜ pending |
| T2-05-02 | 05 | 4 | PAR-05 (Success Criteria #1) | — | ≥40% wall-clock drop on stub-timed 6-read | perf | `pytest tests/perf/test_parallel_read_speedup.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/harness/test_partition_scheduler.py` — stubs for PAR-01, PAR-02
- [ ] `tests/harness/test_permissions.py` — preserve existing; add per-step assertion stub
- [ ] `tests/harness/test_config.py` — stubs for PAR-05 (`max_parallel_reads`)
- [ ] `tests/harness/tools/test_fs_edit_many.py` — stubs for PAR-03 (4 acceptance cases)
- [ ] `tests/harness/tools/test_fs_read_many.py` — stubs for PAR-04
- [ ] `tests/harness/test_recorder.py` — stubs for PAR-06 batch events + schema
- [ ] `tests/perf/__init__.py` + `tests/perf/test_parallel_read_speedup.py` — stub for benchmark (PAR-05 Success Criteria #1)
- [ ] `tests/harness/conftest.py` — shared mock-tool fixtures with `asyncio.sleep`-based latency stubs

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TUI DiffModal hunk walk-through for `fs_edit_many` | PAR-03 | Interactive Textual modal — real UI smoke must be human-verified | Run `voss` against a fixture file, invoke a plan that calls `fs_edit_many` with 3 hunks, accept/reject/skip each, confirm batch outcome matches modal decisions |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
