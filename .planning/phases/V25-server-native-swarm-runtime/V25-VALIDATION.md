---
phase: V25
slug: server-native-swarm-runtime
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-17
---

# Phase V25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from V25-RESEARCH.md § Validation Architecture. All requirements verified HEADLESSLY (API/CLI/pytest) — no UI in scope.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing harness suite) |
| **Config file** | `pyproject.toml` / `pytest.ini` |
| **Interpreter** | `.venv/bin/python` (bare python3 lacks harness deps) |
| **Quick run command** | `.venv/bin/python -m pytest tests/harness/test_swarm_store.py -x` |
| **Full suite command** | `.venv/bin/python -m pytest tests/harness/ tests/test_swarm_e2e.py -x` |
| **Estimated runtime** | ~15–40 s (unit); e2e longer (fake-turn seam, no live provider) |

---

## Sampling Rate

- **After every task commit:** `.venv/bin/python -m pytest tests/harness/test_swarm_store.py -x`
- **After every plan wave:** `.venv/bin/python -m pytest tests/harness/ tests/test_swarm_e2e.py -x`
- **Before `/gsd-verify-work`:** Full suite green
- **Max feedback latency:** ~40 s

---

## Per-Requirement Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| VSWARM-01 | SwarmStore state reconstructs from JSONL replay | unit | `pytest tests/harness/test_swarm_store.py::test_replay_reconstructs_state -x` | ❌ W0 | ⬜ pending |
| VSWARM-01 | JSONL append-only (no rewrite) | unit | `pytest tests/harness/test_swarm_store.py::test_event_log_append_only -x` | ❌ W0 | ⬜ pending |
| VSWARM-02 | All 5 swarm SSE event types delivered to subscriber | unit | `pytest tests/harness/server/test_swarm_routes.py::test_swarm_sse_event_types -x` | ❌ W0 | ⬜ pending |
| VSWARM-03 | POST/GET /swarm bearer-auth + 401 without token | unit | `pytest tests/harness/server/test_swarm_routes.py::test_swarm_auth -x` | ❌ W0 | ⬜ pending |
| VSWARM-04 | Builder runs zero turns until `swarm.assign` (deterministic) | unit | `pytest tests/harness/test_swarm_store.py::test_spawn_gate_zero_turns_before_assign -x` | ❌ W0 | ⬜ pending |
| VSWARM-05 | Write outside ownedFiles denied at gate + escalation emitted | unit | `pytest tests/harness/test_swarm_store.py::test_ownership_denies_non_owned_write -x` | ❌ W0 | ⬜ pending |
| VSWARM-06 | Overlapping ownedFiles rejected 4xx; dependsOn-ordered accepted | unit | `pytest tests/harness/server/test_swarm_routes.py::test_overlap_rejected -x` | ❌ W0 | ⬜ pending |
| VSWARM-07 | Recall hits scoped to task ownedFiles; no default scout | unit | `pytest tests/harness/test_swarm_store.py::test_recall_scoped_to_owned_files -x` | ❌ W0 | ⬜ pending |
| VSWARM-08 | 3-role swarm spawns sessions w/ distinct resolved models | unit | `pytest tests/harness/server/test_swarm_routes.py::test_per_role_model_routing -x` | ❌ W0 | ⬜ pending |
| VSWARM-09 | Swarm state carries swarm_id/role/owned_files, listable by swarm | unit | `pytest tests/harness/test_swarm_store.py::test_agent_registry_swarm_columns -x` | ❌ W0 | ⬜ pending |
| VSWARM-10 | Operator escalation answerable via /permission; reviewer reject writes decision .md | unit | `pytest tests/harness/server/test_swarm_routes.py::test_operator_escalation -x` | ❌ W0 | ⬜ pending |
| VSWARM-11 | Replay yields full ordered task-state timeline, no gaps | unit | `pytest tests/harness/test_swarm_store.py::test_audit_replay_full_timeline -x` | ❌ W0 | ⬜ pending |
| **E2E bar** | **2-builder enforced run** (SPEC acceptance): assign 2 disjoint tasks → owned-only edits → 3rd-file write denied → reviewer gate → `swarm.complete` → events.jsonl replays | integration | `pytest tests/test_swarm_e2e.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

New test + source files (none exist yet):
- [ ] `voss/harness/swarm_store.py` — SwarmStore (must exist before tests import)
- [ ] `voss/harness/swarm/__init__.py`, `voss/harness/swarm/events.py` — append-only JSONL event-log writer (fs2 lock + temp-rename discipline)
- [ ] `voss/harness/swarm/prompts/coordinator.md`, `builder.md`, `reviewer.md` — **authored from scratch** (BridgeSwarm playbook confirmed absent from disk)
- [ ] `tests/harness/test_swarm_store.py` — VSWARM-01, 04, 05, 06, 07, 09, 11
- [ ] `tests/harness/server/test_swarm_routes.py` — VSWARM-02, 03, 06, 08, 10
- [ ] `tests/test_swarm_e2e.py` — 2-builder enforced integration test (SPEC acceptance bar)

**Reusable existing infrastructure:**
- `tests/harness/test_server_app.py` — `VOSS_SERVE_FAKE_TURN` seam + `TestClient` pattern; V25 tests monkeypatch `_resolve_provider` + `run_turn`, drive via `TestClient`.
- `tests/harness/test_permissions*.py` — import + reuse `PermissionGate.check` directly for ownership tests.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| VSWARM-09 Rust SQLite column migration on live agent-registry | VSWARM-09 | Rust crate test boundary; headless acceptance defaults to the Python-side SwarmStore index (research Open Q2). The Rust `agent_sessions` column add is verified in `cargo test`, separate from the Python acceptance. | `cargo test -p voss-app-core agent_registry` |

*Coordinator decomposition QUALITY is intentionally NOT validated here — out of scope per SPEC (validated separately via E-track).*

---

## Validation Sign-Off

- [ ] All requirements have an automated verify or a Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING test/source references
- [ ] No watch-mode flags
- [ ] Feedback latency < 40 s
- [ ] `nyquist_compliant: true` set in frontmatter (after Wave 0 lands)

**Approval:** pending
