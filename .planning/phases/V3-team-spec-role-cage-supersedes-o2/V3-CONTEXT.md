# Phase V3: Team Spec + Role Cage (supersedes O2) - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning
**Source:** Direct from V3-SPEC.md (discuss-phase skipped — ambiguity 0.137, decisions locked; SPEC interview log carries the researcher scout)

<spec_lock>
## Locked Requirements (from V3-SPEC.md — MUST read before planning)

`.planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-SPEC.md` — V3 is a **DELTA on shipped O2**.

- **Already shipped (TEAM-01..06 = VTEAM-01..06): VERIFY-GREEN only, do NOT rebuild.**
  `compile_team` → frozen `TeamConfig` + `SubagentRegistry`; `SubagentSpec` carries
  id/prompt/model/mode/scope/budget/tools/net; compile-time scope + budget containment
  (raises); EM-invent guard. V3 must regress these green after the delta.
- **Build the four gaps:** VTEAM-09 (roster), VTEAM-08 (model tiers), VTEAM-10 (`voss team check`),
  VTEAM-07 (capability-binding seam — keep toolset-key filtering, document the V1 seam).
- VTEAM-02 grammar `principles{}` nesting → V10. Audit recording → V9. board/gate/ritual execution → V5/V7. NOT here.

The 7 SPEC Acceptance Criteria are the verification bar.
</spec_lock>

<domain>
## Phase Boundary

Close the gap between the shipped O2 `.voss team{}` compiler and PRD TEAM-01..10: replace the
default roster with the PRD's seven specialist roles, add model-tier aliases (strong/cheap/fast),
ship a `voss team check` CLI, and document the V1 capability-registry binding seam — while keeping
the shipped compile/containment/cage path + legacy roles working and the record schemas frozen.
Marks O2 superseded (O2 artifacts retained as reference). New deps: none.
</domain>

<decisions>
## Implementation Decisions (the HOW the SPEC's "next step" flagged)

### D-01 — Default roster → the PRD seven (VTEAM-09)
- Replace `DEFAULT_ROSTER = ("backend", "frontend", "ui", "ai")` (team.py:48) with
  `("architect", "backend", "frontend", "tester", "reviewer", "skeptic", "docs")`.
- Extend `default_team_role_defaults` (team.py:51, today returns only `(description, role_prompt)`
  for backend/frontend/ui/ai) so each of the seven carries a non-empty default
  description, role_prompt, model-tier, scope, and tools. If the current return shape can't hold
  tier/scope/tools, widen it (a per-role defaults struct/map) — planner's call; keep it frozen-config-friendly.
- Open-roster fallback for custom names retained (OQ-02-A opaque fallback stays).

### D-02 — Model-tier aliases (VTEAM-08)
- `_parse_model_value` (team.py:304, today raw `StringLit` → string only) gains tier resolution:
  `strong` / `cheap` / `fast` resolve to a concrete model id; a raw model string still passes through;
  an unknown model OR unknown tier raises a clear `VossTeamConfigError` naming the offending value.
- **Tier→model resolution source:** the existing models stack — `model_catalog.py`
  (`load_catalog`/`find_by_id`) + `model_prefs.py`. There is NO `RuntimeConfig` class today; the
  tier→concrete-model TABLE is config-backed (resolve a tier to a model id, then validate it exists
  in the catalog). Exact table location (a `.voss` config key vs a model_prefs-style store) is
  Claude's discretion — but it MUST be config/catalog-driven, not hardcoded model names in team.py.
- Roster defaults (D-01) use TIERS, not concrete model names.

### D-03 — `voss team check [path]` CLI (VTEAM-10)
- Add a `team` click group (or `team_check` command) with `check [path]`, default path
  `.voss/team.voss`, registered in the `AGENT_COMMANDS` tuple (cli.py:3672, same pattern as
  V1's `capabilities`/V2's `principles`).
- It WRAPS `compile_team` — single validation path, no second validator. On success: exit 0 +
  print PASS with roster + ceiling summary. On `VossTeamConfigError`: exit 1 + print the first error.
  Missing file: exit non-zero + clear message. JSON-first option welcome (`--json`).

### D-04 — Capability-registry binding seam (VTEAM-07)
- Keep today's `filter_toolset_for_role` (team.py:128, raw toolset-key + `net` alias) — NO behavior
  change in V3. Add a documented seam/marker (comment + a small doc note) where V1's capability
  registry will replace raw-key filtering. Verify a role declaring a tool subset receives exactly
  those tools (net excluded unless declared).

### D-05 — Backward compatibility (verify, SPEC req 5)
- New roster is the default, but legacy `explorer`/`worker`/`reviewer` (subagents.py
  `default_subagent_registry`) AND old roster names `ui`/`ai` still resolve (overlap/aliases).
  Existing O2 specs/tests pass UNMODIFIED. Note: `reviewer` is in BOTH the legacy path and the new
  roster — ensure they reconcile, not collide.

### D-06 — Shipped-surface regression + O2 supersede (verify, SPEC req 6)
- Verify TEAM-04/05/06 regress green: scope-widening fails at compile; over-ceiling role budget
  fails at compile; EM dispatch to undeclared role denied (`em/handle.py`). Mark O2 superseded (bookkeeping only).

### Claude's Discretion (lock at planning)
- The per-role default values (scope globs, tool sets, tiers, prompt text) for the seven roles —
  use the PRD §"Example Syntax" as the template for architect/backend/reviewer; author tester/
  skeptic/frontend/docs in the same spirit.
- The tier→model table location + exact resolution call into model_catalog.
- `team check` output formatting + whether it's a group or a flat command.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Spec / PRD
- `.planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-SPEC.md` — locked delta requirements + 7 acceptance criteria. Read first.
- `.planning/docs/ORCHESTRATION_LAYERS.md` §"Phase 3: Team Specification And Role Cage" — PRD TEAM-01..10 + §"Example Syntax" (the per-role default template).
- `.planning/ROADMAP.md` §"Phase V3" — VTEAM mapping; O2 supersession (V3↔O2).

### The shipped O2 surface being extended
- `voss/harness/team.py` — `DEFAULT_ROSTER` (L48), `default_team_role_defaults` (L51),
  `_parse_model_value` (L304), `filter_toolset_for_role` (L128), `gate_for_role` (L98),
  `compile_team`, `TeamConfig` (L211), `VossTeamConfigError` (L33), scope/budget containment.
- `voss/harness/subagents.py` — `SubagentSpec` (L34), `SubagentRegistry` (L48),
  `default_subagent_registry` (L65, legacy explorer/worker/reviewer).
- `voss/harness/model_catalog.py` (`load_catalog`, `find_by_id`, `ModelEntry`) +
  `voss/harness/model_prefs.py` — the tier→concrete-model resolution source (the `/models` picker stack).
- `voss/harness/cli.py` — `AGENT_COMMANDS` (L3672) — register `voss team check`.
- `voss/harness/em/handle.py` — EM-invent guard (verify TEAM-04 green).
- O2 reference artifacts: `.planning/phases/O2-voss-team-spec-roster/` (SUMMARYs O2-01/02/03).

### Frozen — must NOT change (schema-freeze constraint, carried)
- `voss/harness/session.py` `RunRecord`/`SessionRecord`, `voss_runtime/budget.py` `BudgetScope` —
  zero field changes; redaction test stays green.

### Tests
- Existing O2 team tests (must pass unmodified) + new tests for roster/tiers/`team check`/back-compat.
</canonical_refs>

<code_context>
## Reusable Assets / Integration Points

- `compile_team` is the single compile/validation path — `voss team check` wraps it (D-03); do not fork a second validator.
- `default_team_role_defaults` today returns `(description, role_prompt)` for 4 roles — the natural extension point for the 7-role defaults (D-01).
- `_parse_model_value` is the single model-parse choke point — tier alias resolution lands here (D-02).
- `filter_toolset_for_role` (raw toolset-key + net alias) stays as-is; V1 capability registry replaces it later (D-04 seam).
- `AGENT_COMMANDS` click-group tuple = where `voss team` attaches (same as V1 `capabilities`, V2 `principles`).
- Legacy `default_subagent_registry` (explorer/worker/reviewer) must keep resolving (D-05).
</code_context>

<specifics>
## Specific Ideas

- PRD §"Example Syntax" gives concrete defaults for architect (model strong/mode plan/scope src+docs/tools fs,code,git/budget 12k), backend (cheap/edit/server scope/fs,code,test,git/24k), reviewer (strong/plan/src+tests/16k) — use as the roster default template.
- `voss team check`: exit 0 + roster/ceiling on valid; exit 1 + first error on invalid; missing file non-zero + clear message.
- Tiers (strong/cheap/fast) in roster defaults, never hardcoded model names.
- Schema freeze carried: zero field changes on RunRecord/SessionRecord/BudgetScope.
</specifics>

<deferred>
## Deferred Ideas

- TEAM-07 capability-registry FORM (raw-key → capability binding) → V1 (V3 keeps toolset-key filtering + documents seam).
- `principles{}` nested in `team{}` → V10 (grammar block).
- `board{}`/`gate{}`/`ritual{}` execution semantics → V5 (board) / V7 (EM dispatch).
- Audit recording of team config → V9.
</deferred>

---

*Phase: V3-team-spec-role-cage-supersedes-o2*
*Context derived 2026-06-06 directly from V3-SPEC.md (discuss-phase skipped per low ambiguity)*
