---
phase: O5-engineering-manager-loop
plan: 01
type: tdd
wave: 1
depends_on:
  - O5-00
files_modified:
  - voss/harness/em/__init__.py
  - voss/harness/em/tickets.py
  - voss/harness/em/errors.py
  - voss/harness/session.py
  - tests/harness/em/__init__.py
  - tests/harness/em/test_em_tickets.py
  - tests/harness/em/test_em_lineage.py
  - tests/harness/em/test_em_exit_reasons.py
autonomous: true
requirements:
  - OEM-01
  - OEM-07
  - OEM-10
must_haves:
  truths:
    - "voss/harness/em/ exists as a subpackage with __init__.py re-exporting the public surface"
    - "Ticket / KillRecord / RescopeRecord / RoutingRationale / RunFinal are frozen-slots dataclasses"
    - "Every EM-emitted audit record carries a `kind: Literal[\"em.*\"]` discriminator and never `board.*`"
    - "RescopeRecord links predecessor↔successor bidirectionally; kill-then-rescope reads either direction"
    - "EXIT_REASONS gains 'killed' (additive only) and continues to pass tests/harness/test_session_redaction.py"
    - "EMCageViolation is a typed exception with .op and .reason structured attributes"
    - "Tests fail RED before tickets.py exists, then GREEN after the dataclasses land"
    - "Audit copy never contains the L2-vocab strings 'model'/'cost'/'token'/'provider' (L-03 landmine)"
  artifacts:
    - path: "voss/harness/em/tickets.py"
      provides: "Ticket, KillRecord, RescopeRecord, RoutingRationale, RunFinal frozen dataclasses"
      contains: "@dataclass(frozen=True, slots=True)"
    - path: "voss/harness/em/errors.py"
      provides: "EMCageViolation typed exception"
      contains: "class EMCageViolation"
    - path: "voss/harness/em/__init__.py"
      provides: "Public surface re-export"
      contains: "__all__"
    - path: "voss/harness/session.py"
      provides: "EXIT_REASONS additively extended with 'killed'"
      contains: "\"killed\""
    - path: "tests/harness/em/test_em_tickets.py"
      provides: "TDD coverage for Ticket / RoutingRationale frozen invariants"
    - path: "tests/harness/em/test_em_lineage.py"
      provides: "TDD coverage for KillRecord / RescopeRecord lineage invariants"
    - path: "tests/harness/em/test_em_exit_reasons.py"
      provides: "TDD coverage for EXIT_REASONS additive extension"
  key_links:
    - from: "voss/harness/em/__init__.py"
      to: "voss/harness/em/tickets.py"
      via: "re-export"
      pattern: "from \\.tickets import"
    - from: "voss/harness/em/tickets.py"
      to: "voss/harness/session.py"
      via: "EXIT_REASONS membership (KillRecord rationale ↔ exit_reason='killed')"
      pattern: "EXIT_REASONS"
---

<objective>
Land the EM data model: frozen-slots dataclasses for Ticket / KillRecord /
RescopeRecord / RoutingRationale / RunFinal in `voss/harness/em/tickets.py`,
the typed EMCageViolation in `voss/harness/em/errors.py`, the package skeleton
`voss/harness/em/__init__.py`, and the additive `"killed"` extension to
`voss/harness/session.EXIT_REASONS` for kill-flow termination.

This is the foundational data wave. Every later wave (W2 facade, W3 LLM, W4
loop, W5 integration) imports these dataclasses. No board mocks, no LLM, no
asyncio — pure data + one frozenset extension.

Purpose: Lock the audit-record vocabulary O6 will read. The `kind="em.*"`
discriminator separates EM-emitted records from O3's `board.*` records; the
bidirectional KillRecord↔RescopeRecord pointers let O6 walk lineage in O(1);
the `"killed"` EXIT_REASONS extension matches O3's `"timeout"` playbook
(both additive, both land in session.py).

Output: One new subpackage, 5 frozen value-objects, 1 typed exception, 1
additive frozenset member, 3 RED→GREEN test files.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/O5-engineering-manager-loop/O5-CONTEXT.md
@.planning/phases/O5-engineering-manager-loop/O5-RESEARCH.md
@.planning/phases/O5-engineering-manager-loop/O5-PATTERNS.md
@.planning/phases/O5-engineering-manager-loop/O5-00-SUMMARY.md
@voss/harness/team.py
@voss/harness/session.py
@voss/harness/session_tree.py
@voss/eval/judge.py

<interfaces>
<!-- Patterns to copy verbatim -->

From voss/harness/team.py lines 187-218 (frozen-slots cluster — canonical analog):
```
@dataclass(frozen=True, slots=True)
class TeamCeiling:
    budget_tokens: int | None
    scope: TeamRoleScope | None
    latency_seconds: int | None
```

From voss/harness/session.py lines 74-76 (EXIT_REASONS frozenset):
```
EXIT_REASONS: frozenset[str] = frozenset(
    {"done", "max-iter", "budget", "interrupt", "batch-invariant"}
)
```

From voss/harness/session.py lines 141-146 (one-invariant __post_init__):
```
def __post_init__(self) -> None:
    if self.exit_reason is not None and self.exit_reason not in EXIT_REASONS:
        raise ValueError(...)
```

From voss/harness/session_tree.py lines 34-44 (typed exception with structured attrs):
```
class BudgetCapRaiseError(Exception):
    def __init__(self, node_id, attempted_delta, reason) -> None:
        self.node_id = node_id
        self.attempted_delta = attempted_delta
        self.reason = reason
        super().__init__(f"cap raise rejected for node {node_id}: ...")
```

From voss/harness/skill/__init__.py: sub-package init shape — a single
docstring + zero/minimal re-exports until the public surface is finalized.
</interfaces>

<behavior_locks>
<!-- L-01..L-05 landmines from O5-00-SUMMARY (PATTERNS.md): -->

L-02 (kind discriminator): every EM record's `kind` field MUST be one of
  {"em.ticket","em.routing","em.kill","em.rescope","em.run_final"}.
  Test rejects `kind="board.*"`.
L-03 (no L2 vocab): tests scan every string field on every record and FAIL
  if any literal field value contains "model", "cost", "token", "provider".
  Internal variable names are fine — this is about audit copy the human reads.
L-04 (append-not-delete): KillRecord and RescopeRecord are pure records —
  they do NOT delete or mutate the predecessor in-place; tests assert this by
  constructing both, asserting the predecessor record still exists and is
  equal to its pre-kill snapshot.
</behavior_locks>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: RED — frozen-record + EXIT_REASONS test scaffolds</name>
  <files>tests/harness/em/__init__.py, tests/harness/em/test_em_tickets.py, tests/harness/em/test_em_lineage.py, tests/harness/em/test_em_exit_reasons.py</files>
  <read_first>
    - tests/harness/test_session_tree.py (frozen-record + tmp_path + pytest.raises patterns)
    - tests/harness/test_session_redaction.py (redaction-invariant pattern that the EXIT_REASONS extension must continue to pass)
    - voss/harness/team.py lines 187-220 (frozen-slots cluster shape)
    - voss/harness/session.py lines 70-150 (EXIT_REASONS + RunRecord __post_init__)
    - .planning/phases/O5-engineering-manager-loop/O5-RESEARCH.md §Q2, §Q3, §Q4 (record shapes)
    - .planning/phases/O5-engineering-manager-loop/O5-PATTERNS.md §"voss/harness/em/tickets.py"
  </read_first>
  <behavior>
    - Ticket has fields: id, card_node_id, original_idea, acceptance, dod,
      worker_role, routing_rationale_id, lineage_parent_id (Optional[str]),
      domain (Literal["code","ai"] default "code"), risk_tier
      (Literal["low","med","high"] default "med"), created_at, kind
      (Literal["em.ticket"] default "em.ticket"). Frozen+slots. Equality
      reflects all fields.
    - Mutating any Ticket field via attribute assignment raises FrozenInstanceError.
    - RoutingRationale: id, card_id, chosen_role, candidates_considered
      (tuple[str,...]), rationale_text, confidence_hint (Optional[float] in
      [0,1] or None), ts, kind (Literal["em.routing"] default "em.routing").
      __post_init__ raises ValueError if confidence_hint is set and outside [0,1].
    - KillRecord: killed_node_id, lineage_parent_id (Optional[str]),
      rationale_text, evidence_refs (tuple[str,...]), killed_at,
      successor_card_id (Optional[str]), kind (Literal["em.kill"] default
      "em.kill"). __post_init__ raises ValueError if lineage_parent_id ==
      killed_node_id (no self-parented kills).
    - RescopeRecord: predecessor_card_id, successor_card_id, diff_summary,
      rationale_text, new_acceptance (tuple[str,...]),
      new_dod (tuple[str,...]), rescoped_at, kind (Literal["em.rescope"]
      default "em.rescope"). __post_init__ raises ValueError if
      predecessor_card_id == successor_card_id.
    - RunFinal: root_id, idea, total_cards, done_count, blocked_count,
      killed_count, rescope_count, em_iterations, ts, kind
      (Literal["em.run_final"] default "em.run_final"). Counts are
      non-negative ints; __post_init__ enforces.
    - L-02: every record's `kind` is in {"em.ticket","em.routing","em.kill",
      "em.rescope","em.run_final"}; constructing with kind="board.transition"
      is a static-typing failure (Literal violation) AND a runtime
      ValueError if forcibly bypassed (the test uses `dataclasses.replace`
      with an invalid Literal expecting Literal to enforce at runtime via a
      __post_init__ assert on each record).
    - L-03: tests build one of each record with realistic copy and scan every
      str field value for the substrings ["model","cost","token","provider"]
      (case-insensitive); assertion fails the test if found.
    - L-04: building a KillRecord referencing card X plus a RescopeRecord
      successor referencing X leaves the original Ticket value unchanged
      (test snapshots via dataclasses.replace + equality).
    - EXIT_REASONS test: "killed" is a member; "budget", "done", "interrupt"
      remain members; the frozenset is still a frozenset; constructing a
      RunRecord with exit_reason="killed" no longer raises ValueError.
    - EMCageViolation(op="dispatch", reason="unknown role 'phantom'") has
      .op == "dispatch", .reason == "unknown role 'phantom'", and the
      formatted str(exc) contains both substrings.
  </behavior>
  <action>
    Write the four test files RED — they will fail until Task 2 lands the
    implementation. Use pytest 7.x style (asyncio_mode=auto is already
    configured; these tests are sync so the marker is irrelevant).

    File 1: `tests/harness/em/__init__.py` — empty, so pytest picks up the
    package.

    File 2: `tests/harness/em/test_em_tickets.py` — covers Ticket and
    RoutingRationale construction, frozen-mutation refusal, L-02 kind check,
    L-03 L2-vocab scan, confidence_hint range guard. Imports the future
    `voss.harness.em.tickets`; the import is expected to fail at collection
    time today.

    File 3: `tests/harness/em/test_em_lineage.py` — covers KillRecord,
    RescopeRecord, RunFinal construction; bidirectional pointer test (build
    a KillRecord with successor_card_id=Y and a RescopeRecord with
    predecessor_card_id=X, assert both pointers); L-04 append-not-delete
    (original Ticket value unchanged after building kill/rescope records);
    counts-non-negative guard.

    File 4: `tests/harness/em/test_em_exit_reasons.py` — covers EXIT_REASONS
    extension; uses `from voss.harness.session import EXIT_REASONS,
    RunRecord`; asserts "killed" ∈ EXIT_REASONS and the existing five
    members remain; constructs RunRecord(..., exit_reason="killed") and
    asserts no ValueError.

    Run the RED tests via the .venv interpreter and confirm they fail with
    ImportError / ModuleNotFoundError on voss.harness.em.tickets, and one
    ValueError-or-AssertionError on the EXIT_REASONS test.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; .venv/bin/python -m pytest tests/harness/em/ -x -q --tb=short 2>&amp;1 | tee /tmp/o5-01-red.log; grep -qE "(ModuleNotFoundError|ImportError|AssertionError)" /tmp/o5-01-red.log &amp;&amp; echo EM_DATAMODEL_RED_OK</automated>
  </verify>
  <acceptance_criteria>
    - 3 new test files exist under tests/harness/em/.
    - pytest collects the tests but every test fails with ImportError or AssertionError (RED).
    - Existing tests/harness/test_session_redaction.py is NOT modified.
  </acceptance_criteria>
  <done>RED tests committed; pytest collection succeeds; every new test fails.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: GREEN — implement em/ subpackage + EXIT_REASONS extension</name>
  <files>voss/harness/em/__init__.py, voss/harness/em/tickets.py, voss/harness/em/errors.py, voss/harness/session.py</files>
  <read_first>
    - voss/harness/team.py lines 1-30 (imports header style)
    - voss/harness/team.py lines 187-218 (frozen-slots cluster)
    - voss/harness/session.py lines 70-150 (EXIT_REASONS frozenset + RunRecord __post_init__)
    - voss/harness/session_tree.py lines 30-44 (BudgetCapRaiseError shape)
    - voss/harness/skill/__init__.py (sub-package docstring header)
    - tests/harness/em/test_em_tickets.py (the contract — Task 1 output)
    - tests/harness/em/test_em_lineage.py (the contract — Task 1 output)
    - tests/harness/em/test_em_exit_reasons.py (the contract — Task 1 output)
  </read_first>
  <behavior>
    The implementation MUST make every RED test from Task 1 pass without
    modifying any test file. The shape is fully specified by the test file
    contracts; the implementation only fills in the dataclasses and the
    frozenset extension.

    Key invariants to enforce:
    - `@dataclass(frozen=True, slots=True)` on every record.
    - `from __future__ import annotations` at the top of every new module.
    - tickets.py imports ONLY from typing, dataclasses, and (optionally)
      voss.harness.session.EXIT_REASONS when needed for cross-check. Zero
      transitive harness imports — mirrors O3 verdict.py's "typing +
      dataclasses only" discipline (PATTERNS §rationale).
    - errors.py: `class EMCageViolation(Exception)` with structured
      `.op` and `.reason` attributes (mirrors BudgetCapRaiseError).
    - `kind` fields use `Literal[...]` so static typing rejects "board.*".
      Runtime __post_init__ adds a defensive `assert self.kind == "em.ticket"`
      (etc.) — defense in depth.
    - __post_init__ validations are one-liners each (mirror RunRecord
      pattern); no monolithic validator.
    - __init__.py re-exports the public surface:
        from .tickets import Ticket, KillRecord, RescopeRecord, RoutingRationale, RunFinal
        from .errors import EMCageViolation
        __all__ = ["Ticket","KillRecord","RescopeRecord","RoutingRationale",
                   "RunFinal","EMCageViolation"]
    - session.py modification: extend EXIT_REASONS additively to include
      "killed". Surrounding comment explains the additive playbook (mirror
      the T1-01 / T2-03 comments above the frozenset). No other change to
      session.py.

    Constraints (negative):
    - Do NOT touch tests/harness/test_session_redaction.py — it must still
      pass without modification (proves the extension is truly additive).
    - Do NOT import anything from voss.harness.board.* — that subpackage is
      not yet shipped (W0 confirmed).
    - Do NOT add any L2 vocab ("model"/"cost"/"token"/"provider") to
      docstrings or default values for human-visible fields.
  </behavior>
  <action>
    Implement four files plus one targeted edit:

    1. `voss/harness/em/__init__.py` — Module docstring + re-exports + __all__.

    2. `voss/harness/em/tickets.py` — The 5 frozen dataclasses
       (Ticket / KillRecord / RescopeRecord / RoutingRationale / RunFinal)
       with their __post_init__ validators per the Task 1 behavior contract.
       Use `dataclasses.field(default_factory=tuple)` for empty tuple
       defaults. Domain / WorkerRole type aliases at module top.

    3. `voss/harness/em/errors.py` — EMCageViolation with structured .op
       and .reason attributes; super().__init__ formats the message.

    4. `voss/harness/session.py` — Edit the EXIT_REASONS frozenset to
       additively include "killed". Add a short inline comment explaining
       the O5 OEM-10 extension (same playbook the T1-01 / T2-03 comments
       use above the frozenset). Do not touch any other line.

    Run pytest again; the RED tests from Task 1 should all flip to GREEN.

    Run the full redaction test to confirm the extension is non-breaking:
      .venv/bin/python -m pytest tests/harness/test_session_redaction.py -x -q
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; .venv/bin/python -m pytest tests/harness/em/ tests/harness/test_session_redaction.py -x -q --tb=short &amp;&amp; .venv/bin/python -c "from voss.harness.em import Ticket, KillRecord, RescopeRecord, RoutingRationale, RunFinal, EMCageViolation; from voss.harness.session import EXIT_REASONS; assert 'killed' in EXIT_REASONS; print('green')" &amp;&amp; echo EM_DATAMODEL_OK</automated>
  </verify>
  <acceptance_criteria>
    - All Task 1 RED tests now pass GREEN.
    - tests/harness/test_session_redaction.py still passes (EXIT_REASONS extension is additive).
    - `from voss.harness.em import Ticket, KillRecord, RescopeRecord, RoutingRationale, RunFinal, EMCageViolation` succeeds.
    - `"killed" in EXIT_REASONS` is True; `"budget"`, `"done"`, `"interrupt"`, `"max-iter"`, `"batch-invariant"` are still members (no member removed).
    - All five records have `__dataclass_params__.frozen == True` and `slots=True`.
    - Every record's `kind` default starts with `"em."`.
    - Grep over voss/harness/em/ shows zero occurrences (case-insensitive) of "model", "cost", "token", "provider" outside comments / variable names that are not user-visible field default values.
  </acceptance_criteria>
  <done>All tests GREEN; EXIT_REASONS extended additively; em/ subpackage shipped with the five frozen records + EMCageViolation; commit message references OEM-01, OEM-07, OEM-10.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| EM-emitted record ↔ disk (via O1 _write_node_file) | Record kind/text becomes auditable evidence; tampering would corrupt the audit. |
| Audit copy ↔ human reader (O6 surface) | Record text strings are read by humans at sign-off; L2-vocab leak would confuse the audit. |
| EXIT_REASONS frozenset ↔ RunRecord __post_init__ | Adding "killed" without breaking redaction invariant is a security-additive change. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O5-01 | Tampering | KillRecord/RescopeRecord mutated after emit | mitigate | `frozen=True, slots=True` on every record; tests assert FrozenInstanceError on attribute set. |
| T-O5-02 | Spoofing | EM record claims `kind="board.*"` to spoof O3 audit | mitigate | `kind: Literal["em.*"]` plus runtime __post_init__ assert; static-typing + runtime defense in depth. |
| T-O5-04 | Tampering | Self-parented kill (record claims it killed itself) | mitigate | KillRecord __post_init__ rejects `lineage_parent_id == killed_node_id`. |
| T-O5-04 | Tampering | Rescope cycle (predecessor == successor) | mitigate | RescopeRecord __post_init__ rejects `predecessor_card_id == successor_card_id`. |
| T-O5-06 | Tampering | EXIT_REASONS extension breaks redaction invariant | mitigate | `test_session_redaction.py` must still pass with no modification; verify in Task 2. |
| T-O5-03 | Information disclosure | Audit copy leaks L2 vocab (model/cost/token/provider) | mitigate | Test scans every str field of every constructed record for the substrings; FAIL on hit. |
</threat_model>

<verification>
.venv/bin/python -m pytest tests/harness/em/ tests/harness/test_session_redaction.py -x -q && .venv/bin/python -c "from voss.harness.em import Ticket, KillRecord, RescopeRecord, RoutingRationale, RunFinal, EMCageViolation; from voss.harness.session import EXIT_REASONS; assert 'killed' in EXIT_REASONS; assert {'budget','done','interrupt','max-iter','batch-invariant'} <= EXIT_REASONS" && grep -RIvE '^\s*#|\bem\.(ticket|routing|kill|rescope|run_final)\b' voss/harness/em/ | grep -viE '\b(model|cost|token|provider)\b' >/dev/null; test $? -eq 0 || true && echo EM_DATAMODEL_OK
</verification>

<success_criteria>
- voss/harness/em/ subpackage exists with __init__.py, tickets.py, errors.py.
- 5 frozen-slots dataclasses + 1 typed exception ship.
- EXIT_REASONS additively gains "killed"; no member removed.
- tests/harness/em/ has 3 new test files; all tests green.
- tests/harness/test_session_redaction.py still passes.
- No L2 vocab in audit copy.
- Closes with the unique tag EM_DATAMODEL_OK.
</success_criteria>

<output>
Create `.planning/phases/O5-engineering-manager-loop/O5-01-SUMMARY.md` when done.
</output>
