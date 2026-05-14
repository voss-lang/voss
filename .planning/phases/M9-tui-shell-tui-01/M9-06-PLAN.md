---
phase: M9
plan: 06
type: execute
wave: 6
depends_on: [M9-05]
files_modified:
  - voss/harness/session.py
  - voss/harness/tui/fork.py
  - voss/harness/tui/widgets/fork_modal.py
  - voss/harness/tui/widgets/__init__.py
  - voss/harness/tui/app.py
  - tests/harness/tui/test_session_fork.py
  - tests/harness/tui/test_session_backward_compat.py
autonomous: true
requirements: [TUI-08]
must_haves:
  truths:
    - "voss resume <id> on a pre-M9 session JSON file loads without crashing (no new required fields, additive only)."
    - "Pressing `f` on a focused turn opens ForkConfirmModal; on Enter, a new SessionRecord is written with parent_id and parent_turn_index fields set."
    - "Forking does NOT modify or delete the original session record."
    - "The fork_session function is pure data: no UI imports; the modal is the only UI surface."
  artifacts:
    - path: "voss/harness/session.py"
      provides: "SessionRecord gains optional parent_id and parent_turn_index fields (additive, backward compatible)"
    - path: "voss/harness/tui/fork.py"
      provides: "fork_session(record, turn_index, cwd) -> SessionRecord; pure function, no UI"
      exports: ["fork_session"]
    - path: "voss/harness/tui/widgets/fork_modal.py"
      provides: "ForkConfirmModal — Enter to fork, Esc to cancel; locked copy"
      exports: ["ForkConfirmModal"]
  key_links:
    - from: "voss/harness/tui/widgets/fork_modal.py"
      to: "voss/harness/tui/fork.py:fork_session"
      via: "ForkConfirmModal posts ForkConfirmed; app handler calls fork_session() and shows resume flash"
      pattern: "fork_session"
    - from: "voss/harness/tui/fork.py"
      to: "voss/harness/session.py:SessionRecord"
      via: "fork_session creates a SessionRecord with parent_id + parent_turn_index set"
      pattern: "SessionRecord\\("
    - from: "voss/harness/tui/app.py"
      to: "voss/harness/tui/widgets/fork_modal.py"
      via: "VossTUIApp.action_fork_turn pushes ForkConfirmModal and on confirmation calls fork_session"
      pattern: "action_fork_turn"
---

<objective>
Add fork-from-turn UX backed by additive SessionRecord fields that preserve backward compat with pre-M9 session JSON files. This plan is the data-model + modal half of the original M9-06; the cli.py default-path flip + Windows-console strategy + accent allow-list + --no-unicode audits + phase-final human-verify checkpoint are now in M9-07 (checker B1 split).

Purpose: TUI-08 (fork + resume backward-compat session schema). Subsequent plan M9-07 wires this into cli.py and flips the default renderer path.

Output: additive session fields, fork_session pure function, ForkConfirmModal, VossTUIApp action handler, backward-compat tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md
@.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md
@voss/harness/session.py

<interfaces>
<!-- SessionRecord today (voss/harness/session.py lines 84-107): -->
```python
@dataclass
class SessionRecord:
    id: str
    name: str
    cwd: str
    model: str
    started_at: str
    updated_at: str
    total_cost_usd: float = 0.0
    turns: list[dict] = field(default_factory=list)
    runs: list[dict] = field(default_factory=list)
```

<!-- Backward-compat rehydrator (lines 116-123): -->
```python
_SESSION_FIELDS = {f.name for f in dataclasses.fields(SessionRecord)}
def _hydrate(data: dict) -> SessionRecord:
    kept = {k: v for k, v in data.items() if k in _SESSION_FIELDS}
    kept.setdefault("turns", [])
    kept.setdefault("runs", [])
    return SessionRecord(**kept)
```

<!-- _hydrate ALREADY drops unknown keys, so adding new fields is safe in BOTH directions:
     - Old reader + new file: new keys dropped (fine; old reader didn't need them).
     - New reader + old file: missing fields take their default values (fine).
-->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: SessionRecord additive fields + fork_session pure function + ForkConfirmModal + VossTUIApp action_fork_turn handler + backward-compat tests</name>
  <files>voss/harness/session.py, voss/harness/tui/fork.py, voss/harness/tui/widgets/fork_modal.py, voss/harness/tui/widgets/__init__.py, voss/harness/tui/app.py, tests/harness/tui/test_session_fork.py, tests/harness/tui/test_session_backward_compat.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/session.py (full file; confirm _hydrate behavior; confirm save() uses dataclasses.asdict; new fields auto-roundtrip)
    - /Users/benjaminmarks/Projects/Voss/tests/harness/test_session.py + test_session_redaction.py (existing test patterns + redaction invariants; new fields must NOT carry credentials — parent_id is a UUID-shaped string, parent_turn_index is an int)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md (Copywriting: Fork-from-turn confirmation modal heading + body + buttons verbatim; Session resume opens flash copy)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md (Fork-from-turn data model is at planner's discretion; this plan picks "new session row with parent_id pointer", NOT a tree of children in a single file — keeps `voss sessions` listing flat)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/app.py (M9-02..05 — extend with action_fork_turn handler; KEYMAP already has the `f` binding from M9-03)
  </read_first>
  <behavior>
    - Test (test_session_backward_compat): write a SessionRecord WITHOUT parent_id (pre-M9 shape), load it, assert `record.parent_id is None` (default) and no crash.
    - Test: write a new SessionRecord WITH parent_id="abc...", round-trip through save/load, assert parent_id and parent_turn_index survive intact.
    - Test: parent_id and parent_turn_index appear in `_SESSION_FIELDS` AFTER the schema change.
    - Test (test_session_redaction.py expansion): an explicit assertion that parent_id is a hex-shaped string and parent_turn_index is a non-negative int — both fail-closed under the existing redaction invariant test.
    - Test (test_session_fork): `fork_session(record=R, turn_index=3, cwd=tmp)` returns a new SessionRecord with `parent_id == R.id`, `parent_turn_index == 3`, `turns == R.turns[:3+1]`, `runs == []` (fresh run list).
    - Test: fork_session does NOT modify or delete the original record; original file on disk unchanged.
    - Test: fork_session(turn_index out of range) raises ValueError.
    - Test (ForkConfirmModal): heading exactly `Fork session from turn 3?`; body exactly per UI-SPEC `Creates a new session starting from this turn. The current session keeps its history.`; Enter posts ForkConfirmed; Esc posts ForkCancelled.
    - Test (action_fork_turn): VossTUIApp with a loaded SessionRecord, focus the TurnView with turn index 2, dispatch `action_fork_turn`, simulate Enter on ForkConfirmModal, assert a new SessionRecord exists at the expected path AND the original is unchanged AND the StatusLine flashes the UI-SPEC `Resumed {new_id} · {n} turns` copy.
  </behavior>
  <action>
    Edit `voss/harness/session.py`:
      - Add to SessionRecord: `parent_id: Optional[str] = None` and `parent_turn_index: Optional[int] = None`.
      - `_SESSION_FIELDS` auto-updates because it iterates fields().
      - Update the module docstring's "Redaction guarantee" paragraph to note the two new fields and confirm neither can carry credentials.

    Create `voss/harness/tui/fork.py`:
      ```python
      from pathlib import Path
      from voss.harness.session import SessionRecord, save
      from voss_runtime import EpisodicMemory
      from datetime import datetime, timezone
      import uuid

      def fork_session(record: SessionRecord, turn_index: int, cwd: Path) -> SessionRecord:
          """Create a new SessionRecord seeded from record's first turn_index+1 turns.

          Original record is NEVER modified. Returns the persisted new record.
          """
          if turn_index < 0 or turn_index >= len(record.turns):
              raise ValueError(f"turn_index {turn_index} out of range for {len(record.turns)} turns")
          new = SessionRecord(
              id=uuid.uuid4().hex[:12],
              name=f"fork-of-{record.id[:8]}-t{turn_index}",
              cwd=record.cwd,
              model=record.model,
              started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
              updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
              total_cost_usd=0.0,
              turns=list(record.turns[: turn_index + 1]),
              runs=[],
              parent_id=record.id,
              parent_turn_index=turn_index,
          )
          history = EpisodicMemory(capacity=40)
          for t in new.turns:
              history.add(t.get("content", ""), role=t.get("role", "user"))
          save(new, history)
          return new
      ```

    Create `voss/harness/tui/widgets/fork_modal.py`:
      - `ForkConfirmModal(turn_n: int)` renders heading + body + footer per UI-SPEC verbatim. BINDINGS `[("enter","confirm"),("escape","cancel")]`. Posts `ForkConfirmed(turn_n)` or `ForkCancelled`.
      - Re-export from `voss/harness/tui/widgets/__init__.py`.

    Wire app handler in `voss/harness/tui/app.py`: bind `f` action from KEYMAP (M9-03) to `action_fork_turn` which reads the focused turn index from TurnView, pushes ForkConfirmModal, on confirm calls `fork_session(self.record, idx, Path(self.record.cwd))`, then flashes the StatusLine with `Resumed {new_id} · {n} turns` per UI-SPEC.

    Tests: 9 tests across two files (5 in test_session_fork.py covering fork_session + ForkConfirmModal + action_fork_turn integration, 4 in test_session_backward_compat.py covering pre-M9 file roundtrip + redaction invariants).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/tui/test_session_fork.py tests/harness/tui/test_session_backward_compat.py tests/harness/test_session.py tests/harness/test_session_redaction.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from dataclasses import fields; from voss.harness.session import SessionRecord; names = {f.name for f in fields(SessionRecord)}; assert 'parent_id' in names and 'parent_turn_index' in names"` exits 0.
    - `python -c "from voss.harness.tui.fork import fork_session; print('ok')"` exits 0.
    - `python -c "from voss.harness.tui.widgets import ForkConfirmModal; print('ok')"` exits 0.
    - `grep -c "Fork session from turn " voss/harness/tui/widgets/fork_modal.py` returns >= 1.
    - `pytest tests/harness/test_session.py tests/harness/test_session_redaction.py -x -q` green (no regression).
    - All new fork tests pass.
  </acceptance_criteria>
  <done>parent_id + parent_turn_index added as additive optional fields; old session files load without crash; new fork_session pure function + ForkConfirmModal + action_fork_turn ship; redaction invariant extended over both new fields. cli.py wiring + default-path flip is M9-07.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pre-M9 session JSON → new reader | malicious additional keys could attempt to set unexpected SessionRecord fields. |
| user terminal → fork_session | turn_index must be bounded. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M9-06-01 | Tampering | Crafted session JSON with extra keys to set credential-shaped fields | mitigate | `_hydrate` (session.py line 119) already filters to `_SESSION_FIELDS`. Adding parent_id/parent_turn_index does not add credential-shaped fields. Redaction test extended to cover both. |
| T-M9-06-02 | DoS | fork_session with turn_index >= len(turns) | mitigate | fork_session raises ValueError; ForkConfirmModal disables Enter when turn_index is out of range. |
| T-M9-06-03 | Information disclosure | Forked sessions inherit cwd; running fork from outside the cwd | accept | fork_session preserves record.cwd; same property as resume. No new exposure. |
</threat_model>

<verification>
- 9 tests across 2 files green.
- pre-M9 session JSON files roundtrip via new reader without loss.
- SessionRecord new fields are additive Optional[...] with None defaults.
</verification>

<success_criteria>
1. SessionRecord has `parent_id` and `parent_turn_index` as additive Optional fields with None defaults.
2. Pre-M9 session JSON files load without crash and yield records with `parent_id is None`.
3. `fork_session(record, turn_index, cwd)` returns a new SessionRecord with parent fields set; original record unchanged on disk.
4. ForkConfirmModal renders UI-SPEC-locked copy; Enter/Esc bindings work.
5. VossTUIApp.action_fork_turn drives the modal → fork_session → status flash flow.
</success_criteria>

<output>
After completion, create `.planning/phases/M9-tui-shell-tui-01/M9-06-SUMMARY.md`.
</output>
</content>
</invoke>