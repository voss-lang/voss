---
phase: V18
slug: budget-aware-context-allocator-token-optimization
status: complete
nyquist_compliant: true
wave_0_complete: true
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
| V18-02-01 | 02 | 2 | VOPT-01 | T-V18-04 | allocator is pure (no provider/fs); 50 iters under ceiling; byte-identical below threshold | unit | `pytest tests/harness/test_context_allocator.py -k "allocator_pure or under_ceiling or byte_identical"` | ✅ | ✅ green |
| V18-02-01 | 02 | 2 | VOPT-02 | T-V18-03 | tiered render full/digest/fold; newest full; packed ≤ full | unit | `pytest tests/harness/test_context_allocator.py -k "tier_boundaries or never_exceed_full"` | ✅ | ✅ green |
| V18-02-02 | 02 | 2 | VOPT-03 | T-V18-05 | stable-region hash unchanged below high-water; exactly one recompaction at crossing | unit | `pytest tests/harness/test_context_allocator.py -k "append_only or recompaction"` | ✅ | ✅ green |
| V18-03-02 | 03 | 3 | VOPT-03 | T-V18-08 | steady-state cache_read_input_tokens > 0 with packing on | integration | `pytest tests/harness/test_agent_packing.py::test_cache_coherence_steady_state` | ✅ | ✅ green |
| V18-02-01 | 02 | 2 | VOPT-04 | T-V18-03 | folded iter emits deduped re-fetch pointers capped at 5; no index dep | unit | `pytest tests/harness/test_context_allocator.py::test_eviction_pointer_emitted` | ✅ | ✅ green |
| V18-04-xx | 04 | 4 | VOPT-05 | T-V18-11/12 | ledger packed≤original; no-pack ⇒ original==packed; $ nets cache reads; /cost line | unit | `pytest tests/harness/test_savings_ledger.py` | ✅ | ✅ green |
| V18-03-02 | 03 | 3 | VOPT-06 | T-V18-06/07 | --no-pack messages byte-identical; T4 prefix unchanged | integration | `pytest tests/harness/test_agent_packing.py -k "no_pack_byte_identical or cached_prefix"` | ✅ | ✅ green |
| V18-05-02 | 05 | 5 | VOPT-07 | T-V18-14 | packing-on success ≥ off−tol on golden stub; regressing/inflating profile rejected (gate bites) | eval | `pytest tests/harness/test_packing_eval_gate.py` | ✅ | ✅ green |
| V18-05-03 | 05 | 5 | VOPT-08 | T-V18-15 | no index/embedding/vector dep in V18 diff; budget OSC frozen; no second budget emitter | unit | `pytest tests/harness/test_coherence_guard.py -k v18` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/harness/test_context_allocator.py` (+ test_agent_packing / test_savings_ledger / test_packing_eval_gate) — RED stubs for VOPT-01..08 (Plan 01)
- [x] Reused existing FakeStreamingProvider + SimpleNamespace iteration-record fixtures (no new conftest needed)
- [x] No new framework — existing pytest harness covers all phase requirements

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
