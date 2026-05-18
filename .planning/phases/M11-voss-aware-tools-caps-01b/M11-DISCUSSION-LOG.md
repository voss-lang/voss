# Phase M11: Voss-aware Tools (CAPS-01b) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-18
**Phase:** M11-voss-aware-tools-caps-01b
**Areas discussed:** SPEC gate, No-emit vs graph/trace fidelity, Deliverable scope & done-state, Inspector/tracer shapes, .voss→Python diff trigger & surface

---

## SPEC gate (pre-discussion)

| Option | Description | Selected |
|--------|-------------|----------|
| SPEC first, then discuss | Run /gsd:spec-phase M11, lock VTOOL reqs, re-discuss on locked SPEC (M10 precedent) | |
| Discuss now, no SPEC | Proceed on ROADMAP's 4 deliverables; VTOOL reqs stay fluid | ✓ |
| Discuss now, scope-narrow | Decide which deliverables ship now vs split before deep-dive | |

**User's choice:** Discuss now, no SPEC.
**Notes:** User then directed: auto-resolve all gray areas with Claude's recommended answers and write CONTEXT.md to move straight to plan-phase. Gray-area selection question was not answered interactively — resolved per that direction.

---

## No-emit vs graph/trace fidelity

| Option | Description | Selected |
|--------|-------------|----------|
| Scope to existing recorded data (best-effort, no true graph) | Honor no-new-emit; derive views from RunRecord | ✓ |
| Derive a graph from decision ordering | Infer edges heuristically | partial |
| Escalate to lift the constraint | Allow new emit points | |

**User's choice:** Recommended (auto). Scope to existing recorded data; derive a confidence-annotated decision *sequence* (not DAG) — `RunRecord.decisions` confirmed `{title,body,confidence}` only, no lineage field. Explicit ROADMAP-wording divergence noted (D-01).
**Notes:** Highest-risk decision. Constraint binding, not escalated.

---

## Deliverable scope & done-state

| Option | Description | Selected |
|--------|-------------|----------|
| Deliverable 1 = verify/expose only | SKL-06 already shipped (T7); consume frozen schema | ✓ |
| Deliverable 1 = extend to callable-from-.voss | Add .voss-skill exec path | |

**User's choice:** Recommended (auto). T7 SKL-06 lint skill done; M11 consumes the frozen schema unchanged, adds no `.voss`-exec path (T7 rejected it, registry locked). Deliverables 2/3/4 are thin wiring over existing M9 widgets, not greenfield (D-02).
**Notes:** M11 reframed as a wiring/exposure phase.

---

## Inspector/tracer shapes

| Option | Description | Selected |
|--------|-------------|----------|
| Probable inspector keyed by session + decision index | CLI + ConfidenceBar reuse | ✓ |
| Budget tracer per agent iteration | CLI + BudgetMeter reuse, only recorded frame unit | ✓ |
| Per-scope / per-tool budget frames | Requires new emit points | |

**User's choice:** Recommended (auto). D-04: inspector input `<session-id> [--decision N]`; tracer input `<session-id>`, frame = iteration; both reuse M9 widgets; new handler module (planner names, suggest `voss/harness/inspect.py`).

---

## .voss→Python diff trigger & surface

| Option | Description | Selected |
|--------|-------------|----------|
| On-demand CLI/slash | `voss vdiff <file.voss>`, no edit-path hook | ✓ |
| Auto on every agent .voss edit | Approaches new emit point, noisy | |

**User's choice:** Recommended (auto). D-05: on-demand only; pair `<name>.voss` ↔ `.voss-cache/harness/<name>.py` (or fresh `generate_python`); two-pane read-only view, no line source map; reuse DiffModal *pattern* via a read-only sibling; dogfood-capable on `voss/harness/agent/*.voss`.

---

## Claude's Discretion

- CLI flag design, table/tree/sparkline rendering format.
- New inspect handler module/file names.
- Whether TUI modals ship in M11 or CLI-only first (ROADMAP permits CLI-only).
- Fixture reuse strategy (recorded sessions + harness `.voss`, not new repos).
- Concrete derived-sequence algorithm within the D-01 no-edge constraint.
- Slash-name collision check for `/budget` (alternates `/probe`,`/btrace`,`/vdiff`).

## Deferred Ideas

- True probable-value propagation DAG (cross-value lineage edges) — needs new emit points.
- Per-`ctx(budget:)`-scope / per-tool-call budget frames — needs new emit points.
- Auto-on-every-edit `.voss`→Py diff.
- `.voss`-skill execution path / loader (T7-rejected, registry locked).
- `.voss`↔Python line-level source map.
- Editor-extension surfaces (EDIT track).
- Live-replay / time-travel debugger over recorded runs.
