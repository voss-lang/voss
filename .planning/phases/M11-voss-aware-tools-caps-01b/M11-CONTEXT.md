# Phase M11: Voss-aware Tools (CAPS-01b) - Context

**Gathered:** 2026-05-18
**Status:** Ready for planning
**Source:** `/gsd-discuss-phase M11`. User declined a pre-discuss SPEC ("Discuss now, no SPEC") and directed Claude to lock all gray areas with recommended answers (auto-resolve). No `M11-SPEC.md` exists — see "No SPEC — Requirements Posture" below.

<domain>
## Phase Boundary

M11 exposes 4 Voss runtime primitives as **visible, read-only product surfaces** — the "unfair advantage" axis (`notes/voss-agent-unfair-advantage.md`): every feature exposes a runtime primitive the user can inspect, never instruments new ones.

Fixed boundary (ROADMAP §"Phase M11", lines ~521-545 — authoritative since no SPEC):
1. **`.voss` lint-as-skill** — already shipped as T7 SKL-06; M11 = consume + expose + integration-test only.
2. **Probable-value inspector** — confidence + decision lineage for a recorded runtime point.
3. **Budget tracer** — token consumption across a recorded run.
4. **`.voss`→Python diff viewer** — source `.voss` vs generated Python, side by side.

In scope: CLI-first surfaces for all 4 + read-only reuse of existing M9 TUI widgets via slash/modal. Out of scope: languages other than `.voss` (M10 owns Python ecosystem), editor extensions (EDIT track), live-replay debugger, ANY new runtime emit point.

</domain>

## No SPEC — Requirements Posture

`VTOOL-01..0N` and success criteria are **not locked** (ROADMAP defers them to a SPEC that was deliberately skipped). This CONTEXT + the ROADMAP M11 block are the planner's authority. Recommended VTOOL mapping for the planner / a thin downstream SPEC:

- **VTOOL-01** — `voss-lint-as-skill` reachable as a first-class skill; its frozen JSON schema (T7 D-12) is consumed unchanged by M11 tools. (Mostly verification — code exists.)
- **VTOOL-02** — Probable-value inspector: CLI + read-only TUI over `RunRecord.decisions[]`.
- **VTOOL-03** — Budget tracer: CLI + read-only TUI over `RunRecord.iterations[]` token deltas.
- **VTOOL-04** — `.voss`→Python diff viewer: on-demand CLI/slash, harness-dogfood-capable.
- **VTOOL-05** — All M11 tools registered, `is_mutating=False`, zero new emit points (the thesis guardrail).

Planner may run `/gsd:spec-phase M11` to formalize these, or proceed `--skip-research`-style treating this CONTEXT as the contract (T6/A3 precedent).

<decisions>
## Implementation Decisions

### D-01 — No-emit constraint wins; graph/trace fidelity is DERIVED, not instrumented (central tension)
ROADMAP hard constraint "reuses `voss_runtime/{probable,budget,agent}.py` read-only; no new emit points" is **binding and not escalated**. M11 builds best-effort views over data already recorded:
- `RunRecord.decisions: list[dict]` — confirmed schema is `{title, body, confidence}` only (recorder.py:251-265). **No lineage/`inputs`/`refs` field exists.**
- `RunRecord.iterations: list[IterationRecord]` — per-iteration `prompt_tokens`, `completion_tokens`, cache tokens, `cost_usd`, `exit_reason`.
- `voss_runtime/probable.ProbableValue` is `(value, confidence)` frozen — no provenance attribute.

**Divergence-from-ROADMAP-wording (explicit, M10-CONTEXT-style):** ROADMAP says "propagation graph" and "frame-by-frame". The recorded data **cannot produce a true propagation DAG or per-`ctx(budget:)`-scope frames without new emit points**, which are forbidden. M11 therefore delivers:
- "Propagation graph" → **confidence-annotated decision sequence** (ordered list/tree from `decisions[]`, gate threshold annotated when a decision dict carries one). Planner must NOT add edges that require new recording.
- "Frame-by-frame budget" → **per-agent-iteration token timeline** (the only frame unit already persisted).
True DAG lineage and per-scope budget frames are recorded as deferred (need a future emit-point phase, out of M11).

### D-02 — Deliverable 1 (.voss lint-as-skill) is VERIFY/EXPOSE, not rebuild
T7 already shipped `voss/harness/skills/voss_lint_as_skill.py` (SKL-06) with a **FROZEN M11 diagnostics schema** (`version:1`, `findings[file,line,col,rule,severity,msg,hint]`). M11:
- Consumes that schema **unchanged** — it is a cross-phase contract; do not add/rename/remove fields.
- Does **not** add a `.voss`-skill execution path (T7 explicitly rejected this; registry is LOCKED — respect it).
- Scope = integration test that the skill is first-class reachable + that M11 inspectors/diff can consume its JSON output. No new lint code.

### D-03 — All M11 surfaces are CLI-first; TUI reuse is modal/slash, NO new M9 structural amendment
ROADMAP allows CLI-only first. M9 is COMPLETE and already ships the display widgets. M11 reuses them through on-demand modals/slash — it does **not** reserve a new region or schedule an M9-08-style structural amendment (avoids re-triggering M9 plan-checker; lower risk than M10's CodeIntelPanel path because M11 uses screen-modals, not region panels).
- Probable inspector → reuse `ConfidenceBar` (locked 16-cell widget).
- Budget tracer → reuse `BudgetMeter` / `BudgetModal`.
- `.voss`→Py diff → reuse the `DiffModal` *pattern* as a read-only two-pane sibling (DiffModal itself is approval/fs-hunk-shaped — do not repurpose it; add a read-only `VossPyDiffModal` or CLI side-by-side).

### D-04 — Inspector / tracer shapes
- **Probable-value inspector:** input = `<session-id> [--decision N]`. Output = decision `value`/`title` repr + `confidence` (ConfidenceBar), gate threshold if recorded, and a flat fed-by/feeds-into sequence derived from `decisions[]` order. CLI tree + optional read-only TUI modal.
- **Budget tracer:** input = `<session-id>`. Output = per-iteration cumulative token table + bar (BudgetMeter reuse), marking the iteration where a recorded `token_limit`/`exit_reason="budget"` trips. Frame unit = agent iteration.
- New CLI handler module (planner names — suggest `voss/harness/inspect.py`), mirroring the `voss/harness/skills/*` and M10 tool/slash registration patterns.

### D-05 — `.voss`→Python diff: on-demand, dogfood-capable, no source map
- Trigger = **on-demand only** (`voss vdiff <file.voss>` + slash). NOT auto-on-every-edit (hooking the edit path approaches a new emit point + is noisy; on-demand respects the thesis guardrail and CLI-first).
- Pairing: a `.voss` file → its compiled `.voss-cache/harness/<name>.py` when present (artifacts `loop/router/planner/executor/reviewer.py` + `_manifest.json` already exist); for arbitrary `.voss`, generate via existing `voss.codegen.generate_python` into a cache/temp path and show source-vs-generated. No `.voss`↔`.py` line source map — two-pane file view, not line-mapped hunks.
- MUST work on the harness's own `.voss` (M4 dogfood compound) — e.g. `voss vdiff voss/harness/agent/planner.voss`.

### D-06 — Permission + redaction posture (inherited from M10 sibling pattern)
All M11 tools/skills are `is_mutating=False` (read-only); permission tiers `plan`/`edit`/`auto` all allow them. Any file-content snippet (decision bodies, diff panes) routes through M1's existing `voss/harness/session.py` redaction before persistence — M11 adds no new redaction path, reuses the M10/M1 integration point.

### D-07 — Slash names
Reserved set = `("/recall", "/forget", "/memory", "/save")`; M10 took `/symbol /refs /refresh`. M11 proposes `/probable`, `/budget`, `/vdiff` (no collision with reserved). **Planner must confirm `/budget` is not already claimed by an M9/T-track command** (slash registry not statically enumerable via grep); collision-safe alternates: `/probe`, `/btrace`, `/vdiff`.

### Claude's Discretion (left to planner)
- Exact CLI flag design, table/tree rendering format, sparkline glyph choice.
- Module/file names for the new inspect handlers.
- Whether the TUI modals ship in M11 or are CLI-only first (ROADMAP permits CLI-only; planner sizes against effort).
- Fixture reuse: M10 built `tests/fixtures/code/...`; M11 should reuse `voss/harness/skills/voss/*.voss` + `voss/harness/agent/*.voss` + recorded session fixtures rather than new repos.
- Concrete derived-sequence algorithm for the probable inspector within the D-01 no-edge constraint.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase intent (authoritative — no SPEC exists)
- `.planning/ROADMAP.md` §"Phase M11: Voss-aware Tools (CAPS-01b)" (≈ lines 521-545) — fixed boundary, 4 deliverables, cross-cutting constraints. **Primary authority absent a SPEC.**
- `.planning/notes/voss-agent-unfair-advantage.md` — the "why". The no-new-emit / expose-don't-instrument guardrail traces to this thesis.
- `.planning/seeds/agent-capability-surface.md` (capability 2) — original CAPS-01 seed framing for Voss-aware tools.

### Sibling-phase pattern (closest analog — reuse its structure)
- `.planning/phases/M10-agent-capability-surface-caps-01/M10-CONTEXT.md` — tool/slash/redaction/CLI integration decisions, M9-amendment precedent (M11 deliberately does NOT take the amendment path — see D-03), fixture-reuse + divergence-note pattern.
- `.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md` — requirement/acceptance shape to mirror if `/gsd:spec-phase M11` is run.

### Cross-phase contract (do not break)
- `.planning/phases/T7-skills-bootstrap/T7-CONTEXT.md` — SKL-06 lock, frozen M11 diagnostics schema (D-12), and the explicit rejection of a `.voss`-skill exec path. M11 honors all three.
- `voss/harness/skills/voss_lint_as_skill.py` — the frozen JSON schema source. Consume, never modify.

### Code integration points (read before implementing)
- `voss/harness/session.py` — `RunRecord` (`decisions`, `iterations`), `IterationRecord`, `SessionRecord` schemas. The ONLY data source for D-04/D-05. Also the redaction integration point (D-06).
- `voss/harness/recorder.py` — how `decisions[]` confidence is read/written (`write_decisions_md`, lines ~240-270); confirms the `{title, body, confidence}` shape (no lineage edges).
- `voss_runtime/probable.py`, `voss_runtime/budget.py` — read-only primitives. **No new emit points** (ROADMAP / thesis guardrail).
- `voss/harness/tui/widgets/confidence_bar.py`, `budget_meter.py`, `budget_modal.py`, `diff_modal.py` — reuse targets (D-03). Locked widths/contracts from M9-UI-SPEC.
- `voss/harness/tools.py` (`ToolEntry`, `make_toolset`), `voss/harness/slash.py`, `voss/harness/tui/reserved_slash_names.py` — registration surfaces + reserved-name lock (D-07).
- `voss/harness/permissions.py` — all M11 tools `is_mutating=False`, all tiers allow (D-06).
- `voss/codegen.py` (`generate_python`, ≈ line 1307) + `.voss-cache/harness/*.py` + `.voss-cache/harness/_manifest.json` — diff pairing for D-05.
- `.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md`, `.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md` — widget/glyph/keymap/modal contract authority for any TUI reuse.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `voss_lint_as_skill.py` (T7 SKL-06): deliverable 1 is effectively shipped — frozen JSON contract already feeds M11 consumers.
- M9 widgets `ConfidenceBar` / `BudgetMeter` / `BudgetModal` / `DiffModal`: render layer for deliverables 2/3/4 — no widget rebuild needed.
- `voss.codegen.generate_python`: produces the Python side of the D-05 diff; `.voss-cache/harness/*.py` already compiled for harness dogfood.
- `voss/harness/skills/*.py` + M10 tool/slash registration: the template for new M11 CLI/skill handlers.

### Established Patterns
- M10 sibling: read-only `is_mutating=False` tools, plan/edit/auto all allow, redaction via existing `session.py` pipeline, divergence-from-ROADMAP captured explicitly in CONTEXT.
- Reserved-slash-name allow-list lock (M8) — new names must dodge `("/recall","/forget","/memory","/save")`.
- Recorded-data-only inspection: `RunRecord`/`IterationRecord` are the contract; additive-default discipline (T1/T4) means M11 must not assume fields beyond the confirmed schema.

### Integration Points
- New `voss inspect|vdiff` CLI handlers → register in the same path as M10's tools/slash.
- TUI: on-demand modals pushed onto the existing M9 app (no region reservation, no M9-08 amendment).
- Diff pairing: `<name>.voss` ↔ `.voss-cache/harness/<name>.py` via `_manifest.json`; arbitrary `.voss` ↔ fresh `generate_python` output.

</code_context>

<specifics>
## Specific Ideas

- M11 is a **wiring/exposure phase, not greenfield** — the dominant risk is over-building. Planner should size each deliverable as "thin surface over existing data/widgets," not new subsystems.
- The single highest-risk item is the D-01 divergence: if the planner or a downstream SPEC re-asserts a literal "propagation graph," it will demand new emit points that the ROADMAP forbids. The divergence note must survive into PLAN.md acceptance criteria verbatim.
- Reuse recorded sessions + `voss/harness/agent/*.voss` as fixtures (dogfood compound), not new fixture repos — diff/inspect must demonstrably run on the harness's own workflows.
- `voss vdiff voss/harness/agent/planner.voss` is the canonical dogfood acceptance demo for deliverable 4.

</specifics>

<deferred>
## Deferred Ideas

- **True probable-value propagation DAG** (cross-value lineage edges) — needs new recording instrumentation; forbidden by the M11 no-emit constraint. Future emit-point phase.
- **Per-`ctx(budget:)`-scope / per-tool-call budget frames** — same reason; M11 ships per-iteration granularity only.
- **Auto-on-every-edit `.voss`→Py diff** — rejected for M11 (approaches a new emit point + noisy); on-demand only.
- **`.voss`-skill execution path / `.voss`-as-skill loader** — rejected by T7, registry locked; not reopened here.
- **`.voss`↔Python line-level source map** — out of scope; M11 ships a two-pane file view, not mapped hunks.
- **Editor-extension surfaces for the inspectors** — EDIT track, not M11.
- **Live-replay / time-travel debugger over recorded runs** — explicitly out of ROADMAP M11 scope.

</deferred>

---

*Phase: M11-voss-aware-tools-caps-01b*
*Context gathered: 2026-05-18 via `/gsd-discuss-phase M11` (auto-resolved gray areas per user direction; no SPEC)*
*Next step: `/clear` then `/gsd:plan-phase M11` (planner may run `/gsd:spec-phase M11` first to formalize VTOOL-01..05, or treat this CONTEXT as the contract per T6/A3 precedent).*
