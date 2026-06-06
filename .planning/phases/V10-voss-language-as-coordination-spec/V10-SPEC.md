# Phase V10: Voss Language as Coordination Spec — Specification

**Created:** 2026-06-06
**Ambiguity score:** 0.137 (gate: ≤ 0.20)
**Requirements:** 7 locked (delta on shipped grammar/CLI)

## Goal

Make `.voss` able to fully declare a team run: add the missing coordination grammar blocks (`principles{}`, `gate{}`, `memory{}`) that compile-to-config over the already-shipped runtime, raise compiler diagnostics to a construct+line+fix-hint bar, and ship runnable org-loop examples — so a single `.voss` file passes `voss check` and drives a team run, with the language staying coordination-focused (not a general-programming language).

## Background

The grammar and CLI verbs are largely shipped:
- `voss/cli.py` has `compile`, `run`, `check`, `ast` (LANG-03..06 ✅).
- `voss/grammar.lark` has `team_decl`/`ceiling_block`/`roster_block`/`board_block`/`gate_decl`/`ritual_block`; `ast_nodes.py` has the matching nodes; `team.py` compiles them.
- Raw-Python parity tests exist from M3/M4 (LANG-07).

Gaps vs PRD LANG-01..08:
- **LANG-01** — no `principles{}` block (deferred here from V2), no `memory{}` block, no standalone declarative `gate{}` block (PRD §10: `gate done { require tests_passed; require independent_review; require evidence_refs }`).
- **LANG-02** — `VossTeamConfigError` exists but there's no construct+line+fix-hint diagnostic contract.
- **LANG-08** — no org-loop examples (team orchestration / reviewer split / audit gates); no proven "fully declare a team run".

**Locked direction (interview):** delta — add `principles{}`/`gate{}`/`memory{}` blocks; `principles{}` compiles to the **same V2 `PrinciplesConfig`** (two surfaces, one config); `gate{}`/`memory{}` **compile-to-config over existing runtime** (V5 board gates, V4/cognition memory) — no new enforcement; diagnostics = construct + file:line + fix hint; ship runnable examples + one end-to-end team file; no separate `review{}` block (use `gate ... require independent_review`); language stays coordination-focused.

## Requirements

1. **`principles{}` grammar block** (VLANG-01a): principles are declarable in `.voss`.
   - Current: principles only via `.voss/principles.yml` (V2); no grammar block.
   - Target: `principles { key: "..." }` parses standalone AND nested in `team{}`, compiling to the **same V2 `PrinciplesConfig`**; the block and the YAML file merge per V2's additive/disable rules.
   - Acceptance: a `principles{}` block (standalone + team-nested) parses and compiles to a `PrinciplesConfig`; a file using both the block and `principles.yml` merges per V2 rules.

2. **`gate{}` declarative block** (VLANG-01b): Done gates are declarable.
   - Current: gates are code (`board/gates.py`); the `gate_decl` grammar exists inside `board{}` but no standalone declarative `gate done { require ... }`.
   - Target: `gate done { require tests_passed; require independent_review; require evidence_refs }` parses and compiles to a config that maps onto the existing V5/V6 Done-gate behavior — no new enforcement logic.
   - Acceptance: a `gate done {...}` with the three requires parses + compiles to a config whose requirements correspond to the shipped Done-gate predicates.

3. **`memory{}` grammar block** (VLANG-01c): memory paths are declarable.
   - Current: memory paths are convention (`.voss/decisions`, `.voss/sessions`, `.voss-cache/semantic`); no grammar block.
   - Target: `memory { decisions: "..."; sessions: "..."; semantic: "..." }` parses and compiles to a config that maps onto the existing memory/cognition paths — no new memory engine.
   - Acceptance: a `memory{}` block parses + compiles to a config carrying the three declared paths; defaults apply when a key is omitted.

4. **Diagnostics bar** (VLANG-02): compiler errors are actionable.
   - Current: `VossTeamConfigError` text only.
   - Target: each scope/budget/tools/role/unknown-model/unknown-block error emits a diagnostic naming the offending construct + `file:line` + a one-line fix hint.
   - Acceptance: a message-shape test asserts that each error class includes construct name, `file:line`, and a fix hint.

5. **CLI verbs + parity verification** (verify): the shipped surface regresses green.
   - Current: `ast`/`check`/`compile`/`run` shipped; raw-Python parity tests from M3/M4.
   - Target: verify these still pass after the grammar additions; the new blocks are inspectable via `voss ast` and validated via `voss check`.
   - Acceptance: `ast`/`check`/`compile`/`run` work on a file using the new blocks; existing parity tests pass.

6. **Org-loop examples + end-to-end team file** (VLANG-08): `.voss` can fully declare a team run.
   - Current: no org-loop examples.
   - Target: ship examples for team orchestration, reviewer split, and audit gates; AND one end-to-end `team{}` `.voss` that `voss check` passes and `voss run` drives as a team run on the stub provider.
   - Acceptance: the three examples `voss check` clean; the end-to-end team file passes `voss check` AND `voss run` completes a team run on the stub provider.

7. **Coordination-focus guard** (constraint-as-requirement): the language does not sprawl.
   - Current: `.voss` is a workflow-control language (M3), not general-purpose.
   - Target: V10 additions are coordination constructs only (team/principles/gate/memory/board/roster); no general-programming parity is added.
   - Acceptance: the new grammar adds only coordination blocks; no new general-purpose language features land in the V10 diff.

## Boundaries

**In scope:**
- `principles{}` (standalone + team-nested) → V2 `PrinciplesConfig`.
- `gate{}` declarative block → compile-to-config over V5/V6 gates.
- `memory{}` block → compile-to-config over existing memory paths.
- Diagnostics (construct + file:line + fix hint) + message-shape test.
- Verify `ast`/`check`/`compile`/`run` + raw-Python parity.
- Org-loop examples + one end-to-end runnable `team{}` file.

**Out of scope:**
- A separate `review{}` block — reviewer requirements are expressed via `gate ... require independent_review`.
- New runtime **enforcement** — V10 maps declared config onto existing V2/V4/V5/V6 behavior; it adds no new gate/memory/principle enforcement.
- General-programming language expansion — PRD non-goal ("pure workflow DSL"/"replacement for all languages" are non-goals).
- ADE / editor language tooling — out of this phase.
- Any field change to `RunRecord`/`SessionRecord`/`BudgetScope` — frozen.
- New third-party dependencies.

## Constraints

- `principles{}` compiles to the **same** V2 `PrinciplesConfig` (merge per V2 additive/disable rules) — one config, two surfaces.
- `gate{}`/`memory{}` compile to config objects mapped onto **existing** runtime (V5 board gates, V4/cognition memory) — no new enforcement.
- Diagnostics: construct name + `file:line` + fix hint; asserted by a message-shape test.
- Language stays coordination-focused — no general-programming parity chase.
- Raw-Python parity tests stay green; no change to frozen `RunRecord`/`SessionRecord`/`BudgetScope`; no new deps.

## Acceptance Criteria

- [ ] `principles{}` (standalone + team-nested) parses + compiles to the V2 `PrinciplesConfig`; block + `principles.yml` merge per V2 rules.
- [ ] `gate done { require tests_passed; require independent_review; require evidence_refs }` parses + compiles to a config corresponding to the shipped Done-gate predicates.
- [ ] `memory { decisions/sessions/semantic }` parses + compiles to a config carrying the declared paths; omitted keys default.
- [ ] Each scope/budget/tools/role/unknown-model/unknown-block error emits construct + `file:line` + fix hint; a message-shape test passes.
- [ ] `ast`/`check`/`compile`/`run` work on a file using the new blocks; existing raw-Python parity tests pass.
- [ ] Examples for team orchestration, reviewer split, audit gates `voss check` clean; one end-to-end `team{}` file passes `voss check` AND `voss run` drives a team run on the stub provider.
- [ ] The V10 diff adds only coordination grammar (no general-purpose language features).
- [ ] `git diff` shows zero field changes on `RunRecord`/`SessionRecord`/`BudgetScope`.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                              |
|--------------------|-------|------|--------|--------------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Delta = principles/gate/memory blocks + diagnostics + examples     |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | No review{} block, no new enforcement, no general-programming      |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Same-config principles, compile-to-config, coordination-focus      |
| Acceptance Criteria| 0.84  | 0.70 | ✓      | 8 pass/fail criteria                                              |
| **Ambiguity**      | 0.137 | ≤0.20| ✓      |                                                                  |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective       | Question summary                                  | Decision locked                                                       |
|-------|-------------------|--------------------------------------------------|----------------------------------------------------------------------|
| 0     | Researcher (scout)| What of LANG-01..08 already exists?              | ast/check/compile/run + team/board/gate grammar shipped; gaps = blocks/diagnostics/examples |
| 1     | Researcher        | V10 scope?                                        | Delta: new blocks + diagnostics + examples                          |
| 1     | Researcher        | Which new grammar blocks?                         | principles + gate + memory (no separate review{} block)            |
| 1     | Researcher        | Runtime binding for new blocks?                  | Compile-to-config over shipped runtime (no new enforcement)        |
| 2     | Boundary Keeper   | Diagnostics bar?                                  | Construct + file:line + fix hint (message-shape test)              |
| 2     | Simplifier        | principles{} ↔ V2 config?                         | Same config, two surfaces                                          |
| 2     | Failure Analyst   | Examples + "fully declare a team run"?           | Runnable end-to-end team file (voss check + voss run on stub)      |

---

*Phase: V10-voss-language-as-coordination-spec*
*Spec created: 2026-06-06*
*Next step: /gsd-discuss-phase V10 — implementation decisions (block grammar shapes, diagnostic formatter, example set)*
