---
phase: V10-voss-language-as-coordination-spec
plan: 04
type: execute
wave: 4
depends_on:
  - V10-03
files_modified:
  - voss/harness/team.py
autonomous: true
requirements:
  - VLANG-02

must_haves:
  truths:
    - "Each scope/budget/tools/mode/model/ceiling config error emits a construct name"
    - "Each such error emits a file:line location"
    - "Each such error emits a one-line fix hint"
    - "A message-shape test asserts construct + file:line + fix_hint per error class"
    - "Existing VossTeamConfigError callers (no construct/fix_hint) still work — fields default to empty"
  artifacts:
    - path: "voss/harness/team.py"
      provides: "VossTeamConfigError.construct + .fix_hint + format_diagnostic() and retrofit of raise sites"
      contains: "format_diagnostic"
  key_links:
    - from: "voss/harness/team.py raise sites"
      to: "VossTeamConfigError(construct=, fix_hint=, role_span=)"
      via: "every config-error raise passes construct + fix_hint"
      pattern: "construct="
    - from: "VossTeamConfigError.format_diagnostic"
      to: "Span.file / Span.line_start"
      via: "renders file:line from role_span or ceiling_span"
      pattern: "line_start"
---

<objective>
Raise compiler diagnostics to the VLANG-02 bar: every team-config error names the offending construct, points at `file:line`, and gives a one-line fix hint. This is an additive upgrade to the single `VossTeamConfigError` class (add `construct`/`fix_hint` kwargs, both defaulted for back-compat, plus a `format_diagnostic()` renderer) and a retrofit of the ~14 raise sites in `team.py` so each populates `construct` + `fix_hint`. A message-shape test (already RED-scaffolded in V10-01) asserts the shape per error class.

Purpose: Close VLANG-02. Sequenced AFTER V10-03 because both edit `voss/harness/team.py` (file-ownership conflict → serial waves).
Output: `voss/harness/team.py` diagnostics-upgraded; V10-01 diagnostics-shape scaffold (Task 3) goes GREEN.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V10-voss-language-as-coordination-spec/V10-SPEC.md
@.planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md
@.planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md

<interfaces>
<!-- Diagnostics upgrade surface, verified against the live codebase. -->

voss/harness/team.py:
  VossTeamConfigError (line 33): __init__(self, message, *, role_span=None, ceiling_span=None)
    self.role_span, self.ceiling_span

voss/ast_nodes.py:
  Span (line 7): file: str; line_start: int; col_start: int; line_end; col_end; synthetic=False

Raise-site → construct map (V10-RESEARCH.md lines 362-381 / V10-PATTERNS.md lines 290-303):
  team.py 395, 399        → construct="scope"   hint="scope list entries must be string literals"
  team.py 413             → construct="budget"  hint="use a token budget like: budget: 100 tokens"
  team.py 428, 434        → construct="tools"   hint='tools must be a string literal or list: tools: ["fs", "test"]'
  team.py 445             → construct="mode"    hint="mode must be one of: plan, edit, auto"
  team.py 450             → construct="mode"    hint="mode must be a string literal"
  team.py 467             → construct="model"   hint="configure the tier in [model_tiers]"
  team.py 492             → construct="model"   hint="model must be a string literal or tier keyword"
  team.py 525, 535        → construct="scope"   hint="role scope must be within the ceiling scope globs"
  team.py 606, 618        → construct="scope"/"budget"  (roster equivalents)
  team.py 648             → construct="ceiling" hint="add a ceiling { budget: N tokens } block to team"
  (line numbers are approximate — they shift after V10-03 edits; locate by error-message text, not line number)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Upgrade VossTeamConfigError with construct + fix_hint + format_diagnostic()</name>
  <behavior>
    - VossTeamConfigError("m") still constructs (construct=="" , fix_hint=="") — back-compat
    - VossTeamConfigError("m", construct="budget", fix_hint="h", role_span=Span(...)) stores all four
    - err.format_diagnostic() returns a string containing the construct in brackets, the message, "file:line" from role_span (fallback ceiling_span, fallback "<unknown>"), and the hint when present
  </behavior>
  <read_first>
    - voss/harness/team.py (VossTeamConfigError lines 33-45 — current __init__ keeps role_span/ceiling_span)
    - voss/ast_nodes.py (Span fields lines 7-15 — file + line_start are the location source)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md (target shape + format_diagnostic lines 265-288)
  </read_first>
  <action>
    In voss/harness/team.py modify `VossTeamConfigError.__init__` to add two keyword-only parameters with defaults: `construct: str = ""` and `fix_hint: str = ""`, placed before the existing `role_span`/`ceiling_span` kwargs (all keyword-only, so order is flexible; keep existing ones). Store `self.construct = construct` and `self.fix_hint = fix_hint`.
    Add a `format_diagnostic(self) -> str` method: pick `span = self.role_span or self.ceiling_span`; compute `location = f"{span.file}:{span.line_start}"` when a span exists else `"<unknown>"`; render `f"[{self.construct}] {self} at {location}"` plus `f"  hint: {self.fix_hint}"` when `fix_hint` is non-empty. (Exact prose is discretionary per CONTEXT "Diagnostic formatter implementation"; the required tokens are: the construct, a `file:line` substring, and the hint text.)
    Do not change any existing behavior of the message string passed to `super().__init__`.
  </action>
  <verify>
    <automated>.venv/bin/python -c "from voss.harness.team import VossTeamConfigError; from voss.ast_nodes import Span; e=VossTeamConfigError('bad', construct='budget', fix_hint='lower it', role_span=Span('f.voss',4,5,4,9)); d=e.format_diagnostic(); assert 'budget' in d and 'f.voss:4' in d and 'lower it' in d, d; e2=VossTeamConfigError('x'); assert e2.construct=='' and e2.fix_hint==''; print('DIAG_OK')"</automated>
  </verify>
  <acceptance_criteria>
    - VossTeamConfigError.__init__ accepts construct and fix_hint (both defaulting to "")
    - VossTeamConfigError has a format_diagnostic method
    - format_diagnostic output contains the construct, a `file:line` substring, and the fix hint
    - Back-compat: `VossTeamConfigError("x")` constructs with construct=="" and fix_hint==""
    - Existing team-compile/back-compat suites green: `.venv/bin/python -m pytest tests/voss/test_team_compile.py tests/voss/test_team_backcompat_regression.py -q` exits 0
    - Inline -c prints DIAG_OK
  </acceptance_criteria>
  <done>VossTeamConfigError gains construct/fix_hint/format_diagnostic; back-compat preserved; existing suites green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Retrofit team.py raise sites with construct + fix_hint; turn diagnostic-shape test green</name>
  <behavior>
    - Compiling a team whose role budget exceeds the ceiling raises VossTeamConfigError with construct=="budget", non-empty fix_hint, and a span (file:line resolvable)
    - A role scope outside the ceiling scope raises construct=="scope"
    - An unknown model tier raises construct=="model"
    - A team missing its ceiling raises construct=="ceiling"
    - Each such error's format_diagnostic() contains a file:line substring
  </behavior>
  <read_first>
    - voss/harness/team.py (ALL `raise VossTeamConfigError(...)` sites — locate by message text since V10-03 shifted line numbers; the helpers `_parse_scope_literal`/`_parse_budget_value`/`_parse_tools_value` and the roster/agent/ceiling paths)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md (Pitfall 5 — helpers lacking a Span; thread Span|None into helper signatures, lines 480-485)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md (raise-site retrofit table lines 290-303; construct+fix_hint raise example lines 541-551)
    - tests/voss/test_team_diagnostic_shape.py (the RED scaffold from V10-01 — confirm which error classes/snippets it exercises so every asserted construct is produced with a span)
  </read_first>
  <action>
    Retrofit every `raise VossTeamConfigError(...)` in voss/harness/team.py to pass `construct=` and `fix_hint=` per the map in the `<interfaces>` block (locate sites by message text, not line number). Preserve the existing `role_span`/`ceiling_span` arguments where already present.
    For the error classes the V10-01 diagnostic-shape test exercises (at minimum budget / scope / model / ceiling), ensure a Span reaches the error so `format_diagnostic()` renders a real `file:line`:
    - Where a site already has `role_span`/`ceiling_span`, keep it.
    - For raises inside the value-parse helpers (`_parse_scope_literal`, `_parse_budget_value`, `_parse_tools_value`, mode/model helpers) that currently have NO span (Pitfall 5): thread an optional `span: Span | None = None` parameter into the helper signature and pass the caller's role/ceiling span at each call site, then raise with `role_span=span`. If threading a span into a helper is disproportionate for a given site, instead raise the typed error at the caller (which already has the span) rather than inside the span-less helper — pick whichever keeps the diff smallest while satisfying the test.
    Keep messages otherwise unchanged. Do not introduce new error classes — `VossTeamConfigError` remains the single class.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/voss/test_team_diagnostic_shape.py -q</automated>
  </verify>
  <acceptance_criteria>
    - Every `raise VossTeamConfigError(` in voss/harness/team.py passes a non-empty `construct=`: `grep -c "raise VossTeamConfigError(" voss/harness/team.py` equals the count of `construct=` occurrences inside those raises (no bare raises remain)
    - The V10-01 diagnostic-shape scaffold PASSES: the pytest command above exits 0, covering at least budget/scope/model/ceiling with construct + file:line + fix_hint assertions
    - No new exception class is introduced (VossTeamConfigError stays the only team-config error)
    - Full compile + parity regression green: `.venv/bin/python -m pytest tests/voss/ tests/parser/ tests/harness/test_team_check_cli.py tests/harness/test_principles_config.py -q` exits 0
  </acceptance_criteria>
  <done>All raise sites carry construct + fix_hint with a resolvable span for tested classes; diagnostic-shape scaffold GREEN; single error class preserved; full compile+parity green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `.voss` config error → diagnostic string | Error messages render user-supplied construct context (key names, span file path) into operator-facing text |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V10-04-01 | Information Disclosure | format_diagnostic leaking absolute file paths in error output | accept | The `Span.file` value is the path the user themselves passed to `voss check`/`parse`; echoing it back in a diagnostic is expected behavior, not a disclosure beyond the user's own input |
| T-V10-04-02 | Repudiation | error text not actionable / wrong construct attribution | mitigate | The message-shape test asserts construct + file:line + fix_hint are present per error class, preventing silent regression to bare-text errors |
| T-V10-04-SC | Tampering | npm/pip/cargo installs | accept (N/A) | No package installs; pure additive edit to the existing error class. No new dependency. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/voss/test_team_diagnostic_shape.py -q` — green.
- Per-wave merge: `.venv/bin/python -m pytest tests/voss/ tests/parser/ tests/harness/test_team_check_cli.py tests/harness/test_principles_config.py tests/harness/test_voss_loop_parity.py -q` — all green except org-loop + e2e scaffolds (RED until V10-05).
- VossTeamConfigError remains the single team-config error class (no new classes).
</verification>

<success_criteria>
- Every team-config error names construct + file:line + fix hint.
- Back-compat preserved (defaulted kwargs).
- V10-01 diagnostic-shape scaffold GREEN.
</success_criteria>

<output>
Create `.planning/phases/V10-voss-language-as-coordination-spec/V10-04-SUMMARY.md` when done.
</output>
