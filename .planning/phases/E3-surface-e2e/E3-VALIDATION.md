---
phase: E3
slug: surface-e2e
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-10
---

# Phase E3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing; `.venv/bin/python -m pytest`) |
| **Config file** | existing repo pytest config |
| **Quick run command** | `.venv/bin/python -m pytest tests/eval -q -m "not slow and not live"` |
| **Full suite command** | `.venv/bin/python -m pytest tests/eval tests/e2e -q -m "not live"` |
| **Estimated runtime** | ~60 seconds |
| **Live seam (hermetic)** | `VOSS_SERVE_FAKE_TURN=1` for serve driver; stub sitecustomize for CLI drivers (tests only) |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

*(Filled by planner — every E3 task gets an `<automated>` verify against the stub/fake-turn seams; the live proof run is the single human-checkpoint exception, mirroring E1-05.)*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | — | — | EVSRF-* | — | — | unit/integration | pytest | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/eval/test_surface_drivers.py` — stubs for surface dispatch + CLI subprocess driver (stub sitecustomize) + serve driver (FAKE_TURN)
- [ ] Verify driver test scaffolds against REAL module APIs on disk before xfail (known fictional-API false-green hazard)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live full surfaces suite on codex auth (≥80% gate_pass, 0 capped, permission-gate scenario passing) | EVSRF live-proof | Needs operator subscription creds | `VOSS_DEV=1 voss eval --suite surfaces --auth codex`; inspect runs.jsonl + summary.md |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
