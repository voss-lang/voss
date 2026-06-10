---
phase: V17
slug: external-agent-coordination-surface-claims-bus-verbs-as-prot
status: draft
nyquist_compliant: true
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
| V17-01-T1 | V17-01 | 1 | VBUS-01,02,06 | T-V17-01 | tmp_path-jailed test writes | scaffold (RED) | `.venv/bin/python -m pytest tests/harness/claims/ --co -q` | ❌ W0 | ⬜ pending |
| V17-01-T2 | V17-01 | 1 | VBUS-04,05 | — | xfail-gated, no live secrets | scaffold (xfail) | `.venv/bin/python -m pytest tests/harness/bus/ -q` | ❌ W0 | ⬜ pending |
| V17-01-T3 | V17-01 | 1 | VBUS-03,07,08 | T-V17-01,T-V17-SC | runtime-hash baseline, no fs-watcher dep | scaffold + guard | `.venv/bin/python -m pytest tests/harness/test_coherence_guard.py -q` | ❌ W0 | ⬜ pending |
| V17-02-T1 | V17-02 | 2 | VBUS-01,02 | T-V17-02 | canonicalize rejects `..` traversal; no fs reads in overlap | unit (TDD) | `.venv/bin/python -m pytest tests/harness/claims/test_overlap.py -x -q` | ❌ W0 | ⬜ pending |
| V17-02-T2 | V17-02 | 2 | VBUS-02 | T-V17-03,T-V17-04 | BEGIN IMMEDIATE exactly-one-winner; path-jailed db | integration (TDD) | `.venv/bin/python -m pytest tests/harness/claims/test_claims_concurrent.py tests/harness/claims/test_claims_ttl.py -x -q` | ❌ W0 | ⬜ pending |
| V17-03-T1 | V17-03 | 3 | VBUS-01,02,06 | T-V17-06 | identity exit-2; canonicalized patterns | acceptance (TDD) | `.venv/bin/python -m pytest tests/harness/claims/test_claims_verbs.py tests/harness/claims/test_claims_advice.py -x -q` | ❌ W0 | ⬜ pending |
| V17-03-T2 | V17-03 | 3 | VBUS-01 | — | surgical register, no board/jobs edits | integration | `.venv/bin/python -c "from voss.harness import cli; assert any(getattr(c,'name',None)=='claims' for c in cli.AGENT_COMMANDS)"` | ❌ W0 | ⬜ pending |
| V17-04-T1 | V17-04 | 2 | VBUS-03 | — | slug from controlled CLI set | unit (TDD) | `cd apps/voss-app && npx vitest run src/pane/slugRegistry.test.ts` | ❌ W0 | ⬜ pending |
| V17-04-T2 | V17-04 | 2 | VBUS-03 | — | camelCase IPC field threaded | typecheck | `cd apps/voss-app && npx tsc --noEmit` | ❌ W0 | ⬜ pending |
| V17-04-T3 | V17-04 | 2 | VBUS-03 | T-V17-09,T-V17-10 | owned-env injects only VOSS_AGENT_ID; Some/None round-trip asserted (no silent None) | unit (Rust) | `cargo test -p voss-app build_env_with_agent_id 2>&1 \| tail -5 \|\| cargo test -p voss-app-core build_env_with_agent_id 2>&1 \| tail -5` | ❌ W0 | ⬜ pending |
| V17-05-T1 | V17-05 | 4 (V15-gated) | VBUS-05 | T-V17-13 | additive-only event union; Go+Py drift gates | acceptance | `.venv/bin/python -m pytest tests/harness/server/test_contract_drift.py -x -q` + `cd sdk/go && go test ./internal/drift/...` | ✅ (drift gate exists) | ⬜ pending |
| V17-05-T2 | V17-05 | 4 (V15-gated) | VBUS-04,05 | T-V17-11,12,14 | bearer-authed routes; sole-writer journal; drop-on-QueueFull | integration | `.venv/bin/python -m pytest tests/harness/bus/ -x -q` | ❌ W0 | ⬜ pending |
| V17-06-T1 | V17-06 | 5 (V15-gated) | VBUS-04,06 | T-V17-15,16,17 | discovery exit-2; token in header not argv; timeout exit-124 | integration | `.venv/bin/python -m pytest tests/harness/bus/test_bus_wait.py tests/harness/bus/test_bus_inbox.py -x -q` | ❌ W0 | ⬜ pending |
| V17-06-T2 | V17-06 | 5 (V15-gated) | VBUS-04 | — | surgical register, no collateral edits | integration | `.venv/bin/python -c "from voss.harness import cli; assert any(getattr(c,'name',None)=='bus' for c in cli.AGENT_COMMANDS)"` | ❌ W0 | ⬜ pending |
| V17-07-T1 | V17-07 | 4 | VBUS-07 | T-V17-18 | doc states no secrets in bus messages | doc check | `.venv/bin/python -m pytest tests/harness/test_coordination_doc.py -x -q` | ❌ W0 | ⬜ pending |
| V17-07-T2 | V17-07 | 4 | VBUS-08 | T-V17-19 | coherence guard: no parallel substrate/UI/fs-watcher; sandbox.rs untouched | guard | `.venv/bin/python -m pytest tests/harness/test_coherence_guard.py -x -q && cargo test -p voss-app-core` | ❌ W0 | ⬜ pending |

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
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
