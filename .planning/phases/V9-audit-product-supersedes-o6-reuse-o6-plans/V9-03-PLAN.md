---
phase: V9-audit-product-supersedes-o6-reuse-o6-plans
plan: 03
type: execute
wave: 2
depends_on: ["V9-02"]
files_modified:
  - voss/harness/audit/report.py
autonomous: true
requirements: [VAUD-02, VAUD-03, VAUD-07, VAUD-10]

must_haves:
  truths:
    - "build_audit_report assembles all PRD §9 sections from persisted data, read-only, never writing"
    - "EM-authored claims (em.ticket/em.run_final/em.routing) are distinguished from verified evidence (review sidecars); unsupported EM claims are flagged"
    - "A missing source renders explicit 'none' (empty value + sections_missing entry), never a crash"
    - "Leak-6 is synthesized as an accepted-gap when no audit.leak6 marker and no standup-to-memory write path exists"
    - "report.py may import principles/team but never board/.em/.cli"
  artifacts:
    - path: "voss/harness/audit/report.py"
      provides: "build_audit_report aggregate + claims-vs-evidence tagging + residual-risk synthesis"
      contains: "def build_audit_report"
  key_links:
    - from: "voss/harness/audit/report.py"
      to: "voss.harness.audit.load.load_audit_snapshot / _load_review_sidecars / _load_run_final_file"
      via: "import + call"
      pattern: "load_audit_snapshot"
    - from: "voss/harness/audit/report.py"
      to: "voss.harness.principles.resolve_principles"
      via: "import inside report.py (allowed; forbidden in load.py)"
      pattern: "principles"
---

<objective>
Assemble the V9 `AuditReport` — the PRD §9 surface — from the persisted sources the loader now exposes. This wave owns: section assembly, claims-vs-evidence source tagging (VAUD-03), residual-risk + Leak-6 synthesis (VAUD-10), `sections_missing` tracking for graceful "none" rendering (VAUD-02), and surfacing `rejected_raises` scope denials + kill/rescope lineage (VAUD-07).

Purpose: `report.py` is the single read-only aggregator that the render layer and CLI consume. It is also the ONLY new audit module permitted to import `voss.harness.principles` and `voss.harness.team` (load.py is forbidden from doing so by TestNoLiveImports).
Output: New `voss/harness/audit/report.py` with `build_audit_report`. The Wave-0 `test_audit_report.py` RED tests turn GREEN.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-SPEC.md
@.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-PATTERNS.md
@.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-RESEARCH.md
@.planning/docs/ORCHESTRATION_LAYERS.md

<interfaces>
From V9-02 (now landed):
  voss/harness/audit/load.py:
    load_audit_snapshot(root: Path, run_id: str | None = None) -> AuditSnapshot
    _load_review_sidecars(run_dir: Path) -> dict[str, dict]
    _load_run_final_file(run_dir: Path) -> dict | None
  voss/harness/audit/model.py:
    AuditReport(run_id, idea, principles, team_config, snapshot, review_sidecars,
                run_final, signoff_ack, calibration, sections_missing, unsupported_claims=())
    CalibrationReport(...)   # an empty/zero instance is acceptable here; calibration wired by CLI in V9-04

Principles surface (voss/harness/principles.py — AUTHORITATIVE):
  resolve_principles(cwd: Path) -> tuple[tuple[str, str], ...]   # MERGED+RESOLVED view (line ~170) — USE THIS
  DEFAULT_PRINCIPLES: tuple[tuple[str, str], ...]                 # fallback on exception
  NOTE: load_principles(cwd) returns a _ProjectLayer (.items of (key, text|None)), NOT a resolved set.
        Do NOT use load_principles directly for the principles section — use resolve_principles.

Team surface (voss/harness/team.py — AUTHORITATIVE):
  compile_team(decl: TeamDecl) -> (TeamConfig, SubagentRegistry)
  TeamConfig.roster_ids: frozenset[str] ; TeamConfig.ceiling (TeamCeiling)
  Parsing a team file: see cli.py:4028-4044 (parse → next TeamDecl → compile_team).

Claims-vs-evidence rule (V9-RESEARCH §3):
  EM-authored claim = node transition kind in {"em.ticket","em.run_final","em.routing"}.
  Verified evidence = sidecar a_verification (A) + b_verdict (B) + evidence_refs.
  UNSUPPORTED = node has em.ticket AND (sidecar absent OR a_verification is null AND b_verdict is null).

Leak-6 rule (V9-RESEARCH §7, Open Q #5): synthesize accepted_gap when no audit.leak6 marker
  AND no standup→semantic.memory write path exists in V2-V7 (it does not). Do NOT inject a runtime transition.

Scope denials (VAUD-05): rejected_raises lives on the raw node JSON dicts
  (each entry {attempted_delta, reason, attempted_at}); reachable via snapshot.nodes' raw transitions
  or re-read of node JSONs. report.py must surface them.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create report.py — build_audit_report aggregate + sections_missing + scope-denial surfacing</name>
  <files>voss/harness/audit/report.py</files>
  <behavior>
    - build_audit_report(cwd) returns an AuditReport with idea (from run-final.json), principles (resolved or DEFAULT), team_config (dict; "default roster (not persisted)" marker when no team.voss), snapshot, review_sidecars, run_final, signoff_ack (from .signoff-ack.json or None), calibration (empty instance ok), sections_missing.
    - Missing run-final.json → idea == "" AND "goal" (or the section key) in sections_missing; no exception.
    - rejected_raises from node JSONs are surfaced (the report exposes scope denials with reasons).
    - Kill/rescope lineage + routing rationale reachable via snapshot (already in AuditSnapshot).
    - build_audit_report performs NO writes (read-only).
  </behavior>
  <read_first>
    - voss/harness/audit/load.py (post-V9-02: load_audit_snapshot signature, _load_review_sidecars, _load_run_final_file) — the data sources
    - voss/harness/audit/model.py (post-V9-02: AuditReport/CalibrationReport fields)
    - voss/harness/principles.py:25-32,160-170 (DEFAULT_PRINCIPLES, resolve_principles) — the AUTHORITATIVE principles surface
    - voss/harness/cli.py:4028-4044 (team file parse → compile_team) — team config loading pattern
    - voss/harness/board/cli_view.py (render_board assembly without live Board/EM — the read-only aggregator analog)
    - V9-PATTERNS.md "voss/harness/audit/report.py (new)" (module header, build_audit_report shape, graceful-missing, claims-vs-evidence excerpts lines 223-295)
    - tests/harness/audit/test_audit_report.py (Wave-0 RED tests this task must satisfy)
  </read_first>
  <action>
    Create `voss/harness/audit/report.py`. Module docstring states: read-only; no board/.em/.cli imports; principles/team imported HERE (not load.py) per TestNoLiveImports. `build_audit_report(cwd: Path, run_id: str | None = None, calibration: CalibrationReport | None = None) -> AuditReport`: call `load_audit_snapshot(cwd, run_id=run_id)`, derive `run_dir = cwd/".voss"/"sessions"/snapshot.root_id`, then `_load_run_final_file(run_dir)` and `_load_review_sidecars(run_dir)`. Add a module-level `_load_signoff_ack(run_dir)` that reads `.signoff-ack.json` (dict or None, graceful). Principles: `try: principles = resolve_principles(cwd); except Exception: principles = DEFAULT_PRINCIPLES` (import resolve_principles + DEFAULT_PRINCIPLES from voss.harness.principles INSIDE report.py). Team config: add `_load_team_config_dict(cwd)` that parses `.voss/team.voss` via `parse` + `compile_team` (guarded; on absence return a serializable dict marked `{"source": "default roster (not persisted)", "roster_ids": [...]}` reconstructed best-effort from node `role` fields per RESEARCH Open Q #4). Compute `sections_missing`: a tuple of PRD §9 section names whose source had no data (e.g. "goal" when run_final is None, "diff_summary" and "tests_evals" ALWAYS — those have no persisted source per SPEC, render explicit "none"). Surface `rejected_raises`: re-read or carry the raw node dicts so scope denials `{attempted_delta, reason, attempted_at}` are reachable — expose them on the report (e.g. a helper or a field the render layer reads; if AuditReport has no dedicated field, surface via `team_config`/a dict the render reads — prefer a small module-level helper `scope_denials(snapshot, run_dir)` that re-reads node JSONs for `rejected_raises`). Assemble and return the `AuditReport`. Never write.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py -x -k "not claims_vs_evidence and not residual_risk"</automated>
  </verify>
  <acceptance_criteria>
    - `build_audit_report(fixture_root)` returns an AuditReport with non-empty `principles`, an `idea`, populated `review_sidecars`, and a `sections_missing` containing "diff_summary" + "tests_evals".
    - Missing run-final.json → `report.idea == ""` and the goal section flagged in `sections_missing`; no exception.
    - Scope denials: a node with `rejected_raises` is surfaced with its `reason` (assert via the test that injects a rejected_raises node).
    - `grep -v '^#' voss/harness/audit/report.py | grep -c "voss.harness.board\|voss.harness.em\|voss.harness.cli"` returns 0.
    - Read-only: file mtimes under the sessions dir are unchanged after `build_audit_report` (the test asserts this, mirroring TestReadOnly).
  </acceptance_criteria>
  <done>report.py assembles the full AuditReport read-only; principles/team loaded here; sections_missing + scope denials surfaced; import-clean of board/em/cli.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Claims-vs-evidence tagging + Leak-6 accepted-gap synthesis</name>
  <files>voss/harness/audit/report.py</files>
  <behavior>
    - A node with an em.ticket transition but no matching .review.json sidecar is flagged in report.unsupported_claims.
    - A node with a sidecar carrying a_verification/b_verdict is NOT flagged unsupported.
    - The report exposes a Leak-6 assessment with status "accepted_gap" when no audit.leak6 marker is present and no standup→memory write path exists (synthesized in report.py, not injected at runtime).
  </behavior>
  <read_first>
    - voss/harness/audit/report.py (the build_audit_report from Task 1 — extend it)
    - voss/harness/audit/model.py (AuditReport.unsupported_claims field; Leak6Assessment in AuditSnapshot.leak6)
    - voss/harness/audit/load.py (_extract_leak6 fallback returns status="warning" when no marker — see Pitfall 6)
    - V9-RESEARCH.md §3 (claims-vs-evidence mechanical rule) + §7 (Leak-6 accepted gap, no standup-to-memory writer) + Pitfall 6 (warning vs accepted_gap)
    - tests/harness/audit/test_audit_report.py::test_claims_vs_evidence + ::test_residual_risk (the RED tests)
  </read_first>
  <action>
    Extend `build_audit_report` (Task 1). Claims-vs-evidence: iterate `snapshot.nodes`; for each non-root node whose transitions include an `em.ticket`, check the sidecar at `review_sidecars.get(node.id)`; mark UNSUPPORTED when the sidecar is absent/empty OR both `a_verification` is falsy AND `b_verdict` is falsy. Collect the unsupported node ids into a sorted tuple and pass it as `AuditReport.unsupported_claims`. Leak-6 synthesis (VAUD-10, accepted-gap): `snapshot.leak6` already carries the loader's assessment; when it is the fallback `status="warning"` (no `audit.leak6` marker found) AND the run has no standup→semantic.memory write path (true for all V2-V7 — this is the documented accepted gap), synthesize a corrected `Leak6Assessment(status="accepted_gap", evidence="no standup-to-memory writer in V2-V7 substrate", mitigation_present=False)` for the report's residual-risk surface. Do NOT mutate `snapshot` (frozen); compute the residual-risk value at report-assembly time and expose it (re-use `snapshot.leak6` when it is already `accepted_gap`, otherwise the synthesized one). Add a small `_residual_risk(snapshot)` helper returning the effective `Leak6Assessment`. Do NOT inject any transition into persisted data.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `node_killed_01` (em.ticket, no sidecar per V9-01) appears in `report.unsupported_claims`; `node_ab_block1` (has sidecar) does NOT.
    - The report's residual-risk Leak-6 assessment has `status == "accepted_gap"` even when the fixture has only the loader fallback (or has it explicitly) — synthesized, not injected.
    - `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py -x` exits 0 (full VAUD-02/03/04/05/06/07/10 coverage green).
    - No write to persisted data (read-only invariant preserved).
  </acceptance_criteria>
  <done>Unsupported EM claims flagged; Leak-6 accepted-gap synthesized read-only; test_audit_report.py fully green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| persisted JSON / team.voss / principles.yml → report assembler | Untrusted persisted artifacts cross into report.py |
| report.py → audited run data | report.py must remain strictly read-only (no writes to the audited run) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V9-03-01 | Denial of Service | malformed team.voss / principles.yml | mitigate | team/principles loads wrapped in try/except → default markers; absence → "default roster (not persisted)" / DEFAULT_PRINCIPLES; never crash |
| T-V9-03-02 | Tampering | report.py accidentally writing to the audited run | mitigate | build_audit_report performs zero writes; read-only invariant asserted by a mtime-unchanged test mirroring TestReadOnly |
| T-V9-03-03 | Repudiation | false "verified" status on an EM claim | mitigate | Claims-vs-evidence rule flags em.ticket-without-sidecar as unsupported; verification status derived only from review sidecars, not EM narrative |
| T-V9-03-SC | Tampering | npm/pip/cargo installs | accept | Zero new dependencies; stdlib + existing project modules only |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py -x` — VAUD-02/03/04/05/06/07/10 green.
- `.venv/bin/python -m pytest tests/harness/audit/ -x -k "not render and not cli and not calibration and not signoff"` — loader + report green, 37 baseline preserved.
- Import-clean grep gate (board/em/cli) returns 0 for report.py.
</verification>

<success_criteria>
- report.py assembles the full PRD §9 AuditReport read-only; principles via resolve_principles, team via compile_team, both imported in report.py only.
- Unsupported EM claims flagged; Leak-6 accepted-gap synthesized; scope denials + lineage surfaced.
- sections_missing drives "none" rendering for diff_summary/tests_evals (no persisted source).
- test_audit_report.py fully green; baseline preserved.
</success_criteria>

<output>
Create `.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-03-SUMMARY.md` when done.
</output>
