---
phase: BOS4-decision-ledger-schema
plan: BOS4-05
type: execute
wave: 2
depends_on: [BOS4-03]
files_modified:
  - voss/harness/permissions.py
  - tests/harness/test_bos_decision_permission_emit.py
autonomous: true
requirements: [BOS-DATA-02]

must_haves:
  truths:
    - "When a human answers a permission prompt, a decision record is appended to .voss/bos/decisions.jsonl"
    - "allow-once / allow-always map to human_verdict.verdict = approve; deny maps to dismiss"
    - "Auto-allows and non-interactive denials do NOT emit a record (no human answered)"
    - "The emitted record validates against contracts/decision-ledger.schema.json"
  artifacts:
    - path: "voss/harness/permissions.py"
      provides: "human-verdict emission from the _prompt return path"
      contains: "build_verdict_record"
    - path: "tests/harness/test_bos_decision_permission_emit.py"
      provides: "verdict-emission + no-emit-on-auto test"
      contains: "decisions.jsonl"
  key_links:
    - from: "voss/harness/permissions.py"
      to: "voss/harness/bos_decisions.py"
      via: "build_verdict_record + append_decision after a human answer in _prompt"
      pattern: "build_verdict_record|append_decision"
---

<objective>
Wire the SECOND real decision producer: human-answered permission verdicts. In
`PermissionGate._prompt` (permissions.py lines 442-456), AFTER `choice =
prompt(tool_name, args)` resolves (i.e. a human was actually shown a prompt and
answered), emit a decision record using the builders from BOS4-03.

Per D-R04 ONLY human-prompted answers become records: allow-once / allow-always →
`human_verdict.verdict = approve`; deny → `dismiss`. The non-interactive
short-circuit (`prompt_fn is None and not sys.stdin.isatty()`) and all auto-allow
paths in `_check_impl` (auto mode, remembered, rule-allow) MUST NOT emit — they
are not human decisions. `override` and `do_nothing` are reserved (no
recommendation to diverge from until BOS9).

Because the schema enum has NO `permission_verdict` type, the verdict record uses
`decision_type = "no_action"` (the only non-policy-producer type available),
carrying the human answer in `human_verdict`. This was settled in BOS4-03's
build_verdict_record.

Purpose: Delivers the human-verdict half of BOS-DATA-02's runtime coverage.
Output: emission in `permissions.py`, new emission test.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md
@.planning/phases/BOS4-decision-ledger-schema/BOS4-PATTERNS.md
@contracts/decision-ledger.schema.json
@voss/harness/permissions.py

<interfaces>
<!-- From BOS4-03 (voss/harness/bos_decisions.py): -->
- build_verdict_record(*, decision_id, verdict, actor_id, feature_snapshot,
    entity_ref, as_of, rationale, reason=None, autonomy_band="") -> dict
    # verdict in {approve, dismiss}; decision_type emitted is "no_action"
- build_as_of(events_path: Path) -> dict
- append_decision(cwd, record) -> bool

<!-- From voss/harness/permissions.py: -->
- PermissionGate (dataclass): fields mode, store, auto_yes, prompt_fn,
  edit_scope, ... NO cwd field today.
- _prompt(self, tool_name, args) -> tuple[bool, str]:
    line 446-447: if prompt_fn is None and not stdin.isatty(): return False,
      "non-interactive denial"   <-- NO human; DO NOT emit
    line 448-449: choice = prompt(tool_name, args)   <-- human answered AFTER this
    choice=="a"  -> approve (allowed once)
    choice=="A"  -> approve (allowed always)
    else         -> dismiss  (denied)
- self.mode, self.signature(tool_name, args) available for feature_snapshot
- _check_impl auto-allow paths that must NOT emit: "auto" (line 345),
  "remembered" (line 349), rule "allow" (line 339)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Emit verdict record after a human answers _prompt</name>
  <files>voss/harness/permissions.py</files>
  <read_first>
    - voss/harness/permissions.py (lines 199-215 PermissionGate fields; lines 442-456 _prompt; lines 320-350 the auto-allow short-circuits that must NOT emit)
    - voss/harness/bos_decisions.py (build_verdict_record + append_decision — from BOS4-03)
    - .planning/phases/BOS4-decision-ledger-schema/BOS4-PATTERNS.md (lines 214-242, 435-436 — exact hook + which paths must not emit)
    - contracts/decision-ledger.schema.json (human_verdict required sub-keys)
  </read_first>
  <action>
    In voss/harness/permissions.py, import build_verdict_record, build_as_of,
    append_decision from voss.harness.bos_decisions.

    Add a `cwd: Path | None = None` field to the PermissionGate dataclass (the
    ledger needs a project root; gate has none today). Document it as the
    decision-ledger root; when None, emission is skipped (no path to write to).

    In _prompt, AFTER `choice = prompt(tool_name, args)` resolves and the verdict
    is determined, emit ONE decision record per human answer, BEFORE returning:
      - verdict mapping (D-R04): choice in {"a","A"} -> "approve"; else -> "dismiss"
      - actor_id: a stable local actor id (e.g. "operator" — no per-user identity
        source exists pre-BOS9; do NOT fabricate one)
      - feature_snapshot (D-R06): {"tool_name": tool_name,
        "is_mutating": <thread is_mutating through to _prompt or accept a
          feature_extras kwarg; if not readily available pass the value used by
          needs_prompt>, "mode": self.mode,
        "signature": self.signature(tool_name, args),
        "diff_summary": <short string if a diff was rendered, else "">}
        Do NOT dump raw `args` — capture ONLY the named fields to avoid leaking
        secrets/tokens from tool arguments (threat T-BOS4-05-01).
      - entity_ref: {} or {"session_id": <if available>} — no swarm/task context here
      - as_of: build_as_of(self.cwd / ".voss" / "bos" / "events.jsonl")
      - decision_id: a fresh unique id per prompt answer (e.g. uuid4 hex or
        f"dec-perm-{signature}-{_now_iso-ish}") — each human answer is a distinct
        decision, so do NOT collapse them; ensure uniqueness so none dedup away.
      - reason: short note, e.g. "permission prompt: <tool_name>"
      - rationale: prose describing the gate, e.g.
        f"permission gate verdict for {tool_name} in mode {self.mode}"
      - autonomy_band: "" (D-R03)
    Append via append_decision(self.cwd, record) ONLY when self.cwd is not None.
    Wrap the emit in a best-effort guard (catch OSError/ValueError) so a ledger
    write never breaks the permission decision itself.

    CRITICAL — do NOT emit from any path other than after a human answer:
      - the `prompt_fn is None and not sys.stdin.isatty()` non-interactive denial
        (returns before `choice =`) must NOT emit.
      - the _check_impl auto-allow returns ("auto", "remembered", rule "allow")
        never reach _prompt, so they already don't emit — leave them untouched.
    Add a comment marking this as inline human-verdict emission (D-R01/D-R04).
  </action>
  <verify>
    <automated>grep -n "build_verdict_record\|append_decision" voss/harness/permissions.py | grep -v '^#'</automated>
  </verify>
  <acceptance_criteria>
    - PermissionGate gains a cwd: Path | None field; emission is skipped when None
    - emit happens ONLY after `choice = prompt(...)` resolves (a human answered)
    - allow-once/allow-always -> approve; deny -> dismiss
    - feature_snapshot captures only named fields (no raw args dump)
    - emit best-effort guarded; permission verdict returns unchanged on ledger error
    - .venv/bin/python -c "import voss.harness.permissions" succeeds
  </acceptance_criteria>
  <done>Human-answered permission prompts emit a schema-valid verdict record; auto/non-interactive paths do not.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Test verdict emission and no-emit-on-auto</name>
  <files>tests/harness/test_bos_decision_permission_emit.py</files>
  <read_first>
    - tests/harness/test_bos_event_ledger.py (validator fixture + tmp_path ledger style)
    - voss/harness/permissions.py (PermissionGate with injected prompt_fn for tests; cwd field)
    - contracts/decision-ledger.schema.json
  </read_first>
  <behavior>
    - PermissionGate(mode="edit", cwd=tmp_path, prompt_fn=lambda t,a: "a") then
      gate.check(...) on a mutating tool -> exactly one record in
      tmp_path/.voss/bos/decisions.jsonl, human_verdict.verdict == "approve",
      schema-valid.
    - prompt_fn returning "n" (deny) -> one record, verdict == "dismiss".
    - Auto path: PermissionGate(mode="auto", cwd=tmp_path) check on a tool that
      auto-allows -> NO decisions.jsonl written (file absent or empty).
    - Remembered path: a signature already in store.always -> auto-allow -> NO emit.
    - Non-interactive denial (prompt_fn=None, no TTY) -> NO emit.
    - cwd=None -> NO emit even on a human answer (no ledger root).
    - Each record validates against contracts/decision-ledger.schema.json.
  </behavior>
  <action>
    Create tests/harness/test_bos_decision_permission_emit.py. Reuse the
    module-scope jsonschema validator fixture pointed at
    contracts/decision-ledger.schema.json. Drive PermissionGate.check with
    injected prompt_fn for the approve/deny cases, and with mode="auto" /
    pre-seeded store.always for the no-emit cases. Read back decisions.jsonl via
    voss.harness.bos_decisions.read_decisions(tmp_path) and assert counts +
    verdicts + schema validity. Assert the no-emit cases leave the ledger absent
    or empty.
  </action>
  <verify>
    <automated>.venv/bin/pytest tests/harness/test_bos_decision_permission_emit.py -x 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - tests/harness/test_bos_decision_permission_emit.py exits 0
    - Approve + dismiss verdicts both asserted and schema-valid
    - Auto / remembered / non-interactive / cwd=None cases assert NO record written
  </acceptance_criteria>
  <done>Verdict emission and the no-emit invariants are covered by a green schema-validating test.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| human prompt answer → decisions.jsonl | tool name, mode, signature, diff summary, operator verdict captured into the ledger |
| tool args → feature_snapshot | UNTRUSTED: tool args may contain secrets/tokens; only curated fields cross |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-BOS4-05-01 | Information Disclosure | secrets/tokens in raw tool `args` leaking into feature_snapshot | mitigate | feature_snapshot captures ONLY named fields (tool_name, is_mutating, mode, signature, diff_summary). Raw `args` dict is never serialized into the record. signature() already elides arg bodies for shell_run. |
| T-BOS4-05-02 | Repudiation | verdict recorded with no/forged actor | accept | No per-user identity source pre-BOS9; actor_id = "operator" placeholder, documented. Real actor identity is a BOS9+ concern. Not fabricated beyond the honest placeholder. |
| T-BOS4-05-03 | Denial of Service | ledger write error breaking a permission decision | mitigate | Emit wrapped in best-effort guard; verdict returns unchanged on ledger failure. |
| T-BOS4-05-04 | Tampering | spurious records from auto-allows polluting the human-decision signal | mitigate | Emit gated strictly to the post-`choice=prompt()` path; auto/remembered/rule-allow/non-interactive paths never emit (asserted in tests). |
| T-BOS4-05-05 | Information Disclosure | decisions.jsonl readable by other users | mitigate | File written via BOS4-03 BosDecisionLedger which chmods 0o600. |
| T-BOS4-05-SC | Tampering | new package installs | mitigate | None — reuses BOS4-03 module + existing permissions surface. No new dependency; no install task. |
</threat_model>

<verification>
- .venv/bin/pytest tests/harness/test_bos_decision_permission_emit.py exits 0
- .venv/bin/python -c "import voss.harness.permissions" succeeds
- Emitted records validate against contracts/decision-ledger.schema.json
- No regression: existing permissions tests still pass
  (.venv/bin/pytest tests/harness/ -k permission exits 0)
</verification>

<success_criteria>
- Human-answered prompts emit schema-valid verdict records inline (D-R01/D-R04)
- approve/dismiss mapping correct; override/do_nothing reserved
- auto-allow / remembered / non-interactive / cwd=None paths emit nothing
- feature_snapshot leaks no raw tool args; emission best-effort guarded
</success_criteria>

<output>
Create `.planning/phases/BOS4-decision-ledger-schema/BOS4-05-SUMMARY.md` when done.
</output>
