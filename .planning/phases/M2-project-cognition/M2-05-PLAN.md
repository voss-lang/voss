---
phase: M2
plan: 05
type: execute
wave: 4
depends_on: [M1, M2-00, M2-01, M2-02, M2-03, M2-04]
files_modified:
  - voss/harness/agent.py
  - voss/harness/render.py
  - voss/harness/cli.py
  - tests/harness/test_repl_cognition.py
  - tests/harness/test_agent_integration.py
autonomous: true
requirements:
  - COG-02
  - COG-08
tags:
  - harness
  - agent
  - cognition
  - renderer

must_haves:
  truths:
    - "When cognition.load(cwd) returns initialized=True, run_turn prepends architecture.md (full) + constraints.yml (bullets) before PLAN_SYSTEM in the system message."
    - "If the rendered cognition block exceeds 6000 tokens, the harness emits a cognition_overflow event and truncates constraints first (architecture stays intact). User-visible hint surfaces."
    - "Renderer protocol gains show_cognition; Tty prints a dim status line, Plain prints to stderr, Json emits a cognition_loaded NDJSON event."
    - "voss resume rehydrates a 'Prior context' system-prompt block containing the most-recent RunRecord's goal/plan/decisions/follow_ups/risks."
    - "REPL launch wires cognition into the run_turn calls inside _run_repl via cognition.load(cwd) — once per REPL session, passed into each turn."
  artifacts:
    - path: "voss/harness/agent.py"
      provides: "_compose_cognition_prompt(bundle) helper + cognition prepend in run_turn + 6k overflow handling + prior-context block for resume"
      contains: "_compose_cognition_prompt"
    - path: "voss/harness/render.py"
      provides: "Renderer.show_cognition(...) on protocol + Tty/Plain/Json implementations + cognition_overflow event on Json"
      contains: "show_cognition"
    - path: "voss/harness/cli.py"
      provides: "_run_repl loads cognition bundle once + passes into run_turn + resume passes most-recent RunRecord as prior_context"
      contains: "cognition.load(cwd"
    - path: "tests/harness/test_repl_cognition.py"
      provides: "test_cognition_status_line_tty, test_cognition_loaded_ndjson_event, test_cognition_overflow_truncates_constraints unskipped"
      contains: "def test_cognition_status_line_tty"
    - path: "tests/harness/test_agent_integration.py"
      provides: "test_turn_injects_cognition + test_resume_injects_prior_run_context"
      contains: "def test_turn_injects_cognition"
  key_links:
    - from: "voss/harness/agent.py::run_turn"
      to: "voss/harness/cognition.py::CognitionBundle"
      via: "system message construction: cognition prepend + PLAN_SYSTEM"
      pattern: "_compose_cognition_prompt"
    - from: "voss/harness/render.py::JsonRenderer"
      to: "stdout NDJSON"
      via: "_emit(type='cognition_loaded', ...) and _emit(type='cognition_overflow', ...)"
      pattern: "cognition_loaded\\|cognition_overflow"
    - from: "voss/harness/cli.py::resume_cmd"
      to: "voss/harness/agent.py::run_turn"
      via: "prior_context=record.runs[-1] passed via run_turn keyword + agent inlines into system prompt"
      pattern: "prior_context\\|record\\.runs\\[-1\\]"
---

<objective>
Wire cognition auto-injection into every agent turn per D-17/D-18: prepend architecture.md + constraints bullets to the system prompt with a 6k token reservation that truncates constraints first on overflow; expose the renderer surfaces (D-20) so users see the cognition status line and machine readers get the NDJSON event; and rehydrate the most-recent RunRecord as a "Prior context" block in `voss resume` (D-19).

Purpose: This is the "Repeated sessions improve from stored context" success criterion of M2 — without this plan, M2-01..M2-04 produce inert files that nothing reads. After this plan, every turn that runs in a project with `.voss/architecture.md` starts with cognition loaded, visible in the renderer, and bounded by the 6k reservation. The resume rehydration closes the gap between session end and the next session start.

Output:
- `voss/harness/agent.py` — `_compose_cognition_prompt(bundle, *, model)` helper, `_truncate_for_budget` helper, cognition prepend at run_turn system-message construction site, `prior_context` parameter handling.
- `voss/harness/render.py` — `show_cognition` added to Renderer Protocol + 3 implementations + `cognition_overflow` JSON event.
- `voss/harness/cli.py` — `_run_repl` calls `cognition.load(cwd, token_count=...)` once at boot and passes the bundle into every `run_turn`; `resume_cmd` additionally pulls `record.runs[-1]` as prior_context.
- 5 tests flipped from skip to live + 2 new agent_integration tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M2-project-cognition/M2-CONTEXT.md
@.planning/phases/M2-project-cognition/M2-RESEARCH.md
@.planning/phases/M2-project-cognition/M2-PATTERNS.md
@voss/harness/agent.py
@voss/harness/render.py
@voss/harness/cli.py
@voss/harness/cognition.py

<interfaces>
From voss/harness/cognition.py (M2-01):
    @dataclass(frozen=True) CognitionBundle(initialized, project, architecture_md, architecture_frontmatter, constraints, permissions, validation, architecture_tokens, load_errors)
    def load(cwd, *, token_count=None) -> CognitionBundle
    def render_constraints_bullets(c: ConstraintsConfig | None) -> str

From voss/harness/agent.py (M2-03 currently):
    async def run_turn(task, *, tools, cwd, renderer, ..., cognition=None, session_id=None) -> TurnResult
        — accepts `cognition` keyword but currently no-ops it. This plan implements the prepend.
    PLAN_SYSTEM = "You are Voss, a coding agent ..." (line 64)
    System message construction site: lines 150-162 (messages=[{"role":"system","content":PLAN_SYSTEM}, ...]).

From voss/harness/render.py (M1):
    class Renderer(Protocol):  # lines 24-32 — add show_cognition method
    class TtyRenderer (line 51); class PlainRenderer (line 134); class JsonRenderer (line 167)
    JsonRenderer._emit(**kw) — used to emit events. V=1.

litellm.token_counter signature for the 6k budget calculation:
    import litellm
    litellm.token_counter(model=str, text=str) -> int

6k budget rule (D-18):
    BUDGET_TOKENS = 6000
    cognition_text = _compose_cognition_prompt(bundle, model=model)
    if litellm.token_counter(model=model, text=cognition_text) > BUDGET_TOKENS:
        # Truncate constraints bullets only; keep architecture intact.
        # Re-render with fewer (or zero) constraints. Emit cognition_overflow event.
        # Surface user-visible click.echo hint:
        #   "architecture.md is X tokens (over 6k budget) — /analyze can rewrite a tighter digest"

Prior-context block (D-19) format — prepended to PLAN_SYSTEM only on resume:
    "Prior context (most-recent turn):\n"
    f"- goal: {run.goal}\n"
    f"- plan rationale: {plan_rationale}\n"
    f"- decisions: {bulleted}\n"
    f"- follow_ups: {bulleted}\n"
    f"- risks: {bulleted}\n"
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add Renderer.show_cognition (Tty/Plain/Json) + cognition_overflow event</name>
  <files>voss/harness/render.py, tests/harness/test_repl_cognition.py</files>
  <read_first>
    - voss/harness/render.py (entire file — Protocol at 24-32, TtyRenderer 51-119, PlainRenderer 134-159, JsonRenderer 167-203)
    - .planning/phases/M2-project-cognition/M2-CONTEXT.md (§D-20 — status-line wording, NDJSON event shape)
    - .planning/phases/M2-project-cognition/M2-PATTERNS.md (§voss/harness/render.py MODIFIED — verbatim show_cognition snippets per renderer)
    - tests/harness/test_repl_cognition.py (Wave-3 stubs from M2-00 — exact names this task unskips)
  </read_first>
  <behavior>
    - test_cognition_status_line_tty: instantiate TtyRenderer with a captured Console; call show_cognition(architecture_tokens=1200, constraints_count=2); the captured output contains "cognition: architecture (1.2k) + 2 constraints" (with dim/style markup acceptable).
    - test_cognition_loaded_ndjson_event: instantiate JsonRenderer; capture stdout; call show_cognition(architecture_tokens=1200, constraints_count=2, plans_loaded=0, decisions_loaded=0); stdout has one NDJSON line that json-decodes to {"v": 1, "type": "cognition_loaded", "architecture_tokens": 1200, "constraints_count": 2, "plans_loaded": 0, "decisions_loaded": 0}.
    - test_cognition_overflow_truncates_constraints: build a CognitionBundle with a huge architecture_md (e.g. 8000-token text via a long lorem string + the litellm.token_counter measured value, OR use a stubbed token_count callable). Call the helper `_compose_cognition_prompt(bundle, model="claude-sonnet-4-5", token_count_fn=<stub>)` — assert the helper truncates constraints to empty when the budget is blown, returns a text whose token count is ≤ 6000 (per stub), AND that a side-effect emits the cognition_overflow event (via the renderer if passed, or returns an overflow flag the caller raises into the renderer).
  </behavior>
  <action>
    1. Edit voss/harness/render.py.
    2. Update the Renderer Protocol (lines 24-32) to add: `def show_cognition(self, *, architecture_tokens: int, constraints_count: int, plans_loaded: int = 0, decisions_loaded: int = 0) -> None: ...`. Also add: `def show_cognition_overflow(self, *, architecture_tokens: int, budget: int = 6000) -> None: ...` and `def show_warning(self, msg: str) -> None: ...` (the show_warning was referenced by M2-03 with a placeholder; add the protocol slot here).
    3. TtyRenderer.show_cognition: prints `[dim]  cognition: architecture (Xk) + N constraints[/dim]` where X = architecture_tokens / 1000 formatted to 1 decimal. If plans_loaded or decisions_loaded > 0, extend with `+ P plans + D decisions`. Suppress entirely if `self.quiet` is True (add `quiet: bool = False` field to TtyRenderer dataclass; later wired by make_renderer when a future --quiet flag exists; for now default False).
    4. TtyRenderer.show_cognition_overflow: prints `[yellow]⚠ architecture.md is {architecture_tokens} tokens (over {budget} budget) — /analyze can rewrite a tighter digest[/yellow]`.
    5. TtyRenderer.show_warning: prints `[yellow]⚠ {msg}[/yellow]`.
    6. PlainRenderer.show_cognition: `print(f"cognition: arch={architecture_tokens}tok constraints={constraints_count}", file=sys.stderr)`.
    7. PlainRenderer.show_cognition_overflow: `print(f"cognition overflow: {architecture_tokens} > {budget}", file=sys.stderr)`.
    8. PlainRenderer.show_warning: `print(f"warning: {msg}", file=sys.stderr)`.
    9. JsonRenderer.show_cognition: `self._emit(type="cognition_loaded", architecture_tokens=architecture_tokens, constraints_count=constraints_count, plans_loaded=plans_loaded, decisions_loaded=decisions_loaded)`.
    10. JsonRenderer.show_cognition_overflow: `self._emit(type="cognition_overflow", architecture_tokens=architecture_tokens, budget=budget)`.
    11. JsonRenderer.show_warning: `self._emit(type="warning", message=msg)`.
    12. In tests/harness/test_repl_cognition.py: unskip the 3 Wave-3 tests. Use rich.console.Console(file=StringIO()) for the Tty test capture; capsys for the Json test capture.
    13. test_cognition_overflow_truncates_constraints — this test verifies the agent.py helper but also that the renderer emits the overflow event. Mock the helper if necessary; the assertion is "calling _compose_cognition_prompt with a bundle whose architecture_tokens already exceed 6000 results in constraints being truncated to empty in the returned text". Couple the renderer event verification with capturing the renderer output (the helper takes an optional renderer arg, or the caller pulls a returned overflow flag and calls renderer.show_cognition_overflow).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/test_repl_cognition.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def show_cognition\\|def show_cognition_overflow\\|def show_warning" voss/harness/render.py` returns at least 9 (3 methods × 3 renderers; protocol declarations may add 3 more).
    - `grep -c "cognition_loaded\\|cognition_overflow" voss/harness/render.py` returns at least 2.
    - `pytest tests/harness/test_repl_cognition.py::test_cognition_status_line_tty -v` exits 0.
    - `pytest tests/harness/test_repl_cognition.py::test_cognition_loaded_ndjson_event -v` exits 0.
    - `pytest tests/harness/test_repl_cognition.py::test_cognition_overflow_truncates_constraints -v` exits 0.
    - Pre-existing render-using tests (test_cli.py — runs renderer indirectly via CliRunner) still pass: `pytest tests/harness/test_cli.py -x` exits 0.
  </acceptance_criteria>
  <done>Renderer trio gains cognition surfaces; 3 renderer tests pass; overflow path is testable.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire cognition prepend in run_turn + prior_context for resume + REPL boot loads bundle once</name>
  <files>voss/harness/agent.py, voss/harness/cli.py, tests/harness/test_agent_integration.py</files>
  <read_first>
    - voss/harness/agent.py (lines 100-231 — full run_turn, especially message construction at 150-162; M2-03 added cognition=None and session_id=None params)
    - voss/harness/cli.py (lines 227-326 — _run_repl, where cognition.load should happen once at start; resume_cmd 402-442)
    - voss/harness/cognition.py (M2-01 — load + render_constraints_bullets signatures)
    - voss/harness/render.py (just-modified show_cognition surfaces)
    - .planning/phases/M2-project-cognition/M2-CONTEXT.md (§D-17, D-18, D-19, D-20)
    - .planning/phases/M2-project-cognition/M2-PATTERNS.md (§voss/harness/agent.py MODIFIED — cognition prepend insertion point)
    - tests/harness/test_agent_integration.py (FakeProvider patterns; M2-03 extended for record_run)
  </read_first>
  <behavior>
    - test_turn_injects_cognition: build a tmp_path with .voss/architecture.md (frontmatter + body) + .voss/constraints.yml (one rule). Use a FakeProvider that captures `messages` from complete(); invoke run_turn(..., cognition=cognition.load(tmp_path)). Assert the first system message includes the architecture.md body AND a bullet rendered from the constraint rule, ALL preceding the PLAN_SYSTEM text.
    - test_resume_injects_prior_run_context: build a SessionRecord with one prior run in `runs` (goal="prev goal", decisions=[{"title":"chose X","body":"b","confidence":0.9}], follow_ups=["next: y"], risks=["r1"]). Call run_turn(..., prior_context=runs[-1]); assert the system message contains "Prior context" and the goal/decisions/follow_ups/risks strings.
    - (Existing tests still pass — the cognition=None default keeps M1-style turns unchanged.)
  </behavior>
  <action>
    1. Edit voss/harness/agent.py.
    2. Define helper `_compose_cognition_prompt(bundle, *, model: str, token_count_fn=None, renderer=None) -> str`:
       - If bundle is None or not bundle.initialized → return "".
       - body = "" — start with `# Project cognition\n\n## Architecture\n\n{bundle.architecture_md}\n\n## Constraints\n\n{render_constraints_bullets(bundle.constraints)}"`.
       - If token_count_fn is provided, measure body; if measured > 6000:
           - Emit overflow via renderer.show_cognition_overflow if renderer is provided.
           - Re-render dropping constraints entirely (`body_no_constraints = "# Project cognition\n\n## Architecture\n\n{bundle.architecture_md}"`).
           - Return body_no_constraints + " (constraints truncated due to budget)" suffix.
       - Return body.
    3. Default token_count_fn — `from voss_runtime.providers.litellm_provider import ...` or use `litellm.token_counter` directly: `def _default_token_count(text, *, model): return litellm.token_counter(model=model, text=text)`. Pass into the helper as a partial.
    4. Modify run_turn:
       - Add `prior_context: dict | None = None` kwarg.
       - Build `cognition_text = _compose_cognition_prompt(cognition, model=model, token_count_fn=_default_token_count, renderer=renderer)`.
       - Build `prior_context_text = _compose_prior_context_block(prior_context)` where helper formats the D-19 block (returns "" if None).
       - sys_prompt = "\n\n".join(filter(None, [cognition_text, prior_context_text, PLAN_SYSTEM])).
       - Use sys_prompt as the "system" content in messages.
       - After the (possibly-overflowed) cognition compose, also call renderer.show_cognition if cognition is initialized:
           constraints_count = len(cognition.constraints.rules) if cognition.constraints and cognition.constraints.rules else 0
           renderer.show_cognition(architecture_tokens=cognition.architecture_tokens, constraints_count=constraints_count)
    5. Helper `_compose_prior_context_block(run_dict)` returns a string per D-19 format or "" if run_dict is None or empty.
    6. Edit voss/harness/cli.py — _run_repl:
       - Near the top of _run_repl (after `renderer = make_renderer(...)`), insert: `from . import cognition as cognition_mod`; `bundle = cognition_mod.load(cwd, token_count=lambda t: __import__('litellm').token_counter(model=cfg.default_model, text=t))`.
       - If `bundle.load_errors`: for each err, click.echo(f"cognition error: {err}", err=True).
       - Pass `cognition=bundle` into the run_turn calls.
    7. Edit voss/harness/cli.py — resume_cmd:
       - After session_store.load(...) returns (record, history), if `record.runs`: extract `record.runs[-1]` as the prior_context dict.
       - Pass `prior_context=<dict>` into _run_repl OR into the first run_turn call. (Cleaner: pass into _run_repl via a new kwarg; _run_repl uses it on the FIRST turn only.)
       - Add `prior_context: dict | None = None` kwarg to `_run_repl`; on first turn pass to run_turn, then set to None.
    8. In tests/harness/test_agent_integration.py: add `test_turn_injects_cognition` and `test_resume_injects_prior_run_context` per behavior. Use the existing FakeProvider pattern; capture `provider.calls[0]["messages"]` to inspect the system prompt.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/test_agent_integration.py tests/harness/test_repl_cognition.py tests/harness/test_cli.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "_compose_cognition_prompt\\|_compose_prior_context_block" voss/harness/agent.py` returns at least 2.
    - `grep -c "renderer\\.show_cognition" voss/harness/agent.py` returns at least 1.
    - `grep -c "cognition_mod\\.load\\|cognition\\.load(cwd" voss/harness/cli.py` returns at least 1.
    - `grep -c "prior_context" voss/harness/cli.py voss/harness/agent.py` returns at least 4 (signature + call sites).
    - `pytest tests/harness/test_agent_integration.py::test_turn_injects_cognition -v` exits 0.
    - `pytest tests/harness/test_agent_integration.py::test_resume_injects_prior_run_context -v` exits 0.
    - `pytest tests/harness/test_cli.py -x` exits 0 (no regression — REPL still launches cleanly with or without `.voss/`).
    - Manual: in a non-`.voss/` directory, run `voss chat` and confirm no cognition status line appears (bundle.initialized=False → no show_cognition call).
  </acceptance_criteria>
  <done>Cognition prepend + 6k budget enforcement + prior-context rehydration are wired and testable; REPL boot loads bundle once.</done>
</task>

</tasks>

<verification>
- `pytest tests/harness/ -x` exits 0; cognition-injection + overflow + prior-context tests green.
- Manual: `voss chat` in this repo (after running /analyze once) shows the dim `cognition: architecture (Xk) + N constraints` line on the first turn.
- Manual: `voss chat --json` produces an NDJSON `cognition_loaded` event before any `plan` event.
- Manual: `voss resume <id>` after a session with at least one RunRecord shows the agent referencing the prior goal in its first response.
</verification>

<success_criteria>
- M2 success criterion 5 ("Repeated sessions improve from stored project context") observably true via auto-injection.
- 6k cognition budget enforced — constraints get truncated first; user sees the overflow hint (Pitfall 2).
- Renderer trio gains cognition surfaces without breaking existing renderer tests.
- Resume rehydrates the most-recent RunRecord as a "Prior context" block — closes the cross-session memory loop.
- M1-style runs (cognition=None) remain unchanged — backward compatibility preserved.
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| disk → system prompt | architecture.md and constraints.yml content lands in every LLM prompt |
| prior_context (run JSON) → system prompt | persisted agent free-form text gets re-injected |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M2-17 | Information Disclosure | architecture.md authored by agent contains accidentally-pasted user secrets | accept | Same posture as M1 D-17 user-prompt passthrough; documented carve-out. Architecture.md sits in `.voss/`, gitignored by default for the file itself only when `.voss/.gitignore` lists it (it doesn't — architecture.md IS committed). User responsibility. |
| T-M2-18 | Denial of Service | architecture.md grows to 50k tokens, every turn blocked or LLM context overflows | mitigate | 6k budget check + cognition_overflow event + user-visible hint (Pitfall 2); constraints truncate first; architecture stays but turn proceeds. |
| T-M2-19 | Tampering | prior_context contains malicious decision body that prompt-injects the next agent turn | accept | Prior runs are produced by the SAME agent in the SAME project; trust boundary is already inside the agent's authority. Out of scope for M2 — flagged for future "agent-vs-agent" security review. |
| T-M2-20 | Reliability | litellm.token_counter unavailable (litellm import fails) → 6k check skipped silently | mitigate | _compose_cognition_prompt wraps token_count_fn call in try/except; on exception treats as "unmeasurable", emits a one-line cognition_warning event but still prepends architecture. No silent skip. |
</threat_model>

<output>
After completion, create `.planning/phases/M2-project-cognition/M2-05-SUMMARY.md` documenting: (1) the system-prompt composition order (cognition → prior_context → PLAN_SYSTEM), (2) the 6k truncation rule (constraints first), (3) the renderer surface additions per renderer, (4) the prior_context dict shape consumed by resume, (5) how to disable auto-inject (pass cognition=None to run_turn — used by /analyze bootstrap and tests).
</output>
