---
phase: V18
slug: budget-aware-context-allocator-token-optimization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-10
---

# Phase V18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Generated from `V18-RESEARCH.md` §Validation Architecture. Per-task map is filled by the planner.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Interpreter** | `.venv/bin/python` (bare `python3` lacks deps — REQUIRED) |
| **Quick run command** | `.venv/bin/python -m pytest tests/ -k context_allocator -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -q` |
| **Estimated runtime** | ~quick <10s · full per existing harness suite |

---

## Sampling Rate

- **After every task commit:** Run the quick command (allocator-scoped).
- **After every plan wave:** Run the full harness suite.
- **Before `/gsd-verify-work`:** Full suite green + `voss do`/`voss chat` smoke pass (PRD §9 top risk).
- **Max feedback latency:** ~10s (quick) / full-suite at wave boundaries.

---

## Per-Task Verification Map

*Filled by the planner once PLAN.md task IDs exist. Each VOPT requirement maps to at least one automated assertion (see V18-RESEARCH.md §Validation Architecture). Seed rows:*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| V18-01-xx | 01 | 1 | VOPT-01 | — | allocator is pure (no provider/fs) | unit | `pytest -k allocator_pure` | ❌ W0 | ⬜ pending |
| V18-0x-xx | 0x | x | VOPT-02 | — | tiered render full/digest/fold; newest full | unit | `pytest -k tier_render` | ❌ W0 | ⬜ pending |
| V18-0x-xx | 0x | x | VOPT-03 | — | stable replay-prefix hash unchanged under high-water; cache_read dominates | unit | `pytest -k cache_coherent` | ❌ W0 | ⬜ pending |
| V18-0x-xx | 0x | x | VOPT-04 | — | folded iter emits actionable re-fetch pointer; no index dep added | unit | `pytest -k eviction_pointer` | ❌ W0 | ⬜ pending |
| V18-0x-xx | 0x | x | VOPT-05 | — | ledger packed≤original; --no-pack ⇒ original==packed; $ nets cache reads | unit | `pytest -k savings_ledger` | ❌ W0 | ⬜ pending |
| V18-0x-xx | 0x | x | VOPT-06 | — | `--no-pack` messages byte-identical to pre-V18 | unit | `pytest -k no_pack_identical` | ❌ W0 | ⬜ pending |
| V18-0x-xx | 0x | x | VOPT-07 | — | packing-on success ≥ off−tol; over-aggressive profile fails gate | eval | `pytest -k packing_quality_gate` | ❌ W0 | ⬜ pending |
| V18-0x-xx | 0x | x | VOPT-08 | — | diff adds no index/embedding dep; recorder OSC shape unchanged | unit | `pytest -k coherence_guard` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_context_allocator.py` — RED stubs for VOPT-01..08
- [ ] `tests/conftest.py` — reuse existing FakeProvider + iteration-record fixtures
- [ ] No new framework — existing pytest harness covers all phase requirements

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/cost` savings line + F3 HUD render | VOPT-05 (D-01) | OSC HUD render is visual | Run a long `voss do`; confirm `context packed: X→Y (−Z%) ~$…` in `/cost` and the F3 budget HUD |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s (quick)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
