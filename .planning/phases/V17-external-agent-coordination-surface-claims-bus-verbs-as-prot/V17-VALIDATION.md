---
phase: V17
slug: external-agent-coordination-surface-claims-bus-verbs-as-prot
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-09
---

# Phase V17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (harness Python) + cargo test (Rust spawn paths) + vitest (voss-app TS) |
| **Config file** | pyproject.toml / Cargo.toml / apps/voss-app/vitest config — existing |
| **Quick run command** | `.venv/bin/python -m pytest tests/ -k "claims or bus" -q` (focused) |
| **Full suite command** | `.venv/bin/python -m pytest -q` + `cd apps/voss-app && npx vitest run` + `cargo test -p voss-app-core` |
| **Estimated runtime** | ~60–180 seconds (full, per stack) |

---

## Sampling Rate

- **After every task commit:** Run the focused quick command for the touched stack
- **After every plan wave:** Run the full suite command(s) for touched stacks
- **Before `/gsd-verify-work`:** Full suite must be green (incl. `test_contract_drift.py` + sdk/go drift gate when event union changes)
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner — every VBUS-01..08 acceptance criterion maps to a pytest/cargo/vitest assertion or documented manual check) | | | VBUS-01..08 | — | claims storage path-jailed to project dirs; bearer auth on all /bus routes | unit/integration | per-plan | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_claims.py` — stubs for VBUS-01/02 (stake/check/release/extend/list, TTL, concurrency race, URI overlap)
- [ ] `tests/test_bus.py` — stubs for VBUS-04/05 (send/inbox/wait, journal durability, event union additivity) — V15-gated wave
- [ ] Existing pytest infra covers fixtures; no framework install needed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Managed-launched pane env contains VOSS_AGENT_ID end-to-end in the running app | VBUS-03 | Requires live Tauri app + PTY | Launch agent via modal; run `env \| grep VOSS_AGENT_ID` in pane |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
