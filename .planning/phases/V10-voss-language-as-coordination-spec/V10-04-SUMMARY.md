---
phase: V10-voss-language-as-coordination-spec
plan: 04
type: execute
status: complete
wave: 4
---

# V10-04 Summary — Compiler Diagnostics (VLANG-02)

## Outcome

`VossTeamConfigError` gained `construct`/`fix_hint`/`format_diagnostic()`; all 14
raise sites retrofitted with a construct + fix hint + a resolvable span.
diagnostic-shape scaffold GREEN. Back-compat preserved. Single error class kept.

(Note: V10-04 had not actually run — a prior turn's tool call was malformed.
Executed now, before V10-05 which depends on it.)

## `voss/harness/team.py`

- `VossTeamConfigError.__init__(..., *, construct="", fix_hint="", role_span=None,
  ceiling_span=None)` — both new kwargs defaulted (back-compat). `format_diagnostic()`
  renders `[construct] <message> at file:line` (+ `hint:` line) using
  `role_span or ceiling_span`, else `<unknown>`.
- All 14 raises now pass `construct=` + `fix_hint=` (grep: 14 raises == 14 construct=).
- Span threaded into the value-parse helpers (`_parse_scope_literal`,
  `_parse_budget_value`, `_parse_tools_value`, `_parse_mode_value`,
  `_parse_model_value`, `_resolve_model_string`) via an optional `span` param,
  passed `role_decl_span`/`agent_decl.span` at every roster/agent call site
  (Pitfall 5 — helpers previously lacked a span, so `file:line` was unresolvable).
- Missing-ceiling raise now carries `ceiling_span=decl.span`.

## Construct map (per V10-RESEARCH)

scope (list-item + overflow), budget (type + overflow), tools (type), mode
(value + type), model (tier-not-configured + type), ceiling (missing).

## Verification

- `format_diagnostic` smoke: contains construct + `f.voss:4` + hint. Back-compat:
  `VossTeamConfigError("x").construct == ""`.
- `pytest tests/voss/test_team_diagnostic_shape.py` — 4 passed (budget/scope/model/ceiling, each construct + file:line + fix_hint).
- `pytest tests/voss/ tests/parser/ tests/harness/test_team_check_cli.py tests/harness/test_principles_config.py` — green except org-loop sample tests (sample files absent → V10-05), as expected.
- No new exception class; `VossTeamConfigError` remains the only team-config error.

## Remaining RED

org-loop sample files (→ V10-05, executing next).
