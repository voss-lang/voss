# Phase V2: Principles Layer — Specification

**Created:** 2026-06-06
**Ambiguity score:** 0.153 (gate: ≤ 0.20)
**Requirements:** 6 locked (VPRIN-01/03/04/05/06/07; VPRIN-02→V10, VPRIN-08→V9)

## Goal

Make engineering principles first-class: a `.voss/principles.yml` file (with shipped defaults) compiles to an immutable config and injects as a distinct, capped block into the agent system prompt for `voss do`/`voss chat` — so every run carries the team's culture as text, with no control flow depending on any individual principle.

## Background

No principles plumbing exists (`grep principle` → nothing; no `.voss/principles.yml`). The injection seam is already clean: `agent.py:_compose_system_blocks(voss_md_block, cognition_text, project_index, loop_system, …)` assembles the system prompt from ordered blocks — M2 cognition, M8 VOSS.md, and M10 project index all inject this way (cognition enforces a 6k-token budget with an overflow renderer event). **Principles = one more ordered block**, following that exact precedent.

The grammar already has org-layer nodes (`CeilingDecl`, `TeamDecl`, `RosterDecl`, `BoardDecl` in `ast_nodes.py`) but no `PrinciplesDecl` — a `principles{}` block would follow that model and is deferred to V10. `RunRecord`/`SessionRecord`/`voss_runtime.BudgetScope` are frozen by the O1/V4 redaction invariant, so recording active principles in the audit cannot add a field there.

**Locked direction (interview):** YAML-first (`principles{}` grammar block → V10); inject into the current `_compose_system_blocks` path now (role-specific EM/reviewer/tester contexts inherit the block as V3/V6/V7 build them); audit recording of active principles → V9; additive merge with explicit disable; frozen config / opaque injection guarded by a no-branching test; ~1k-token cap with overflow warning.

## Requirements

1. **principles.yml loader** (VPRIN-01): a YAML principles file loads into a config.
   - Current: no loader; no `.voss/principles.yml`.
   - Target: `.voss/principles.yml` (a key→string map) loads into a `PrinciplesConfig`; a malformed file surfaces a clear error (not silent), reusing the existing YAML/pydantic stack (no new deps).
   - Acceptance: a valid `principles.yml` loads to the expected key→string set; a malformed file raises a clear, non-silent error.

2. **Immutable config + no control-flow coupling** (VPRIN-03): principles are frozen, opaque text.
   - Current: n/a.
   - Target: principles compile to a frozen `PrinciplesConfig`; principles are injected as opaque text only — no harness/agent code branches on individual principle keys/strings.
   - Acceptance: `PrinciplesConfig` is immutable (mutation raises); a guard test confirms no code path conditionals on individual principle keys/strings.

3. **System-prompt injection** (VPRIN-04): active principles inject into the current agent context.
   - Current: `_compose_system_blocks` injects cognition/VOSS.md/index but not principles.
   - Target: active principles inject as a distinct ordered block in `_compose_system_blocks`, so `voss do`/`voss chat` (and current subagents) carry them; the block respects a ~1k-token cap with truncation + a renderer overflow warning (mirroring cognition's budget pattern). Role-specific contexts (EM/reviewer/tester) inherit the same block as later phases build them.
   - Acceptance: the system prompt for a `voss do`/`voss chat` turn contains a distinct principles block; an over-cap principles set truncates and emits a renderer warning.

4. **Default principles shipped** (VPRIN-05): Voss ships a default set, active without any project file.
   - Current: none.
   - Target: ship the six defaults — `diff`, `evidence`, `tests`, `scope`, `review`, `reversibility` (PRD §P2 text).
   - Acceptance: with no `.voss/principles.yml` present, the six defaults are the active principles and are injected.

5. **Additive override + explicit disable** (VPRIN-06): project principles layer over defaults.
   - Current: n/a.
   - Target: a project `.voss/principles.yml` adds to / overrides defaults by key; defaults remain active unless explicitly disabled (key set null, or a `disable: [keys]` list).
   - Acceptance: a project file adding a new key yields defaults + the new key; overriding an existing key replaces that string; a disabled default is absent while non-disabled defaults remain.

6. **`voss principles show`** (VPRIN-07): the active set is inspectable.
   - Current: no command.
   - Target: `voss principles show` prints the active (merged) principles and each one's source (default vs project).
   - Acceptance: `voss principles show` exits 0 and lists every active principle with its source label.

## Boundaries

**In scope:**
- `.voss/principles.yml` loader → frozen `PrinciplesConfig`.
- Six shipped default principles.
- Additive override + explicit-disable merge.
- Injection as a capped ordered block in `_compose_system_blocks` (current `voss do`/`voss chat`/subagent path).
- `voss principles show`.
- No-control-flow-branching guard test.

**Out of scope:**
- `principles{}` grammar block + `team{}` nesting (PRIN-02) — V10 (language stabilization).
- Audit recording of active principles (PRIN-08) — V9 (Audit Product owns the audit surface; avoids touching frozen `RunRecord` + double-building audit plumbing).
- Role-specific (EM/reviewer/tester) context injection — those roles inherit the principles block as V3/V6/V7 build them; V2 wires only the existing context path.
- Any field change to `RunRecord`/`SessionRecord`/`voss_runtime.BudgetScope` — frozen (redaction invariant).
- New third-party dependencies.

## Constraints

- **Schema freeze:** no field added/removed on `RunRecord`/`SessionRecord`/`BudgetScope`; redaction test stays green.
- Principles are opaque injected text; **no harness/agent code may branch on individual principle keys/strings** (guard test).
- Injected principles block ≤ ~1k tokens; overflow truncates + emits a renderer warning (mirror cognition's 6k pattern).
- `principles.yml` is a YAML key→string map; reuse the existing YAML/pydantic stack — no new deps.
- Defaults are always active unless explicitly disabled.

## Acceptance Criteria

- [ ] A valid `.voss/principles.yml` (key→string) loads into a frozen `PrinciplesConfig`; a malformed file raises a clear, non-silent error.
- [ ] The six defaults (`diff`, `evidence`, `tests`, `scope`, `review`, `reversibility`) ship and are active when no project file exists.
- [ ] A project `principles.yml` additively overrides/extends defaults by key; a default is removed only via explicit disable (null / `disable:` list); non-disabled defaults remain.
- [ ] Active principles inject as a distinct block in the system prompt for `voss do`/`voss chat` (and current subagents) via `_compose_system_blocks`.
- [ ] The injected block respects the ~1k-token cap; overflow truncates and emits a renderer warning.
- [ ] `voss principles show` exits 0 and prints the active merged principles + each one's source (default vs project).
- [ ] `PrinciplesConfig` is immutable; a guard test confirms no code branches on individual principle keys/strings.
- [ ] `git diff` shows zero field changes on `RunRecord`/`SessionRecord`/`BudgetScope`.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                            |
|--------------------|-------|------|--------|------------------------------------------------------------------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | YAML-first, inject-now, defaults, show — scope pinned             |
| Boundary Clarity   | 0.86  | 0.70 | ✓      | Grammar→V10, audit→V9, role contexts inherit-later all explicit   |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Schema freeze, no-branching guard, ~1k cap, no new deps           |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | 8 pass/fail criteria                                              |
| **Ambiguity**      | 0.153 | ≤0.20| ✓      |                                                                  |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective       | Question summary                                  | Decision locked                                                      |
|-------|-------------------|--------------------------------------------------|---------------------------------------------------------------------|
| 0     | Researcher (scout)| What principles plumbing exists?                 | None; clean injection seam (`_compose_system_blocks`) + grammar precedent |
| 1     | Researcher        | Config surface: YAML vs `principles{}` grammar?  | YAML-first; grammar block → V10                                     |
| 1     | Researcher        | Where to inject given role contexts don't exist? | Inject into current `_compose_system_blocks` path now; roles inherit later |
| 1     | Researcher        | Audit recording vs the RunRecord freeze?         | Defer audit recording to V9                                          |
| 2     | Simplifier        | Override/merge semantics?                         | Additive + explicit disable                                         |
| 2     | Boundary Keeper   | Immutability + no-branching?                      | Frozen `PrinciplesConfig`, opaque injection, guard test            |
| 2     | Failure Analyst   | Token budget for the injected block?             | ~1k hard cap + overflow warning                                     |

---

*Phase: V2-principles-layer*
*Spec created: 2026-06-06*
*Next step: /gsd-discuss-phase V2 — implementation decisions (principles.yml schema, show output, injection block placement/order)*
