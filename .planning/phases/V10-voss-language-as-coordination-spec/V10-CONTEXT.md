# Phase V10: Voss Language as Coordination Spec - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning
**Source:** Direct synthesis from V10-SPEC.md (ambiguity 0.137; locked direction from interview)

<domain>
## Phase Boundary

Make `.voss` able to **fully declare a team run**. The grammar (`team`/`board`/`gate_decl`/`roster`/`ritual`) and CLI verbs (`compile`/`run`/`check`/`ast`) are already shipped (M3/M4). V10 closes the remaining LANG-01..08 gaps as a **delta**:

1. Add three missing coordination grammar blocks: `principles{}`, `gate{}` (standalone declarative), `memory{}`.
2. Raise compiler diagnostics to a **construct + file:line + fix-hint** bar.
3. Ship runnable org-loop examples + one end-to-end `team{}` `.voss` that `voss check` passes and `voss run` drives on the stub provider.

The new blocks **compile-to-config over the already-shipped runtime** — no new enforcement. `principles{}` compiles to the *same* V2 `PrinciplesConfig` (two surfaces, one config). `gate{}`/`memory{}` map onto existing V5/V6 Done-gates and V4/cognition memory paths. Language stays coordination-focused; no general-programming parity.

</domain>

<decisions>
## Implementation Decisions

All locked at SPEC (interview rounds 0–2). Treat every item below as a locked decision.

### Grammar blocks (delta on shipped `voss/grammar.lark` + `ast_nodes.py` + `team.py`)
- Add `principles{}` block — parses **standalone AND nested in `team{}`**; compiles to the **same V2 `PrinciplesConfig`**; block + `.voss/principles.yml` merge per V2 additive/disable rules.
- Add standalone declarative `gate{}` block — `gate done { require tests_passed; require independent_review; require evidence_refs }` parses + compiles to a config mapping onto **existing** V5/V6 Done-gate predicates. (`gate_decl` already exists *inside* `board{}` — this is the standalone form.)
- Add `memory{}` block — `memory { decisions: "..."; sessions: "..."; semantic: "..." }` parses + compiles to a config carrying the three paths; omitted keys default to convention (`.voss/decisions`, `.voss/sessions`, `.voss-cache/semantic`).

### Runtime binding
- All three blocks are **compile-to-config only** over shipped runtime. No new gate/memory/principle enforcement logic. V10 maps declared config onto existing V2/V4/V5/V6 behavior.

### Diagnostics bar (VLANG-02)
- Each scope/budget/tools/role/unknown-model/unknown-block error emits a diagnostic naming the offending **construct + `file:line` + a one-line fix hint**.
- Asserted by a **message-shape test** (construct name, `file:line`, fix hint present per error class).
- Builds on existing `VossTeamConfigError` (currently text-only).

### CLI + parity (verify)
- `ast`/`check`/`compile`/`run` must work on a file using the new blocks; new blocks inspectable via `voss ast`, validated via `voss check`.
- Existing raw-Python parity tests (M3/M4, LANG-07) stay green.

### Examples (VLANG-08)
- Ship three org-loop examples: team orchestration, reviewer split, audit gates — each `voss check` clean.
- Ship **one** end-to-end `team{}` `.voss` file that passes `voss check` AND `voss run` drives as a team run **on the stub provider**.

### Claude's Discretion
- Exact block grammar shapes (lark rule structure, terminal naming) within the coordination-focused constraint.
- Diagnostic formatter implementation (how construct/file:line/fix-hint are assembled).
- Example set content/scenarios beyond the three named categories.
- Internal config object shapes for `gate{}`/`memory{}` (must map onto existing runtime).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase spec
- `.planning/phases/V10-voss-language-as-coordination-spec/V10-SPEC.md` — locked requirements, boundaries, constraints, acceptance criteria.

### Grammar / language (shipped — extend, don't rewrite)
- `voss/grammar.lark` — existing `team_decl`/`ceiling_block`/`roster_block`/`board_block`/`gate_decl`/`ritual_block`.
- `voss/ast_nodes.py` — matching AST nodes.
- `voss/team.py` — compiles team grammar blocks to config.
- `voss/cli.py` — `compile`/`run`/`check`/`ast` verbs.

### Runtime config to compile *onto* (no new enforcement)
- V2 `PrinciplesConfig` (principles surface — `.voss/principles.yml` loader + additive/disable merge rules).
- V5/V6 board Done-gate predicates (`board/gates.py`) — target for `gate{}` config.
- V4/cognition memory paths — target for `memory{}` config.

### Parity (must stay green)
- Raw-Python parity tests from M3/M4 (LANG-07).

</canonical_refs>

<specifics>
## Specific Ideas

- Done-gate canonical form: `gate done { require tests_passed; require independent_review; require evidence_refs }`.
- No separate `review{}` block — reviewer requirement is expressed via `gate ... require independent_review`.
- Frozen (zero field changes): `RunRecord`, `SessionRecord`, `BudgetScope` — `git diff` must show no field changes on these.
- No new third-party dependencies.

## Requirements (locked at SPEC)
- VLANG-01a — `principles{}` grammar block → V2 `PrinciplesConfig`
- VLANG-01b — `gate{}` declarative block → config over V5/V6 gates
- VLANG-01c — `memory{}` grammar block → config over existing memory paths
- VLANG-02 — diagnostics bar (construct + file:line + fix hint; message-shape test)
- (verify) — CLI verbs `ast`/`check`/`compile`/`run` + raw-Python parity green
- VLANG-08 — org-loop examples + one end-to-end runnable `team{}` file
- (guard) — coordination-focus: V10 diff adds only coordination grammar

</specifics>

<deferred>
## Deferred Ideas

- A separate `review{}` block — explicitly out; use `gate ... require independent_review`.
- New runtime enforcement for gates/memory/principles — out; compile-to-config only.
- General-programming language expansion — PRD non-goal.
- ADE / editor language tooling — out of this phase.

</deferred>

---

*Phase: V10-voss-language-as-coordination-spec*
*Context synthesized: 2026-06-07 direct from V10-SPEC.md*
