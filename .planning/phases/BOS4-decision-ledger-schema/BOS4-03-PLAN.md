---
phase: BOS4-decision-ledger-schema
plan: BOS4-03
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/bos_decisions.py
  - tests/harness/test_bos_decision_ledger.py
autonomous: true
requirements: [BOS-DATA-02]

must_haves:
  truths:
    - "A decision record can be appended to .voss/bos/decisions.jsonl at decision time"
    - "Every emitted record validates against contracts/decision-ledger.schema.json"
    - "Re-appending a record with a known decision_id is a no-op (byte-identical file)"
    - "A torn trailing line does not make the decisions ledger unreadable"
    - "as_of carries the last event_id from the BOS3 events ledger (or null/empty when absent)"
    - "task_to_agent and permission-verdict records carry minimal-real feature_snapshot (no fabricated data)"
  artifacts:
    - path: "voss/harness/bos_decisions.py"
      provides: "BosDecisionLedger writer + record builders + as_of tail helper"
      contains: "class BosDecisionLedger"
      min_lines: 120
    - path: "tests/harness/test_bos_decision_ledger.py"
      provides: "Regression-gate tests mirroring test_bos_event_ledger.py"
      contains: "validator.validate"
  key_links:
    - from: "voss/harness/bos_decisions.py"
      to: "contracts/decision-ledger.schema.json"
      via: "builders emit all required envelope fields"
      pattern: "decision_id|as_of|feature_snapshot|human_verdict"
    - from: "voss/harness/bos_decisions.py"
      to: ".voss/bos/events.jsonl"
      via: "_read_last_event_id tail scan for as_of"
      pattern: "_read_last_event_id"
---

<objective>
Build the decision-ledger runtime writer and record builders in a new module
`voss/harness/bos_decisions.py`. This is the foundation the two gate-wiring plans
(BOS4-04, BOS4-05) consume. The module mirrors the BOS3 `bos_ledger.py`
append/dedup/torn-line/0o600 pattern exactly, but dedups by `decision_id`, writes
to `.voss/bos/decisions.jsonl`, and adds builders that produce schema-valid
records for the two decision types with a real runtime producer today.

This plan deliberately establishes the **inline-emission** contract (D-R01): the
module's docstring and the builders make explicit that decisions are written AT
decision time carrying frozen state, NOT reconstructed by after-the-fact
projection like BOS3's `bos_events.py`.

Purpose: Covers the storage + record-construction half of BOS-DATA-02. Without a
schema-valid writer, no gate can emit.
Output: `voss/harness/bos_decisions.py`, `tests/harness/test_bos_decision_ledger.py`.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md
@.planning/phases/BOS4-decision-ledger-schema/BOS4-PATTERNS.md
@contracts/decision-ledger.schema.json
@voss/harness/bos_ledger.py
@voss/harness/bos_events.py
@tests/harness/test_bos_event_ledger.py

<interfaces>
<!-- Target contract (contracts/decision-ledger.schema.json). Every record MUST -->
<!-- carry ALL of these top-level keys (all are "required"); none may be null    -->
<!-- except where the field type permits it: -->
<!--   decision_id (string), decision_type (enum: task_to_agent | autonomy_band -->
<!--     | review_depth | validation_depth | escalation | no_action), -->
<!--   created_at (date-time string), as_of (object: {event_seq?: int, -->
<!--     snapshot_id?: string}, additionalProperties:true), -->
<!--   feature_snapshot (object, additionalProperties:true), -->
<!--   entity_ref (object: {task_id?, session_id?, agent_id?, swarm_id?}, -->
<!--     additionalProperties:true), -->
<!--   autonomy_band (string), recommended_action (object, additionalProperties:true),-->
<!--   human_verdict (object, additionalProperties:false, REQUIRED sub-keys: -->
<!--     verdict in {approve, override, dismiss, do_nothing}, actor_id, verdict_at), -->
<!--   actual_action (object), rationale (string), -->
<!--   payload (oneOf the 6 typed payloads, discriminated by decision_type). -->

<!-- CRITICAL RECONCILIATION: the enum has NO "permission_verdict" type. The only -->
<!-- non-policy-producer types available today are task_to_agent and no_action. A -->
<!-- human permission verdict is therefore emitted as decision_type="no_action" -->
<!-- (NoActionPayload: {decision_type, reason?}), carrying the human answer in the -->
<!-- human_verdict object. This is wired in BOS4-05; THIS plan only needs the -->
<!-- builder. -->

<!-- Pre-BOS9 field values (D-R03, PATTERNS finding #5 — schema forbids nulls on -->
<!-- object-typed required fields): recommended_action = {} (empty object), -->
<!-- actual_action = the chosen action object, autonomy_band = "" (or the active -->
<!-- band string if available), rationale = prose describing the gate. -->

From voss/harness/bos_ledger.py (the writer pattern to mirror exactly):
- ledger_path(cwd) -> Path  (.voss/bos/events.jsonl)
- class BosEventLedger: append_event, append_many (portalocker LOCK_EX|LOCK_NB,
  timeout 10s, dedup-by-id under lock, chmod 0o600 after write), read_events
  (torn-line tolerant: break on first JSONDecodeError)
- module fns append_event / append_many / read_events delegating to the class
- _event_id(event) raises ValueError if missing; _read_event_ids(f) scans ids

From voss/harness/bos_events.py:
- _now_iso() -> str  (datetime.now(timezone.utc).isoformat(timespec="seconds"))
- BOS3 events carry top-level "event_id"; _read_last_event_id reads that key
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Write failing tests for BosDecisionLedger + builders (RED)</name>
  <files>tests/harness/test_bos_decision_ledger.py</files>
  <read_first>
    - tests/harness/test_bos_event_ledger.py (analog — mirror header, validator fixture, append/replay/dedup/torn-line tests verbatim where noted in PATTERNS)
    - contracts/decision-ledger.schema.json (the schema the validator fixture loads)
    - .planning/phases/BOS4-decision-ledger-schema/BOS4-PATTERNS.md (lines 281-362 give the exact test mirrors)
  </read_first>
  <behavior>
    - validator fixture (scope="module") loads contracts/decision-ledger.schema.json
      via jsonschema.Draft202012Validator; SCHEMA_PATH = REPO / "contracts" /
      "decision-ledger.schema.json" (NOT .planning/schemas/).
    - test_records_append_replay_and_validate: build one task_to_agent record via
      build_task_to_agent_record(...) and one verdict record via
      build_verdict_record(...); append both via BosDecisionLedger(tmp_path);
      assert ledger.path == tmp_path/".voss"/"bos"/"decisions.jsonl"; assert
      replay order by decision_id; assert validator.validate(record) passes for each.
    - test_duplicate_decision_id_is_noop_and_preserves_bytes: append a record,
      capture file bytes, append a dict copy, assert append returns False and
      bytes unchanged.
    - test_read_decisions_tolerates_torn_trailing_line: write one valid line plus
      a torn `{"decision_id":` suffix; assert read_decisions returns [record].
    - test_as_of_reads_last_event_id: write a .voss/bos/events.jsonl with two
      events (event_id "e1","e2"); assert _read_last_event_id(events_path) == "e2";
      empty/absent file returns None.
    - test_verdict_record_uses_no_action_type: build_verdict_record produces
      decision_type=="no_action" and human_verdict.verdict in {approve,dismiss},
      and validates against the schema.
  </behavior>
  <action>
    Create tests/harness/test_bos_decision_ledger.py mirroring
    tests/harness/test_bos_event_ledger.py. Import BosDecisionLedger,
    append_decision, read_decisions, build_task_to_agent_record,
    build_verdict_record, _read_last_event_id from voss.harness.bos_decisions.
    Set SCHEMA_PATH = REPO / "contracts" / "decision-ledger.schema.json". Reuse the
    module-scope validator fixture verbatim. Write the six tests in the behavior
    block. Tests MUST fail now (module does not exist yet) — this is RED.
  </action>
  <verify>
    <automated>.venv/bin/pytest tests/harness/test_bos_decision_ledger.py -x 2>&1 | grep -qE "ModuleNotFoundError|ImportError|collected 6" && echo RED-OK</automated>
  </verify>
  <acceptance_criteria>
    - tests/harness/test_bos_decision_ledger.py exists with 6 test functions
    - SCHEMA_PATH points at contracts/decision-ledger.schema.json
    - Running pytest fails on import (module missing) — confirms RED before GREEN
  </acceptance_criteria>
  <done>Test file written; all tests fail because bos_decisions.py does not yet exist.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement bos_decisions.py writer + builders + as_of helper (GREEN)</name>
  <files>voss/harness/bos_decisions.py</files>
  <read_first>
    - voss/harness/bos_ledger.py (copy append_many / read_events / _event_id /
      _read_event_ids / module wrappers verbatim, renaming event_id→decision_id)
    - voss/harness/bos_events.py (lines 27-28 _now_iso; envelope/builder keyword-only style)
    - contracts/decision-ledger.schema.json (required envelope fields + the 2 payload $defs used: TaskToAgentPayload, NoActionPayload)
    - .planning/phases/BOS4-decision-ledger-schema/BOS4-PATTERNS.md (lines 22-211 give verbatim writer code + the _read_last_event_id pattern)
    - tests/harness/test_bos_decision_ledger.py (the tests this must turn green)
  </read_first>
  <action>
    Create voss/harness/bos_decisions.py. Module docstring MUST state the
    inline-emission contract (D-R01): decisions are written AT decision time
    carrying frozen state, a deliberate break from BOS3's pure projection
    (bos_events.py). Implement:

    1. decisions_ledger_path(cwd) -> Path returning
       Path(cwd).resolve()/".voss"/"bos"/"decisions.jsonl" (copy of ledger_path,
       last segment changed).
    2. class BosDecisionLedger with append_decision / append_decisions /
       read_decisions, copied from bos_ledger.py's append_event / append_many /
       read_events. Dedup by decision_id via _decision_id / _read_decision_ids
       (copies of _event_id / _read_event_ids reading the "decision_id" key;
       ValueError message "BOS decision record missing decision_id"). Keep
       portalocker LOCK_EX|LOCK_NB timeout 10s, sort_keys=True writes,
       parent.mkdir, chmod(0o600). read_decisions filter kwarg = decision_type only.
    3. _read_last_event_id(events_path: Path) -> str | None — cheap line-by-line
       tail scan of the BOS3 events ledger (do NOT call BosEventLedger.read_events);
       torn-line break-on-JSONDecodeError; returns last valid top-level "event_id"
       or None when absent/empty. Also expose _read_event_seq or count lines so
       as_of.event_seq can be set (D-R05). Use this to assemble as_of in a small
       helper build_as_of(events_path) -> dict returning {} when empty or
       {"event_seq": <count>, "snapshot_id": <last_event_id>}.
    4. _now_iso() copied from bos_events.py.
    5. build_task_to_agent_record(*, decision_id, task_id, chosen_agent_id,
       candidate_agents, feature_snapshot, entity_ref, as_of, rationale,
       autonomy_band="") -> dict. Returns the full envelope with decision_type
       "task_to_agent", created_at=_now_iso(), recommended_action={},
       actual_action={"chosen_agent_id": chosen_agent_id}, human_verdict an empty
       human_verdict is NOT valid (verdict/actor_id/verdict_at required) — for
       task_to_agent the gate decision has no human prompt, so set human_verdict
       to a do_nothing/system placeholder ONLY IF schema-valid; VERIFY against
       schema: human_verdict is a required object whose sub-keys are required, so
       populate {verdict:"approve", actor_id:"system", verdict_at:_now_iso()}
       representing the automatic assignment with no human override path
       (pre-BOS9). Payload = TaskToAgentPayload {decision_type:"task_to_agent",
       task_id, chosen_agent_id, candidate_agents}.
    6. build_verdict_record(*, decision_id, verdict, actor_id, feature_snapshot,
       entity_ref, as_of, rationale, reason=None, autonomy_band="") -> dict.
       decision_type="no_action" (no permission_verdict enum value exists);
       human_verdict={verdict, actor_id, verdict_at:_now_iso()} where verdict in
       {approve, dismiss}; recommended_action={}, actual_action reflects the gate
       outcome (e.g. {"allowed": verdict=="approve"}); payload = NoActionPayload
       {decision_type:"no_action", reason}. rationale describes the gate.
    7. Module-level append_decision / append_decisions / read_decisions wrappers
       delegating to BosDecisionLedger, plus __all__.

    Reconcile every field against contracts/decision-ledger.schema.json before
    finishing — the tests validate against it. Do NOT inline outcome data
    (no-leakage guard, schema D-04). Do NOT add stub rows for the four
    no-producer decision types.
  </action>
  <verify>
    <automated>.venv/bin/pytest tests/harness/test_bos_decision_ledger.py -x 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - tests/harness/test_bos_decision_ledger.py exits 0 (all 6 tests pass)
    - Both build_task_to_agent_record and build_verdict_record outputs pass
      jsonschema.validate against contracts/decision-ledger.schema.json
    - .venv/bin/python -c "import voss.harness.bos_decisions" succeeds
    - grep -q "inline" voss/harness/bos_decisions.py (D-R01 contract documented)
    - No new decision_type values beyond task_to_agent and no_action are emitted
  </acceptance_criteria>
  <done>Writer + builders + as_of helper implemented; full decision-ledger test file green via .venv/bin/pytest.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| gate/runtime → decisions.jsonl | decision records (operator/agent identity, file paths, tool args) cross into a persisted local ledger |
| BOS3 events.jsonl → as_of read | this module reads (never writes) the sibling event ledger to set the point-in-time pointer |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-BOS4-03-01 | Information Disclosure | feature_snapshot / payload capturing tool args or secrets | mitigate | Builders accept ONLY the minimal-real fields named in D-R06; callers (BOS4-04/05) pass curated snapshots, never raw `args`. This plan's builders do not auto-serialize arbitrary arg dicts. |
| T-BOS4-03-02 | Tampering | decisions.jsonl file permissions | mitigate | chmod(0o600) after every append (copied verbatim from bos_ledger.py). |
| T-BOS4-03-03 | Tampering | torn/partial write corrupting ledger replay | mitigate | torn-line break-on-JSONDecodeError in read_decisions + _read_decision_ids (verbatim from bos_ledger). |
| T-BOS4-03-04 | Information Disclosure | outcome/label leakage into a decision record | accept | Schema D-04 forbids it; builders expose no outcome param. Enforced by schema additionalProperties:false at envelope level. |
| T-BOS4-03-SC | Tampering | new package installs | mitigate | None — only stdlib + already-vendored portalocker/jsonschema (both used by BOS3). No new dependency; no install task. |
</threat_model>

<verification>
- .venv/bin/pytest tests/harness/test_bos_decision_ledger.py exits 0
- .venv/bin/python -c "import voss.harness.bos_decisions" succeeds
- Emitted records validate against contracts/decision-ledger.schema.json (asserted in tests)
- .voss/bos/decisions.jsonl file mode is 0o600 after write
</verification>

<success_criteria>
- BosDecisionLedger appends, dedups by decision_id, replays torn-line-safely, chmods 0o600
- build_task_to_agent_record + build_verdict_record produce schema-valid records
- _read_last_event_id / build_as_of resolve as_of from the BOS3 event ledger tail
- All 6 tests green; module imports cleanly
</success_criteria>

<output>
Create `.planning/phases/BOS4-decision-ledger-schema/BOS4-03-SUMMARY.md` when done.
</output>
