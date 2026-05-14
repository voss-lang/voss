---
phase: M8
slug: project-memory-mem-01
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase M8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Task-level rows populated by planner — see M8-RESEARCH.md `## Validation Architecture` for source mapping (14 new test files + 2 extended).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (project standard — see `tests/` + existing `pyproject.toml`) |
| **Config file** | `pyproject.toml` ([tool.pytest.ini_options]) |
| **Quick run command** | `pytest tests/harness/test_memory_store.py tests/harness/test_voss_md.py -x` |
| **Full suite command** | `pytest tests/ -x --timeout=60` |
| **Estimated runtime** | ~45 seconds (target — measured after Wave 0) |

---

## Sampling Rate

- **After every task commit:** Run quick command for the touched module
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

*Populated by planner during plan generation. Each task's `<automated>` block references one row.*

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD-by-planner | — | — | — | — | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 = scaffolding before behavioral implementation. From RESEARCH.md:

- [ ] `tests/harness/conftest.py` — shared fixtures: tmp_voss_repo, fake_session_corpus, chroma_disabled_env
- [ ] `tests/harness/test_voss_md.py` — stubs for SPEC Req 1 (loader + injection)
- [ ] `tests/harness/test_voss_md_migration.py` — stubs for SPEC Req 2 (architecture.md migration)
- [ ] `tests/harness/test_memory_store.py` — stubs for SPEC Req 3 (recall store + chroma fallback)
- [ ] `tests/harness/test_memory_store_keyword.py` — stubs for Req 3 keyword fallback
- [ ] `tests/harness/test_conventions.py` — stubs for Req 4 (extraction + confirmation)
- [ ] `tests/harness/test_memory_slash.py` — stubs for Req 5 (/recall, /forget, /memory, /save)
- [ ] `tests/harness/test_memory_cli.py` — stubs for Req 6 (vacuum) + cap enforcement
- [ ] `tests/harness/test_memory_size_cap.py` — stubs for Req 6 (100MB cap + eviction)
- [ ] `tests/harness/test_runtime_reuse.py` — stub for Req 7 grep-gate (no parallel Memory classes)
- [ ] Skeletons: `voss/harness/voss_md.py`, `voss/harness/memory_store.py`, `voss/harness/conventions.py`, `voss/harness/memory_cli.py`
- [ ] Planner decision on Pitfall 1 (/save collision) + Pitfall 3 (portalocker dep)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TBD by planner | — | — | — |

*Conventions extraction quality (Req 4) may need a manual review row — planner to decide.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
