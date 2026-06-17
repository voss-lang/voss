---
phase: V25-server-native-swarm-runtime
plan: 06
type: execute
wave: 4
depends_on: [V25-01, V25-02, V25-04, V25-05]
files_modified:
  - tests/test_swarm_e2e.py
autonomous: true
requirements: [VSWARM-01, VSWARM-02, VSWARM-03, VSWARM-04, VSWARM-05, VSWARM-06, VSWARM-07, VSWARM-10, VSWARM-11]
must_haves:
  truths:
    - "A scripted 2-builder run passes as ONE integration test: coordinator assigns 2 disjoint-file tasks → both builders edit only owned files → a 3rd-file write is denied at the gate → reviewer gates → swarm.complete emitted → events.jsonl replays the run"
    - "The e2e uses the VOSS_SERVE_FAKE_TURN seam (no live provider) and zero nudge files / stdin injection"
  artifacts:
    - path: "tests/test_swarm_e2e.py"
      provides: "The 2-builder enforced end-to-end integration test (SPEC acceptance bar)"
      min_lines: 80
  key_links:
    - from: "tests/test_swarm_e2e.py"
      to: "the full /swarm + spawn-gate + ownership + events stack"
      via: "TestClient drives the whole runtime headlessly"
      pattern: "swarm.complete"
---

<objective>
Write the single 2-builder enforced end-to-end integration test that is the SPEC's acceptance bar: a coordinator assigns two disjoint-file tasks, both builders edit only their owned files, a third-file write is denied at the gate, a reviewer gates, `swarm.complete` is emitted, and the `events.jsonl` replays the whole run. This is the terminal Wave-4 gate that proves the V25 runtime works as a system.

Purpose: Every prior plan verified one requirement in isolation. This test exercises the integrated path end-to-end (VSWARM-01/02/03/04/05/06/07/10/11 in one run) and is the closing acceptance criterion from SPEC §Acceptance Criteria and the VALIDATION e2e row.

Output: `tests/test_swarm_e2e.py`.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V25-server-native-swarm-runtime/V25-SPEC.md
@.planning/phases/V25-server-native-swarm-runtime/V25-VALIDATION.md
@.planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md

<interfaces>
<!-- The full stack assembled by V25-01..05 -->
/swarm routes (V25-04): POST /swarm, GET /swarm/{id}, POST /swarm/{id}/task, POST /swarm/{id}/message.
Spawn-gate (V25-04): gated builders await swarm.assign; gate_event.set() unblocks in-process.
Ownership (V25-05): swarm_policy denies writes outside ownedFiles at PermissionGate; emits swarm.needs_operator.
Events (V25-02): swarm.assign/worker_done/gate/needs_operator/complete on the SSE bus.
Replay (V25-01): SwarmStore.replay(swarm_id) reconstructs task timeline from events/events.jsonl.

<!-- Test seam — verified -->
VOSS_SERVE_FAKE_TURN (app.py:93, :185-197): hermetic canned turn over the real event/SSE path, no provider.
TestClient fixture pattern: tests/harness/test_server_app.py monkeypatches _resolve_provider + run_turn,
drives via fastapi.testclient.TestClient with a Bearer token. GET /session/{id}/events streams SSE.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: 2-builder enforced end-to-end integration test</name>
  <read_first>
    - tests/harness/test_server_app.py (TestClient + monkeypatch fixture, SSE event consumption pattern, Bearer auth helper)
    - tests/harness/server/test_swarm_routes.py (the route + spawn-gate + ownership tests from V25-04/05 — reuse their fixtures/helpers)
    - voss/harness/swarm_store.py (replay API from V25-01)
    - .planning/phases/V25-server-native-swarm-runtime/V25-SPEC.md (§Acceptance Criteria — the e2e bar, last bullet)
    - .planning/phases/V25-server-native-swarm-runtime/V25-VALIDATION.md (E2E bar row + sampling)
  </read_first>
  <action>
    Create `tests/test_swarm_e2e.py` with one integration test driving the whole runtime headlessly via `TestClient` under the `VOSS_SERVE_FAKE_TURN` seam (no live provider). Script the SPEC acceptance bar in order: (1) POST /swarm to create + seed a goal; (2) the coordinator adds 2 tasks via POST /swarm/{id}/task with DISJOINT ownedFiles (e.g. task A owns `a.py`, task B owns `b.py`) — assert both succeed and a third task overlapping an active task's files is rejected 4xx (VSWARM-06); (3) spawn 2 builder sessions gated (waiting), assert each runs zero turns until its swarm.assign (VSWARM-04); (4) on assign, each builder edits ONLY its owned file (allowed) and a write to a 3rd file is DENIED at the gate with swarm.needs_operator emitted (VSWARM-05/10); (5) a reviewer gate runs and a `.voss/decisions/*.md` is written (VSWARM-10); (6) assert `swarm.complete` is emitted (VSWARM-02); (7) call `SwarmStore.replay(swarm_id)` and assert the reconstructed task timeline shows each task open→assigned→done in order with no gaps (VSWARM-01/11). Assert NO nudge file and NO stdin injection were used (the path goes through routes + SSE only). Keep it ONE test function (the SPEC bar is "passes as one integration test"). Reuse helpers from tests/harness/server/test_swarm_routes.py where possible.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/test_swarm_e2e.py -x</automated>
  </verify>
  <acceptance_criteria>
    The scripted 2-builder run passes as ONE integration test covering: 2 disjoint-task assign, owned-only edits, 3rd-file gate denial + escalation, reviewer gate + decision .md, swarm.complete, and events.jsonl replay of the full ordered timeline — with no nudge/stdin. Matches SPEC §Acceptance Criteria final bullet and the VALIDATION E2E row. `pytest tests/test_swarm_e2e.py -x` PASSES.
  </acceptance_criteria>
  <done>The single 2-builder enforced e2e test passes, exercising the integrated runtime end-to-end.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test harness → full runtime | the e2e drives every trust boundary the prior plans established, in one path |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V25-06-01 | Elevation of privilege | e2e passes while ownership deny is actually a no-op | mitigate | The test asserts the 3rd-file write is DENIED (gate returns deny, edit absent) AND swarm.needs_operator emitted — a no-op deny fails the test |
| T-V25-06-02 | Repudiation | run not reconstructable from disk | mitigate | The test replays events.jsonl and asserts the full ordered open→assigned→done timeline with no gaps (VSWARM-11) |
| T-V25-06-03 | Tampering | hidden nudge/stdin path slips through | mitigate | Test asserts no nudge file written and no stdin injection — the SPEC anti-pattern guard |
| T-V25-06-SC | Tampering | npm/pip installs | accept | No new packages (RESEARCH audit empty) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/test_swarm_e2e.py -x` green
- Full phase suite green: `.venv/bin/python -m pytest tests/harness/ tests/test_swarm_e2e.py -x`
- `git diff --check` clean
</verification>

<success_criteria>
- The 2-builder enforced run passes as one integration test (SPEC acceptance bar)
- Covers assign → owned-only edits → 3rd-file deny → reviewer gate → swarm.complete → events replay
- Zero nudge files / stdin injection
</success_criteria>

<output>
Create `.planning/phases/V25-server-native-swarm-runtime/V25-06-SUMMARY.md` when done
</output>
